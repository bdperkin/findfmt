//! Gitignore line normalization (`#354`) and panic-free `ignore` / `globset` matching (#582, #585).

use std::fs;
use std::path::{Component, Path, PathBuf};

use globset::{GlobBuilder, GlobMatcher};
use ignore::Match;
use ignore::gitignore::{Gitignore, GitignoreBuilder, Glob};

use crate::shebang::py_strip;

/// Trim a `.gitignore` pattern line preserving significant leading and `\ `-escaped trailing spaces.
///
/// Mirrors `src/findfmt/traversal/ignore.py:_trim_gitignore_line` (#354):
/// - Strips trailing `\r` and `\n`.
/// - Strips unescaped trailing ASCII spaces (`' '`), stopping when an odd number of backslashes
///   immediately precedes the trailing space.
/// - Preserves leading spaces verbatim.
pub fn trim_gitignore_line(raw_line: &str) -> &str {
    let mut line = raw_line.trim_end_matches(['\r', '\n']);
    while line.ends_with(' ') {
        let bytes = line.as_bytes();
        let mut num_slashes = 0_usize;
        let mut cursor = bytes.len().saturating_sub(1);
        while cursor > 0 {
            cursor -= 1;
            if bytes.get(cursor) == Some(&b'\\') {
                num_slashes += 1;
            } else {
                break;
            }
        }
        if num_slashes % 2 == 1 {
            break;
        }
        line = line.get(..line.len() - 1).unwrap_or("");
    }
    line
}

/// Return `true` when `trimmed_line` represents an active gitignore rule (non-blank and non-comment).
///
/// Mirrors `if line.strip() and not line.startswith("#"):` in `src/findfmt/traversal/ignore.py`.
pub fn is_active_gitignore_line(trimmed_line: &str) -> bool {
    !py_strip(trimmed_line).is_empty() && !trimmed_line.starts_with('#')
}

/// Return `true` when `trimmed_line` ends with an odd number of trailing backslashes (invalid escape).
fn has_dangling_trailing_backslash(trimmed_line: &str) -> bool {
    let trailing_slashes = trimmed_line
        .as_bytes()
        .iter()
        .rev()
        .take_while(|&&b| b == b'\\')
        .count();
    trailing_slashes % 2 == 1
}

/// Split raw text across universal newlines (`\r\n`, `\n`, and standalone `\r`).
pub(crate) fn split_universal_lines(content: &str) -> Vec<&str> {
    let bytes = content.as_bytes();
    let mut out = Vec::new();
    let mut start = 0_usize;
    let mut i = 0_usize;
    while i < bytes.len() {
        match bytes[i] {
            b'\r' => {
                if let Some(seg) = content.get(start..i) {
                    out.push(seg);
                }
                if bytes.get(i + 1) == Some(&b'\n') {
                    i += 2;
                } else {
                    i += 1;
                }
                start = i;
            }
            b'\n' => {
                if let Some(seg) = content.get(start..i) {
                    out.push(seg);
                }
                i += 1;
                start = i;
            }
            _ => i += 1,
        }
    }
    if let Some(seg) = content.get(start..) {
        out.push(seg);
    }
    out
}

fn normalize_relative_components(stripped: &Path) -> PathBuf {
    let mut clean = PathBuf::new();
    for comp in stripped.components() {
        match comp {
            Component::Normal(part) if !part.is_empty() => clean.push(part),
            Component::ParentDir => {
                let _ = clean.pop();
            }
            _ => {}
        }
    }
    clean
}

/// Evaluate `gi` against `clean` and its non-empty relative parent directories (skipping `""`).
fn matched_non_empty_ancestors<'a>(gi: &'a Gitignore, clean: &Path, is_dir: bool) -> Match<&'a Glob> {
    let direct = gi.matched(clean, is_dir);
    if !direct.is_none() {
        return direct;
    }
    for parent in clean.ancestors().skip(1) {
        if parent.as_os_str().is_empty() {
            break;
        }
        let parent_match = gi.matched(parent, true);
        if !parent_match.is_none() {
            return parent_match;
        }
    }
    Match::None
}

/// Compiled `.gitignore` specification bound to a directory root.
#[derive(Clone, Debug)]
pub struct GitignoreMatcher {
    root: PathBuf,
    inner: Gitignore,
}

impl GitignoreMatcher {
    /// Parse and compile `.gitignore` text, returning `(matcher, invalid_line_count)` without panicking.
    pub fn from_text(root: &Path, content: &str) -> (Self, usize) {
        Self::compile_internal(root, content).0
    }

    fn compile_internal(root: &Path, content: &str) -> ((Self, usize), usize) {
        let mut builder = GitignoreBuilder::new(Path::new(""));
        let mut errors = 0_usize;
        let mut active_lines = 0_usize;
        for raw_line in split_universal_lines(content) {
            let trimmed = trim_gitignore_line(raw_line);
            if !is_active_gitignore_line(trimmed) {
                continue;
            }
            active_lines += 1;
            if has_dangling_trailing_backslash(trimmed) {
                errors += 1;
                continue;
            }
            // Mirror `pathspec` GitIgnoreBasicPattern slash-only semantics:
            // `/` matches everything (`**`), `!/` whitelists everything (`!**`),
            // while multi-slash `//`+ or `!//`+ are valid no-op rules.
            let normalized = if trimmed == "/" {
                Some("**")
            } else if trimmed == "!/" {
                Some("!**")
            } else if trimmed.chars().all(|c| c == '/')
                || trimmed
                    .strip_prefix('!')
                    .is_some_and(|rest| !rest.is_empty() && rest.chars().all(|c| c == '/'))
            {
                None
            } else {
                Some(trimmed)
            };
            if normalized.is_some_and(|rule| builder.add_line(None, rule).is_err()) {
                errors += 1;
            }
        }
        let inner = match builder.build() {
            Ok(gi) => gi,
            Err(_) => {
                errors += 1;
                Gitignore::empty()
            }
        };
        (
            (
                Self {
                    root: root.to_path_buf(),
                    inner,
                },
                errors,
            ),
            active_lines,
        )
    }

    /// Parse raw `.gitignore` bytes using UTF-8 replacement (`errors="replace"` parity).
    pub fn from_bytes_lossy(root: &Path, raw_bytes: &[u8]) -> (Self, usize) {
        let decoded = String::from_utf8_lossy(raw_bytes);
        Self::from_text(root, &decoded)
    }

    /// Load a specification file strictly mirroring `src/findfmt/traversal/ignore.py:load_spec_file`.
    pub fn from_spec_file(base_dir: &Path, spec_file: &Path) -> Option<Self> {
        if !spec_file.is_file() {
            return None;
        }
        let raw_bytes = fs::read(spec_file).ok()?;
        let decoded = String::from_utf8_lossy(&raw_bytes);
        let ((matcher, errors), active_lines) = Self::compile_internal(base_dir, &decoded);
        if active_lines == 0 || errors > 0 {
            None
        } else {
            Some(matcher)
        }
    }

    /// Return the directory root this matcher is bound to.
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Evaluate tri-state ignore decision when `candidate` resides strictly beneath `self.root`.
    pub fn check_scoped(&self, candidate: &Path, is_dir: bool) -> Option<bool> {
        let stripped = candidate.strip_prefix(&self.root).ok()?;
        let clean = normalize_relative_components(stripped);
        if clean.as_os_str().is_empty() {
            return None;
        }
        match matched_non_empty_ancestors(&self.inner, &clean, is_dir) {
            Match::Ignore(_) => Some(true),
            Match::Whitelist(_) => Some(false),
            Match::None => None,
        }
    }

    /// Evaluate whether `candidate` (or any parent directory under `root`) is ignored.
    pub fn is_ignored(&self, candidate: &Path, is_dir: bool) -> bool {
        let stripped = candidate.strip_prefix(&self.root).unwrap_or(candidate);
        let clean = normalize_relative_components(stripped);
        if clean.as_os_str().is_empty() {
            return false;
        }
        matches!(
            matched_non_empty_ancestors(&self.inner, &clean, is_dir),
            Match::Ignore(_)
        )
    }
}

/// Compile a standalone glob pattern via `globset` (`-P` / `-I` foundation for `#582`).
pub fn compile_glob_matcher(
    pattern: &str,
    case_insensitive: bool,
) -> Result<GlobMatcher, globset::Error> {
    GlobBuilder::new(pattern)
        .case_insensitive(case_insensitive)
        .literal_separator(false)
        .build()
        .map(|g| g.compile_matcher())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trim_gitignore_preserves_leading_and_escaped_trailing_spaces() {
        assert_eq!(trim_gitignore_line("*.pyc   \r\n"), "*.pyc");
        assert_eq!(trim_gitignore_line(r"escaped\ "), r"escaped\ ");
        assert_eq!(trim_gitignore_line(r"double\\ "), r"double\\");
        assert_eq!(trim_gitignore_line(r"triple\\\  "), r"triple\\\ ");
        assert_eq!(
            trim_gitignore_line("  leading_space.txt  \n"),
            "  leading_space.txt"
        );
        assert!(!is_active_gitignore_line(""));
        assert!(!is_active_gitignore_line("# comment"));
        assert!(is_active_gitignore_line(r"\#not_comment"));
    }

    #[test]
    fn gitignore_matcher_handles_wildcard_dirs_slashes_and_scoped_checks() {
        let root = Path::new("/repo");
        let (star_dir, errs0) = GitignoreMatcher::from_text(root, "*/  \n");
        assert_eq!(errs0, 0);
        assert_eq!(star_dir.check_scoped(Path::new("/repo/.gitignore"), false), None);
        assert_eq!(star_dir.check_scoped(Path::new("/repo/symlink_dir"), false), None);
        assert_eq!(star_dir.check_scoped(Path::new("/repo/sub"), true), Some(true));
        assert_eq!(
            star_dir.check_scoped(Path::new("/repo/sub/file.py"), false),
            Some(true)
        );

        let (double_slash, _) = GitignoreMatcher::from_text(root, "//\n");
        assert_eq!(double_slash.check_scoped(Path::new("/repo/a"), false), None);
        assert_eq!(double_slash.check_scoped(Path::new("/repo/a"), true), None);

        let (single_slash, _) = GitignoreMatcher::from_text(root, "/\n");
        assert_eq!(single_slash.check_scoped(Path::new("/repo/a"), false), Some(true));

        let rules = "*.log\r\n!keep.log\r/root_only.tmp\nbuild/\n[z-a]\n\\\n";
        let (matcher, errs) = GitignoreMatcher::from_text(root, rules);
        assert!(errs >= 2);
        assert!(matcher.is_ignored(Path::new("/repo/debug.log"), false));
        assert!(!matcher.is_ignored(Path::new("/repo/keep.log"), false));
        assert_eq!(matcher.check_scoped(Path::new("/repo"), true), None);
        assert!(compile_glob_matcher("*.rs", true).is_ok());
        assert!(compile_glob_matcher("[unclosed", false).is_err());
    }
}
