//! Directory entry sorting (`--filelimit`, `SortKey`) and `--du` disk usage accumulation (#582).

use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use crate::metadata::RawStat;
use crate::sorting::natural_sort_key_osstr;
use crate::walker_filter::{is_hidden_name, is_valid_descent_dir};
use crate::walker_types::{
    DirKey, ScannedEntry, WalkConfig, WalkEvent, WalkOsError, WalkSortKey,
    surrogateescape_codepoints,
};

type MetricSortEntry = (Vec<u32>, (f64, f64, u64), ScannedEntry);

fn stat_sort_metrics(entry: &ScannedEntry, follow_symlinks: bool) -> (f64, f64, u64) {
    let is_sym = entry.file_type.as_ref().is_some_and(fs::FileType::is_symlink);
    let meta_res = if is_sym && follow_symlinks {
        fs::metadata(&entry.path)
    } else {
        fs::symlink_metadata(&entry.path)
    };
    let Ok(meta) = meta_res else {
        return (0.0, 0.0, 0);
    };
    let raw = RawStat::from_std_metadata(&meta);
    (raw.mtime.unwrap_or(0.0), raw.ctime.unwrap_or(0.0), raw.size)
}

/// Read and sort directory entries honoring `file_limit` and `sort_by` (`sorting.py` parity).
pub fn collect_and_sort_entries(
    dir: &Path,
    config: &WalkConfig,
    events: &mut Vec<WalkEvent>,
) -> Option<Vec<ScannedEntry>> {
    if !is_valid_descent_dir(dir, config.follow_symlinks) {
        return None;
    }
    let read_dir = match fs::read_dir(dir) {
        Ok(rd) => rd,
        Err(err) => {
            events.push(WalkEvent::Error(WalkOsError::from_io(&err, dir)));
            return None;
        }
    };
    let mut entries = Vec::new();
    for item_res in read_dir {
        let ent = match item_res {
            Ok(e) => e,
            Err(err) => {
                events.push(WalkEvent::Error(WalkOsError::from_io(&err, dir)));
                return None;
            }
        };
        entries.push(ScannedEntry {
            path: ent.path(),
            file_name: ent.file_name(),
            file_type: ent.file_type().ok(),
        });
        if config.file_limit.is_some_and(|lim| entries.len() > lim) {
            return None;
        }
    }

    match config.sort_by {
        WalkSortKey::None => {}
        WalkSortKey::Name => {
            let mut keyed: Vec<(Vec<u32>, ScannedEntry)> = entries
                .into_iter()
                .map(|e| (surrogateescape_codepoints(&e.file_name, config.ignore_case), e))
                .collect();
            keyed.sort_by(|a, b| {
                let ord = a.0.cmp(&b.0);
                if config.reverse_sort { ord.reverse() } else { ord }
            });
            entries = keyed.into_iter().map(|(_, e)| e).collect();
        }
        WalkSortKey::Version => {
            let mut keyed: Vec<(_, ScannedEntry)> = entries
                .into_iter()
                .map(|e| {
                    let k = natural_sort_key_osstr(
                        &e.file_name,
                        config.ignore_case,
                        config.unicode_major,
                    );
                    (k, e)
                })
                .collect();
            keyed.sort_by(|a, b| {
                let ord = a.0.cmp(&b.0);
                if config.reverse_sort { ord.reverse() } else { ord }
            });
            entries = keyed.into_iter().map(|(_, e)| e).collect();
        }
        WalkSortKey::Time | WalkSortKey::Ctime | WalkSortKey::Size => {
            let descending = !config.reverse_sort;
            let mut keyed: Vec<MetricSortEntry> = entries
                .into_iter()
                .map(|e| {
                    let nk = surrogateescape_codepoints(&e.file_name, config.ignore_case);
                    let metrics = stat_sort_metrics(&e, config.follow_symlinks);
                    (nk, metrics, e)
                })
                .collect();
            keyed.sort_by(|a, b| a.0.cmp(&b.0));
            keyed.sort_by(|a, b| {
                let ord = match config.sort_by {
                    WalkSortKey::Size => a.1.2.cmp(&b.1.2),
                    WalkSortKey::Ctime => a.1.1.partial_cmp(&b.1.1).unwrap_or(Ordering::Equal),
                    _ => a.1.0.partial_cmp(&b.1.0).unwrap_or(Ordering::Equal),
                };
                if descending { ord.reverse() } else { ord }
            });
            entries = keyed.into_iter().map(|(_, _, e)| e).collect();
        }
    }
    Some(entries)
}

/// Calculate accumulated directory disk usage iteratively (`src/findfmt/sizes.py` parity).
pub fn calculate_accumulated_sizes_nogil(
    root: &Path,
    follow_symlinks: bool,
    include_hidden: bool,
) -> HashMap<PathBuf, u64> {
    let mut visited: HashSet<DirKey> = HashSet::new();
    let mut sizes: HashMap<PathBuf, u64> = HashMap::new();
    let mut stack: Vec<(PathBuf, bool, u64, Vec<PathBuf>)> =
        vec![(root.to_path_buf(), false, 0, Vec::new())];

    while let Some((curr_path, expanded, files_size, subdirs)) = stack.pop() {
        if expanded {
            let sub_total: u64 = subdirs
                .iter()
                .map(|s| sizes.get(s).copied().unwrap_or(0))
                .sum();
            sizes.insert(curr_path, files_size.saturating_add(sub_total));
            continue;
        }
        let Some(dir_key) = DirKey::from_dir(&curr_path) else {
            sizes.insert(curr_path, 0);
            continue;
        };
        let is_dir = if follow_symlinks {
            fs::metadata(&curr_path).is_ok_and(|m| m.is_dir())
        } else {
            fs::symlink_metadata(&curr_path).is_ok_and(|m| m.is_dir())
        };
        if !visited.insert(dir_key) {
            continue;
        }
        if !is_dir {
            let sz = if follow_symlinks {
                fs::metadata(&curr_path).map_or(0, |m| m.len())
            } else {
                fs::symlink_metadata(&curr_path).map_or(0, |m| m.len())
            };
            sizes.insert(curr_path, sz);
            continue;
        }
        let mut curr_files_size = 0_u64;
        let mut curr_subdirs = Vec::new();
        if let Ok(rd) = fs::read_dir(&curr_path) {
            for ent in rd.flatten() {
                if !include_hidden && is_hidden_name(&ent.file_name()) {
                    continue;
                }
                let p = ent.path();
                let meta_opt = if follow_symlinks {
                    fs::metadata(&p).ok()
                } else {
                    ent.metadata().ok()
                };
                if let Some(m) = meta_opt {
                    if m.is_dir() {
                        curr_subdirs.push(p);
                    } else if m.is_file() {
                        curr_files_size = curr_files_size.saturating_add(m.len());
                    }
                }
            }
        }
        let push_subs: Vec<PathBuf> = curr_subdirs.iter().rev().cloned().collect();
        stack.push((curr_path, true, curr_files_size, curr_subdirs));
        for sub in push_subs {
            stack.push((sub, false, 0, Vec::new()));
        }
    }
    sizes
}
