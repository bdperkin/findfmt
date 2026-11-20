"""Package metadata, process-locale, typing, and repository invariant tests."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from tools.verify_release_version import check as check_release_version

import findfmt
from findfmt import _FALLBACK_VERSION
from findfmt.cli import diagnostics
from findfmt.cli.config_template import _format_toml_value

if TYPE_CHECKING:
    import enum


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


def test_fallback_version_synchronization() -> None:
    """Verify fallback versions in pyproject.toml, findfmt, and diagnostics match (#609)."""
    root = Path(__file__).resolve().parents[2]
    with (root / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)

    expected_fallback = data["tool"]["hatch"]["version"]["fallback-version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+\.dev0", expected_fallback) is not None
    assert expected_fallback == _FALLBACK_VERSION

    with patch("findfmt._pkg_version", side_effect=PackageNotFoundError):
        assert findfmt.get_version() == expected_fallback

    with patch("findfmt.cli.diagnostics.version", side_effect=PackageNotFoundError):
        assert diagnostics.get_version() == expected_fallback

    base_version = expected_fallback.removesuffix(".dev0")
    assert check_release_version(f"v{base_version}", repo=root) == []

    dev_literal = re.compile(r"\b\d+\.\d+\.\d+\.dev\d+\b")
    src_matches = [
        (p.relative_to(root).as_posix(), m.group(0))
        for p in sorted((root / "src").rglob("*.py"))
        for m in dev_literal.finditer(p.read_text(encoding="utf-8"))
    ]
    assert src_matches == [("src/findfmt/__init__.py", expected_fallback)]


def test_no_stack_frame_introspection() -> None:
    """Verify no module in src/findfmt uses inspect or sys._getframe (#342)."""
    pkg_root = Path(findfmt.__file__).resolve().parent
    forbidden_attrs = {"currentframe", "stack", "_getframe"}
    offenders: list[str] = []

    for file_path in sorted(pkg_root.rglob("*.py")):
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name == "inspect" for a in node.names):
                offenders.append(f"{file_path.relative_to(pkg_root)}:{node.lineno}:import inspect")
            elif isinstance(node, ast.ImportFrom) and node.module == "inspect":
                offenders.append(f"{file_path.relative_to(pkg_root)}:{node.lineno}:from inspect")
            elif isinstance(node, ast.Attribute) and node.attr in forbidden_attrs:
                offenders.append(f"{file_path.relative_to(pkg_root)}:{node.lineno}:.{node.attr}")

    assert not offenders, f"Disallowed stack frame introspection in src/findfmt: {offenders}"
