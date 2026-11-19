//! Native PyO3 extension module scaffold for `findfmt._rust_ext`.

use pyo3::prelude::*;

/// Native acceleration module for `findfmt`.
#[pymodule]
fn _rust_ext(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__doc__", "Native PyO3 acceleration module for findfmt.")?;
    Ok(())
}
