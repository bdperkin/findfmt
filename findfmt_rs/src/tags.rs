//! `identify`-compatible filename/interpreter tag tables, MIME lookup, and filter matching (#583).

use std::collections::{BTreeSet, HashMap};
use std::sync::OnceLock;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};

static PYTHON_TAG_REGISTRY: OnceLock<TagRegistry> = OnceLock::new();

/// Immutable lookup tables mirroring `identify` and Python's initialized `mimetypes` database.
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

    /// Evaluate `src/findfmt/traversal/filters.py` tag and shebang predicates on a non-directory item.
    pub fn matches(&self, tags: &BTreeSet<String>, shebang: Option<&str>, is_dir: bool) -> bool {
        if is_dir {
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

/// Split `(root, ext)` matching Python's `os.path.splitext` leading-dot semantics.
pub fn py_splitext(path: &str) -> (String, String) {
    let sep_idx = if cfg!(windows) {
        path.rfind(['/', '\\'])
    } else {
        path.rfind('/')
    };
    let name_start = sep_idx.map_or(0, |i| i + 1);
    let filename = &path[name_start..];
    let Some(non_dot_rel) = filename.bytes().position(|b| b != b'.') else {
        return (path.to_owned(), String::new());
    };
    let search_start = name_start + non_dot_rel;
    match path[search_start..].rfind('.') {
        Some(dot_rel) => {
            let dot_idx = search_start + dot_rel;
            (path[..dot_idx].to_owned(), path[dot_idx..].to_owned())
        }
        None => (path.to_owned(), String::new()),
    }
}

fn extract_tag_map(obj: &Bound<'_, PyAny>) -> PyResult<HashMap<String, Vec<String>>> {
    let dict = obj.cast::<PyDict>()?;
    let mut out = HashMap::with_capacity(dict.len());
    for (k, v) in dict.iter() {
        let key: String = k.extract()?;
        let mut vals: Vec<String> = v.try_iter()?.map(|item| item?.extract()).collect::<PyResult<_>>()?;
        vals.sort();
        vals.dedup();
        out.insert(key, vals);
    }
    Ok(out)
}

fn extract_str_map(obj: &Bound<'_, PyAny>) -> PyResult<HashMap<String, String>> {
    let dict = obj.cast::<PyDict>()?;
    let mut out = HashMap::with_capacity(dict.len());
    for (k, v) in dict.iter() {
        out.insert(k.extract()?, v.extract()?);
    }
    Ok(out)
}

impl TagRegistry {
    /// Obtain or initialize the process-wide `TagRegistry` synced with `identify` and `mimetypes`.
    pub fn global_from_python(py: Python<'_>) -> PyResult<&'static Self> {
        if let Some(reg) = PYTHON_TAG_REGISTRY.get() {
            return Ok(reg);
        }
        let built = Self::load_from_python(py)?;
        let _ = PYTHON_TAG_REGISTRY.set(built);
        Ok(PYTHON_TAG_REGISTRY.get().expect("initialized TagRegistry"))
    }

    fn load_from_python(py: Python<'_>) -> PyResult<Self> {
        let ext_mod = py.import("identify.extensions")?;
        let interp_mod = py.import("identify.interpreters")?;
        let mime_mod = py.import("mimetypes")?;
        if mime_mod.getattr("_db")?.is_none() {
            mime_mod.call_method0("init")?;
        }
        let db = mime_mod.getattr("_db")?;
        let types_map_tuple = db.getattr("types_map")?.cast_into::<PyTuple>()?;
        let strict_dict = types_map_tuple.get_item(1)?;

        Ok(Self {
            extensions: extract_tag_map(&ext_mod.getattr("EXTENSIONS")?)?,
            extensions_need_binary_check: extract_tag_map(
                &ext_mod.getattr("EXTENSIONS_NEED_BINARY_CHECK")?,
            )?,
            names: extract_tag_map(&ext_mod.getattr("NAMES")?)?,
            interpreters: extract_tag_map(&interp_mod.getattr("INTERPRETERS")?)?,
            mime_types_strict: extract_str_map(&strict_dict)?,
            mime_suffix_map: extract_str_map(&db.getattr("suffix_map")?)?,
            mime_encodings_map: extract_str_map(&db.getattr("encodings_map")?)?,
        })
    }

    /// Minimal built-in registry for standalone `cargo test --no-default-features` unit tests.
    #[cfg(test)]
    pub fn builtin_for_tests() -> Self {
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

    /// Match `mimetypes.guess_type(str_path)[0]`.
    pub fn guess_mime_type(&self, str_path: &str) -> Option<String> {
        let target = strip_url_scheme_if_any(str_path)?;
        let (mut base, mut ext) = py_splitext(target);
        for _ in 0..8 {
            let lower = ext.to_lowercase();
            let Some(mapped) = self.mime_suffix_map.get(&lower) else {
                break;
            };
            let combined = format!("{base}{mapped}");
            let (nb, ne) = py_splitext(&combined);
            base = nb;
            ext = ne;
        }
        if self.mime_encodings_map.contains_key(&ext) {
            let (_, ne) = py_splitext(&base);
            ext = ne;
        }
        if ext.is_empty() {
            return None;
        }
        self.mime_types_strict
            .get(&ext)
            .or_else(|| self.mime_types_strict.get(&ext.to_lowercase()))
            .cloned()
    }
}

fn strip_url_scheme_if_any(str_path: &str) -> Option<&str> {
    if let Some(colon_idx) = str_path.find(':')
        && colon_idx > 1
    {
        let scheme = &str_path[..colon_idx];
        let valid_scheme = scheme.as_bytes().first().is_some_and(u8::is_ascii_alphabetic)
            && scheme
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'+' | b'-' | b'.'));
        if valid_scheme {
            let rest = &str_path[colon_idx + 1..];
            if scheme.eq_ignore_ascii_case("data") {
                return None;
            }
            let end = rest.find(['?', '#']).unwrap_or(rest.len());
            return Some(&rest[..end]);
        }
    }
    Some(str_path)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn splitext_and_tag_lookup_parity() {
        assert_eq!(py_splitext(".bashrc"), (".bashrc".into(), String::new()));
        assert_eq!(py_splitext(".hidden.py"), (".hidden".into(), ".py".into()));
        assert_eq!(py_splitext("archive.tar.gz"), ("archive.tar".into(), ".gz".into()));

        let reg = TagRegistry::builtin_for_tests();
        assert!(reg.tags_from_filename("Dockerfile.prod").contains("dockerfile"));
        assert!(reg.tags_from_filename("app.PY").contains("python"));
        assert!(reg.tags_from_interpreter("/usr/bin/python3.12.1").contains("python3"));
        assert_eq!(
            reg.guess_mime_type("bundle.tgz"),
            Some("application/x-tar".into())
        );
    }

    #[test]
    fn filter_criteria_evaluation() {
        let tags: BTreeSet<String> = ["file", "python", "text"]
            .into_iter()
            .map(String::from)
            .collect();
        let mut crit = FilterCriteria {
            include_tags: ["python", "text"].into_iter().map(String::from).collect(),
            exclude_tags: BTreeSet::new(),
            all_tags: true,
            shebang_filter: Some("python3".into()),
        };
        assert!(crit.is_active());
        assert!(crit.matches(&tags, Some("#!/usr/bin/env python3"), false));
        assert!(!crit.matches(&tags, None, false));
        crit.exclude_tags.insert("text".into());
        assert!(!crit.matches(&tags, Some("#!/usr/bin/env python3"), false));
        assert!(crit.matches(&tags, None, true));
    }
}
