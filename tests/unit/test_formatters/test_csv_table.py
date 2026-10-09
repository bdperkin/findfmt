"""Unit tests for CsvTableFormatter and NDJSON output formatting."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.formatters import (
    CsvTableFormatter,
    JsonlFormatter,
    OutputFormat,
    get_formatter,
)
from findfmt.formatters.base import TABLE_FIELD_NAMES
from findfmt.formatters.visual import UnsupportedBoxStyleError
from findfmt.models import FileInfo


@pytest.fixture
def sample_files() -> list[FileInfo]:
    """Provide sample FileInfo objects for CSV table testing."""
    return [
        FileInfo(
            path=Path("/workspace/project/main.py"),
            relative_path=Path("main.py"),
            tags=frozenset({"python", "text"}),
            shebang="#!/usr/bin/env python3",
            mime_type="text/x-python",
            is_executable=True,
            is_symlink=False,
            size_bytes=1024,
        ),
        FileInfo(
            path=Path("/workspace/project/data.json"),
            relative_path=Path("data.json"),
            tags=frozenset({"json", "text"}),
            shebang=None,
            mime_type="application/json",
            is_executable=False,
            is_symlink=True,
            size_bytes=256,
        ),
    ]


def test_csv_table_formatter_rendering(sample_files: list[FileInfo]) -> None:
    """Verify CsvTableFormatter outputs aligned table with CSV schema columns."""
    formatter = CsvTableFormatter(absolute=False, table_style="rounded")
    output = formatter.format(sample_files)

    assert "findfmt CSV Table" in output
    for col_name in TABLE_FIELD_NAMES:
        assert col_name in output

    assert "main.py" in output
    assert "data.json" in output
    assert "text/x-python" in output
    assert "1024" in output


def test_csv_table_formatter_stream(sample_files: list[FileInfo]) -> None:
    """Verify CsvTableFormatter stream output matches formatted output."""
    formatter = CsvTableFormatter(absolute=False, console_width=120)
    buf = io.StringIO()
    formatter.stream(sample_files, buf)
    assert buf.getvalue() == formatter.format(sample_files)

    formatter_default = CsvTableFormatter(absolute=False)
    buf_default = io.StringIO()
    formatter_default.stream(sample_files, buf_default)
    assert "main.py" in buf_default.getvalue()


def test_csv_table_formatter_empty() -> None:
    """Verify CsvTableFormatter renders table header for empty file input."""
    formatter = CsvTableFormatter()
    output = formatter.format([])
    assert "findfmt CSV Table" in output
    assert "relative_path" in output


def test_csv_table_formatter_absolute(sample_files: list[FileInfo]) -> None:
    """Verify CsvTableFormatter respects absolute path flag."""
    formatter = CsvTableFormatter(absolute=True, table_style="ascii")
    output = formatter.format(sample_files)
    assert str(sample_files[0].path) in output
    assert "+" in output


def test_csv_table_formatter_invalid_style() -> None:
    """Verify CsvTableFormatter raises UnsupportedBoxStyleError for unknown style."""
    with pytest.raises(UnsupportedBoxStyleError, match="Unsupported table style: 'unknown'"):
        CsvTableFormatter(table_style="unknown")


def test_csv_table_formatter_color_options(sample_files: list[FileInfo]) -> None:
    """Verify CsvTableFormatter respects explicit force_color flag."""
    fmt_no_color = CsvTableFormatter(force_color=False)
    out_no_color = fmt_no_color.format(sample_files)
    assert "\x1b[" not in out_no_color

    fmt_color = CsvTableFormatter(force_color=True)
    out_color = fmt_color.format(sample_files)
    assert "findfmt CSV Table" in out_color


def test_get_formatter_csv_table_options() -> None:
    """Verify get_formatter passes options to CsvTableFormatter."""
    fmt = get_formatter(
        OutputFormat.CSV_TABLE,
        table_style="minimal",
        absolute=True,
        force_color=False,
    )
    assert isinstance(fmt, CsvTableFormatter)
    assert fmt.table_style == "minimal"
    assert fmt.absolute is True
    assert fmt.force_color is False

    ndjson_fmt = get_formatter(OutputFormat.NDJSON, absolute=True)
    assert isinstance(ndjson_fmt, JsonlFormatter)
    assert ndjson_fmt.absolute is True


def test_cli_csv_table_and_ndjson(sample_repo: Path) -> None:
    """Verify CLI accepts --format csv-table and --format ndjson."""
    runner = CliRunner()

    res_csv_table = runner.invoke(app, ["--format", "csv-table", str(sample_repo)])
    assert res_csv_table.exit_code == 0
    assert "findfmt CSV Table" in res_csv_table.stdout

    res_ndjson = runner.invoke(app, ["-f", "ndjson", str(sample_repo)])
    assert res_ndjson.exit_code == 0
    assert '"relative_path"' in res_ndjson.stdout
