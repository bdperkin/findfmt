//! Unit tests for resumable `--prune` search, bounded descent, and candidate steps (#590).

use std::collections::{HashMap, HashSet, VecDeque};
use std::env;
use std::fs;
use std::io;
use std::path::Path;
use std::sync::Arc;

use super::*;
use crate::patterns::PatternMatcher;
use crate::tags::{FilterCriteria, TagRegistry};
use crate::walker::NativeWalker;
use crate::walker_descent::advance_active_root;
use crate::walker_step::{ActiveRootState, CandidateBatch, WalkFrame, drain_candidate_batch};
use crate::walker_types::{
    GlobalIgnoreResolution, MimeSnapshot, RootTarget, WalkBounds, WalkOsError, WalkScope, WalkSort,
    WalkSortKey,
};

pub(crate) fn lock_unreadable_dir(path: &Path) -> io::Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(path, fs::Permissions::from_mode(0o000))
    }
    #[cfg(windows)]
    {
        let status = std::process::Command::new("icacls")
            .arg(path)
            .args(["/deny", "*S-1-1-0:(RD)"])
            .status()?;
        if !status.success() {
            return Err(io::Error::other("icacls /deny failed"));
        }
        Ok(())
    }
}

pub(crate) fn unlock_unreadable_dir(path: &Path) {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = fs::set_permissions(path, fs::Permissions::from_mode(0o755));
    }
    #[cfg(windows)]
    {
        let _ = std::process::Command::new("icacls")
            .arg(path)
            .args(["/remove:d", "*S-1-1-0"])
            .status();
    }
}

fn make_prune_cfg() -> WalkConfig {
    WalkConfig {
        respect_gitignore: false,
        custom_gitignore_file: None,
        scope: WalkScope {
            include_hidden: true,
            follow_symlinks: false,
            dirs_only: true,
        },
        bounds: WalkBounds {
            one_file_system: false,
            prune_empty: true,
            accumulate_size: false,
            max_depth: None,
            file_limit: None,
        },
        sort: WalkSort {
            sort_by: WalkSortKey::Name,
            reverse_sort: false,
            dirs_first: false,
            ignore_case: false,
        },
        filter: FilterCriteria::default(),
        matcher: PatternMatcher::default(),
        home_dir: None,
        pathext_upper: None,
        unicode_major: 16,
        mime_snapshot: MimeSnapshot::default(),
    }
}

#[test]
fn prune_portable_memo_invalid_dirs_and_cycle_guards() -> Result<(), Box<dyn std::error::Error>> {
    let tmp = env::temp_dir().join(format!("findfmt_rs_wp1_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    let sub = tmp.join("sub");
    let ok_dir = sub.join("c_ok");
    fs::create_dir_all(sub.join(".git"))?;
    fs::create_dir_all(&ok_dir)?;
    fs::write(ok_dir.join("hit.py"), b"x = 1\n")?;

    let mut mcfg = make_prune_cfg();
    mcfg.scope.follow_symlinks = true;
    let dk = DirKey::from_dir(&sub).ok_or("dk")?;
    let specs: Arc<[GitignoreMatcher]> = Arc::from([]);
    assert!(make_memo_key(&dk, &sub, &tmp, &specs, &mcfg).1.is_none());
    mcfg.custom_gitignore_file = Some(tmp.join("c.ign"));
    assert!(make_memo_key(&dk, &sub, &tmp, &specs, &mcfg).1.is_some());

    let reg = Box::leak(Box::new(TagRegistry::sample_registry()));
    let mut memo = HashMap::new();
    let mut evs = Vec::new();
    let cyc_root = tmp.join("cyc");
    fs::create_dir_all(&cyc_root)?;
    let cyc_dk = DirKey::from_dir(&cyc_root).ok_or("cyc_dk")?;

    // Pre-visited cycle both at initial_target and with an active parent frame
    let mut pre_vis = PruneSearch::new(cyc_root.clone(), Arc::clone(&specs), 1, false);
    pre_vis.visited.insert(cyc_dk.clone());
    assert!(matches!(
        pre_vis.poll(&tmp, None, &mcfg, reg, &mut memo, &mut evs),
        PrunePoll::Empty
    ));

    let mut framed_cyc = PruneSearch {
        initial_target: None,
        visited: HashSet::from([cyc_dk]),
        frames: vec![PruneFrame {
            dir_key: dk,
            memo_key: (DirKey::from_dir(&sub).ok_or("dk2")?, None),
            subdirs: vec![cyc_root],
            idx: 0,
            specs: Arc::clone(&specs),
            depth: 1,
            inherited_match: false,
            had_incomplete_child: false,
        }],
    };
    assert!(matches!(
        framed_cyc.poll(&tmp, None, &mcfg, reg, &mut memo, &mut evs),
        PrunePoll::Empty
    ));

    // Invalid queued dir (regular file) in both CandidateBatch and WalkFrame
    let reg_file = ok_dir.join("hit.py");
    let pcfg = make_prune_cfg();
    let mut st = ActiveRootState {
        base_root: tmp.clone(),
        prefix: None,
        root_dev: None,
        visited_dirs: HashSet::new(),
        accumulated_sizes: None,
        prune_memo: HashMap::new(),
        stack: vec![WalkFrame {
            subdirs: vec![reg_file.clone()],
            idx: 0,
            specs: Arc::clone(&specs),
            depth: 0,
            inherited_match: false,
            deferred_batch: None,
        }],
        pending_batch: Some(CandidateBatch {
            targets: VecDeque::from([(reg_file, false)]),
            active_prune: None,
            specs: Arc::clone(&specs),
            depth: 0,
            inherited_match: false,
        }),
        pending_subdir_prune: None,
    };
    drain_candidate_batch(&pcfg, reg, &mut st, &mut evs, 4);
    st.pending_batch = None;
    let _ = advance_active_root(&pcfg, reg, st, &mut evs, 4);

    let _ = fs::remove_dir_all(&tmp);
    Ok(())
}

#[test]
fn prune_portable_bounded_multi_error_resume() -> Result<(), Box<dyn std::error::Error>> {
    let tmp = env::temp_dir().join(format!("findfmt_rs_wp2_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);

    let a_empty = tmp.join("a_err_then_empty");
    let a_l1 = a_empty.join("c1_locked");
    let a_l2 = a_empty.join("c2_locked");
    fs::create_dir_all(&a_l1)?;
    fs::create_dir_all(&a_l2)?;
    fs::create_dir_all(a_empty.join("c3_empty"))?;
    fs::create_dir_all(a_empty.join(".git"))?;

    let b_match = tmp.join("b_err_then_match");
    let b_l1 = b_match.join("c1_locked");
    let b_l2 = b_match.join("c2_locked");
    let b_ok = b_match.join("c3_ok");
    fs::create_dir_all(&b_l1)?;
    fs::create_dir_all(&b_l2)?;
    fs::create_dir_all(&b_ok)?;
    fs::write(b_ok.join("hit.py"), b"x = 1\n")?;
    fs::create_dir_all(tmp.join("c_pure_empty"))?;

    for d in [&a_l1, &a_l2, &b_l1, &b_l2] {
        lock_unreadable_dir(d)?;
    }

    let reg = Box::leak(Box::new(TagRegistry::sample_registry()));
    let mut saw_err = 0usize;
    let mut saw_item = 0usize;
    for dirs_first in [false, true] {
        let mut pcfg = make_prune_cfg();
        pcfg.bounds.max_depth = Some(4);
        pcfg.sort.dirs_first = dirs_first;
        let mut walker = NativeWalker::new(
            pcfg,
            reg,
            vec![RootTarget {
                resolved_root: Some(tmp.clone()),
                prefix: None,
                global_gitignore: GlobalIgnoreResolution::ResolvedNone,
                initial_error: None,
            }],
        );
        loop {
            let batch = walker.next_batch(4);
            if batch.is_empty() {
                break;
            }
            for ev in batch {
                match ev {
                    WalkEvent::Error(_) => saw_err += 1,
                    WalkEvent::Item(_) => saw_item += 1,
                }
            }
        }
    }
    for d in [&a_l1, &a_l2, &b_l1, &b_l2] {
        unlock_unreadable_dir(d);
    }
    let _ = fs::remove_dir_all(&tmp);
    assert!(saw_err >= 4);
    assert!(saw_item >= 2);
    Ok(())
}

#[test]
fn prune_portable_nested_incomplete_and_mutated_subdir() -> Result<(), Box<dyn std::error::Error>> {
    let tmp = env::temp_dir().join(format!("findfmt_rs_wp3_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    let reg = Box::leak(Box::new(TagRegistry::sample_registry()));
    let specs: Arc<[GitignoreMatcher]> = Arc::from([]);
    let mut memo = HashMap::new();
    let mut evs = Vec::new();
    let mut pcfg = make_prune_cfg();
    pcfg.bounds.max_depth = Some(4);

    // 2-level nested incomplete child propagation (d0 -> d1 -> locked_d2) & mutated sibling file
    let d0 = tmp.join("d0");
    let d1 = d0.join("a_d1");
    let locked_d2 = d1.join("locked_d2");
    let b_mut = d0.join("b_mut");
    fs::create_dir_all(&locked_d2)?;
    fs::create_dir_all(&b_mut)?;
    lock_unreadable_dir(&locked_d2)?;

    let mut deep_search = PruneSearch::new(d0, Arc::clone(&specs), 1, false);
    assert!(matches!(
        deep_search.poll(&tmp, None, &pcfg, reg, &mut memo, &mut evs),
        PrunePoll::YieldedError
    ));
    fs::remove_dir(&b_mut)?;
    fs::write(&b_mut, b"replaced_with_file")?;
    assert!(matches!(
        deep_search.poll(&tmp, None, &pcfg, reg, &mut memo, &mut evs),
        PrunePoll::Empty
    ));

    unlock_unreadable_dir(&locked_d2);
    let _ = fs::remove_dir_all(&tmp);
    let _ = WalkOsError {
        raw_errno: None,
        path: tmp,
    };
    Ok(())
}
