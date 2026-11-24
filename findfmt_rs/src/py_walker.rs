//! Streaming GIL-released `#[pyclass]` iterator for `find_files_rs` and `find_files` (#582).

use std::collections::{HashMap, VecDeque};

use pyo3::gc::{PyTraverseError, PyVisit};
use pyo3::prelude::*;

use crate::classifier::RawClassifyInput;
#[cfg(not(unix))]
use crate::classifier::classify_one_nogil;
use crate::py_bridge::build_py_file_info;
#[cfg(not(unix))]
use crate::py_paths::fetch_windows_pre_stat;
use crate::py_paths::{PyHandles, deliver_walk_os_error, get_handles, pathbuf_to_py_path};
use crate::py_walker_config::{prepare_walk_from_py_config, resolve_single_root_py};
use crate::tags::TagRegistry;
use crate::walker::NativeWalker;
#[cfg(not(unix))]
use crate::walker_filter::resolve_relative_pathbuf;
use crate::walker_types::{WalkConfig, WalkEvent, WalkYieldItem};

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

fn materialize_yield_item<'py>(
    py: Python<'py>,
    handles: &PyHandles,
    driver: &mut NativeIterDriver,
    item: WalkYieldItem,
) -> PyResult<Option<Bound<'py, PyAny>>> {
    let path_obj = pathbuf_to_py_path(py, handles, &item.path)?;
    let root_obj = pathbuf_to_py_path(py, handles, &item.root_path)?;
    let prefix_obj = match item.prefix {
        Some(ref pfx) => Some(pathbuf_to_py_path(py, handles, pfx)?),
        None => None,
    };
    let is_abs = item.path.is_absolute();

    #[cfg(not(unix))]
    let (raw_input, raw_classified) = {
        let mut pre = fetch_windows_pre_stat(py, &path_obj, None, item.follow_symlinks);
        // Mirror `os.DirEntry.stat()` on Windows (`WIN32_FIND_DATA` caches `st_ino=0, st_dev=0`
        // and regular-file mode `0o666`/`0o444` unless `follow_symlinks=True` resolves a symlink).
        if item.has_entry && (!pre.0 || !item.follow_symlinks) {
            if let Some(ref mut raw) = pre.4 {
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
        }
        let pre_stat = Some(pre);
        let pre_guessed_mime = Some(item.classified.mime_type.clone());
        let win_in = RawClassifyInput {
            path: item.path,
            str_path: item.str_path,
            filename: item.filename,
            follow_symlinks: item.follow_symlinks,
            accumulated_size: item.classified.accumulated_size,
            pre_stat,
            pre_guessed_mime,
        };
        let registry = driver.registry;
        let pathext_ref = driver.walk_cfg.pathext_upper.as_deref();
        let refreshed = py.detach(|| classify_one_nogil(&win_in, registry, pathext_ref));
        let is_dir_item = refreshed.is_dir || refreshed.tags.contains("directory");
        if driver.walk_cfg.scope.dirs_only && !is_dir_item {
            return Ok(None);
        }
        let rel_pb =
            resolve_relative_pathbuf(&win_in.path, &item.root_path, item.prefix.as_deref());
        if !driver.walk_cfg.filter.matches(
            &refreshed.tags,
            refreshed.shebang.as_deref(),
            is_dir_item,
        ) || !driver.walk_cfg.matcher.matches_classified_item(
            &rel_pb,
            is_dir_item,
            item.inherited_match,
        ) {
            return Ok(None);
        }
        (win_in, refreshed)
    };

    #[cfg(unix)]
    let (raw_input, raw_classified) = (
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
    );

    let mut user_map: HashMap<u32, Bound<'py, PyAny>> = driver
        .uid_cache
        .iter()
        .map(|(&k, v)| (k, v.bind(py).clone()))
        .collect();
    let mut group_map: HashMap<u32, Bound<'py, PyAny>> = driver
        .gid_cache
        .iter()
        .map(|(&k, v)| (k, v.bind(py).clone()))
        .collect();

    let info = build_py_file_info(
        py,
        handles,
        &path_obj,
        &raw_input,
        is_abs,
        item.has_entry,
        Some((&root_obj, &item.root_path)),
        prefix_obj.as_ref().zip(item.prefix.as_deref()),
        raw_classified,
        &mut user_map,
        &mut group_map,
    )?;

    for (k, v) in user_map {
        driver.uid_cache.entry(k).or_insert_with(|| v.unbind());
    }
    for (k, v) in group_map {
        driver.gid_cache.entry(k).or_insert_with(|| v.unbind());
    }
    Ok(Some(info))
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
                    if let Some(info) = materialize_yield_item(py, handles, driver, *item)? {
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
