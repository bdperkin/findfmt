//! Non-blocking header inspection and binary-vs-text byte detection (#583).

#[cfg(not(unix))]
use std::fs;
use std::fs::{File, Metadata, OpenOptions};
use std::io::{self, Read};
use std::path::Path;

/// Maximum header bytes read per regular file (`src/findfmt/classifier.py` parity).
pub const MAX_HEADER_BYTES: usize = 2048;

/// Maximum prefix bytes inspected for libmagic-style binary vs. text detection.
pub const TEXT_CHECK_BYTES: usize = 1024;

/// Result of opening a candidate file and inspecting its file-descriptor metadata.
#[derive(Debug)]
pub struct HeaderInspection {
    /// Bytes read from the start of the file (empty when non-regular).
    pub buffer: Vec<u8>,
    /// File-descriptor `fstat` metadata when `open` and `metadata()` succeeded.
    pub opened_meta: Option<Metadata>,
}

/// Read up to `max_bytes` from `path` without blocking on FIFOs, sockets, or devices.
///
/// Opens with `O_NONBLOCK` on Unix and verifies `meta.file_type().is_file()` via
/// `fstat` on the open descriptor before reading any bytes, preventing TOCTOU
/// FIFO/named-pipe swap hangs (#363, #583).
#[must_use]
pub fn read_header_nonblocking(path: &Path, max_bytes: usize) -> Option<HeaderInspection> {
    read_header_with_hook(path, max_bytes, || {})
}

/// Internal testable variant allowing a pre-open hook to simulate TOCTOU swaps.
pub fn read_header_with_hook<F>(
    path: &Path,
    max_bytes: usize,
    before_open: F,
) -> Option<HeaderInspection>
where
    F: FnOnce(),
{
    before_open();
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;

        let file = OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NONBLOCK)
            .open(path)
            .ok()?;
        inspect_open_file(file, max_bytes)
    }
    #[cfg(not(unix))]
    {
        let target_meta = fs::metadata(path).ok()?;
        if !target_meta.file_type().is_file() {
            return Some(HeaderInspection {
                buffer: Vec::new(),
                opened_meta: Some(target_meta),
            });
        }
        let file = OpenOptions::new().read(true).open(path).ok()?;
        inspect_open_file(file, max_bytes)
    }
}

pub(crate) fn read_bounded_nonblocking<R: Read>(
    reader: &mut R,
    max_bytes: usize,
) -> Option<Vec<u8>> {
    let mut buffer = vec![0_u8; max_bytes];
    let mut total = 0_usize;
    while total < max_bytes {
        match reader.read(&mut buffer[total..]) {
            Ok(0) => break,
            Ok(n) => total += n,
            Err(err) if err.kind() == io::ErrorKind::Interrupted => {}
            Err(err) if err.kind() == io::ErrorKind::WouldBlock => break,
            Err(_) => return None,
        }
    }
    buffer.truncate(total);
    Some(buffer)
}

fn inspect_open_file(mut file: File, max_bytes: usize) -> Option<HeaderInspection> {
    let meta = file.metadata().ok()?;
    if !meta.file_type().is_file() {
        return Some(HeaderInspection {
            buffer: Vec::new(),
            opened_meta: Some(meta),
        });
    }
    let buffer = read_bounded_nonblocking(&mut file, max_bytes)?;
    Some(HeaderInspection {
        buffer,
        opened_meta: Some(meta),
    })
}

/// Return `true` when the first `1024` bytes of `buffer` contain only `identify` text bytes.
///
/// Matches `identify.identify.is_text`: allowed bytes are `{7..=13, 27, 0x20..=0x7E, 0x80..=0xFF}`.
#[must_use]
pub fn is_text_buffer(buffer: &[u8]) -> bool {
    let limit = buffer.len().min(TEXT_CHECK_BYTES);
    buffer[..limit]
        .iter()
        .all(|&b| matches!(b, 7..=13 | 27 | 0x20..=0x7E | 0x80..=0xFF))
}

#[cfg(test)]
#[path = "header_tests.rs"]
mod tests;
