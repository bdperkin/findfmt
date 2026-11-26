//! Header, shebang, symlink, and tag classification helpers for `classifier` (#583, #588).

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

use crate::classifier::RawClassifyInput;
use crate::header::{MAX_HEADER_BYTES, is_text_buffer, read_header_nonblocking};
use crate::metadata::RawStat;
use crate::shebang::{extract_shebang_from_buffer, parse_shebang_tokens};
use crate::tags::TagRegistry;

/// Symbolic link status and optional target path for a classified entry.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub enum SymlinkState {
    /// Entry is not a symbolic link.
    #[default]
    NotSymlink,
    /// Entry is a symbolic link with an optional `readlink` target path.
    Symlink(Option<PathBuf>),
}

impl SymlinkState {
    /// Return `true` when the entry is a symbolic link.
    #[must_use]
    pub const fn is_symlink(&self) -> bool {
        matches!(self, Self::Symlink(_))
    }

    /// Return the symbolic link target path when present.
    #[must_use]
    pub fn target(&self) -> Option<&Path> {
        match self {
            Self::NotSymlink => None,
            Self::Symlink(target) => target.as_deref(),
        }
    }
}

#[cfg(unix)]
pub(crate) fn inspect_unix_metadata(
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

pub(crate) fn check_executable(
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

pub(crate) fn identify_tags_from_buffer(
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

pub(crate) fn identify_tags_without_buffer(
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

pub(crate) fn read_regular_header(
    path: &Path,
    is_file: &mut bool,
    size_bytes: &mut u64,
    raw_stat: &mut Option<RawStat>,
) -> Vec<u8> {
    match read_header_nonblocking(path, MAX_HEADER_BYTES) {
        Some(hdr) => {
            if let Some(ref opened) = hdr.opened_meta
                && !opened.file_type().is_file()
            {
                *is_file = false;
                *size_bytes = opened.len();
                *raw_stat = Some(RawStat::from_std_metadata(opened));
            }
            hdr.buffer
        }
        None => Vec::new(),
    }
}

pub(crate) fn extract_shebang_info(
    buffer: &[u8],
    registry: &TagRegistry,
) -> (Option<String>, Vec<String>, BTreeSet<String>) {
    let Some(raw_sb) = extract_shebang_from_buffer(buffer) else {
        return (None, Vec::new(), BTreeSet::new());
    };
    let parts = parse_shebang_tokens(buffer);
    let mut sb_tags = BTreeSet::new();
    for part in &parts {
        sb_tags.extend(registry.tags_from_interpreter(part));
    }
    (Some(raw_sb), parts, sb_tags)
}

pub(crate) fn augment_symlink_and_mime_tags(
    tags: &mut BTreeSet<String>,
    input: &RawClassifyInput,
    symlink: &SymlinkState,
    is_executable: bool,
    has_pathext: bool,
    mime_type: Option<&str>,
    registry: &TagRegistry,
) {
    if symlink.is_symlink() {
        tags.insert("symlink".to_owned());
        tags.extend(registry.tags_from_filename(&input.filename));
        if input.follow_symlinks
            && let Some(target_name) = symlink.target().and_then(Path::file_name)
        {
            tags.extend(registry.tags_from_filename(&target_name.to_string_lossy()));
        }
    }
    if has_pathext {
        if is_executable {
            tags.remove("non-executable");
            tags.insert("executable".to_owned());
        } else {
            tags.remove("executable");
            tags.insert("non-executable".to_owned());
        }
    }
    if let Some(mt) = mime_type {
        tags.insert(format!("mime:{mt}"));
        let primary = mt.split('/').next().unwrap_or(mt);
        tags.insert(primary.to_owned());
    }
}
