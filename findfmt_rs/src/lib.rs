//! Native PyO3 extension module for `findfmt._rust_ext`.

use pyo3::prelude::*;

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

/// Native acceleration module for `findfmt`.
#[pymodule]
fn _rust_ext(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__doc__", "Native PyO3 acceleration module for findfmt.")?;
    m.add_function(wrap_pyfunction!(backend_name, m)?)?;
    m.add_function(wrap_pyfunction!(rust_ext_version, m)?)?;
    Ok(())
}
