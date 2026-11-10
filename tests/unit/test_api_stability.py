"""API surface stability, public export contract, and exception hierarchy tests."""

from __future__ import annotations

import ast
import enum
import importlib
import os
import re
import subprocess
import sys
import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest

import findfmt
from findfmt.cli.file_config import _format_toml_value
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


@pytest.mark.parametrize(
    "attr",
    [
        "main",
        "main_findfilefmt",
        "main_findfilemime",
        "main_findfiles",
        "main_findfmt0",
        "main_findshebang",
        "main_findsummary",
        "_",
    ],
)
def test_lazy_deprecated_root_exports(attr: str) -> None:
    """Deprecated CLI entry points and _ lazy-load from findfmt with DeprecationWarning (#452)."""
    with pytest.deprecated_call(match=rf"'findfmt\.{attr}' is deprecated"):
        resolved = getattr(findfmt, attr)

    assert callable(resolved)


def test_lazy_module_getattr_and_importtime() -> None:
    """Verify lazy __getattr__ fallbacks and that importing findfmt skips typer and rich (#452)."""
    assert findfmt.get_version() == findfmt.__version__
    with patch("findfmt._pkg_version", side_effect=PackageNotFoundError):
        assert findfmt.get_version() == "1.1.3.dev0"

    with pytest.raises(AttributeError, match="has no attribute 'nonexistent_symbol'"):
        findfmt.__getattr__("nonexistent_symbol")

    assert findfmt.formatters.__getattr__("RichTableFormatter").__name__ == "RichTableFormatter"
    assert findfmt.formatters.__getattr__("RichTreeFormatter").__name__ == "RichTreeFormatter"
    with pytest.raises(AttributeError, match="has no attribute 'nonexistent_formatter'"):
        findfmt.formatters.__getattr__("nonexistent_formatter")

    proc = subprocess.run(
        [sys.executable, "-X", "importtime", "-c", "import findfmt"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "typer" not in proc.stderr
    assert "rich" not in proc.stderr


def test_import_does_not_change_process_locale() -> None:
    """Importing findfmt under LC_ALL=de_DE.UTF-8 leaves process locale unchanged (#451)."""
    script = (
        "import locale, sys; "
        "before_all = locale.setlocale(locale.LC_ALL); "
        "before_num = locale.setlocale(locale.LC_NUMERIC); "
        "import findfmt; "
        "after_all = locale.setlocale(locale.LC_ALL); "
        "after_num = locale.setlocale(locale.LC_NUMERIC); "
        "assert before_all == after_all, (before_all, after_all); "
        "assert before_num == after_num, (before_num, after_num); "
        "assert findfmt.format_size_binary(1536) == '1.5 KiB'; "
        "sys.stdout.write('ok\\n')"
    )
    env = {**os.environ, "LC_ALL": "de_DE.UTF-8", "LANG": "de_DE.UTF-8", "LANGUAGE": "de_DE:de"}
    proc = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == "ok"


def test_py_typed_marker_present() -> None:
    """Verify PEP 561 py.typed marker is present in the findfmt package root."""
    pkg_root = Path(findfmt.__file__).resolve().parent
    py_typed = pkg_root / "py.typed"
    assert py_typed.exists(), "PEP 561 marker py.typed is missing from findfmt package"
    assert py_typed.is_file(), "PEP 561 marker py.typed is not a regular file"


def test_project_description_has_no_typos() -> None:
    """The PyPI summary must not run the leading article into the next word (#443)."""
    pyproject = (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    assert "A.gitignore" not in pyproject
    assert "A .gitignore-aware" in pyproject


def test_no_pre_311_version_guards() -> None:
    """Verify no ``sys.version_info`` guard targets Python 3.11 or older (3.11 is the minimum)."""
    guard = re.compile(r"version_info\s*[<>]=?\s*\(\s*3\s*,\s*(\d+)\s*\)")
    root = Path(__file__).resolve().parents[2]
    offenders = [
        f"{path.relative_to(root)}:{lineno}"
        for top in ("src", "tests", "tools")
        for path in sorted((root / top).rglob("*.py"))
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if (match := guard.search(line)) and int(match.group(1)) <= 11
    ]
    assert not offenders, f"Obsolete Python <= 3.11 version guards: {offenders}"


@pytest.mark.parametrize("enum_cls", [findfmt.SortKey, findfmt.OutputFormat])
def test_public_str_enums_stringify_to_value(enum_cls: type[enum.StrEnum]) -> None:
    """Verify public string enums render as their value in str(), format() and TOML output."""
    for member in enum_cls:
        assert str(member) == member.value
        assert f"{member}" == member.value
        assert _format_toml_value(member) == f'"{member.value}"'
        assert enum_cls(member.value) is member


def test_no_coverage_pragma_on_reachable_code() -> None:
    """Verify no pragma: no cover annotations remain in src, tests, or tools (#353)."""
    root = Path(__file__).resolve().parents[2]
    pragma = re.compile(r"#\s*pragma:\s*no cover\b")
    bad = [
        f"{p.relative_to(root)}:{n}"
        for top in ("src", "tests", "tools")
        for p in sorted((root / top).rglob("*.py"))
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if pragma.search(line)
    ]
    assert not bad, f"Disallowed pragma: no cover found: {bad}"


def test_declared_minimums_match_lockfile_floor() -> None:
    """Verify declared pyproject.toml dependency minimums are >= bisected verified floors (#325)."""
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    verified_floors = {
        "identify": (2, 6),
        "pathspec": (1, 0, 1),
        "pyyaml": (6, 0, 1),
        "rich": (13, 8),
        "typer": (0, 16),
        "typing-extensions": (4, 4),
    }

    declared: dict[str, tuple[int, ...]] = {}
    for spec in data["project"]["dependencies"]:
        pkg, ver = spec.split(";")[0].strip().split(">=", 1)
        declared[pkg.strip()] = tuple(int(part) for part in ver.strip().split("."))

    assert set(declared) == set(verified_floors)
    for pkg, floor in verified_floors.items():
        assert declared[pkg] >= floor, f"{pkg} minimum {declared[pkg]} is below floor {floor}"
