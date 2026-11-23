//! Glob pattern matching (`-P`, `-I`, `--ignore-case`, `--match-dirs`) and early tag skipping (#582).

use std::collections::BTreeSet;
use std::path::Path;

use ignore::Match;
use ignore::gitignore::{Gitignore, GitignoreBuilder};

use crate::shebang::py_strip;
use crate::tags::{FilterCriteria, TagRegistry};

const INTERPRETER_TAGS: [&str; 24] = [
    "ash",
    "awk",
    "bash",
    "bats",
    "cbsd",
    "csh",
    "dash",
    "erlang",
    "expect",
    "javascript",
    "ksh",
    "nushell",
    "perl",
    "php",
    "php7",
    "php8",
    "python",
    "python2",
    "python3",
    "ruby",
    "sh",
    "shell",
    "tcsh",
    "zsh",
];

const GENERIC_TAGS: [&str; 7] = [
    "binary",
    "directory",
    "executable",
    "file",
    "non-executable",
    "symlink",
    "text",
];

/// Split a glob pattern by `|` alternation outside `[...]` bracket classes (`patterns.py` parity).
pub fn split_pattern_alternations(pattern: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut in_bracket = false;

    for ch in pattern.chars() {
        if ch == '[' && !in_bracket {
            in_bracket = true;
            current.push(ch);
        } else if ch == ']' && in_bracket {
            in_bracket = false;
            current.push(ch);
        } else if ch == '|' && !in_bracket {
            let trimmed = py_strip(&current);
            if !trimmed.is_empty() {
                parts.push(trimmed.to_owned());
            }
            current.clear();
        } else {
            current.push(ch);
        }
    }
    let trimmed = py_strip(&current);
    if !trimmed.is_empty() {
        parts.push(trimmed.to_owned());
    }
    parts
}

fn compile_pattern_gitignore(patterns: &[String], ignore_case: bool) -> Option<Gitignore> {
    if patterns.is_empty() {
        return None;
    }
    let mut lines = Vec::new();
    for pat in patterns {
        lines.extend(split_pattern_alternations(pat));
    }
    if lines.is_empty() {
        return None;
    }
    let mut builder = GitignoreBuilder::new(Path::new(""));
    builder.case_insensitive(ignore_case).ok()?;
    for line in &lines {
        let _ = builder.add_line(None, line);
    }
    builder.build().ok()
}

fn strip_root_prefix_str(s: &str) -> &str {
    let bytes = s.as_bytes();
    let without_drive = if bytes.len() >= 3 && bytes[0].is_ascii_alphabetic() && bytes[1] == b':' && bytes[2] == b'/' {
        &s[3..]
    } else {
        s
    };
    without_drive.trim_matches('/')
}

fn match_gitignore_spec(spec: &Gitignore, rel_posix: &str, name: &str, is_dir: bool) -> bool {
    let clean_rel = strip_root_prefix_str(rel_posix);
    let clean_name = name.trim_matches('/');
    (!clean_rel.is_empty()
        && matches!(
            spec.matched_path_or_any_parents(Path::new(clean_rel), is_dir),
            Match::Ignore(_)
        ))
        || (!clean_name.is_empty()
            && matches!(spec.matched(Path::new(clean_name), is_dir), Match::Ignore(_)))
}

/// Convert `path` (optionally stripped of `base_root`) into `(posix_rel, basename)` strings.
pub fn to_posix_and_name(path: &Path, base_root: Option<&Path>) -> (String, String) {
    let rel = match base_root {
        Some(base) => path.strip_prefix(base).unwrap_or(path),
        None => path,
    };
    let raw_rel = rel.to_string_lossy();
    let posix_rel = if cfg!(windows) {
        raw_rel.replace('\\', "/")
    } else {
        raw_rel.into_owned()
    };
    let name = rel
        .file_name()
        .or_else(|| path.file_name())
        .map_or_else(String::new, |n| n.to_string_lossy().into_owned());
    (posix_rel, name)
}

/// Compiled include (`-P`) and exclude (`-I`) pattern matcher mirroring `PatternMatcher` in `patterns.py`.
#[derive(Clone, Debug, Default)]
pub struct PatternMatcher {
    include_spec: Option<Gitignore>,
    exclude_spec: Option<Gitignore>,
    pub ignore_case: bool,
    pub match_dirs: bool,
}

impl PatternMatcher {
    /// Construct a `PatternMatcher` from raw include and exclude pattern lists.
    pub fn new(
        include_patterns: &[String],
        exclude_patterns: &[String],
        ignore_case: bool,
        match_dirs: bool,
    ) -> Self {
        Self {
            include_spec: compile_pattern_gitignore(include_patterns, ignore_case),
            exclude_spec: compile_pattern_gitignore(exclude_patterns, ignore_case),
            ignore_case,
            match_dirs,
        }
    }

    pub fn is_active(&self) -> bool {
        self.include_spec.is_some() || self.exclude_spec.is_some()
    }

    pub fn should_exclude(&self, path: &Path, is_dir: bool, base_root: Option<&Path>) -> bool {
        let Some(ref spec) = self.exclude_spec else {
            return false;
        };
        let (rel_str, name) = to_posix_and_name(path, base_root);
        match_gitignore_spec(spec, &rel_str, &name, is_dir)
    }

    pub fn matches_file(
        &self,
        path: &Path,
        base_root: Option<&Path>,
        inherited_match: bool,
    ) -> bool {
        if self.should_exclude(path, false, base_root) {
            return false;
        }
        let Some(ref spec) = self.include_spec else {
            return true;
        };
        if inherited_match {
            return true;
        }
        let (rel_str, name) = to_posix_and_name(path, base_root);
        match_gitignore_spec(spec, &rel_str, &name, false)
    }

    pub fn matches_dir(&self, path: &Path, base_root: Option<&Path>) -> bool {
        let Some(ref spec) = self.include_spec else {
            return true;
        };
        let (rel_str, name) = to_posix_and_name(path, base_root);
        match_gitignore_spec(spec, &rel_str, &name, true)
    }

    pub fn should_inherit_match(
        &self,
        dir_path: &Path,
        base_root: Option<&Path>,
        parent_inherited: bool,
    ) -> bool {
        if !self.match_dirs {
            return false;
        }
        if parent_inherited {
            return true;
        }
        self.matches_dir(dir_path, base_root)
    }

    pub fn matches_classified_item(
        &self,
        target_rel_or_abs: &Path,
        is_dir_item: bool,
        inherited_match: bool,
    ) -> bool {
        if !self.is_active() {
            return true;
        }
        if is_dir_item {
            if self.should_exclude(target_rel_or_abs, true, None) {
                return false;
            }
            if self.include_spec.is_none() || inherited_match || !self.match_dirs {
                return true;
            }
            return self.matches_dir(target_rel_or_abs, None);
        }
        self.matches_file(target_rel_or_abs, None, inherited_match)
    }
}

/// Early tag-based file rejection mirroring `src/findfmt/traversal/tags.py:can_skip_file_by_tags`.
pub fn can_skip_entry_by_tags(
    filename: &str,
    is_symlink: bool,
    follow_symlinks: bool,
    is_executable: Option<bool>,
    criteria: &FilterCriteria,
    registry: &TagRegistry,
    guessed_mime: Option<&str>,
) -> bool {
    if criteria.include_tags.is_empty() && criteria.exclude_tags.is_empty() {
        return false;
    }
    if follow_symlinks && is_symlink {
        return false;
    }
    let name_tags = registry.tags_from_filename(filename);
    if !criteria.exclude_tags.is_empty() && !name_tags.is_disjoint(&criteria.exclude_tags) {
        return true;
    }
    if criteria.include_tags.is_empty()
        || GENERIC_TAGS
            .iter()
            .any(|&g| criteria.include_tags.contains(g))
    {
        return false;
    }

    let wants_interpreter = INTERPRETER_TAGS
        .iter()
        .any(|&it| criteria.include_tags.contains(it));
    let allow_interp = is_executable != Some(false) && wants_interpreter;

    let mut possible: BTreeSet<String> = name_tags;
    if let Some(mt) = guessed_mime {
        possible.insert(format!("mime:{mt}"));
        if let Some(primary) = mt.split('/').next() {
            possible.insert(primary.to_owned());
        }
    }
    if allow_interp {
        for &it in &INTERPRETER_TAGS {
            possible.insert(it.to_owned());
        }
    }

    if criteria.all_tags {
        !criteria.include_tags.is_subset(&possible)
    } else {
        criteria.include_tags.is_disjoint(&possible)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn alternations_and_pattern_matcher_mirror_python_semantics() {
        assert_eq!(
            split_pattern_alternations("  *.py | [a|b].txt | *.rs "),
            vec!["*.py", "[a|b].txt", "*.rs"]
        );
        let matcher = PatternMatcher::new(
            &["*.py|docs/*.rst".into(), "src/**/*.ts".into(), "[!a-z].dat".into()],
            &["test_*.py".into(), "build/".into()],
            false,
            false,
        );
        assert!(matcher.matches_file(Path::new("main.py"), None, false));
        assert!(!matcher.matches_file(Path::new("test_main.py"), None, false));
        assert!(matcher.matches_file(Path::new("docs/guide.rst"), None, false));
        assert!(matcher.matches_file(Path::new("src/a/b/app.ts"), None, false));
        assert!(matcher.matches_file(Path::new("9.dat"), None, false));
        assert!(!matcher.matches_file(Path::new("a.dat"), None, false));
        assert!(matcher.should_exclude(Path::new("build"), true, None));
        assert!(!matcher.should_exclude(Path::new("build"), false, None));
    }
}
