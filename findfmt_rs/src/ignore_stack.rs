//! Hierarchical `.gitignore`, `.git/info/exclude`, and global ignore evaluation (#582).

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::gitignore::GitignoreMatcher;
use crate::shebang::py_strip;
use crate::walker_types::GlobalIgnoreResolution;

/// Normalize Windows `\\?\` verbatim prefixes so canonicalized paths match Python `Path.resolve()`.
fn align_path_form(candidate: PathBuf, reference: &Path) -> PathBuf {
    #[cfg(windows)]
    {
        let ref_lossy = reference.as_os_str().to_string_lossy();
        if !ref_lossy.starts_with(r"\\?\") {
            let cand_lossy = candidate.as_os_str().to_string_lossy();
            if let Some(unc_tail) = cand_lossy.strip_prefix(r"\\?\UNC\") {
                return PathBuf::from(format!(r"\\{unc_tail}"));
            }
            if let Some(dos_tail) = cand_lossy.strip_prefix(r"\\?\") {
                return PathBuf::from(dos_tail);
            }
        }
        candidate
    }
    #[cfg(not(windows))]
    {
        let _ = reference;
        candidate
    }
}

/// Locate the nearest enclosing Git repository root containing a `.git` directory or pointer file.
pub fn find_git_repo_root(start_dir: &Path) -> Option<PathBuf> {
    let resolved = fs::canonicalize(start_dir)
        .map(|p| align_path_form(p, start_dir))
        .unwrap_or_else(|_| start_dir.to_path_buf());
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

fn trim_crlf_bytes(mut raw: &[u8]) -> &[u8] {
    while let Some((&last, head)) = raw.split_last() {
        if last == b'\r' || last == b'\n' {
            raw = head;
        } else {
            break;
        }
    }
    raw
}

/// Resolve the effective Git common directory for a resolved `gitdir` (linked worktree `commondir`).
fn resolve_common_git_dir(resolved_gitdir: &Path) -> PathBuf {
    let try_common = (|| -> Option<PathBuf> {
        let commondir_file = resolved_gitdir.join("commondir");
        if !commondir_file.is_file() {
            return None;
        }
        let raw = fs::read(&commondir_file).ok()?;
        let trimmed = trim_crlf_bytes(&raw);
        if trimmed.is_empty() {
            return None;
        }
        #[cfg(unix)]
        let rel_path = {
            use std::ffi::OsStr;
            use std::os::unix::ffi::OsStrExt;
            PathBuf::from(OsStr::from_bytes(trimmed))
        };
        #[cfg(not(unix))]
        let rel_path = PathBuf::from(String::from_utf8_lossy(trimmed).into_owned());

        let joined = resolved_gitdir.join(rel_path);
        let candidate = fs::canonicalize(&joined)
            .map(|p| align_path_form(p, resolved_gitdir))
            .unwrap_or(joined);
        candidate.is_dir().then_some(candidate)
    })();
    try_common.unwrap_or_else(|| resolved_gitdir.to_path_buf())
}

fn resolve_repo_git_dir(repo_root: &Path) -> Option<PathBuf> {
    let git_path = repo_root.join(".git");
    if git_path.is_dir() {
        return Some(git_path);
    }
    if git_path.is_file() {
        let raw = fs::read(&git_path).ok()?;
        let text = String::from_utf8_lossy(&raw);
        let rest = py_strip(&text).strip_prefix("gitdir:")?;
        let joined = repo_root.join(py_strip(rest));
        return Some(
            fs::canonicalize(&joined)
                .map(|p| align_path_form(p, repo_root))
                .unwrap_or(joined),
        );
    }
    None
}

fn parse_core_excludes_from_ini(config_path: &Path) -> Option<String> {
    let raw = fs::read(config_path).ok()?;
    let content = String::from_utf8_lossy(&raw);
    let mut in_core = false;
    let mut found: Option<String> = None;
    for line in content.lines() {
        let trimmed = py_strip(line);
        if trimmed.is_empty() || trimmed.starts_with('#') || trimmed.starts_with(';') {
            continue;
        }
        if let Some(sec) = trimmed.strip_prefix('[').and_then(|s| s.strip_suffix(']')) {
            in_core = py_strip(sec).eq_ignore_ascii_case("core");
            continue;
        }
        if let Some((_, val)) = trimmed
            .split_once('=')
            .filter(|(key, _)| in_core && py_strip(key).eq_ignore_ascii_case("excludesfile"))
        {
            found = Some(py_strip(val).trim_matches('"').to_owned());
        }
    }
    found.filter(|s| !s.is_empty())
}

fn find_git_config_excludes_file(base_dir: &Path, home_dir: Option<&Path>) -> Option<PathBuf> {
    let repo_val = resolve_repo_git_dir(base_dir).and_then(|git_dir| {
        let common = resolve_common_git_dir(&git_dir);
        parse_core_excludes_from_ini(&common.join("config"))
            .or_else(|| parse_core_excludes_from_ini(&git_dir.join("config")))
    });
    let val = repo_val
        .or_else(|| {
            let xdg = std::env::var_os("XDG_CONFIG_HOME").filter(|v| !v.is_empty())?;
            parse_core_excludes_from_ini(&PathBuf::from(xdg).join("git").join("config"))
        })
        .or_else(|| {
            let home = home_dir?;
            parse_core_excludes_from_ini(&home.join(".gitconfig")).or_else(|| {
                parse_core_excludes_from_ini(&home.join(".config").join("git").join("config"))
            })
        })?;
    let mut configured = expand_tilde(&val, home_dir);
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

/// Resolve the user's global gitignore path without spawning blocking child processes (`#323`, `#582`).
pub fn find_global_gitignore_path(base_dir: &Path, home_dir: Option<&Path>) -> Option<PathBuf> {
    find_git_config_excludes_file(base_dir, home_dir)
        .or_else(|| find_standard_global_gitignore(home_dir))
}

/// Load `.git/info/exclude` supporting `.git/` directories, submodules, and linked worktrees (`commondir`).
pub fn load_git_exclude_spec(repo_root: &Path) -> Option<GitignoreMatcher> {
    let resolved_gitdir = resolve_repo_git_dir(repo_root)?;
    let effective_dir = resolve_common_git_dir(&resolved_gitdir);
    GitignoreMatcher::from_spec_file(repo_root, &effective_dir.join("info").join("exclude"))
}

/// Discover and compile initial root ignore specifications (`resolve_active_specs` parity).
pub fn resolve_root_specs(
    root: &Path,
    respect_gitignore: bool,
    custom_gitignore_file: Option<&Path>,
    home_dir: Option<&Path>,
    pre_resolved_global: &GlobalIgnoreResolution,
) -> Arc<[GitignoreMatcher]> {
    let mut specs = Vec::new();
    if respect_gitignore {
        let git_root = find_git_repo_root(root);
        let ancestors = collect_ancestor_dirs(root, git_root.as_deref());
        let base_dir = git_root.as_deref().unwrap_or(root);

        let global_opt = match pre_resolved_global {
            GlobalIgnoreResolution::ResolvedPath(gp) => Some(gp.clone()),
            GlobalIgnoreResolution::ResolvedNone => None,
            GlobalIgnoreResolution::Unresolved => find_global_gitignore_path(base_dir, home_dir),
        };
        if let Some(global_spec) =
            global_opt.and_then(|gp| GitignoreMatcher::from_spec_file(base_dir, &gp))
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
#[path = "ignore_stack_tests.rs"]
mod tests;
