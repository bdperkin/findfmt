use std::fs;

use super::*;

#[test]
fn linked_worktree_commondir_ini_config_and_child_negation_behave_cleanly() {
    let tmp = std::env::temp_dir().join(format!("findfmt_rs_ign_stack_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    let common_git = tmp.join("  main_repo_git");
    let private_wt = tmp.join("private_wt");
    let repo = tmp.join("worktree_repo");
    let sub = repo.join("sub");
    let fake_home = tmp.join("home");
    fs::create_dir_all(common_git.join("info")).expect("create common info");
    fs::create_dir_all(private_wt.join("info")).expect("create private info");
    fs::create_dir_all(&sub).expect("create sub");
    fs::create_dir_all(&fake_home).expect("create home");

    fs::write(fake_home.join("glob.ign"), "*.cfg_ign\n").expect("write glob.ign");
    fs::write(
        common_git.join("config"),
        "[core]\n\texcludesFile = ~/glob.ign\n",
    )
    .expect("write git config");
    fs::write(common_git.join("info").join("exclude"), "*.excl\n").expect("write exclude");
    fs::write(private_wt.join("info").join("exclude"), "*.stale\n")
        .expect("write stale private exclude");
    fs::write(
        private_wt.join("commondir"),
        format!("{}\n", common_git.display()),
    )
    .expect("write commondir");
    fs::write(repo.join(".git"), format!("gitdir: {}\n", private_wt.display()))
        .expect("write gitdir");
    fs::write(repo.join(".gitignore"), "*.log\n").expect("write root gitignore");
    fs::write(sub.join(".gitignore"), "!keep.log\n").expect("write sub gitignore");

    let canon_repo = fs::canonicalize(&repo)
        .map(|p| align_path_form(p, &repo))
        .unwrap_or(repo);
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

    assert!(is_path_ignored(&canon_repo.join("secret.excl"), false, &sub_specs));
    assert!(!is_path_ignored(&canon_repo.join("secret.stale"), false, &sub_specs));
    assert!(is_path_ignored(&canon_repo.join("item.cfg_ign"), false, &sub_specs));
    assert!(!is_path_ignored(&canon_repo.join("item.cfg_ign"), false, &no_glob));
    assert!(is_path_ignored(&canon_sub.join("drop.log"), false, &sub_specs));
    assert!(!is_path_ignored(&canon_sub.join("keep.log"), false, &sub_specs));

    let _ = fs::remove_dir_all(&tmp);
}
