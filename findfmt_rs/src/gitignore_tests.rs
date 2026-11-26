//! Unit tests for `findfmt_rs::gitignore` (#582, #590).

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
    assert_eq!(star_dir.root(), root);
    assert_eq!(
        star_dir.check_scoped(Path::new("/repo/.gitignore"), false),
        None
    );
    assert_eq!(
        star_dir.check_scoped(Path::new("/repo/symlink_dir"), false),
        None
    );
    assert_eq!(
        star_dir.check_scoped(Path::new("/repo/sub"), true),
        Some(true)
    );
    assert_eq!(
        star_dir.check_scoped(Path::new("/repo/sub/file.py"), false),
        Some(true)
    );

    let (neg_dir, _) = GitignoreMatcher::from_text(root, "/*\n!sub/\n");
    assert_eq!(
        neg_dir.check_scoped(Path::new("/repo/sub"), true),
        Some(false)
    );
    assert_eq!(
        neg_dir.check_scoped(Path::new("/repo/sub/file.py"), false),
        Some(false)
    );

    let (double_slash, _) = GitignoreMatcher::from_text(root, "//\n");
    assert_eq!(double_slash.check_scoped(Path::new("/repo/a"), false), None);
    assert_eq!(double_slash.check_scoped(Path::new("/repo/a"), true), None);

    let (single_slash, _) = GitignoreMatcher::from_text(root, "/\n");
    assert_eq!(
        single_slash.check_scoped(Path::new("/repo/a"), false),
        Some(true)
    );

    let (build_star, _) = GitignoreMatcher::from_text(root, "/build/*\n");
    assert!(build_star.is_ignored(Path::new("/repo/build/cache/item.txt"), false));

    let rules = "*.log\r\n!keep.log\r/root_only.tmp\nbuild/\n[z-a]\n\\\n";
    let (matcher, errs) = GitignoreMatcher::from_text(root, rules);
    assert!(errs >= 2);
    assert!(matcher.is_ignored(Path::new("/repo/debug.log"), false));
    assert_eq!(
        matcher.check_scoped(Path::new("/repo/sub/../debug.log"), false),
        Some(true)
    );
    assert!(!matcher.is_ignored(Path::new("/repo/keep.log"), false));
    assert_eq!(matcher.check_scoped(Path::new("/repo"), true), None);
    assert!(compile_glob_matcher("*.rs", true).is_ok());
    assert!(compile_glob_matcher("[unclosed", false).is_err());
}
