"""Unit tests for findfmt CLI output file redirection (-o / --output)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from typing_extensions import override

if TYPE_CHECKING:
    from typing import TextIO

import pytest
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.cli.runner import _is_stream_tty
from findfmt.formatters import TextFormatter


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
    assert "Matched file" in result.stderr


def test_cli_output_redirection_error(tmp_path: Path) -> None:
    """Verify error handling when output file cannot be opened."""
    runner = CliRunner()
    # Path inside a non-existent directory
    invalid_out = tmp_path / "nonexistent_dir" / "out.txt"

    result = runner.invoke(app, [str(tmp_path), "-o", str(invalid_out)])
    assert result.exit_code == 2
    assert "Error opening output file" in result.stderr


def test_is_stream_tty() -> None:
    """Verify _is_stream_tty correctly handles TTY, non-TTY, missing attr, and closed streams."""

    class TtyStream(io.StringIO):
        @override
        def isatty(self) -> bool:
            return True

    class NonTtyStream(io.StringIO):
        @override
        def isatty(self) -> bool:
            return False

    class ErrorStream(io.StringIO):
        @override
        def isatty(self) -> bool:
            msg = "I/O operation on closed file"
            raise ValueError(msg)

    assert _is_stream_tty(TtyStream()) is True
    assert _is_stream_tty(NonTtyStream()) is False
    assert _is_stream_tty(cast("TextIO", object())) is False
    assert _is_stream_tty(ErrorStream()) is False


def test_text_formatter_null_delimiter_preserves_literals() -> None:
    """Verify TextFormatter with delimiter NUL sets literal=True and hide_control_chars=False."""
    fmt = TextFormatter(delimiter="\0", literal=False, hide_control_chars=True)
    assert fmt.literal is True
    assert fmt.hide_control_chars is False


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows filesystems disallow control characters in filenames",
)
@pytest.mark.parametrize(
    "filename",
    [
        "new\nline.txt",
        "tab\tname.txt",
        "esc\x1b[31mred.txt",
    ],
)
def test_print0_preserves_control_characters(tmp_path: Path, filename: str) -> None:
    """Verify -0 / --print0 preserves control characters and escape sequences verbatim."""
    file_path = tmp_path / filename
    file_path.write_text("data", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "findfmt", "-0", str(tmp_path)],
        capture_output=True,
        check=True,
    )
    assert proc.stdout == filename.encode("utf-8") + b"\x00"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows filesystems disallow control characters in filenames",
)
def test_piped_text_output_is_not_sanitised(tmp_path: Path) -> None:
    """Verify piped (non-TTY) text output is emitted verbatim without sanitisation."""
    bad_filename = "bad\x07file.txt"
    (tmp_path / bad_filename).write_text("data", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert bad_filename in result.stdout
    assert "bad?file.txt" not in result.stdout


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows filesystems disallow control characters in filenames",
)
def test_tty_text_output_masks_control_characters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify interactive TTY text output masks control characters and strips ANSI sequences."""
    (tmp_path / "bad\x07file.txt").write_text("data", encoding="utf-8")
    (tmp_path / "esc\x1b[31mred.txt").write_text("data", encoding="utf-8")

    monkeypatch.setattr("findfmt.cli.runner._is_stream_tty", lambda _stream: True)

    runner = CliRunner()
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "bad?file.txt" in result.stdout
    assert "\x07" not in result.stdout
    assert "escred.txt" in result.stdout
    assert "\x1b[31m" not in result.stdout


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows filesystems disallow control characters in filenames",
)
def test_quote_flag_forces_masking_when_piped_and_literal_on_tty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify -q forces masking when piped, and -N forces literal output on a TTY."""
    (tmp_path / "bad\x07file.txt").write_text("data", encoding="utf-8")

    runner = CliRunner()
    # Piped with explicit -q: should mask control characters
    res_piped_q = runner.invoke(app, ["-q", str(tmp_path)])
    assert res_piped_q.exit_code == 0
    assert "bad?file.txt" in res_piped_q.stdout
    assert "\x07" not in res_piped_q.stdout

    # TTY with explicit -N: should preserve control characters verbatim
    monkeypatch.setattr("findfmt.cli.runner._is_stream_tty", lambda _stream: True)
    res_tty_literal = runner.invoke(app, ["-N", str(tmp_path)])
    assert res_tty_literal.exit_code == 0
    assert "bad\x07file.txt" in res_tty_literal.stdout
    assert "\x07" in res_tty_literal.stdout


def test_cli_csv_safe_tsv_and_csv(tmp_path: Path) -> None:
    """Verify CLI --csv-safe neutralizes formula triggers for both CSV and TSV."""
    (tmp_path / "=formula.txt").write_text("data", encoding="utf-8")
    runner = CliRunner()

    res_csv = runner.invoke(app, ["-f", "csv", "--csv-safe", str(tmp_path)])
    assert res_csv.exit_code == 0
    assert "'=formula.txt" in res_csv.stdout

    res_tsv = runner.invoke(app, ["-f", "tsv", "--csv-safe", str(tmp_path)])
    assert res_tsv.exit_code == 0
    assert "'=formula.txt" in res_tsv.stdout
