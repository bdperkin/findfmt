//! Unit tests for `findfmt_rs::classifier` (#583).

use std::collections::BTreeSet;
use std::env;
use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

use super::*;

#[cfg(unix)]
#[test]
fn classify_regular_shebang_symlink_and_batch_filter() -> Result<(), Box<dyn std::error::Error>> {
    use std::os::unix::fs::{PermissionsExt, symlink};

    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    let dir = env::temp_dir().join(format!("findfmt_rs_cls_{}_{nanos}", std::process::id()));
    fs::create_dir_all(&dir)?;

    let script = dir.join("runner");
    fs::write(&script, b"#!/usr/bin/env -S python3 -u\nprint('ok')\n")?;
    fs::set_permissions(&script, fs::Permissions::from_mode(0o755))?;

    let plain = dir.join("notes.rs");
    fs::write(&plain, b"fn main() {}\n")?;

    let link = dir.join("link_rs");
    symlink(&plain, &link)?;

    let reg = TagRegistry::builtin_for_tests();
    let inputs = vec![
        RawClassifyInput {
            path: script.clone(),
            str_path: script.to_string_lossy().into_owned(),
            filename: "runner".into(),
            follow_symlinks: false,
            accumulated_size: None,
            pre_stat: None,
            pre_guessed_mime: None,
        },
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
            path: link.clone(),
            str_path: link.to_string_lossy().into_owned(),
            filename: "link_rs".into(),
            follow_symlinks: true,
            accumulated_size: None,
            pre_stat: None,
            pre_guessed_mime: None,
        },
    ];

    let all = classify_batch_nogil(&inputs, None, &reg, None);
    assert_eq!(all.len(), 3);
    assert!(all[0].1.tags.contains("python"));
    assert_eq!(
        all[0].1.shebang.as_deref(),
        Some("#!/usr/bin/env -S python3 -u")
    );
    assert_eq!(all[0].1.indicator, Some("*"));
    assert!(all[2].1.is_symlink());
    assert!(all[2].1.tags.contains("rust"));

    let py_only = FilterCriteria {
        include_tags: BTreeSet::from(["python".to_owned()]),
        exclude_tags: BTreeSet::new(),
        all_tags: false,
        shebang_filter: Some("python3".into()),
    };
    let filtered = classify_batch_nogil(&inputs, Some(&py_only), &reg, None);
    assert_eq!(filtered.len(), 1);
    assert_eq!(filtered[0].0, 0);

    // Simulated regular-file pre_stat swapped for a directory before header open
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
    assert_ne!(swapped.inode, Some(42));

    let _ = fs::remove_dir_all(&dir);
    Ok(())
}
