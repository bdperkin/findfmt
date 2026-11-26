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
    unicode_major: u8,
) -> Result<Option<GlobSpecU32>, String> {
    if patterns.is_empty() {
        return Ok(None);
    }
    let mut lines = Vec::new();
    for pat in patterns {
        lines.extend(split_pattern_alternations(pat));
    }
    GlobSpecU32::try_from_lines_with_unicode(&lines, ignore_case, unicode_major)
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
    pub match_dirs: bool,
}

impl PatternMatcher {
    /// Fallible constructor gated to `unicode_major` `ignore_case` equivalences (`#581`).
    pub fn try_new_for_unicode(
        include_patterns: &[String],
        exclude_patterns: &[String],
        ignore_case: bool,
        match_dirs: bool,
        unicode_major: u8,
    ) -> Result<Self, String> {
        Ok(Self {
            include_spec: compile_pattern_spec(include_patterns, ignore_case, unicode_major)?,
            exclude_spec: compile_pattern_spec(exclude_patterns, ignore_case, unicode_major)?,
            match_dirs,
        })
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
        let primary = mt.split('/').next().unwrap_or(mt);
        possible.insert(primary.to_owned());
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
#[path = "patterns_tests.rs"]
mod tests;
