//! Unit tests for `findfmt_rs::shebang` (#583, #590).

use super::*;

#[test]
fn extract_shebang_raw_line() {
    assert_eq!(
        extract_shebang_from_buffer(b"#!/usr/bin/env -S python3 -u\nprint(1)"),
        Some("#!/usr/bin/env -S python3 -u".to_owned()),
    );
    assert_eq!(extract_shebang_from_buffer(b"plain text\n"), None);
}

#[test]
fn parse_shebang_env_quotes_and_nix_shell() {
    assert_eq!(
        parse_shebang_tokens(b"#!/usr/bin/env -S python3 -u\n"),
        vec!["python3", "-u"],
    );
    assert_eq!(parse_shebang_tokens(b"#!/usr/bin/env node\n"), vec!["node"]);
    assert_eq!(
        parse_shebang_tokens(b"#!\"/opt/my python/bin/python3.12\" -O\n"),
        vec!["/opt/my python/bin/python3.12", "-O"],
    );
    assert_eq!(
        parse_shebang_tokens(b"#!/bin/sh '' arg\n"),
        vec!["/bin/sh", "", "arg"],
    );
    assert_eq!(
        parse_shebang_tokens(b"#!/bin/sh 'unclosed\n"),
        vec!["/bin/sh", "'unclosed"],
    );
    assert_eq!(
        parse_shebang_tokens(b"#!/usr/bin/python3 \xff\n"),
        Vec::<String>::new(),
    );
    assert_eq!(
        parse_shebang_tokens(b"#!/usr/bin/python3 \x01\n"),
        Vec::<String>::new(),
    );

    assert_eq!(
        parse_shebang_tokens(b"#!\"/opt/my\\\"dir\\\\bin\\py\" \\/arg\\ one"),
        vec!["/opt/my\"dir\\bin\\py", "/arg one"],
    );
    assert_eq!(
        parse_shebang_tokens(b"#!   /bin/sh   foo'bar'   \n"),
        vec!["/bin/sh", "foobar"],
    );
    assert_eq!(parse_shebang_tokens(b"plain text"), Vec::<String>::new());
    let nix = b"#! /usr/bin/env nix-shell\n#! single\n#! nix-shell -i bash -p bash\necho ok\n";
    assert_eq!(parse_shebang_tokens(nix), vec!["bash"]);
    assert_eq!(
        parse_shebang_tokens(b"#! /usr/bin/env nix-shell\n#!\xff\n"),
        vec!["nix-shell"],
    );
    assert_eq!(
        parse_shebang_tokens(b"#! /usr/bin/env nix-shell\n#!\x01\n"),
        vec!["nix-shell"],
    );
}
