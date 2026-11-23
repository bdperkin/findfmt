//! Hierarchical `.gitignore`, `.git/info/exclude`, and global ignore evaluation (#582).

use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

use crate::gitignore::GitignoreMatcher;
use crate::shebang::py_strip;

const GIT_CONFIG_TIMEOUT: Duration = Duration::from_secs(2);
const GIT_POLL_INTERVAL: Duration = Duration::from_millis(5);

/// Locate the nearest enclosing Git repository root containing a `.git` directory or pointer file.
pub fn find_git_repo_root(start_dir: &Path) -> Option<PathBuf> {
    let resolved = fs::canonicalize(start_dir).unwrap_or_else(|_| start_dir.to_path_buf());
    for directory in resolved.ancestors() {
        if directory.join(".git").exists() {
            return Some(directory.to_path_buf());
        }
    }
    None
}

fn collect_ancestor_dirs(resolved: &Path, git_root: Option<&Path>) -> Vec<PathBuf> {
    let Some(repo_root) = git_root else {
        return vec![resolved.to_path_buf()];
    };
    if resolved == repo_root {
        return vec![resolved.to_path_buf()];
    }
    let mut ancestors = Vec::new();
    for dir in resolved.ancestors() {
        ancestors.push(dir.to_path_buf());
        if dir == repo_root {
            break;
        }
    }
    ancestors.reverse();
    ancestors
}

fn expand_tilde(raw: &str, home_dir: Option<&Path>) -> PathBuf {
    if let Some(home) = home_dir {
        if raw == "~" {
            return home.to_path_buf();
        }
        if let Some(rest) = raw.strip_prefix("~/").or_else(|| raw.strip_prefix("~\\")) {
            return home.join(rest);
        }
    }
    PathBuf::from(raw)
}

fn run_git_config_with_timeout(git_bin: &Path, base_dir: &Path, timeout: Duration) -> Option<Vec<u8>> {
    let mut child = Command::new(git_bin)
        .arg("-C")
        .arg(base_dir)
        .args(["config", "--get", "core.excludesFile"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;

    let deadline = Instant::now() + timeout;
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                if !status.success() {
                    return None;
                }
                let mut stdout_buf = Vec::new();
                if let Some(mut out) = child.stdout.take() {
                    let _ = out.read_to_end(&mut stdout_buf);
                }
                return Some(stdout_buf);
            }
            Ok(None) => {
                if Instant::now() >= deadline {
                    let _ = child.kill();
                    let _ = child.wait();
                    return None;
                }
                thread::sleep(GIT_POLL_INTERVAL);
            }
            Err(_) => {
                let _ = child.kill();
                let _ = child.wait();
                return None;
            }
        }
    }
}

fn find_git_config_excludes_file(base_dir: &Path, home_dir: Option<&Path>) -> Option<PathBuf> {
    let stdout_bytes = run_git_config_with_timeout(Path::new("git"), base_dir, GIT_CONFIG_TIMEOUT)?;
    let stdout = String::from_utf8_lossy(&stdout_bytes);
    let trimmed = py_strip(&stdout);
    if trimmed.is_empty() {
        return None;
    }
    let mut configured = expand_tilde(trimmed, home_dir);
    if !configured.is_absolute() {
        configured = base_dir.join(configured);
    }
    configured.is_file().then_some(configured)
}

fn find_standard_global_gitignore(home_dir: Option<&Path>) -> Option<PathBuf> {
    if let Some(xdg_os) = std::env::var_os("XDG_CONFIG_HOME").filter(|v| !v.is_empty()) {
        let xdg_path = PathBuf::from(xdg_os).join("git").join("ignore");
        return xdg_path.is_file().then_some(xdg_path);
    }
    let home = home_dir?;
    let fallback = home.join(".config").join("git").join("ignore");
    fallback.is_file().then_some(fallback)
}

/// Resolve the user's global gitignore path mirroring `ignore.py:find_global_gitignore_path` (#323).
pub fn find_global_gitignore_path(base_dir: &Path, home_dir: Option<&Path>) -> Option<PathBuf> {
    find_git_config_excludes_file(base_dir, home_dir)
        .or_else(|| find_standard_global_gitignore(home_dir))
}

/// Resolve the effective Git common directory for a resolved `gitdir` (linked worktree `commondir`).
fn resolve_common_git_dir(resolved_gitdir: &Path) -> PathBuf {
    let try_common = (|| -> Option<PathBuf> {
        let commondir_file = resolved_gitdir.join("commondir");
        if !commondir_file.is_file() {
            return None;
        }
        let raw = fs::read(&commondir_file).ok()?;
        let text = String::from_utf8_lossy(&raw);
        let rel = py_strip(&text);
        if rel.is_empty() {
            return None;
        }
        let candidate = resolved_gitdir.join(rel);
        Some(fs::canonicalize(&candidate).unwrap_or(candidate))
    })();
    try_common.unwrap_or_else(|| resolved_gitdir.to_path_buf())
}

/// Load `.git/info/exclude` supporting `.git/` directories, submodules, and linked worktrees (`commondir`).
pub fn load_git_exclude_spec(repo_root: &Path) -> Option<GitignoreMatcher> {
    let git_path = repo_root.join(".git");
    if git_path.is_dir() {
        return GitignoreMatcher::from_spec_file(repo_root, &git_path.join("info").join("exclude"));
    }
    if git_path.is_file() {
        let raw = fs::read(&git_path).ok()?;
        let text = String::from_utf8_lossy(&raw);
        let trimmed = py_strip(&text);
        if let Some(rest) = trimmed.strip_prefix("gitdir:") {
            let gitdir_rel = py_strip(rest);
            let joined = repo_root.join(gitdir_rel);
            let resolved_gitdir = fs::canonicalize(&joined).unwrap_or(joined);
            let common_dir = resolve_common_git_dir(&resolved_gitdir);
            return GitignoreMatcher::from_spec_file(
                repo_root,
                &common_dir.join("info").join("exclude"),
            )
            .or_else(|| {
                GitignoreMatcher::from_spec_file(
                    repo_root,
                    &resolved_gitdir.join("info").join("exclude"),
                )
            });
        }
    }
    None
}

/// Discover and compile initial root ignore specifications (`resolve_active_specs` parity).
pub fn resolve_root_specs(
    root: &Path,
    respect_gitignore: bool,
    custom_gitignore_file: Option<&Path>,
    home_dir: Option<&Path>,
) -> Arc<[GitignoreMatcher]> {
    let mut specs = Vec::new();
    if respect_gitignore {
        let git_root = find_git_repo_root(root);
        let ancestors = collect_ancestor_dirs(root, git_root.as_deref());
        let base_dir = git_root.as_deref().unwrap_or(root);

        if let Some(global_spec) = find_global_gitignore_path(base_dir, home_dir)
            .and_then(|gp| GitignoreMatcher::from_spec_file(base_dir, &gp))
        {
            specs.push(global_spec);
        }
        if let Some(excl) = git_root.as_deref().and_then(load_git_exclude_spec) {
            specs.push(excl);
        }
        for dir in &ancestors {
            if let Some(gi) = GitignoreMatcher::from_spec_file(dir, &dir.join(".gitignore")) {
                specs.push(gi);
            }
        }
    }
    if let Some(custom_path) = custom_gitignore_file {
        let expanded = match custom_path.to_str() {
            Some(s) => expand_tilde(s, home_dir),
            None => custom_path.to_path_buf(),
        };
        if let Some(custom_spec) = GitignoreMatcher::from_spec_file(root, &expanded) {
            specs.push(custom_spec);
        }
    }
    Arc::from(specs)
}

/// Load child `.git/info/exclude` and `.gitignore` specs during downward directory descent.
pub fn load_child_specs(
    child_dir: &Path,
    active_specs: &Arc<[GitignoreMatcher]>,
    respect_gitignore: bool,
) -> Arc<[GitignoreMatcher]> {
    if !respect_gitignore {
        return Arc::clone(active_specs);
    }
    let nested_excl = if child_dir.join(".git").exists() {
        load_git_exclude_spec(child_dir)
    } else {
        None
    };
    let local_gi = GitignoreMatcher::from_spec_file(child_dir, &child_dir.join(".gitignore"));
    if nested_excl.is_none() && local_gi.is_none() {
        return Arc::clone(active_specs);
    }
    let mut combined = Vec::with_capacity(active_specs.len() + 2);
    combined.extend(active_specs.iter().cloned());
    if let Some(ex) = nested_excl {
        combined.push(ex);
    }
    if let Some(gi) = local_gi {
        combined.push(gi);
    }
    Arc::from(combined)
}

/// Evaluate hierarchical gitignore rules in reverse order (deepest to shallowest).
pub fn is_path_ignored(entry_path: &Path, is_dir: bool, specs: &[GitignoreMatcher]) -> bool {
    for spec in specs.iter().rev() {
        if let Some(decision) = spec.check_scoped(entry_path, is_dir) {
            return decision;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn linked_worktree_commondir_and_child_negation_and_timeout_behave_cleanly() {
        let tmp = std::env::temp_dir().join(format!("findfmt_rs_ign_stack_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let common_git = tmp.join("main_repo_git");
        let private_wt = common_git.join("worktrees").join("wt1");
        let repo = tmp.join("worktree_repo");
        let sub = repo.join("sub");
        fs::create_dir_all(common_git.join("info")).expect("create common info");
        fs::create_dir_all(&private_wt).expect("create private worktree gitdir");
        fs::create_dir_all(&sub).expect("create sub");

        fs::write(common_git.join("info").join("exclude"), "*.excl\n").expect("write exclude");
        fs::write(private_wt.join("commondir"), "../..\n").expect("write commondir");
        fs::write(repo.join(".git"), format!("gitdir: {}\n", private_wt.display()))
            .expect("write gitdir");
        fs::write(repo.join(".gitignore"), "*.log\n").expect("write root gitignore");
        fs::write(sub.join(".gitignore"), "!keep.log\n").expect("write sub gitignore");

        let canon_repo = fs::canonicalize(&repo).unwrap_or(repo);
        let canon_sub = canon_repo.join("sub");
        let root_specs = resolve_root_specs(&canon_repo, true, None, None);
        let sub_specs = load_child_specs(&canon_sub, &root_specs, true);

        assert!(is_path_ignored(&canon_repo.join("secret.excl"), false, &sub_specs));
        assert!(is_path_ignored(&canon_sub.join("drop.log"), false, &sub_specs));
        assert!(!is_path_ignored(&canon_sub.join("keep.log"), false, &sub_specs));

        #[cfg(unix)]
        {
            let timed_out = run_git_config_with_timeout(
                Path::new("sleep"),
                &canon_repo,
                Duration::from_millis(15),
            );
            assert!(timed_out.is_none());
        }

        let _ = fs::remove_dir_all(&tmp);
    }
}
