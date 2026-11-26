//! Unit tests for `findfmt_rs::walker_filter` (#582, #590).

use std::env;
use std::ffi::OsString;
use std::fs;
use std::path::Path;

use super::*;
use crate::metadata::{has_windows_exec_suffix, parse_pathext_upper};

#[test]
fn windows_exec_suffix_and_pathext_parsing() {
    assert!(has_windows_exec_suffix(".exe"));
    assert!(has_windows_exec_suffix(".CMD"));
    assert!(has_windows_exec_suffix("tool.EXE"));
    assert!(has_windows_exec_suffix("é.bat"));
    assert!(has_windows_exec_suffix("legacy.CoM"));
    assert!(!has_windows_exec_suffix("exe"));
    assert!(!has_windows_exec_suffix("script.py"));

    assert_eq!(
        parse_pathext_upper(" .com ; exe ;; .Py "),
        vec![".COM", ".EXE", ".PY"]
    );
}

#[test]
fn filter_helpers_cover_missing_dirs_relative_fallbacks_and_untyped_entries()
-> Result<(), Box<dyn std::error::Error>> {
    let tmp = env::temp_dir().join(format!("findfmt_rs_wf_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    fs::create_dir_all(&tmp)?;
    let reg_file = tmp.join("a.py");
    fs::write(&reg_file, b"x = 1\n")?;

    assert!(is_valid_descent_dir(&tmp.join("vanished_dir"), false));
    assert!(!is_valid_descent_dir(&reg_file, false));
    assert_eq!(
        resolve_relative_pathbuf(Path::new("/outside/a.py"), Path::new("/root"), None),
        Path::new("/outside/a.py")
    );
    assert_eq!(
        resolve_relative_pathbuf(&tmp, &tmp, Some(Path::new("pfx"))),
        Path::new("pfx/.")
    );
    assert!(check_entry_device(&reg_file, false, false, None));

    let cfg = WalkConfig {
        respect_gitignore: false,
        custom_gitignore_file: None,
        scope: crate::walker_types::WalkScope {
            include_hidden: true,
            follow_symlinks: false,
            dirs_only: false,
        },
        bounds: crate::walker_types::WalkBounds {
            one_file_system: false,
            prune_empty: false,
            accumulate_size: false,
            max_depth: None,
            file_limit: None,
        },
        sort: crate::walker_types::WalkSort {
            sort_by: crate::walker_types::WalkSortKey::Name,
            reverse_sort: false,
            dirs_first: false,
            ignore_case: false,
        },
        filter: crate::tags::FilterCriteria::default(),
        matcher: crate::patterns::PatternMatcher::default(),
        home_dir: None,
        pathext_upper: None,
        unicode_major: 16,
        mime_snapshot: crate::walker_types::MimeSnapshot::default(),
    };

    let untyped_file = ScannedEntry {
        path: reg_file.clone(),
        file_name: OsString::from("a.py"),
        file_type: None,
    };
    let filtered = filter_entry_nogil(&untyped_file, &cfg, &[], None, &tmp);
    assert!(filtered.is_some_and(|(_, is_dir, is_file, is_sym)| !is_dir && is_file && !is_sym));

    assert!(resolve_device_id(&reg_file, false, false).is_some());
    assert!(resolve_device_id(&reg_file, true, false).is_some());
    assert!(executable_hint_for_skip(&tmp, "dir", false, false).is_some());
    assert!(executable_hint_for_skip(&reg_file, "a.exe", false, true).is_some());
    assert!(executable_hint_for_skip(&reg_file, "a.py", true, false).is_some());
    let missing_in = build_raw_classify_input(tmp.join("missing.py"), false, None, &cfg);
    assert_eq!(missing_in.filename, "missing.py");

    #[cfg(windows)]
    {
        let broken = tmp.join("broken_win.py");
        if std::os::windows::fs::symlink_file(tmp.join("no_target.py"), &broken).is_ok() {
            let broken_in = build_raw_classify_input(broken, true, None, &cfg);
            assert!(broken_in.pre_stat.is_some_and(|s| s.0 && !s.1));
        }
    }

    #[cfg(unix)]
    {
        use std::os::unix::fs::symlink;
        let sym = tmp.join("sym.py");
        symlink(&reg_file, &sym)?;
        assert!(resolve_device_id(&sym, true, false).is_some());
        let untyped_sym = ScannedEntry {
            path: sym,
            file_name: OsString::from("sym.py"),
            file_type: None,
        };
        let sym_res = filter_entry_nogil(&untyped_sym, &cfg, &[], None, &tmp);
        assert!(sym_res.is_some_and(|(_, _, _, is_sym)| is_sym));
    }

    let _ = fs::remove_dir_all(&tmp);
    Ok(())
}
