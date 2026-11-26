//! Materialization of `WalkYieldItem` records into Python `FileInfo` objects (#582, #588).

use std::collections::HashMap;

use pyo3::prelude::*;

use crate::classifier::RawClassifyInput;
#[cfg(not(unix))]
use crate::classifier::{RawClassifiedFile, classify_one_nogil};
use crate::py_bridge::build_py_file_info;
#[cfg(not(unix))]
use crate::py_paths::fetch_windows_pre_stat;
use crate::py_paths::{PyHandles, pathbuf_to_py_path};
use crate::tags::TagRegistry;
#[cfg(not(unix))]
use crate::walker_filter::resolve_relative_pathbuf;
use crate::walker_types::{WalkConfig, WalkYieldItem};

#[cfg(unix)]
type MaterializedItem<'py> = Bound<'py, PyAny>;
#[cfg(not(unix))]
type MaterializedItem<'py> = Option<Bound<'py, PyAny>>;

#[cfg(not(unix))]
fn refresh_windows_yield_item(
    py: Python<'_>,
    path_obj: &Bound<'_, PyAny>,
    walk_cfg: &WalkConfig,
    registry: &'static TagRegistry,
    item: WalkYieldItem,
) -> Option<(
    RawClassifyInput,
    RawClassifiedFile,
    std::path::PathBuf,
    Option<std::path::PathBuf>,
    bool,
)> {
    let mut pre = fetch_windows_pre_stat(py, path_obj, None, item.follow_symlinks);
    if item.has_entry
        && (!pre.0 || !item.follow_symlinks)
        && let Some(ref mut raw) = pre.4
    {
        raw.ino = Some(0);
        raw.dev = Some(0);
        if raw.is_reg() {
            raw.mode = 0o100_000
                | if (raw.mode & 0o200) == 0 {
                    0o444
                } else {
                    0o666
                };
        }
    }
    let win_in = RawClassifyInput {
        path: item.path,
        str_path: item.str_path,
        filename: item.filename,
        follow_symlinks: item.follow_symlinks,
        accumulated_size: item.classified.accumulated_size,
        pre_stat: Some(pre),
        pre_guessed_mime: Some(item.classified.mime_type.clone()),
    };
    let pathext_ref = walk_cfg.pathext_upper.as_deref();
    let refreshed = py.detach(|| classify_one_nogil(&win_in, registry, pathext_ref));
    let is_dir_item = refreshed.is_dir || refreshed.tags.contains("directory");
    if walk_cfg.scope.dirs_only && !is_dir_item {
        return None;
    }
    let rel_pb = resolve_relative_pathbuf(&win_in.path, &item.root_path, item.prefix.as_deref());
    if !walk_cfg
        .filter
        .matches(&refreshed.tags, refreshed.shebang.as_deref(), is_dir_item)
        || !walk_cfg
            .matcher
            .matches_classified_item(&rel_pb, is_dir_item, item.inherited_match)
    {
        return None;
    }
    Some((
        win_in,
        refreshed,
        item.root_path,
        item.prefix,
        item.has_entry,
    ))
}

pub(crate) fn materialize_yield_item<'py>(
    py: Python<'py>,
    handles: &PyHandles,
    walk_cfg: &WalkConfig,
    registry: &'static TagRegistry,
    uid_cache: &mut HashMap<u32, Py<PyAny>>,
    gid_cache: &mut HashMap<u32, Py<PyAny>>,
    item: WalkYieldItem,
) -> PyResult<MaterializedItem<'py>> {
    let path_obj = pathbuf_to_py_path(py, handles, &item.path)?;
    let root_obj = pathbuf_to_py_path(py, handles, &item.root_path)?;
    let prefix_obj = match item.prefix {
        Some(ref pfx) => Some(pathbuf_to_py_path(py, handles, pfx)?),
        None => None,
    };
    let is_abs = item.path.is_absolute();

    #[cfg(not(unix))]
    let (raw_input, raw_classified, root_pb, prefix_pb, has_entry) =
        match refresh_windows_yield_item(py, &path_obj, walk_cfg, registry, item) {
            Some(done) => done,
            None => return Ok(None),
        };

    #[cfg(unix)]
    let (raw_input, raw_classified, root_pb, prefix_pb, has_entry) = {
        let _ = (walk_cfg, registry);
        (
            RawClassifyInput {
                path: item.path,
                str_path: item.str_path,
                filename: item.filename,
                follow_symlinks: item.follow_symlinks,
                accumulated_size: item.classified.accumulated_size,
                pre_stat: None,
                pre_guessed_mime: None,
            },
            item.classified,
            item.root_path,
            item.prefix,
            item.has_entry,
        )
    };

    let mut user_map: HashMap<u32, Bound<'py, PyAny>> = uid_cache
        .iter()
        .map(|(&k, v)| (k, v.bind(py).clone()))
        .collect();
    let mut group_map: HashMap<u32, Bound<'py, PyAny>> = gid_cache
        .iter()
        .map(|(&k, v)| (k, v.bind(py).clone()))
        .collect();

    let info = build_py_file_info(
        py,
        handles,
        &path_obj,
        &raw_input,
        is_abs,
        has_entry,
        Some((&root_obj, &root_pb)),
        prefix_obj.as_ref().zip(prefix_pb.as_deref()),
        raw_classified,
        &mut user_map,
        &mut group_map,
    )?;

    for (k, v) in user_map {
        uid_cache.entry(k).or_insert_with(|| v.unbind());
    }
    for (k, v) in group_map {
        gid_cache.entry(k).or_insert_with(|| v.unbind());
    }
    #[cfg(unix)]
    {
        Ok(info)
    }
    #[cfg(not(unix))]
    {
        Ok(Some(info))
    }
}
