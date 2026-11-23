//! Property-based (`proptest`) suite for `findfmt_rs` natural version sort keys and gitignore globs (#585).

use std::cmp::Ordering;
use std::path::Path;

use _rust_ext::fuzz_entrypoints::fuzz_sort_and_gitignore_bytes;
use _rust_ext::gitignore::{
    GitignoreMatcher, compile_glob_matcher, is_active_gitignore_line, trim_gitignore_line,
};
use _rust_ext::sorting::{compare_natural, decimal_digit_value, natural_sort_key};
use proptest::prelude::*;

proptest! {
    #![proptest_config(ProptestConfig {
        cases: 256,
        failure_persistence: None,
        .. ProptestConfig::default()
    })]

    #[test]
    fn prop_natural_sort_total_order_axioms(
        a in "\\PC{0,48}",
        b in "\\PC{0,48}",
        c in "\\PC{0,48}",
        ignore_case in any::<bool>(),
    ) {
        // Reflexivity
        prop_assert_eq!(compare_natural(&a, &a, ignore_case), Ordering::Equal);

        // Antisymmetry
        let ab = compare_natural(&a, &b, ignore_case);
        let ba = compare_natural(&b, &a, ignore_case);
        prop_assert_eq!(ab, ba.reverse());

        // Transitivity on any sorted triple
        let mut triple = [&a, &b, &c];
        triple.sort_by(|x, y| compare_natural(x, y, ignore_case));
        let k0 = natural_sort_key(triple[0], ignore_case);
        let k1 = natural_sort_key(triple[1], ignore_case);
        let k2 = natural_sort_key(triple[2], ignore_case);
        prop_assert!(k0 <= k1);
        prop_assert!(k1 <= k2);
        prop_assert!(k0 <= k2);
    }

    #[test]
    fn prop_natural_sort_numeric_and_unicode_digit_monotonicity(
        prefix in "[a-zA-Z_]{1,8}",
        suffix in "\\.[a-z]{1,4}",
        n1 in 0_u64..1_000_000_u64,
        n2 in 0_u64..1_000_000_u64,
        big_len_a in 40_usize..80_usize,
        big_len_b in 81_usize..120_usize,
    ) {
        let s1 = format!("{prefix}{n1}{suffix}");
        let s2 = format!("{prefix}{n2}{suffix}");
        prop_assert_eq!(compare_natural(&s1, &s2, false), n1.cmp(&n2));

        // Arbitrary-precision digit runs beyond u128::MAX never overflow
        let huge_smaller = format!("{prefix}{}{suffix}", "9".repeat(big_len_a));
        let huge_larger = format!("{prefix}1{}{suffix}", "0".repeat(big_len_b));
        prop_assert_eq!(compare_natural(&huge_smaller, &huge_larger, false), Ordering::Less);
    }

    #[test]
    fn prop_unicode_decimal_digit_blocks_preserve_numeric_value(
        digit in 0_u8..=9_u8,
    ) {
        // Sample ASCII, Arabic-Indic, Extended Arabic-Indic, Devanagari, Fullwidth, Math Bold
        let bases: [u32; 6] = [0x0030, 0x0660, 0x06F0, 0x0966, 0xFF10, 0x1D7CE];
        for base in bases {
            let ch = char::from_u32(base + u32::from(digit)).expect("valid Unicode decimal scalar");
            prop_assert_eq!(decimal_digit_value(ch), Some(digit));
        }
    }

    #[test]
    fn prop_trim_gitignore_line_whitespace_and_escape_invariants(
        body in "[a-zA-Z0-9*?._/-]{0,32}",
        leading_spaces in 0_usize..=4_usize,
        slashes in 0_usize..=5_usize,
        trailing_spaces in 0_usize..=5_usize,
        crlf in prop_oneof![Just(""), Just("\n"), Just("\r\n")],
    ) {
        let raw = format!(
            "{}{}{}{}{}",
            " ".repeat(leading_spaces),
            body,
            "\\".repeat(slashes),
            " ".repeat(trailing_spaces),
            crlf,
        );
        let trimmed = trim_gitignore_line(&raw);
        prop_assert!(!trimmed.ends_with('\n'));
        prop_assert!(!trimmed.ends_with('\r'));

        if !body.is_empty() {
            prop_assert!(trimmed.starts_with(&" ".repeat(leading_spaces)));
            if trailing_spaces > 0 && slashes % 2 == 1 {
                // Exactly one escaped trailing space remains
                let expected = format!(
                    "{}{}{}\\ ",
                    " ".repeat(leading_spaces),
                    body,
                    "\\".repeat(slashes - 1),
                );
                prop_assert_eq!(trimmed, expected);
            } else {
                prop_assert!(!trimmed.ends_with(' '));
            }
        }
        let _ = is_active_gitignore_line(trimmed);
    }

    #[test]
    fn prop_gitignore_and_globset_never_panic_on_malformed_inputs(
        raw_rules in proptest::collection::vec(any::<u8>(), 0..=1024),
        candidate in "[\\PC/\\\\.]{0,64}",
        is_dir in any::<bool>(),
        case_insensitive in any::<bool>(),
    ) {
        let root = Path::new("/prop_repo");
        let (matcher, _errs) = GitignoreMatcher::from_bytes_lossy(root, &raw_rules);
        let _ = matcher.is_ignored(Path::new(&candidate), is_dir);
        let _ = matcher.is_ignored(&root.join(&candidate), is_dir);
        let _ = compile_glob_matcher(&candidate, case_insensitive);

        let sorted_keys = fuzz_sort_and_gitignore_bytes(&raw_rules);
        for pair in sorted_keys.windows(2) {
            prop_assert!(pair[0] <= pair[1]);
        }
    }

    #[test]
    fn prop_gitignore_negation_and_root_anchoring_semantics(
        stem in "[a-z][a-z0-9_]{1,12}",
        sub in "[a-z][a-z0-9_]{1,8}",
    ) {
        let root = Path::new("/repo");
        let whitelisted = format!("{stem}.gen");
        let anchored = format!("{stem}_anchored.tmp");
        let rules = format!("*.gen\n!{whitelisted}\n/{anchored}\n");
        let (matcher, errs) = GitignoreMatcher::from_text(root, &rules);
        prop_assert_eq!(errs, 0);
        prop_assert!(matcher.is_ignored(&root.join("other_item.gen"), false));
        prop_assert!(!matcher.is_ignored(&root.join(&whitelisted), false));
        prop_assert!(matcher.is_ignored(&root.join(&anchored), false));
        prop_assert!(!matcher.is_ignored(&root.join(&sub).join(&anchored), false));
    }
}
