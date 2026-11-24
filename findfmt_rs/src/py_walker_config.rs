//! Python `TraversalConfig` extraction and live `mimetypes` snapshotting (#582, #588).

use std::collections::{HashMap, HashSet, VecDeque};
use std::path::PathBuf;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};

use crate::patterns::PatternMatcher;
use crate::py_bridge::extract_tag_set;
use crate::py_paths::{PyHandles, py_path_to_pathbuf, windows_pathext_upper};
use crate::tags::FilterCriteria;
use crate::walker_types::{MimeSnapshot, WalkBounds, WalkConfig, WalkScope, WalkSort, WalkSortKey};

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
    obj.try_iter()?
        .map(|item| item?.extract::<String>())
        .collect()
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

    let mut strict = HashMap::with_capacity(strict_py.len());
    for (k, v) in strict_py.iter() {
        if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) {
            strict.insert(ks, vs);
        }
    }
    let mut suffixes = HashMap::with_capacity(suffix_py.len());
    for (k, v) in suffix_py.iter() {
        if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) {
            suffixes.insert(ks, vs);
        }
    }
    let mut encodings = HashSet::with_capacity(enc_py.len());
    for (k, _) in enc_py.iter() {
        if let Ok(ks) = k.extract::<String>() {
            encodings.insert(ks);
        }
    }
    Ok(MimeSnapshot {
        strict,
        suffixes,
        encodings,
    })
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
    let matcher = PatternMatcher::try_new_for_unicode(
        &include_patterns,
        &exclude_patterns,
        ignore_case,
        match_dirs,
        handles.unicode_major,
    )
    .map_err(pyo3::exceptions::PyValueError::new_err)?;

    let filter = FilterCriteria {
        include_tags: extract_tag_set(Some(&config_obj.getattr("include_tags")?))?,
        exclude_tags: extract_tag_set(Some(&config_obj.getattr("exclude_tags")?))?,
        all_tags: config_obj.getattr("all_tags")?.extract()?,
        shebang_filter: config_obj.getattr("shebang_filter")?.extract()?,
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
        scope: WalkScope {
            include_hidden,
            follow_symlinks,
            dirs_only,
        },
        bounds: WalkBounds {
            one_file_system,
            prune_empty,
            accumulate_size,
            max_depth,
            file_limit,
        },
        sort: WalkSort {
            sort_by,
            reverse_sort,
            dirs_first,
            ignore_case,
        },
        filter,
        matcher,
        home_dir,
        pathext_upper: windows_pathext_upper(),
        unicode_major: handles.unicode_major,
        mime_snapshot: snapshot_live_mime_db(py)?,
    };
    Ok(Some((walk_cfg, pending_roots, relative_prefix)))
}
