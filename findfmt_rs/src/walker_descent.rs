//! Subdirectory descent and resumable `--prune` poll progression for `NativeWalker` (#582).

use std::path::PathBuf;
use std::sync::Arc;

use crate::gitignore::GitignoreMatcher;
use crate::ignore_stack::load_child_specs;
use crate::tags::TagRegistry;
use crate::walker_filter::is_valid_descent_dir;
use crate::walker_prune::{PrunePoll, PruneSearch};
use crate::walker_step::{
    ActiveRootState, PendingSubdirPrune, drain_candidate_batch, enter_directory_state,
};
use crate::walker_types::{DirKey, WalkConfig, WalkEvent};

pub(crate) fn has_work_remaining(state: &ActiveRootState) -> bool {
    state.pending_batch.is_some()
        || state.pending_subdir_prune.is_some()
        || !state.stack.is_empty()
}

pub(crate) fn finish_subdir_descent(
    config: &WalkConfig,
    state: &mut ActiveRootState,
    subdir: PathBuf,
    child_specs: Arc<[GitignoreMatcher]>,
    child_depth: usize,
    child_inh: bool,
    events: &mut Vec<WalkEvent>,
) {
    let allow = if config.follow_symlinks {
        DirKey::from_dir(&subdir).is_some_and(|dk| state.visited_dirs.insert(dk))
    } else {
        true
    };
    if allow {
        enter_directory_state(
            config,
            state,
            &subdir,
            child_specs,
            child_depth,
            child_inh,
            events,
        );
    }
}

pub(crate) fn advance_active_root(
    config: &WalkConfig,
    registry: &'static TagRegistry,
    mut state: ActiveRootState,
    events: &mut Vec<WalkEvent>,
    cap: usize,
) -> Option<ActiveRootState> {
    if state.pending_batch.is_some() {
        drain_candidate_batch(config, registry, &mut state, events, cap);
        return has_work_remaining(&state).then_some(state);
    }
    if let Some(mut pending) = state.pending_subdir_prune.take() {
        match pending.search.poll(
            &state.base_root,
            state.root_dev,
            config,
            registry,
            &mut state.prune_memo,
            events,
        ) {
            PrunePoll::Matched => {
                finish_subdir_descent(
                    config,
                    &mut state,
                    pending.subdir,
                    pending.child_specs,
                    pending.child_depth,
                    pending.child_inh,
                    events,
                );
            }
            PrunePoll::Empty => {}
            PrunePoll::YieldedError => {
                state.pending_subdir_prune = Some(pending);
            }
        }
        return has_work_remaining(&state).then_some(state);
    }

    let top = state.stack.last_mut()?;
    if top.idx >= top.subdirs.len() {
        if let Some(popped) = state.stack.pop() {
            state.pending_batch = popped.deferred_batch;
        }
        return has_work_remaining(&state).then_some(state);
    }

    let subdir = top.subdirs[top.idx].clone();
    top.idx += 1;
    if !is_valid_descent_dir(&subdir, config.follow_symlinks) {
        return has_work_remaining(&state).then_some(state);
    }

    let parent_specs = Arc::clone(&top.specs);
    let child_depth = top.depth + 1;
    let parent_inh = top.inherited_match;
    let child_specs = load_child_specs(&subdir, &parent_specs, config.respect_gitignore);
    let child_inh =
        config
            .matcher
            .should_inherit_match(&subdir, Some(&state.base_root), parent_inh);

    if config.dirs_only && config.prune_empty {
        let mut search =
            PruneSearch::new(subdir.clone(), Arc::clone(&child_specs), child_depth, child_inh);
        match search.poll(
            &state.base_root,
            state.root_dev,
            config,
            registry,
            &mut state.prune_memo,
            events,
        ) {
            PrunePoll::Matched => {
                finish_subdir_descent(
                    config,
                    &mut state,
                    subdir,
                    child_specs,
                    child_depth,
                    child_inh,
                    events,
                );
            }
            PrunePoll::Empty => {}
            PrunePoll::YieldedError => {
                state.pending_subdir_prune = Some(PendingSubdirPrune {
                    subdir,
                    child_specs,
                    child_depth,
                    child_inh,
                    search,
                });
            }
        }
    } else {
        finish_subdir_descent(
            config,
            &mut state,
            subdir,
            child_specs,
            child_depth,
            child_inh,
            events,
        );
    }

    has_work_remaining(&state).then_some(state)
}
