//! Python `TraversalConfig` extraction and lazy root path resolution for `RustFileIterator` (#582).

use std::collections::{HashMap, HashSet, VecDeque};
use std::path::PathBuf;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};

use crate::ignore_stack::find_git_repo_root;
use crate::patterns::PatternMatcher;
use crate::py_bridge::extract_tag_set;
use crate::py_paths::{
    PyHandles, pathbuf_to_py_path, py_path_to_pathbuf, windows_pathext_upper,
};
use crate::tags::FilterCriteria;
use crate::walker_types::{MimeSnapshot, RootTarget, WalkConfig, WalkSortKey};

type ResolvedRootStep<'py> = (Option<Bound<'py, PyAny>>, Option<Py<PyAny>>);
pub(crate) type PreparedWalk = (WalkConfig, VecDeque<Py<PyAny>>, bool);

fn extract_optional_non_negative(
    py: Python<'_>,
    handles: &PyHandles,
    config_obj: &Bound<'_, PyAny>,
    attr_name: &str,
) -> PyResult<Option<usize>> {
    let val_obj = config_obj.getattr(attr_name)?;
    if val_obj.is_none() {
        return Ok(None);
    }
    let signed: i64 = val_obj.extract()?;
    if signed < 0 {
        let msg = format!("{attr_name} must be non-negative, got {signed}");
        let err = handles.traversal_error_cls.bind(py).call1((msg,))?;
        return Err(PyErr::from_value(err));
    }
    usize::try_from(signed).map(Some).map_err(|_| {
        pyo3::exceptions::PyOverflowError::new_err(format!("{attr_name} exceeds platform usize"))
    })
}

fn extract_string_vec(obj: &Bound<'_, PyAny>) -> PyResult<Vec<String>> {
    obj.try_iter()?.map(|item| item?.extract::<String>()).collect()
}

fn extract_sort_key(config_obj: &Bound<'_, PyAny>) -> PyResult<WalkSortKey> {
    let sort_obj = config_obj.getattr("sort_by")?;
    let val_str: String = if let Ok(v) = sort_obj.getattr("value") {
        v.extract()?
    } else {
        sort_obj.extract()?
    };
    Ok(match val_str.trim().to_ascii_lowercase().as_str() {
        "version" => WalkSortKey::Version,
        "time" | "mtime" => WalkSortKey::Time,
        "ctime" => WalkSortKey::Ctime,
        "size" => WalkSortKey::Size,
        "none" | "unsorted" => WalkSortKey::None,
        _ => WalkSortKey::Name,
    })
}

fn snapshot_live_mime_db(py: Python<'_>) -> PyResult<MimeSnapshot> {
    let mime_mod = py.import("mimetypes")?;
    if mime_mod.getattr("_db")?.is_none() {
        mime_mod.call_method0("init")?;
    }
    let db = mime_mod.getattr("_db")?;
    let types_map_tuple = db.getattr("types_map")?.cast_into::<PyTuple>()?;
    let strict_py = types_map_tuple.get_item(1)?.cast_into::<PyDict>()?;
    let suffix_py = db.getattr("suffix_map")?.cast_into::<PyDict>()?;
    let enc_py = db.getattr("encodings_map")?.cast_into::<PyDict>()?;

    let mut strict_map = HashMap::with_capacity(strict_py.len());
    for (k, v) in strict_py.iter() {
        if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) {
            strict_map.insert(ks, vs);
        }
    }
    let mut suffix_map = HashMap::with_capacity(suffix_py.len());
    for (k, v) in suffix_py.iter() {
        if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) {
            suffix_map.insert(ks, vs);
        }
    }
    let mut encodings_map = HashSet::with_capacity(enc_py.len());
    for (k, _) in enc_py.iter() {
        if let Ok(ks) = k.extract::<String>() {
            encodings_map.insert(ks);
        }
    }
    Ok(MimeSnapshot {
        strict_map,
        suffix_map,
        encodings_map,
    })
}

fn ensure_oserror_filename(
    py: Python<'_>,
    err_val: &Bound<'_, PyAny>,
    fallback_root: &Bound<'_, PyAny>,
) -> PyResult<()> {
    let cur_fn = err_val.getattr("filename")?;
    let is_empty = cur_fn.is_none() || cur_fn.extract::<String>().is_ok_and(|s| s.is_empty());
    if is_empty {
        let root_str = fallback_root.str()?;
        let _ = err_val.setattr("filename", root_str);
    }
    let _ = py;
    Ok(())
}

/// Resolve a single Python root `Path` immediately prior to walking it (`engine.py` lazy parity).
pub(crate) fn resolve_single_root_py<'py>(
    py: Python<'py>,
    handles: &PyHandles,
    root_obj: &Bound<'py, PyAny>,
    follow_symlinks: bool,
    relative_prefix: bool,
    respect_gitignore: bool,
) -> PyResult<(RootTarget, Option<Py<PyAny>>)> {
    let (raw_root, _, _, _) = py_path_to_pathbuf(py, handles, root_obj)?;

    let step = (|| -> PyResult<ResolvedRootStep<'py>> {
        let is_symlink: bool = root_obj.call_method0("is_symlink")?.extract()?;
        if is_symlink && !follow_symlinks {
            let parent_res = root_obj.getattr("parent")?.call_method0("resolve")?;
            let name_obj = root_obj.getattr("name")?;
            let joined = parent_res.call_method1("__truediv__", (name_obj,))?;
            return Ok((Some(joined), None));
        }
        let resolved_cand = root_obj.call_method0("resolve")?;
        let exists: bool = resolved_cand.call_method0("exists")?.extract()?;
        if exists {
            let is_dir: bool = resolved_cand.call_method0("is_dir")?.extract()?;
            if is_symlink && !is_dir {
                let parent_res = root_obj.getattr("parent")?.call_method0("resolve")?;
                let name_obj = root_obj.getattr("name")?;
                let joined = parent_res.call_method1("__truediv__", (name_obj,))?;
                return Ok((Some(joined), None));
            }
            return Ok((Some(resolved_cand), None));
        }
        if !is_symlink {
            let enoent = libc_enoent();
            let msg = handles.os_strerror.bind(py).call1((enoent,))?;
            let root_str = root_obj.str()?;
            let fnf = pyo3::exceptions::PyFileNotFoundError::new_err((
                enoent,
                msg.unbind(),
                root_str.unbind(),
            ));
            return Ok((None, Some(fnf.value(py).clone().into_any().unbind())));
        }
        Ok((None, None))
    })();

    let (resolved_bound, root_py_err) = match step {
        Ok(pair) => pair,
        Err(err) => {
            if err.is_instance_of::<pyo3::exceptions::PyOSError>(py) {
                let val = err.value(py);
                ensure_oserror_filename(py, val, root_obj)?;
                (None, Some(val.clone().into_any().unbind()))
            } else if err.is_instance_of::<pyo3::exceptions::PyRuntimeError>(py) {
                (None, None)
            } else {
                return Err(err);
            }
        }
    };

    let (resolved_pb, prefix_pb) = match resolved_bound {
        Some(ref res_obj) => {
            let (rpb, _, _, _) = py_path_to_pathbuf(py, handles, res_obj)?;
            let pfx = if relative_prefix {
                let is_file = res_obj.call_method0("is_file")?.extract::<bool>().unwrap_or(false)
                    || (!follow_symlinks
                        && res_obj
                            .call_method0("is_symlink")?
                            .extract::<bool>()
                            .unwrap_or(false));
                let pfx_arg = if is_file {
                    root_obj.getattr("parent")?
                } else {
                    root_obj.clone()
                };
                let computed = handles.compute_relative_prefix.bind(py).call1((pfx_arg,))?;
                if computed.is_none() {
                    None
                } else {
                    Some(py_path_to_pathbuf(py, handles, &computed)?.0)
                }
            } else {
                None
            };
            (Some(rpb), pfx)
        }
        None => (None, None),
    };

    let global_gitignore = if let Some(rpb) = resolved_pb.as_ref().filter(|_| respect_gitignore) {
        let base_dir = find_git_repo_root(rpb).unwrap_or_else(|| rpb.clone());
        match pathbuf_to_py_path(py, handles, &base_dir).ok() {
            None => None,
            Some(bp) => match handles.find_global_gitignore_path.bind(py).call1((bp,)) {
                Ok(res) if res.is_none() => None,
                Ok(res) => py_path_to_pathbuf(py, handles, &res).ok().map(|t| t.0),
                Err(err) if err.is_instance_of::<pyo3::exceptions::PyException>(py) => None,
                Err(err) => return Err(err),
            },
        }
    } else {
        None
    };

    Ok((
        RootTarget {
            raw_root,
            resolved_root: resolved_pb,
            prefix: prefix_pb,
            global_gitignore,
            initial_error: None,
        },
        root_py_err,
    ))
}

const fn libc_enoent() -> i32 {
    2
}

/// Extract `WalkConfig`, ordered pending root objects, and `relative_prefix`, or `None` when `from_file` is set.
pub(crate) fn prepare_walk_from_py_config<'py>(
    py: Python<'py>,
    handles: &PyHandles,
    config_obj: &Bound<'py, PyAny>,
) -> PyResult<Option<PreparedWalk>> {
    let max_depth = extract_optional_non_negative(py, handles, config_obj, "max_depth")?;
    let file_limit = extract_optional_non_negative(py, handles, config_obj, "file_limit")?;

    if !config_obj.getattr("from_file")?.is_none() {
        return Ok(None);
    }

    let respect_gitignore: bool = config_obj.getattr("respect_gitignore")?.extract()?;
    let custom_gi_obj = config_obj.getattr("gitignore_file")?;
    let custom_gitignore_file = if custom_gi_obj.is_none() {
        None
    } else {
        Some(py_path_to_pathbuf(py, handles, &custom_gi_obj)?.0)
    };
    let include_hidden: bool = config_obj.getattr("include_hidden")?.extract()?;
    let follow_symlinks: bool = config_obj.getattr("follow_symlinks")?.extract()?;
    let dirs_only: bool = config_obj.getattr("dirs_only")?.extract()?;
    let one_file_system: bool = config_obj.getattr("one_file_system")?.extract()?;
    let prune_empty: bool = config_obj.getattr("prune_empty")?.extract()?;
    let ignore_case: bool = config_obj.getattr("ignore_case")?.extract()?;
    let match_dirs: bool = config_obj.getattr("match_dirs")?.extract()?;
    let relative_prefix: bool = config_obj.getattr("relative_prefix")?.extract()?;
    let accumulate_size: bool = config_obj.getattr("accumulate_size")?.extract()?;
    let sort_by = extract_sort_key(config_obj)?;
    let reverse_sort: bool = config_obj.getattr("reverse_sort")?.extract()?;
    let dirs_first: bool = config_obj.getattr("dirs_first")?.extract()?;

    let include_patterns = extract_string_vec(&config_obj.getattr("include_patterns")?)?;
    let exclude_patterns = extract_string_vec(&config_obj.getattr("exclude_patterns")?)?;
    let matcher =
        PatternMatcher::try_new(&include_patterns, &exclude_patterns, ignore_case, match_dirs)
            .map_err(pyo3::exceptions::PyValueError::new_err)?;

    let include_tags = extract_tag_set(Some(&config_obj.getattr("include_tags")?))?;
    let exclude_tags = extract_tag_set(Some(&config_obj.getattr("exclude_tags")?))?;
    let all_tags: bool = config_obj.getattr("all_tags")?.extract()?;
    let shebang_filter: Option<String> = config_obj.getattr("shebang_filter")?.extract()?;
    let filter = FilterCriteria {
        include_tags,
        exclude_tags,
        all_tags,
        shebang_filter,
    };

    let home_dir: Option<PathBuf> = handles
        .path_home
        .bind(py)
        .call0()
        .ok()
        .and_then(|h| py_path_to_pathbuf(py, handles, &h).ok().map(|t| t.0));

    let raw_roots_obj = config_obj.getattr("root_paths")?;
    let ordered_roots = if sort_by == WalkSortKey::None {
        raw_roots_obj
    } else {
        handles.sorted_fn.bind(py).call1((raw_roots_obj,))?
    };

    let mut pending_roots = VecDeque::new();
    for item_res in ordered_roots.try_iter()? {
        pending_roots.push_back(item_res?.unbind());
    }

    let walk_cfg = WalkConfig {
        respect_gitignore,
        custom_gitignore_file,
        include_hidden,
        follow_symlinks,
        dirs_only,
        one_file_system,
        max_depth,
        file_limit,
        prune_empty,
        ignore_case,
        match_dirs,
        accumulate_size,
        sort_by,
        reverse_sort,
        dirs_first,
        filter,
        matcher,
        home_dir,
        pathext_upper: windows_pathext_upper(),
        unicode_major: handles.unicode_major,
        mime_snapshot: snapshot_live_mime_db(py)?,
    };
    Ok(Some((walk_cfg, pending_roots, relative_prefix)))
}
