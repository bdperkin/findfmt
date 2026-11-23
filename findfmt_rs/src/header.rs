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
        let lst = fs::symlink_metadata(path).ok()?;
        if !lst.file_type().is_file() && !lst.file_type().is_symlink() {
            return Some(HeaderInspection {
                buffer: Vec::new(),
                opened_meta: Some(lst),
            });
        }
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

fn inspect_open_file(mut file: File, max_bytes: usize) -> Option<HeaderInspection> {
    let meta = file.metadata().ok()?;
    if !meta.file_type().is_file() {
        return Some(HeaderInspection {
            buffer: Vec::new(),
            opened_meta: Some(meta),
        });
    }

    let mut buffer = vec![0_u8; max_bytes];
    let mut total = 0_usize;
    while total < max_bytes {
        match file.read(&mut buffer[total..]) {
            Ok(0) => break,
            Ok(n) => total += n,
            Err(err) if err.kind() == io::ErrorKind::Interrupted => continue,
            Err(err) if err.kind() == io::ErrorKind::WouldBlock => break,
            Err(_) => return None,
        }
    }
    buffer.truncate(total);
    Some(HeaderInspection {
        buffer,
        opened_meta: Some(meta),
    })
}

/// Return `true` when the first `1024` bytes of `buffer` contain only `identify` text bytes.
///
/// Matches `identify.identify.is_text`: allowed bytes are `{7..=13, 27, 0x20..=0x7E, 0x80..=0xFF}`.
pub fn is_text_buffer(buffer: &[u8]) -> bool {
    let limit = buffer.len().min(TEXT_CHECK_BYTES);
    buffer[..limit]
        .iter()
        .all(|&b| matches!(b, 7..=13 | 27 | 0x20..=0x7E | 0x80..=0xFF))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn unique_temp_dir(label: &str) -> std::path::PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |d| d.as_nanos());
        let dir = env::temp_dir().join(format!(
            "findfmt_rs_hdr_{label}_{}_{nanos}",
            std::process::id()
        ));
        fs::create_dir_all(&dir).expect("create temp dir");
        dir
    }

    #[test]
    fn text_vs_binary_detection_matches_identify() {
        assert!(is_text_buffer(b""));
        assert!(is_text_buffer(b"hello world\n\t\r\x1b[31mred\x1b[0m"));
        assert!(is_text_buffer("héllo 世界\n".as_bytes()));
        assert!(!is_text_buffer(b"hello\x00world"));
        assert!(!is_text_buffer(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"));
        assert!(!is_text_buffer(b"\x7fELF\x02\x01\x01\x00"));

        let mut nul_past_1kb = vec![b'a'; 1024];
        nul_past_1kb.push(0);
        assert!(is_text_buffer(&nul_past_1kb));
    }

    #[test]
    fn regular_and_missing_header_reads() {
        let dir = unique_temp_dir("reg");
        let file_path = dir.join("sample.py");
        fs::write(&file_path, b"#!/usr/bin/env python3\nprint(1)\n").expect("write sample");

        let res = read_header_nonblocking(&file_path, MAX_HEADER_BYTES).expect("header read");
        assert!(res.opened_meta.as_ref().is_some_and(|m| m.is_file()));
        assert!(res.buffer.starts_with(b"#!/usr/bin/env python3"));

        assert!(read_header_nonblocking(&dir.join("missing.py"), MAX_HEADER_BYTES).is_none());
        let _ = fs::remove_dir_all(&dir);
    }

    #[cfg(unix)]
    #[test]
    fn fifo_swap_never_blocks_and_reports_non_regular() {
        use std::ffi::CString;
        use std::os::unix::ffi::OsStrExt;
        use std::os::unix::fs::FileTypeExt;

        let dir = unique_temp_dir("fifo");
        let pipe_path = dir.join("swapped.pipe");
        fs::write(&pipe_path, b"regular initial content\n").expect("write regular");

        let swap_target = pipe_path.clone();
        let res = read_header_with_hook(&pipe_path, MAX_HEADER_BYTES, move || {
            fs::remove_file(&swap_target).expect("unlink regular");
            let c_path = CString::new(swap_target.as_os_str().as_bytes()).expect("cstring");
            let rc = {
                // Create POSIX FIFO via mkfifo CLI fallback if needed; test uses std process `mkfifo`
                let _ = c_path;
                std::process::Command::new("mkfifo")
                    .arg(&swap_target)
                    .status()
                    .map_or(-1, |s| if s.success() { 0 } else { -1 })
            };
            assert_eq!(rc, 0, "mkfifo must succeed");
        })
        .expect("non-blocking open of FIFO");

        assert!(res.buffer.is_empty());
        let meta = res.opened_meta.expect("fstat metadata present");
        assert!(!meta.file_type().is_file());
        assert!(meta.file_type().is_fifo());
        let _ = fs::remove_dir_all(&dir);
    }
}
