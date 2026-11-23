//! `cargo-fuzz` target for `.gitignore` line trimming, malformed globs, and natural version sorting (#585).

#![no_main]
#![forbid(unsafe_code)]

use _rust_ext::fuzz_entrypoints::fuzz_sort_and_gitignore_bytes;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    let sorted_keys = fuzz_sort_and_gitignore_bytes(data);
    for pair in sorted_keys.windows(2) {
        assert!(pair[0] <= pair[1]);
    }
});
