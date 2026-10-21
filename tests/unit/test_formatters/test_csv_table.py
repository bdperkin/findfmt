"""Unit tests for CsvTableFormatter and NDJSON output formatting."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.formatters import (
    FORMULA_TRIGGER_CHARS,
    CsvTableFormatter,
    JsonlFormatter,
    OutputFormat,
    get_formatter,
    sanitize_csv_cell,
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


@pytest.mark.parametrize("trigger", ["=", "+", "-", "@", "\t", "\r"])
@pytest.mark.parametrize("fmt_name", ["csv", "tsv"])
def test_csv_safe_prefixes_formula_triggers(trigger: str, fmt_name: str) -> None:
    """Verify formula injection triggers are prefixed with ' only when --csv-safe is enabled."""
    filename = f"{trigger}danger.txt"
    file_info = FileInfo(
        path=Path(filename),
        relative_path=Path(filename),
        tags=frozenset({"text"}),
        shebang=None,
        mime_type="text/plain",
        is_executable=False,
        is_symlink=False,
        size_bytes=42,
    )

    fmt_unsafe = get_formatter(fmt_name, csv_safe=False)
    out_unsafe = fmt_unsafe.format([file_info])

    fmt_safe = get_formatter(fmt_name, csv_safe=True)
    out_safe = fmt_safe.format([file_info])

    if fmt_name == "csv":
        rows_unsafe = list(csv.reader(io.StringIO(out_unsafe)))
        rows_safe = list(csv.reader(io.StringIO(out_safe)))
        assert len(rows_unsafe) == 2
        assert len(rows_safe) == 2
        assert not rows_unsafe[1][0].startswith("'")
        assert rows_unsafe[1][0] == filename
        assert rows_safe[1][0].startswith("'")
        assert rows_safe[1][0] == f"'{filename}"
        assert rows_safe[1][1] == f"'{filename}"
    else:
        lines_unsafe = out_unsafe.splitlines()
        lines_safe = out_safe.splitlines()
        assert len(lines_unsafe) == 2
        assert len(lines_safe) == 2
        cells_unsafe = lines_unsafe[1].split("\t")
        cells_safe = lines_safe[1].split("\t")
        assert not cells_unsafe[0].startswith("'")
        assert cells_safe[0].startswith("'")
        assert cells_safe[1].startswith("'")


def test_csv_safe_round_trip_with_csv_reader() -> None:
    """Verify csv.reader round-trip preserves clean data and alters only formula triggers."""
    triggers = ["=", "+", "-", "@", "\t", "\r"]
    files = [
        FileInfo(
            path=Path("normal.txt"),
            relative_path=Path("normal.txt"),
            tags=frozenset({"text"}),
            shebang=None,
            mime_type="text/plain",
            is_executable=False,
            is_symlink=False,
            size_bytes=100,
        ),
        *(
            FileInfo(
                path=Path(f"{char}payload.csv"),
                relative_path=Path(f"{char}payload.csv"),
                tags=frozenset({"text"}),
                shebang=None,
                mime_type="text/plain",
                is_executable=False,
                is_symlink=False,
                size_bytes=200,
            )
            for char in triggers
        ),
    ]

    fmt_unsafe = get_formatter("csv", csv_safe=False)
    fmt_safe = get_formatter("csv", csv_safe=True)

    rows_unsafe = list(csv.reader(io.StringIO(fmt_unsafe.format(files))))
    rows_safe = list(csv.reader(io.StringIO(fmt_safe.format(files))))

    assert len(rows_unsafe) == len(rows_safe) == len(files) + 1
    assert rows_unsafe[0] == rows_safe[0]

    for r_unsafe, r_safe in zip(rows_unsafe[1:], rows_safe[1:], strict=True):
        assert len(r_unsafe) == len(r_safe)
        for u_cell, s_cell in zip(r_unsafe, r_safe, strict=True):
            if u_cell.startswith(("=", "+", "-", "@", "\t", "\r")):
                assert s_cell == f"'{u_cell}"
            else:
                assert s_cell == u_cell


def test_sanitize_csv_cell_behavior() -> None:
    """Verify sanitize_csv_cell prefixes formula triggers and leaves clean cells intact."""
    assert sanitize_csv_cell("") == ""
    assert sanitize_csv_cell("clean_file.txt") == "clean_file.txt"
    assert sanitize_csv_cell("12345") == "12345"

    for char in FORMULA_TRIGGER_CHARS:
        cell_val = f"{char}dangerous"
        assert sanitize_csv_cell(cell_val) == f"'{cell_val}"


def test_csv_table_formatter_csv_safe() -> None:
    """Verify CsvTableFormatter applies formula neutralization when csv_safe=True."""
    dangerous_file = FileInfo(
        path=Path("=calc.bat"),
        relative_path=Path("=calc.bat"),
        tags=frozenset({"script"}),
        shebang=None,
        mime_type="application/x-bat",
        is_executable=True,
        is_symlink=False,
        size_bytes=50,
    )
    fmt_unsafe = CsvTableFormatter(csv_safe=False)
    out_unsafe = fmt_unsafe.format([dangerous_file])
    assert "'=calc.bat" not in out_unsafe
    assert "=calc.bat" in out_unsafe

    fmt_safe = CsvTableFormatter(csv_safe=True)
    out_safe = fmt_safe.format([dangerous_file])
    assert "'=calc.bat" in out_safe


def test_cli_csv_safe_flag(tmp_path: Path) -> None:
    """Verify CLI --csv-safe flag enables formula injection sanitization in CSV output."""
    runner = CliRunner()
    bad_file = tmp_path / "=evil.csv"
    bad_file.write_text("dummy", encoding="utf-8")

    res_unsafe = runner.invoke(app, ["--format", "csv", "--no-csv-safe", str(tmp_path)])
    assert res_unsafe.exit_code == 0
    assert "=evil.csv" in res_unsafe.stdout
    assert "'=evil.csv" not in res_unsafe.stdout

    res_safe = runner.invoke(app, ["--format", "csv", "--csv-safe", str(tmp_path)])
    assert res_safe.exit_code == 0
    assert "'=evil.csv" in res_safe.stdout
