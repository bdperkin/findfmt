//! Streaming GIL-released `#[pyclass]` iterator for `find_files_rs` and `find_files` (#582).

use std::collections::{HashMap, VecDeque};

use pyo3::gc::{PyTraverseError, PyVisit};
use pyo3::prelude::*;

use crate::py_paths::{deliver_walk_os_error, get_handles};
use crate::py_walker_config::prepare_walk_from_py_config;
use crate::py_walker_item::materialize_yield_item;
use crate::py_walker_root::resolve_single_root_py;
use crate::tags::TagRegistry;
use crate::walker::NativeWalker;
use crate::walker_types::{WalkConfig, WalkEvent};

const WALK_BATCH_SIZE: usize = 256;

struct NativeIterDriver {
    walk_cfg: WalkConfig,
    relative_prefix: bool,
    registry: &'static TagRegistry,
    pending_roots: VecDeque<Py<PyAny>>,
    current_walker: Option<NativeWalker>,
    buffered_events: VecDeque<WalkEvent>,
    on_error: Option<Py<PyAny>>,
    uid_cache: HashMap<u32, Py<PyAny>>,
    gid_cache: HashMap<u32, Py<PyAny>>,
}

enum IterState {
    Uninitialized {
        config: Py<PyAny>,
        on_error: Option<Py<PyAny>>,
    },
    Delegated {
        py_iter: Py<PyAny>,
    },
    Native(Box<NativeIterDriver>),
    Exhausted,
}

/// Lazy, streaming `Iterator[FileInfo]` backed by the GIL-free Rust directory walker.
#[pyclass(module = "findfmt._rust_ext")]
pub struct RustFileIterator {
    state: IterState,
}

#[pymethods]
impl RustFileIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __traverse__(&self, visit: PyVisit<'_>) -> Result<(), PyTraverseError> {
        match &self.state {
            IterState::Uninitialized { config, on_error } => {
                visit.call(config)?;
                if let Some(cb) = on_error {
                    visit.call(cb)?;
                }
            }
            IterState::Delegated { py_iter } => {
                visit.call(py_iter)?;
            }
            IterState::Native(driver) => {
                if let Some(cb) = &driver.on_error {
                    visit.call(cb)?;
                }
                for root_py in &driver.pending_roots {
                    visit.call(root_py)?;
                }
                for u in driver.uid_cache.values() {
                    visit.call(u)?;
                }
                for g in driver.gid_cache.values() {
                    visit.call(g)?;
                }
            }
            IterState::Exhausted => {}
        }
        Ok(())
    }

    fn __clear__(&mut self) {
        self.state = IterState::Exhausted;
    }

    fn __next__<'py>(&mut self, py: Python<'py>) -> PyResult<Option<Bound<'py, PyAny>>> {
        if matches!(self.state, IterState::Uninitialized { .. }) {
            let prev = std::mem::replace(&mut self.state, IterState::Exhausted);
            if let IterState::Uninitialized { config, on_error } = prev {
                self.initialize(py, config.bind(py), on_error)?;
            }
        }

        match &mut self.state {
            IterState::Exhausted | IterState::Uninitialized { .. } => Ok(None),
            IterState::Delegated { py_iter } => {
                let bound_iter = py_iter.bind(py);
                match bound_iter.call_method0("__next__") {
                    Ok(item) => Ok(Some(item)),
                    Err(err) if err.is_instance_of::<pyo3::exceptions::PyStopIteration>(py) => {
                        self.state = IterState::Exhausted;
                        Ok(None)
                    }
                    Err(err) => {
                        self.state = IterState::Exhausted;
                        Err(err)
                    }
                }
            }
            IterState::Native(driver) => match step_native_driver(py, driver) {
                Ok(Some(info)) => Ok(Some(info)),
                Ok(None) => {
                    self.state = IterState::Exhausted;
                    Ok(None)
                }
                Err(err) => {
                    self.state = IterState::Exhausted;
                    Err(err)
                }
            },
        }
    }
}

impl RustFileIterator {
    fn initialize(
        &mut self,
        py: Python<'_>,
        config_obj: &Bound<'_, PyAny>,
        on_error: Option<Py<PyAny>>,
    ) -> PyResult<()> {
        let handles = get_handles(py)?;
        let Some((walk_cfg, pending_roots, relative_prefix)) =
            prepare_walk_from_py_config(py, handles, config_obj)?
        else {
            let delegated_gen = handles.ingest_from_file.bind(py).call1((config_obj,))?;
            let py_iter = delegated_gen.try_iter()?.into_any().unbind();
            self.state = IterState::Delegated { py_iter };
            return Ok(());
        };

        let registry = TagRegistry::global_from_python(py)?;
        self.state = IterState::Native(Box::new(NativeIterDriver {
            walk_cfg,
            relative_prefix,
            registry,
            pending_roots,
            current_walker: None,
            buffered_events: VecDeque::new(),
            on_error,
            uid_cache: HashMap::new(),
            gid_cache: HashMap::new(),
        }));
        Ok(())
    }
}

fn step_native_driver<'py>(
    py: Python<'py>,
    driver: &mut NativeIterDriver,
) -> PyResult<Option<Bound<'py, PyAny>>> {
    let handles = get_handles(py)?;
    loop {
        if let Some(ev) = driver.buffered_events.pop_front() {
            match ev {
                WalkEvent::Error(os_err) => {
                    if let Some(ref cb) = driver.on_error {
                        deliver_walk_os_error(py, handles, cb, &os_err)?;
                    }
                }
                WalkEvent::Item(item) => {
                    if let Some(info) = materialize_yield_item(
                        py,
                        handles,
                        &driver.walk_cfg,
                        driver.registry,
                        &mut driver.uid_cache,
                        &mut driver.gid_cache,
                        *item,
                    )? {
                        return Ok(Some(info));
                    }
                }
            }
            continue;
        }

        if let Some(ref mut walker) = driver.current_walker {
            let next_events = py.detach(|| walker.next_batch(WALK_BATCH_SIZE));
            if next_events.is_empty() {
                driver.current_walker = None;
            } else {
                driver.buffered_events.extend(next_events);
            }
            continue;
        }

        let Some(raw_root_py) = driver.pending_roots.pop_front() else {
            return Ok(None);
        };
        let (root_target, maybe_root_err) = resolve_single_root_py(
            py,
            handles,
            raw_root_py.bind(py),
            driver.walk_cfg.scope.follow_symlinks,
            driver.relative_prefix,
            driver.walk_cfg.respect_gitignore,
        )?;
        if let (Some(py_err), Some(cb)) = (maybe_root_err, driver.on_error.as_ref()) {
            cb.bind(py).call1((py_err.bind(py),))?;
        }
        if root_target.resolved_root.is_some() {
            driver.current_walker = Some(NativeWalker::new(
                driver.walk_cfg.clone(),
                driver.registry,
                vec![root_target],
            ));
        }
    }
}

/// Construct a lazy `RustFileIterator` for `find_files_rs` and `find_files`.
pub fn find_files_py(
    config: &Bound<'_, PyAny>,
    on_error: Option<&Bound<'_, PyAny>>,
) -> RustFileIterator {
    let err_cb = on_error
        .filter(|cb| !cb.is_none())
        .map(|cb| cb.clone().unbind());
    RustFileIterator {
        state: IterState::Uninitialized {
            config: config.clone().unbind(),
            on_error: err_cb,
        },
    }
}
