//! Unit tests for `findfmt_rs::tags` (#583).

use super::*;

#[test]
fn splitext_tag_and_data_uri_lookup_parity() {
    assert_eq!(py_splitext(".bashrc"), (".bashrc".into(), String::new()));
    assert_eq!(py_splitext(".hidden.py"), (".hidden".into(), ".py".into()));
    assert_eq!(
        py_splitext("archive.tar.gz"),
        ("archive.tar".into(), ".gz".into())
    );

    let reg = TagRegistry::builtin_for_tests();
    assert!(reg.tags_from_filename("Dockerfile.prod").contains("dockerfile"));
    assert!(reg.tags_from_filename("app.PY").contains("python"));
    assert!(reg.tags_from_interpreter("/usr/bin/python3.12.1").contains("python3"));
    assert_eq!(
        reg.guess_mime_type("bundle.tgz"),
        Some("application/x-tar".into())
    );
    assert_eq!(
        reg.guess_mime_type("data:,hello"),
        Some("text/plain".into())
    );
    assert_eq!(
        reg.guess_mime_type("data:image/png;base64,iVBORw0KGgo="),
        Some("image/png".into())
    );
    assert_eq!(reg.guess_mime_type("data:hello"), None);
    assert_eq!(
        reg.guess_mime_type("https://example.com/pkg/app.py?v=1#top"),
        Some("text/x-python".into())
    );
    assert_eq!(
        reg.guess_mime_type("http:report.py;v=1"),
        Some("text/x-python".into())
    );

    let mut case_reg = reg;
    case_reg
        .mime_types_strict
        .insert(".PY".into(), "text/x-upper-py".into());
    case_reg
        .mime_types_strict
        .insert(String::new(), "application/x-extensionless".into());
    assert_eq!(
        case_reg.guess_mime_type("report.PY"),
        Some("text/x-python".into())
    );
    assert_eq!(
        case_reg.guess_mime_type("README"),
        Some("application/x-extensionless".into())
    );
}

#[test]
fn filter_criteria_evaluation_and_directory_tag_exemption() {
    let tags: BTreeSet<String> = ["file", "python", "text"]
        .into_iter()
        .map(String::from)
        .collect();
    let mut crit = FilterCriteria {
        include_tags: ["python", "text"].into_iter().map(String::from).collect(),
        exclude_tags: BTreeSet::new(),
        all_tags: true,
        shebang_filter: Some("python3".into()),
    };
    assert!(crit.is_active());
    assert!(crit.matches(&tags, Some("#!/usr/bin/env python3"), false));
    assert!(!crit.matches(&tags, None, false));
    crit.exclude_tags.insert("text".into());
    assert!(!crit.matches(&tags, Some("#!/usr/bin/env python3"), false));
    assert!(crit.matches(&tags, None, true));

    let dir_tagged: BTreeSet<String> = ["file", "directory", "mime:directory/x-vcard"]
        .into_iter()
        .map(String::from)
        .collect();
    assert!(crit.matches(&dir_tagged, None, false));
}
