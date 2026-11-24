//! Python `Path` / `os.fsencode` / `os.fsdecode` helpers and cached handles (#583).

use std::path::{Path, PathBuf};
use std::sync::OnceLock;

use pyo3::prelude::*;
#[cfg(unix)]
use pyo3::types::PyBytes;
#[cfg(not(unix))]
use pyo3::types::PyDict;

#[cfg(not(unix))]
use crate::metadata::RawStat;
use crate::walker_types::WalkOsError;

pub(crate) struct PyHandles {
    pub path_cls: Py<PyAny>,
    pub path_home: Py<PyAny>,
    pub file_info_cls: Py<PyAny>,
    #[cfg(unix)]
    pub fsencode: Py<PyAny>,
    #[cfg(unix)]
    pub fsdecode: Py<PyAny>,
    pub os_strerror: Py<PyAny>,
    pub sorted_fn: Py<PyAny>,
    pub resolve_user_name: Py<PyAny>,
    pub resolve_group_name: Py<PyAny>,
    pub resolve_relative: Py<PyAny>,
    pub compute_relative_prefix: Py<PyAny>,
    pub find_global_gitignore_path: Py<PyAny>,
    pub traversal_error_cls: Py<PyAny>,
    pub ingest_from_file: Py<PyAny>,
    pub unicode_major: u8,
}

static PY_HANDLES: OnceLock<PyHandles> = OnceLock::new();

pub(crate) fn get_handles(py: Python<'_>) -> PyResult<&'static PyHandles> {
    if let Some(h) = PY_HANDLES.get() {
        return Ok(h);
    }
    let builtins = py.import("builtins")?;
    let os_mod = py.import("os")?;
    let pathlib = py.import("pathlib")?;
    let models = py.import("findfmt.models")?;
    let metadata = py.import("findfmt.metadata")?;
    let classifier = py.import("findfmt.classifier")?;
    let trav_ignore = py.import("findfmt.traversal.ignore")?;
    let exceptions = py.import("findfmt.exceptions")?;
    let parsers = py.import("findfmt.parsers")?;
    let unicode_major = py
        .import("unicodedata")
        .ok()
        .and_then(|u| u.getattr("unidata_version").ok())
        .and_then(|v| v.extract::<String>().ok())
        .and_then(|s| s.split('.').next()?.parse::<u8>().ok())
        .unwrap_or(16);
    let path_cls_bound = pathlib.getattr("Path")?;
    let built = PyHandles {
        path_home: path_cls_bound.getattr("home")?.unbind(),
        path_cls: path_cls_bound.unbind(),
        file_info_cls: models.getattr("FileInfo")?.unbind(),
        #[cfg(unix)]
        fsencode: os_mod.getattr("fsencode")?.unbind(),
        #[cfg(unix)]
        fsdecode: os_mod.getattr("fsdecode")?.unbind(),
        os_strerror: os_mod.getattr("strerror")?.unbind(),
        sorted_fn: builtins.getattr("sorted")?.unbind(),
        resolve_user_name: metadata.getattr("resolve_user_name")?.unbind(),
        resolve_group_name: metadata.getattr("resolve_group_name")?.unbind(),
        resolve_relative: classifier.getattr("_resolve_relative")?.unbind(),
        compute_relative_prefix: classifier.getattr("compute_relative_prefix")?.unbind(),
        find_global_gitignore_path: trav_ignore.getattr("find_global_gitignore_path")?.unbind(),
        traversal_error_cls: exceptions.getattr("TraversalError")?.unbind(),
        ingest_from_file: parsers.getattr("ingest_from_file")?.unbind(),
        unicode_major,
    };
    let _ = PY_HANDLES.set(built);
    PY_HANDLES
        .get()
        .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("failed to initialize PyHandles"))
}

pub(crate) fn py_path_to_pathbuf(
    py: Python<'_>,
    handles: &PyHandles,
    obj: &Bound<'_, PyAny>,
) -> PyResult<(PathBuf, String, String, bool)> {
    #[cfg(unix)]
    {
        use std::ffi::OsStr;
        use std::os::unix::ffi::OsStrExt;

        let encoded = handles.fsencode.bind(py).call1((obj,))?;
        let raw = encoded.cast::<PyBytes>()?.as_bytes();
        let pb = PathBuf::from(OsStr::from_bytes(raw));
        let str_lossy = String::from_utf8_lossy(raw).into_owned();
        let name_lossy = pb
            .file_name()
            .map_or_else(String::new, |n| n.to_string_lossy().into_owned());
        let is_abs = pb.is_absolute();
        Ok((pb, str_lossy, name_lossy, is_abs))
    }
    #[cfg(not(unix))]
    {
        let _ = (py, handles);
        let pb: PathBuf = obj.extract()?;
        let str_lossy = pb.to_string_lossy().into_owned();
        let name_lossy = pb
            .file_name()
            .map_or_else(String::new, |n| n.to_string_lossy().into_owned());
        let is_abs = pb.is_absolute();
        Ok((pb, str_lossy, name_lossy, is_abs))
    }
}

pub(crate) fn pathbuf_to_py_str<'py>(
    py: Python<'py>,
    handles: &PyHandles,
    pb: &Path,
) -> PyResult<Bound<'py, PyAny>> {
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;

        let b = PyBytes::new(py, pb.as_os_str().as_bytes());
        handles.fsdecode.bind(py).call1((b,))
    }
    #[cfg(not(unix))]
    {
        let _ = handles;
        Ok(pb.to_string_lossy().into_pyobject(py)?.into_any())
    }
}

pub(crate) fn pathbuf_to_py_path<'py>(
    py: Python<'py>,
    handles: &PyHandles,
    pb: &Path,
) -> PyResult<Bound<'py, PyAny>> {
    let s = pathbuf_to_py_str(py, handles, pb)?;
    handles.path_cls.bind(py).call1((s,))
}

#[cfg(not(unix))]
pub(crate) fn fetch_windows_pre_stat(
    py: Python<'_>,
    path_obj: &Bound<'_, PyAny>,
    entry: Option<&Bound<'_, PyAny>>,
    follow_symlinks: bool,
) -> (bool, bool, bool, u64, Option<RawStat>) {
    let (is_symlink, st) = if let Some(ent) = entry {
        let sym = ent
            .call_method0("is_symlink")
            .and_then(|v| v.extract::<bool>())
            .unwrap_or(false);
        let kwargs = PyDict::new(py);
        let _ = kwargs.set_item("follow_symlinks", follow_symlinks || !sym);
        let Ok(stat_res) = ent.call_method("stat", (), Some(&kwargs)) else {
            return (sym, false, false, 0, None);
        };
        (sym, stat_res)
    } else {
        let Ok(os_mod) = py.import("os") else {
            return (false, false, false, 0, None);
        };
        let kwargs_no_follow = PyDict::new(py);
        let _ = kwargs_no_follow.set_item("follow_symlinks", false);
        let Ok(lst) = os_mod.call_method("stat", (path_obj,), Some(&kwargs_no_follow)) else {
            return (false, false, false, 0, None);
        };
        let lmode: u32 = lst
            .getattr("st_mode")
            .and_then(|v| v.extract())
            .unwrap_or(0);
        let sym = (lmode & 0o170_000) == 0o120_000;
        if sym && follow_symlinks {
            let Ok(followed) = os_mod.call_method1("stat", (path_obj,)) else {
                return (sym, false, false, 0, None);
            };
            (sym, followed)
        } else {
            (sym, lst)
        }
    };
    let mode: u32 = st.getattr("st_mode").and_then(|v| v.extract()).unwrap_or(0);
    let size: u64 = st.getattr("st_size").and_then(|v| v.extract()).unwrap_or(0);
    let uid: Option<u32> = st.getattr("st_uid").and_then(|v| v.extract()).ok();
    let gid: Option<u32> = st.getattr("st_gid").and_then(|v| v.extract()).ok();
    let ino: Option<u128> = st.getattr("st_ino").and_then(|v| v.extract()).ok();
    let dev: Option<u128> = st.getattr("st_dev").and_then(|v| v.extract()).ok();
    let mtime: Option<f64> = st.getattr("st_mtime").and_then(|v| v.extract()).ok();
    let ctime: Option<f64> = st.getattr("st_ctime").and_then(|v| v.extract()).ok();
    let raw = RawStat {
        mode,
        size,
        uid,
        gid,
        ino,
        dev,
        mtime,
        ctime,
    };
    let is_file = raw.is_reg();
    (is_symlink, true, is_file, size, Some(raw))
}

pub(crate) fn windows_pathext_upper() -> Option<Vec<String>> {
    if !cfg!(windows) {
        return None;
    }
    let raw = std::env::var("PATHEXT")
        .unwrap_or_else(|_| ".COM;.EXE;.BAT;.CMD;.VBS;.JS;.WS;.MSC".to_owned());
    let exts = raw
        .split(';')
        .map(str::trim)
        .filter(|e| !e.is_empty())
        .map(|e| {
            let up = e.to_uppercase();
            if up.starts_with('.') {
                up
            } else {
                format!(".{up}")
            }
        })
        .collect();
    Some(exts)
}

pub(crate) fn compute_relative_py<'py>(
    py: Python<'py>,
    handles: &PyHandles,
    path_obj: &Bound<'py, PyAny>,
    raw_path: &Path,
    root_pair: Option<(&Bound<'py, PyAny>, &Path)>,
    prefix_pair: Option<(&Bound<'py, PyAny>, &Path)>,
) -> PyResult<Bound<'py, PyAny>> {
    let Some((root_obj, raw_root)) = root_pair else {
        return Ok(path_obj.clone());
    };
    if let Ok(rel) = raw_path.strip_prefix(raw_root) {
        let rel_norm = if rel.as_os_str().is_empty() {
            Path::new(".")
        } else {
            rel
        };
        let combined = match prefix_pair {
            Some((_, pfx)) if !pfx.as_os_str().is_empty() && pfx != Path::new(".") => {
                pfx.join(rel_norm)
            }
            _ => rel_norm.to_path_buf(),
        };
        return pathbuf_to_py_path(py, handles, &combined);
    }
    let prefix_arg = prefix_pair.map_or_else(|| py.None(), |(p, _)| p.clone().unbind());
    handles
        .resolve_relative
        .bind(py)
        .call1((path_obj, root_obj, prefix_arg))
}

pub(crate) fn deliver_walk_os_error(
    py: Python<'_>,
    handles: &PyHandles,
    cb: &Py<PyAny>,
    err: &WalkOsError,
) -> PyResult<()> {
    let filename_py = pathbuf_to_py_str(py, handles, &err.path)?;
    let py_err = if let Some(code) = err.raw_errno {
        #[cfg(windows)]
        {
            let _ = handles;
            let sys_msg = py
                .import("_winapi")
                .and_then(|m| m.call_method1("FormatMessage", (code,)))
                .and_then(|v| v.extract::<String>())
                .map_or_else(
                    |_| {
                        err.message
                            .strip_suffix(&format!(" (os error {code})"))
                            .unwrap_or(&err.message)
                            .to_owned()
                    },
                    |s| s.trim_end_matches(['\r', '\n', ' ', '.']).to_owned(),
                );
            pyo3::exceptions::PyOSError::new_err((0_i32, sys_msg, filename_py.unbind(), code))
        }
        #[cfg(not(windows))]
        {
            let msg_py = handles
                .os_strerror
                .bind(py)
                .call1((code,))
                .unwrap_or_else(|_| {
                    err.message
                        .as_str()
                        .into_pyobject(py)
                        .map_or_else(|_| py.None().into_bound(py), Bound::into_any)
                });
            pyo3::exceptions::PyOSError::new_err((code, msg_py.unbind(), filename_py.unbind()))
        }
    } else {
        let base = pyo3::exceptions::PyOSError::new_err(err.message.clone());
        let _ = base.value(py).setattr("filename", filename_py);
        base
    };
    cb.bind(py).call1((py_err.value(py),))?;
    Ok(())
}
