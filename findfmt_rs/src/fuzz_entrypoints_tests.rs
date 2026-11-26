//! Unit tests for `findfmt_rs::fuzz_entrypoints` (#585, #590).

use std::path::Path;

use super::*;

#[test]
fn fuzz_entrypoints_handle_normal_and_missing_scratch_base() {
    let (is_text, sb, toks) = fuzz_shebang_and_header_bytes(b"#!/usr/bin/env python3\nprint(1)\n");
    assert!(is_text);
    assert!(sb.is_some());
    assert_eq!(toks, vec!["python3"]);

    let (recon, mode_len, _) = fuzz_classifier_and_tags_bytes(b"app.py#!/bin/sh\n");
    assert!(recon);
    assert_eq!(mode_len, 10);
    let (_, alt_mode_len, _) = fuzz_classifier_and_tags_bytes(b"\x01\x01\x01app.py");
    assert_eq!(alt_mode_len, 10);

    let keys = fuzz_sort_and_gitignore_bytes(b"*.log\n\0a2\na10\n");
    assert_ne!(keys.len(), 0);

    let missing_base = Path::new("/nonexistent_findfmt_scratch_parent/missing");
    assert!(create_private_scratch_dir_in(missing_base).is_none());
    let (_, fallback_mode_len, _) = fuzz_classifier_and_tags_in(b"...", missing_base);
    assert_eq!(fallback_mode_len, 10);
    let fallback_keys = fuzz_sort_and_gitignore_in(b"*.pyc\na1\na2", missing_base);
    assert_ne!(fallback_keys.len(), 0);
}
