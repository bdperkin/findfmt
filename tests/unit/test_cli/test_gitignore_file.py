"""Unit tests for findfmt CLI --gitignore-file option."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from findfmt.cli import app


def test_cli_gitignore_file_option(tmp_path: Path) -> None:
    """Verify findfmt --gitignore-file on CLI."""
    runner = CliRunner()
    ignore_file = tmp_path / "my.ignore"
    ignore_file.write_text("*.hidden_ext\n", encoding="utf-8")

    file_a = tmp_path / "a.txt"
    file_a.write_text("a", encoding="utf-8")
    file_b = tmp_path / "b.hidden_ext"
    file_b.write_text("b", encoding="utf-8")

    result = runner.invoke(
        app,
        [str(tmp_path), "--gitignore-file", str(ignore_file)],
    )
    assert result.exit_code == 0
    assert "a.txt" in result.stdout
    assert "b.hidden_ext" not in result.stdout

    # Non-existent gitignore file raises error with exit code 2
    bad_result = runner.invoke(
        app,
        [str(tmp_path), "--gitignore-file", str(tmp_path / "missing.ignore")],
    )
    assert bad_result.exit_code == 2
    assert "not found" in bad_result.stderr
