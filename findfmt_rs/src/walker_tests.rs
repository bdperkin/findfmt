//! Unit tests for `walker`, `walker_descent`, `walker_prune*`, `walker_sort`, and `walker_step` (#590).

use std::collections::{BTreeSet, HashMap, HashSet};
use std::env;
use std::fs;
use std::io;
use std::sync::Arc;

use super::*;
use crate::gitignore::GitignoreMatcher;
use crate::patterns::PatternMatcher;
use crate::tags::{FilterCriteria, TagRegistry};
use crate::walker_prune::{PruneFrame, PrunePoll, PruneSearch};
use crate::walker_prune_inspect::inspect_prune_dir;
use crate::walker_sort::{
    calculate_accumulated_sizes_nogil, collect_and_sort_entries, collect_scanned_entries,
};
use crate::walker_step::{ActiveRootState, drain_candidate_batch};
use crate::walker_types::{
    GlobalIgnoreResolution, MimeSnapshot, PruneCache, WalkBounds, WalkConfig, WalkOsError,
    WalkScope, WalkSort, WalkSortKey,
};

fn base_walk_cfg() -> WalkConfig {
    WalkConfig {
        respect_gitignore: false,
        custom_gitignore_file: None,
        scope: WalkScope {
            include_hidden: false,
            follow_symlinks: false,
            dirs_only: false,
        },
        bounds: WalkBounds {
            one_file_system: false,
            prune_empty: false,
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

fn make_root(resolved_root: Option<PathBuf>, initial_error: Option<WalkOsError>) -> RootTarget {
    RootTarget {
        resolved_root,
        prefix: None,
        global_gitignore: GlobalIgnoreResolution::ResolvedNone,
        initial_error,
    }
}

#[test]
fn walker_overflow_single_file_root_errors_and_drain_noop() -> Result<(), Box<dyn std::error::Error>>
{
    let tmp = env::temp_dir().join(format!("findfmt_rs_wk1_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    fs::create_dir_all(&tmp)?;
    let f1 = tmp.join("a.py");
    let f2 = tmp.join("b.txt");
    fs::write(&f1, b"print(1)\n")?;
    fs::write(&f2, b"hello\n")?;

    let reg = Box::leak(Box::new(TagRegistry::sample_registry()));
    let cfg = base_walk_cfg();
    let err_root = make_root(
        None,
        Some(WalkOsError {
            path: tmp.join("missing"),
            raw_errno: Some(2),
        }),
    );
    let ok_root = make_root(
        Some(f1.clone()),
        Some(WalkOsError {
            path: tmp.clone(),
            raw_errno: None,
        }),
    );
    let vanished_root = make_root(Some(tmp.join("vanished_dir")), None);
    let dir_root = make_root(Some(tmp.clone()), None);

    let mut walker = NativeWalker::new(
        cfg.clone(),
        reg,
        vec![err_root, ok_root, vanished_root, dir_root],
    );
    let b1 = walker.next_batch(1);
    assert!(matches!(b1.as_slice(), [WalkEvent::Error(_)]));
    let _ = walker.next_batch(1);
    let _ = walker.next_batch(8);

    walker
        .overflow
        .push_back(WalkEvent::Item(Box::new(WalkYieldItem {
            path: f1.clone(),
            str_path: f1.to_string_lossy().into_owned(),
            filename: "a.py".into(),
            root_path: tmp.clone(),
            prefix: None,
            has_entry: false,
            follow_symlinks: false,
            #[cfg(not(unix))]
            inherited_match: false,
            classified: crate::classifier::classify_one_nogil(
                &crate::walker_filter::build_raw_classify_input(f1, false, None, &cfg),
                reg,
                None,
            ),
        })));
    walker.overflow.push_back(WalkEvent::Error(WalkOsError {
        path: tmp.clone(),
        raw_errno: None,
    }));
    let drained = walker.next_batch(4);
    assert_eq!(drained.len(), 2);

    let _ = fs::remove_dir_all(&tmp);
    Ok(())
}

#[test]
fn walker_single_file_roots_du_sort_and_portable_prune() -> Result<(), Box<dyn std::error::Error>> {
    let tmp = env::temp_dir().join(format!("findfmt_rs_wk1b_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    let sub_match = tmp.join("b_match").join("inner");
    fs::create_dir_all(&sub_match)?;
    let f1 = sub_match.join("hit.py");
    fs::write(&f1, b"print(1)\n")?;
    fs::write(tmp.join(".hidden"), b"h")?;

    let reg = Box::leak(Box::new(TagRegistry::sample_registry()));
    let mut cfg = base_walk_cfg();
    cfg.scope.dirs_only = true;
    let mut dirs_walker =
        NativeWalker::new(cfg.clone(), reg, vec![make_root(Some(f1.clone()), None)]);
    assert_eq!(dirs_walker.next_batch(4).len(), 0);

    cfg.scope.dirs_only = false;
    cfg.filter.include_tags = BTreeSet::from(["rust".to_owned()]);
    let mut filt_walker =
        NativeWalker::new(cfg.clone(), reg, vec![make_root(Some(f1.clone()), None)]);
    assert_eq!(filt_walker.next_batch(4).len(), 0);

    let mut empty_state = ActiveRootState {
        base_root: tmp.clone(),
        prefix: None,
        root_dev: None,
        visited_dirs: HashSet::new(),
        accumulated_sizes: None,
        prune_memo: HashMap::new(),
        stack: Vec::new(),
        pending_batch: None,
        pending_subdir_prune: None,
    };
    let mut evs = Vec::new();
    drain_candidate_batch(&cfg, reg, &mut empty_state, &mut evs, 4);
    assert_eq!(evs.len(), 0);

    let missing_du = calculate_accumulated_sizes_nogil(&tmp.join("nope"), false, false);
    assert_eq!(missing_du.get(&tmp.join("nope")), Some(&0));
    assert!(
        calculate_accumulated_sizes_nogil(&f1, false, false)
            .values()
            .all(|&v| v > 0)
    );
    assert!(
        calculate_accumulated_sizes_nogil(&f1, true, false)
            .values()
            .all(|&v| v > 0)
    );
    assert!(calculate_accumulated_sizes_nogil(&tmp, false, false).contains_key(&tmp));

    let mid_err = collect_scanned_entries(
        &tmp,
        vec![Err(io::Error::other("mid-read"))],
        None,
        &mut evs,
    );
    assert!(mid_err.is_none());
    assert!(collect_and_sort_entries(&f1, &cfg, &mut evs).is_none());

    let _ = fs::remove_dir_all(&tmp);
    Ok(())
}

#[test]
fn walker_portable_prune_inspect_and_poll_resume() -> Result<(), Box<dyn std::error::Error>> {
    use crate::walker_prune::tests::{lock_unreadable_dir, unlock_unreadable_dir};

    let tmp = env::temp_dir().join(format!("findfmt_rs_wkp_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    let sub_a = tmp.join("a_sub");
    let locked_init = sub_a.join("a_locked");
    let peer_hit_dir = sub_a.join("z_ok");
    fs::create_dir_all(&locked_init)?;
    fs::create_dir_all(&peer_hit_dir)?;
    fs::write(peer_hit_dir.join("ok.py"), b"1\n")?;
    lock_unreadable_dir(&locked_init)?;

    let reg = Box::leak(Box::new(TagRegistry::sample_registry()));
    let mut pcfg = base_walk_cfg();
    pcfg.scope.dirs_only = true;
    pcfg.bounds.prune_empty = true;
    pcfg.custom_gitignore_file = Some(tmp.join("custom.ign"));
    let specs: Arc<[GitignoreMatcher]> = Arc::from([]);
    let dk_sub = DirKey::from_dir(&sub_a).ok_or("dk_sub")?;
    let mk_sub = crate::walker_prune::make_memo_key(&dk_sub, &sub_a, &tmp, &specs, &pcfg);

    let mut search = PruneSearch::new(locked_init.clone(), Arc::clone(&specs), 2, false);
    search.frames.push(PruneFrame {
        dir_key: dk_sub,
        memo_key: mk_sub,
        subdirs: vec![peer_hit_dir.clone()],
        idx: 0,
        specs: Arc::clone(&specs),
        depth: 1,
        inherited_match: false,
        had_incomplete_child: false,
    });
    let mut memo = HashMap::new();
    let mut pevs = Vec::new();
    assert!(matches!(
        search.poll(&tmp, None, &pcfg, reg, &mut memo, &mut pevs),
        PrunePoll::YieldedError
    ));
    assert!(matches!(
        search.poll(&tmp, None, &pcfg, reg, &mut memo, &mut pevs),
        PrunePoll::Matched
    ));

    assert!(!inspect_prune_dir(
        &mut search,
        &peer_hit_dir.join("ok.py"),
        &specs,
        1,
        false,
        &tmp,
        None,
        &pcfg,
        reg,
        &mut memo,
        &mut pevs,
    ));
    assert!(!inspect_prune_dir(
        &mut search,
        &tmp.join("does_not_exist"),
        &specs,
        1,
        false,
        &tmp,
        None,
        &pcfg,
        reg,
        &mut memo,
        &mut pevs,
    ));
    pcfg.bounds.max_depth = Some(5);
    let dk = DirKey::from_dir(&peer_hit_dir).ok_or("dk")?;
    let mk = crate::walker_prune::make_memo_key(&dk, &peer_hit_dir, &tmp, &specs, &pcfg);
    memo.insert(
        mk,
        PruneCache::Empty {
            searched_from_depth: 10,
            had_cycle_skip: false,
        },
    );
    let _ = inspect_prune_dir(
        &mut search,
        &peer_hit_dir,
        &specs,
        2,
        false,
        &tmp,
        None,
        &pcfg,
        reg,
        &mut memo,
        &mut pevs,
    );

    unlock_unreadable_dir(&locked_init);
    let _ = fs::remove_dir_all(&tmp);
    Ok(())
}

#[cfg(unix)]
#[test]
fn walker_unix_cycles_fifo_broken_symlink_and_locked_du() -> Result<(), Box<dyn std::error::Error>>
{
    use std::os::unix::fs::{PermissionsExt, symlink};

    let tmp = env::temp_dir().join(format!("findfmt_rs_wku_{}", std::process::id()));
    let _ = fs::remove_dir_all(&tmp);
    let locked_dir = tmp.join("locked");
    fs::create_dir_all(&locked_dir)?;
    let fifo = tmp.join("pipe.fifo");
    assert!(
        std::process::Command::new("mkfifo")
            .arg(&fifo)
            .status()?
            .success()
    );
    symlink(&tmp, tmp.join("loop_dir"))?;
    symlink(tmp.join("vanished_target"), tmp.join("broken_sort.py"))?;
    fs::set_permissions(&locked_dir, fs::Permissions::from_mode(0o000))?;

    let cycle_du = calculate_accumulated_sizes_nogil(&tmp, true, false);
    assert!(cycle_du.contains_key(&tmp));

    let mut cfg = base_walk_cfg();
    cfg.scope.follow_symlinks = true;
    cfg.sort.sort_by = WalkSortKey::Size;
    let mut evs = Vec::new();
    assert!(collect_and_sort_entries(&tmp, &cfg, &mut evs).is_some());

    let _ = fs::set_permissions(&locked_dir, fs::Permissions::from_mode(0o755));
    let _ = fs::remove_dir_all(&tmp);
    Ok(())
}
