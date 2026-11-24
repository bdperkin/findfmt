use std::fs;

use super::*;

#[test]
fn linked_worktree_commondir_ini_config_and_child_negation_behave_cleanly()
-> Result<(), Box<dyn std::error::Error>> {
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
        "[core]\n\texcludesFile = ~/glob.ign\n",
    )?;
    fs::write(common_git.join("info").join("exclude"), "*.excl\n")?;
    fs::write(private_wt.join("info").join("exclude"), "*.stale\n")?;
    fs::write(
        private_wt.join("commondir"),
        format!("{}\n", common_git.display()),
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
        None,
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
