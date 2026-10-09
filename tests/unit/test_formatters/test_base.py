"""Unit tests for base formatter and TextFormatter."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

import pytest

from findfmt.formatters import (
    CsvFormatter,
    Formatter,
    IpynbFormatter,
    JsonFormatter,
    JsonlFormatter,
    MarkdownFormatter,
    OutputFormat,
    RstFormatter,
    TextFormatter,
    TsvFormatter,
    UnsupportedFormatError,
    YamlFormatter,
    get_formatter,
)
from findfmt.models import FileInfo

if TYPE_CHECKING:
    from collections.abc import Iterable


@pytest.fixture
def sample_files() -> list[FileInfo]:
    """Provide sample FileInfo objects for testing."""
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


def test_get_formatter_supported_types() -> None:
    """Verify get_formatter resolves all supported format types."""
    assert isinstance(get_formatter(OutputFormat.TEXT), TextFormatter)
    assert isinstance(get_formatter(OutputFormat.JSON), JsonFormatter)
    assert isinstance(get_formatter(OutputFormat.JSONL), JsonlFormatter)
    assert isinstance(get_formatter(OutputFormat.YAML), YamlFormatter)
    assert isinstance(get_formatter(OutputFormat.IPYNB), IpynbFormatter)
    assert isinstance(get_formatter(OutputFormat.CSV), CsvFormatter)
    assert isinstance(get_formatter(OutputFormat.TSV), TsvFormatter)
    assert isinstance(get_formatter(OutputFormat.MARKDOWN), MarkdownFormatter)
    assert isinstance(get_formatter(OutputFormat.MD), MarkdownFormatter)
    assert isinstance(get_formatter(OutputFormat.RST), RstFormatter)

    assert isinstance(get_formatter("text"), TextFormatter)
    assert isinstance(get_formatter("JSON"), JsonFormatter)
    assert isinstance(get_formatter("jsonl"), JsonlFormatter)
    assert isinstance(get_formatter("YAML"), YamlFormatter)
    assert isinstance(get_formatter("ipynb"), IpynbFormatter)
    assert isinstance(get_formatter("csv"), CsvFormatter)
    assert isinstance(get_formatter("TSV"), TsvFormatter)
    assert isinstance(get_formatter("markdown"), MarkdownFormatter)
    assert isinstance(get_formatter("md"), MarkdownFormatter)
    assert isinstance(get_formatter("rst"), RstFormatter)


def test_get_formatter_with_options() -> None:
    """Verify get_formatter passes custom configuration parameters."""
    fmt = get_formatter("json", absolute=True, indent=4)
    assert isinstance(fmt, JsonFormatter)
    assert fmt.absolute is True
    assert fmt.indent == 4

    yaml_fmt = get_formatter("yaml", absolute=True, indent=4)
    assert isinstance(yaml_fmt, YamlFormatter)
    assert yaml_fmt.absolute is True
    assert yaml_fmt.indent == 4

    text_fmt = get_formatter("text", absolute=True, show_tags=True, delimiter="\0")
    assert isinstance(text_fmt, TextFormatter)
    assert text_fmt.absolute is True
    assert text_fmt.show_tags is True
    assert text_fmt.delimiter == "\0"


def test_get_formatter_invalid() -> None:
    """Verify get_formatter raises UnsupportedFormatError on unsupported format."""
    with pytest.raises(UnsupportedFormatError, match="Unsupported output format: 'unknown'"):
        get_formatter("unknown")


def test_base_formatter_default_stream(sample_files: list[FileInfo]) -> None:
    """Verify default stream implementation on Formatter base class."""

    class SimpleFormatter(Formatter):
        @override
        def format(self, files: Iterable[FileInfo]) -> str:
            return f"count={len(list(files))}\n"

    fmt = SimpleFormatter(absolute=False)
    buf = io.StringIO()
    fmt.stream(sample_files, buf)
    assert buf.getvalue() == "count=2\n"


def test_text_formatter_empty() -> None:
    """Verify TextFormatter behavior on empty file sequence."""
    fmt = TextFormatter()
    assert fmt.format([]) == ""

    buf = io.StringIO()
    fmt.stream([], buf)
    assert buf.getvalue() == ""


def test_text_formatter_with_tags_and_absolute(sample_files: list[FileInfo]) -> None:
    """Verify TextFormatter with absolute paths, tag listing, and NUL delimiter."""
    fmt = TextFormatter(absolute=True, show_tags=True, delimiter="\n")
    output = fmt.format(sample_files)
    lines = output.strip().split("\n")
    assert len(lines) == 2
    main_p = str(sample_files[0].path)
    data_p = str(sample_files[1].path)
    assert lines[0] == f"{main_p} [python, text]"
    assert lines[1] == f"{data_p} [json, text]"

    stream_buf = io.StringIO()
    fmt.stream(sample_files, stream_buf)
    assert stream_buf.getvalue() == output


def test_text_formatter_relative_no_tags(sample_files: list[FileInfo]) -> None:
    """Verify TextFormatter with relative paths and no tags."""
    fmt = TextFormatter(absolute=False, show_tags=False)
    output = fmt.format(sample_files)
    assert output == "main.py\ndata.json\n"
