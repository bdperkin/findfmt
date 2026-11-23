//! MIME lookup, `splitext`, and URL-scheme resolution mirroring Python's `mimetypes` (#583).

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};

/// Live view of Python's `mimetypes._db` dictionaries refreshed per classification operation.
pub struct LiveMimeDb<'py> {
    strict_dict: Bound<'py, PyDict>,
    suffix_map: Bound<'py, PyDict>,
    encodings_map: Bound<'py, PyDict>,
}

impl<'py> LiveMimeDb<'py> {
    /// Read the active `mimetypes._db` dictionaries so runtime `mimetypes.add_type` calls take effect.
    pub fn from_python(py: Python<'py>) -> PyResult<Self> {
        let mime_mod = py.import("mimetypes")?;
        if mime_mod.getattr("_db")?.is_none() {
            mime_mod.call_method0("init")?;
        }
        let db = mime_mod.getattr("_db")?;
        let types_map_tuple = db.getattr("types_map")?.cast_into::<PyTuple>()?;
        Ok(Self {
            strict_dict: types_map_tuple.get_item(1)?.cast_into::<PyDict>()?,
            suffix_map: db.getattr("suffix_map")?.cast_into::<PyDict>()?,
            encodings_map: db.getattr("encodings_map")?.cast_into::<PyDict>()?,
        })
    }

    /// Match `mimetypes.guess_type(str_path)[0]` against the live Python `mimetypes._db`.
    pub fn guess_mime_type(&self, str_path: &str) -> Option<String> {
        let dict_str = |d: &Bound<'py, PyDict>, key: &str| -> Option<String> {
            d.get_item(key).ok().flatten().and_then(|v| v.extract().ok())
        };
        guess_mime_with_lookup(
            str_path,
            |k| dict_str(&self.suffix_map, k),
            |k| self.encodings_map.contains(k).unwrap_or(false),
            |k| dict_str(&self.strict_dict, k),
        )
    }
}

/// Split `(root, ext)` matching Python's `os.path.splitext` leading-dot semantics.
pub fn py_splitext(path: &str) -> (String, String) {
    py_splitext_mode(path, false)
}

pub(crate) fn py_splitext_mode(path: &str, posix_only: bool) -> (String, String) {
    let sep_idx = if cfg!(windows) && !posix_only {
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

enum MimeUrlOutcome<'a> {
    DirectMime(Option<String>),
    FilePath { path: &'a str, posix_only: bool },
}

fn parse_mime_url_or_path(str_path: &str) -> MimeUrlOutcome<'_> {
    if let Some(colon_idx) = str_path.find(':') {
        if colon_idx > 1 {
            let scheme = &str_path[..colon_idx];
            let valid_scheme = scheme.as_bytes().first().is_some_and(u8::is_ascii_alphabetic)
                && scheme
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'+' | b'-' | b'.'));
            if valid_scheme {
                let rest = &str_path[colon_idx + 1..];
                let end = rest.find(['?', '#']).unwrap_or(rest.len());
                let path_part = match rest[..end].strip_prefix("//") {
                    Some(after_slashes) => match after_slashes.find('/') {
                        Some(slash_idx) => &after_slashes[slash_idx..],
                        None => "",
                    },
                    None => &rest[..end],
                };
                if scheme.eq_ignore_ascii_case("data") {
                    let Some(comma_idx) = path_part.find(',') else {
                        return MimeUrlOutcome::DirectMime(None);
                    };
                    let before_comma = &path_part[..comma_idx];
                    let raw_type = match before_comma.find(';') {
                        Some(semi_idx) => &before_comma[..semi_idx],
                        None => before_comma,
                    };
                    let mime = if raw_type.contains('=') || !raw_type.contains('/') {
                        "text/plain".to_owned()
                    } else {
                        raw_type.to_owned()
                    };
                    return MimeUrlOutcome::DirectMime(Some(mime));
                }
                return MimeUrlOutcome::FilePath {
                    path: path_part,
                    posix_only: true,
                };
            }
        }
    }
    MimeUrlOutcome::FilePath {
        path: str_path,
        posix_only: false,
    }
}

pub(crate) fn guess_mime_with_lookup<FSuf, FEnc, FType>(
    str_path: &str,
    lookup_suffix: FSuf,
    has_encoding: FEnc,
    lookup_type: FType,
) -> Option<String>
where
    FSuf: Fn(&str) -> Option<String>,
    FEnc: Fn(&str) -> bool,
    FType: Fn(&str) -> Option<String>,
{
    let (target, posix_only) = match parse_mime_url_or_path(str_path) {
        MimeUrlOutcome::DirectMime(mime) => return mime,
        MimeUrlOutcome::FilePath { path, posix_only } => (path, posix_only),
    };
    let (mut base, mut ext) = py_splitext_mode(target, posix_only);
    for _ in 0..8 {
        let lower = ext.to_lowercase();
        let Some(mapped) = lookup_suffix(&lower) else {
            break;
        };
        let combined = format!("{base}{mapped}");
        let (nb, ne) = py_splitext_mode(&combined, posix_only);
        base = nb;
        ext = ne;
    }
    if has_encoding(&ext) {
        let (_, ne) = py_splitext_mode(&base, posix_only);
        ext = ne;
    }
    if ext.is_empty() {
        return None;
    }
    lookup_type(&ext).or_else(|| lookup_type(&ext.to_lowercase()))
}
