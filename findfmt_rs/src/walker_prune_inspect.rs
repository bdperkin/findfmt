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
use crate::walker_sort::collect_scanned_entries;
use crate::walker_types::{
    DirKey, PruneCache, PruneMemoKey, ScannedEntry, WalkConfig, WalkEvent, WalkOsError,
    surrogateescape_codepoints,
};

fn scan_sorted_for_prune(
    directory: &Path,
    events: &mut Vec<WalkEvent>,
) -> Option<Vec<ScannedEntry>> {
    let rd = match fs::read_dir(directory) {
        Ok(r) => r,
        Err(err) => {
            events.push(WalkEvent::Error(WalkOsError::from_io(&err, directory)));
            return None;
        }
    };
    let mapped = rd.map(|res| {
        res.map(|ent| ScannedEntry {
            path: ent.path(),
            file_name: ent.file_name(),
            file_type: ent.file_type().ok(),
        })
    });
    let mut entries = collect_scanned_entries(directory, mapped, None, events)?;
    entries.sort_by_key(|e| surrogateescape_codepoints(&e.file_name, false));
    Some(entries)
}

fn check_prune_memo(
    memo: &HashMap<PruneMemoKey, PruneCache>,
    memo_key: &PruneMemoKey,
    current_depth: usize,
    max_depth: Option<usize>,
) -> Option<bool> {
    let &cached = memo.get(memo_key)?;
    match cached {
        PruneCache::Matched {
            searched_from_depth,
        } if max_depth.is_none() || current_depth <= searched_from_depth => Some(true),
        PruneCache::Empty {
            searched_from_depth,
            had_cycle_skip,
        } if !had_cycle_skip && (max_depth.is_none() || current_depth >= searched_from_depth) => {
            Some(false)
        }
        _ => None,
    }
}

fn prune_candidate_matches(
    entry: &ScannedEntry,
    entry_path: PathBuf,
    is_symlink: bool,
    inherited_match: bool,
    base_root: &Path,
    config: &WalkConfig,
    registry: &TagRegistry,
) -> bool {
    let (tag_active, needs_mime, needs_exec) = tag_prefilter_requirements(&config.filter);
    if tag_active {
        let filename = entry.file_name.to_string_lossy();
        let exec_hint = needs_exec
            .then(|| {
                executable_hint_for_skip(
                    &entry_path,
                    &filename,
                    is_symlink,
                    config.scope.follow_symlinks,
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
            config.scope.follow_symlinks,
            exec_hint,
            &config.filter,
            registry,
            guessed_mime.as_deref(),
        ) {
            return false;
        }
    }
    let rel_pb = resolve_relative_pathbuf(&entry_path, base_root, None);
    let raw_in = build_raw_classify_input(entry_path, config.scope.follow_symlinks, None, config);
    let classified = classify_one_nogil(&raw_in, registry, config.pathext_upper.as_deref());
    let is_dir_item = classified.is_dir || classified.tags.contains("directory");
    config
        .filter
        .matches(&classified.tags, classified.shebang.as_deref(), is_dir_item)
        && config
            .matcher
            .matches_classified_item(&rel_pb, is_dir_item, inherited_match)
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
    if !is_valid_descent_dir(directory, config.scope.follow_symlinks) {
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
    if let Some(hit) = check_prune_memo(memo, &memo_key, current_depth, config.bounds.max_depth) {
        return hit;
    }

    let Some(entries) = scan_sorted_for_prune(directory, events) else {
        if let Some(parent) = search.frames.last_mut() {
            parent.had_incomplete_child = true;
        }
        memo.insert(
            memo_key,
            PruneCache::Empty {
                searched_from_depth: 0,
                had_cycle_skip: false,
            },
        );
        return false;
    };

    let mut subdirs: Vec<PathBuf> = Vec::new();
    for entry in &entries {
        let Some((entry_path, is_dir, is_cand_file, is_symlink)) =
            filter_entry_nogil(entry, config, specs, root_dev, base_root)
        else {
            continue;
        };
        if is_dir {
            if !should_skip_dir(&entry.file_name, config.scope.include_hidden) {
                subdirs.push(entry_path);
            }
        } else if is_cand_file
            && prune_candidate_matches(
                entry,
                entry_path,
                is_symlink,
                inherited_match,
                base_root,
                config,
                registry,
            )
        {
            memo.insert(
                memo_key,
                PruneCache::Matched {
                    searched_from_depth: usize::MAX,
                },
            );
            return true;
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
    if config
        .bounds
        .max_depth
        .is_some_and(|max_d| current_depth >= max_d)
    {
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
