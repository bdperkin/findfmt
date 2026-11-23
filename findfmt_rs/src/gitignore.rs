//! Gitignore line normalization (`#354`) and panic-free `ignore` / `globset` matching (#582, #585).

use std::path::{Component, Path, PathBuf};

use globset::{GlobBuilder, GlobMatcher};
use ignore::Match;
use ignore::gitignore::{Gitignore, GitignoreBuilder};

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

/// Compiled `.gitignore` specification bound to a directory root.
#[derive(Clone, Debug)]
pub struct GitignoreMatcher {
    root: PathBuf,
    inner: Gitignore,
}

impl GitignoreMatcher {
    /// Parse and compile `.gitignore` text, returning `(matcher, invalid_line_count)` without panicking.
    pub fn from_text(root: &Path, content: &str) -> (Self, usize) {
        // Bind inner GitignoreBuilder to an empty relative base so `self.root` is stripped
        // once in `is_ignored` (preventing double-stripping when `root` itself is relative).
        let mut builder = GitignoreBuilder::new(Path::new(""));
        let mut errors = 0_usize;
        for raw_line in content.split('\n') {
            let trimmed = trim_gitignore_line(raw_line);
            if !is_active_gitignore_line(trimmed) {
                continue;
            }
            if builder.add_line(None, trimmed).is_err() {
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
            Self {
                root: root.to_path_buf(),
                inner,
            },
            errors,
        )
    }

    /// Parse raw `.gitignore` bytes using UTF-8 replacement (`errors="replace"` parity).
    pub fn from_bytes_lossy(root: &Path, raw_bytes: &[u8]) -> (Self, usize) {
        let decoded = String::from_utf8_lossy(raw_bytes);
        Self::from_text(root, &decoded)
    }

    /// Evaluate whether `candidate` (or any parent directory under `root`) is ignored.
    ///
    /// Normalizes arbitrary candidate paths so malformed, empty, root, or `..` segments never panic.
    pub fn is_ignored(&self, candidate: &Path, is_dir: bool) -> bool {
        let stripped = candidate.strip_prefix(&self.root).unwrap_or(candidate);
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
        if clean.as_os_str().is_empty() {
            return false;
        }

        match self.inner.matched(&clean, is_dir) {
            Match::Ignore(_) => return true,
            Match::Whitelist(_) => return false,
            Match::None => {}
        }

        let mut cur = clean.parent();
        while let Some(parent) = cur {
            if parent.as_os_str().is_empty() {
                break;
            }
            match self.inner.matched(parent, true) {
                Match::Ignore(_) => return true,
                Match::Whitelist(_) => return false,
                Match::None => cur = parent.parent(),
            }
        }
        false
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
        assert_eq!(trim_gitignore_line("  leading_space.txt  \n"), "  leading_space.txt");
        assert!(!is_active_gitignore_line(""));
        assert!(!is_active_gitignore_line("# comment"));
        assert!(is_active_gitignore_line(r"\#not_comment"));
    }

    #[test]
    fn gitignore_matcher_handles_negation_anchors_and_malformed_globs() {
        let root = Path::new("/repo");
        let rules = "*.log\n!keep.log\n/root_only.tmp\nbuild/\n[z-a]\n";
        let (matcher, errs) = GitignoreMatcher::from_text(root, rules);
        assert!(errs >= 1);
        assert!(matcher.is_ignored(Path::new("/repo/debug.log"), false));
        assert!(!matcher.is_ignored(Path::new("/repo/keep.log"), false));
        assert!(matcher.is_ignored(Path::new("/repo/root_only.tmp"), false));
        assert!(!matcher.is_ignored(Path::new("/repo/sub/root_only.tmp"), false));
        assert!(matcher.is_ignored(Path::new("/repo/build/artifact.o"), false));
        assert!(!matcher.is_ignored(Path::new(""), false));
        assert!(!matcher.is_ignored(Path::new("/repo/.."), true));

        let rel_root = Path::new("repo");
        let (rel_matcher, rel_errs) = GitignoreMatcher::from_text(rel_root, "/only.tmp\n");
        assert_eq!(rel_errs, 0);
        assert!(rel_matcher.is_ignored(Path::new("repo/only.tmp"), false));
        assert!(!rel_matcher.is_ignored(Path::new("repo/repo/only.tmp"), false));

        assert!(compile_glob_matcher("*.rs", true).is_ok());
        assert!(compile_glob_matcher("[unclosed", false).is_err());
    }
}
