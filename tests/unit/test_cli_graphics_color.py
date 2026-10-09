"""Unit tests for CLI graphics, indentation, and colorization options."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from findfmt.cli import app

if TYPE_CHECKING:
    from pathlib import Path


def _make_dummy_tree(tmp_path: Path) -> Path:
    """Create a structured test directory with multiple files."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "root.py").write_text("print('root')\n")
    sub = repo / "pkg"
    sub.mkdir()
    (sub / "mod.py").write_text("x = 1\n")
    return repo


def test_cli_no_indent_tree(tmp_path: Path) -> None:
    """Verify -i and --no-indent omit branch characters in tree view."""
    repo = _make_dummy_tree(tmp_path)
    runner = CliRunner()

    res = runner.invoke(app, ["--tree", "-i", str(repo)])
    assert res.exit_code == 0
    assert "├──" not in res.stdout
    assert "└──" not in res.stdout
    assert "root.py" in res.stdout
    assert "mod.py" in res.stdout

    res_long = runner.invoke(app, ["--format", "tree", "--no-indent", str(repo)])
    assert res_long.exit_code == 0
    assert "├──" not in res_long.stdout
    assert "└──" not in res_long.stdout


def test_cli_no_indent_structured_formats(tmp_path: Path) -> None:
    """Verify -i produces compact machine output in json, yaml, and markdown."""
    repo = _make_dummy_tree(tmp_path)
    runner = CliRunner()

    # JSON compact
    res_json = runner.invoke(app, ["--format", "json", "-i", str(repo)])
    assert res_json.exit_code == 0
    data = json.loads(res_json.stdout)
    assert len(data) == 2
    assert "\n" not in res_json.stdout.strip()

    # YAML compact
    res_yaml = runner.invoke(app, ["--format", "yaml", "--no-indent", str(repo)])
    assert res_yaml.exit_code == 0
    assert "root.py" in res_yaml.stdout

    # Markdown compact (unpadded cells)
    res_md = runner.invoke(app, ["--format", "markdown", "-i", str(repo)])
    assert res_md.exit_code == 0
    assert "|path|relative_path|tags|mime_type|shebang|is_executable|is_symlink|size_bytes|" in (
        res_md.stdout
    )


def test_cli_ansi_lines_tree(tmp_path: Path) -> None:
    """Verify -A and --ansi-lines use VT100 escape sequences in tree view."""
    repo = _make_dummy_tree(tmp_path)
    runner = CliRunner()

    res = runner.invoke(app, ["--tree", "-A", str(repo)])
    assert res.exit_code == 0
    assert "\x1b(0" in res.stdout
    assert "root.py" in res.stdout


def test_cli_cp437_tree(tmp_path: Path) -> None:
    """Verify -S and --cp437 use IBM-PC console box characters in tree view."""
    repo = _make_dummy_tree(tmp_path)
    runner = CliRunner()

    res = runner.invoke(app, ["--tree", "-S", str(repo)])
    assert res.exit_code == 0
    assert "\xc3\xc4\xc4" in res.stdout or "\xc0\xc4\xc4" in res.stdout
    assert "root.py" in res.stdout


def test_cli_color_force_option(tmp_path: Path) -> None:
    """Verify -C and --color force ANSI color escapes even in non-TTY buffers."""
    repo = _make_dummy_tree(tmp_path)
    runner = CliRunner()

    res = runner.invoke(app, ["--tree", "-C", str(repo)], env={"NO_COLOR": "1"})
    assert res.exit_code == 0
    assert "\x1b[" in res.stdout


def test_cli_no_color_option(tmp_path: Path) -> None:
    """Verify -n and --no-color strip ANSI escapes even when CLICOLOR_FORCE=1."""
    repo = _make_dummy_tree(tmp_path)
    runner = CliRunner()

    res = runner.invoke(app, ["--tree", "-n", str(repo)], env={"CLICOLOR_FORCE": "1"})
    assert res.exit_code == 0
    assert "\x1b[" not in res.stdout
    assert "root.py" in res.stdout


def test_cli_full_path_alias(tmp_path: Path) -> None:
    """Verify --full-path acts as alias for --absolute."""
    repo = _make_dummy_tree(tmp_path)
    runner = CliRunner()

    res = runner.invoke(app, ["--full-path", str(repo)])
    assert res.exit_code == 0
    assert str(repo.resolve()) in res.stdout


def test_cli_summary_with_color_flags(tmp_path: Path) -> None:
    """Verify summary panel honors -n and -C color flags."""
    repo = _make_dummy_tree(tmp_path)
    runner = CliRunner()

    res_off = runner.invoke(app, ["-s", "-n", str(repo)])
    assert res_off.exit_code == 0
    assert "findfmt summary" in res_off.stderr

    res_on = runner.invoke(app, ["-s", "-C", str(repo)])
    assert res_on.exit_code == 0
    assert "findfmt summary" in res_on.stderr
