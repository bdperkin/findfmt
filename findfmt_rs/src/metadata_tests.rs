//! Unit tests for `findfmt_rs::metadata` (#583, #590).

use std::env;
use std::fs;

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
    assert_eq!(format_filemode(S_IFDIR | S_ISGID | 0o765), "drwxrwSr-x");
    assert_eq!(format_filemode(S_IFDIR | S_ISVTX | 0o777), "drwxrwxrwt");
    assert_eq!(format_filemode(S_IFDIR | S_ISVTX | 0o776), "drwxrwxrwT");
    assert_eq!(format_filemode(S_IFBLK | 0o660), "brw-rw----");
    assert_eq!(format_filemode(S_IFCHR | 0o660), "crw-rw----");
    assert_eq!(format_filemode(S_IFDOOR | 0o644), "Drw-r--r--");
    assert_eq!(format_filemode(S_IFPORT | 0o644), "Prw-r--r--");
    assert_eq!(format_filemode(0o644), "?rw-r--r--");
}

#[test]
fn indicator_and_portable_metadata_cover_all_entry_kinds() -> Result<(), Box<dyn std::error::Error>>
{
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
    let sock_stat = RawStat {
        mode: S_IFSOCK | 0o600,
        ..fifo_stat.clone()
    };
    let door_stat = RawStat {
        mode: S_IFDOOR | 0o600,
        ..fifo_stat.clone()
    };
    assert_eq!(classification_indicator(true, false, true, None), Some("/"));
    assert_eq!(classification_indicator(false, true, true, None), Some("@"));
    assert_eq!(
        classification_indicator(false, false, false, Some(&fifo_stat)),
        Some("|")
    );
    assert_eq!(
        classification_indicator(false, false, false, Some(&sock_stat)),
        Some("=")
    );
    assert_eq!(
        classification_indicator(false, false, false, Some(&door_stat)),
        Some(">")
    );
    assert_eq!(
        classification_indicator(false, false, true, None),
        Some("*")
    );
    assert_eq!(classification_indicator(false, false, false, None), None);

    let tmp = env::temp_dir().join(format!("findfmt_rs_meta_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    fs::create_dir_all(&tmp)?;
    let reg = tmp.join("plain.txt");
    fs::write(&reg, b"abc")?;

    let dir_stat = RawStat::from_portable_metadata(&fs::metadata(&tmp)?);
    assert!(dir_stat.is_dir());
    let reg_stat = RawStat::from_portable_metadata(&fs::metadata(&reg)?);
    assert!(reg_stat.is_reg());

    let mut ro_perms = fs::metadata(&reg)?.permissions();
    ro_perms.set_readonly(true);
    fs::set_permissions(&reg, ro_perms)?;
    let ro_stat = RawStat::from_portable_metadata(&fs::metadata(&reg)?);
    assert_eq!(ro_stat.mode & 0o777, 0o444);

    #[cfg(unix)]
    {
        use std::os::unix::fs::symlink;
        let lnk = tmp.join("sym.txt");
        symlink(&reg, &lnk)?;
        let lnk_stat = RawStat::from_portable_metadata(&fs::symlink_metadata(&lnk)?);
        assert!(lnk_stat.is_lnk());

        let pipe = tmp.join("fifo.pipe");
        let status = std::process::Command::new("mkfifo").arg(&pipe).status()?;
        assert!(status.success());
        let pipe_stat = RawStat::from_portable_metadata(&fs::symlink_metadata(&pipe)?);
        assert_eq!(pipe_stat.mode & S_IFMT, S_IFCHR);
    }

    let _ = fs::remove_dir_all(&tmp);
    Ok(())
}
