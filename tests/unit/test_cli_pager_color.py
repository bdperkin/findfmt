"""Unit tests for CLI help output color preservation and pager styling."""

from __future__ import annotations

import io
import sys
from typing import Any

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

import pytest
import typer
import typer.core
from rich.pager import Pager

from findfmt.cli_pager import (
    FindfmtCommand,
    _capture_help_output,
    _extract_raw_args,
    resolve_color_flag,
)
from findfmt.terminal import PagerController, strip_ansi


class MockInteractiveStream(io.StringIO):
    """Simulated interactive TTY stream."""

    @override
    def isatty(self) -> bool:
        """Report stream as interactive terminal."""
        return True


class MockCapturePager(Pager):
    """Capture pager output for assertions."""

    def __init__(self) -> None:
        """Initialize capture buffer."""
        self.contents: list[str] = []

    @override
    def show(self, content: str) -> None:
        """Record paged content."""
        self.contents.append(content)


def test_extract_raw_args_from_ctx_args() -> None:
    """Verify _extract_raw_args resolves argument list directly from ctx.args."""
    cmd = FindfmtCommand(name="findfmt", help="test command")
    ctx = typer.Context(cmd, info_name="findfmt")
    ctx.args = ["--no-color", "--pager"]

    extracted = _extract_raw_args(ctx)
    assert extracted == ["--no-color", "--pager"]
    assert resolve_color_flag(ctx) is False


def test_help_pager_preserves_ansi_color_on_tty() -> None:
    """Verify FindfmtCommand preserves Rich ANSI color escapes when paged on TTY."""
    cmd = FindfmtCommand(name="findfmt", help="findfmt command help description")
    ctx = typer.Context(cmd, info_name="findfmt")
    formatter = ctx.make_formatter()

    tty_stream = MockInteractiveStream()
    mock_pager = MockCapturePager()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "stdout", tty_stream)
        mp.setenv("TERM", "xterm-256color")
        original_init = PagerController.__init__

        def custom_init(self: PagerController, *args: Any, **kwargs: Any) -> None:
            kwargs["term_height"] = 5
            kwargs["pager_impl"] = mock_pager
            original_init(self, *args, **kwargs)

        mp.setattr(PagerController, "__init__", custom_init)
        cmd.format_help(ctx, formatter)

    assert len(mock_pager.contents) == 1
    # Paged content must retain Rich ANSI escape sequences
    assert "\x1b[" in mock_pager.contents[0]
    assert "Usage: findfmt" in strip_ansi(mock_pager.contents[0])


def test_help_pager_strips_color_when_no_color_flag() -> None:
    """Verify FindfmtCommand suppresses ANSI colors when --no-color flag is passed."""
    cmd = FindfmtCommand(name="findfmt", help="findfmt command help description")
    ctx = typer.Context(cmd, info_name="findfmt")
    ctx.args = ["--no-color"]
    formatter = ctx.make_formatter()

    tty_stream = MockInteractiveStream()
    mock_pager = MockCapturePager()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "stdout", tty_stream)
        original_init = PagerController.__init__

        def custom_init(self: PagerController, *args: Any, **kwargs: Any) -> None:
            kwargs["term_height"] = 5
            kwargs["pager_impl"] = mock_pager
            original_init(self, *args, **kwargs)

        mp.setattr(PagerController, "__init__", custom_init)
        cmd.format_help(ctx, formatter)

    assert len(mock_pager.contents) == 1
    assert "\x1b[" not in mock_pager.contents[0]
    assert "Usage: findfmt" in mock_pager.contents[0]


def test_help_pager_honors_no_color_env() -> None:
    """Verify FindfmtCommand suppresses ANSI colors when NO_COLOR is set."""
    cmd = FindfmtCommand(name="findfmt", help="findfmt command help description")
    ctx = typer.Context(cmd, info_name="findfmt")
    formatter = ctx.make_formatter()

    tty_stream = MockInteractiveStream()
    mock_pager = MockCapturePager()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "stdout", tty_stream)
        mp.setenv("NO_COLOR", "1")
        original_init = PagerController.__init__

        def custom_init(self: PagerController, *args: Any, **kwargs: Any) -> None:
            kwargs["term_height"] = 5
            kwargs["pager_impl"] = mock_pager
            original_init(self, *args, **kwargs)

        mp.setattr(PagerController, "__init__", custom_init)
        cmd.format_help(ctx, formatter)

    assert len(mock_pager.contents) == 1
    assert "\x1b[" not in mock_pager.contents[0]
    assert "Usage: findfmt" in mock_pager.contents[0]


def test_help_capture_fallback_to_formatter() -> None:
    """Verify _capture_help_output falls back to formatter content if super is empty."""
    cmd = FindfmtCommand(name="findfmt", help="test fallback")
    ctx = typer.Context(cmd, info_name="findfmt")
    formatter = ctx.make_formatter()
    formatter.write("custom formatter output\n")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(typer.core.TyperCommand, "format_help", lambda _s, _c, _f: None)
        captured = _capture_help_output(cmd, ctx, formatter)

    assert "custom formatter output" in captured


def test_help_capture_empty_when_no_content() -> None:
    """Verify _capture_help_output returns empty string when neither super nor formatter write."""
    cmd = FindfmtCommand(name="findfmt", help="test empty")
    ctx = typer.Context(cmd, info_name="findfmt")
    formatter = ctx.make_formatter()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(typer.core.TyperCommand, "format_help", lambda _s, _c, _f: None)
        captured = _capture_help_output(cmd, ctx, formatter)

    assert captured == ""


def test_help_pager_preserves_color_on_dumb_term_when_forced() -> None:
    """Verify FindfmtCommand falls back to standard color system on dumb terminal."""
    cmd = FindfmtCommand(name="findfmt", help="findfmt command help description")
    ctx = typer.Context(cmd, info_name="findfmt")
    ctx.args = ["--color"]
    formatter = ctx.make_formatter()

    tty_stream = MockInteractiveStream()
    mock_pager = MockCapturePager()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "stdout", tty_stream)
        mp.setenv("TERM", "dumb")
        original_init = PagerController.__init__

        def custom_init(self: PagerController, *args: Any, **kwargs: Any) -> None:
            kwargs["term_height"] = 5
            kwargs["pager_impl"] = mock_pager
            original_init(self, *args, **kwargs)

        mp.setattr(PagerController, "__init__", custom_init)
        cmd.format_help(ctx, formatter)

    assert len(mock_pager.contents) == 1
    assert "\x1b[" in mock_pager.contents[0]
    assert "Usage: findfmt" in strip_ansi(mock_pager.contents[0])
