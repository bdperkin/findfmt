//! Shebang line extraction and `identify`-compatible interpreter token parsing (#583).

fn is_py_whitespace(c: char) -> bool {
    c.is_whitespace() || matches!(c, '\x1c'..='\x1f' | '\u{0085}')
}

/// Trim characters matching Python's `str.strip()` semantics (Unicode whitespace + ASCII FS/GS/RS/US/NEL).
#[must_use]
pub fn py_strip(input: &str) -> &str {
    input.trim_matches(is_py_whitespace)
}

/// Trim trailing characters matching Python's `str.rstrip()` semantics.
#[must_use]
pub fn py_rstrip(input: &str) -> &str {
    input.trim_end_matches(is_py_whitespace)
}

/// Extract the raw `#!` shebang header line from a byte buffer (`extract_shebang_from_buffer` parity).
#[must_use]
pub fn extract_shebang_from_buffer(buffer: &[u8]) -> Option<String> {
    if !buffer.starts_with(b"#!") {
        return None;
    }
    let first_line = buffer.split(|&b| b == b'\n').next().unwrap_or(buffer);
    let decoded = String::from_utf8_lossy(first_line);
    Some(py_strip(&decoded).to_owned())
}

fn is_python_printable_ascii(ch: char) -> bool {
    matches!(ch, ' '..='~' | '\t' | '\n' | '\r' | '\x0b' | '\x0c')
}

fn is_shlex_whitespace(ch: char) -> bool {
    matches!(ch, ' ' | '\t' | '\r' | '\n')
}

/// Parse a shebang command line using POSIX `shlex.split` rules, falling back to whitespace split.
#[must_use]
pub fn shebang_split(line: &str) -> Vec<String> {
    posix_shlex_split(line).unwrap_or_else(|()| {
        line.split_whitespace()
            .map(std::borrow::ToOwned::to_owned)
            .collect()
    })
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum ShlexState {
    Whitespace,
    Word,
    Quote(char),
    Escape { prev_quote: Option<char> },
}

fn posix_shlex_split(line: &str) -> Result<Vec<String>, ()> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut quoted = false;
    let mut state = ShlexState::Whitespace;

    for ch in line.chars() {
        match state {
            ShlexState::Whitespace => {
                if is_shlex_whitespace(ch) {
                    // Remain in leading/inter-token whitespace.
                } else if ch == '\\' {
                    state = ShlexState::Escape { prev_quote: None };
                } else if ch == '\'' || ch == '"' {
                    state = ShlexState::Quote(ch);
                } else {
                    current.push(ch);
                    state = ShlexState::Word;
                }
            }
            ShlexState::Word => {
                if is_shlex_whitespace(ch) {
                    state = ShlexState::Whitespace;
                    tokens.push(std::mem::take(&mut current));
                    quoted = false;
                } else if ch == '\'' || ch == '"' {
                    state = ShlexState::Quote(ch);
                } else if ch == '\\' {
                    state = ShlexState::Escape { prev_quote: None };
                } else {
                    current.push(ch);
                }
            }
            ShlexState::Quote(q) => {
                quoted = true;
                if ch == q {
                    state = ShlexState::Word;
                } else if ch == '\\' && q == '"' {
                    state = ShlexState::Escape {
                        prev_quote: Some(q),
                    };
                } else {
                    current.push(ch);
                }
            }
            ShlexState::Escape { prev_quote } => {
                if let Some(q) = prev_quote {
                    if ch != '\\' && ch != q {
                        current.push('\\');
                    }
                    current.push(ch);
                    state = ShlexState::Quote(q);
                } else {
                    current.push(ch);
                    state = ShlexState::Word;
                }
            }
        }
    }

    match state {
        ShlexState::Quote(_) | ShlexState::Escape { .. } => Err(()),
        ShlexState::Whitespace | ShlexState::Word => {
            if !current.is_empty() || quoted {
                tokens.push(current);
            }
            Ok(tokens)
        }
    }
}

fn read_line_slice(input: &[u8]) -> (&[u8], &[u8]) {
    match input.iter().position(|&b| b == b'\n') {
        Some(idx) => (&input[..=idx], &input[idx + 1..]),
        None => (input, &[]),
    }
}

/// Parse interpreter command tokens from a `#!` buffer (`identify.identify.parse_shebang` parity).
///
/// Supports `#!/usr/bin/env -S ...`, `#!/usr/bin/env ...`, quoted paths, and multi-line `nix-shell -i`.
#[must_use]
pub fn parse_shebang_tokens(buffer: &[u8]) -> Vec<String> {
    let Some(after_magic) = buffer.strip_prefix(b"#!") else {
        return Vec::new();
    };
    let (first_line_bytes, mut rest) = read_line_slice(after_magic);
    let Ok(first_line) = std::str::from_utf8(first_line_bytes) else {
        return Vec::new();
    };
    if !first_line.chars().all(is_python_printable_ascii) {
        return Vec::new();
    }

    let mut cmd = shebang_split(py_strip(first_line));
    if cmd.len() >= 2 && cmd[0] == "/usr/bin/env" && cmd[1] == "-S" {
        cmd.drain(..2);
    } else if !cmd.is_empty() && cmd[0] == "/usr/bin/env" {
        cmd.drain(..1);
    }

    if cmd.len() == 1 && cmd[0] == "nix-shell" {
        while let Some(next_after_magic) = rest.strip_prefix(b"#!") {
            let (next_line_bytes, remaining) = read_line_slice(next_after_magic);
            rest = remaining;
            let Ok(next_line) = std::str::from_utf8(next_line_bytes) else {
                return cmd;
            };
            if !next_line.chars().all(is_python_printable_ascii) {
                return cmd;
            }
            let line_tokens = shebang_split(py_strip(next_line));
            if line_tokens.len() >= 2 {
                for i in 0..(line_tokens.len() - 1) {
                    if line_tokens[i] == "-i" {
                        cmd = vec![line_tokens[i + 1].clone()];
                    }
                }
            }
        }
    }

    cmd
}

#[cfg(test)]
#[path = "shebang_tests.rs"]
mod tests;
