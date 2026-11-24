//! GIL-free file classification engine mirroring `src/findfmt/classifier.py` (#583).

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

pub use crate::classifier_helpers::SymlinkState;
#[cfg(unix)]
use crate::classifier_helpers::inspect_unix_metadata;
use crate::classifier_helpers::{
    augment_symlink_and_mime_tags, check_executable, extract_shebang_info,
    identify_tags_from_buffer, identify_tags_without_buffer, read_regular_header,
};
use crate::metadata::{RawStat, classification_indicator, format_filemode};
use crate::tags::{FilterCriteria, TagRegistry};

/// Pure-Rust input descriptor for classifying a single path without holding the Python GIL.
#[derive(Clone, Debug)]
pub struct RawClassifyInput {
    /// Filesystem path to inspect.
    pub path: PathBuf,
    /// String form of `path` (`str(path)`) for filename and MIME evaluation.
    pub str_path: String,
    /// Basename of `path` (`path.name`) with `surrogateescape` preserved.
    pub filename: String,
    /// Whether symbolic links should be dereferenced during metadata and header inspection.
    pub follow_symlinks: bool,
    /// Optional pre-accumulated `--du` directory or file byte size.
    pub accumulated_size: Option<u64>,
    /// Pre-fetched `RawStat` on platforms where stat metadata comes from OS handle/Python.
    pub pre_stat: Option<(bool, bool, bool, u64, Option<RawStat>)>,
    /// Optional MIME type resolved from Python's live `mimetypes._db` before releasing the GIL.
    pub pre_guessed_mime: Option<Option<String>>,
}

/// Pure-Rust classification result produced inside `py.detach(...)` before building `FileInfo`.
#[derive(Clone, Debug)]
pub struct RawClassifiedFile {
    /// Whether the target path exists on disk (or as an unfollowed symlink).
    pub exists: bool,
    /// Whether the effective metadata denotes a directory.
    pub is_dir: bool,
    /// Symbolic link status and optional link target path.
    pub symlink: SymlinkState,
    /// Whether the entry has executable permissions (or `PATHEXT` / shebang on Windows).
    pub is_executable: bool,
    /// Effective byte size reported for `FileInfo.size_bytes`.
    pub size_bytes: u64,
    /// Optional pre-accumulated `--du` directory size.
    pub accumulated_size: Option<u64>,
    /// Ordered set of `identify` and MIME tags.
    pub tags: BTreeSet<String>,
    /// Extracted `#!` header line when present on a regular file.
    pub shebang: Option<String>,
    /// Guessed MIME type (`type/subtype`), if any.
    pub mime_type: Option<String>,
    /// Formatted 10-character POSIX mode string (`-rwxr-xr-x`).
    pub permissions_str: Option<String>,
    /// Numeric owner user ID (`st_uid`).
    pub uid: Option<u32>,
    /// Numeric owner group ID (`st_gid`).
    pub gid: Option<u32>,
    /// Filesystem inode identifier (`st_ino`).
    pub inode: Option<u128>,
    /// Filesystem device identifier (`st_dev`).
    pub device: Option<u128>,
    /// Last modification timestamp in seconds since the Unix epoch.
    pub mtime: Option<f64>,
    /// Metadata change / creation timestamp in seconds since the Unix epoch.
    pub ctime: Option<f64>,
    /// Optional `ls -F` classification indicator (`"/"`, `"@"`, `"*"`, `"|"`, `"="`, `">"`).
    pub indicator: Option<&'static str>,
}

impl RawClassifiedFile {
    /// Return `true` when the classified entry is a symbolic link.
    #[must_use]
    pub const fn is_symlink(&self) -> bool {
        self.symlink.is_symlink()
    }

    /// Return the symbolic link target path when present.
    #[must_use]
    pub fn symlink_target(&self) -> Option<&Path> {
        self.symlink.target()
    }
}

/// Classify a single `RawClassifyInput` without holding the Python GIL.
#[must_use]
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

    let symlink = if is_symlink {
        SymlinkState::Symlink(fs::read_link(&input.path).ok())
    } else {
        SymlinkState::NotSymlink
    };

    let follow_target = !is_symlink || input.follow_symlinks;
    let buffer = (exists && is_file && follow_target)
        .then(|| read_regular_header(&input.path, &mut is_file, &mut size_bytes, &mut raw_stat));

    let (shebang, parsed_shebang, shebang_tags) = match buffer.as_deref() {
        Some(buf) if is_file && follow_target => extract_shebang_info(buf, registry),
        _ => (None, Vec::new(), BTreeSet::new()),
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
            identify_tags_from_buffer(
                &input.filename,
                buf,
                is_executable,
                &parsed_shebang,
                registry,
            )
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

    let mime_type = match input.pre_guessed_mime {
        Some(ref pre) => pre.clone(),
        None => registry.guess_mime_type(&input.str_path),
    };
    augment_symlink_and_mime_tags(
        &mut tags,
        input,
        &symlink,
        is_executable,
        pathext_upper.is_some(),
        mime_type.as_deref(),
        registry,
    );

    let is_dir = raw_stat.as_ref().is_some_and(RawStat::is_dir);
    let indicator = classification_indicator(is_dir, is_symlink, is_executable, raw_stat.as_ref());
    let permissions_str = raw_stat.as_ref().map(|st| format_filemode(st.mode));

    RawClassifiedFile {
        exists,
        is_dir,
        symlink,
        is_executable,
        size_bytes: input.accumulated_size.unwrap_or(size_bytes),
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
#[must_use]
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
