//! `cargo-fuzz` target for shebang extraction, POSIX shlex tokenization, and header byte sniffing (#585).

#![no_main]
#![forbid(unsafe_code)]

use _rust_ext::fuzz_entrypoints::fuzz_shebang_and_header_bytes;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    let (_is_text, extracted, parsed) = fuzz_shebang_and_header_bytes(data);
    if data.starts_with(b"#!") {
        assert!(extracted.is_some());
    } else {
        assert!(extracted.is_none());
        assert!(parsed.is_empty());
    }
});
