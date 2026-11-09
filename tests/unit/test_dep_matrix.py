"""Unit tests for tools/dep_matrix.py and tools/verify_quality.py."""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from tools import dep_matrix, verify_quality
from tools.dep_matrix import (
    FULL_MATRIX,
    SMOKE_MATRIX,
    DiagnosticSnapshot,
    MatrixCell,
    capture_diagnostics,
    extract_failed_modules,
    format_failure_diagnostics,
    is_prerelease_version,
    load_declared_bounds,
    load_locked_versions,
    load_supported_pythons,
    normalize_pkg_name,
    select_cells,
)


def _proc(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["cmd"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_matrix_cell_and_normalization_helpers() -> None:
    cell = MatrixCell("M1", "lowest-direct", "disallow", "fewest")
    assert "M1 (resolution=lowest-direct, prerelease=disallow, fork-strategy=fewest)" in cell.label
    assert len(SMOKE_MATRIX) == 2
    assert len(FULL_MATRIX) == 6
    assert normalize_pkg_name("Typing_Extensions..Foo") == "typing-extensions-foo"
    assert is_prerelease_version("1.2.0a1") is True
    assert is_prerelease_version("2.0.0rc2") is True
    assert is_prerelease_version("1.0.dev3") is True
    assert is_prerelease_version("1.2.0") is False


def test_load_declared_bounds_and_locked_versions(tmp_path: Path) -> None:
    assert load_declared_bounds(tmp_path / "missing.toml") == {}
    assert load_locked_versions(tmp_path / "missing.lock") == {}

    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text(
        'project = "not-a-dict"\n[dependency-groups]\ntest = "bad"\n',
        encoding="utf-8",
    )
    assert load_declared_bounds(bad_toml) == {}

    bad_lock = tmp_path / "bad.lock"
    bad_lock.write_text('package = "not-a-list"\n', encoding="utf-8")
    assert load_locked_versions(bad_lock) == {}

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\ndependencies = [\n  "typer>=0.16",\n'
        '  "typing_extensions>=4.4; python_version<\'3.12\'",\n  "===bad",\n]\n'
        '[dependency-groups]\ntest = ["pytest>=8", { include-group = "other" }]\n',
        encoding="utf-8",
    )
    bounds = load_declared_bounds(pyproject)
    assert bounds == {
        "typer": "typer>=0.16",
        "typing-extensions": "typing_extensions>=4.4",
        "pytest": "pytest>=8",
    }

    lockfile = tmp_path / "uv.lock"
    lockfile.write_text(
        '[[package]]\nname = "Typer"\nversion = "0.24.0"\n[[package]]\nname = "incomplete"\n',
        encoding="utf-8",
    )
    assert load_locked_versions(lockfile) == {"typer": "0.24.0"}


def test_extract_failed_modules() -> None:
    trace = (
        "ModuleNotFoundError: No module named 'typer.core'\n"
        "ImportError: cannot import name 'Console' from 'rich.console'\n"
        "AttributeError: module 'pathspec' has no attribute 'GitIgnoreSpec'\n"
        "ModuleNotFoundError: No module named 'typer'\n"
    )
    assert extract_failed_modules(trace) == ["typer", "rich", "pathspec"]


def test_format_failure_diagnostics_all_branches() -> None:
    cell_m1 = MatrixCell("M1", "lowest-direct", "disallow", "fewest")
    snap = DiagnosticSnapshot(
        tree_output="findfmt v1.1.3\n└── typer v0.16.0",
        installed={"typer": "0.16.0", "rich": "13.8.0", "untracked": "1.0.0"},
        declared_bounds={
            "typer": "typer>=0.16",
            "rich": "rich>=13.8",
            "missing": "missing>=1.0",
            "untracked": "untracked>=1.0",
        },
        locked_versions={"typer": "0.24.0", "rich": "13.8.0"},
        error_output="AttributeError: module 'untracked' has no attribute 'run'",
    )
    report = format_failure_diagnostics(cell_m1, snap)
    assert "[Stage 1] Resolved Dependency Tree" in report
    assert "typer: installed=0.16.0 (uv.lock=0.24.0)" in report
    assert "Implicated modules from traceback: untracked" in report
    assert "Update 'typer>=0.16' in pyproject.toml" in report
    assert "recommend 'typer>=0.24.0'" in report
    assert "Update 'untracked>=1.0' in pyproject.toml" in report
    assert "recommend 'untracked>1.0.0'" in report

    cell_m2 = MatrixCell("M2", "highest", "allow", "fewest")
    snap_pre = DiagnosticSnapshot(
        tree_output="",
        installed={"click": "8.2.0a1", "rich": "13.8.0"},
        declared_bounds={},
        locked_versions={"click": "8.2.0a1", "rich": "13.8.0"},
        error_output="",
    )
    report_pre = format_failure_diagnostics(cell_m2, snap_pre)
    assert "(dependency tree unavailable)" in report_pre
    assert "(all installed packages match uv.lock)" in report_pre
    assert "Pre-release package detected: click==8.2.0a1" in report_pre

    snap_empty = DiagnosticSnapshot("", {}, {}, {}, "")
    report_empty = format_failure_diagnostics(cell_m1, snap_empty)
    assert "Inspect the dependency tree above" in report_empty


def test_capture_diagnostics_subprocess_handling(tmp_path: Path) -> None:
    cell = MatrixCell("M1", "lowest-direct", "disallow", "fewest")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["typer>=0.16"]\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "typer"\nversion = "0.24.0"\n',
        encoding="utf-8",
    )

    with patch("tools.dep_matrix.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _proc(0, stdout="findfmt\n└── typer v0.16.0\n"),
            _proc(0, stdout='[{"name": "typer", "version": "0.16.0"}, "skip"]'),
        ]
        out = capture_diagnostics(cell, tmp_path / "venv", tmp_path, "")
        assert "typer>=0.24.0" in out

        mock_run.side_effect = [
            _proc(1, stdout="", stderr="tree err"),
            _proc(0, stdout="not-json"),
        ]
        out_bad_json = capture_diagnostics(cell, tmp_path / "venv", tmp_path, "")
        assert "tree err" in out_bad_json

        mock_run.side_effect = [
            _proc(0, stdout="tree ok"),
            _proc(0, stdout='{"not": "a-list"}'),
        ]
        out_non_list = capture_diagnostics(cell, tmp_path / "venv", tmp_path, "")
        assert "tree ok" in out_non_list

        mock_run.side_effect = [
            _proc(0, stdout="tree ok"),
            _proc(1, stdout=""),
        ]
        out_list_fail = capture_diagnostics(cell, tmp_path / "venv", tmp_path, "")
        assert "tree ok" in out_list_fail


def test_select_cells_and_dep_matrix_main() -> None:
    assert select_cells(full=True) == FULL_MATRIX
    assert select_cells(smoke=True) == SMOKE_MATRIX
    assert select_cells() == SMOKE_MATRIX
    custom = select_cells(resolution="lowest", prerelease="if-necessary")
    assert len(custom) == 1
    assert custom[0] == MatrixCell("CUSTOM", "lowest", "if-necessary", "fewest")

    with patch("tools.dep_matrix.subprocess.run", return_value=_proc(0)) as mock_run:
        assert dep_matrix.main(["--smoke"]) == 0
        mock_run.assert_called_once()


def test_venv_python_resolution(tmp_path: Path) -> None:
    assert verify_quality.resolve_venv_python(tmp_path) == tmp_path / "bin" / "python"
    win_dir = tmp_path / "Scripts"
    win_dir.mkdir()
    win_py = win_dir / "python.exe"
    win_py.write_text("", encoding="utf-8")
    assert verify_quality.resolve_venv_python(tmp_path) == win_py
    posix_dir = tmp_path / "bin"
    posix_dir.mkdir()
    posix_py = posix_dir / "python"
    posix_py.write_text("", encoding="utf-8")
    assert verify_quality.resolve_venv_python(tmp_path) == posix_py


def test_run_step_and_quality_suite() -> None:
    with patch("tools.verify_quality.subprocess.run", return_value=_proc(0)):
        assert verify_quality.run_step("TestStep", ["echo", "ok"]) is True
        assert verify_quality.run_quality_suite() == 0

    with patch("tools.verify_quality.subprocess.run", return_value=_proc(2)):
        assert verify_quality.run_step("FailStep", ["false"]) is False
        assert verify_quality.run_quality_suite() == 1


def test_run_matrix_cell_and_run_matrix(tmp_path: Path) -> None:
    cell = MatrixCell("M1", "lowest-direct", "disallow", "fewest")

    with patch("tools.verify_quality.subprocess.run", return_value=_proc(1, stderr="venv error")):
        assert verify_quality.run_matrix_cell(cell, "3.11", tmp_path) is False

    with (
        patch(
            "tools.verify_quality.subprocess.run",
            side_effect=[_proc(0), _proc(1, stderr="resolver err")],
        ),
        patch("tools.verify_quality.capture_diagnostics", return_value="DIAG_INSTALL"),
    ):
        assert verify_quality.run_matrix_cell(cell, "3.11", tmp_path) is False

    with (
        patch(
            "tools.verify_quality.subprocess.run",
            side_effect=[_proc(0), _proc(0), _proc(1, stdout="test fail")],
        ),
        patch("tools.verify_quality.capture_diagnostics", return_value="DIAG_PYTEST"),
    ):
        assert verify_quality.run_matrix_cell(cell, "3.11", tmp_path) is False

    with patch("tools.verify_quality.subprocess.run", side_effect=[_proc(0), _proc(0), _proc(0)]):
        assert verify_quality.run_matrix([cell], "3.11", tmp_path) == 0

    with patch("tools.verify_quality.run_matrix_cell", return_value=False):
        assert verify_quality.run_matrix([cell], "3.11", tmp_path) == 1


def test_supported_pythons_and_multi_python_runner(tmp_path: Path) -> None:
    assert load_supported_pythons(tmp_path / "missing.toml") == ()
    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text('[project]\nclassifiers = "not-a-list"\n', encoding="utf-8")
    assert load_supported_pythons(bad_toml) == ()

    good_toml = tmp_path / "pyproject.toml"
    good_toml.write_text(
        "[project]\n"
        "classifiers = [\n"
        '  "Programming Language :: Python :: 3.15",\n'
        '  "Programming Language :: Python :: 3.11",\n'
        '  "Programming Language :: Python :: 3 :: Only",\n'
        "]\n",
        encoding="utf-8",
    )
    assert load_supported_pythons(good_toml) == ("3.11", "3.15")
    assert verify_quality.list_sessions(tmp_path) == 0

    with patch("tools.verify_quality.subprocess.run", return_value=_proc(0)):
        assert verify_quality.is_python_available("3.13") is True

    with patch("tools.verify_quality.subprocess.run", return_value=_proc(1)):
        assert verify_quality.is_python_available("3.99") is False
        assert verify_quality.run_python_session("3.99", tmp_path) == "skipped"

    with (
        patch("tools.verify_quality.is_python_available", return_value=True),
        patch("tools.verify_quality.run_matrix_cell", return_value=True),
    ):
        assert verify_quality.run_python_session("3.11", tmp_path) == "passed"

    with (
        patch("tools.verify_quality.is_python_available", return_value=True),
        patch("tools.verify_quality.run_matrix_cell", return_value=False),
    ):
        assert verify_quality.run_python_session("3.11", tmp_path) == "failed"

    with patch(
        "tools.verify_quality.run_python_session",
        side_effect=["passed", "skipped"],
    ):
        assert verify_quality.run_multi_python(["3.11", "3.15"], tmp_path) == 0

    with patch(
        "tools.verify_quality.run_python_session",
        side_effect=["passed", "failed"],
    ):
        assert verify_quality.run_multi_python(["3.11", "3.15"], tmp_path) == 1

    with patch("tools.verify_quality.run_python_session", return_value="skipped"):
        assert verify_quality.run_multi_python(["3.15"], tmp_path) == 1


def test_verify_quality_main_and_module_entrypoints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with patch("tools.verify_quality.run_quality_suite", return_value=0) as mock_suite:
        assert verify_quality.main([]) == 0
        mock_suite.assert_called_once()

    with patch("tools.verify_quality.list_sessions", return_value=0) as mock_list:
        assert verify_quality.main(["--list"], repo_root=tmp_path) == 0
        mock_list.assert_called_once_with(tmp_path)

    with patch("tools.verify_quality.run_multi_python", return_value=0) as mock_mp:
        assert verify_quality.main(["--all-pythons"], repo_root=tmp_path) == 0
        assert verify_quality.main(["--pythons", "3.11,3.15"], repo_root=tmp_path) == 0
        assert mock_mp.call_count == 2

    with patch("tools.verify_quality.run_matrix", return_value=0) as mock_matrix:
        assert verify_quality.main(["--smoke"], repo_root=tmp_path) == 0
        mock_matrix.assert_called_once()

    monkeypatch.setattr(sys, "argv", ["dep_matrix.py"])
    with (
        patch("subprocess.run", return_value=_proc(0)),
        pytest.raises(SystemExit) as exc_dep,
    ):
        runpy.run_path(str(Path(dep_matrix.__file__)), run_name="__main__")

    assert exc_dep.value.code == 0

    repo_root_str = str(Path(verify_quality.__file__).resolve().parent.parent)
    monkeypatch.setattr(sys, "argv", ["verify_quality.py", "--smoke"])
    monkeypatch.setattr(
        sys,
        "path",
        [p for p in sys.path if Path(p).resolve() != Path(repo_root_str).resolve()],
    )
    monkeypatch.delitem(sys.modules, "tools", raising=False)
    monkeypatch.delitem(sys.modules, "tools.dep_matrix", raising=False)
    with (
        patch("subprocess.run", return_value=_proc(0)),
        pytest.raises(SystemExit) as exc_vq,
    ):
        runpy.run_path(str(Path(verify_quality.__file__)), run_name="__main__")

    assert exc_vq.value.code == 0
