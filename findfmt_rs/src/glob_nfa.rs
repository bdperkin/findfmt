//! Linear-time Thompson NFA compiler and evaluator for `pathspec` `GitIgnoreBasicPattern` (#582).

use crate::shebang::py_rstrip;

#[inline]
pub(crate) fn fold_cp(cp: u32, ignore_case: bool) -> u32 {
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
pub(crate) enum Inst {
    Split(usize, usize),
    AnyNonNewline,
    NonSlash,
    Char(u32),
    Class {
        negated: bool,
        ranges: Vec<(u32, u32)>,
    },
    End,
    Match,
}

#[derive(Clone, Debug)]
pub(crate) enum RuleKind {
    AnyDot,
    ContainsSlash,
    Nfa(Vec<Inst>),
}

#[derive(Clone, Debug)]
pub(crate) struct CompiledRuleU32 {
    pub negated: bool,
    pub kind: RuleKind,
}

struct InvalidGlob;

fn try_parse_bracket(
    chars: &[char],
    start: usize,
    ignore_case: bool,
) -> Result<Option<(Inst, usize)>, InvalidGlob> {
    let mut j = start + 1;
    if j < chars.len() && (chars[j] == '!' || chars[j] == '^') {
        j += 1;
    }
    if j < chars.len() && chars[j] == ']' {
        j += 1;
    }
    while j < chars.len() && chars[j] != ']' {
        j += 1;
    }
    if j >= chars.len() {
        return Ok(None);
    }

    let mut body_start = start + 1;
    let mut negated = false;
    if body_start < j && (chars[body_start] == '!' || chars[body_start] == '^') {
        negated = true;
        body_start += 1;
    }
    let body = &chars[body_start..j];
    let mut k = 0_usize;
    let mut ranges: Vec<(u32, u32)> = Vec::new();
    while k < body.len() {
        let lo_ch = body[k];
        k += 1;
        if k + 1 < body.len() && body[k] == '-' {
            k += 1;
            let hi_ch = body[k];
            k += 1;
            let lo_raw = u32::from(lo_ch);
            let hi_raw = u32::from(hi_ch);
            if lo_raw > hi_raw {
                return Err(InvalidGlob);
            }
            if ignore_case && hi_raw.saturating_sub(lo_raw) <= 1024 {
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
            let f = fold_cp(u32::from(lo_ch), ignore_case);
            ranges.push((f, f));
        }
    }
    Ok(Some((Inst::Class { negated, ranges }, j + 1)))
}

fn emit_segment_glob(prog: &mut Vec<Inst>, seg: &str, ignore_case: bool) -> Result<(), InvalidGlob> {
    let chars: Vec<char> = seg.chars().collect();
    let mut k = 0_usize;
    while k < chars.len() {
        match chars[k] {
            '\\' => {
                k += 1;
                let Some(&esc) = chars.get(k) else {
                    return Err(InvalidGlob);
                };
                prog.push(Inst::Char(fold_cp(u32::from(esc), ignore_case)));
                k += 1;
            }
            '*' => {
                while chars.get(k + 1) == Some(&'*') {
                    k += 1;
                }
                let pc_split = prog.len();
                prog.push(Inst::Split(0, 0));
                let pc_ns = prog.len();
                prog.push(Inst::NonSlash);
                let pc_after = pc_ns + 2;
                prog.push(Inst::Split(pc_ns, pc_after));
                prog[pc_split] = Inst::Split(pc_ns, pc_after);
                k += 1;
            }
            '?' => {
                prog.push(Inst::NonSlash);
                k += 1;
            }
            '[' => match try_parse_bracket(&chars, k, ignore_case)? {
                Some((cls_inst, next_k)) => {
                    prog.push(cls_inst);
                    k = next_k;
                }
                None => {
                    prog.push(Inst::Char(u32::from('[')));
                    k += 1;
                }
            },
            ch => {
                prog.push(Inst::Char(fold_cp(u32::from(ch), ignore_case)));
                k += 1;
            }
        }
    }
    Ok(())
}

/// Compile a single rule line mirroring `pathspec`'s `GitIgnoreBasicPattern.pattern_to_regex`.
pub(crate) fn compile_gitignore_rule(
    raw_line: &str,
    ignore_case: bool,
) -> Result<Option<CompiledRuleU32>, String> {
    let trimmed = if raw_line.ends_with(r"\ ") {
        raw_line
    } else {
        py_rstrip(raw_line)
    };
    if trimmed.is_empty() || trimmed.starts_with('#') {
        return Ok(None);
    }
    let (negated, pattern_str) = match trimmed.strip_prefix('!') {
        Some(r) => (true, r),
        None => (false, trimmed),
    };

    let mut segs: Vec<&str> = pattern_str.split('/').collect();
    let mut is_dir_pattern = segs.last().is_some_and(|s| s.is_empty());
    if pattern_str == "/" {
        is_dir_pattern = false;
    }

    if segs.first() == Some(&"") {
        segs.remove(0);
    } else if (segs.len() == 1 || (segs.len() == 2 && segs[1].is_empty())) && segs[0] != "**" {
        segs.insert(0, "**");
    }

    if segs.is_empty() {
        return Err(format!("Invalid git pattern: {raw_line:?}"));
    }
    if segs.last() == Some(&"") {
        if let Some(last) = segs.last_mut() {
            *last = "**";
        }
    }
    for idx in (1..segs.len()).rev() {
        if segs[idx - 1] == "**" && segs[idx] == "**" {
            segs.remove(idx);
        }
    }

    if segs.len() == 1 && segs[0] == "**" {
        let kind = if is_dir_pattern {
            RuleKind::ContainsSlash
        } else {
            RuleKind::AnyDot
        };
        return Ok(Some(CompiledRuleU32 { negated, kind }));
    }
    if segs.len() == 2 && segs[0] == "**" && segs[1] == "*" {
        return Ok(Some(CompiledRuleU32 {
            negated,
            kind: RuleKind::AnyDot,
        }));
    }
    if segs.len() == 3 && segs[0] == "**" && segs[1] == "*" && segs[2] == "**" {
        return Ok(Some(CompiledRuleU32 {
            negated,
            kind: RuleKind::ContainsSlash,
        }));
    }

    let mut prog = Vec::new();
    let mut need_slash = false;
    let end = segs.len() - 1;
    for (i, &seg) in segs.iter().enumerate() {
        if seg == "**" {
            if i == 0 {
                let pc_split = prog.len();
                prog.push(Inst::Split(0, 0));
                let pc_dot = prog.len();
                prog.push(Inst::AnyNonNewline);
                let pc_loop = prog.len();
                prog.push(Inst::Split(pc_dot, pc_loop + 1));
                prog.push(Inst::Char(u32::from('/')));
                let pc_skip = prog.len();
                prog[pc_split] = Inst::Split(pc_dot, pc_skip);
            } else if i < end {
                let pc_split = prog.len();
                prog.push(Inst::Split(0, 0));
                let pc_slash = prog.len();
                prog.push(Inst::Char(u32::from('/')));
                let pc_dot = prog.len();
                prog.push(Inst::AnyNonNewline);
                let pc_loop = prog.len();
                prog.push(Inst::Split(pc_dot, pc_loop + 1));
                let pc_skip = prog.len();
                prog[pc_split] = Inst::Split(pc_slash, pc_skip);
                need_slash = true;
            } else {
                prog.push(Inst::Char(u32::from('/')));
            }
        } else {
            if need_slash {
                prog.push(Inst::Char(u32::from('/')));
            }
            if seg == "*" {
                let pc_ns = prog.len();
                prog.push(Inst::NonSlash);
                let pc_loop = prog.len();
                prog.push(Inst::Split(pc_ns, pc_loop + 1));
            } else {
                emit_segment_glob(&mut prog, seg, ignore_case)
                    .map_err(|_| format!("Invalid git pattern: {raw_line:?}"))?;
            }
            if i == end {
                if seg == "*" {
                    let pc_split = prog.len();
                    prog.push(Inst::Split(0, 0));
                    let pc_slash = prog.len();
                    prog.push(Inst::Char(u32::from('/')));
                    let pc_end = prog.len();
                    prog.push(Inst::End);
                    prog[pc_split] = Inst::Split(pc_slash, pc_end);
                } else {
                    let pc_split = prog.len();
                    prog.push(Inst::Split(0, 0));
                    let pc_slash = prog.len();
                    prog.push(Inst::Char(u32::from('/')));
                    let pc_jump = prog.len();
                    prog.push(Inst::Split(0, 0));
                    let pc_end = prog.len();
                    prog.push(Inst::End);
                    let pc_match = prog.len();
                    prog[pc_split] = Inst::Split(pc_slash, pc_end);
                    prog[pc_jump] = Inst::Split(pc_match, pc_match);
                }
            }
            need_slash = true;
        }
    }
    prog.push(Inst::Match);
    Ok(Some(CompiledRuleU32 {
        negated,
        kind: RuleKind::Nfa(prog),
    }))
}
