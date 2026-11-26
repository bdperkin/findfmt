//! Unit tests for `findfmt_rs::classifier` and `classifier_helpers` (#583, #590).

use std::collections::BTreeSet;
use std::env;
use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

use super::*;

#[test]
fn classify_portable_pathext_batch_vanished_and_swapped_stat()
-> Result<(), Box<dyn std::error::Error>> {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    let dir = env::temp_dir().join(format!("findfmt_rs_clsp_{}_{nanos}", std::process::id()));
    fs::create_dir_all(&dir)?;

    let plain = dir.join("notes.rs");
    fs::write(&plain, b"fn main() {}\n")?;
    let exe_file = dir.join("tool.exe");
    fs::write(&exe_file, b"MZ\x00\x00")?;

    let reg = TagRegistry::sample_registry();
    let pathext = vec![".EXE".to_owned()];
    let inputs = vec![
        RawClassifyInput {
            path: plain.clone(),
            str_path: plain.to_string_lossy().into_owned(),
            filename: "notes.rs".into(),
            follow_symlinks: false,
            accumulated_size: None,
            pre_stat: None,
            pre_guessed_mime: None,
        },
        RawClassifyInput {
            path: exe_file.clone(),
            str_path: exe_file.to_string_lossy().into_owned(),
            filename: "tool.exe".into(),
            follow_symlinks: false,
            accumulated_size: None,
            pre_stat: Some((
                false,
                true,
                true,
                4,
                Some(RawStat::from_std_metadata(&fs::metadata(&exe_file)?)),
            )),
            pre_guessed_mime: None,
        },
    ];
    let rust_only = FilterCriteria {
        include_tags: BTreeSet::from(["rust".to_owned()]),
        exclude_tags: BTreeSet::new(),
        all_tags: false,
        shebang_filter: None,
    };
    let filtered = classify_batch_nogil(&inputs, Some(&rust_only), &reg, Some(&pathext));
    assert_eq!(filtered.len(), 1);
    let all = classify_batch_nogil(&inputs, None, &reg, Some(&pathext));
    assert_eq!(all.len(), 2);
    assert!(all[1].1.is_executable);

    assert!(identify_tags_without_buffer(&plain, "notes.rs", false, true, &reg).contains("rust"));
    assert!(
        identify_tags_without_buffer(&dir.join("missing.rs"), "missing.rs", true, true, &reg)
            .contains("rust")
    );
    assert!(identify_tags_without_buffer(&dir, "d", true, true, &reg).contains("directory"));

    let mut is_file = true;
    let mut sz = 0;
    let mut raw_st = None;
    assert_eq!(
        read_regular_header(&dir.join("vanished"), &mut is_file, &mut sz, &mut raw_st).len(),
        0
    );

    let stale_file_stat = RawStat {
        mode: 0o100_644,
        size: 999,
        uid: Some(0),
        gid: Some(0),
        ino: Some(42),
        dev: Some(7),
        mtime: Some(1.0),
        ctime: Some(1.0),
    };
    let swapped = classify_one_nogil(
        &RawClassifyInput {
            path: dir.clone(),
            str_path: dir.to_string_lossy().into_owned(),
            filename: "swapped_dir".into(),
            follow_symlinks: false,
            accumulated_size: None,
            pre_stat: Some((false, true, true, 999, Some(stale_file_stat))),
            pre_guessed_mime: None,
        },
        &reg,
        None,
    );
    assert!(swapped.is_dir);
    assert_eq!(swapped.indicator, Some("/"));

    let _ = fs::remove_dir_all(&dir);
    Ok(())
}

#[cfg(unix)]
#[test]
fn classify_unix_shebang_symlink_socket_and_fifo() -> Result<(), Box<dyn std::error::Error>> {
    use std::os::unix::fs::{PermissionsExt, symlink};
    use std::os::unix::net::UnixListener;

    let dir = env::temp_dir().join(format!("findfmt_rs_clsu_{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir)?;

    let script = dir.join("runner");
    fs::write(&script, b"#!/usr/bin/env -S python3 -u\nprint('ok')\n")?;
    fs::set_permissions(&script, fs::Permissions::from_mode(0o755))?;
    let plain = dir.join("notes.rs");
    fs::write(&plain, b"fn main() {}\n")?;
    let link = dir.join("link_rs");
    symlink(&plain, &link)?;

    let reg = TagRegistry::sample_registry();
    let res_script = classify_one_nogil(
        &RawClassifyInput {
            path: script.clone(),
            str_path: script.to_string_lossy().into_owned(),
            filename: "runner".into(),
            follow_symlinks: false,
            accumulated_size: None,
            pre_stat: None,
            pre_guessed_mime: None,
        },
        &reg,
        None,
    );
    assert!(res_script.tags.contains("python"));
    assert_eq!(res_script.indicator, Some("*"));

    let res_link = classify_one_nogil(
        &RawClassifyInput {
            path: link.clone(),
            str_path: link.to_string_lossy().into_owned(),
            filename: "link_rs".into(),
            follow_symlinks: true,
            accumulated_size: None,
            pre_stat: None,
            pre_guessed_mime: None,
        },
        &reg,
        None,
    );
    assert!(res_link.is_symlink());
    assert!(res_link.symlink_target().is_some());
    assert!(identify_tags_without_buffer(&link, "link_rs", true, true, &reg).contains("symlink"));

    let sock_path = env::temp_dir().join(format!("ff_s_{}.sock", std::process::id()));
    let _ = fs::remove_file(&sock_path);
    let _listener = UnixListener::bind(&sock_path)?;
    assert!(identify_tags_without_buffer(&sock_path, "s", true, true, &reg).contains("socket"));
    let _ = fs::remove_file(&sock_path);

    let fifo_path = dir.join("p.fifo");
    let st = std::process::Command::new("mkfifo")
        .arg(&fifo_path)
        .status()?;
    assert!(st.success());
    assert!(identify_tags_without_buffer(&fifo_path, "p.py", true, true, &reg).contains("python"));

    let _ = fs::remove_dir_all(&dir);
    Ok(())
}
