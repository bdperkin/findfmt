//! Python `re.IGNORECASE` Unicode equivalence classes for glob NFA evaluation (#582).

/// Return up to 4 codepoints in `cp`'s Python `re.IGNORECASE` equivalence class (`sre_lib.h`).
///
/// Because `re.IGNORECASE` partitions Unicode scalar values into equivalence classes of size
/// at most 4, an input character `raw_cp` matches a pattern character `exp` iff `exp` appears in
/// `re_ignorecase_equivalents(raw_cp)`, and matches a raw character range `lo..=hi` iff at least
/// one member of `re_ignorecase_equivalents(raw_cp)` falls within `lo..=hi`.
#[inline]
pub(crate) fn re_ignorecase_equivalents(cp: u32) -> ([u32; 4], usize) {
    match cp {
        0x0049 | 0x0069 | 0x0130 | 0x0131 => ([0x0049, 0x0069, 0x0130, 0x0131], 4),
        0x004B | 0x006B | 0x212A => ([0x004B, 0x006B, 0x212A, 0], 3),
        0x0053 | 0x0073 | 0x017F => ([0x0053, 0x0073, 0x017F, 0], 3),
        0x00B5 | 0x039C | 0x03BC => ([0x00B5, 0x039C, 0x03BC, 0], 3),
        0x00C5 | 0x00E5 | 0x212B => ([0x00C5, 0x00E5, 0x212B, 0], 3),
        0x00DF | 0x1E9E => ([0x00DF, 0x1E9E, 0, 0], 2),
        0x01C4..=0x01C6 => ([0x01C4, 0x01C5, 0x01C6, 0], 3),
        0x01C7..=0x01C9 => ([0x01C7, 0x01C8, 0x01C9, 0], 3),
        0x01CA..=0x01CC => ([0x01CA, 0x01CB, 0x01CC, 0], 3),
        0x01F1..=0x01F3 => ([0x01F1, 0x01F2, 0x01F3, 0], 3),
        0x0345 | 0x0399 | 0x03B9 | 0x1FBE => ([0x0345, 0x0399, 0x03B9, 0x1FBE], 4),
        0x0390 | 0x1FD3 => ([0x0390, 0x1FD3, 0, 0], 2),
        0x0392 | 0x03B2 | 0x03D0 => ([0x0392, 0x03B2, 0x03D0, 0], 3),
        0x0395 | 0x03B5 | 0x03F5 => ([0x0395, 0x03B5, 0x03F5, 0], 3),
        0x0398 | 0x03B8 | 0x03D1 | 0x03F4 => ([0x0398, 0x03B8, 0x03D1, 0x03F4], 4),
        0x039A | 0x03BA | 0x03F0 => ([0x039A, 0x03BA, 0x03F0, 0], 3),
        0x03A0 | 0x03C0 | 0x03D6 => ([0x03A0, 0x03C0, 0x03D6, 0], 3),
        0x03A1 | 0x03C1 | 0x03F1 => ([0x03A1, 0x03C1, 0x03F1, 0], 3),
        0x03A3 | 0x03C2 | 0x03C3 => ([0x03A3, 0x03C2, 0x03C3, 0], 3),
        0x03A6 | 0x03C6 | 0x03D5 => ([0x03A6, 0x03C6, 0x03D5, 0], 3),
        0x03A9 | 0x03C9 | 0x2126 => ([0x03A9, 0x03C9, 0x2126, 0], 3),
        0x03B0 | 0x1FE3 => ([0x03B0, 0x1FE3, 0, 0], 2),
        0x0412 | 0x0432 | 0x1C80 => ([0x0412, 0x0432, 0x1C80, 0], 3),
        0x0414 | 0x0434 | 0x1C81 => ([0x0414, 0x0434, 0x1C81, 0], 3),
        0x041E | 0x043E | 0x1C82 => ([0x041E, 0x043E, 0x1C82, 0], 3),
        0x0421 | 0x0441 | 0x1C83 => ([0x0421, 0x0441, 0x1C83, 0], 3),
        0x0422 | 0x0442 | 0x1C84 | 0x1C85 => ([0x0422, 0x0442, 0x1C84, 0x1C85], 4),
        0x042A | 0x044A | 0x1C86 => ([0x042A, 0x044A, 0x1C86, 0], 3),
        0x0462 | 0x0463 | 0x1C87 => ([0x0462, 0x0463, 0x1C87, 0], 3),
        0x1C88 | 0xA64A | 0xA64B => ([0x1C88, 0xA64A, 0xA64B, 0], 3),
        0x1E60 | 0x1E61 | 0x1E9B => ([0x1E60, 0x1E61, 0x1E9B, 0], 3),
        0x1F80..=0x1FAF => ([cp & !8, cp | 8, 0, 0], 2),
        0x1FB3 | 0x1FBC => ([0x1FB3, 0x1FBC, 0, 0], 2),
        0x1FC3 | 0x1FCC => ([0x1FC3, 0x1FCC, 0, 0], 2),
        0x1FF3 | 0x1FFC => ([0x1FF3, 0x1FFC, 0, 0], 2),
        0xFB05 | 0xFB06 => ([0xFB05, 0xFB06, 0, 0], 2),
        0x0041..=0x005A => ([cp, cp + 32, 0, 0], 2),
        0x0061..=0x007A => ([cp - 32, cp, 0, 0], 2),
        0x0000..=0x007F => ([cp, 0, 0, 0], 1),
        _ => non_ascii_pair(cp),
    }
}

fn non_ascii_pair(cp: u32) -> ([u32; 4], usize) {
    let Some(ch) = char::from_u32(cp) else {
        return ([cp, 0, 0, 0], 1);
    };
    let mut out = [cp, 0, 0, 0];
    let mut len = 1_usize;

    let mut lower = ch.to_lowercase();
    if let Some(lc) = lower.next() {
        let lcp = u32::from(lc);
        if lower.next().is_none() && lcp != cp {
            out[len] = lcp;
            len += 1;
        }
    }

    let mut upper = ch.to_uppercase();
    if let Some(uc) = upper.next() {
        let ucp = u32::from(uc);
        if upper.next().is_none() && !out[..len].contains(&ucp) {
            out[len] = ucp;
            len += 1;
        }
    }
    (out, len)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn equivalences_cover_long_s_turkish_i_kelvin_and_ascii() {
        let (long_s, n_s) = re_ignorecase_equivalents(u32::from('ſ'));
        let exp_s = [u32::from('S'), u32::from('s'), u32::from('ſ')];
        assert_eq!(&long_s[..n_s], &exp_s);

        let (dotless_i, n_i) = re_ignorecase_equivalents(u32::from('ı'));
        assert!(dotless_i[..n_i].contains(&u32::from('i')));

        let (mult, n_m) = re_ignorecase_equivalents(u32::from('×'));
        assert_eq!(&mult[..n_m], &[u32::from('×')]);
    }
}
