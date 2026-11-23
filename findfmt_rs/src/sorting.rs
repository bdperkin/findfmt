//! Natural version sort key tokenization with Unicode `Decimal_Number` and PEP 383 parity (#582, #585).

use std::cmp::Ordering;
use std::ffi::OsStr;

use crate::walker_types::surrogateescape_codepoints;

/// Sorted Unicode 16 `Decimal_Number` block base codepoints (`zero ..= zero + 9`).
///
/// Matches Python's `re.compile(r"(\d+)")` and `str.isdecimal()` across all 76 Unicode decimal scripts.
const DECIMAL_ZERO_BASES: [u32; 76] = [
    0x00030, 0x00660, 0x006F0, 0x007C0, 0x00966, 0x009E6, 0x00A66, 0x00AE6, 0x00B66, 0x00BE6,
    0x00C66, 0x00CE6, 0x00D66, 0x00DE6, 0x00E50, 0x00ED0, 0x00F20, 0x01040, 0x01090, 0x017E0,
    0x01810, 0x01946, 0x019D0, 0x01A80, 0x01A90, 0x01B50, 0x01BB0, 0x01C40, 0x01C50, 0x0A620,
    0x0A8D0, 0x0A900, 0x0A9D0, 0x0A9F0, 0x0AA50, 0x0ABF0, 0x0FF10, 0x104A0, 0x10D30, 0x10D40,
    0x11066, 0x110F0, 0x11136, 0x111D0, 0x112F0, 0x11450, 0x114D0, 0x11650, 0x116C0, 0x116D0,
    0x116DA, 0x11730, 0x118E0, 0x11950, 0x11BF0, 0x11C50, 0x11D50, 0x11DA0, 0x11F50, 0x16130,
    0x16A60, 0x16AC0, 0x16B50, 0x16D70, 0x1CCF0, 0x1D7CE, 0x1D7D8, 0x1D7E2, 0x1D7EC, 0x1D7F6,
    0x1E140, 0x1E2F0, 0x1E4F0, 0x1E5F1, 0x1E950, 0x1FBF0,
];

/// Return the minimum Unicode major version where decimal block `base` was introduced.
#[inline]
const fn block_min_unicode_major(base: u32) -> u8 {
    match base {
        // Added in Unicode 15.0 (Python 3.12+): Kawi, Nag Mundari
        0x11F50 | 0x1E4F0 => 15,
        // Added in Unicode 16.0 (Python 3.14+): Garay, Myanmar Pao, Eastern Pwo Karen,
        // Sunuwar, Gurung Khema, Kirat Rai, Outlined, Ol Onal
        0x10D40 | 0x116D0 | 0x116DA | 0x11BF0 | 0x16130 | 0x16D70 | 0x1CCF0 | 0x1E5F1 => 16,
        _ => 14,
    }
}

/// Return the decimal value (`0..=9`) when `ch` belongs to Unicode `Decimal_Number` at `unicode_major`.
#[inline]
pub fn decimal_digit_value_for_unicode(ch: char, unicode_major: u8) -> Option<u8> {
    if ch.is_ascii_digit() {
        return Some((ch as u8) - b'0');
    }
    if ch.is_ascii() {
        return None;
    }
    let cp = u32::from(ch);
    let idx = DECIMAL_ZERO_BASES.partition_point(|&base| base <= cp);
    if idx == 0 {
        return None;
    }
    let base = DECIMAL_ZERO_BASES.get(idx - 1).copied()?;
    if block_min_unicode_major(base) > unicode_major {
        return None;
    }
    let offset = cp.saturating_sub(base);
    if offset <= 9 {
        u8::try_from(offset).ok()
    } else {
        None
    }
}

/// Return the decimal value (`0..=9`) when `ch` belongs to Unicode 16 `Decimal_Number`.
#[inline]
pub fn decimal_digit_value(ch: char) -> Option<u8> {
    decimal_digit_value_for_unicode(ch, 16)
}

/// Comparable token for natural version sort keys (`src/findfmt/traversal/sorting.py` `_SortChunk` parity).
#[derive(Clone, Debug, Eq, PartialEq, Hash)]
pub enum SortChunk {
    /// Contiguous decimal digit run stored as leading-zero-stripped ASCII digits (`""` represents `0`).
    Digit(String),
    /// Contiguous non-decimal text run (lowercased when `ignore_case` is active).
    Text(String),
}

impl Ord for SortChunk {
    fn cmp(&self, other: &Self) -> Ordering {
        match (self, other) {
            (Self::Digit(lhs), Self::Digit(rhs)) => lhs
                .len()
                .cmp(&rhs.len())
                .then_with(|| lhs.as_bytes().cmp(rhs.as_bytes())),
            (Self::Digit(_), Self::Text(_)) => Ordering::Less,
            (Self::Text(_), Self::Digit(_)) => Ordering::Greater,
            (Self::Text(lhs), Self::Text(rhs)) => lhs.cmp(rhs),
        }
    }
}

impl PartialOrd for SortChunk {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// Complete natural sort key with filename tie-breaker (`(chunks, normalized)` parity).
#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct NaturalSortKey {
    /// Parsed alternating digit and text tokens.
    pub chunks: Vec<SortChunk>,
    /// Full filename tie-breaker (lowercased when `ignore_case` is `true`).
    pub normalized: String,
}

/// PEP 383 `surrogateescape`-preserving natural sort chunk (`0xDC80..=0xDCFF` `< 0xE000`).
#[derive(Clone, Debug, Eq, PartialEq, Hash)]
pub enum SortChunkU32 {
    Digit(String),
    Text(Vec<u32>),
}

impl Ord for SortChunkU32 {
    fn cmp(&self, other: &Self) -> Ordering {
        match (self, other) {
            (Self::Digit(lhs), Self::Digit(rhs)) => lhs
                .len()
                .cmp(&rhs.len())
                .then_with(|| lhs.as_bytes().cmp(rhs.as_bytes())),
            (Self::Digit(_), Self::Text(_)) => Ordering::Less,
            (Self::Text(_), Self::Digit(_)) => Ordering::Greater,
            (Self::Text(lhs), Self::Text(rhs)) => lhs.cmp(rhs),
        }
    }
}

impl PartialOrd for SortChunkU32 {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// PEP 383 `surrogateescape`-preserving natural sort key for `OsStr` filenames.
#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct NaturalSortKeyU32 {
    pub chunks: Vec<SortChunkU32>,
    pub normalized: Vec<u32>,
}

fn push_text_chunk(chunks: &mut Vec<SortChunk>, buf: &mut String, ignore_case: bool) {
    if buf.is_empty() {
        return;
    }
    let raw = std::mem::take(buf);
    let text = if ignore_case { raw.to_lowercase() } else { raw };
    chunks.push(SortChunk::Text(text));
}

fn push_digit_chunk<T>(chunks: &mut Vec<T>, digits: &mut String, wrap: fn(String) -> T) {
    if digits.is_empty() {
        return;
    }
    let raw = std::mem::take(digits);
    let stripped = raw.trim_start_matches('0').to_owned();
    chunks.push(wrap(stripped));
}

fn flush_u32_text(
    chunks: &mut Vec<SortChunkU32>,
    valid_buf: &mut String,
    text_cps: &mut Vec<u32>,
    ignore_case: bool,
) {
    if !valid_buf.is_empty() {
        let seg = std::mem::take(valid_buf);
        if ignore_case {
            text_cps.extend(seg.to_lowercase().chars().map(u32::from));
        } else {
            text_cps.extend(seg.chars().map(u32::from));
        }
    }
    if !text_cps.is_empty() {
        chunks.push(SortChunkU32::Text(std::mem::take(text_cps)));
    }
}

/// Generate a PEP 383 `surrogateescape`-preserving natural sort key from an `OsStr`.
pub fn natural_sort_key_osstr(
    name: &OsStr,
    ignore_case: bool,
    unicode_major: u8,
) -> NaturalSortKeyU32 {
    let raw_cps = surrogateescape_codepoints(name, false);
    let normalized = surrogateescape_codepoints(name, ignore_case);

    let mut chunks = Vec::new();
    let mut valid_text = String::new();
    let mut text_cps: Vec<u32> = Vec::new();
    let mut digit_buf = String::new();

    for cp in raw_cps {
        match char::from_u32(cp) {
            Some(ch) => {
                if let Some(d) = decimal_digit_value_for_unicode(ch, unicode_major) {
                    flush_u32_text(&mut chunks, &mut valid_text, &mut text_cps, ignore_case);
                    digit_buf.push(char::from(b'0' + d));
                } else {
                    push_digit_chunk(&mut chunks, &mut digit_buf, SortChunkU32::Digit);
                    valid_text.push(ch);
                }
            }
            None => {
                push_digit_chunk(&mut chunks, &mut digit_buf, SortChunkU32::Digit);
                if !valid_text.is_empty() {
                    let seg = std::mem::take(&mut valid_text);
                    if ignore_case {
                        text_cps.extend(seg.to_lowercase().chars().map(u32::from));
                    } else {
                        text_cps.extend(seg.chars().map(u32::from));
                    }
                }
                text_cps.push(cp);
            }
        }
    }
    flush_u32_text(&mut chunks, &mut valid_text, &mut text_cps, ignore_case);
    push_digit_chunk(&mut chunks, &mut digit_buf, SortChunkU32::Digit);

    NaturalSortKeyU32 { chunks, normalized }
}

/// Generate a natural version sort key chunking embedded decimal integers (`natural_sort_key` parity).
pub fn natural_sort_key(name: &str, ignore_case: bool) -> NaturalSortKey {
    let normalized = if ignore_case {
        name.to_lowercase()
    } else {
        name.to_owned()
    };

    let mut chunks = Vec::new();
    let mut text_buf = String::new();
    let mut digit_buf = String::new();

    for ch in name.chars() {
        if let Some(d) = decimal_digit_value(ch) {
            push_text_chunk(&mut chunks, &mut text_buf, ignore_case);
            digit_buf.push(char::from(b'0' + d));
        } else {
            push_digit_chunk(&mut chunks, &mut digit_buf, SortChunk::Digit);
            text_buf.push(ch);
        }
    }
    push_text_chunk(&mut chunks, &mut text_buf, ignore_case);
    push_digit_chunk(&mut chunks, &mut digit_buf, SortChunk::Digit);

    NaturalSortKey { chunks, normalized }
}

/// Compare two filenames using natural version ordering.
pub fn compare_natural(lhs: &str, rhs: &str, ignore_case: bool) -> Ordering {
    natural_sort_key(lhs, ignore_case).cmp(&natural_sort_key(rhs, ignore_case))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn natural_sort_handles_ascii_leading_zeros_unicode_digits_surrogates_and_sigma() {
        assert_eq!(compare_natural("item2.py", "item10.py", false), Ordering::Less);
        assert_eq!(compare_natural("item02.py", "item2.py", false), Ordering::Less);
        assert_eq!(compare_natural("000", "0", false), Ordering::Greater);
        assert_eq!(compare_natural("1_first", "a_second", false), Ordering::Less);
        assert_eq!(
            compare_natural("uni_\u{0662}.txt", "uni_\u{0661}\u{0660}.txt", false),
            Ordering::Less,
        );
        assert_eq!(compare_natural("ΟΣ", "Οςa", true), Ordering::Less);
        #[cfg(unix)]
        {
            use std::os::unix::ffi::OsStrExt;
            let k_ff = natural_sort_key_osstr(OsStr::from_bytes(b"\xff_v2"), false, 16);
            let k_pua = natural_sort_key_osstr(OsStr::new("\u{e000}_v2"), false, 16);
            assert!(k_ff < k_pua);
        }
        assert_eq!(decimal_digit_value_for_unicode('\u{11F52}', 14), None);
        assert_eq!(decimal_digit_value_for_unicode('\u{11F52}', 15), Some(2));
    }
}
