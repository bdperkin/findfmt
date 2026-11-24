//! `identify`-compatible filename/interpreter tag tables and filter matching (#583).

use std::collections::{BTreeSet, HashMap};
use std::sync::OnceLock;

use pyo3::prelude::*;
use pyo3::types::PyDict;

pub use crate::mime::{LiveMimeDb, py_splitext};
use crate::mime::guess_mime_with_lookup;

static PYTHON_TAG_REGISTRY: OnceLock<TagRegistry> = OnceLock::new();

/// Immutable lookup tables mirroring `identify` (with optional built-in MIME maps for Rust tests).
#[derive(Clone, Debug, Default)]
pub struct TagRegistry {
    pub extensions: HashMap<String, Vec<String>>,
    pub extensions_need_binary_check: HashMap<String, Vec<String>>,
    pub names: HashMap<String, Vec<String>>,
    pub interpreters: HashMap<String, Vec<String>>,
    pub mime_types_strict: HashMap<String, String>,
    pub mime_suffix_map: HashMap<String, String>,
    pub mime_encodings_map: HashMap<String, String>,
}

/// Tag and shebang filter criteria for combined GIL-released batch classification.
#[derive(Clone, Debug, Default)]
pub struct FilterCriteria {
    pub include_tags: BTreeSet<String>,
    pub exclude_tags: BTreeSet<String>,
    pub all_tags: bool,
    pub shebang_filter: Option<String>,
}

impl FilterCriteria {
    /// Return `true` when any tag or shebang filter is active.
    pub fn is_active(&self) -> bool {
        !self.include_tags.is_empty()
            || !self.exclude_tags.is_empty()
            || self.shebang_filter.as_ref().is_some_and(|s| !s.is_empty())
    }

    /// Evaluate `src/findfmt/traversal/filters.py` tag and shebang predicates on an item.
    pub fn matches(&self, tags: &BTreeSet<String>, shebang: Option<&str>, is_dir: bool) -> bool {
        if is_dir || tags.contains("directory") {
            return true;
        }
        if !self.exclude_tags.is_empty() && !tags.is_disjoint(&self.exclude_tags) {
            return false;
        }
        if !self.include_tags.is_empty() {
            let tag_ok = if self.all_tags {
                self.include_tags.is_subset(tags)
            } else {
                !tags.is_disjoint(&self.include_tags)
            };
            if !tag_ok {
                return false;
            }
        }
        if let Some(ref needle) = self.shebang_filter
            && !needle.is_empty()
        {
            return shebang.is_some_and(|sb| sb.contains(needle.as_str()));
        }
        true
    }
}

fn extract_tag_map(obj: &Bound<'_, PyAny>) -> PyResult<HashMap<String, Vec<String>>> {
    let dict = obj.cast::<PyDict>()?;
    let mut out = HashMap::with_capacity(dict.len());
    for (k, v) in dict.iter() {
        let key: String = k.extract()?;
        let mut vals: Vec<String> = v
            .try_iter()?
            .map(|item| item?.extract())
            .collect::<PyResult<_>>()?;
        vals.sort();
        vals.dedup();
        out.insert(key, vals);
    }
    Ok(out)
}

impl TagRegistry {
    /// Obtain or initialize the process-wide static `identify` tables.
    pub fn global_from_python(py: Python<'_>) -> PyResult<&'static Self> {
        if let Some(reg) = PYTHON_TAG_REGISTRY.get() {
            return Ok(reg);
        }
        let built = Self::load_from_python(py)?;
        let _ = PYTHON_TAG_REGISTRY.set(built);
        PYTHON_TAG_REGISTRY.get().ok_or_else(|| {
            pyo3::exceptions::PyRuntimeError::new_err("failed to initialize TagRegistry")
        })
    }

    fn load_from_python(py: Python<'_>) -> PyResult<Self> {
        let ext_mod = py.import("identify.extensions")?;
        let interp_mod = py.import("identify.interpreters")?;
        Ok(Self {
            extensions: extract_tag_map(&ext_mod.getattr("EXTENSIONS")?)?,
            extensions_need_binary_check: extract_tag_map(
                &ext_mod.getattr("EXTENSIONS_NEED_BINARY_CHECK")?,
            )?,
            names: extract_tag_map(&ext_mod.getattr("NAMES")?)?,
            interpreters: extract_tag_map(&interp_mod.getattr("INTERPRETERS")?)?,
            mime_types_strict: HashMap::new(),
            mime_suffix_map: HashMap::new(),
            mime_encodings_map: HashMap::new(),
        })
    }

    /// Built-in representative registry for standalone Rust unit tests, `proptest`, and `cargo-fuzz`.
    pub fn sample_registry() -> Self {
        let mut extensions = HashMap::new();
        extensions.insert("py".into(), vec!["python".into(), "text".into()]);
        extensions.insert("rs".into(), vec!["rust".into(), "text".into()]);
        extensions.insert("sh".into(), vec!["shell".into(), "text".into()]);
        extensions.insert("png".into(), vec!["binary".into(), "image".into(), "png".into()]);
        let mut extensions_need_binary_check = HashMap::new();
        extensions_need_binary_check.insert("plist".into(), vec!["plist".into()]);
        let mut names = HashMap::new();
        names.insert("Dockerfile".into(), vec!["dockerfile".into(), "text".into()]);
        names.insert("Makefile".into(), vec!["makefile".into(), "text".into()]);
        let mut interpreters = HashMap::new();
        interpreters.insert("python3".into(), vec!["python".into(), "python3".into()]);
        interpreters.insert("bash".into(), vec!["bash".into(), "shell".into()]);
        let mut mime_types_strict = HashMap::new();
        mime_types_strict.insert(".py".into(), "text/x-python".into());
        mime_types_strict.insert(".tar".into(), "application/x-tar".into());
        let mut mime_suffix_map = HashMap::new();
        mime_suffix_map.insert(".tgz".into(), ".tar.gz".into());
        let mut mime_encodings_map = HashMap::new();
        mime_encodings_map.insert(".gz".into(), "gzip".into());
        Self {
            extensions,
            extensions_need_binary_check,
            names,
            interpreters,
            mime_types_strict,
            mime_suffix_map,
            mime_encodings_map,
        }
    }

    /// Alias preserved for internal `#[cfg(test)]` suites.
    #[cfg(test)]
    pub fn builtin_for_tests() -> Self {
        Self::sample_registry()
    }

    /// Match `identify.identify.tags_from_filename(filename)`.
    pub fn tags_from_filename(&self, filename: &str) -> BTreeSet<String> {
        let base_name = if cfg!(windows) {
            filename.rsplit(['/', '\\']).next().unwrap_or(filename)
        } else {
            filename.rsplit('/').next().unwrap_or(filename)
        };
        let mut ret = BTreeSet::new();

        if let Some(found) = self.names.get(base_name) {
            ret.extend(found.iter().cloned());
        } else {
            for part in base_name.split('.') {
                if let Some(found) = self.names.get(part) {
                    ret.extend(found.iter().cloned());
                    break;
                }
            }
        }

        let (_, ext) = py_splitext(base_name);
        if ext.len() > 1 {
            let ext_key = ext[1..].to_lowercase();
            if let Some(found) = self.extensions.get(&ext_key) {
                ret.extend(found.iter().cloned());
            } else if let Some(found) = self.extensions_need_binary_check.get(&ext_key) {
                ret.extend(found.iter().cloned());
            }
        }
        ret
    }

    /// Match `identify.identify.tags_from_interpreter(interpreter)`.
    pub fn tags_from_interpreter(&self, interpreter: &str) -> BTreeSet<String> {
        let mut candidate = interpreter.rsplit('/').next().unwrap_or(interpreter);
        while !candidate.is_empty() {
            if let Some(found) = self.interpreters.get(candidate) {
                return found.iter().cloned().collect();
            }
            match candidate.rfind('.') {
                Some(idx) => candidate = &candidate[..idx],
                None => break,
            }
        }
        BTreeSet::new()
    }

    /// Match `mimetypes.guess_type(str_path)[0]` against in-memory Rust maps.
    pub fn guess_mime_type(&self, str_path: &str) -> Option<String> {
        guess_mime_with_lookup(
            str_path,
            |k| self.mime_suffix_map.get(k).cloned(),
            |k| self.mime_encodings_map.contains_key(k),
            |k| self.mime_types_strict.get(k).cloned(),
        )
    }
}

#[cfg(test)]
#[path = "tags_tests.rs"]
mod tests;
