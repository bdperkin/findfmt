//! `PyO3` FFI bridge converting GIL-free Rust classification outputs into `FileInfo` (#583).

use std::collections::{BTreeSet, HashMap};
use std::path::Path;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFrozenSet, PyList};

use crate::classifier::{
    RawClassifiedFile, RawClassifyInput, classify_batch_nogil, classify_one_nogil,
};
#[cfg(not(unix))]
use crate::py_paths::fetch_windows_pre_stat;
use crate::py_paths::{
    PyHandles, compute_relative_py, get_handles, pathbuf_to_py_str, py_path_to_pathbuf,
    windows_pathext_upper,
};
use crate::tags::{FilterCriteria, LiveMimeDb, TagRegistry};

#[allow(clippy::too_many_arguments)]
pub(crate) fn build_py_file_info<'py>(
    py: Python<'py>,
    handles: &PyHandles,
    path_obj: &Bound<'py, PyAny>,
    raw_input: &RawClassifyInput,
    is_abs: bool,
    has_entry: bool,
    root_pair: Option<(&Bound<'py, PyAny>, &Path)>,
    prefix_pair: Option<(&Bound<'py, PyAny>, &Path)>,
    raw_res: RawClassifiedFile,
    uid_cache: &mut HashMap<u32, Bound<'py, PyAny>>,
    gid_cache: &mut HashMap<u32, Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyAny>> {
    let is_symlink = raw_res.is_symlink();
    let resolved_path = if !has_entry && !is_symlink && raw_res.exists && !is_abs {
        path_obj.call_method0("resolve")?
    } else {
        path_obj.clone()
    };
    let relative_path = compute_relative_py(
        py,
        handles,
        path_obj,
        &raw_input.path,
        root_pair,
        prefix_pair,
    )?;
    let py_tags = PyFrozenSet::new(py, raw_res.tags.iter().map(String::as_str))?;

    let symlink_target_py: Option<Bound<'py, PyAny>> = match raw_res.symlink_target() {
        Some(t_pb) => {
            let decoded = pathbuf_to_py_str(py, handles, t_pb)?;
            Some(decoded.call_method1("removeprefix", (r"\\?\",))?)
        }
        None => None,
    };

    let owner_user = match raw_res.uid {
        Some(uid) => {
            if let Some(cached) = uid_cache.get(&uid) {
                Some(cached.clone())
            } else {
                let resolved = handles.resolve_user_name.bind(py).call1((uid,))?;
                uid_cache.insert(uid, resolved.clone());
                Some(resolved)
            }
        }
        None => None,
    };
    let owner_group = match raw_res.gid {
        Some(gid) => {
            if let Some(cached) = gid_cache.get(&gid) {
                Some(cached.clone())
            } else {
                let resolved = handles.resolve_group_name.bind(py).call1((gid,))?;
                gid_cache.insert(gid, resolved.clone());
                Some(resolved)
            }
        }
        None => None,
    };

    let kwargs = PyDict::new(py);
    kwargs.set_item("path", resolved_path)?;
    kwargs.set_item("relative_path", relative_path)?;
    kwargs.set_item("tags", py_tags)?;
    kwargs.set_item("shebang", raw_res.shebang)?;
    kwargs.set_item("mime_type", raw_res.mime_type)?;
    kwargs.set_item("is_executable", raw_res.is_executable)?;
    kwargs.set_item("is_symlink", is_symlink)?;
    kwargs.set_item("symlink_target", symlink_target_py)?;
    kwargs.set_item("size_bytes", raw_res.size_bytes)?;
    kwargs.set_item("permissions_str", raw_res.permissions_str)?;
    kwargs.set_item("owner_user", owner_user)?;
    kwargs.set_item("owner_group", owner_group)?;
    kwargs.set_item("inode", raw_res.inode)?;
    kwargs.set_item("device", raw_res.device)?;
    kwargs.set_item("accumulated_size", raw_res.accumulated_size)?;
    kwargs.set_item("mtime", raw_res.mtime)?;
    kwargs.set_item("ctime", raw_res.ctime)?;
    kwargs.set_item("indicator", raw_res.indicator)?;

    handles.file_info_cls.bind(py).call((), Some(&kwargs))
}

/// Execute single-file native classification (`classify_file` and `classify_file_rs`).
#[allow(clippy::too_many_arguments)]
pub fn classify_single_py<'py>(
    py: Python<'py>,
    path: &Bound<'py, PyAny>,
    root_path: Option<&Bound<'py, PyAny>>,
    prefix: Option<&Bound<'py, PyAny>>,
    accumulated_size: Option<u64>,
    entry: Option<&Bound<'py, PyAny>>,
    follow_symlinks: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let handles = get_handles(py)?;
    let registry = TagRegistry::global_from_python(py)?;
    let mime_db = LiveMimeDb::from_python(py)?;
    let (pb, str_path, filename, is_abs) = py_path_to_pathbuf(py, handles, path)?;
    let pre_guessed_mime = Some(mime_db.guess_mime_type(&str_path));
    let root_decoded = match root_path {
        Some(rp) => Some((rp, py_path_to_pathbuf(py, handles, rp)?.0)),
        None => None,
    };
    let prefix_decoded = match prefix {
        Some(pf) => Some((pf, py_path_to_pathbuf(py, handles, pf)?.0)),
        None => None,
    };
    #[cfg(not(unix))]
    let pre_stat = Some(fetch_windows_pre_stat(py, path, entry, follow_symlinks));
    #[cfg(unix)]
    let pre_stat = None;

    let raw_input = RawClassifyInput {
        path: pb,
        str_path,
        filename,
        follow_symlinks,
        accumulated_size,
        pre_stat,
        pre_guessed_mime,
    };
    let pathext = windows_pathext_upper();
    let raw_res = py.detach(|| classify_one_nogil(&raw_input, registry, pathext.as_deref()));

    let mut uid_cache = HashMap::new();
    let mut gid_cache = HashMap::new();
    build_py_file_info(
        py,
        handles,
        path,
        &raw_input,
        is_abs,
        entry.is_some(),
        root_decoded.as_ref().map(|(o, p)| (*o, p.as_path())),
        prefix_decoded.as_ref().map(|(o, p)| (*o, p.as_path())),
        raw_res,
        &mut uid_cache,
        &mut gid_cache,
    )
}

pub(crate) fn extract_tag_set(opt: Option<&Bound<'_, PyAny>>) -> PyResult<BTreeSet<String>> {
    let Some(obj) = opt else {
        return Ok(BTreeSet::new());
    };
    obj.try_iter()?
        .map(|item| Ok(item?.extract::<String>()?.trim().to_lowercase()))
        .collect()
}

/// Execute combined batch header classification + tag/shebang filtering in a single GIL-released pass.
#[allow(clippy::too_many_arguments)]
pub fn classify_batch_py<'py>(
    py: Python<'py>,
    candidates: &Bound<'py, PyAny>,
    root_path: Option<&Bound<'py, PyAny>>,
    prefix: Option<&Bound<'py, PyAny>>,
    follow_symlinks: bool,
    include_tags: Option<&Bound<'py, PyAny>>,
    exclude_tags: Option<&Bound<'py, PyAny>>,
    all_tags: bool,
    shebang_filter: Option<String>,
) -> PyResult<Bound<'py, PyList>> {
    let handles = get_handles(py)?;
    let registry = TagRegistry::global_from_python(py)?;
    let mime_db = LiveMimeDb::from_python(py)?;
    let root_decoded = match root_path {
        Some(rp) => Some((rp, py_path_to_pathbuf(py, handles, rp)?.0)),
        None => None,
    };
    let prefix_decoded = match prefix {
        Some(pf) => Some((pf, py_path_to_pathbuf(py, handles, pf)?.0)),
        None => None,
    };

    let mut py_items: Vec<(Bound<'py, PyAny>, bool, bool)> = Vec::new();
    let mut raw_inputs: Vec<RawClassifyInput> = Vec::new();
    for elem in candidates.try_iter()? {
        let tup = elem?;
        let path_obj = tup.get_item(0)?;
        let entry_obj = tup.get_item(1)?;
        let has_entry = !entry_obj.is_none();
        let accum_opt: Option<u64> = tup.get_item(2)?.extract()?;
        let (pb, str_path, filename, is_abs) = py_path_to_pathbuf(py, handles, &path_obj)?;
        let pre_guessed_mime = Some(mime_db.guess_mime_type(&str_path));
        #[cfg(not(unix))]
        let pre_stat = Some(fetch_windows_pre_stat(
            py,
            &path_obj,
            has_entry.then_some(&entry_obj),
            follow_symlinks,
        ));
        #[cfg(unix)]
        let pre_stat = None;

        py_items.push((path_obj, is_abs, has_entry));
        raw_inputs.push(RawClassifyInput {
            path: pb,
            str_path,
            filename,
            follow_symlinks,
            accumulated_size: accum_opt,
            pre_stat,
            pre_guessed_mime,
        });
    }

    let criteria = FilterCriteria {
        include_tags: extract_tag_set(include_tags)?,
        exclude_tags: extract_tag_set(exclude_tags)?,
        all_tags,
        shebang_filter,
    };
    let filter_ref = criteria.is_active().then_some(&criteria);
    let pathext = windows_pathext_upper();

    let matched =
        py.detach(|| classify_batch_nogil(&raw_inputs, filter_ref, registry, pathext.as_deref()));

    let out = PyList::empty(py);
    let mut uid_cache = HashMap::new();
    let mut gid_cache = HashMap::new();
    for (idx, raw_res) in matched {
        let (ref path_obj, is_abs, has_entry) = py_items[idx];
        let root_arg = root_decoded.as_ref().map(|(o, p)| (*o, p.as_path()));
        let pfx_arg = prefix_decoded.as_ref().map(|(o, p)| (*o, p.as_path()));
        let info_res = build_py_file_info(
            py,
            handles,
            path_obj,
            &raw_inputs[idx],
            is_abs,
            has_entry,
            root_arg,
            pfx_arg,
            raw_res,
            &mut uid_cache,
            &mut gid_cache,
        );
        out.append(info_res?)?;
    }
    Ok(out)
}
