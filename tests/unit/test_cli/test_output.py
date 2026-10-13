"""Unit tests for findfmt CLI output file redirection (-o / --output)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from findfmt.cli import app


def test_cli_output_redirection_text(tmp_path: Path) -> None:
    """Verify -o redirects plain text file list to destination file."""
    runner = CliRunner()
    file_1 = tmp_path / "file1.txt"
    file_1.write_text("hello", encoding="utf-8")
    out_file = tmp_path / "out.txt"

    result = runner.invoke(app, [str(tmp_path), "-o", str(out_file)])
    assert result.exit_code == 0
    assert result.stdout == ""
    assert out_file.is_file()
    content = out_file.read_text(encoding="utf-8")
    assert "file1.txt" in content


def test_cli_output_redirection_json(tmp_path: Path) -> None:
    """Verify --output with --format json produces valid JSON in the output file."""
    runner = CliRunner()
    (tmp_path / "script.py").write_text("print('hi')", encoding="utf-8")
    out_file = tmp_path / "results.json"

    result = runner.invoke(
        app,
        [str(tmp_path), "--format", "json", "--output", str(out_file)],
    )
    assert result.exit_code == 0
    assert result.stdout == ""
    assert out_file.is_file()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert any("script.py" in item["path"] for item in data)


def test_cli_output_redirection_with_summary(tmp_path: Path) -> None:
    """Verify -o sends formatted output to file and -s sends summary to stderr."""
    runner = CliRunner()
    (tmp_path / "test.py").write_text("import os", encoding="utf-8")
    out_file = tmp_path / "out_summary.txt"

    result = runner.invoke(app, [str(tmp_path), "-o", str(out_file), "-s"])
    assert result.exit_code == 0
    assert out_file.is_file()
    assert "test.py" in out_file.read_text(encoding="utf-8")
    assert "Matched files:" in result.stderr


def test_cli_output_redirection_error(tmp_path: Path) -> None:
    """Verify error handling when output file cannot be opened."""
    runner = CliRunner()
    # Path inside a non-existent directory
    invalid_out = tmp_path / "nonexistent_dir" / "out.txt"

    result = runner.invoke(app, [str(tmp_path), "-o", str(invalid_out)])
    assert result.exit_code == 1
    assert "Error opening output file" in result.stderr
