//! POSIX mode formatting, classification indicators, and raw filesystem metadata (#583).

use std::fs::Metadata;
#[cfg(any(not(unix), test))]
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

/// Portable snapshot of `stat_result` fields required to populate `FileInfo`.
#[derive(Clone, Debug)]
pub struct RawStat {
    pub mode: u32,
    pub size: u64,
    pub uid: Option<u32>,
    pub gid: Option<u32>,
    pub ino: Option<u128>,
    pub dev: Option<u128>,
    pub mtime: Option<f64>,
    pub ctime: Option<f64>,
}

impl RawStat {
    /// Extract a `RawStat` from `std::fs::Metadata` on Unix platforms.
    #[cfg(unix)]
    pub fn from_std_metadata(meta: &Metadata) -> Self {
        use std::os::unix::fs::MetadataExt;

        let mtime = (meta.mtime() as f64) + 1e-9 * (meta.mtime_nsec() as f64);
        let ctime = (meta.ctime() as f64) + 1e-9 * (meta.ctime_nsec() as f64);
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
    pub fn from_std_metadata(meta: &Metadata) -> Self {
        Self::from_portable_metadata(meta)
    }

    /// Build a consistent `RawStat` snapshot from portable `std::fs::Metadata` fields.
    #[cfg(any(not(unix), test))]
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

    pub fn is_reg(&self) -> bool {
        (self.mode & S_IFMT) == S_IFREG
    }

    pub fn is_dir(&self) -> bool {
        (self.mode & S_IFMT) == S_IFDIR
    }

    pub fn is_lnk(&self) -> bool {
        (self.mode & S_IFMT) == S_IFLNK
    }

    pub fn is_sock(&self) -> bool {
        (self.mode & S_IFMT) == S_IFSOCK
    }

    pub fn is_fifo(&self) -> bool {
        (self.mode & S_IFMT) == S_IFIFO
    }

    pub fn is_door(&self) -> bool {
        (self.mode & S_IFMT) == S_IFDOOR
    }
}

/// Format POSIX mode bits into a 10-character `ls -l` permissions string (`stat.filemode` parity).
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn filemode_matches_python_stat_filemode() {
        assert_eq!(format_filemode(S_IFREG | 0o644), "-rw-r--r--");
        assert_eq!(format_filemode(S_IFREG | 0o755), "-rwxr-xr-x");
        assert_eq!(format_filemode(S_IFDIR | 0o755), "drwxr-xr-x");
        assert_eq!(format_filemode(S_IFLNK | 0o777), "lrwxrwxrwx");
        assert_eq!(format_filemode(S_IFIFO | 0o640), "prw-r-----");
        assert_eq!(format_filemode(S_IFSOCK | 0o660), "srw-rw----");
        assert_eq!(format_filemode(S_IFREG | S_ISUID | 0o755), "-rwsr-xr-x");
        assert_eq!(format_filemode(S_IFREG | S_ISUID | 0o644), "-rwSr--r--");
        assert_eq!(format_filemode(S_IFDIR | S_ISGID | 0o775), "drwxrwsr-x");
        assert_eq!(format_filemode(S_IFDIR | S_ISVTX | 0o777), "drwxrwxrwt");
        assert_eq!(format_filemode(S_IFDIR | S_ISVTX | 0o776), "drwxrwxrwT");
    }

    #[test]
    fn indicator_matches_posix_symbols() {
        let fifo_stat = RawStat {
            mode: S_IFIFO | 0o644,
            size: 0,
            uid: None,
            gid: None,
            ino: None,
            dev: None,
            mtime: None,
            ctime: None,
        };
        assert_eq!(classification_indicator(true, false, true, None), Some("/"));
        assert_eq!(classification_indicator(false, true, true, None), Some("@"));
        assert_eq!(
            classification_indicator(false, false, false, Some(&fifo_stat)),
            Some("|")
        );
        assert_eq!(
            classification_indicator(false, false, true, None),
            Some("*")
        );
        assert_eq!(classification_indicator(false, false, false, None), None);

        let cur_dir_meta = std::fs::metadata(".").expect("current dir metadata");
        let portable_dir = RawStat::from_portable_metadata(&cur_dir_meta);
        assert!(portable_dir.is_dir());
        assert!(!portable_dir.is_reg());
    }
}
