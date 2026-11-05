"""CLI integration tests for Rich visual formatting (--format table, --tree, --table-style)."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from findfmt.cli import app

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_format_table(sample_repo: Path) -> None:
    """Verify --format table renders styled table output."""
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "table", str(sample_repo)])
    assert res.exit_code == 0
    assert "findfmt Files" in res.stdout
    assert "app.py" in res.stdout


def test_cli_format_table_with_table_style(sample_repo: Path) -> None:
    """Verify --table-style alters border output."""
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "table", "--table-style", "ascii", str(sample_repo)])
    assert res.exit_code == 0
    assert "findfmt Files" in res.stdout
    assert "+" in res.stdout


def test_cli_format_tree(sample_repo: Path) -> None:
    """Verify --format tree renders hierarchical directory tree output."""
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "tree", str(sample_repo)])
    assert res.exit_code == 0
    assert "src" in res.stdout
    assert "app.py" in res.stdout


def test_cli_tree_flag(sample_repo: Path) -> None:
    """Verify --tree flag activates hierarchical directory tree output."""
    runner = CliRunner()
    res = runner.invoke(app, ["--tree", str(sample_repo)])
    assert res.exit_code == 0
    assert "src" in res.stdout
    assert "app.py" in res.stdout


def test_cli_tree_with_summary(sample_repo: Path) -> None:
    """Verify tree format works cleanly alongside --summary."""
    runner = CliRunner()
    res = runner.invoke(app, ["--tree", "--summary", str(sample_repo)])
    assert res.exit_code == 0
    assert "app.py" in res.stdout
    assert "--- findfmt summary ---" in res.stderr
    assert "Matched files:" in res.stderr


def test_cli_table_with_summary(sample_repo: Path) -> None:
    """Verify table format works cleanly alongside --summary."""
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "table", "--summary", str(sample_repo)])
    assert res.exit_code == 0
    assert "findfmt Files" in res.stdout
    assert "--- findfmt summary ---" in res.stderr


def test_tree_cp437_output_bytes(sample_repo: Path) -> None:
    """Verify subprocess findfmt --tree --cp437 emits valid CP437 box bytes without mojibake."""
    proc = subprocess.run(
        [sys.executable, "-m", "findfmt", "--tree", "--cp437", str(sample_repo)],
        capture_output=True,
        check=True,
    )
    decoded = proc.stdout.decode("cp437")
    assert "├──" in decoded or "└──" in decoded
    assert "Ã" not in decoded
    assert "Ä" not in decoded
    assert b"\xc3\xc4\xc4" in proc.stdout or b"\xc0\xc4\xc4" in proc.stdout


def test_table_cp437_output_bytes(sample_repo: Path) -> None:
    """Verify --format table with --cp437 emits CP437 box-drawing bytes."""
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "table", "--cp437", str(sample_repo)])
    assert res.exit_code == 0
    decoded = res.stdout_bytes.decode("cp437")
    assert "┌" in decoded
    assert "─" in decoded
    assert "Ã" not in decoded
    assert "Ä" not in decoded
