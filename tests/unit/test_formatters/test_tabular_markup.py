"""Unit tests for delimited (CSV, TSV) and markup (Markdown, RST) formatters."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import docutils.core
import pytest
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.formatters import (
    CsvFormatter,
    MarkdownFormatter,
    OutputFormat,
    RstFormatter,
    TsvFormatter,
    get_formatter,
)
from findfmt.formatters.base import TABLE_FIELD_NAMES
from findfmt.formatters.delimited import escape_tsv_cell, file_to_record
from findfmt.formatters.markup import (
    UnsupportedTableStyleError,
    escape_markdown_cell,
    escape_rst_cell,
)
from findfmt.models import FileInfo


@pytest.fixture
def sample_files() -> list[FileInfo]:
    """Provide a consistent list of classified test files."""
    return [
        FileInfo(
            path=Path("/workspace/project/src/main.py"),
            relative_path=Path("src/main.py"),
            tags=frozenset({"python", "text"}),
            shebang="#!/usr/bin/env python3",
            mime_type="text/x-python",
            is_executable=True,
            is_symlink=False,
            size_bytes=1024,
        ),
        FileInfo(
            path=Path("/workspace/project/docs/guide.md"),
            relative_path=Path("docs/guide.md"),
            tags=frozenset({"markdown"}),
            shebang=None,
            mime_type=None,
            is_executable=False,
            is_symlink=True,
            size_bytes=256,
        ),
    ]


@pytest.fixture
def special_file() -> FileInfo:
    """Provide a file with quotes, pipes, commas, and newlines."""
    return FileInfo(
        path=Path('/workspace/special|path,with\ttab\nand"quotes.sh'),
        relative_path=Path('special|path,with\ttab\nand"quotes.sh'),
        tags=frozenset({"shell"}),
        shebang="#!/bin/sh",
        mime_type="text/x-shellscript",
        is_executable=True,
        is_symlink=False,
        size_bytes=42,
    )


def test_file_to_record_relative_and_absolute(sample_files: list[FileInfo]) -> None:
    """Verify file_to_record respects absolute and relative path flags."""
    rel_record = file_to_record(sample_files[0], absolute=False)
    assert rel_record[0] == "src/main.py"
    assert rel_record[1] == "src/main.py"
    assert rel_record[2] == "python, text"
    assert rel_record[3] == "text/x-python"
    assert rel_record[4] == "#!/usr/bin/env python3"
    assert rel_record[5] == "true"
    assert rel_record[6] == "false"
    assert rel_record[7] == "1024"

    abs_record = file_to_record(sample_files[0], absolute=True)
    assert abs_record[0] == str(sample_files[0].path)


def test_escape_helpers() -> None:
    """Verify cell escaping functions for TSV, Markdown, and RST."""
    raw = 'pipe|slash\\tab\tnewline\rcarriage\nquote"'
    assert escape_tsv_cell(raw) == 'pipe|slash\\\\tab\\tnewline\\rcarriage\\nquote"'
    assert escape_markdown_cell(raw) == 'pipe\\|slash\\\\tab newline carriage quote"'
    assert escape_rst_cell(raw) == 'pipe\\|slash\\tab newline carriage quote"'


def test_csv_formatter(sample_files: list[FileInfo], special_file: FileInfo) -> None:
    """Verify CsvFormatter produces valid RFC 4180 CSV with headers and escaping."""
    formatter = CsvFormatter(absolute=False)
    output = formatter.format([*sample_files, special_file])

    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 4
    assert tuple(reader[0]) == TABLE_FIELD_NAMES
    assert reader[1][0] == "src/main.py"
    assert reader[1][2] == "python, text"
    assert reader[2][3] == ""  # None mime_type becomes empty string

    # Check that special file path preserves embedded quotes, commas, and newlines
    assert reader[3][0] == 'special|path,with\ttab\nand"quotes.sh'

    # Test streaming
    buf = io.StringIO()
    formatter.stream(sample_files, buf)
    assert buf.getvalue() == formatter.format(sample_files)


def test_csv_formatter_empty() -> None:
    """Verify CsvFormatter emits header row for empty input."""
    output = CsvFormatter().format([])
    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 1
    assert tuple(reader[0]) == TABLE_FIELD_NAMES


def test_tsv_formatter(sample_files: list[FileInfo], special_file: FileInfo) -> None:
    """Verify TsvFormatter produces single-line records with escaped delimiters."""
    formatter = TsvFormatter(absolute=False)
    output = formatter.format([*sample_files, special_file])

    lines = output.strip().split("\n")
    assert len(lines) == 4
    header_fields = lines[0].split("\t")
    assert tuple(header_fields) == TABLE_FIELD_NAMES

    # Ensure special file with newlines is escaped so each record is one line
    special_fields = lines[3].split("\t")
    assert len(special_fields) == len(TABLE_FIELD_NAMES)
    assert "\\n" in special_fields[0]
    assert "\\t" in special_fields[0]

    # Test streaming
    buf = io.StringIO()
    formatter.stream(sample_files, buf)
    assert buf.getvalue() == formatter.format(sample_files)


def test_tsv_formatter_empty() -> None:
    """Verify TsvFormatter emits header row for empty input."""
    output = TsvFormatter().format([])
    assert output == "\t".join(TABLE_FIELD_NAMES) + "\n"


def test_markdown_formatter(sample_files: list[FileInfo], special_file: FileInfo) -> None:
    """Verify MarkdownFormatter outputs aligned GFM tables with pipe escaping."""
    formatter = MarkdownFormatter(absolute=False)
    output = formatter.format([*sample_files, special_file])

    lines = output.strip().split("\n")
    assert len(lines) == 5  # header, separator, 3 rows
    assert lines[0].startswith("| ")
    assert lines[0].endswith(" |")

    sep_cells = [c.strip() for c in lines[1].split("|")[1:-1]]
    assert sep_cells[0].startswith(":")
    assert sep_cells[5].startswith(":")
    assert sep_cells[5].endswith(":")
    assert sep_cells[7].endswith(":")
    assert not sep_cells[7].startswith(":")

    # Pipe in special file must be escaped
    assert "\\|" in lines[4]

    # Test streaming
    buf = io.StringIO()
    formatter.stream(sample_files, buf)
    assert buf.getvalue() == formatter.format(sample_files)


def test_markdown_formatter_empty() -> None:
    """Verify MarkdownFormatter renders valid empty table with headers."""
    output = MarkdownFormatter().format([])
    lines = output.strip().split("\n")
    assert len(lines) == 2


def test_rst_formatter_grid(sample_files: list[FileInfo], special_file: FileInfo) -> None:
    """Verify RstFormatter generates docutils-valid grid table."""
    formatter = RstFormatter(absolute=False, table_style="grid")
    output = formatter.format([*sample_files, special_file])

    assert "+---" in output
    assert "+===" in output
    assert "\\|" in output

    # Validate docutils can parse the output into HTML without errors
    html = docutils.core.publish_string(output, writer="html")
    assert b"<table" in html

    # Test streaming
    buf = io.StringIO()
    formatter.stream(sample_files, buf)
    assert buf.getvalue() == formatter.format(sample_files)


def test_rst_formatter_simple(sample_files: list[FileInfo]) -> None:
    """Verify RstFormatter generates docutils-valid simple table."""
    formatter = RstFormatter(absolute=False, table_style="simple")
    output = formatter.format(sample_files)

    assert "=" in output
    html = docutils.core.publish_string(output, writer="html")
    assert b"<table" in html


def test_rst_formatter_empty() -> None:
    """Verify RstFormatter handles empty file collections."""
    grid_output = RstFormatter(table_style="grid").format([])
    assert "+===" in grid_output
    docutils.core.publish_string(grid_output, writer="html")

    simple_output = RstFormatter(table_style="simple").format([])
    assert "=" in simple_output
    docutils.core.publish_string(simple_output, writer="html")


def test_rst_formatter_invalid_style() -> None:
    """Verify RstFormatter raises ValueError for unsupported table styles."""
    with pytest.raises(UnsupportedTableStyleError, match="Unsupported RST table style: 'fancy'"):
        RstFormatter(table_style="fancy")


def test_get_formatter_tabular_and_markup() -> None:
    """Verify get_formatter instantiates CSV, TSV, Markdown, and RST formatters."""
    csv_fmt = get_formatter(OutputFormat.CSV, delimiter=";", quoting=csv.QUOTE_ALL)
    assert isinstance(csv_fmt, CsvFormatter)
    assert csv_fmt.delimiter == ";"
    assert csv_fmt.quoting == csv.QUOTE_ALL

    tsv_fmt = get_formatter(OutputFormat.TSV)
    assert isinstance(tsv_fmt, TsvFormatter)

    md_fmt = get_formatter(OutputFormat.MARKDOWN)
    assert isinstance(md_fmt, MarkdownFormatter)

    md_alias_fmt = get_formatter(OutputFormat.MD)
    assert isinstance(md_alias_fmt, MarkdownFormatter)

    md_str_fmt = get_formatter("md")
    assert isinstance(md_str_fmt, MarkdownFormatter)

    rst_fmt = get_formatter(OutputFormat.RST, table_style="simple")
    assert isinstance(rst_fmt, RstFormatter)
    assert rst_fmt.table_style == "simple"


def test_cli_tabular_and_markup_formats(sample_repo: Path) -> None:
    """Verify CLI runs with --format csv, tsv, markdown, md, and rst."""
    runner = CliRunner()

    res_csv = runner.invoke(app, ["--format", "csv", str(sample_repo)])
    assert res_csv.exit_code == 0
    assert "path,relative_path" in res_csv.stdout

    res_tsv = runner.invoke(app, ["-f", "tsv", str(sample_repo)])
    assert res_tsv.exit_code == 0
    assert "path\trelative_path" in res_tsv.stdout

    res_md = runner.invoke(app, ["--format", "markdown", str(sample_repo)])
    assert res_md.exit_code == 0
    assert "| path " in res_md.stdout

    res_md_alias = runner.invoke(app, ["-f", "md", str(sample_repo)])
    assert res_md_alias.exit_code == 0
    assert "| path " in res_md_alias.stdout

    res_rst = runner.invoke(app, ["--format", "rst", str(sample_repo)])
    assert res_rst.exit_code == 0
    assert "+---" in res_rst.stdout
