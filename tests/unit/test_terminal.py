"""Unit tests for terminal management, color resolution, and PagerController."""

from __future__ import annotations

import io
import sys

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

import pytest
from rich.pager import Pager

from findfmt.terminal import (
    PagerController,
    get_console,
    get_terminal_height,
    is_color_enabled,
    should_use_pager,
    strip_ansi,
)


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


def test_strip_ansi_sequences() -> None:
    """Verify strip_ansi cleans various ANSI styling codes."""
    raw = "\x1b[31;1mRed Bold\x1b[0m normal \x1b[?25h"
    assert strip_ansi(raw) == "Red Bold normal "
    assert strip_ansi("Plain text") == "Plain text"


def test_is_color_enabled_no_color() -> None:
    """Verify NO_COLOR takes unconditional precedence over all other settings."""
    tty = MockInteractiveStream()
    pipe = io.StringIO()

    # Non-empty NO_COLOR disables color regardless of TTY or CLICOLOR_FORCE
    assert is_color_enabled(tty, env={"NO_COLOR": "1"}) is False
    assert is_color_enabled(pipe, env={"NO_COLOR": "1", "CLICOLOR_FORCE": "1"}) is False

    # Empty NO_COLOR is ignored
    assert is_color_enabled(tty, env={"NO_COLOR": ""}) is True


def test_is_color_enabled_clicolor_flags() -> None:
    """Verify CLICOLOR_FORCE and CLICOLOR precedence rules."""
    pipe = io.StringIO()
    tty = MockInteractiveStream()

    # CLICOLOR_FORCE forces color on non-terminal
    assert is_color_enabled(pipe, env={"CLICOLOR_FORCE": "1"}) is True
    assert is_color_enabled(pipe, env={"CLICOLOR_FORCE": "0"}) is False
    assert is_color_enabled(pipe, env={"CLICOLOR_FORCE": ""}) is False

    # CLICOLOR=0 disables color even on interactive TTY
    assert is_color_enabled(tty, env={"CLICOLOR": "0"}) is False
    assert is_color_enabled(tty, env={"CLICOLOR": "1"}) is True


def test_is_color_enabled_tty_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify default TTY detection when environment variables are omitted."""
    tty = MockInteractiveStream()
    pipe = io.StringIO()

    assert is_color_enabled(tty, env={}) is True
    assert is_color_enabled(pipe, env={}) is False

    # When stream is omitted, check sys.stdout
    monkeypatch.setattr("sys.stdout", tty)
    assert is_color_enabled(env={}) is True


def test_get_terminal_height() -> None:
    """Verify terminal height returns positive integer with fallback."""
    height = get_terminal_height(fallback=30)
    assert height > 0


def test_should_use_pager_disabled() -> None:
    """Verify should_use_pager returns False when pager=False or non-TTY."""
    tty = MockInteractiveStream()
    pipe = io.StringIO()

    # Explicit disable
    assert should_use_pager(100, pager=False, stream=tty) is False

    # Non-interactive stream always disables pager
    assert should_use_pager(100, pager=True, stream=pipe) is False
    assert should_use_pager(100, pager=None, stream=pipe) is False


def test_should_use_pager_interactive() -> None:
    """Verify interactive paging thresholds for forced and auto modes."""
    tty = MockInteractiveStream()

    # Forced paging on TTY activates even with short content
    assert should_use_pager(1, pager=True, stream=tty) is True

    # Auto-paging activates only when content exceeds terminal height
    assert should_use_pager(10, pager=None, stream=tty, term_height=24) is False
    assert should_use_pager(24, pager=None, stream=tty, term_height=24) is False
    assert should_use_pager(25, pager=None, stream=tty, term_height=24) is True


def test_get_console_configuration() -> None:
    """Verify get_console properly configures no_color, force_terminal, and width."""
    tty = MockInteractiveStream()
    pipe = io.StringIO()

    # Disabled color
    c_no_color = get_console(pipe, env={}, width=100)
    assert c_no_color.no_color is True
    assert c_no_color.width == 100

    # TTY with color
    c_tty = get_console(tty, env={})
    assert c_tty.no_color is False

    # Forced color on non-terminal
    c_forced = get_console(pipe, env={"CLICOLOR_FORCE": "1"})
    assert c_forced.no_color is False
    assert c_forced.color_system == "standard"

    # Explicit force_color flag
    c_explicit_on = get_console(pipe, force_color=True)
    assert c_explicit_on.no_color is False

    c_explicit_off = get_console(tty, force_color=False)
    assert c_explicit_off.no_color is True


def test_pager_controller_direct_stream() -> None:
    """Verify PagerController writes directly to stream when paging is not needed."""
    stream = io.StringIO()
    controller = PagerController(pager=False, stream=stream)

    controller.display("Line 1\nLine 2\n")
    assert stream.getvalue() == "Line 1\nLine 2\n"


def test_pager_controller_interactive_paging() -> None:
    """Verify PagerController routes through Rich pager when paging is needed."""
    stream = MockInteractiveStream()
    pager = MockCapturePager()
    controller = PagerController(
        pager=True,
        stream=stream,
        pager_impl=pager,
    )

    controller.display("Page 1\nPage 2\n")
    assert len(pager.contents) == 1
    assert "Page 1\nPage 2\n" in pager.contents[0]


def test_pager_controller_strips_ansi_when_uncolored() -> None:
    """Verify PagerController automatically strips ANSI escapes for non-colored streams."""
    stream = io.StringIO()
    controller = PagerController(
        pager=False,
        stream=stream,
        env={"NO_COLOR": "1"},
    )

    controller.display("\x1b[32mSuccess\x1b[0m\n")
    assert stream.getvalue() == "Success\n"


def test_pager_controller_preserves_ansi_when_colored() -> None:
    """Verify PagerController preserves ANSI escapes when color is enabled."""
    stream = MockInteractiveStream()
    controller = PagerController(
        pager=False,
        stream=stream,
        env={"CLICOLOR_FORCE": "1"},
    )

    controller.display("\x1b[32mSuccess\x1b[0m\n")
    assert stream.getvalue() == "\x1b[32mSuccess\x1b[0m\n"
