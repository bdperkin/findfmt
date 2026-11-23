//! Core GIL-free traversal types, directory keys, and PEP 383 codepoint ordering (#582).

use std::collections::{HashMap, HashSet};
use std::ffi::{OsStr, OsString};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

use crate::classifier::RawClassifiedFile;
use crate::mime::guess_mime_with_lookup;
use crate::patterns::PatternMatcher;
use crate::tags::FilterCriteria;

/// Canonical sort key variants mirroring `findfmt.models.SortKey`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum WalkSortKey {
    Name,
    Version,
    Time,
    Ctime,
    Size,
    None,
}

/// Owned, GIL-free snapshot of Python's live `mimetypes._db` maps.
#[derive(Clone, Debug, Default)]
pub struct MimeSnapshot {
    pub strict_map: HashMap<String, String>,
    pub suffix_map: HashMap<String, String>,
    pub encodings_map: HashSet<String>,
}

impl MimeSnapshot {
    /// Guess MIME type for `str_path` without holding the Python GIL.
    pub fn guess_mime_type(&self, str_path: &str) -> Option<String> {
        guess_mime_with_lookup(
            str_path,
            |k| self.suffix_map.get(k).cloned(),
            |k| self.encodings_map.contains(k),
            |k| self.strict_map.get(k).cloned(),
        )
    }
}

/// Portable directory identity key for cycle detection and `--prune` memoization (`#318`, `#345`).
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub enum DirKey {
    Inode(u64, u64),
    Canonical(PathBuf),
}

impl DirKey {
    /// Resolve the canonical directory identity (following symlinks) or `None` on `OSError`.
    pub fn from_dir(path: &Path) -> Option<Self> {
        #[cfg(unix)]
        {
            use std::os::unix::fs::MetadataExt;
            let meta = fs::metadata(path).ok()?;
            Some(Self::Inode(meta.dev(), meta.ino()))
        }
        #[cfg(not(unix))]
        {
            fs::canonicalize(path).ok().map(Self::Canonical)
        }
    }
}

/// Scoped memoization key for `--prune` descendant discovery.
pub type PruneMemoKey = (DirKey, Option<PathBuf>);

/// Depth-aware memoization entry for `--prune` descendant discovery.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PruneCache {
    Matched {
        searched_from_depth: usize,
    },
    Empty {
        searched_from_depth: usize,
        had_cycle_skip: bool,
    },
}

/// Pre-resolved root target passed into `NativeWalker`.
#[derive(Clone, Debug)]
pub struct RootTarget {
    pub raw_root: PathBuf,
    pub resolved_root: Option<PathBuf>,
    pub prefix: Option<PathBuf>,
    pub global_gitignore: Option<PathBuf>,
    pub initial_error: Option<WalkOsError>,
}

/// Pure-Rust traversal configuration mirroring `TraversalConfig`.
#[derive(Clone, Debug)]
pub struct WalkConfig {
    pub respect_gitignore: bool,
    pub custom_gitignore_file: Option<PathBuf>,
    pub include_hidden: bool,
    pub follow_symlinks: bool,
    pub dirs_only: bool,
    pub one_file_system: bool,
    pub max_depth: Option<usize>,
    pub file_limit: Option<usize>,
    pub prune_empty: bool,
    pub ignore_case: bool,
    pub match_dirs: bool,
    pub accumulate_size: bool,
    pub sort_by: WalkSortKey,
    pub reverse_sort: bool,
    pub dirs_first: bool,
    pub filter: FilterCriteria,
    pub matcher: PatternMatcher,
    pub home_dir: Option<PathBuf>,
    pub pathext_upper: Option<Vec<String>>,
    pub unicode_major: u8,
    pub mime_snapshot: MimeSnapshot,
}

/// OS error captured during GIL-free traversal for chronological `on_error` delivery.
#[derive(Clone, Debug)]
pub struct WalkOsError {
    pub raw_errno: Option<i32>,
    pub message: String,
    pub path: PathBuf,
}

impl WalkOsError {
    pub fn from_io(err: &io::Error, path: &Path) -> Self {
        Self {
            raw_errno: err.raw_os_error(),
            message: err.to_string(),
            path: path.to_path_buf(),
        }
    }
}

/// Classified item emitted by `NativeWalker` ready for `FileInfo` construction.
#[derive(Clone, Debug)]
pub struct WalkYieldItem {
    pub path: PathBuf,
    pub str_path: String,
    pub filename: String,
    pub root_path: PathBuf,
    pub prefix: Option<PathBuf>,
    pub has_entry: bool,
    pub follow_symlinks: bool,
    pub inherited_match: bool,
    pub classified: RawClassifiedFile,
}

/// Chronological event produced by `NativeWalker::next_batch`.
#[derive(Clone, Debug)]
pub enum WalkEvent {
    Error(WalkOsError),
    Item(Box<WalkYieldItem>),
}

/// Lightweight directory entry snapshot produced by `read_dir`.
#[derive(Clone, Debug)]
pub struct ScannedEntry {
    pub path: PathBuf,
    pub file_name: OsString,
    pub file_type: Option<fs::FileType>,
}

/// Convert `OsStr` into PEP 383 `surrogateescape` codepoints (`u32`) for exact Python `str` ordering.
pub fn surrogateescape_codepoints(name: &OsStr, ignore_case: bool) -> Vec<u32> {
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;
        let bytes = name.as_bytes();
        let mut out = Vec::with_capacity(bytes.len());
        for chunk in bytes.utf8_chunks() {
            if ignore_case {
                out.extend(chunk.valid().to_lowercase().chars().map(u32::from));
            } else {
                out.extend(chunk.valid().chars().map(u32::from));
            }
            for &bad in chunk.invalid() {
                out.push(0xDC00 + u32::from(bad));
            }
        }
        out
    }
    #[cfg(not(unix))]
    {
        let lossy = name.to_string_lossy();
        if ignore_case {
            lossy.to_lowercase().chars().map(u32::from).collect()
        } else {
            lossy.chars().map(u32::from).collect()
        }
    }
}
