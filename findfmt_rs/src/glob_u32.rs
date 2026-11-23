//! Lossless PEP 383 `surrogateescape` (`u32`) gitignore-glob matcher for `-P` / `-I` (#582).

use std::path::{Component, Path};

use crate::walker_types::surrogateescape_codepoints;

#[inline]
fn fold_cp(cp: u32, ignore_case: bool) -> u32 {
    if !ignore_case {
        return cp;
    }
    // Python `re.IGNORECASE` treats Greek 'Σ' (0x03A3), 'σ' (0x03C3), and 'ς' (0x03C2) identically.
    if cp == 0x03C2 {
        return 0x03C3;
    }
    let Some(ch) = char::from_u32(cp) else {
        return cp;
    };
    let mut lower = ch.to_lowercase();
    let first = lower.next().unwrap_or(ch);
    if lower.next().is_none() {
        let lcp = u32::from(first);
        if lcp == 0x03C2 { 0x03C3 } else { lcp }
    } else {
        cp
    }
}

#[derive(Clone, Debug)]
enum SegToken {
    Star,
    AnyOne,
    Literal(u32),
    Class {
        negated: bool,
        ranges: Vec<(u32, u32)>,
    },
}

#[derive(Clone, Debug)]
enum SegPat {
    DoubleStar,
    Seq(Vec<SegToken>),
}

#[derive(Clone, Debug)]
struct CompiledRuleU32 {
    negated: bool,
    dir_only: bool,
    anchored: bool,
    match_all: bool,
    segments: Vec<SegPat>,
}

struct InvalidGlob;

fn try_parse_bracket(
    chars: &[char],
    start: usize,
    ignore_case: bool,
) -> Result<Option<(SegToken, usize)>, InvalidGlob> {
    let mut idx = start + 1;
    if idx >= chars.len() {
        return Ok(None);
    }
    let mut negated = false;
    if chars[idx] == '!' || chars[idx] == '^' {
        negated = true;
        idx += 1;
    }
    let first_item_idx = idx;
    let mut items: Vec<u32> = Vec::new();
    let mut ranges: Vec<(u32, u32)> = Vec::new();

    while idx < chars.len() {
        if chars[idx] == ']' && idx > first_item_idx {
            for cp in items {
                ranges.push((cp, cp));
            }
            return Ok(Some((SegToken::Class { negated, ranges }, idx + 1)));
        }
        let lo_ch = if chars[idx] == '\\' {
            idx += 1;
            let Some(&esc) = chars.get(idx) else {
                return Err(InvalidGlob);
            };
            idx += 1;
            esc
        } else {
            let c = chars[idx];
            idx += 1;
            c
        };

        if idx + 1 < chars.len() && chars[idx] == '-' && chars[idx + 1] != ']' {
            idx += 1; // consume '-'
            let hi_ch = if chars[idx] == '\\' {
                idx += 1;
                let Some(&esc) = chars.get(idx) else {
                    return Err(InvalidGlob);
                };
                idx += 1;
                esc
            } else {
                let c = chars[idx];
                idx += 1;
                c
            };
            let lo_raw = u32::from(lo_ch);
            let hi_raw = u32::from(hi_ch);
            if lo_raw > hi_raw {
                return Err(InvalidGlob);
            }
            if ignore_case && hi_raw.saturating_sub(lo_raw) <= 256 {
                for raw_cp in lo_raw..=hi_raw {
                    let f = fold_cp(raw_cp, true);
                    ranges.push((f, f));
                }
            } else {
                let flo = fold_cp(lo_raw, ignore_case);
                let fhi = fold_cp(hi_raw, ignore_case);
                ranges.push((flo.min(fhi), flo.max(fhi)));
            }
        } else {
            items.push(fold_cp(u32::from(lo_ch), ignore_case));
        }
    }
    // Unclosed '[' is treated as a literal '[' (`fnmatch` / `pathspec` parity).
    Ok(None)
}

fn parse_segment_tokens(seg: &str, ignore_case: bool) -> Result<SegPat, InvalidGlob> {
    if seg == "**" {
        return Ok(SegPat::DoubleStar);
    }
    let chars: Vec<char> = seg.chars().collect();
    let mut tokens = Vec::new();
    let mut i = 0_usize;
    while i < chars.len() {
        match chars[i] {
            '\\' => {
                i += 1;
                let Some(&esc) = chars.get(i) else {
                    return Err(InvalidGlob);
                };
                tokens.push(SegToken::Literal(fold_cp(u32::from(esc), ignore_case)));
                i += 1;
            }
            '*' => {
                if !matches!(tokens.last(), Some(SegToken::Star)) {
                    tokens.push(SegToken::Star);
                }
                i += 1;
            }
            '?' => {
                tokens.push(SegToken::AnyOne);
                i += 1;
            }
            '[' => match try_parse_bracket(&chars, i, ignore_case)? {
                Some((cls_tok, next_i)) => {
                    tokens.push(cls_tok);
                    i = next_i;
                }
                None => {
                    tokens.push(SegToken::Literal(u32::from('[')));
                    i += 1;
                }
            },
            ch => {
                tokens.push(SegToken::Literal(fold_cp(u32::from(ch), ignore_case)));
                i += 1;
            }
        }
    }
    Ok(SegPat::Seq(tokens))
}

fn compile_rule_line(line: &str, ignore_case: bool) -> Option<CompiledRuleU32> {
    if line.is_empty() || line.starts_with('#') {
        return None;
    }
    let (negated, rest) = match line.strip_prefix('!') {
        Some(r) => (true, r),
        None => (false, line),
    };
    if rest.is_empty() {
        return None;
    }
    if rest == "/" {
        return Some(CompiledRuleU32 {
            negated,
            dir_only: false,
            anchored: false,
            match_all: true,
            segments: Vec::new(),
        });
    }
    if rest.chars().all(|c| c == '/') {
        return None;
    }
    let dir_only = rest.ends_with('/');
    let without_trailing = rest.trim_end_matches('/');
    let anchored = without_trailing.contains('/');
    let body = without_trailing
        .strip_prefix('/')
        .unwrap_or(without_trailing);

    let mut segments = Vec::new();
    for raw_seg in body.split('/') {
        segments.push(parse_segment_tokens(raw_seg, ignore_case).ok()?);
    }
    Some(CompiledRuleU32 {
        negated,
        dir_only,
        anchored,
        match_all: false,
        segments,
    })
}

fn match_tokens_slice(tokens: &[SegToken], text: &[u32], ignore_case: bool) -> bool {
    let mut ti = 0_usize;
    let mut si = 0_usize;
    let mut star_ti: Option<usize> = None;
    let mut star_si = 0_usize;

    while si < text.len() {
        let cp = fold_cp(text[si], ignore_case);
        if let Some(tok) = tokens.get(ti) {
            match tok {
                SegToken::Star => {
                    star_ti = Some(ti);
                    star_si = si;
                    ti += 1;
                    continue;
                }
                SegToken::AnyOne => {
                    ti += 1;
                    si += 1;
                    continue;
                }
                SegToken::Literal(exp) if *exp == cp => {
                    ti += 1;
                    si += 1;
                    continue;
                }
                SegToken::Class { negated, ranges } => {
                    let hit = ranges.iter().any(|&(lo, hi)| cp >= lo && cp <= hi);
                    if hit != *negated {
                        ti += 1;
                        si += 1;
                        continue;
                    }
                }
                SegToken::Literal(_) => {}
            }
        }
        if let Some(st) = star_ti {
            star_si += 1;
            si = star_si;
            ti = st + 1;
        } else {
            return false;
        }
    }
    while matches!(tokens.get(ti), Some(SegToken::Star)) {
        ti += 1;
    }
    ti == tokens.len()
}

fn match_seg_pats(pats: &[SegPat], segs: &[Vec<u32>], ignore_case: bool) -> bool {
    let mut pi = 0_usize;
    let mut si = 0_usize;
    let mut dstar_pi: Option<usize> = None;
    let mut dstar_si = 0_usize;

    while si < segs.len() {
        if let Some(pat) = pats.get(pi) {
            match pat {
                SegPat::DoubleStar => {
                    dstar_pi = Some(pi);
                    dstar_si = si;
                    pi += 1;
                    continue;
                }
                SegPat::Seq(toks)
                    if !segs[si].is_empty() && match_tokens_slice(toks, &segs[si], ignore_case) =>
                {
                    pi += 1;
                    si += 1;
                    continue;
                }
                SegPat::Seq(_) => {}
            }
        }
        if let Some(dp) = dstar_pi {
            dstar_si += 1;
            si = dstar_si;
            pi = dp + 1;
        } else {
            return false;
        }
    }
    while matches!(pats.get(pi), Some(SegPat::DoubleStar)) {
        pi += 1;
    }
    pi == pats.len()
}

/// Compiled sequence of gitignore-style glob rules operating on PEP 383 `u32` segments.
#[derive(Clone, Debug, Default)]
pub struct GlobSpecU32 {
    rules: Vec<CompiledRuleU32>,
    ignore_case: bool,
}

impl GlobSpecU32 {
    /// Compile trimmed pattern lines (`patterns.py:compile_pattern_spec` parity).
    pub fn from_lines(lines: &[String], ignore_case: bool) -> Option<Self> {
        let rules: Vec<CompiledRuleU32> = lines
            .iter()
            .filter_map(|l| compile_rule_line(l, ignore_case))
            .collect();
        (!rules.is_empty()).then_some(Self { rules, ignore_case })
    }

    /// Evaluate `spec.match_file` semantics on `segs` with `is_dir` trailing-slash parity.
    pub fn matches_segments(&self, segs: &[Vec<u32>], is_dir: bool) -> bool {
        if segs.is_empty() {
            return false;
        }
        let mut matched = false;
        for rule in &self.rules {
            if self.rule_hits(rule, segs, is_dir) {
                matched = !rule.negated;
            }
        }
        matched
    }

    fn rule_hits(&self, rule: &CompiledRuleU32, segs: &[Vec<u32>], is_dir: bool) -> bool {
        if rule.match_all {
            return true;
        }
        for p in 1..=segs.len() {
            let prefix_is_dir = if p < segs.len() { true } else { is_dir };
            if rule.dir_only && !prefix_is_dir {
                continue;
            }
            let prefix = &segs[..p];
            if rule.anchored {
                if match_seg_pats(&rule.segments, prefix, self.ignore_case) {
                    return true;
                }
            } else if prefix.last().is_some_and(|last_seg| {
                match_seg_pats(
                    &rule.segments,
                    std::slice::from_ref(last_seg),
                    self.ignore_case,
                )
            }) {
                return true;
            }
        }
        false
    }
}

/// Extract lossless PEP 383 `(rel_segments, basename_opt)` preserving Unix `C:` directories.
pub fn path_to_u32_segments(
    path: &Path,
    base_root: Option<&Path>,
) -> (Vec<Vec<u32>>, Option<Vec<u32>>) {
    let rel = match base_root {
        Some(base) => path.strip_prefix(base).unwrap_or(path),
        None => path,
    };
    let mut segs = Vec::new();
    for comp in rel.components() {
        match comp {
            Component::Normal(part) if !part.is_empty() => {
                segs.push(surrogateescape_codepoints(part, false));
            }
            Component::ParentDir => segs.push(vec![u32::from('.'), u32::from('.')]),
            Component::CurDir if segs.is_empty() => segs.push(vec![u32::from('.')]),
            _ => {}
        }
    }
    let name_cps = rel
        .file_name()
        .or_else(|| path.file_name())
        .map(|n| surrogateescape_codepoints(n, false))
        .filter(|v| !v.is_empty());
    (segs, name_cps)
}
