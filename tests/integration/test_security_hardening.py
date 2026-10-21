"""Integration tests verifying security hardening across terminal sanitization, ReDoS, and FIFOs.

Part of Epic #338 (sub-issues #361, #362, #363).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from findfmt import classify_file, strip_ansi_escapes, terminal
from findfmt.cli import app
from findfmt.formatters import TextFormatter
from findfmt.models import FileInfo
from findfmt.utils import hyperlinks, strings

runner = CliRunner()


def test_redos_terminal_escape_c1_osc_linear_time_integration() -> None:
    """Verify C1-OSC terminal escape sequence processing finishes in under 100 ms."""
    payload = "\x9d" * 50000 + ";test"
    t_start = time.perf_counter()
    sanitized = strip_ansi_escapes(payload)
    elapsed = time.perf_counter() - t_start

    assert elapsed < 0.1, f"Regex stripping took too long: {elapsed:.3f}s (expected < 0.1s)"
    assert sanitized == payload

    assert strings._ANSI_ESCAPE_RE is terminal._ANSI_REGEX  # noqa: SLF001
    assert strings._ANSI_ESCAPE_RE is hyperlinks._ESCAPE_SEQ_RE  # noqa: SLF001


def test_bidi_override_trojan_source_tty_vs_piped_integration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Trojan Source bidi override characters are masked on TTY and preserved on pipes."""
    trojan_file = tmp_path / "report\u202egnp.py"
    trojan_file.write_text("print('harmless')\n", encoding="utf-8")

    # 1. Piped stream (non-TTY): literal preservation
    res_piped = runner.invoke(app, [str(tmp_path)])
    assert res_piped.exit_code == 0
    assert "\u202e" in res_piped.stdout
    assert "report\u202egnp.py" in res_piped.stdout

    # 2. TTY stream: masked control characters
    monkeypatch.setattr("findfmt.cli.runner._is_stream_tty", lambda _stream: True)
    res_tty = runner.invoke(app, [str(tmp_path)])
    assert res_tty.exit_code == 0
    assert "\u202e" not in res_tty.stdout
    assert "report?gnp.py" in res_tty.stdout

    # 3. NUL-delimited output (-0): literal preservation even under TTY
    res_nul = runner.invoke(app, ["-0", str(tmp_path)])
    assert res_nul.exit_code == 0
    assert "\u202e" in res_nul.stdout
    assert "report\u202egnp.py" in res_nul.stdout

    # 4. Literal option (-N): literal preservation even under TTY
    res_lit = runner.invoke(app, ["-N", str(tmp_path)])
    assert res_lit.exit_code == 0
    assert "\u202e" in res_lit.stdout
    assert "report\u202egnp.py" in res_lit.stdout


def test_fifo_swap_safety_integration(tmp_path: Path) -> None:
    """Verify classification and traversal of swapped named pipe never hangs without writer."""
    if not hasattr(os, "mkfifo"):
        pytest.skip("mkfifo not available on this platform")

    fifo_path = tmp_path / "swapped_target.pipe"
    fifo_path.write_text("regular file initial\n", encoding="utf-8")
    assert fifo_path.is_file()

    fifo_path.unlink()
    os.mkfifo(fifo_path)

    t_start = time.perf_counter()
    info = classify_file(fifo_path, root_path=tmp_path)
    elapsed = time.perf_counter() - t_start

    assert elapsed < 1.0, f"FIFO classification took {elapsed:.3f}s (expected < 1.0s)"
    assert info.indicator == "|"
    assert info.shebang is None
    assert "file" not in info.tags
    assert info.permissions_str is not None
    assert info.permissions_str.startswith("p")

    res = runner.invoke(app, [str(fifo_path)])
    assert res.exit_code == 0


def test_combined_security_hardening_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ReDoS-safe and bidi-sanitized strings pass through formatters cleanly."""
    bidi_name = "data_\u2066test\u2069.csv"
    test_file = tmp_path / bidi_name
    test_file.write_text("1,2,3\n", encoding="utf-8")

    info = FileInfo(
        path=test_file,
        relative_path=Path(bidi_name),
        size_bytes=6,
        tags=frozenset(["text", "csv"]),
    )
    formatter = TextFormatter()
    rendered = formatter.format_item(info)

    assert "data_" in rendered
    assert ".csv" in rendered

    monkeypatch.setattr("findfmt.cli.runner._is_stream_tty", lambda _stream: True)
    res = runner.invoke(app, [str(tmp_path)])
    assert res.exit_code == 0
    assert "\u2066" not in res.stdout
    assert "\u2069" not in res.stdout
    assert "data_?test?.csv" in res.stdout
