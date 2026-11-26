//! Unit tests for `findfmt_rs::glob_case` (#581, #590).

use super::*;

#[test]
fn equivalences_cover_long_s_turkish_i_and_unicode_version_gating() {
    let (long_s, n_s) = re_ignorecase_equivalents(u32::from('ſ'), 16);
    let exp_s = [u32::from('S'), u32::from('s'), u32::from('ſ')];
    assert_eq!(&long_s[..n_s], &exp_s);

    let (dotless_i, n_i) = re_ignorecase_equivalents(u32::from('ı'), 16);
    assert!(dotless_i[..n_i].contains(&u32::from('i')));

    let (mult, n_m) = re_ignorecase_equivalents(u32::from('×'), 16);
    assert_eq!(&mult[..n_m], &[u32::from('×')]);

    let (cyrillic_u14, len_u14) = re_ignorecase_equivalents(0x1C89, 14);
    assert_eq!(&cyrillic_u14[..len_u14], &[0x1C89]);
    let (cyrillic_u16, len_u16) = re_ignorecase_equivalents(0x1C89, 16);
    assert_eq!(&cyrillic_u16[..len_u16], &[0x1C89, 0x1C8A]);

    let (beria_old, len_old) = re_ignorecase_equivalents(0x16EA0, 16);
    assert_eq!(&beria_old[..len_old], &[0x16EA0]);
    let (beria_new, len_new) = re_ignorecase_equivalents(0x16EA0, 17);
    assert_eq!(&beria_new[..len_new], &[0x16EA0, 0x16EBB]);
}

#[test]
fn equivalences_cover_all_unicode_16_17_special_tables_and_surrogates() {
    for cp in [
        0x019B, 0xA7DC, 0x0264, 0xA7CB, 0x1C89, 0x1C8A, 0xA7CC, 0xA7CD, 0xA7DA, 0xA7DB, 0x10D50,
        0x10D70,
    ] {
        let (_, len_old) = re_ignorecase_equivalents(cp, 14);
        assert_eq!(len_old, 1);
        let (_, len_new) = re_ignorecase_equivalents(cp, 16);
        assert_eq!(len_new, 2);
    }

    for cp in [
        0xA7CE, 0xA7CF, 0xA7D2, 0xA7D3, 0xA7D4, 0xA7D5, 0x16EA0, 0x16EBB,
    ] {
        let (_, len_old) = re_ignorecase_equivalents(cp, 16);
        assert_eq!(len_old, 1);
        let (_, len_new) = re_ignorecase_equivalents(cp, 17);
        assert_eq!(len_new, 2);
    }

    for cp in [
        0x0049, 0x004B, 0x0053, 0x00B5, 0x00C5, 0x00DF, 0x01C4, 0x01C7, 0x01CA, 0x01F1, 0x0345,
        0x0390, 0x0392, 0x0395, 0x0398, 0x039A, 0x03A0, 0x03A1, 0x03A3, 0x03A6, 0x03A9, 0x03B0,
        0x0412, 0x0414, 0x041E, 0x0421, 0x0422, 0x042A, 0x0462, 0x1C88, 0x1E60, 0x1F80, 0x1FB3,
        0x1FC3, 0x1FF3, 0xFB05,
    ] {
        let (_, n) = re_ignorecase_equivalents(cp, 17);
        assert!(n >= 2);
    }

    assert_eq!(
        re_ignorecase_equivalents(0xD800, 16),
        ([0xD800, 0, 0, 0], 1)
    );
    assert_eq!(re_ignorecase_equivalents(u32::from('Α'), 16).1, 2);
    assert_eq!(re_ignorecase_equivalents(u32::from('α'), 16).1, 2);
    assert_eq!(
        non_ascii_pair(u32::from('ß')),
        ([u32::from('ß'), 0, 0, 0], 1)
    );
}
