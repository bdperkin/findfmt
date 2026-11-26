//! Unit tests for `findfmt_rs::header` (#583, #590).

use std::collections::VecDeque;
use std::env;
use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

use super::*;

struct ScriptedReader {
    steps: VecDeque<io::Result<Vec<u8>>>,
}

impl Read for ScriptedReader {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        match self.steps.pop_front() {
            Some(Ok(chunk)) => {
                let n = chunk.len().min(buf.len());
                buf[..n].copy_from_slice(&chunk[..n]);
                Ok(n)
            }
            Some(Err(err)) => Err(err),
            None => Ok(0),
        }
    }
}

fn unique_temp_dir(label: &str) -> io::Result<std::path::PathBuf> {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    let dir = env::temp_dir().join(format!(
        "findfmt_rs_hdr_{label}_{}_{nanos}",
        std::process::id()
    ));
    fs::create_dir_all(&dir)?;
    Ok(dir)
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
fn bounded_reader_handles_interrupted_wouldblock_and_fatal_errors() {
    let mut retry_reader = ScriptedReader {
        steps: VecDeque::from([
            Err(io::Error::from(io::ErrorKind::Interrupted)),
            Ok(b"ab".to_vec()),
            Err(io::Error::from(io::ErrorKind::WouldBlock)),
        ]),
    };
    assert_eq!(
        read_bounded_nonblocking(&mut retry_reader, 16),
        Some(b"ab".to_vec())
    );

    let mut fatal_reader = ScriptedReader {
        steps: VecDeque::from([Err(io::Error::other("io failure"))]),
    };
    assert_eq!(read_bounded_nonblocking(&mut fatal_reader, 16), None);
}

#[test]
fn regular_and_missing_header_reads() -> Result<(), Box<dyn std::error::Error>> {
    let dir = unique_temp_dir("reg")?;
    let file_path = dir.join("sample.py");
    fs::write(&file_path, b"#!/usr/bin/env python3\nprint(1)\n")?;

    let res = read_header_nonblocking(&file_path, MAX_HEADER_BYTES).ok_or("header read")?;
    assert!(res.opened_meta.as_ref().is_some_and(Metadata::is_file));
    assert!(res.buffer.starts_with(b"#!/usr/bin/env python3"));

    let dir_res = read_header_nonblocking(&dir, MAX_HEADER_BYTES).ok_or("dir header")?;
    assert_eq!(dir_res.buffer.len(), 0);
    assert!(dir_res.opened_meta.as_ref().is_some_and(Metadata::is_dir));

    assert!(read_header_nonblocking(&dir.join("missing.py"), MAX_HEADER_BYTES).is_none());
    let _ = fs::remove_dir_all(&dir);
    Ok(())
}

#[cfg(unix)]
#[test]
fn fifo_swap_never_blocks_and_reports_non_regular() -> Result<(), Box<dyn std::error::Error>> {
    use std::os::unix::fs::FileTypeExt;

    let dir = unique_temp_dir("fifo")?;
    let pipe_path = dir.join("swapped.pipe");
    fs::write(&pipe_path, b"regular initial content\n")?;

    let swap_target = pipe_path.clone();
    let res = read_header_with_hook(&pipe_path, MAX_HEADER_BYTES, move || {
        let removed = fs::remove_file(&swap_target);
        assert!(removed.is_ok(), "unlink regular must succeed");
        let rc = std::process::Command::new("mkfifo")
            .arg(&swap_target)
            .status()
            .map_or(-1, |s| if s.success() { 0 } else { -1 });
        assert_eq!(rc, 0, "mkfifo must succeed");
    })
    .ok_or("non-blocking open of FIFO")?;

    assert_eq!(res.buffer, b"");
    let meta = res.opened_meta.ok_or("fstat metadata present")?;
    assert!(!meta.file_type().is_file());
    assert!(meta.file_type().is_fifo());
    let _ = fs::remove_dir_all(&dir);
    Ok(())
}
