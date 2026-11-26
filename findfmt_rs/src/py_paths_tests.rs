//! Unit tests for `findfmt_rs::py_paths` error-delivery and pre-stat fallbacks (#590).

use pyo3::types::PyList;

use super::*;

#[test]
fn deliver_walk_os_error_handles_missing_and_invalid_errno() -> PyResult<()> {
    Python::initialize();
    Python::attach(|py| {
        let builtins = py.import("builtins")?;
        let os_mod = py.import("os")?;
        let pathlib = py.import("pathlib")?;
        let path_cls = pathlib.getattr("Path")?;
        let none = || py.None();
        let handles = PyHandles {
            path_home: path_cls.getattr("home")?.unbind(),
            path_cls: path_cls.unbind(),
            file_info_cls: none(),
            #[cfg(unix)]
            fsencode: os_mod.getattr("fsencode")?.unbind(),
            #[cfg(unix)]
            fsdecode: os_mod.getattr("fsdecode")?.unbind(),
            os_strerror: os_mod.getattr("strerror")?.unbind(),
            sorted_fn: builtins.getattr("sorted")?.unbind(),
            resolve_user_name: none(),
            resolve_group_name: none(),
            resolve_relative: none(),
            compute_relative_prefix: none(),
            find_global_gitignore_path: none(),
            i18n_gettext: builtins.getattr("str")?.unbind(),
            make_negative_bound_error: none(),
            make_overflow_bound_error: none(),
            make_invalid_pattern_error: none(),
            ingest_from_file: none(),
            unicode_major: 16,
        };

        let captured = PyList::empty(py);
        let append_cb = captured.getattr("append")?.unbind();

        for code in [None, Some(2), Some(-999_999)] {
            deliver_walk_os_error(
                py,
                &handles,
                &append_cb,
                &WalkOsError {
                    raw_errno: code,
                    path: PathBuf::from("/tmp/os_err_case"),
                },
            )?;
        }

        let bad_handles = PyHandles {
            path_home: handles.path_home.clone_ref(py),
            path_cls: handles.path_cls.clone_ref(py),
            file_info_cls: none(),
            #[cfg(unix)]
            fsencode: handles.fsencode.clone_ref(py),
            #[cfg(unix)]
            fsdecode: handles.fsdecode.clone_ref(py),
            os_strerror: builtins.getattr("len")?.unbind(),
            sorted_fn: handles.sorted_fn.clone_ref(py),
            resolve_user_name: none(),
            resolve_group_name: none(),
            resolve_relative: none(),
            compute_relative_prefix: none(),
            find_global_gitignore_path: none(),
            i18n_gettext: handles.i18n_gettext.clone_ref(py),
            make_negative_bound_error: none(),
            make_overflow_bound_error: none(),
            make_invalid_pattern_error: none(),
            ingest_from_file: none(),
            unicode_major: 16,
        };
        deliver_walk_os_error(
            py,
            &bad_handles,
            &append_cb,
            &WalkOsError {
                raw_errno: Some(1),
                path: PathBuf::from("/tmp/broken_strerror"),
            },
        )?;
        assert_eq!(captured.len(), 4);

        #[cfg(not(unix))]
        {
            let types_mod = py.import("types")?;
            let sns = types_mod.getattr("SimpleNamespace")?;
            let missing = handles
                .path_cls
                .bind(py)
                .call1(("nonexistent_findfmt_win_stat_target.py",))?;
            assert!(!fetch_windows_pre_stat(py, &missing, None, false).1);

            let bad_ent_kw = pyo3::types::PyDict::new(py);
            bad_ent_kw.set_item("is_symlink", builtins.getattr("bool")?)?;
            bad_ent_kw.set_item("stat", builtins.getattr("int")?)?;
            let bad_ent = sns.call((), Some(&bad_ent_kw))?;
            assert!(!fetch_windows_pre_stat(py, &missing, Some(&bad_ent), false).1);
        }

        Ok(())
    })
}
