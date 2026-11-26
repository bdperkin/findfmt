//! Lossless PEP 383 `surrogateescape` (`u32`) gitignore-glob matcher (`pathspec` parity, #582).

use std::path::{Component, Path};

use crate::glob_case::re_ignorecase_equivalents;
use crate::glob_nfa::{CompiledRuleU32, Inst, RuleKind, compile_gitignore_rule};
use crate::walker_types::surrogateescape_codepoints;

#[inline]
fn at_end_pos(text: &[u32], pos: usize) -> bool {
    pos == text.len() || (pos + 1 == text.len() && text[pos] == u32::from('\n'))
}

fn add_epsilon_states(
    prog: &[Inst],
    start_pc: usize,
    at_end: bool,
    out: &mut Vec<usize>,
    visited: &mut [bool],
    stack: &mut Vec<usize>,
) -> bool {
    stack.clear();
    stack.push(start_pc);
    while let Some(cur) = stack.pop() {
        if cur >= prog.len() || visited[cur] {
            continue;
        }
        visited[cur] = true;
        match prog[cur] {
            Inst::Match => return true,
            Inst::Split(a, b) => {
                stack.push(b);
                stack.push(a);
            }
            Inst::End => {
                if at_end {
                    stack.push(cur + 1);
                }
            }
            Inst::AnyNonNewline | Inst::NonSlash | Inst::Char(_) | Inst::Class { .. } => {
                out.push(cur);
            }
        }
    }
    false
}

fn eval_step_inst(inst: &Inst, raw_cp: u32, eq_slice: &[u32]) -> bool {
    match *inst {
        Inst::AnyNonNewline => raw_cp != u32::from('\n'),
        Inst::NonSlash => raw_cp != u32::from('/'),
        Inst::Char(exp) => eq_slice.contains(&exp),
        Inst::Class {
            negated,
            ref ranges,
        } => {
            ranges
                .iter()
                .any(|&(lo, hi)| eq_slice.iter().any(|&c| c >= lo && c <= hi))
                != negated
        }
        Inst::Split(_, _) | Inst::End | Inst::Match => false,
    }
}

fn eval_rule(kind: &RuleKind, text: &[u32], ignore_case: bool, unicode_major: u8) -> bool {
    match kind {
        RuleKind::AnyDot => text.iter().any(|&cp| cp != u32::from('\n')),
        RuleKind::ContainsSlash => text.contains(&u32::from('/')),
        RuleKind::Nfa(prog) => {
            let mut curr = Vec::with_capacity(prog.len());
            let mut next = Vec::with_capacity(prog.len());
            let mut visited = vec![false; prog.len()];
            let mut stack = Vec::with_capacity(prog.len());

            if add_epsilon_states(
                prog,
                0,
                at_end_pos(text, 0),
                &mut curr,
                &mut visited,
                &mut stack,
            ) {
                return true;
            }
            for (idx, &raw_cp) in text.iter().enumerate() {
                if curr.is_empty() {
                    return false;
                }
                let next_at_end = at_end_pos(text, idx + 1);
                let (equivs, eq_len) = if ignore_case {
                    re_ignorecase_equivalents(raw_cp, unicode_major)
                } else {
                    ([raw_cp, 0, 0, 0], 1)
                };
                let eq_slice = &equivs[..eq_len];
                next.clear();
                visited.fill(false);
                for &pc in &curr {
                    if eval_step_inst(&prog[pc], raw_cp, eq_slice)
                        && add_epsilon_states(
                            prog,
                            pc + 1,
                            next_at_end,
                            &mut next,
                            &mut visited,
                            &mut stack,
                        )
                    {
                        return true;
                    }
                }
                std::mem::swap(&mut curr, &mut next);
            }
            false
        }
    }
}

/// Build a `/`‑joined PEP 383 `u32` buffer from `segs`, appending `/` when `is_dir` is `true`.
pub fn build_target_u32(segs: &[Vec<u32>], is_dir: bool) -> Vec<u32> {
    if segs.is_empty() {
        return if is_dir {
            vec![u32::from('/')]
        } else {
            Vec::new()
        };
    }
    let cap: usize = segs.iter().map(Vec::len).sum::<usize>() + segs.len();
    let mut out = Vec::with_capacity(cap);
    for (idx, seg) in segs.iter().enumerate() {
        if idx > 0 {
            out.push(u32::from('/'));
        }
        out.extend_from_slice(seg);
    }
    if is_dir {
        out.push(u32::from('/'));
    }
    out
}

/// Compiled sequence of `GitIgnoreBasicPattern` rules operating on PEP 383 `u32` codepoints.
#[derive(Clone, Debug)]
pub struct GlobSpecU32 {
    rules: Vec<CompiledRuleU32>,
    ignore_case: bool,
    unicode_major: u8,
}

impl Default for GlobSpecU32 {
    fn default() -> Self {
        Self {
            rules: Vec::new(),
            ignore_case: false,
            unicode_major: 16,
        }
    }
}

impl GlobSpecU32 {
    /// Compile trimmed pattern lines gated to `unicode_major` case equivalences (`#581`).
    pub fn try_from_lines_with_unicode(
        lines: &[String],
        ignore_case: bool,
        unicode_major: u8,
    ) -> Result<Option<Self>, String> {
        if lines.is_empty() {
            return Ok(None);
        }
        let mut rules = Vec::with_capacity(lines.len());
        for line in lines {
            if let Some(compiled) = compile_gitignore_rule(line)? {
                rules.push(compiled);
            }
        }
        Ok(Some(Self {
            rules,
            ignore_case,
            unicode_major,
        }))
    }

    /// Compile lines leniently for fuzzing / `GitignoreMatcher::from_text`, counting invalid lines.
    pub fn from_lines_lenient<'a, I>(lines: I, ignore_case: bool) -> (Self, usize)
    where
        I: IntoIterator<Item = &'a str>,
    {
        let mut rules = Vec::new();
        let mut errors = 0_usize;
        for line in lines {
            match compile_gitignore_rule(line) {
                Ok(Some(compiled)) => rules.push(compiled),
                Ok(None) => {}
                Err(_) => errors += 1,
            }
        }
        (
            Self {
                rules,
                ignore_case,
                unicode_major: 16,
            },
            errors,
        )
    }

    /// Evaluate `spec.check_file` tri-state semantics (`None`, `Some(true)`, `Some(false)`).
    pub fn check_segments(&self, segs: &[Vec<u32>], is_dir: bool) -> Option<bool> {
        let target = build_target_u32(segs, is_dir);
        if target.is_empty() {
            return None;
        }
        let mut state: Option<bool> = None;
        for rule in &self.rules {
            if eval_rule(&rule.kind, &target, self.ignore_case, self.unicode_major) {
                state = Some(!rule.negated);
            }
        }
        state
    }

    /// Evaluate `spec.match_file` boolean semantics on `segs` with `is_dir` trailing-slash parity.
    pub fn matches_segments(&self, segs: &[Vec<u32>], is_dir: bool) -> bool {
        self.check_segments(segs, is_dir) == Some(true)
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

#[cfg(test)]
#[path = "glob_u32_tests.rs"]
mod tests;
