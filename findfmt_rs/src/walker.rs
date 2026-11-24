//! Iterative GIL-free native directory walker mirroring `src/findfmt/traversal/engine.py` (#582).

use std::collections::{HashMap, HashSet, VecDeque};
use std::fs;
use std::path::{Path, PathBuf};

use crate::classifier::classify_one_nogil;
use crate::ignore_stack::resolve_root_specs;
use crate::tags::TagRegistry;
use crate::walker_descent::advance_active_root;
use crate::walker_filter::{build_raw_classify_input, resolve_device_id, resolve_relative_pathbuf};
use crate::walker_sort::calculate_accumulated_sizes_nogil;
use crate::walker_step::{ActiveRootState, enter_directory_state};
use crate::walker_types::{DirKey, RootTarget, WalkConfig, WalkEvent, WalkYieldItem};

/// Streaming GIL-free directory traversal state machine.
pub struct NativeWalker {
    config: WalkConfig,
    registry: &'static TagRegistry,
    roots: VecDeque<RootTarget>,
    active_root: Option<ActiveRootState>,
    overflow: VecDeque<WalkEvent>,
}

impl NativeWalker {
    /// Construct a new `NativeWalker` over pre-resolved `RootTarget`s.
    pub fn new(config: WalkConfig, registry: &'static TagRegistry, roots: Vec<RootTarget>) -> Self {
        Self {
            config,
            registry,
            roots: VecDeque::from(roots),
            active_root: None,
            overflow: VecDeque::new(),
        }
    }

    /// Advance traversal without the GIL up to `max_events`, pausing immediately at any error boundary.
    pub fn next_batch(&mut self, max_events: usize) -> Vec<WalkEvent> {
        let cap = max_events.max(1);
        let mut out = Vec::new();

        while out.len() < cap {
            let Some(ev) = self.overflow.pop_front() else {
                break;
            };
            let is_err = matches!(ev, WalkEvent::Error(_));
            out.push(ev);
            if is_err {
                return out;
            }
        }

        let mut step_events = Vec::new();
        while out.len() < cap {
            step_events.clear();
            let sub_cap = cap - out.len();
            if let Some(state) = self.active_root.take() {
                self.active_root = advance_active_root(
                    &self.config,
                    self.registry,
                    state,
                    &mut step_events,
                    sub_cap,
                );
            } else if let Some(target) = self.roots.pop_front() {
                self.start_root(target, &mut step_events);
            } else {
                break;
            }

            let mut hit_error = false;
            for ev in step_events.drain(..) {
                if !hit_error && out.len() < cap {
                    if matches!(ev, WalkEvent::Error(_)) {
                        hit_error = true;
                    }
                    out.push(ev);
                } else {
                    self.overflow.push_back(ev);
                }
            }
            if hit_error {
                break;
            }
        }
        out
    }

    fn emit_single_file_root(
        &self,
        resolved_root: PathBuf,
        prefix: Option<PathBuf>,
        events: &mut Vec<WalkEvent>,
    ) {
        if self.config.scope.dirs_only {
            return;
        }
        let parent_root = resolved_root
            .parent()
            .map_or_else(|| PathBuf::from("."), Path::to_path_buf);
        let raw_in = build_raw_classify_input(
            resolved_root.clone(),
            self.config.scope.follow_symlinks,
            None,
            &self.config,
        );
        let classified =
            classify_one_nogil(&raw_in, self.registry, self.config.pathext_upper.as_deref());
        let is_dir_item = classified.is_dir || classified.tags.contains("directory");
        let rel_pb = resolve_relative_pathbuf(&resolved_root, &parent_root, prefix.as_deref());
        if self
            .config
            .filter
            .matches(&classified.tags, classified.shebang.as_deref(), is_dir_item)
            && self
                .config
                .matcher
                .matches_classified_item(&rel_pb, is_dir_item, false)
        {
            events.push(WalkEvent::Item(Box::new(WalkYieldItem {
                path: resolved_root,
                str_path: raw_in.str_path,
                filename: raw_in.filename,
                root_path: parent_root,
                prefix,
                has_entry: false,
                follow_symlinks: self.config.scope.follow_symlinks,
                #[cfg(not(unix))]
                inherited_match: false,
                classified,
            })));
        }
    }

    fn start_root(&mut self, target: RootTarget, events: &mut Vec<WalkEvent>) {
        if let Some(err) = target.initial_error {
            events.push(WalkEvent::Error(err));
        }
        let Some(resolved_root) = target.resolved_root else {
            return;
        };

        let is_symlink =
            fs::symlink_metadata(&resolved_root).is_ok_and(|m| m.file_type().is_symlink());
        let is_file_root = (!self.config.scope.follow_symlinks && is_symlink)
            || fs::metadata(&resolved_root).is_ok_and(|m| m.is_file());

        if is_file_root {
            self.emit_single_file_root(resolved_root, target.prefix, events);
            return;
        }

        if !fs::metadata(&resolved_root).is_ok_and(|m| m.is_dir()) {
            return;
        }

        let accumulated_sizes = self.config.bounds.accumulate_size.then(|| {
            calculate_accumulated_sizes_nogil(
                &resolved_root,
                self.config.scope.follow_symlinks,
                self.config.scope.include_hidden,
            )
        });
        let root_dev = self
            .config
            .bounds
            .one_file_system
            .then(|| resolve_device_id(&resolved_root, false, true))
            .flatten();

        let mut visited_dirs = HashSet::new();
        if let Some(dk) = self
            .config
            .scope
            .follow_symlinks
            .then(|| DirKey::from_dir(&resolved_root))
            .flatten()
        {
            visited_dirs.insert(dk);
        }
        let root_specs = resolve_root_specs(
            &resolved_root,
            self.config.respect_gitignore,
            self.config.custom_gitignore_file.as_deref(),
            self.config.home_dir.as_deref(),
            &target.global_gitignore,
        );

        let mut root_state = ActiveRootState {
            base_root: resolved_root.clone(),
            prefix: target.prefix,
            root_dev,
            visited_dirs,
            accumulated_sizes,
            prune_memo: HashMap::new(),
            stack: Vec::new(),
            pending_batch: None,
            pending_subdir_prune: None,
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
}
