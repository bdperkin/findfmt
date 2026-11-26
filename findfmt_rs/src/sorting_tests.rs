//! Unit tests for `findfmt_rs::sorting` (#582, #590).

use super::*;

#[test]
fn natural_sort_handles_ascii_leading_zeros_unicode_digits_surrogates_and_sigma() {
    assert_eq!(
        compare_natural("item2.py", "item10.py", false),
        Ordering::Less
    );
    assert_eq!(
        compare_natural("item02.py", "item2.py", false),
        Ordering::Less
    );
    assert_eq!(compare_natural("000", "0", false), Ordering::Greater);
    assert_eq!(
        compare_natural("1_first", "a_second", false),
        Ordering::Less
    );
    assert_eq!(
        compare_natural("uni_\u{0662}.txt", "uni_\u{0661}\u{0660}.txt", false),
        Ordering::Less,
    );
    assert_eq!(compare_natural("ΟΣ", "Οςa", true), Ordering::Less);

    assert!(SortChunk::Digit("1".into()) < SortChunk::Text("a".into()));
    assert!(SortChunkU32::Digit("1".into()) < SortChunkU32::Text(vec![97]));
    assert!(SortChunkU32::Text(vec![97]) > SortChunkU32::Digit("1".into()));

    assert_eq!(decimal_digit_value_for_unicode('\u{00A0}', 16), None);
    assert_eq!(decimal_digit_value_for_unicode('\u{11F52}', 14), None);
    assert_eq!(decimal_digit_value_for_unicode('\u{11F52}', 15), Some(2));

    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;
        let k_ff = natural_sort_key_osstr(OsStr::from_bytes(b"\xff_v2"), false, 16);
        let k_pua = natural_sort_key_osstr(OsStr::new("\u{e000}_v2"), false, 16);
        assert!(k_ff < k_pua);

        let key_ignore_case = natural_sort_key_osstr(OsStr::from_bytes(b"Abc\xff12"), true, 16);
        let key_exact_case = natural_sort_key_osstr(OsStr::from_bytes(b"Abc\xff12"), false, 16);
        assert_ne!(key_ignore_case, key_exact_case);
    }
}
