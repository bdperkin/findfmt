//! Property-based (`proptest`) suite for `findfmt_rs` header, shebang, MIME, and tag classification (#585).

use std::collections::BTreeSet;

use _rust_ext::classifier::{RawClassifyInput, classify_one_nogil};
use _rust_ext::fuzz_entrypoints::{fuzz_classifier_and_tags_bytes, fuzz_shebang_and_header_bytes};
use _rust_ext::header::{TEXT_CHECK_BYTES, is_text_buffer};
use _rust_ext::metadata::format_filemode;
use _rust_ext::mime::py_splitext;
use _rust_ext::shebang::{
    extract_shebang_from_buffer, parse_shebang_tokens, py_strip, shebang_split,
};
use _rust_ext::tags::TagRegistry;
use proptest::prelude::*;

proptest! {
    #![proptest_config(ProptestConfig {
        cases: 256,
        failure_persistence: None,
        .. ProptestConfig::default()
    })]

    #[test]
    fn prop_is_text_buffer_boundary_and_control_bytes(
        prefix in proptest::collection::vec(any::<u8>(), 0..=1536),
        tail in proptest::collection::vec(any::<u8>(), 0..=512),
    ) {
        let base_is_text = is_text_buffer(&prefix);
        if prefix.is_empty() {
            prop_assert!(base_is_text);
        }
        let inspected_len = prefix.len().min(TEXT_CHECK_BYTES);
        let has_disallowed = prefix[..inspected_len]
            .iter()
            .any(|&b| !matches!(b, 7..=13 | 27 | 0x20..=0x7E | 0x80..=0xFF));
        prop_assert_eq!(base_is_text, !has_disallowed);

        if prefix.len() >= TEXT_CHECK_BYTES {
            let mut extended = prefix;
            extended.extend_from_slice(&tail);
            prop_assert_eq!(is_text_buffer(&extended), base_is_text);
        }
    }

    #[test]
    fn prop_shebang_extraction_and_tokenization_never_panic(
        raw in proptest::collection::vec(any::<u8>(), 0..=2048),
    ) {
        let (_is_txt, extracted, tokens) = fuzz_shebang_and_header_bytes(&raw);
        if raw.starts_with(b"#!") {
            let line = extracted.expect("buffer starting with #! must extract shebang");
            prop_assert!(!line.contains('\n'));
            prop_assert_eq!(py_strip(&line), line.as_str());
        } else {
            prop_assert!(extracted.is_none());
            prop_assert!(tokens.is_empty());
        }
    }

    #[test]
    fn prop_structured_shebang_env_quotes_and_nix_shell(
        use_env in any::<bool>(),
        use_split_flag in any::<bool>(),
        interp in "[a-zA-Z0-9_./-]{1,24}",
        arg in "[a-zA-Z0-9_=-]{0,16}",
        quote_choice in 0_u8..4_u8,
    ) {
        let formatted_interp = match quote_choice {
            1 => format!("'{interp}'"),
            2 => format!("\"{interp}\""),
            3 => format!("'{interp}"), // intentionally unclosed quote
            _ => interp.clone(),
        };
        let mut line = String::from("#!");
        if use_env {
            line.push_str("/usr/bin/env ");
            if use_split_flag {
                line.push_str("-S ");
            }
        }
        line.push_str(&formatted_interp);
        if !arg.is_empty() {
            line.push(' ');
            line.push_str(&arg);
        }
        line.push('\n');

        let extracted = extract_shebang_from_buffer(line.as_bytes());
        prop_assert!(extracted.is_some());
        let tokens = parse_shebang_tokens(line.as_bytes());
        if quote_choice != 3 {
            prop_assert!(!tokens.is_empty());
            prop_assert_eq!(&tokens[0], &interp);
        }
        let _ = shebang_split(&line);
    }

    #[test]
    fn prop_splitext_mime_and_tag_lookup_invariants(
        raw_path in "[\\PC/\\\\:.;,?=#]{0,96}",
    ) {
        let (stem, ext) = py_splitext(&raw_path);
        let joined = format!("{stem}{ext}");
        prop_assert_eq!(joined.as_str(), raw_path.as_str());
        if !ext.is_empty() {
            prop_assert!(ext.starts_with('.'));
            prop_assert!(!ext[1..].contains('.'));
        }

        let reg = TagRegistry::sample_registry();
        let _ = reg.tags_from_filename(&raw_path);
        let _ = reg.tags_from_interpreter(&raw_path);
        let mime = reg.guess_mime_type(&raw_path);
        if let Some(ref mt) = mime {
            prop_assert!(mt.contains('/'));
        }
    }

    #[test]
    fn prop_filemode_and_fuzz_classifier_harness(
        mode in any::<u32>(),
        payload in proptest::collection::vec(any::<u8>(), 0..=512),
    ) {
        let formatted = format_filemode(mode);
        prop_assert_eq!(formatted.len(), 10);
        prop_assert!(formatted.is_ascii());

        let (reconstructed, mode_len, tags) = fuzz_classifier_and_tags_bytes(&payload);
        prop_assert!(reconstructed);
        prop_assert_eq!(mode_len, 10);
        if tags.contains("file") {
            let has_text = tags.contains("text");
            let has_bin = tags.contains("binary");
            prop_assert!(has_text ^ has_bin);

            let has_exec = tags.contains("executable");
            let has_non_exec = tags.contains("non-executable");
            prop_assert!(has_exec ^ has_non_exec);
        }
    }

    #[test]
    fn prop_missing_file_classify_one_nogil_never_panics(
        name in "[a-zA-Z0-9._-]{0,32}",
        follow in any::<bool>(),
        accum in proptest::option::of(any::<u64>()),
    ) {
        let reg = TagRegistry::sample_registry();
        let missing = std::env::temp_dir().join(format!("findfmt_nonexistent_{}_{name}", std::process::id()));
        let input = RawClassifyInput {
            path: missing,
            str_path: name.clone(),
            filename: name,
            follow_symlinks: follow,
            accumulated_size: accum,
            pre_stat: Some((false, false, false, 0, None)),
            pre_guessed_mime: None,
        };
        let out = classify_one_nogil(&input, &reg, None);
        prop_assert!(!out.exists);
        let _: BTreeSet<String> = out.tags;
    }
}
