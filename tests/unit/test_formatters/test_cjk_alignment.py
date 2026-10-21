"""Unit and regression tests for CJK double-width character cell alignment across formatters."""

from __future__ import annotations

import io
import pathlib

import pytest
from rich.cells import cell_len

from findfmt.formatters.delimited import (
    CsvFormatter,
    CsvTableFormatter,
    TsvFormatter,
    escape_tsv_cell,
)
from findfmt.formatters.markup import MarkdownFormatter, RstFormatter
from findfmt.formatters.text import TextFormatter
from findfmt.formatters.tree import RichTreeFormatter
from findfmt.formatters.visual import RichTableFormatter
from findfmt.models import FileInfo
from findfmt.utils.strings import cell_width, pad_to_cell_width


@pytest.fixture
def cjk_file_sample() -> list[FileInfo]:
    """Provide a diverse sample of FileInfo records containing CJK and full-width text."""
    return [
        FileInfo(
            path=pathlib.Path("日本語/テスト.py"),
            relative_path=pathlib.Path("日本語/テスト.py"),
            tags=frozenset(["パイソン", "スクリプト"]),
            mime_type="text/x-python",
            size_bytes=1024,
            is_executable=True,
            shebang="#!/usr/bin/env python3",
        ),
        FileInfo(
            path=pathlib.Path("中文目录/数据_报告.json"),
            relative_path=pathlib.Path("中文目录/数据_报告.json"),
            tags=frozenset(["配置", "数据"]),
            mime_type="application/json",
            size_bytes=2048,
            is_executable=False,
        ),
        FileInfo(
            path=pathlib.Path("繁體目錄/檔案_備份.txt"),
            relative_path=pathlib.Path("繁體目錄/檔案_備份.txt"),
            tags=frozenset(["文件"]),
            mime_type="text/plain",
            size_bytes=4096,
            is_executable=False,
            is_symlink=True,
        ),
        FileInfo(
            path=pathlib.Path("한국어/문서_프로젝트.md"),
            relative_path=pathlib.Path("한국어/문서_프로젝트.md"),
            tags=frozenset(["마크다운"]),
            mime_type="text/markdown",
            size_bytes=8192,
            is_executable=False,
        ),
        FileInfo(
            path=pathlib.Path("mixed_混合/ascii_and_全角.txt"),
            relative_path=pathlib.Path("mixed_混合/ascii_and_全角.txt"),
            tags=frozenset(["text"]),
            mime_type="text/plain",
            size_bytes=512,
            is_executable=False,
        ),
    ]


# ---------------------------------------------------------------------------
# Utility function tests: cell_width & pad_to_cell_width
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_text", "expected_width"),
    [
        ("", 0),
        ("hello", 5),
        ("日本語", 6),
        ("中文", 4),
        ("한국어", 6),
        ("全角：１２３", 12),  # noqa: RUF001
        ("\x1b[31mhello\x1b[0m", 5),
        ("\x1b[1;34m日本語\x1b[0m", 6),
        ("abc 日本語 def", 14),
    ],
)
def test_cell_width_measurement(input_text: str, expected_width: int) -> None:
    """Verify that cell_width accurately measures monospace cells across character sets."""
    assert cell_width(input_text) == expected_width


@pytest.mark.parametrize(
    ("text", "width", "align", "expected"),
    [
        ("hello", 10, "left", "hello     "),
        ("hello", 10, "right", "     hello"),
        ("hello", 10, "center", "  hello   "),
        ("hello", 11, "center", "   hello   "),
        ("日本語", 10, "left", "日本語    "),
        ("日本語", 10, "right", "    日本語"),
        ("日本語", 10, "center", "  日本語  "),
        ("日本語", 11, "center", "  日本語   "),
        ("toolongstring", 5, "left", "toolongstring"),
        ("toolongstring", 5, "right", "toolongstring"),
        ("toolongstring", 5, "center", "toolongstring"),
    ],
)
def test_pad_to_cell_width_alignments(text: str, width: int, align: str, expected: str) -> None:
    """Verify padding respects display width and alignment options."""
    result = pad_to_cell_width(text, width, align=align)
    assert result == expected
    if cell_width(text) < width:
        assert cell_width(result) == width


def test_pad_to_cell_width_custom_fillchar() -> None:
    """Verify pad_to_cell_width supports custom single-width fill characters."""
    assert pad_to_cell_width("CJK", 7, align="center", fillchar="-") == "--CJK--"
    assert pad_to_cell_width("日本語", 8, align="left", fillchar="-") == "日本語--"
    assert pad_to_cell_width("日本語", 8, align="right", fillchar="-") == "--日本語"


# ---------------------------------------------------------------------------
# MarkdownFormatter alignment tests
# ---------------------------------------------------------------------------


def test_markdown_formatter_cjk_line_widths(cjk_file_sample: list[FileInfo]) -> None:
    """Verify that all lines in Markdown table output maintain identical cell display width."""
    formatter = MarkdownFormatter(absolute=False)
    output = formatter.format(cjk_file_sample)
    lines = [line for line in output.splitlines() if line.strip()]

    assert len(lines) >= len(cjk_file_sample) + 2  # header, separator, rows

    expected_width = cell_width(lines[0])
    for idx, line in enumerate(lines):
        actual_width = cell_width(line)
        assert actual_width == expected_width, (
            f"Line {idx} width mismatch: expected {expected_width}, got {actual_width}.\n"
            f"Content: {line!r}"
        )


def test_markdown_formatter_cjk_pipe_alignment(cjk_file_sample: list[FileInfo]) -> None:
    """Verify that vertical column separator pipes '|' align at the exact same cell positions."""
    formatter = MarkdownFormatter(absolute=False)
    output = formatter.format(cjk_file_sample)
    lines = [line for line in output.splitlines() if line.strip()]

    def get_pipe_cell_positions(line_str: str) -> list[int]:
        positions: list[int] = []
        current_w = 0
        for char in line_str:
            if char == "|":
                positions.append(current_w)

            current_w += cell_len(char)

        return positions

    reference_positions = get_pipe_cell_positions(lines[0])
    for idx, line in enumerate(lines[1:], start=1):
        actual_positions = get_pipe_cell_positions(line)
        assert actual_positions == reference_positions, (
            f"Line {idx} pipe positions mismatch:\n"
            f"Expected: {reference_positions}\n"
            f"Actual:   {actual_positions}\n"
            f"Line: {line!r}"
        )


def test_markdown_formatter_cjk_no_indent(cjk_file_sample: list[FileInfo]) -> None:
    """Verify MarkdownFormatter correctly renders compact unpadded table in no-indent mode."""
    formatter = MarkdownFormatter(no_indent=True)
    output = formatter.format(cjk_file_sample)
    lines = output.splitlines()
    assert lines[0].startswith("|path|relative_path|")
    assert any("日本語" in line and "テスト.py" in line for line in lines)


# ---------------------------------------------------------------------------
# RstFormatter grid and simple table alignment tests
# ---------------------------------------------------------------------------


def test_rst_grid_formatter_cjk_line_widths(cjk_file_sample: list[FileInfo]) -> None:
    """Verify that all lines in reStructuredText grid table output have identical cell width."""
    formatter = RstFormatter(table_style="grid")
    output = formatter.format(cjk_file_sample)
    lines = [line for line in output.splitlines() if line.strip()]

    expected_width = cell_width(lines[0])
    for idx, line in enumerate(lines):
        actual_width = cell_width(line)
        assert actual_width == expected_width, (
            f"RST Grid line {idx} width mismatch: expected {expected_width}, got {actual_width}.\n"
            f"Content: {line!r}"
        )


def test_rst_grid_formatter_cjk_border_intersection_alignment(
    cjk_file_sample: list[FileInfo],
) -> None:
    """Verify that RST grid borders '+' and column separators '|' align at identical cells."""
    formatter = RstFormatter(table_style="grid")
    output = formatter.format(cjk_file_sample)
    lines = [line for line in output.splitlines() if line.strip()]

    def get_junction_cell_positions(line_str: str) -> list[int]:
        positions: list[int] = []
        current_w = 0
        for char in line_str:
            if char in ("+", "|"):
                positions.append(current_w)

            current_w += cell_len(char)

        return positions

    reference_positions = get_junction_cell_positions(lines[0])
    for idx, line in enumerate(lines[1:], start=1):
        actual_positions = get_junction_cell_positions(line)
        assert actual_positions == reference_positions, (
            f"RST Grid line {idx} boundary mismatch:\n"
            f"Expected: {reference_positions}\n"
            f"Actual:   {actual_positions}\n"
            f"Line: {line!r}"
        )


def test_rst_simple_formatter_cjk_line_widths(cjk_file_sample: list[FileInfo]) -> None:
    """Verify that all lines in reStructuredText simple table output have identical cell width."""
    formatter = RstFormatter(table_style="simple")
    output = formatter.format(cjk_file_sample)
    lines = [line for line in output.splitlines() if line.strip()]

    expected_width = cell_width(lines[0])
    for idx, line in enumerate(lines):
        actual_width = cell_width(line)
        assert actual_width == expected_width, (
            f"RST Simple line {idx} width mismatch: "
            f"expected {expected_width}, got {actual_width}.\n"
            f"Content: {line!r}"
        )


# ---------------------------------------------------------------------------
# RichTableFormatter & CsvTableFormatter visual alignment tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("style", ["rounded", "ascii", "double", "grid"])
def test_rich_table_formatter_cjk_border_alignment(
    cjk_file_sample: list[FileInfo],
    style: str,
) -> None:
    """Verify RichTableFormatter box borders maintain vertical alignment with CJK records."""
    formatter = RichTableFormatter(table_style=style)
    output = formatter.format(cjk_file_sample)
    lines = [line for line in output.splitlines() if line.strip()]

    # Skip header title line (e.g. 'findfmt Files') and inspect box lines
    box_lines = [line for line in lines if any(c in line for c in "─-═━╭┌┏╔╰└┗╚")]
    assert box_lines, "Expected box border lines"

    expected_width = cell_width(box_lines[0])
    for idx, line in enumerate(box_lines):
        actual_width = cell_width(line)
        assert actual_width == expected_width, (
            f"Rich table ({style}) border {idx} width mismatch: "
            f"expected {expected_width}, got {actual_width}"
        )


def test_csv_table_formatter_cjk_border_alignment(cjk_file_sample: list[FileInfo]) -> None:
    """Verify CsvTableFormatter maintains strict cell alignment with CJK records."""
    formatter = CsvTableFormatter(table_style="grid")
    output = formatter.format(cjk_file_sample)
    lines = [line for line in output.splitlines() if line.strip()]
    box_lines = [line for line in lines if any(c in line for c in "─-═━┌┏╔└┗╚")]
    assert box_lines
    expected_width = cell_width(box_lines[0])
    for line in box_lines:
        assert cell_width(line) == expected_width


# ---------------------------------------------------------------------------
# RichTreeFormatter hierarchical rendering tests
# ---------------------------------------------------------------------------


def test_rich_tree_formatter_cjk_rendering(cjk_file_sample: list[FileInfo]) -> None:
    """Verify RichTreeFormatter renders hierarchical tree nodes for CJK directory paths."""
    formatter = RichTreeFormatter()
    output = formatter.format(cjk_file_sample)
    lines = output.splitlines()

    # Check that directory nodes and files render cleanly
    assert any("📁 日本語" in line for line in lines)
    assert any("📁 中文目录" in line for line in lines)
    assert any("📁 繁體目錄" in line for line in lines)
    assert any("📁 한국어" in line for line in lines)
    assert any("📄 テスト.py" in line for line in lines)
    assert any("📄 数据_报告.json" in line for line in lines)

    # Check tree guide connectors exist
    assert any(line.startswith(("├──", "└──", "│")) for line in lines[1:])


# ---------------------------------------------------------------------------
# Stream and delimited formatters with CJK inputs
# ---------------------------------------------------------------------------


def test_text_formatter_cjk_paths(cjk_file_sample: list[FileInfo]) -> None:
    """Verify TextFormatter outputs CJK paths and tags without corruption."""
    formatter = TextFormatter(show_tags=True)
    output = formatter.format(cjk_file_sample)
    ja_path = str(pathlib.Path("日本語/テスト.py"))
    zh_path = str(pathlib.Path("中文目录/数据_报告.json"))
    ko_path = str(pathlib.Path("한국어/문서_프로젝트.md"))
    assert f"{ja_path} [スクリプト, パイソン]" in output
    assert f"{zh_path} [数据, 配置]" in output
    assert f"{ko_path} [마크다운]" in output


def test_delimited_formatters_cjk(cjk_file_sample: list[FileInfo]) -> None:
    """Verify CSV and TSV formatters handle CJK text without encoding or escaping issues."""
    ja_path = str(pathlib.Path("日本語/テスト.py"))
    csv_fmt = CsvFormatter()
    csv_out = csv_fmt.format(cjk_file_sample)
    assert ja_path in csv_out
    assert "パイソン, スクリプト" in csv_out or "パイソン" in csv_out

    tsv_fmt = TsvFormatter()
    tsv_out = tsv_fmt.format(cjk_file_sample)
    assert escape_tsv_cell(ja_path) in tsv_out


def test_formatters_stream_cjk(cjk_file_sample: list[FileInfo]) -> None:
    """Verify streaming formatters output identical content with CJK entries."""
    buf_md = io.StringIO()
    md_formatter = MarkdownFormatter()
    md_formatter.stream(cjk_file_sample, buf_md)
    assert buf_md.getvalue() == md_formatter.format(cjk_file_sample)

    buf_rst = io.StringIO()
    rst_formatter = RstFormatter(table_style="grid")
    rst_formatter.stream(cjk_file_sample, buf_rst)
    assert buf_rst.getvalue() == rst_formatter.format(cjk_file_sample)
