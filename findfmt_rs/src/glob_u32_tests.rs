//! Unit tests for `findfmt_rs::glob_u32` (#582, #590).

use super::*;

fn segs(s: &str) -> Vec<Vec<u32>> {
    vec![s.chars().map(u32::from).collect()]
}

#[test]
fn ignore_case_equivalences_wide_ranges_unclosed_brackets_and_final_newline() {
    let (case_fold_az, _) = GlobSpecU32::from_lines_lenient(["[a-z].txt"], true);
    let (exact_case_az, _) = GlobSpecU32::from_lines_lenient(["[a-z].txt"], false);
    assert!(case_fold_az.matches_segments(&segs("ſ.txt"), false));
    assert!(case_fold_az.matches_segments(&segs("\u{212A}.txt"), false));
    assert!(!exact_case_az.matches_segments(&segs("ſ.txt"), false));

    let (wide, _) = GlobSpecU32::from_lines_lenient(["[À-Ա].txt"], true);
    assert!(wide.matches_segments(&segs("×.txt"), false));
    assert!(wide.matches_segments(&segs("à.txt"), false));
    assert!(wide.matches_segments(&segs("ա.txt"), false));

    let many_open = format!("{}tail", "[".repeat(512));
    let (unclosed, errs) = GlobSpecU32::from_lines_lenient([many_open.as_str()], false);
    assert_eq!(errs, 0);
    assert!(unclosed.matches_segments(&segs(&many_open), false));

    let (note, _) = GlobSpecU32::from_lines_lenient(["note"], false);
    assert!(note.matches_segments(&segs("note\n"), false));
    assert!(!note.matches_segments(&segs("note\nmore"), false));
}

#[test]
fn glob_spec_defaults_empty_inputs_epsilon_convergence_and_path_segments() -> Result<(), String> {
    let def = GlobSpecU32::default();
    assert_eq!(def.check_segments(&[], false), None);
    assert_eq!(build_target_u32(&[], true), vec![u32::from('/')]);
    assert_eq!(build_target_u32(&[], false), Vec::<u32>::new());

    assert!(GlobSpecU32::try_from_lines_with_unicode(&[], false, 16)?.is_none());
    let with_comments = GlobSpecU32::try_from_lines_with_unicode(
        &["# header".to_owned(), "  ".to_owned(), "a**b".to_owned()],
        false,
        16,
    )?
    .ok_or_else(|| "expected spec".to_owned())?;
    assert!(with_comments.matches_segments(&segs("axxb"), false));

    let (star, errs) =
        GlobSpecU32::from_lines_lenient(["# comment", "*", "[]a]", "[!]]", r"\*esc"], false);
    assert_eq!(errs, 0);
    assert!(star.matches_segments(&segs("*esc"), false));
    assert!(star.matches_segments(&segs("\n"), false));
    assert!(star.matches_segments(&segs("]"), false));
    assert!(eval_rule(&RuleKind::Nfa(vec![Inst::Match]), &[], false, 16));

    assert!(!eval_step_inst(
        &Inst::Match,
        u32::from('a'),
        &[u32::from('a')]
    ));
    let mut out = Vec::new();
    let mut visited = vec![false; 3];
    let mut stack = Vec::new();
    let diamond = [
        Inst::Split(1, 2),
        Inst::Split(2, 2),
        Inst::Char(u32::from('a')),
    ];
    assert!(!add_epsilon_states(
        &diamond,
        0,
        false,
        &mut out,
        &mut visited,
        &mut stack
    ));
    assert_eq!(out, vec![2]);

    let (rel_segs, base_name) = path_to_u32_segments(Path::new("./../leaf.py"), None);
    assert_eq!(rel_segs.len(), 3);
    assert!(base_name.is_some());

    let (abs_segs, abs_name) = path_to_u32_segments(Path::new("/abs/leaf.py"), None);
    assert_eq!(abs_segs.len(), 2);
    assert!(abs_name.is_some());

    let (dot_segs, fallback_name) =
        path_to_u32_segments(Path::new("/root/item.rs"), Some(Path::new("/root/item.rs")));
    assert_eq!(dot_segs.len(), 0);
    assert!(fallback_name.is_some());
    Ok(())
}
