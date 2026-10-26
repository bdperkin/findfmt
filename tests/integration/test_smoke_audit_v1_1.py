"""Final smoke and edge-case audit for v1.1.0 (#496).

End-to-end checks, through the CLI, of the user-visible behavior changes since v1.0.0, and of the
edge cases that must never end in a traceback. ``test_smoke_audit.py`` covers the v1.0.0 audit
(empty trees, unreadable directories, symlink cycles, massive ignored trees).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.entrypoints import main_findfiles

runner = CliRunner()
POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="name is invalid on Windows")


def _run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, [*args, "--no-pager"])
    assert "Traceback" not in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    return result.exit_code, result.output


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Return a small tree with one Python file and one 2 KiB binary file."""
    (tmp_path / "script.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "blob.bin").write_bytes(b"\0" * 2048)
    return tmp_path


def test_exit_status_contract(tree: Path) -> None:
    """--exit-status exits 1 only when nothing matches; without it, no match exits 0 (#367)."""
    assert _run(str(tree), "-t", "python", "--exit-status")[0] == 0
    assert _run(str(tree), "-t", "no-such-tag", "--exit-status")[0] == 1
    assert _run(str(tree), "-t", "no-such-tag")[0] == 0


def test_wrapper_exit_status_and_errors(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Wrapper commands keep the exit-code contract and report errors without tracebacks (#373)."""
    assert main_findfiles([str(tree), "-t", "no-such-tag", "--exit-status"]) == 1
    assert main_findfiles([str(tree), "--sort", "bogus"]) == 2
    assert main_findfiles([str(tree), "--config", str(tree / "missing.toml")]) == 2
    assert "Traceback" not in capsys.readouterr().err


def test_wrapper_honors_config_over_wrapper_defaults(
    tree: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wrapper entry points honor config file overrides while CLI flags still win (#454)."""
    (tree / ".secret").write_text("hidden\n", encoding="utf-8")
    cfg = tree / "findfmt.toml"
    cfg.write_text("hidden = false\n", encoding="utf-8")

    assert main_findfiles(["--config", str(cfg), str(tree)]) == 0
    assert ".secret" not in capsys.readouterr().out

    assert main_findfiles(["--config", str(cfg), "--hidden", str(tree)]) == 0
    assert ".secret" in capsys.readouterr().out


def test_human_readable_sizes_use_iec_labels(tree: Path) -> None:
    """-h prints IEC binary labels, and --si keeps SI metric labels (#352)."""
    assert "[2.0 KiB] blob.bin" in _run(str(tree), "-h", "-l")[1]
    assert "[2.0 kB] blob.bin" in _run(str(tree), "--si", "-l")[1]


@POSIX_ONLY
def test_gitignore_whitespace_matches_git(tmp_path: Path) -> None:
    """Leading whitespace is significant and an escaped trailing space is kept, as in git (#354)."""
    names = (" lead.txt", "lead.txt", "trail.txt ", "trail.txt", "plain.txt")
    for name in names:
        (tmp_path / name).write_text("x", encoding="utf-8")

    (tmp_path / ".gitignore").write_text(" lead.txt\ntrail.txt\\ \n", encoding="utf-8")
    ignored = {" lead.txt", "trail.txt "}

    listed = set(_run(str(tmp_path), "-P", "*.txt*")[1].splitlines())
    assert {Path(line).name for line in listed} == set(names) - ignored

    git = shutil.which("git")
    if git is not None:
        subprocess.run([git, "init", "-q", str(tmp_path)], check=True)
        check = subprocess.run(
            [git, "-C", str(tmp_path), "check-ignore", "--stdin"],
            input="\n".join(names),
            capture_output=True,
            text=True,
            check=False,
        )
        assert set(check.stdout.splitlines()) == ignored


def test_from_file_sorts_by_ctime(tmp_path: Path) -> None:
    """--from-file entries sort by status-change time for --sort ctime, not by mtime (#462)."""
    paths = []
    for index, name in enumerate(("first.txt", "second.txt", "third.txt")):
        path = tmp_path / name
        path.write_text("x", encoding="utf-8")
        os.utime(path, (1_000_000 - index, 1_000_000 - index))  # mtime runs backwards
        paths.append(path)
        time.sleep(0.05)

    ctimes = [path.stat().st_ctime for path in paths]
    if len(set(ctimes)) != len(ctimes):
        pytest.skip("filesystem ctime resolution too coarse")

    listing = tmp_path / "list.txt"
    listing.write_text("\n".join(str(p) for p in reversed(paths)), encoding="utf-8")
    by_ctime = _run("--from-file", str(listing), "--sort", "ctime")[1].splitlines()
    by_mtime = _run("--from-file", str(listing), "--sort", "time")[1].splitlines()
    # Newest first, as with `ls -t`.
    assert [Path(line).name for line in by_ctime] == ["third.txt", "second.txt", "first.txt"]
    assert [Path(line).name for line in by_mtime] == ["first.txt", "second.txt", "third.txt"]


@POSIX_ONLY
def test_ipynb_manifest_cell_executes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The -f ipynb manifest cell runs, even for names with quotes and backslashes (#330)."""
    tricky = 'tri"""ple \\ back.txt'
    (tmp_path / tricky).write_text("x", encoding="utf-8")
    notebook = json.loads(_run(str(tmp_path), "-f", "ipynb")[1])
    code = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]
    for source in code:
        compile(source, "<cell>", "exec")

    # Run the manifest cell against a stand-in for pandas, which is not a test dependency.
    pandas = types.ModuleType("pandas")
    vars(pandas)["DataFrame"] = lambda rows: types.SimpleNamespace(head=lambda: rows)
    monkeypatch.setitem(sys.modules, "pandas", pandas)
    namespace: dict[str, Any] = {}
    exec(code[0], namespace)
    assert [row["relative_path"] for row in namespace["FILES"]] == [tricky]


@pytest.mark.parametrize("fmt", ["text", "json", "table", "tree"])
def test_missing_paths_never_traceback(tmp_path: Path, fmt: str) -> None:
    """A missing path ends without a traceback in every format (exit code: #320)."""
    _run(str(tmp_path / "missing"), "-f", fmt)
    _run(str(tmp_path / "missing"), "--from-file", str(tmp_path / "missing.txt"), "-f", fmt)
