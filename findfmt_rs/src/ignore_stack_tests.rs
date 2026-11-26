//! Unit tests for `findfmt_rs::ignore_stack` (#582, #590).

use std::fs;
use std::sync::Mutex;

use super::*;

static ENV_LOCK: Mutex<()> = Mutex::new(());

#[test]
fn linked_worktree_commondir_ini_config_and_child_negation_behave_cleanly()
-> Result<(), Box<dyn std::error::Error>> {
    let _guard = ENV_LOCK.lock().map_err(|_| "poisoned")?;
    let tmp = std::env::temp_dir().join(format!("findfmt_rs_ign_stack_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    let common_git = tmp.join("  main_repo_git");
    let private_wt = tmp.join("private_wt");
    let repo = tmp.join("worktree_repo");
    let sub = repo.join("sub");
    let fake_home = tmp.join("home");
    fs::create_dir_all(common_git.join("info"))?;
    fs::create_dir_all(private_wt.join("info"))?;
    fs::create_dir_all(&sub)?;
    fs::create_dir_all(&fake_home)?;

    fs::write(fake_home.join("glob.ign"), "*.cfg_ign\n")?;
    fs::write(
        common_git.join("config"),
        "# header\n; comment\n[other]\nkey = 1\n[core]\n\texcludesFile = \"~/glob.ign\"\n",
    )?;
    fs::write(common_git.join("info").join("exclude"), "*.excl\n")?;
    fs::write(private_wt.join("info").join("exclude"), "*.stale\n")?;
    fs::write(
        private_wt.join("commondir"),
        format!("{}\r\n", common_git.display()),
    )?;
    fs::write(
        repo.join(".git"),
        format!("gitdir: {}\n", private_wt.display()),
    )?;
    fs::write(repo.join(".gitignore"), "*.log\n")?;
    fs::write(sub.join(".gitignore"), "!keep.log\n")?;

    let canon_repo = fs::canonicalize(&repo).map_or(repo, |p| align_path_form(p, &tmp));
    let canon_sub = canon_repo.join("sub");
    let root_specs = resolve_root_specs(
        &canon_repo,
        true,
        Some(Path::new("~/glob.ign")),
        Some(&fake_home),
        &GlobalIgnoreResolution::Unresolved,
    );
    let no_glob = resolve_root_specs(
        &canon_repo,
        true,
        None,
        Some(&fake_home),
        &GlobalIgnoreResolution::ResolvedNone,
    );
    let sub_specs = load_child_specs(&canon_sub, &root_specs, true);

    assert!(is_path_ignored(
        &canon_repo.join("secret.excl"),
        false,
        &sub_specs
    ));
    assert!(!is_path_ignored(
        &canon_repo.join("secret.stale"),
        false,
        &sub_specs
    ));
    assert!(is_path_ignored(
        &canon_repo.join("item.cfg_ign"),
        false,
        &sub_specs
    ));
    assert!(!is_path_ignored(
        &canon_repo.join("item.cfg_ign"),
        false,
        &no_glob
    ));
    assert!(is_path_ignored(
        &canon_sub.join("drop.log"),
        false,
        &sub_specs
    ));
    assert!(!is_path_ignored(
        &canon_sub.join("keep.log"),
        false,
        &sub_specs
    ));

    let _ = fs::remove_dir_all(&tmp);
    Ok(())
}

#[test]
fn global_fallbacks_tilde_empty_commondir_and_nested_git_exclude()
-> Result<(), Box<dyn std::error::Error>> {
    let _guard = ENV_LOCK.lock().map_err(|_| "poisoned")?;
    let tmp = std::env::temp_dir().join(format!("findfmt_rs_ign_fb_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    let base = tmp.join("plain_dir");
    let home = tmp.join("home");
    fs::create_dir_all(&base)?;
    fs::create_dir_all(home.join(".config").join("git"))?;

    assert_eq!(expand_tilde("~", Some(&home)), home);
    assert_eq!(expand_tilde("rel.ign", None), PathBuf::from("rel.ign"));
    assert_eq!(
        crate::metadata::normalize_windows_verbatim(r"\\?\C:\repo", r"C:\repo"),
        Some(PathBuf::from(r"C:\repo"))
    );
    assert_eq!(
        crate::metadata::normalize_windows_verbatim(r"\\?\UNC\srv\share", r"\\srv\share"),
        Some(PathBuf::from(r"\\srv\share"))
    );
    assert_eq!(
        crate::metadata::normalize_windows_verbatim(r"\\?\C:\repo", r"\\?\C:\repo"),
        None
    );
    assert_eq!(
        crate::metadata::normalize_windows_verbatim(r"C:\repo", r"C:\repo"),
        None
    );

    let empty_cd_git = tmp.join("empty_cd_git");
    fs::create_dir_all(&empty_cd_git)?;
    fs::write(empty_cd_git.join("commondir"), "\r\n")?;
    assert_eq!(resolve_common_git_dir(&empty_cd_git), empty_cd_git);

    fs::write(base.join("rel.ign"), "*.rel\n")?;
    fs::write(home.join(".gitconfig"), "[core]\nexcludesfile = rel.ign\n")?;
    let prev_xdg = std::env::var_os("XDG_CONFIG_HOME");
    assert_eq!(
        find_global_gitignore_path(&base, Some(&home)),
        Some(base.join("rel.ign"))
    );

    fs::remove_file(home.join(".gitconfig"))?;
    fs::write(
        home.join(".config").join("git").join("config"),
        "[core]\nexcludesfile =\n",
    )?;
    assert!(find_git_config_excludes_with_xdg(&base, Some(&home), None).is_none());
    fs::write(home.join(".config").join("git").join("ignore"), "*.std\n")?;
    assert_eq!(
        find_standard_global_gitignore(Some(&home)),
        Some(home.join(".config").join("git").join("ignore"))
    );

    let xdg_dir = tmp.join("xdg");
    fs::create_dir_all(xdg_dir.join("git"))?;
    fs::write(xdg_dir.join("git").join("ignore"), "*.xdg\n")?;
    assert_eq!(
        find_standard_global_gitignore_with_xdg(Some(xdg_dir.as_os_str()), Some(&home)),
        Some(xdg_dir.join("git").join("ignore"))
    );
    fs::write(
        xdg_dir.join("git").join("config"),
        "[core]\nexcludesfile = rel.ign\n",
    )?;
    assert_eq!(
        find_git_config_excludes_with_xdg(&base, Some(&home), Some(xdg_dir.as_os_str())),
        Some(base.join("rel.ign"))
    );
    let _ = prev_xdg;

    let nested = base.join("subrepo");
    fs::create_dir_all(nested.join(".git").join("info"))?;
    fs::write(nested.join(".git").join("config"), "[user]\nname = x\n")?;
    fs::write(nested.join(".git").join("info").join("exclude"), "*.nex\n")?;
    fs::write(nested.join(".gitignore"), "*.ngi\n")?;
    assert!(find_git_config_excludes_with_xdg(&nested, None, None).is_none());

    let empty_arc: Arc<[GitignoreMatcher]> = Arc::from([]);
    let loaded = load_child_specs(&nested, &empty_arc, true);
    assert_eq!(loaded.len(), 2);
    fs::remove_file(nested.join(".gitignore"))?;
    let excl_only = load_child_specs(&nested, &empty_arc, true);
    assert_eq!(excl_only.len(), 1);

    #[cfg(unix)]
    {
        use std::ffi::OsStr;
        use std::os::unix::ffi::OsStrExt;
        let non_utf8 = Path::new(OsStr::from_bytes(b"/nonexistent_\xff.ign"));
        let specs = resolve_root_specs(
            &base,
            false,
            Some(non_utf8),
            None,
            &GlobalIgnoreResolution::ResolvedNone,
        );
        assert!(specs.is_empty());
    }

    let _ = fs::remove_dir_all(&tmp);
    Ok(())
}
