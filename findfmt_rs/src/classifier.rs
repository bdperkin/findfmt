//! GIL-free file classification engine mirroring `src/findfmt/classifier.py` (#583).

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

use crate::header::{MAX_HEADER_BYTES, is_text_buffer, read_header_nonblocking};
use crate::metadata::{RawStat, classification_indicator, format_filemode};
use crate::shebang::{extract_shebang_from_buffer, parse_shebang_tokens};
use crate::tags::{FilterCriteria, TagRegistry};

/// Pure-Rust input descriptor for classifying a single path without holding the Python GIL.
#[derive(Clone, Debug)]
pub struct RawClassifyInput {
    pub path: PathBuf,
    /// String form of `path` (`str(path)`) for filename and MIME evaluation.
    pub str_path: String,
    /// Basename of `path` (`path.name`) with `surrogateescape` preserved.
    pub filename: String,
    pub follow_symlinks: bool,
    pub accumulated_size: Option<u64>,
    /// Pre-fetched `RawStat` on platforms where stat metadata comes from OS handle/Python.
    pub pre_stat: Option<(bool, bool, bool, u64, Option<RawStat>)>,
    /// Optional MIME type resolved from Python's live `mimetypes._db` before releasing the GIL.
    pub pre_guessed_mime: Option<Option<String>>,
}

/// Pure-Rust classification result produced inside `py.detach(...)` before building `FileInfo`.
#[derive(Clone, Debug)]
pub struct RawClassifiedFile {
    pub exists: bool,
    pub is_dir: bool,
    pub is_symlink: bool,
    pub symlink_target_path: Option<PathBuf>,
    pub is_executable: bool,
    pub size_bytes: u64,
    pub accumulated_size: Option<u64>,
    pub tags: BTreeSet<String>,
    pub shebang: Option<String>,
    pub mime_type: Option<String>,
    pub permissions_str: Option<String>,
    pub uid: Option<u32>,
    pub gid: Option<u32>,
    pub inode: Option<u128>,
    pub device: Option<u128>,
    pub mtime: Option<f64>,
    pub ctime: Option<f64>,
    pub indicator: Option<&'static str>,
}

#[cfg(unix)]
fn inspect_unix_metadata(
    path: &Path,
    follow_symlinks: bool,
) -> (bool, bool, bool, u64, Option<RawStat>) {
    let Ok(lst) = fs::symlink_metadata(path) else {
        return (false, false, false, 0, None);
    };
    let is_symlink = lst.file_type().is_symlink();
    let effective_meta = if is_symlink && follow_symlinks {
        let Ok(st) = fs::metadata(path) else {
            return (is_symlink, false, false, 0, None);
        };
        st
    } else {
        lst
    };
    let raw = RawStat::from_std_metadata(&effective_meta);
    let is_file = raw.is_reg();
    let size = raw.size;
    (is_symlink, true, is_file, size, Some(raw))
}

fn check_executable(
    filename: &str,
    exists_and_followed: bool,
    shebang: Option<&str>,
    stat: Option<&RawStat>,
    pathext_upper: Option<&[String]>,
) -> bool {
    if !exists_and_followed {
        return false;
    }
    if let Some(exts) = pathext_upper {
        let upper_name = filename.to_uppercase();
        return exts.iter().any(|ext| upper_name.ends_with(ext.as_str())) || shebang.is_some();
    }
    stat.is_some_and(|st| (st.mode & 0o111) != 0)
}

fn identify_tags_from_buffer(
    filename: &str,
    buffer: &[u8],
    is_executable: bool,
    parsed_shebang: &[String],
    registry: &TagRegistry,
) -> BTreeSet<String> {
    let mut tags = BTreeSet::new();
    tags.insert("file".to_owned());
    tags.insert(if is_executable {
        "executable".to_owned()
    } else {
        "non-executable".to_owned()
    });

    let name_tags = registry.tags_from_filename(filename);
    if !name_tags.is_empty() {
        tags.extend(name_tags);
    } else if is_executable
        && buffer.starts_with(b"#!")
        && let Some(first_interp) = parsed_shebang.first()
    {
        tags.extend(registry.tags_from_interpreter(first_interp));
    }

    if !tags.contains("text") && !tags.contains("binary") {
        tags.insert(if is_text_buffer(buffer) {
            "text".to_owned()
        } else {
            "binary".to_owned()
        });
    }
    tags
}

fn identify_tags_without_buffer(
    path: &Path,
    filename: &str,
    exists: bool,
    is_regular_or_symlink: bool,
    registry: &TagRegistry,
) -> BTreeSet<String> {
    if !exists || !is_regular_or_symlink {
        return registry.tags_from_filename(filename);
    }
    let Ok(lst) = fs::symlink_metadata(path) else {
        return registry.tags_from_filename(filename);
    };
    if lst.file_type().is_dir() {
        return BTreeSet::from(["directory".to_owned()]);
    }
    if lst.file_type().is_symlink() {
        return BTreeSet::from(["symlink".to_owned()]);
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::FileTypeExt;
        if lst.file_type().is_socket() {
            return BTreeSet::from(["socket".to_owned()]);
        }
    }
    registry.tags_from_filename(filename)
}

/// Classify a single `RawClassifyInput` without holding the Python GIL.
pub fn classify_one_nogil(
    input: &RawClassifyInput,
    registry: &TagRegistry,
    pathext_upper: Option<&[String]>,
) -> RawClassifiedFile {
    let (is_symlink, exists, mut is_file, mut size_bytes, mut raw_stat) =
        if let Some(ref pre) = input.pre_stat {
            pre.clone()
        } else {
            #[cfg(unix)]
            {
                inspect_unix_metadata(&input.path, input.follow_symlinks)
            }
            #[cfg(not(unix))]
            {
                (false, false, false, 0, None)
            }
        };

    let symlink_target_path = if is_symlink {
        fs::read_link(&input.path).ok()
    } else {
        None
    };

    let follow_target = !is_symlink || input.follow_symlinks;
    let mut buffer: Option<Vec<u8>> = None;
    if exists && is_file && follow_target {
        match read_header_nonblocking(&input.path, MAX_HEADER_BYTES) {
            Some(hdr) => {
                if let Some(ref opened) = hdr.opened_meta
                    && !opened.file_type().is_file()
                {
                    is_file = false;
                    size_bytes = opened.len();
                    raw_stat = Some(RawStat::from_std_metadata(opened));
                }
                buffer = Some(hdr.buffer);
            }
            None => {
                buffer = Some(Vec::new());
            }
        }
    }

    let (shebang, parsed_shebang, shebang_tags) = if is_file && follow_target {
        if let Some(ref buf) = buffer {
            let raw_sb = extract_shebang_from_buffer(buf);
            if raw_sb.is_some() {
                let parts = parse_shebang_tokens(buf);
                let mut sb_tags = BTreeSet::new();
                for part in &parts {
                    sb_tags.extend(registry.tags_from_interpreter(part));
                }
                (raw_sb, parts, sb_tags)
            } else {
                (None, Vec::new(), BTreeSet::new())
            }
        } else {
            (None, Vec::new(), BTreeSet::new())
        }
    } else {
        (None, Vec::new(), BTreeSet::new())
    };

    let is_executable = check_executable(
        &input.filename,
        exists && follow_target,
        shebang.as_deref(),
        raw_stat.as_ref(),
        pathext_upper,
    );

    let mut tags = if exists && (is_file || is_symlink) {
        if let Some(ref buf) = buffer {
            identify_tags_from_buffer(&input.filename, buf, is_executable, &parsed_shebang, registry)
        } else {
            identify_tags_without_buffer(
                &input.path,
                &input.filename,
                exists,
                is_file || is_symlink,
                registry,
            )
        }
    } else {
        registry.tags_from_filename(&input.filename)
    };
    tags.extend(shebang_tags);

    if is_symlink {
        tags.insert("symlink".to_owned());
        tags.extend(registry.tags_from_filename(&input.filename));
        if input.follow_symlinks
            && let Some(target_name) = symlink_target_path.as_deref().and_then(Path::file_name)
        {
            tags.extend(registry.tags_from_filename(&target_name.to_string_lossy()));
        }
    }

    if pathext_upper.is_some() {
        if is_executable {
            tags.remove("non-executable");
            tags.insert("executable".to_owned());
        } else {
            tags.remove("executable");
            tags.insert("non-executable".to_owned());
        }
    }

    let mime_type = match input.pre_guessed_mime {
        Some(ref pre) => pre.clone(),
        None => registry.guess_mime_type(&input.str_path),
    };
    if let Some(ref mt) = mime_type {
        tags.insert(format!("mime:{mt}"));
        if let Some(primary) = mt.split('/').next() {
            tags.insert(primary.to_owned());
        }
    }

    let is_dir = raw_stat.as_ref().is_some_and(RawStat::is_dir);
    let indicator = classification_indicator(is_dir, is_symlink, is_executable, raw_stat.as_ref());
    let permissions_str = raw_stat.as_ref().map(|st| format_filemode(st.mode));
    let effective_size = input.accumulated_size.unwrap_or(size_bytes);

    RawClassifiedFile {
        exists,
        is_dir,
        is_symlink,
        symlink_target_path,
        is_executable,
        size_bytes: effective_size,
        accumulated_size: input.accumulated_size,
        tags,
        shebang,
        mime_type,
        permissions_str,
        uid: raw_stat.as_ref().and_then(|st| st.uid),
        gid: raw_stat.as_ref().and_then(|st| st.gid),
        inode: raw_stat.as_ref().and_then(|st| st.ino),
        device: raw_stat.as_ref().and_then(|st| st.dev),
        mtime: raw_stat.as_ref().and_then(|st| st.mtime),
        ctime: raw_stat.as_ref().and_then(|st| st.ctime),
        indicator,
    }
}

/// Classify a batch of candidate files in a single GIL-free pass with optional tag/shebang filtering.
pub fn classify_batch_nogil(
    inputs: &[RawClassifyInput],
    filter: Option<&FilterCriteria>,
    registry: &TagRegistry,
    pathext_upper: Option<&[String]>,
) -> Vec<(usize, RawClassifiedFile)> {
    let mut results = Vec::with_capacity(inputs.len());
    for (idx, item) in inputs.iter().enumerate() {
        let classified = classify_one_nogil(item, registry, pathext_upper);
        if filter.is_some_and(|crit| {
            !crit.matches(
                &classified.tags,
                classified.shebang.as_deref(),
                classified.is_dir,
            )
        }) {
            continue;
        }
        results.push((idx, classified));
    }
    results
}

#[cfg(test)]
#[path = "classifier_tests.rs"]
mod tests;
