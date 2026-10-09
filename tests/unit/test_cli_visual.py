"""CLI integration tests for Rich visual formatting (--format table, --tree, --table-style)."""

from __future__ import annotations

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
