//! Shared entry filtering, `-x` device confinement, and `RawClassifyInput` construction (#582).

use std::ffi::OsStr;
use std::fs;
use std::path::{Path, PathBuf};

use crate::classifier::RawClassifyInput;
use crate::gitignore::GitignoreMatcher;
use crate::ignore_stack::is_path_ignored;
use crate::walker_types::{ScannedEntry, WalkConfig};

/// Return `true` when `name` starts with `'.'`.
pub fn is_hidden_name(name: &OsStr) -> bool {
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;
        name.as_bytes().first() == Some(&b'.')
    }
    #[cfg(not(unix))]
    {
        name.to_string_lossy().starts_with('.')
    }
}

/// Mirror `src/findfmt/traversal/_pruning.py:should_skip_dir`.
pub fn should_skip_dir(dir_name: &OsStr, include_hidden: bool) -> bool {
    dir_name == OsStr::new(".git") || (!include_hidden && is_hidden_name(dir_name))
}

/// Revalidate a queued directory path before opening or loading child ignore files (`#582`).
///
/// When `follow_symlinks` is `false`, rejects paths replaced with symlinks or non-directories
/// after parent enumeration while allowing unreadable real directories (`chmod 000`) to proceed
/// so `read_dir` reports `PermissionError` via `on_error`.
pub fn is_valid_descent_dir(dir: &Path, follow_symlinks: bool) -> bool {
    if follow_symlinks {
        return true;
    }
    match fs::symlink_metadata(dir) {
        Ok(meta) => !meta.file_type().is_symlink() && meta.file_type().is_dir(),
        Err(_) => true,
    }
}

/// Compute `relative_path` mirroring `classifier.py:_resolve_relative`.
pub fn resolve_relative_pathbuf(
    path: &Path,
    base_root: &Path,
    prefix: Option<&Path>,
) -> PathBuf {
    let Ok(rel) = path.strip_prefix(base_root) else {
        return path.to_path_buf();
    };
    let rel_norm = if rel.as_os_str().is_empty() {
        Path::new(".")
    } else {
        rel
    };
    match prefix {
        Some(pfx) if !pfx.as_os_str().is_empty() && pfx != Path::new(".") => pfx.join(rel_norm),
        _ => rel_norm.to_path_buf(),
    }
}

/// Resolve platform filesystem device ID (`st_dev`) mirroring `src/findfmt/traversal/devices.py`.
pub fn resolve_device_id(path: &Path, is_symlink: bool, follow_symlinks: bool) -> Option<u64> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        let meta = if follow_symlinks || !is_symlink {
            fs::metadata(path).ok()?
        } else {
            fs::symlink_metadata(path).ok()?
        };
        let dev = meta.dev();
        if dev != 0 {
            Some(dev)
        } else {
            fs::metadata(path).ok().map(|m| m.dev())
        }
    }
    #[cfg(not(unix))]
    {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        use std::path::Component;

        let target_for_volume = if is_symlink && !follow_symlinks {
            let _ = fs::symlink_metadata(path).ok()?;
            path.parent().unwrap_or(path)
        } else {
            path
        };
        let canon = fs::canonicalize(target_for_volume).ok()?;
        let mut hasher = DefaultHasher::new();
        match canon.components().next()? {
            Component::Prefix(pfx) => pfx.as_os_str().to_string_lossy().to_ascii_uppercase().hash(&mut hasher),
            other => other.hash(&mut hasher),
        }
        Some(hasher.finish())
    }
}

fn check_entry_device(
    entry_path: &Path,
    is_symlink: bool,
    follow_symlinks: bool,
    root_dev: Option<u64>,
) -> bool {
    let Some(expected_dev) = root_dev else {
        return true;
    };
    resolve_device_id(entry_path, is_symlink, follow_symlinks) == Some(expected_dev)
}

/// Filter a directory entry by hidden status, `-x` device boundary, gitignore, and `-I` patterns.
///
/// Returns `Some((entry_path, is_dir, is_candidate_file, is_symlink))` or `None` if excluded.
pub fn filter_entry_nogil(
    entry: &ScannedEntry,
    config: &WalkConfig,
    specs: &[GitignoreMatcher],
    root_dev: Option<u64>,
    base_root: &Path,
) -> Option<(PathBuf, bool, bool, bool)> {
    if !config.include_hidden && is_hidden_name(&entry.file_name) {
        return None;
    }
    let is_symlink = match entry.file_type {
        Some(ft) => ft.is_symlink(),
        None => fs::symlink_metadata(&entry.path).is_ok_and(|m| m.file_type().is_symlink()),
    };
    if config.one_file_system
        && !check_entry_device(&entry.path, is_symlink, config.follow_symlinks, root_dev)
    {
        return None;
    }

    let (is_dir, is_candidate_file) = if !is_symlink {
        match entry.file_type {
            Some(ft) => (ft.is_dir(), ft.is_file()),
            None => {
                let meta = fs::symlink_metadata(&entry.path).ok()?;
                (meta.is_dir(), meta.is_file())
            }
        }
    } else if config.follow_symlinks {
        let target_meta = fs::metadata(&entry.path).ok()?;
        (target_meta.is_dir(), target_meta.is_file())
    } else {
        (false, true)
    };

    if (config.respect_gitignore || !specs.is_empty())
        && is_path_ignored(&entry.path, is_dir, specs)
    {
        return None;
    }
    if config
        .matcher
        .should_exclude(&entry.path, is_dir, Some(base_root))
    {
        return None;
    }
    Some((entry.path.clone(), is_dir, is_candidate_file, is_symlink))
}

/// Compute `(st_mode & 0o111) != 0` hint for early interpreter-tag skipping (`_pruning.py` parity).
pub fn executable_hint_for_skip(
    entry_path: &Path,
    filename: &str,
    is_symlink: bool,
    follow_symlinks: bool,
) -> Option<bool> {
    #[cfg(unix)]
    {
        let _ = filename;
        use std::os::unix::fs::MetadataExt;
        let meta = if follow_symlinks || !is_symlink {
            fs::metadata(entry_path).ok()?
        } else {
            fs::symlink_metadata(entry_path).ok()?
        };
        Some((meta.mode() & 0o111) != 0)
    }
    #[cfg(windows)]
    {
        let meta = if follow_symlinks || !is_symlink {
            fs::metadata(entry_path).ok()?
        } else {
            fs::symlink_metadata(entry_path).ok()?
        };
        if meta.is_dir() {
            return Some(true);
        }
        let lower = filename.to_ascii_lowercase();
        Some(
            lower.ends_with(".exe")
                || lower.ends_with(".bat")
                || lower.ends_with(".cmd")
                || lower.ends_with(".com"),
        )
    }
    #[cfg(not(any(unix, windows)))]
    {
        let _ = (entry_path, filename, is_symlink, follow_symlinks);
        None
    }
}

/// Build a `RawClassifyInput` for a filesystem path during GIL-free traversal.
pub fn build_raw_classify_input(
    path: PathBuf,
    follow_symlinks: bool,
    accumulated_size: Option<u64>,
    config: &WalkConfig,
) -> RawClassifyInput {
    let str_path = path.to_string_lossy().into_owned();
    let filename = path
        .file_name()
        .map_or_else(String::new, |n| n.to_string_lossy().into_owned());
    let pre_guessed_mime = Some(config.mime_snapshot.guess_mime_type(&str_path));
    #[cfg(not(unix))]
    let pre_stat = {
        use crate::metadata::RawStat;
        match fs::symlink_metadata(&path).ok() {
            Some(lst) => {
                let is_sym = lst.file_type().is_symlink();
                let eff_opt = if is_sym && follow_symlinks {
                    fs::metadata(&path).ok()
                } else {
                    Some(lst)
                };
                match eff_opt {
                    Some(eff) => {
                        let raw = RawStat::from_std_metadata(&eff);
                        let is_reg = raw.is_reg();
                        let sz = raw.size;
                        Some((is_sym, true, is_reg, sz, Some(raw)))
                    }
                    None => Some((is_sym, false, false, 0, None)),
                }
            }
            None => Some((false, false, false, 0, None)),
        }
    };
    #[cfg(unix)]
    let pre_stat = None;

    RawClassifyInput {
        path,
        str_path,
        filename,
        follow_symlinks,
        accumulated_size,
        pre_stat,
        pre_guessed_mime,
    }
}
