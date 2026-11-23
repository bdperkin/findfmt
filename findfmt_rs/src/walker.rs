//! Iterative GIL-free native directory walker mirroring `src/findfmt/traversal/engine.py` (#582).

use std::collections::{HashMap, HashSet, VecDeque};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::classifier::classify_one_nogil;
use crate::ignore_stack::{load_child_specs, resolve_root_specs};
use crate::tags::TagRegistry;
use crate::walker_filter::{build_raw_classify_input, resolve_relative_pathbuf};
use crate::walker_prune::has_matching_descendants_nogil;
use crate::walker_sort::calculate_accumulated_sizes_nogil;
use crate::walker_step::{ActiveRootState, drain_candidate_batch, enter_directory_state};
use crate::walker_types::{DirKey, RootTarget, WalkConfig, WalkEvent, WalkYieldItem};

/// Streaming GIL-free directory traversal state machine.
pub struct NativeWalker {
    config: WalkConfig,
    registry: &'static TagRegistry,
    roots: VecDeque<RootTarget>,
    active_root: Option<ActiveRootState>,
}

impl NativeWalker {
    /// Construct a new `NativeWalker` over pre-resolved `RootTarget`s.
    pub fn new(
        config: WalkConfig,
        registry: &'static TagRegistry,
        roots: Vec<RootTarget>,
    ) -> Self {
        Self {
            config,
            registry,
            roots: VecDeque::from(roots),
            active_root: None,
        }
    }

    /// Advance traversal without the GIL until at least one event is ready (up to `max_events`) or EOF.
    pub fn next_batch(&mut self, max_events: usize) -> Vec<WalkEvent> {
        let cap = max_events.max(1);
        let mut events = Vec::new();
        while events.len() < cap {
            if self.active_root.is_some() {
                self.step_active_root(&mut events, cap);
            } else if let Some(target) = self.roots.pop_front() {
                self.start_root(target, &mut events);
            } else {
                break;
            }
        }
        events
    }

    fn start_root(&mut self, target: RootTarget, events: &mut Vec<WalkEvent>) {
        if let Some(err) = target.initial_error {
            events.push(WalkEvent::Error(err));
        }
        let Some(resolved_root) = target.resolved_root else {
            return;
        };

        let is_symlink = fs::symlink_metadata(&resolved_root)
            .is_ok_and(|m| m.file_type().is_symlink());
        let is_file_root = (!self.config.follow_symlinks && is_symlink)
            || fs::metadata(&resolved_root).is_ok_and(|m| m.is_file());

        if is_file_root {
            if !self.config.dirs_only {
                let parent_root = resolved_root
                    .parent()
                    .map_or_else(|| PathBuf::from("."), Path::to_path_buf);
                let raw_in = build_raw_classify_input(
                    resolved_root.clone(),
                    self.config.follow_symlinks,
                    None,
                    &self.config,
                );
                let classified = classify_one_nogil(
                    &raw_in,
                    self.registry,
                    self.config.pathext_upper.as_deref(),
                );
                let is_dir_item = classified.is_dir || classified.tags.contains("directory");
                let rel_pb = resolve_relative_pathbuf(
                    &resolved_root,
                    &parent_root,
                    target.prefix.as_deref(),
                );
                if self.config.filter.matches(
                    &classified.tags,
                    classified.shebang.as_deref(),
                    is_dir_item,
                ) && self
                    .config
                    .matcher
                    .matches_classified_item(&rel_pb, is_dir_item, false)
                {
                    events.push(WalkEvent::Item(WalkYieldItem {
                        path: resolved_root,
                        str_path: raw_in.str_path,
                        filename: raw_in.filename,
                        root_path: parent_root,
                        prefix: target.prefix,
                        has_entry: false,
                        follow_symlinks: self.config.follow_symlinks,
                        classified,
                    }));
                }
            }
            return;
        }

        let is_dir_root = fs::metadata(&resolved_root).is_ok_and(|m| m.is_dir());
        if !is_dir_root {
            return;
        }

        let accumulated_sizes = self.config.accumulate_size.then(|| {
            calculate_accumulated_sizes_nogil(
                &resolved_root,
                self.config.follow_symlinks,
                self.config.include_hidden,
            )
        });
        #[cfg(unix)]
        let root_dev = if self.config.one_file_system {
            use std::os::unix::fs::MetadataExt;
            fs::metadata(&resolved_root).ok().map(|m| m.dev())
        } else {
            None
        };
        #[cfg(not(unix))]
        let root_dev = None;

        #[cfg(not(unix))]
        let root_canon = if self.config.one_file_system {
            fs::canonicalize(&resolved_root).ok()
        } else {
            None
        };
        #[cfg(unix)]
        let root_canon = None;

        let mut visited_dirs = HashSet::new();
        if self.config.follow_symlinks {
            if let Some(dk) = DirKey::from_dir(&resolved_root) {
                visited_dirs.insert(dk);
            }
        }
        let root_specs = resolve_root_specs(
            &resolved_root,
            self.config.respect_gitignore,
            self.config.custom_gitignore_file.as_deref(),
            self.config.home_dir.as_deref(),
        );

        let mut root_state = ActiveRootState {
            base_root: resolved_root.clone(),
            prefix: target.prefix,
            root_dev,
            root_canon,
            visited_dirs,
            accumulated_sizes,
            prune_memo: HashMap::new(),
            stack: Vec::new(),
            pending_batch: None,
        };
        enter_directory_state(
            &self.config,
            &mut root_state,
            &resolved_root,
            root_specs,
            1,
            false,
            events,
        );
        self.active_root = Some(root_state);
    }

    fn step_active_root(&mut self, events: &mut Vec<WalkEvent>, cap: usize) {
        let Some(mut state) = self.active_root.take() else {
            return;
        };
        if state.pending_batch.is_some() {
            drain_candidate_batch(&self.config, self.registry, &mut state, events, cap);
            if state.pending_batch.is_some() || !state.stack.is_empty() {
                self.active_root = Some(state);
            }
            return;
        }

        let Some(top) = state.stack.last_mut() else {
            return;
        };
        if top.idx >= top.subdirs.len() {
            if let Some(popped) = state.stack.pop() {
                state.pending_batch = popped.deferred_batch;
            }
            if state.pending_batch.is_some() || !state.stack.is_empty() {
                self.active_root = Some(state);
            }
            return;
        }

        let subdir = top.subdirs[top.idx].clone();
        top.idx += 1;
        let parent_specs = Arc::clone(&top.specs);
        let child_depth = top.depth + 1;
        let parent_inh = top.inherited_match;
        let child_specs = load_child_specs(&subdir, &parent_specs, self.config.respect_gitignore);
        let child_inh = self.config.matcher.should_inherit_match(
            &subdir,
            Some(&state.base_root),
            parent_inh,
        );

        let should_enter = if self.config.dirs_only
            && self.config.prune_empty
            && !has_matching_descendants_nogil(
                &subdir,
                &child_specs,
                child_depth,
                child_inh,
                &state.base_root,
                state.root_dev,
                state.root_canon.as_deref(),
                &self.config,
                self.registry,
                &mut state.prune_memo,
                events,
            ) {
            false
        } else if self.config.follow_symlinks {
            match DirKey::from_dir(&subdir) {
                Some(dk) => state.visited_dirs.insert(dk),
                None => false,
            }
        } else {
            true
        };

        if should_enter {
            enter_directory_state(
                &self.config,
                &mut state,
                &subdir,
                child_specs,
                child_depth,
                child_inh,
                events,
            );
        }
        if state.pending_batch.is_some() || !state.stack.is_empty() {
            self.active_root = Some(state);
        }
    }
}
