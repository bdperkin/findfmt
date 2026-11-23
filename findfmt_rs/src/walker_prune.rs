//! Resumable, memoized iterative `--prune` descendant search mirroring `_descendants.py` (#582).

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::gitignore::GitignoreMatcher;
use crate::ignore_stack::load_child_specs;
use crate::tags::TagRegistry;
use crate::walker_filter::{is_valid_descent_dir, resolve_relative_pathbuf};
use crate::walker_prune_inspect::inspect_prune_dir;
use crate::walker_types::{DirKey, PruneCache, PruneMemoKey, WalkConfig, WalkEvent};

/// Outcome of advancing a resumable `PruneSearch` up to the next completion or `on_error` pause.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PrunePoll {
    Matched,
    Empty,
    YieldedError,
}

#[derive(Clone, Debug)]
pub(crate) struct PruneFrame {
    pub dir_key: DirKey,
    pub memo_key: PruneMemoKey,
    pub subdirs: Vec<PathBuf>,
    pub idx: usize,
    pub specs: Arc<[GitignoreMatcher]>,
    pub depth: usize,
    pub inherited_match: bool,
    pub had_incomplete_child: bool,
}

/// Resumable iterative descendant search state that pauses immediately at any directory error.
#[derive(Clone, Debug)]
pub struct PruneSearch {
    initial_target: Option<(PathBuf, Arc<[GitignoreMatcher]>, usize, bool)>,
    pub(crate) visited: HashSet<DirKey>,
    pub(crate) frames: Vec<PruneFrame>,
}

pub(crate) fn make_memo_key(
    dir_key: &DirKey,
    directory: &Path,
    base_root: &Path,
    specs: &[GitignoreMatcher],
    config: &WalkConfig,
) -> PruneMemoKey {
    let scoped_path = (config.follow_symlinks
        && (config.matcher.is_active()
            || !specs.is_empty()
            || config.respect_gitignore
            || config.custom_gitignore_file.is_some()))
    .then(|| resolve_relative_pathbuf(directory, base_root, None));
    (dir_key.clone(), scoped_path)
}

impl PruneSearch {
    /// Create a new resumable `--prune` search rooted at `directory`.
    pub fn new(
        directory: PathBuf,
        specs: Arc<[GitignoreMatcher]>,
        current_depth: usize,
        inherited_match: bool,
    ) -> Self {
        Self {
            initial_target: Some((directory, specs, current_depth, inherited_match)),
            visited: HashSet::new(),
            frames: Vec::new(),
        }
    }

    /// Advance the search without holding the GIL, pausing immediately if an I/O error is emitted.
    pub fn poll(
        &mut self,
        base_root: &Path,
        root_dev: Option<u64>,
        config: &WalkConfig,
        registry: &TagRegistry,
        memo: &mut HashMap<PruneMemoKey, PruneCache>,
        events: &mut Vec<WalkEvent>,
    ) -> PrunePoll {
        if let Some((dir, specs, depth, inherited)) = self.initial_target.take() {
            let err_before = events.len();
            if inspect_prune_dir(
                self, &dir, &specs, depth, inherited, base_root, root_dev, config, registry, memo,
                events,
            ) {
                return PrunePoll::Matched;
            }
            if events.len() > err_before {
                return PrunePoll::YieldedError;
            }
        }

        while let Some(top) = self.frames.last_mut() {
            if top.idx >= top.subdirs.len() {
                if let Some(popped) = self.frames.pop() {
                    self.visited.remove(&popped.dir_key);
                    if let Some(parent) =
                        self.frames.last_mut().filter(|_| popped.had_incomplete_child)
                    {
                        parent.had_incomplete_child = true;
                    }
                    if !popped.had_incomplete_child && config.max_depth.is_none() {
                        memo.insert(
                            popped.memo_key,
                            PruneCache::Empty {
                                searched_from_depth: popped.depth,
                                had_cycle_skip: false,
                            },
                        );
                    }
                }
                continue;
            }
            let subdir = top.subdirs[top.idx].clone();
            top.idx += 1;
            if !is_valid_descent_dir(&subdir, config.follow_symlinks) {
                continue;
            }
            let parent_specs = Arc::clone(&top.specs);
            let child_depth = top.depth + 1;
            let parent_inh = top.inherited_match;
            let child_specs = load_child_specs(&subdir, &parent_specs, config.respect_gitignore);
            let child_inh = config
                .matcher
                .should_inherit_match(&subdir, Some(base_root), parent_inh);

            let err_before = events.len();
            if inspect_prune_dir(
                self,
                &subdir,
                &child_specs,
                child_depth,
                child_inh,
                base_root,
                root_dev,
                config,
                registry,
                memo,
                events,
            ) {
                if config.max_depth.is_none() {
                    for frame in &self.frames {
                        memo.insert(
                            frame.memo_key.clone(),
                            PruneCache::Matched {
                                searched_from_depth: frame.depth,
                            },
                        );
                    }
                }
                self.frames.clear();
                self.visited.clear();
                return PrunePoll::Matched;
            }
            if events.len() > err_before {
                if let Some(parent) = self.frames.last_mut() {
                    parent.had_incomplete_child = true;
                }
                return PrunePoll::YieldedError;
            }
        }
        PrunePoll::Empty
    }
}
