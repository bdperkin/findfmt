//! POSIX mode formatting, classification indicators, and raw filesystem metadata (#583).

use std::fs::Metadata;
use std::time::{SystemTime, UNIX_EPOCH};

const S_IFMT: u32 = 0o170_000;
const S_IFSOCK: u32 = 0o140_000;
const S_IFLNK: u32 = 0o120_000;
const S_IFREG: u32 = 0o100_000;
const S_IFBLK: u32 = 0o060_000;
const S_IFDIR: u32 = 0o040_000;
const S_IFCHR: u32 = 0o020_000;
const S_IFIFO: u32 = 0o010_000;
const S_IFDOOR: u32 = 0o150_000;
const S_IFPORT: u32 = 0o160_000;

const S_ISUID: u32 = 0o004_000;
const S_ISGID: u32 = 0o002_000;
const S_ISVTX: u32 = 0o001_000;

#[cfg(unix)]
fn unix_timespec_to_f64(secs: i64, nsecs: i64) -> f64 {
    let sec_hi = i32::try_from(secs >> 32).unwrap_or(0);
    let sec_lo = u32::try_from(secs & 0xFFFF_FFFF).unwrap_or(0);
    let nsec_hi = i32::try_from(nsecs >> 32).unwrap_or(0);
    let nsec_lo = u32::try_from(nsecs & 0xFFFF_FFFF).unwrap_or(0);
    let sec_f = f64::from(sec_hi) * 4_294_967_296.0 + f64::from(sec_lo);
    let nsec_f = f64::from(nsec_hi) * 4_294_967_296.0 + f64::from(nsec_lo);
    sec_f + 1e-9 * nsec_f
}

/// Portable snapshot of `stat_result` fields required to populate `FileInfo`.
#[derive(Clone, Debug)]
pub struct RawStat {
    /// Raw POSIX file mode (`st_mode`).
    pub mode: u32,
    /// File size in bytes (`st_size`).
    pub size: u64,
    /// Numeric owner user ID (`st_uid`).
    pub uid: Option<u32>,
    /// Numeric owner group ID (`st_gid`).
    pub gid: Option<u32>,
    /// Filesystem inode identifier (`st_ino`).
    pub ino: Option<u128>,
    /// Filesystem device identifier (`st_dev`).
    pub dev: Option<u128>,
    /// Last modification timestamp in seconds since the Unix epoch.
    pub mtime: Option<f64>,
    /// Metadata change / creation timestamp in seconds since the Unix epoch.
    pub ctime: Option<f64>,
}

impl RawStat {
    /// Extract a `RawStat` from `std::fs::Metadata` on Unix platforms.
    #[cfg(unix)]
    #[must_use]
    pub fn from_std_metadata(meta: &Metadata) -> Self {
        use std::os::unix::fs::MetadataExt;

        let mtime = unix_timespec_to_f64(meta.mtime(), meta.mtime_nsec());
        let ctime = unix_timespec_to_f64(meta.ctime(), meta.ctime_nsec());
        Self {
            mode: meta.mode(),
            size: meta.len(),
            uid: Some(meta.uid()),
            gid: Some(meta.gid()),
            ino: Some(u128::from(meta.ino())),
            dev: Some(u128::from(meta.dev())),
            mtime: Some(mtime),
            ctime: Some(ctime),
        }
    }

    /// Extract a `RawStat` from `std::fs::Metadata` on non-Unix platforms (e.g., Windows).
    #[cfg(not(unix))]
    #[must_use]
    pub fn from_std_metadata(meta: &Metadata) -> Self {
        Self::from_portable_metadata(meta)
    }

    /// Build a consistent `RawStat` snapshot from portable `std::fs::Metadata` fields.
    #[must_use]
    pub fn from_portable_metadata(meta: &Metadata) -> Self {
        let readonly = meta.permissions().readonly();
        let mode = if meta.is_dir() {
            S_IFDIR | if readonly { 0o555 } else { 0o777 }
        } else if meta.file_type().is_symlink() {
            S_IFLNK | 0o777
        } else if meta.is_file() {
            S_IFREG | if readonly { 0o444 } else { 0o666 }
        } else {
            S_IFCHR | if readonly { 0o444 } else { 0o666 }
        };
        let to_epoch = |res: std::io::Result<SystemTime>| -> Option<f64> {
            res.ok()
                .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map(|d| d.as_secs_f64())
        };
        let mtime = to_epoch(meta.modified());
        let ctime = to_epoch(meta.created()).or(mtime);
        Self {
            mode,
            size: meta.len(),
            uid: Some(0),
            gid: Some(0),
            ino: Some(0),
            dev: Some(0),
            mtime,
            ctime,
        }
    }

    /// Return `true` when `mode` denotes a regular file (`S_IFREG`).
    #[must_use]
    pub const fn is_reg(&self) -> bool {
        (self.mode & S_IFMT) == S_IFREG
    }

    /// Return `true` when `mode` denotes a directory (`S_IFDIR`).
    #[must_use]
    pub const fn is_dir(&self) -> bool {
        (self.mode & S_IFMT) == S_IFDIR
    }

    /// Return `true` when `mode` denotes a symbolic link (`S_IFLNK`).
    #[must_use]
    pub const fn is_lnk(&self) -> bool {
        (self.mode & S_IFMT) == S_IFLNK
    }

    /// Return `true` when `mode` denotes a Unix domain socket (`S_IFSOCK`).
    #[must_use]
    pub const fn is_sock(&self) -> bool {
        (self.mode & S_IFMT) == S_IFSOCK
    }

    /// Return `true` when `mode` denotes a named pipe / FIFO (`S_IFIFO`).
    #[must_use]
    pub const fn is_fifo(&self) -> bool {
        (self.mode & S_IFMT) == S_IFIFO
    }

    /// Return `true` when `mode` denotes a Solaris door (`S_IFDOOR`).
    #[must_use]
    pub const fn is_door(&self) -> bool {
        (self.mode & S_IFMT) == S_IFDOOR
    }
}

/// Format POSIX mode bits into a 10-character `ls -l` permissions string (`stat.filemode` parity).
#[must_use]
pub fn format_filemode(mode: u32) -> String {
    let file_type = match mode & S_IFMT {
        S_IFDIR => 'd',
        S_IFCHR => 'c',
        S_IFBLK => 'b',
        S_IFREG => '-',
        S_IFIFO => 'p',
        S_IFLNK => 'l',
        S_IFSOCK => 's',
        S_IFDOOR => 'D',
        S_IFPORT => 'P',
        _ => '?',
    };

    let usr_r = if (mode & 0o400) != 0 { 'r' } else { '-' };
    let usr_w = if (mode & 0o200) != 0 { 'w' } else { '-' };
    let usr_x = match ((mode & 0o100) != 0, (mode & S_ISUID) != 0) {
        (true, true) => 's',
        (false, true) => 'S',
        (true, false) => 'x',
        (false, false) => '-',
    };

    let grp_r = if (mode & 0o040) != 0 { 'r' } else { '-' };
    let grp_w = if (mode & 0o020) != 0 { 'w' } else { '-' };
    let grp_x = match ((mode & 0o010) != 0, (mode & S_ISGID) != 0) {
        (true, true) => 's',
        (false, true) => 'S',
        (true, false) => 'x',
        (false, false) => '-',
    };

    let oth_r = if (mode & 0o004) != 0 { 'r' } else { '-' };
    let oth_w = if (mode & 0o002) != 0 { 'w' } else { '-' };
    let oth_x = match ((mode & 0o001) != 0, (mode & S_ISVTX) != 0) {
        (true, true) => 't',
        (false, true) => 'T',
        (true, false) => 'x',
        (false, false) => '-',
    };

    [
        file_type, usr_r, usr_w, usr_x, grp_r, grp_w, grp_x, oth_r, oth_w, oth_x,
    ]
    .iter()
    .collect()
}

/// Compute the POSIX classification indicator (`get_classification_indicator` parity).
#[must_use]
pub fn classification_indicator(
    is_dir: bool,
    is_symlink: bool,
    is_executable: bool,
    stat: Option<&RawStat>,
) -> Option<&'static str> {
    if is_dir {
        return Some("/");
    }
    if is_symlink {
        return Some("@");
    }
    if let Some(st) = stat {
        if st.is_sock() {
            return Some("=");
        }
        if st.is_fifo() {
            return Some("|");
        }
        if st.is_door() {
            return Some(">");
        }
    }
    if is_executable && !is_dir {
        Some("*")
    } else {
        None
    }
}

/// Return `true` when `filename` ends with an ASCII case-insensitive Windows executable suffix.
#[must_use]
pub fn has_windows_exec_suffix(filename: &str) -> bool {
    const WIN_EXEC_SUFFIXES: [&[u8]; 4] = [b".exe", b".bat", b".cmd", b".com"];
    let bytes = filename.as_bytes();
    bytes.len() >= 4
        && WIN_EXEC_SUFFIXES
            .iter()
            .any(|sfx| bytes[bytes.len() - 4..].eq_ignore_ascii_case(sfx))
}

/// Normalize a `;`-delimited Windows `PATHEXT` string into uppercase dot-prefixed extensions.
#[must_use]
pub fn parse_pathext_upper(raw: &str) -> Vec<String> {
    raw.split(';')
        .map(str::trim)
        .filter(|e| !e.is_empty())
        .map(|e| {
            let up = e.to_uppercase();
            if up.starts_with('.') {
                up
            } else {
                format!(".{up}")
            }
        })
        .collect()
}

/// Strip Windows `\\?\` or `\\?\UNC\` verbatim prefixes when `ref_lossy` is non-verbatim.
#[must_use]
pub fn normalize_windows_verbatim(cand_lossy: &str, ref_lossy: &str) -> Option<std::path::PathBuf> {
    if ref_lossy.starts_with(r"\\?\") {
        return None;
    }
    if let Some(unc_tail) = cand_lossy.strip_prefix(r"\\?\UNC\") {
        return Some(std::path::PathBuf::from(format!(r"\\{unc_tail}")));
    }
    cand_lossy
        .strip_prefix(r"\\?\")
        .map(std::path::PathBuf::from)
}

#[cfg(test)]
#[path = "metadata_tests.rs"]
mod tests;
