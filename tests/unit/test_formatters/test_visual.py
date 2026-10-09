"""Unit tests for Rich visual formatters (tables, border styles, tree view)."""

from __future__ import annotations

import io
from collections import Counter
from pathlib import Path

import pytest

from findfmt.formatters.visual import (
    RICH_BOX_STYLES,
    RichTableFormatter,
    RichTreeFormatter,
    UnsupportedBoxStyleError,
    format_size,
    format_summary_panel,
    format_tag_badge,
)
from findfmt.models import FileInfo
from findfmt.summary import write_summary


@pytest.fixture
def sample_files() -> list[FileInfo]:
    """Provide diverse FileInfo objects for visual testing."""
    return [
        FileInfo(
            path=Path("/workspace/project/src/app.py"),
            relative_path=Path("src/app.py"),
            tags=frozenset({"python", "executable", "text"}),
            shebang="#!/usr/bin/env python3",
            mime_type="text/x-python",
            is_executable=True,
            is_symlink=False,
            size_bytes=1536,
        ),
        FileInfo(
            path=Path("/workspace/project/docs/guide.md"),
            relative_path=Path("docs/guide.md"),
            tags=frozenset({"markdown", "text"}),
            shebang=None,
            mime_type="text/markdown",
            is_executable=False,
            is_symlink=True,
            size_bytes=1048576,
        ),
        FileInfo(
            path=Path("/workspace/project/README.md"),
            relative_path=Path("README.md"),
            tags=frozenset({"markdown"}),
            shebang=None,
            mime_type=None,
            is_executable=False,
            is_symlink=False,
            size_bytes=512,
        ),
    ]


def test_format_size() -> None:
    """Verify format_size scaling across byte, KB, MB, and GB thresholds."""
    assert format_size(100) == "100 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1536) == "1.5 KB"
    assert format_size(1048576) == "1.0 MB"
    assert format_size(1073741824) == "1.0 GB"


def test_format_tag_badge() -> None:
    """Verify format_tag_badge generates colorful badges and handles unknown tags."""
    badge_py = format_tag_badge("python")
    assert "bright_blue" in badge_py
    assert "python" in badge_py

    badge_unknown = format_tag_badge("custom_unknown_tag")
    assert "cyan" in badge_unknown
    assert "custom_unknown_tag" in badge_unknown


def test_format_summary_panel() -> None:
    """Verify format_summary_panel builds styled panels with stats and tag frequencies."""
    panel_empty = format_summary_panel(0, Counter())
    assert panel_empty.title == "--- findfmt summary ---"

    counter = Counter({"python": 10, "text": 5})
    panel_with_tags = format_summary_panel(15, counter)
    assert panel_with_tags.title == "--- findfmt summary ---"


def test_write_summary_custom_stream() -> None:
    """Verify write_summary outputs correctly to a target stream."""
    buf = io.StringIO()
    counter = Counter({"python": 3, "text": 2})
    write_summary(5, counter, stream=buf)
    out = buf.getvalue()
    assert "findfmt summary" in out
    assert "Matched files:" in out
    assert "python" in out


def test_write_summary_default_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify write_summary defaults to sys.stderr when stream is omitted."""
    counter = Counter({"text": 1})
    write_summary(1, counter)
    captured = capsys.readouterr()
    assert "findfmt summary" in captured.err


def test_rich_table_formatter_valid_styles() -> None:
    """Verify all supported table border styles initialize without error."""
    for style_name in RICH_BOX_STYLES:
        fmt = RichTableFormatter(table_style=style_name)
        assert fmt.table_style == style_name


def test_rich_table_formatter_invalid_style() -> None:
    """Verify RichTableFormatter raises UnsupportedBoxStyleError on unsupported table styles."""
    with pytest.raises(UnsupportedBoxStyleError, match="Unsupported table style: 'neon'"):
        RichTableFormatter(table_style="neon")


def test_rich_table_formatter_rendering(sample_files: list[FileInfo]) -> None:
    """Verify table format output includes columns, filenames, and badges."""
    fmt = RichTableFormatter(absolute=False, table_style="rounded")
    output = fmt.format(sample_files)
    assert "findfmt Files" in output
    assert str(sample_files[0].relative_path) in output
    assert str(sample_files[1].relative_path) in output
    assert "README.md" in output
    assert "1.5 KB" in output
    assert "text/x-python" in output

    buf = io.StringIO()
    fmt.stream(sample_files, buf)
    assert str(sample_files[0].relative_path) in buf.getvalue()


def test_rich_table_formatter_absolute(sample_files: list[FileInfo]) -> None:
    """Verify table format emits absolute paths when absolute=True."""
    fmt = RichTableFormatter(absolute=True, table_style="ascii")
    output = fmt.format(sample_files)
    assert str(sample_files[0].path) in output
    assert "+" in output


def test_rich_table_formatter_empty() -> None:
    """Verify table formatter handles empty file sequences gracefully."""
    fmt = RichTableFormatter()
    output = fmt.format([])
    assert "Path" in output
    assert "findfmt Files" in output


def test_rich_tree_formatter_rendering(sample_files: list[FileInfo]) -> None:
    """Verify tree format constructs hierarchical branches and file leaves."""
    fmt = RichTreeFormatter(absolute=False)
    output = fmt.format(sample_files)
    assert "." in output
    assert "src" in output
    assert "app.py" in output
    assert "docs" in output
    assert "guide.md" in output
    assert "README.md" in output

    buf = io.StringIO()
    fmt.stream(sample_files, buf)
    assert "app.py" in buf.getvalue()


def test_rich_tree_formatter_absolute(sample_files: list[FileInfo]) -> None:
    """Verify tree format constructs absolute hierarchies with root anchor."""
    fmt = RichTreeFormatter(absolute=True)
    output = fmt.format(sample_files)
    assert "/" in output
    assert "workspace" in output
    assert "project" in output
    assert "app.py" in output


def test_rich_tree_formatter_empty() -> None:
    """Verify tree formatter handles empty file sequences gracefully."""
    fmt_rel = RichTreeFormatter(absolute=False)
    assert "." in fmt_rel.format([])

    fmt_abs = RichTreeFormatter(absolute=True)
    assert "/" in fmt_abs.format([])
