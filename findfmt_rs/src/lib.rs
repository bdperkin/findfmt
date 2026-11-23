//! Native PyO3 extension module for `findfmt._rust_ext`.

#![forbid(unsafe_code)]
#![cfg_attr(
    not(test),
    deny(clippy::unwrap_used, clippy::expect_used, clippy::panic)
)]

pub mod classifier;
pub mod fuzz_entrypoints;
pub mod gitignore;
pub mod header;
pub mod metadata;
pub mod mime;
pub mod py_bridge;
mod py_paths;
pub mod shebang;
pub mod sorting;
pub mod tags;

use pyo3::prelude::*;
use pyo3::types::PyList;

/// Return the identifier of the active native backend (`"rust"`).
#[pyfunction]
fn backend_name() -> &'static str {
    "rust"
}

/// Return the Cargo package version of `findfmt_rs`.
#[pyfunction]
fn rust_ext_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Classify a single file path via the GIL-released native Rust inspection engine (#583).
#[pyfunction]
#[pyo3(signature = (path, root_path=None, prefix=None, accumulated_size=None, *, entry=None, follow_symlinks=false))]
fn classify_file_rs<'py>(
    py: Python<'py>,
    path: &Bound<'py, PyAny>,
    root_path: Option<&Bound<'py, PyAny>>,
    prefix: Option<&Bound<'py, PyAny>>,
    accumulated_size: Option<u64>,
    entry: Option<&Bound<'py, PyAny>>,
    follow_symlinks: bool,
) -> PyResult<Bound<'py, PyAny>> {
    py_bridge::classify_single_py(
        py,
        path,
        root_path,
        prefix,
        accumulated_size,
        entry,
        follow_symlinks,
    )
}

/// Gateway alias for `classify_file_rs` dispatched by `src/findfmt/core.py` (#578, #583).
#[pyfunction]
#[pyo3(signature = (path, root_path=None, prefix=None, accumulated_size=None, *, entry=None, follow_symlinks=false))]
fn classify_file<'py>(
    py: Python<'py>,
    path: &Bound<'py, PyAny>,
    root_path: Option<&Bound<'py, PyAny>>,
    prefix: Option<&Bound<'py, PyAny>>,
    accumulated_size: Option<u64>,
    entry: Option<&Bound<'py, PyAny>>,
    follow_symlinks: bool,
) -> PyResult<Bound<'py, PyAny>> {
    py_bridge::classify_single_py(
        py,
        path,
        root_path,
        prefix,
        accumulated_size,
        entry,
        follow_symlinks,
    )
}

/// Classify and filter a batch of `(path, has_entry, accumulated_size)` items in a single GIL-released pass.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(signature = (candidates, *, root_path=None, prefix=None, follow_symlinks=false, include_tags=None, exclude_tags=None, all_tags=false, shebang_filter=None))]
fn classify_batch_rs<'py>(
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
    py_bridge::classify_batch_py(
        py,
        candidates,
        root_path,
        prefix,
        follow_symlinks,
        include_tags,
        exclude_tags,
        all_tags,
        shebang_filter,
    )
}

/// Native acceleration module for `findfmt`.
#[pymodule]
fn _rust_ext(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__doc__", "Native PyO3 acceleration module for findfmt.")?;
    m.add_function(wrap_pyfunction!(backend_name, m)?)?;
    m.add_function(wrap_pyfunction!(rust_ext_version, m)?)?;
    m.add_function(wrap_pyfunction!(classify_file_rs, m)?)?;
    m.add_function(wrap_pyfunction!(classify_file, m)?)?;
    m.add_function(wrap_pyfunction!(classify_batch_rs, m)?)?;
    Ok(())
}
