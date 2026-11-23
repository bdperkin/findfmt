//! Memoized iterative `--prune` descendant search mirroring `_descendants.py` (#582).

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
    DirKey, PruneCache, ScannedEntry, WalkConfig, WalkEvent, WalkOsError,
    surrogateescape_codepoints,
};

struct PruneFrame {
    dir_key: DirKey,
    subdirs: Vec<PathBuf>,
    idx: usize,
    specs: Arc<[GitignoreMatcher]>,
    depth: usize,
    inherited_match: bool,
    had_cycle_skip: bool,
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

#[allow(clippy::too_many_arguments)]
fn step_prune_dir(
    directory: &Path,
    specs: &Arc<[GitignoreMatcher]>,
    current_depth: usize,
    inherited_match: bool,
    base_root: &Path,
    root_dev: Option<u64>,
    config: &WalkConfig,
    registry: &TagRegistry,
    visited: &mut HashSet<DirKey>,
    memo: &mut HashMap<DirKey, PruneCache>,
    frames: &mut Vec<PruneFrame>,
    events: &mut Vec<WalkEvent>,
) -> bool {
    if !is_valid_descent_dir(directory, config.follow_symlinks) {
        return false;
    }
    let Some(dir_key) = DirKey::from_dir(directory) else {
        return false;
    };
    if visited.contains(&dir_key) {
        if let Some(parent) = frames.last_mut() {
            parent.had_cycle_skip = true;
        }
        return false;
    }
    if let Some(&cached) = memo.get(&dir_key) {
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
    let Some(entries) = scan_sorted_for_prune(directory, config.follow_symlinks, events) else {
        if events.len() > err_before {
            memo.insert(
                dir_key,
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
                let exec_hint = if needs_exec {
                    executable_hint_for_skip(
                        &entry_path,
                        &filename,
                        is_symlink,
                        config.follow_symlinks,
                    )
                } else {
                    None
                };
                let guessed_mime = if needs_mime {
                    let str_path = entry_path.to_string_lossy();
                    config.mime_snapshot.guess_mime_type(&str_path)
                } else {
                    None
                };
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
            let raw_in =
                build_raw_classify_input(entry_path.clone(), config.follow_symlinks, None, config);
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
                    dir_key,
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
            dir_key,
            PruneCache::Empty {
                searched_from_depth: 0,
                had_cycle_skip: false,
            },
        );
        return false;
    }
    if config.max_depth.is_some_and(|max_d| current_depth >= max_d) {
        memo.insert(
            dir_key,
            PruneCache::Empty {
                searched_from_depth: current_depth,
                had_cycle_skip: false,
            },
        );
        return false;
    }

    visited.insert(dir_key.clone());
    frames.push(PruneFrame {
        dir_key,
        subdirs,
        idx: 0,
        specs: Arc::clone(specs),
        depth: current_depth,
        inherited_match,
        had_cycle_skip: false,
    });
    false
}

/// Iterative memoized descendant search mirroring `boundaries.py:has_matching_descendants`.
#[allow(clippy::too_many_arguments)]
pub fn has_matching_descendants_nogil(
    directory: &Path,
    specs: &Arc<[GitignoreMatcher]>,
    current_depth: usize,
    inherited_match: bool,
    base_root: &Path,
    root_dev: Option<u64>,
    config: &WalkConfig,
    registry: &TagRegistry,
    memo: &mut HashMap<DirKey, PruneCache>,
    events: &mut Vec<WalkEvent>,
) -> bool {
    let mut visited: HashSet<DirKey> = HashSet::new();
    let mut frames: Vec<PruneFrame> = Vec::new();

    if step_prune_dir(
        directory,
        specs,
        current_depth,
        inherited_match,
        base_root,
        root_dev,
        config,
        registry,
        &mut visited,
        memo,
        &mut frames,
        events,
    ) {
        return true;
    }

    while let Some(top) = frames.last_mut() {
        if top.idx >= top.subdirs.len() {
            if let Some(popped) = frames.pop() {
                visited.remove(&popped.dir_key);
                if let Some(parent) = frames.last_mut().filter(|_| popped.had_cycle_skip) {
                    parent.had_cycle_skip = true;
                }
                memo.insert(
                    popped.dir_key,
                    PruneCache::Empty {
                        searched_from_depth: popped.depth,
                        had_cycle_skip: popped.had_cycle_skip,
                    },
                );
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

        if step_prune_dir(
            &subdir,
            &child_specs,
            child_depth,
            child_inh,
            base_root,
            root_dev,
            config,
            registry,
            &mut visited,
            memo,
            &mut frames,
            events,
        ) {
            for frame in &frames {
                memo.insert(
                    frame.dir_key.clone(),
                    PruneCache::Matched {
                        searched_from_depth: frame.depth,
                    },
                );
            }
            return true;
        }
    }
    false
}
