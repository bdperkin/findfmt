//! Per-directory entry partitioning and bounded-chunk candidate emission (#582).

use std::collections::{HashMap, HashSet, VecDeque};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::classifier::classify_one_nogil;
use crate::gitignore::GitignoreMatcher;
use crate::ignore_stack::load_child_specs;
use crate::patterns::{can_skip_entry_by_tags, tag_prefilter_requirements};
use crate::tags::TagRegistry;
use crate::walker_filter::{
    build_raw_classify_input, executable_hint_for_skip, filter_entry_nogil, is_valid_descent_dir,
    resolve_relative_pathbuf, should_skip_dir,
};
use crate::walker_prune::{PrunePoll, PruneSearch};
use crate::walker_sort::collect_and_sort_entries;
use crate::walker_types::{DirKey, PruneCache, PruneMemoKey, WalkConfig, WalkEvent, WalkYieldItem};

#[derive(Clone, Debug)]
pub(crate) struct CandidateBatch {
    pub targets: VecDeque<(PathBuf, bool)>,
    pub active_prune: Option<((PathBuf, bool), PruneSearch)>,
    pub specs: Arc<[GitignoreMatcher]>,
    pub depth: usize,
    pub inherited_match: bool,
}

#[derive(Clone, Debug)]
pub(crate) struct PendingSubdirPrune {
    pub subdir: PathBuf,
    pub child_specs: Arc<[GitignoreMatcher]>,
    pub child_depth: usize,
    pub child_inh: bool,
    pub search: PruneSearch,
}

pub(crate) struct WalkFrame {
    pub subdirs: Vec<PathBuf>,
    pub idx: usize,
    pub specs: Arc<[GitignoreMatcher]>,
    pub depth: usize,
    pub inherited_match: bool,
    pub deferred_batch: Option<CandidateBatch>,
}

pub(crate) struct ActiveRootState {
    pub base_root: PathBuf,
    pub prefix: Option<PathBuf>,
    pub root_dev: Option<u64>,
    pub visited_dirs: HashSet<DirKey>,
    pub accumulated_sizes: Option<HashMap<PathBuf, u64>>,
    pub prune_memo: HashMap<PruneMemoKey, PruneCache>,
    pub stack: Vec<WalkFrame>,
    pub pending_batch: Option<CandidateBatch>,
    pub pending_subdir_prune: Option<PendingSubdirPrune>,
}

pub(crate) fn enter_directory_state(
    config: &WalkConfig,
    state: &mut ActiveRootState,
    curr_dir: &Path,
    specs: Arc<[GitignoreMatcher]>,
    current_depth: usize,
    inherited_match: bool,
    events: &mut Vec<WalkEvent>,
) {
    let Some(entries) = collect_and_sort_entries(curr_dir, config, events) else {
        return;
    };
    let mut subdirs = Vec::new();
    let mut files = Vec::new();

    for entry in entries {
        let Some((entry_path, is_dir, is_cand_file, is_symlink)) =
            filter_entry_nogil(&entry, config, &specs, state.root_dev, &state.base_root)
        else {
            continue;
        };
        if is_dir {
            if !should_skip_dir(&entry.file_name, config.scope.include_hidden) {
                subdirs.push(entry_path);
            }
        } else if is_cand_file {
            files.push((entry_path, is_symlink));
        }
    }

    let raw_targets: VecDeque<(PathBuf, bool)> = if config.scope.dirs_only {
        subdirs.iter().cloned().map(|p| (p, false)).collect()
    } else {
        VecDeque::from(files)
    };
    let batch = (!raw_targets.is_empty()).then(|| CandidateBatch {
        targets: raw_targets,
        active_prune: None,
        specs: Arc::clone(&specs),
        depth: current_depth,
        inherited_match,
    });

    let can_descend = config
        .bounds
        .max_depth
        .is_none_or(|max_d| current_depth < max_d)
        && !subdirs.is_empty();

    if config.sort.dirs_first && can_descend {
        state.stack.push(WalkFrame {
            subdirs,
            idx: 0,
            specs,
            depth: current_depth,
            inherited_match,
            deferred_batch: batch,
        });
        return;
    }

    state.pending_batch = batch;
    if can_descend {
        state.stack.push(WalkFrame {
            subdirs,
            idx: 0,
            specs,
            depth: current_depth,
            inherited_match,
            deferred_batch: None,
        });
    }
}

enum BatchStep {
    Ready(PathBuf, bool),
    Skip,
    PauseOrDone,
}

fn next_batch_candidate(
    batch: &mut CandidateBatch,
    config: &WalkConfig,
    registry: &TagRegistry,
    state: &mut ActiveRootState,
    events: &mut Vec<WalkEvent>,
) -> BatchStep {
    if let Some((cand, mut search)) = batch.active_prune.take() {
        return match search.poll(
            &state.base_root,
            state.root_dev,
            config,
            registry,
            &mut state.prune_memo,
            events,
        ) {
            PrunePoll::Matched => BatchStep::Ready(cand.0, cand.1),
            PrunePoll::Empty => BatchStep::Skip,
            PrunePoll::YieldedError => {
                batch.active_prune = Some((cand, search));
                BatchStep::PauseOrDone
            }
        };
    }

    let Some(cand) = batch.targets.pop_front() else {
        return BatchStep::PauseOrDone;
    };
    if !config.scope.dirs_only || !config.bounds.prune_empty {
        return BatchStep::Ready(cand.0, cand.1);
    }
    if !is_valid_descent_dir(&cand.0, config.scope.follow_symlinks) {
        return BatchStep::Skip;
    }
    let child_specs = load_child_specs(&cand.0, &batch.specs, config.respect_gitignore);
    let child_inh =
        config
            .matcher
            .should_inherit_match(&cand.0, Some(&state.base_root), batch.inherited_match);
    let mut search = PruneSearch::new(cand.0.clone(), child_specs, batch.depth + 1, child_inh);
    match search.poll(
        &state.base_root,
        state.root_dev,
        config,
        registry,
        &mut state.prune_memo,
        events,
    ) {
        PrunePoll::Matched => BatchStep::Ready(cand.0, cand.1),
        PrunePoll::Empty => BatchStep::Skip,
        PrunePoll::YieldedError => {
            batch.active_prune = Some((cand, search));
            BatchStep::PauseOrDone
        }
    }
}

fn passes_file_prefilter(
    cand_path: &Path,
    rel_pb: &Path,
    is_symlink: bool,
    inherited_match: bool,
    prefilter: (bool, bool, bool),
    config: &WalkConfig,
    registry: &TagRegistry,
) -> bool {
    if config.matcher.is_active() && !config.matcher.matches_file(rel_pb, None, inherited_match) {
        return false;
    }
    let (tag_active, needs_mime, needs_exec) = prefilter;
    if !tag_active {
        return true;
    }
    let filename = cand_path
        .file_name()
        .map_or_else(String::new, |n| n.to_string_lossy().into_owned());
    let exec_hint = needs_exec
        .then(|| {
            executable_hint_for_skip(
                cand_path,
                &filename,
                is_symlink,
                config.scope.follow_symlinks,
            )
        })
        .flatten();
    let guessed_mime = needs_mime
        .then(|| {
            let str_path = cand_path.to_string_lossy();
            config.mime_snapshot.guess_mime_type(&str_path)
        })
        .flatten();
    !can_skip_entry_by_tags(
        &filename,
        is_symlink,
        config.scope.follow_symlinks,
        exec_hint,
        &config.filter,
        registry,
        guessed_mime.as_deref(),
    )
}

pub(crate) fn drain_candidate_batch(
    config: &WalkConfig,
    registry: &TagRegistry,
    state: &mut ActiveRootState,
    events: &mut Vec<WalkEvent>,
    cap: usize,
) {
    let Some(mut batch) = state.pending_batch.take() else {
        return;
    };
    let prefilter = tag_prefilter_requirements(&config.filter);

    while events.len() < cap {
        let (cand_path, is_symlink) =
            match next_batch_candidate(&mut batch, config, registry, state, events) {
                BatchStep::Ready(p, sym) => (p, sym),
                BatchStep::Skip => continue,
                BatchStep::PauseOrDone => break,
            };

        let rel_pb =
            resolve_relative_pathbuf(&cand_path, &state.base_root, state.prefix.as_deref());
        if !config.scope.dirs_only
            && !passes_file_prefilter(
                &cand_path,
                &rel_pb,
                is_symlink,
                batch.inherited_match,
                prefilter,
                config,
                registry,
            )
        {
            continue;
        }

        let accum = state
            .accumulated_sizes
            .as_ref()
            .and_then(|m| m.get(&cand_path).copied());
        let raw_in = build_raw_classify_input(
            cand_path.clone(),
            config.scope.follow_symlinks,
            accum,
            config,
        );
        let classified = classify_one_nogil(&raw_in, registry, config.pathext_upper.as_deref());
        let is_dir_item = classified.is_dir || classified.tags.contains("directory");
        if !config
            .filter
            .matches(&classified.tags, classified.shebang.as_deref(), is_dir_item)
            || !config
                .matcher
                .matches_classified_item(&rel_pb, is_dir_item, batch.inherited_match)
        {
            continue;
        }

        events.push(WalkEvent::Item(Box::new(WalkYieldItem {
            path: cand_path,
            str_path: raw_in.str_path,
            filename: raw_in.filename,
            root_path: state.base_root.clone(),
            prefix: state.prefix.clone(),
            has_entry: !config.scope.dirs_only,
            follow_symlinks: config.scope.follow_symlinks,
            #[cfg(not(unix))]
            inherited_match: batch.inherited_match,
            classified,
        })));
    }
    if batch.active_prune.is_some() || !batch.targets.is_empty() {
        state.pending_batch = Some(batch);
    }
}
