"""API surface stability, public export contract, and exception hierarchy tests."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

import findfmt
from findfmt.exceptions import (
    FindFmtError,
    InvalidSortCriteriaError,
    ParserError,
    TraversalError,
    UnsupportedBoxStyleError,
    UnsupportedFormatError,
    UnsupportedTableStyleError,
)
from findfmt.traversal.sorting import resolve_sort_key


def test_exception_hierarchy_inheritance() -> None:
    """Verify that custom library exceptions inherit from FindFmtError."""
    assert issubclass(FindFmtError, Exception)

    # Format errors inherit from FindFmtError and ValueError
    assert issubclass(UnsupportedFormatError, FindFmtError)
    assert issubclass(UnsupportedFormatError, ValueError)

    assert issubclass(UnsupportedTableStyleError, FindFmtError)
    assert issubclass(UnsupportedTableStyleError, ValueError)

    assert issubclass(UnsupportedBoxStyleError, FindFmtError)
    assert issubclass(UnsupportedBoxStyleError, ValueError)

    # Traversal and sorting errors
    assert issubclass(InvalidSortCriteriaError, FindFmtError)
    assert issubclass(InvalidSortCriteriaError, ValueError)

    assert issubclass(TraversalError, FindFmtError)
    assert not issubclass(TraversalError, ValueError)

    # Ingestion / parser errors
    assert issubclass(ParserError, FindFmtError)
    assert issubclass(ParserError, ValueError)


def test_exception_instantiation_and_attributes() -> None:
    """Verify custom exception constructors populate structured attributes and messages."""
    fmt_err = UnsupportedFormatError("invalid_fmt", "json, text")
    assert fmt_err.format_type == "invalid_fmt"
    assert fmt_err.valid_formats == "json, text"
    assert "invalid_fmt" in str(fmt_err)

    table_err = UnsupportedTableStyleError("fancy")
    assert table_err.table_style == "fancy"
    assert "fancy" in str(table_err)

    box_err = UnsupportedBoxStyleError("neon", "rounded, simple")
    assert box_err.table_style == "neon"
    assert box_err.valid_styles == "rounded, simple"
    assert "neon" in str(box_err)

    sort_err = InvalidSortCriteriaError("random")
    assert sort_err.criteria == "random"
    assert "random" in str(sort_err)

    trav_err = TraversalError("filesystem error")
    assert "filesystem error" in str(trav_err)

    parse_err = ParserError("malformed tab outline")
    assert "malformed tab outline" in str(parse_err)


def test_exception_catching_catch_all_base() -> None:
    """Verify consumers can catch any findfmt exception via FindFmtError or ValueError."""
    exceptions_to_test: list[tuple[Exception, str]] = [
        (UnsupportedFormatError("bad_fmt", "json"), "Unsupported output format"),
        (UnsupportedTableStyleError("bad_table"), "Unsupported RST table style"),
        (UnsupportedBoxStyleError("bad_box", "rounded"), "Unsupported table style"),
        (InvalidSortCriteriaError("bad_criteria"), "Invalid sort criteria"),
        (ParserError("parse failure"), "parse failure"),
    ]

    for exc, match_str in exceptions_to_test:
        # Catchable as FindFmtError
        with pytest.raises(FindFmtError):
            raise exc

        # Catchable as ValueError
        with pytest.raises(ValueError, match=match_str):
            raise exc

    # TraversalError is catchable as FindFmtError
    err_msg = "disk error"
    with pytest.raises(FindFmtError):
        raise TraversalError(err_msg)


def test_resolve_sort_key_raises_invalid_sort_criteria_error() -> None:
    """Verify resolve_sort_key raises InvalidSortCriteriaError."""
    invalid_val = "nonexistent_criteria"
    with pytest.raises(InvalidSortCriteriaError) as exc_info:
        resolve_sort_key(invalid_val)

    assert exc_info.value.criteria == invalid_val

    # Catchable as base package exception
    with pytest.raises(FindFmtError):
        resolve_sort_key(invalid_val)

    # Backwards-compatible catchable as ValueError
    with pytest.raises(ValueError, match="Invalid sort criteria"):
        resolve_sort_key(invalid_val)


def test_all_submodules_define_all() -> None:
    """Verify every python submodule in src/findfmt explicitly declares __all__."""
    pkg_root = Path(findfmt.__file__).resolve().parent
    py_files = sorted(pkg_root.rglob("*.py"))

    missing_all: list[str] = []

    for file_path in py_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        has_all_decl = any(
            (
                isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "__all__"
            )
            for node in tree.body
        )
        if not has_all_decl:
            missing_all.append(str(file_path.relative_to(pkg_root)))

    assert not missing_all, f"The following modules lack explicit __all__: {missing_all}"


def test_all_symbols_in_all_exist_and_are_importable() -> None:
    """Verify all symbols listed in __all__ across all modules exist and are importable."""
    pkg_root = Path(findfmt.__file__).resolve().parent
    py_files = sorted(pkg_root.rglob("*.py"))

    for file_path in py_files:
        rel_parts = file_path.relative_to(pkg_root).with_suffix("").parts
        if not rel_parts or rel_parts == ("__init__",):
            mod_name = "findfmt"
        else:
            mod_name = f"findfmt.{'.'.join(rel_parts)}".removesuffix(".__init__")

        mod = importlib.import_module(mod_name)
        all_symbols = getattr(mod, "__all__", None)
        assert all_symbols is not None, f"Module {mod_name} does not define __all__"

        for sym in all_symbols:
            msg = f"Symbol '{sym}' listed in {mod_name}.__all__ is missing from module"
            assert hasattr(mod, sym), msg


def test_no_private_symbols_in_all() -> None:
    """Verify no internal private symbols are exposed in __all__."""
    pkg_root = Path(findfmt.__file__).resolve().parent
    py_files = sorted(pkg_root.rglob("*.py"))

    for file_path in py_files:
        rel_parts = file_path.relative_to(pkg_root).with_suffix("").parts
        if not rel_parts or rel_parts == ("__init__",):
            mod_name = "findfmt"
        else:
            mod_name = f"findfmt.{'.'.join(rel_parts)}".removesuffix(".__init__")

        mod = importlib.import_module(mod_name)
        all_symbols = getattr(mod, "__all__", [])
        for sym in all_symbols:
            if sym.startswith("_") and sym not in {"_", "__version__"}:
                pytest.fail(f"Module {mod_name} exports internal symbol '{sym}' in __all__")


def test_root_package_exports() -> None:
    """Verify root findfmt package exports deliberate, stable public contract."""
    expected_exports = {
        "FileInfo",
        "FindFmtError",
        "Formatter",
        "InvalidSortCriteriaError",
        "OutputFormat",
        "ParserError",
        "SortKey",
        "TraversalConfig",
        "TraversalError",
        "UnsupportedBoxStyleError",
        "UnsupportedFormatError",
        "UnsupportedTableStyleError",
        "_",
        "__version__",
        "build_file_uri",
        "calculate_accumulated_sizes",
        "classify_file",
        "detect_locale",
        "detect_locales",
        "extract_metadata",
        "find_files",
        "format_display_path",
        "format_hyperlink",
        "format_osc8_link",
        "format_permissions",
        "format_rich_link",
        "format_size",
        "format_size_binary",
        "format_size_bytes",
        "format_size_si",
        "format_timestamp",
        "get_classification_indicator",
        "get_current_locale",
        "get_current_translation",
        "get_formatter",
        "get_known_tags",
        "get_version",
        "main",
        "main_findfilefmt",
        "main_findfilemime",
        "main_findfiles",
        "main_findfmt0",
        "main_findshebang",
        "main_findsummary",
        "mask_control_characters",
        "ngettext",
        "override_locale",
        "quote_filename",
        "reset_locale",
        "set_locale",
        "strip_ansi_escapes",
        "traverse_directory",
    }

    assert set(findfmt.__all__) == expected_exports
    for export in expected_exports:
        msg = f"Expected export '{export}' missing from root findfmt package"
        assert hasattr(findfmt, export), msg


def test_py_typed_marker_present() -> None:
    """Verify PEP 561 py.typed marker is present in the findfmt package root."""
    pkg_root = Path(findfmt.__file__).resolve().parent
    py_typed = pkg_root / "py.typed"
    assert py_typed.exists(), "PEP 561 marker py.typed is missing from findfmt package"
    assert py_typed.is_file(), "PEP 561 marker py.typed is not a regular file"
