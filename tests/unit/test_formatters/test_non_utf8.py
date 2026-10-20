"""Regression tests for non-UTF-8 filesystem paths and surrogate escapes across formatters."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING, cast

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

import pytest
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.cli.runner import _reconfigure_surrogateescape
from findfmt.formatters import OutputFormat
from findfmt.formatters.base import write_stream_safe
from findfmt.formatters.structured import escape_surrogates
from findfmt.formatters.xml_formatter import (
    XmlFormatter,
    _is_valid_xml_char,
    _sanitize_xml_text,
)
from findfmt.models import FileInfo

if TYPE_CHECKING:
    from typing import TextIO

_SURROGATE_MIN = 0xD800
_SURROGATE_MAX = 0xDFFF


@pytest.mark.parametrize("output_format", [fmt.value for fmt in OutputFormat])
def test_formatter_handles_surrogate_paths(non_utf8_tree: Path, output_format: str) -> None:
    """Verify all registered formatters handle non-UTF-8 filenames without UnicodeEncodeError."""
    runner = CliRunner()
    result = runner.invoke(app, [str(non_utf8_tree), "-f", output_format])
    assert result.exit_code == 0, f"Format '{output_format}' failed: {result.exception}"
    assert result.exception is None
    assert "UnicodeEncodeError" not in (result.output or "")


def test_print0_round_trips_raw_bytes(non_utf8_tree: Path) -> None:
    """Verify findfmt -0 round-trips exact raw bytes for non-UTF-8 filenames."""
    proc = subprocess.run(
        [sys.executable, "-m", "findfmt", str(non_utf8_tree), "-0"],
        capture_output=True,
        check=False,
    )
    stderr_msg = proc.stderr.decode("utf-8", errors="replace")
    assert proc.returncode == 0, f"Process failed with stderr: {stderr_msg}"
    assert b"bad\xff.txt\x00" in proc.stdout


def test_json_output_is_valid_with_surrogate_path(non_utf8_tree: Path) -> None:
    """Verify json.loads succeeds on JSON output and identifies the surrogate path."""
    runner = CliRunner()
    result = runner.invoke(app, [str(non_utf8_tree), "-f", "json"])
    assert result.exit_code == 0
    records = json.loads(result.output)
    assert isinstance(records, list)
    matching = [r for r in records if "bad" in r.get("path", "")]
    assert len(matching) == 1
    record = matching[0]
    expected_surrogate_name = "bad\udcff.txt"
    assert record["path"] == expected_surrogate_name
    assert "path_bytes" in record
    assert bytes(record["path_bytes"]).endswith(b"bad\xff.txt")


def test_xml_output_parses_with_surrogate_path(non_utf8_tree: Path) -> None:
    """Verify XML output parses with xml.etree without ParseError."""
    runner = CliRunner()
    result = runner.invoke(app, [str(non_utf8_tree), "-f", "xml"])
    assert result.exit_code == 0
    root = ET.fromstring(result.output)
    assert root.tag == "tree"


def test_escape_surrogates_no_surrogates() -> None:
    """Verify escape_surrogates returns original string unmodified when no surrogates present."""
    text = "regular_unicode_café_日本語"
    assert escape_surrogates(text) is text


def test_escape_surrogates_with_surrogates() -> None:
    """Verify escape_surrogates replaces surrogate code points with \\uXXXX ASCII sequences."""
    text = "bad\udcff.txt"
    escaped = escape_surrogates(text)
    assert escaped == "bad\\udcff.txt"
    assert escaped.encode("utf-8") == b"bad\\udcff.txt"


def test_xml_char_validation() -> None:
    """Verify _is_valid_xml_char accurately discriminates valid XML 1.0 characters."""
    assert _is_valid_xml_char("\t")
    assert _is_valid_xml_char("\n")
    assert _is_valid_xml_char("\r")
    assert _is_valid_xml_char("a")
    assert _is_valid_xml_char("\u00a0")
    assert _is_valid_xml_char("\ud7ff")
    assert not _is_valid_xml_char("\udcff")
    assert not _is_valid_xml_char("\ud800")
    assert not _is_valid_xml_char("\udfff")
    assert _is_valid_xml_char("\ue000")
    assert _is_valid_xml_char("\ufffd")
    assert not _is_valid_xml_char("\ufffe")
    assert not _is_valid_xml_char("\uffff")
    assert not _is_valid_xml_char("\x00")
    assert not _is_valid_xml_char("\x1b")


def test_sanitize_xml_text() -> None:
    """Verify _sanitize_xml_text masks surrogates and control characters as '?'."""
    byte_ff = os.fsdecode(b"\xff")
    surrogate_str = f"bad\x1b[31m{byte_ff}\ufffe.txt"
    sanitized = _sanitize_xml_text(surrogate_str)
    assert sanitized == "bad??.txt"


def test_write_stream_safe_buffer_fallback() -> None:
    """Verify write_stream_safe encodes to stream.buffer on UnicodeEncodeError."""

    class StrictStream(io.TextIOBase):
        """Mock stream whose write method raises UnicodeEncodeError."""

        def __init__(self) -> None:
            super().__init__()
            self.buffer = io.BytesIO()

        @property
        @override
        def encoding(self) -> str:
            return "utf-8"

        @override
        def write(self, s: str) -> int:
            if any(_SURROGATE_MIN <= ord(c) <= _SURROGATE_MAX for c in s):
                enc = "utf-8"
                msg = "surrogates not allowed"
                raise UnicodeEncodeError(enc, s, 0, 1, msg)

            return len(s)

    stream = StrictStream()
    byte_fe = os.fsdecode(b"\xfe")
    surrogate_text = f"prefix_{byte_fe}_suffix"
    write_stream_safe(cast("TextIO", stream), surrogate_text)
    assert stream.buffer.getvalue() == b"prefix_\xfe_suffix"


def test_write_stream_safe_no_buffer_reraises() -> None:
    """Verify write_stream_safe reraises UnicodeEncodeError when buffer is not available."""

    class NoBufferStream(io.TextIOBase):
        @override
        def write(self, s: str) -> int:
            enc = "utf-8"
            msg = "surrogates not allowed"
            raise UnicodeEncodeError(enc, s, 0, 1, msg)

    stream = NoBufferStream()
    with pytest.raises(UnicodeEncodeError):
        write_stream_safe(cast("TextIO", stream), "bad\udcff")


def test_xml_formatter_clean_val_none() -> None:
    """Verify XmlFormatter._clean_val handles None input cleanly."""
    fmt = XmlFormatter()
    assert fmt._clean_val(None) is None  # noqa: SLF001


def test_xml_formatter_literal_masks_surrogates() -> None:
    """Verify XmlFormatter in literal mode masks surrogates and noncharacters."""
    fmt = XmlFormatter(literal=True)
    surrogate_text = "file_\udcff\ufffe_literal.txt"
    assert fmt._clean_val(surrogate_text) == "file_??_literal.txt"  # noqa: SLF001
    assert fmt._clean_val("normal_literal\x03.txt") == "normal_literal\x03.txt"  # noqa: SLF001


def test_file_info_to_dict_with_surrogate_path() -> None:
    """Verify FileInfo.to_dict includes path_bytes when path contains surrogate code points."""
    info = FileInfo(
        path=Path("bad\udcff.txt"),
        relative_path=Path("bad\udcff.txt"),
    )
    result = info.to_dict()
    assert "path_bytes" in result
    assert bytes(result["path_bytes"]) == b"bad\xff.txt"


def test_reconfigure_surrogateescape() -> None:
    """Verify _reconfigure_surrogateescape safely configures streams."""
    buf = io.StringIO()
    _reconfigure_surrogateescape(buf)

    bio = io.BytesIO()
    wrapper = io.TextIOWrapper(bio, encoding="utf-8")
    _reconfigure_surrogateescape(wrapper)
    assert wrapper.errors == "surrogateescape"
