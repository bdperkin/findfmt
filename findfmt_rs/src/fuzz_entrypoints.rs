//! Pure-Rust fuzzing entrypoints shared across `cargo-fuzz`, `proptest`, and smoke tests (#585).

use std::collections::BTreeSet;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::classifier::{RawClassifyInput, classify_batch_nogil, classify_one_nogil};
use crate::gitignore::{GitignoreMatcher, compile_glob_matcher, trim_gitignore_line};
use crate::header::is_text_buffer;
use crate::metadata::{RawStat, classification_indicator, format_filemode};
use crate::mime::py_splitext;
use crate::patterns::PatternMatcher;
use crate::shebang::{extract_shebang_from_buffer, parse_shebang_tokens, py_strip, shebang_split};
use crate::sorting::{NaturalSortKey, compare_natural, natural_sort_key};
use crate::tags::{FilterCriteria, TagRegistry};
use crate::walker::NativeWalker;
use crate::walker_types::{
    GlobalIgnoreResolution, MimeSnapshot, RootTarget, WalkConfig, WalkSortKey,
};

static FUZZ_REGISTRY: OnceLock<TagRegistry> = OnceLock::new();
static SCRATCH_SEQ: AtomicU64 = AtomicU64::new(0);

fn shared_registry() -> &'static TagRegistry {
    FUZZ_REGISTRY.get_or_init(TagRegistry::sample_registry)
}

/// Fuzz shebang extraction, POSIX shlex tokenization, and binary-vs-text byte detection.
///
/// Returns `(is_text, extracted_shebang, parsed_tokens)` so callers can assert invariants.
pub fn fuzz_shebang_and_header_bytes(data: &[u8]) -> (bool, Option<String>, Vec<String>) {
    let text_ok = is_text_buffer(data);
    let raw_shebang = extract_shebang_from_buffer(data);
    let parsed = parse_shebang_tokens(data);

    let lossy = String::from_utf8_lossy(data);
    let trimmed = py_strip(&lossy);
    let _ = shebang_split(trimmed);

    (text_ok, raw_shebang, parsed)
}

fn sanitize_temp_filename(raw: &str) -> String {
    let cleaned: String = raw
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '-' | '_'))
        .take(24)
        .collect();
    if cleaned.is_empty() || cleaned.chars().all(|c| c == '.') {
        "fuzz_sample.dat".to_owned()
    } else {
        cleaned
    }
}

fn create_private_scratch_dir() -> Option<PathBuf> {
    let base = std::env::temp_dir();
    let pid = std::process::id();
    for attempt in 0_u32..16_u32 {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0_u128, |d| d.as_nanos());
        let seq = SCRATCH_SEQ.fetch_add(1, Ordering::Relaxed);
        let candidate = base.join(format!("findfmt_rs_fuzz_{pid}_{nanos:x}_{seq:x}_{attempt}"));
        #[cfg(unix)]
        let created = {
            use std::os::unix::fs::DirBuilderExt;
            fs::DirBuilder::new().mode(0o700).create(&candidate)
        };
        #[cfg(not(unix))]
        let created = fs::create_dir(&candidate);
        if created.is_ok() {
            return Some(candidate);
        }
    }
    None
}

fn write_exclusive_sample(dir: &Path, safe_name: &str, payload: &[u8]) -> Option<PathBuf> {
    let file_path = dir.join(safe_name);
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&file_path)
        .ok()?;
    file.write_all(payload).ok()?;
    Some(file_path)
}

#[allow(clippy::type_complexity)]
fn build_pre_stat(file_path: Option<&Path>) -> Option<(bool, bool, bool, u64, Option<RawStat>)> {
    let Some(path) = file_path else {
        return Some((false, false, false, 0, None));
    };
    #[cfg(unix)]
    {
        let _ = path;
        None
    }
    #[cfg(not(unix))]
    {
        match fs::metadata(path) {
            Ok(meta) => {
                let raw = RawStat::from_std_metadata(&meta);
                Some((false, true, raw.is_reg(), raw.size, Some(raw)))
            }
            Err(_) => Some((false, false, false, 0, None)),
        }
    }
}

/// Fuzz filename/MIME splitting, tag tables, mode formatting, and GIL-free file classification.
///
/// Returns `(split_reconstructed, mode_len, tags)` for caller invariant checks.
pub fn fuzz_classifier_and_tags_bytes(data: &[u8]) -> (bool, usize, BTreeSet<String>) {
    let registry = shared_registry();
    let mid = (data.len() / 3).min(64);
    let (meta_slice, payload) = data.split_at(mid);
    let raw_name = String::from_utf8_lossy(meta_slice);

    let (stem, ext) = py_splitext(&raw_name);
    let reconstructed = format!("{stem}{ext}") == raw_name;

    let _ = registry.tags_from_filename(&raw_name);
    let _ = registry.tags_from_interpreter(&raw_name);
    let _ = registry.guess_mime_type(&raw_name);

    let mode_bits = data.iter().take(4).fold(0_u32, |acc, &b| (acc << 8) | u32::from(b));
    let mode_str = format_filemode(mode_bits);
    let synth_stat = RawStat {
        mode: mode_bits,
        size: u64::try_from(payload.len()).unwrap_or(u64::MAX),
        uid: Some(1000),
        gid: Some(1000),
        ino: Some(1),
        dev: Some(1),
        mtime: Some(0.0),
        ctime: Some(0.0),
    };
    let _ = classification_indicator(
        synth_stat.is_dir(),
        synth_stat.is_lnk(),
        (mode_bits & 0o111) != 0,
        Some(&synth_stat),
    );

    let safe_name = sanitize_temp_filename(&raw_name);
    let scratch_dir = create_private_scratch_dir();
    let written_path = scratch_dir
        .as_deref()
        .and_then(|dir| write_exclusive_sample(dir, &safe_name, payload));
    let pre_stat = build_pre_stat(written_path.as_deref());
    let effective_path = written_path
        .clone()
        .unwrap_or_else(|| PathBuf::from(&safe_name));

    let input = RawClassifyInput {
        path: effective_path,
        str_path: raw_name.into_owned(),
        filename: safe_name,
        follow_symlinks: data.first().is_some_and(|b| (b & 1) == 0),
        accumulated_size: None,
        pre_stat,
        pre_guessed_mime: None,
    };
    let pathext = data
        .get(1)
        .is_some_and(|b| (b & 1) == 1)
        .then(|| vec![".EXE".to_owned(), ".PY".to_owned()]);
    let classified = classify_one_nogil(&input, registry, pathext.as_deref());

    let filter = FilterCriteria {
        include_tags: BTreeSet::from(["file".to_owned()]),
        exclude_tags: BTreeSet::new(),
        all_tags: data.get(2).is_some_and(|b| (b & 1) == 1),
        shebang_filter: None,
    };
    let _ = classify_batch_nogil(std::slice::from_ref(&input), Some(&filter), registry, None);
    if let Some(dir) = scratch_dir {
        let _ = fs::remove_dir_all(&dir);
    }

    (reconstructed, mode_str.chars().count(), classified.tags)
}

/// Fuzz `.gitignore` line trimming, malformed glob compilation, path matching, and natural sorting.
///
/// Returns sorted `NaturalSortKey` sequence for caller monotonicity verification.
pub fn fuzz_sort_and_gitignore_bytes(data: &[u8]) -> Vec<NaturalSortKey> {
    let split_at = data.len() / 2;
    let (gi_bytes, paths_bytes) = data.split_at(split_at);

    let root = Path::new("/fuzz_root");
    let (matcher, _err_count) = GitignoreMatcher::from_bytes_lossy(root, gi_bytes);

    let gi_lossy = String::from_utf8_lossy(gi_bytes);
    for raw_line in gi_lossy.lines().take(16) {
        let trimmed = trim_gitignore_line(raw_line);
        let _ = compile_glob_matcher(trimmed, data.first().is_some_and(|b| (b & 1) == 1));
    }

    let paths_lossy = String::from_utf8_lossy(paths_bytes);
    let ignore_case = data.last().is_some_and(|b| (b & 1) == 1);
    let mut names: Vec<&str> = paths_lossy.split(['\n', '\0']).take(32).collect();
    for candidate in &names {
        let is_dir = candidate.ends_with('/');
        let _ = matcher.is_ignored(Path::new(candidate), is_dir);
        let joined = root.join(candidate);
        let _ = matcher.is_ignored(&joined, is_dir);
    }

    if let Some(dir) = create_private_scratch_dir() {
        let _ = write_exclusive_sample(&dir, ".gitignore", gi_bytes);
        let _ = write_exclusive_sample(&dir, "fuzz_a.py", paths_bytes);
        let walk_cfg = WalkConfig {
            respect_gitignore: true,
            custom_gitignore_file: None,
            include_hidden: (data.first().copied().unwrap_or(0) & 2) != 0,
            follow_symlinks: false,
            dirs_only: (data.first().copied().unwrap_or(0) & 4) != 0,
            one_file_system: false,
            max_depth: Some(3),
            file_limit: None,
            prune_empty: (data.first().copied().unwrap_or(0) & 8) != 0,
            ignore_case,
            match_dirs: false,
            accumulate_size: false,
            sort_by: WalkSortKey::Version,
            reverse_sort: false,
            dirs_first: (data.first().copied().unwrap_or(0) & 16) != 0,
            filter: FilterCriteria::default(),
            matcher: PatternMatcher::default(),
            home_dir: None,
            pathext_upper: None,
            unicode_major: 16,
            mime_snapshot: MimeSnapshot::default(),
        };
        let target = RootTarget {
            raw_root: dir.clone(),
            resolved_root: Some(dir.clone()),
            prefix: None,
            global_gitignore: GlobalIgnoreResolution::Unresolved,
            initial_error: None,
        };
        let mut walker = NativeWalker::new(walk_cfg, shared_registry(), vec![target]);
        let _ = walker.next_batch(32);
        let _ = fs::remove_dir_all(&dir);
    }

    names.sort_by(|a, b| compare_natural(a, b, ignore_case));
    names
        .into_iter()
        .map(|s| natural_sort_key(s, ignore_case))
        .collect()
}
