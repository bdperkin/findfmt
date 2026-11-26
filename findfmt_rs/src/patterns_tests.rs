//! Unit tests for `findfmt_rs::patterns` (#581, #582, #590).

use super::*;

#[test]
fn alternations_unicode_question_colon_dir_and_surrogate_lossless_matching() {
    assert_eq!(
        split_pattern_alternations("  *.py | | [a|b].txt | *.rs | "),
        vec!["*.py", "[a|b].txt", "*.rs"]
    );
    let matcher = PatternMatcher::try_new_for_unicode(
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
        16,
    )
    .unwrap_or_default();
    assert!(matcher.matches_file(Path::new("main.py"), None, false));
    assert!(!matcher.matches_file(Path::new("test_main.py"), None, false));
    assert!(matcher.matches_file(Path::new("é.txt"), None, false));
    assert!(matcher.matches_file(Path::new("🚀.txt"), None, false));
    assert!(!matcher.matches_file(Path::new("ab.txt"), None, false));
    assert!(!matcher.matches_classified_item(Path::new("build"), true, false));
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

#[test]
fn default_matcher_and_tag_prefilter_cover_all_tags_and_empty_criteria() {
    let def = PatternMatcher::default();
    assert!(def.matches_dir(Path::new("sub"), None));
    assert!(def.matches_classified_item(Path::new("sub"), true, false));

    let reg = TagRegistry::sample_registry();
    let empty = FilterCriteria::default();
    assert!(!can_skip_entry_by_tags(
        "app.py",
        false,
        false,
        Some(false),
        &empty,
        &reg,
        None
    ));

    let all_crit = FilterCriteria {
        include_tags: BTreeSet::from(["python".to_owned(), "rust".to_owned()]),
        exclude_tags: BTreeSet::new(),
        all_tags: true,
        shebang_filter: None,
    };
    assert!(can_skip_entry_by_tags(
        "app.py",
        false,
        false,
        Some(false),
        &all_crit,
        &reg,
        Some("text/x-python"),
    ));
}
