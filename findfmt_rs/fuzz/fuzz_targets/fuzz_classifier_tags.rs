//! `cargo-fuzz` target for MIME `splitext`, tag tables, mode formatting, and GIL-free classification (#585).

#![no_main]
#![forbid(unsafe_code)]

use _rust_ext::fuzz_entrypoints::fuzz_classifier_and_tags_bytes;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    let (reconstructed, mode_len, tags) = fuzz_classifier_and_tags_bytes(data);
    assert!(reconstructed);
    assert_eq!(mode_len, 10);
    if tags.contains("file") {
        assert!(tags.contains("text") ^ tags.contains("binary"));
        assert!(tags.contains("executable") ^ tags.contains("non-executable"));
    }
});
