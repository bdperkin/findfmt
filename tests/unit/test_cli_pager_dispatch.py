"""Unit tests for CLI interactive pager resolution and FindfmtCommand dispatching."""

from __future__ import annotations

import io
import sys
from typing import Any
from unittest.mock import MagicMock

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

import pytest
import typer.core
from rich.pager import Pager
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.cli_pager import (
    FindfmtCommand,
    _extract_from_frame,
    _extract_raw_args,
    display_with_pager,
    resolve_color_flag,
    resolve_pager_flag,
)
from findfmt.terminal import PagerController


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


def test_extract_raw_args_explicit_and_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify raw argument extraction from explicit args, context, and environment."""
    assert _extract_raw_args(args=["--pager", "foo"]) == ["--pager", "foo"]

    mock_ctx = MagicMock()
    mock_ctx.obj = {"argv": ["--no-pager", "-t", "python"]}
    assert _extract_raw_args(mock_ctx) == ["--no-pager", "-t", "python"]

    mock_ctx_invalid = MagicMock()
    mock_ctx_invalid.obj = {"other": 123}
    monkeypatch.setattr(sys, "argv", ["findfmt", "--ctx-fallback"])
    assert _extract_raw_args(mock_ctx_invalid) == ["--ctx-fallback"]


def test_extract_raw_args_caller_frames() -> None:
    """Verify extraction checks caller frame locals when ctx.obj is not present."""
    assert _extract_from_frame(None) is None
    mock_ctx = MagicMock()
    mock_ctx.obj = None

    frame_ctx = MagicMock()
    frame_ctx.obj = {"argv": ["--from-frame-ctx"]}

    def frame_helper_ctx() -> list[str]:
        ctx = frame_ctx  # noqa: F841
        return _extract_raw_args()

    assert frame_helper_ctx() == ["--from-frame-ctx"]

    frame_ctx_no_argv = MagicMock()
    frame_ctx_no_argv.obj = {"no_argv": 1}

    def frame_helper_no_argv() -> list[str]:
        ctx = frame_ctx_no_argv  # noqa: F841
        argv = ("--from-argv",)  # noqa: F841
        return _extract_raw_args()

    assert frame_helper_no_argv() == ["--from-argv"]

    def frame_helper_argv() -> list[str]:
        argv = ("--frame-argv-1", "--frame-argv-2")  # noqa: F841
        return _extract_raw_args()

    assert frame_helper_argv() == ["--frame-argv-1", "--frame-argv-2"]

    def frame_helper_args_list() -> list[str]:
        args_list = ["--frame-args-list"]  # noqa: F841
        return _extract_raw_args()

    assert frame_helper_args_list() == ["--frame-args-list"]


def test_extract_raw_args_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify extraction falls back to sys.argv when no args or frames match."""
    monkeypatch.setattr(sys, "argv", ["findfmt", "--sys-argv-flag"])
    assert _extract_raw_args() == ["--sys-argv-flag"]


def test_resolve_pager_flag() -> None:
    """Verify resolve_pager_flag respects ctx params, flags, and returns None."""
    assert resolve_pager_flag(MagicMock(params={"pager": True})) is True
    assert resolve_pager_flag(MagicMock(params={"pager": False})) is False
    assert resolve_pager_flag(args=["--no-pager"]) is False
    assert resolve_pager_flag(args=["--pager"]) is True
    assert resolve_pager_flag(args=["-P"]) is True
    assert resolve_pager_flag(args=["--other-flag"]) is None


def test_resolve_color_flag() -> None:
    """Verify resolve_color_flag respects ctx params, flags, and returns None."""
    assert resolve_color_flag(MagicMock(params={"color": True})) is True
    assert resolve_color_flag(MagicMock(params={"color": False})) is False
    assert resolve_color_flag(args=["--no-color"]) is False
    assert resolve_color_flag(args=["-n"]) is False
    assert resolve_color_flag(args=["--color"]) is True
    assert resolve_color_flag(args=["-C"]) is True
    assert resolve_color_flag(args=["--other-flag"]) is None


def test_display_with_pager_tty_and_bypass() -> None:
    """Verify display_with_pager invokes pager on tall TTY and writes on non-TTY."""
    tall_content = "\n".join(f"line {i}" for i in range(30)) + "\n"
    pager_mock = MockCapturePager()

    # Interactive TTY stream exceeding term_height
    tty_stream = MockInteractiveStream()
    display_with_pager(
        tall_content,
        stream=tty_stream,
        term_height=10,
        pager_impl=pager_mock,
    )
    assert len(pager_mock.contents) == 1
    assert "line 0" in pager_mock.contents[0]

    # Non-TTY stream (bypass pager)
    plain_stream = io.StringIO()
    display_with_pager(
        tall_content,
        stream=plain_stream,
        term_height=10,
        pager_impl=pager_mock,
    )
    assert plain_stream.getvalue() == tall_content

    # Interactive TTY with --no-pager bypass
    tty_stream_no_pager = MockInteractiveStream()
    pager_mock2 = MockCapturePager()
    display_with_pager(
        tall_content,
        stream=tty_stream_no_pager,
        term_height=10,
        pager_impl=pager_mock2,
        ctx=MagicMock(params={"pager": False}),
    )
    assert len(pager_mock2.contents) == 0
    assert tty_stream_no_pager.getvalue() == tall_content


def test_display_with_pager_color_handling() -> None:
    """Verify display_with_pager passes force_color and resolve_color_flag."""
    stream_color = io.StringIO()
    display_with_pager(
        "\x1b[31mRed\x1b[0m",
        stream=stream_color,
        force_color=False,
    )
    assert "\x1b[" not in stream_color.getvalue()
    assert "Red" in stream_color.getvalue()

    stream_colored = io.StringIO()
    display_with_pager(
        "\x1b[31mRed\x1b[0m",
        stream=stream_colored,
        force_color=True,
    )
    assert "\x1b[31mRed\x1b[0m" in stream_colored.getvalue()


def test_findfmt_command_format_help() -> None:
    """Verify FindfmtCommand.format_help captures and pages formatted help."""
    cmd = FindfmtCommand(name="findfmt")
    ctx = typer.Context(cmd, info_name="findfmt")
    formatter = ctx.make_formatter()

    # Test format_help default execution
    captured = io.StringIO()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "stdout", captured)
        cmd.format_help(ctx, formatter)

    assert captured.getvalue() != ""

    # Test format_help with empty super buf and non-empty formatter
    formatter.write("formatter text\n")
    mock_super_ctx = typer.Context(cmd, info_name="findfmt")
    captured2 = io.StringIO()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "stdout", captured2)
        # Mock super().format_help to not write to stdout
        mp.setattr(typer.core.TyperCommand, "format_help", lambda _self, _ctx, _fmt: None)
        cmd.format_help(mock_super_ctx, formatter)

    assert "formatter text" in captured2.getvalue()

    # Test format_help with empty super buf and empty formatter
    empty_formatter = mock_super_ctx.make_formatter()
    captured3 = io.StringIO()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "stdout", captured3)
        mp.setattr(typer.core.TyperCommand, "format_help", lambda _self, _ctx, _fmt: None)
        cmd.format_help(mock_super_ctx, empty_formatter)

    assert captured3.getvalue() == ""


def test_findfmt_command_interactive_paging() -> None:
    """Verify FindfmtCommand formats and invokes pager when terminal is interactive."""
    cmd = FindfmtCommand(name="findfmt", help="findfmt command help description")
    ctx = typer.Context(cmd, info_name="findfmt")
    formatter = ctx.make_formatter()

    tty_stream = MockInteractiveStream()
    mock_pager = MockCapturePager()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "stdout", tty_stream)
        # Force terminal height small so help exceeds height
        original_init = PagerController.__init__

        def custom_init(self: PagerController, *args: Any, **kwargs: Any) -> None:
            kwargs["term_height"] = 5
            kwargs["pager_impl"] = mock_pager
            original_init(self, *args, **kwargs)

        mp.setattr(PagerController, "__init__", custom_init)
        cmd.format_help(ctx, formatter)

    assert len(mock_pager.contents) == 1
    assert "Usage: findfmt" in mock_pager.contents[0]


def test_cli_runner_help_and_diagnostics_paging() -> None:
    """Verify CLI help, help-all, known-tags, and diagnostics output via CliRunner."""
    runner = CliRunner()

    res_help = runner.invoke(app, ["--help"])
    assert res_help.exit_code == 0
    assert "Usage: findfmt" in res_help.stdout

    res_help_no_pager = runner.invoke(app, ["--help", "--no-pager"])
    assert res_help_no_pager.exit_code == 0
    assert "Usage: findfmt" in res_help_no_pager.stdout

    res_help_pager = runner.invoke(app, ["--help", "--pager"])
    assert res_help_pager.exit_code == 0
    assert "Usage: findfmt" in res_help_pager.stdout

    res_help_all = runner.invoke(app, ["--help-all"])
    assert res_help_all.exit_code == 0
    assert "Comprehensive CLI Reference" in res_help_all.stdout

    res_help_all_no_pager = runner.invoke(app, ["--help-all", "--no-pager"])
    assert res_help_all_no_pager.exit_code == 0
    assert "Comprehensive CLI Reference" in res_help_all_no_pager.stdout

    res_known_tags = runner.invoke(app, ["--known-tags", "--no-pager"])
    assert res_known_tags.exit_code == 0
    assert "python\n" in res_known_tags.stdout

    res_diagnostics = runner.invoke(app, ["--diagnostics", "--no-pager"])
    assert res_diagnostics.exit_code == 0
    assert "findfmt " in res_diagnostics.stdout
