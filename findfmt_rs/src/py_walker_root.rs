//! Lazy root path probing and global gitignore resolution for `RustFileIterator` (#582, #588).

use std::path::Path;

use pyo3::prelude::*;

use crate::ignore_stack::find_git_repo_root;
use crate::py_paths::{PyHandles, pathbuf_to_py_path, py_path_to_pathbuf};
use crate::walker_types::{GlobalIgnoreResolution, RootTarget};

type ResolvedRootStep<'py> = (Option<Bound<'py, PyAny>>, Option<Py<PyAny>>);

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

const fn libc_enoent() -> i32 {
    2
}

fn probe_root_candidate_py<'py>(
    py: Python<'py>,
    handles: &PyHandles,
    root_obj: &Bound<'py, PyAny>,
    follow_symlinks: bool,
) -> PyResult<ResolvedRootStep<'py>> {
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
}

fn resolve_global_gitignore_py(
    py: Python<'_>,
    handles: &PyHandles,
    resolved_pb: Option<&Path>,
    respect_gitignore: bool,
) -> PyResult<GlobalIgnoreResolution> {
    let Some(rpb) = resolved_pb.filter(|_| respect_gitignore) else {
        return Ok(GlobalIgnoreResolution::Unresolved);
    };
    let base_dir = find_git_repo_root(rpb).unwrap_or_else(|| rpb.to_path_buf());
    let bp = pathbuf_to_py_path(py, handles, &base_dir)?;
    match handles.find_global_gitignore_path.bind(py).call1((bp,)) {
        Ok(res) if res.is_none() => Ok(GlobalIgnoreResolution::ResolvedNone),
        Ok(res) => match py_path_to_pathbuf(py, handles, &res) {
            Ok((pb, _, _, _)) => Ok(GlobalIgnoreResolution::ResolvedPath(pb)),
            Err(_) => Ok(GlobalIgnoreResolution::ResolvedNone),
        },
        Err(err) if err.is_instance_of::<pyo3::exceptions::PyException>(py) => {
            Ok(GlobalIgnoreResolution::ResolvedNone)
        }
        Err(err) => Err(err),
    }
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
    let _ = py_path_to_pathbuf(py, handles, root_obj)?;
    let (resolved_bound, root_py_err) =
        match probe_root_candidate_py(py, handles, root_obj, follow_symlinks) {
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
                let is_file = res_obj
                    .call_method0("is_file")?
                    .extract::<bool>()
                    .unwrap_or(false)
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

    let global_gitignore =
        resolve_global_gitignore_py(py, handles, resolved_pb.as_deref(), respect_gitignore)?;

    Ok((
        RootTarget {
            resolved_root: resolved_pb,
            prefix: prefix_pb,
            global_gitignore,
            initial_error: None,
        },
        root_py_err,
    ))
}
