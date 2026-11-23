//! Per-directory entry partitioning and bounded-chunk candidate emission (#582).

use std::collections::{HashMap, HashSet, VecDeque};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::classifier::classify_one_nogil;
use crate::gitignore::GitignoreMatcher;
use crate::ignore_stack::load_child_specs;
use crate::patterns::can_skip_entry_by_tags;
use crate::tags::TagRegistry;
use crate::walker_filter::{
    build_raw_classify_input, executable_hint_for_skip, filter_entry_nogil,
    resolve_relative_pathbuf, should_skip_dir,
};
use crate::walker_prune::has_matching_descendants_nogil;
use crate::walker_sort::collect_and_sort_entries;
use crate::walker_types::{DirKey, WalkConfig, WalkEvent, WalkYieldItem};

#[derive(Clone, Debug)]
pub(crate) struct CandidateBatch {
    pub targets: VecDeque<(PathBuf, bool)>,
    pub specs: Arc<[GitignoreMatcher]>,
    pub depth: usize,
    pub inherited_match: bool,
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
    pub root_canon: Option<PathBuf>,
    pub visited_dirs: HashSet<DirKey>,
    pub accumulated_sizes: Option<HashMap<PathBuf, u64>>,
    pub prune_memo: HashMap<DirKey, bool>,
    pub stack: Vec<WalkFrame>,
    pub pending_batch: Option<CandidateBatch>,
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
        let Some((entry_path, is_dir, is_cand_file, is_symlink)) = filter_entry_nogil(
            &entry,
            config,
            &specs,
            state.root_dev,
            state.root_canon.as_deref(),
            &state.base_root,
        ) else {
            continue;
        };
        if is_dir {
            if !should_skip_dir(&entry.file_name, config.include_hidden) {
                subdirs.push(entry_path);
            }
        } else if is_cand_file {
            files.push((entry_path, is_symlink));
        }
    }

    let raw_targets: VecDeque<(PathBuf, bool)> = if config.dirs_only {
        subdirs.iter().cloned().map(|p| (p, false)).collect()
    } else {
        VecDeque::from(files)
    };
    let batch = (!raw_targets.is_empty()).then(|| CandidateBatch {
        targets: raw_targets,
        specs: Arc::clone(&specs),
        depth: current_depth,
        inherited_match,
    });

    let can_descend = config.max_depth.is_none_or(|max_d| current_depth < max_d) && !subdirs.is_empty();

    if config.dirs_first && can_descend {
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
    while events.len() < cap {
        let Some((cand_path, is_symlink)) = batch.targets.pop_front() else {
            break;
        };
        if config.dirs_only && config.prune_empty {
            let child_specs = load_child_specs(&cand_path, &batch.specs, config.respect_gitignore);
            if !has_matching_descendants_nogil(
                &cand_path,
                &child_specs,
                batch.depth + 1,
                batch.inherited_match,
                &state.base_root,
                state.root_dev,
                state.root_canon.as_deref(),
                config,
                registry,
                &mut state.prune_memo,
                events,
            ) {
                continue;
            }
        }

        let rel_pb =
            resolve_relative_pathbuf(&cand_path, &state.base_root, state.prefix.as_deref());
        if !config.dirs_only {
            if config.matcher.is_active()
                && !config
                    .matcher
                    .matches_file(&rel_pb, None, batch.inherited_match)
            {
                continue;
            }
            let filename = cand_path
                .file_name()
                .map_or_else(String::new, |n| n.to_string_lossy().into_owned());
            let exec_hint = executable_hint_for_skip(
                &cand_path,
                &filename,
                is_symlink,
                config.follow_symlinks,
            );
            let str_path = cand_path.to_string_lossy();
            let guessed_mime = config.mime_snapshot.guess_mime_type(&str_path);
            if can_skip_entry_by_tags(
                &filename,
                is_symlink,
                config.follow_symlinks,
                exec_hint,
                &config.filter,
                registry,
                guessed_mime.as_deref(),
            ) {
                continue;
            }
        }

        let accum = state
            .accumulated_sizes
            .as_ref()
            .and_then(|m| m.get(&cand_path).copied());
        let raw_in =
            build_raw_classify_input(cand_path.clone(), config.follow_symlinks, accum, config);
        let classified =
            classify_one_nogil(&raw_in, registry, config.pathext_upper.as_deref());
        let is_dir_item = classified.is_dir || classified.tags.contains("directory");
        if !config.filter.matches(
            &classified.tags,
            classified.shebang.as_deref(),
            is_dir_item,
        ) || !config.matcher.matches_classified_item(
            &rel_pb,
            is_dir_item,
            batch.inherited_match,
        ) {
            continue;
        }

        events.push(WalkEvent::Item(WalkYieldItem {
            path: cand_path,
            str_path: raw_in.str_path,
            filename: raw_in.filename,
            root_path: state.base_root.clone(),
            prefix: state.prefix.clone(),
            has_entry: !config.dirs_only,
            follow_symlinks: config.follow_symlinks,
            classified,
        }));
    }
    if !batch.targets.is_empty() {
        state.pending_batch = Some(batch);
    }
}
