//! Glob pattern matching (`-P`, `-I`, `--ignore-case`, `--match-dirs`) and early tag skipping (#582).

use std::collections::BTreeSet;
use std::path::Path;

use crate::glob_u32::{GlobSpecU32, path_to_u32_segments};
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

fn compile_pattern_spec(
    patterns: &[String],
    ignore_case: bool,
) -> Result<Option<GlobSpecU32>, String> {
    if patterns.is_empty() {
        return Ok(None);
    }
    let mut lines = Vec::new();
    for pat in patterns {
        lines.extend(split_pattern_alternations(pat));
    }
    GlobSpecU32::try_from_lines(&lines, ignore_case)
}

fn match_spec_u32(
    spec: &GlobSpecU32,
    rel_segs: &[Vec<u32>],
    name_opt: Option<&Vec<u32>>,
    is_dir: bool,
) -> bool {
    let name_slice = name_opt.map_or(&[][..], std::slice::from_ref);
    if is_dir {
        spec.matches_segments(rel_segs, true)
            || (!name_slice.is_empty() && spec.matches_segments(name_slice, true))
            || spec.matches_segments(rel_segs, false)
            || (!name_slice.is_empty() && spec.matches_segments(name_slice, false))
    } else {
        spec.matches_segments(rel_segs, false)
            || (!name_slice.is_empty() && spec.matches_segments(name_slice, false))
    }
}

/// Compiled include (`-P`) and exclude (`-I`) pattern matcher mirroring `PatternMatcher` in `patterns.py`.
#[derive(Clone, Debug, Default)]
pub struct PatternMatcher {
    include_spec: Option<GlobSpecU32>,
    exclude_spec: Option<GlobSpecU32>,
    pub ignore_case: bool,
    pub match_dirs: bool,
}

impl PatternMatcher {
    /// Fallible constructor propagating malformed glob syntax as `Err(String)`.
    pub fn try_new(
        include_patterns: &[String],
        exclude_patterns: &[String],
        ignore_case: bool,
        match_dirs: bool,
    ) -> Result<Self, String> {
        Ok(Self {
            include_spec: compile_pattern_spec(include_patterns, ignore_case)?,
            exclude_spec: compile_pattern_spec(exclude_patterns, ignore_case)?,
            ignore_case,
            match_dirs,
        })
    }

    /// Construct a `PatternMatcher` from raw include and exclude pattern lists.
    pub fn new(
        include_patterns: &[String],
        exclude_patterns: &[String],
        ignore_case: bool,
        match_dirs: bool,
    ) -> Self {
        Self::try_new(include_patterns, exclude_patterns, ignore_case, match_dirs)
            .unwrap_or_default()
    }

    pub fn is_active(&self) -> bool {
        self.include_spec.is_some() || self.exclude_spec.is_some()
    }

    pub fn should_exclude(&self, path: &Path, is_dir: bool, base_root: Option<&Path>) -> bool {
        let Some(ref spec) = self.exclude_spec else {
            return false;
        };
        let (rel_segs, name_opt) = path_to_u32_segments(path, base_root);
        match_spec_u32(spec, &rel_segs, name_opt.as_ref(), is_dir)
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
        let (rel_segs, name_opt) = path_to_u32_segments(path, base_root);
        match_spec_u32(spec, &rel_segs, name_opt.as_ref(), false)
    }

    pub fn matches_dir(&self, path: &Path, base_root: Option<&Path>) -> bool {
        let Some(ref spec) = self.include_spec else {
            return true;
        };
        let (rel_segs, name_opt) = path_to_u32_segments(path, base_root);
        match_spec_u32(spec, &rel_segs, name_opt.as_ref(), true)
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

/// Inspect active tag criteria to skip prefilter stat and MIME lookups when unused (`_pruning.py` parity).
pub fn tag_prefilter_requirements(criteria: &FilterCriteria) -> (bool, bool, bool) {
    let active = !criteria.include_tags.is_empty() || !criteria.exclude_tags.is_empty();
    if !active {
        return (false, false, false);
    }
    let has_generic = GENERIC_TAGS
        .iter()
        .any(|&g| criteria.include_tags.contains(g));
    let needs_include_eval = !criteria.include_tags.is_empty() && !has_generic;
    let needs_exec = needs_include_eval
        && INTERPRETER_TAGS
            .iter()
            .any(|&it| criteria.include_tags.contains(it));
    (true, needs_include_eval, needs_exec)
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
    fn alternations_unicode_question_colon_dir_and_surrogate_lossless_matching() {
        assert_eq!(
            split_pattern_alternations("  *.py | [a|b].txt | *.rs "),
            vec!["*.py", "[a|b].txt", "*.rs"]
        );
        let matcher = PatternMatcher::new(
            &[
                "*.py|docs/*.rst".into(),
                "src/**/*.ts".into(),
                "[!a-z].dat".into(),
                "?.txt".into(),
                "/C:/report.md".into(),
            ],
            &["test_*.py".into(), "build/".into(), "\u{fffd}.txt".into()],
            false,
            false,
        );
        assert!(matcher.matches_file(Path::new("main.py"), None, false));
        assert!(!matcher.matches_file(Path::new("test_main.py"), None, false));
        assert!(matcher.matches_file(Path::new("é.txt"), None, false));
        assert!(matcher.matches_file(Path::new("🚀.txt"), None, false));
        assert!(!matcher.matches_file(Path::new("ab.txt"), None, false));
        #[cfg(unix)]
        {
            use std::ffi::OsStr;
            use std::os::unix::ffi::OsStrExt;
            assert!(matcher.matches_file(Path::new("C:/report.md"), None, false));
            let raw_ff = Path::new(OsStr::from_bytes(b"\xff.txt"));
            assert!(matcher.matches_file(raw_ff, None, false));
            assert!(!matcher.should_exclude(raw_ff, false, None));
            assert!(matcher.should_exclude(Path::new("\u{fffd}.txt"), false, None));
        }
        assert!(matcher.should_exclude(Path::new("build"), true, None));
        assert!(!matcher.should_exclude(Path::new("build"), false, None));
    }
}
