//! Single-directory candidate inspection for resumable `PruneSearch` (#582).

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::classifier::classify_one_nogil;
use crate::gitignore::GitignoreMatcher;
use crate::patterns::{can_skip_entry_by_tags, tag_prefilter_requirements};
use crate::tags::TagRegistry;
use crate::walker_filter::{
    build_raw_classify_input, executable_hint_for_skip, filter_entry_nogil, is_valid_descent_dir,
    resolve_relative_pathbuf, should_skip_dir,
};
use crate::walker_prune::{PruneFrame, PruneSearch, make_memo_key};
use crate::walker_types::{
    DirKey, PruneCache, PruneMemoKey, ScannedEntry, WalkConfig, WalkEvent, WalkOsError,
    surrogateescape_codepoints,
};

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
pub(crate) fn inspect_prune_dir(
    search: &mut PruneSearch,
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
    if search.visited.contains(&dir_key) {
        if let Some(parent) = search.frames.last_mut() {
            parent.had_incomplete_child = true;
        }
        return false;
    }
    let memo_key = make_memo_key(&dir_key, directory, base_root, specs, config);
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
    let Some(entries) = scan_sorted_for_prune(directory, config.follow_symlinks, events) else {
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
    let mut subdirs: Vec<PathBuf> = Vec::new();
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
            let raw_in =
                build_raw_classify_input(entry_path.clone(), config.follow_symlinks, None, config);
            let classified = classify_one_nogil(&raw_in, registry, config.pathext_upper.as_deref());
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
        if let Some(parent) = search.frames.last_mut() {
            parent.had_incomplete_child = true;
        }
        return false;
    }

    search.visited.insert(dir_key.clone());
    search.frames.push(PruneFrame {
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
