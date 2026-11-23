//! Resumable, memoized iterative `--prune` descendant search mirroring `_descendants.py` (#582).

use std::collections::{HashMap, HashSet};
use std::fs;
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
use crate::walker_types::{
    DirKey, PruneCache, PruneMemoKey, ScannedEntry, WalkConfig, WalkEvent, WalkOsError,
    surrogateescape_codepoints,
};

/// Outcome of advancing a resumable `PruneSearch` up to the next completion or `on_error` pause.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PrunePoll {
    Matched,
    Empty,
    YieldedError,
}

#[derive(Clone, Debug)]
struct PruneFrame {
    dir_key: DirKey,
    memo_key: PruneMemoKey,
    subdirs: Vec<PathBuf>,
    idx: usize,
    specs: Arc<[GitignoreMatcher]>,
    depth: usize,
    inherited_match: bool,
    had_incomplete_child: bool,
}

/// Resumable iterative descendant search state that pauses immediately at any directory error.
#[derive(Clone, Debug)]
pub struct PruneSearch {
    initial_target: Option<(PathBuf, Arc<[GitignoreMatcher]>, usize, bool)>,
    visited: HashSet<DirKey>,
    frames: Vec<PruneFrame>,
}

fn make_memo_key(dir_key: &DirKey, directory: &Path, config: &WalkConfig) -> PruneMemoKey {
    let scoped_path = (config.follow_symlinks
        && (config.matcher.is_active()
            || config.respect_gitignore
            || config.custom_gitignore_file.is_some()))
    .then(|| directory.to_path_buf());
    (dir_key.clone(), scoped_path)
}

fn scan_sorted_for_prune(
    directory: &Path,
    follow_symlinks: bool,
    events: &mut Vec<WalkEvent>,
) -> Option<Vec<ScannedEntry>> {
    if !is_valid_descent_dir(directory, follow_symlinks) {
        return None;
    }
    let rd = match fs::read_dir(directory) {
        Ok(r) => r,
        Err(err) => {
            events.push(WalkEvent::Error(WalkOsError::from_io(&err, directory)));
            return None;
        }
    };
    let mut entries = Vec::with_capacity(16);
    for item_res in rd {
        let ent = match item_res {
            Ok(e) => e,
            Err(err) => {
                events.push(WalkEvent::Error(WalkOsError::from_io(&err, directory)));
                return None;
            }
        };
        entries.push(ScannedEntry {
            path: ent.path(),
            file_name: ent.file_name(),
            file_type: ent.file_type().ok(),
        });
    }
    entries.sort_by_key(|e| surrogateescape_codepoints(&e.file_name, false));
    Some(entries)
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
            if self.inspect_dir(
                &dir,
                &specs,
                depth,
                inherited,
                base_root,
                root_dev,
                config,
                registry,
                memo,
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
                    if !popped.had_incomplete_child {
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
            if self.inspect_dir(
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
                for frame in &self.frames {
                    memo.insert(
                        frame.memo_key.clone(),
                        PruneCache::Matched {
                            searched_from_depth: frame.depth,
                        },
                    );
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

    #[allow(clippy::too_many_arguments)]
    fn inspect_dir(
        &mut self,
        directory: &Path,
        specs: &Arc<[GitignoreMatcher]>,
        current_depth: usize,
        inherited_match: bool,
        base_root: &Path,
        root_dev: Option<u64>,
        config: &WalkConfig,
        registry: &TagRegistry,
        memo: &mut HashMap<PruneMemoKey, PruneCache>,
        events: &mut Vec<WalkEvent>,
    ) -> bool {
        if !is_valid_descent_dir(directory, config.follow_symlinks) {
            return false;
        }
        let Some(dir_key) = DirKey::from_dir(directory) else {
            return false;
        };
        if self.visited.contains(&dir_key) {
            if let Some(parent) = self.frames.last_mut() {
                parent.had_incomplete_child = true;
            }
            return false;
        }
        let memo_key = make_memo_key(&dir_key, directory, config);
        if let Some(&cached) = memo.get(&memo_key) {
            match cached {
                PruneCache::Matched {
                    searched_from_depth,
                } if config.max_depth.is_none() || current_depth <= searched_from_depth => {
                    return true;
                }
                PruneCache::Empty {
                    searched_from_depth,
                    had_cycle_skip,
                } if !had_cycle_skip
                    && (config.max_depth.is_none() || current_depth >= searched_from_depth) =>
                {
                    return false;
                }
                _ => {}
            }
        }

        let err_before = events.len();
        let Some(entries) = scan_sorted_for_prune(directory, config.follow_symlinks, events)
        else {
            if events.len() > err_before {
                memo.insert(
                    memo_key,
                    PruneCache::Empty {
                        searched_from_depth: 0,
                        had_cycle_skip: false,
                    },
                );
            }
            return false;
        };

        let (tag_active, needs_mime, needs_exec) = tag_prefilter_requirements(&config.filter);
        let mut subdirs = Vec::new();
        for entry in &entries {
            let Some((entry_path, is_dir, is_cand_file, is_symlink)) =
                filter_entry_nogil(entry, config, specs, root_dev, base_root)
            else {
                continue;
            };
            if is_dir {
                if !should_skip_dir(&entry.file_name, config.include_hidden) {
                    subdirs.push(entry_path);
                }
            } else if is_cand_file {
                if tag_active {
                    let filename = entry.file_name.to_string_lossy();
                    let exec_hint = needs_exec
                        .then(|| {
                            executable_hint_for_skip(
                                &entry_path,
                                &filename,
                                is_symlink,
                                config.follow_symlinks,
                            )
                        })
                        .flatten();
                    let guessed_mime = needs_mime
                        .then(|| {
                            let str_path = entry_path.to_string_lossy();
                            config.mime_snapshot.guess_mime_type(&str_path)
                        })
                        .flatten();
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
                let raw_in = build_raw_classify_input(
                    entry_path.clone(),
                    config.follow_symlinks,
                    None,
                    config,
                );
                let classified =
                    classify_one_nogil(&raw_in, registry, config.pathext_upper.as_deref());
                let is_dir_item = classified.is_dir || classified.tags.contains("directory");
                let rel_pb = resolve_relative_pathbuf(&entry_path, base_root, None);
                if config.filter.matches(
                    &classified.tags,
                    classified.shebang.as_deref(),
                    is_dir_item,
                ) && config.matcher.matches_classified_item(
                    &rel_pb,
                    is_dir_item,
                    inherited_match,
                ) {
                    memo.insert(
                        memo_key,
                        PruneCache::Matched {
                            searched_from_depth: usize::MAX,
                        },
                    );
                    return true;
                }
            }
        }

        if subdirs.is_empty() {
            memo.insert(
                memo_key,
                PruneCache::Empty {
                    searched_from_depth: 0,
                    had_cycle_skip: false,
                },
            );
            return false;
        }
        if config.max_depth.is_some_and(|max_d| current_depth >= max_d) {
            if let Some(parent) = self.frames.last_mut() {
                parent.had_incomplete_child = true;
            }
            return false;
        }

        self.visited.insert(dir_key.clone());
        self.frames.push(PruneFrame {
            dir_key,
            memo_key,
            subdirs,
            idx: 0,
            specs: Arc::clone(specs),
            depth: current_depth,
            inherited_match,
            had_incomplete_child: false,
        });
        false
    }
}
