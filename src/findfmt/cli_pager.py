"""CLI interactive pager dispatching, eager flag resolution, and help formatting."""

from __future__ import annotations

import contextlib
import inspect
import io
import sys
from typing import TYPE_CHECKING, Literal, TextIO, cast

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

import typer
import typer.core
from typer import rich_utils

from findfmt.terminal import PagerController, get_console, is_color_enabled

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import FrameType

    from rich.pager import Pager
    from typer.core import _click

__all__ = [
    "FindfmtCommand",
    "display_with_pager",
    "resolve_color_flag",
    "resolve_pager_flag",
]


def _extract_from_context(ctx: object | None) -> list[str] | None:
    """Extract argv from Click/Typer context args or obj dictionary.

    Args:
        ctx: Click/Typer context instance, if available.

    Returns:
        List of argument strings, or None if not found.
    """
    if ctx is None:
        return None

    args = getattr(ctx, "args", None)
    if isinstance(args, list | tuple) and args:
        return [str(x) for x in args]

    obj = getattr(ctx, "obj", None)
    if isinstance(obj, dict):
        cand = obj.get("argv")
        if isinstance(cand, list | tuple) and cand:
            return [str(x) for x in cand]

    return None


def _extract_from_frame_args(frame: FrameType) -> list[str] | None:
    """Extract argv from argv, args_list, or args in frame locals.

    Args:
        frame: Call stack frame to inspect.

    Returns:
        List of argument strings, or None if not found.
    """
    for key in ("argv", "args_list", "args"):
        cand = frame.f_locals.get(key)
        if isinstance(cand, list | tuple) and cand and all(isinstance(x, str) for x in cand):
            return [str(x) for x in cand]

    return None


def _extract_from_frame(frame: FrameType | None) -> list[str] | None:
    """Extract argv candidate from single call stack frame locals.

    Args:
        frame: Call stack frame to inspect.

    Returns:
        List of argument strings, or None if not found.
    """
    if frame is None:
        return None

    return _extract_from_context(frame.f_locals.get("ctx")) or _extract_from_frame_args(frame)


def _extract_from_stack() -> list[str] | None:
    """Walk caller frames to locate CLI arguments.

    Returns:
        List of argument strings, or None if not found.
    """
    frame = inspect.currentframe()
    while frame:
        cand = _extract_from_frame(frame)
        if cand is not None:
            return cand

        frame = frame.f_back

    return None


def _extract_raw_args(
    ctx: object = None,
    args: Sequence[str] | None = None,
) -> list[str]:
    """Extract raw argument string list from sequence, context, or call stack.

    Args:
        ctx: Click/Typer context, if available.
        args: Optional explicit sequence of argument strings.

    Returns:
        List of raw command-line argument strings.
    """
    if args is not None:
        return list(args)

    cand = _extract_from_context(ctx) or _extract_from_stack()
    if cand is not None:
        return cand

    return list(sys.argv[1:])


def resolve_pager_flag(
    ctx: object = None,
    *,
    args: Sequence[str] | None = None,
) -> bool | None:
    """Resolve explicit pager request from context, arguments, or environment.

    Args:
        ctx: Click/Typer context, if available.
        args: Optional explicit sequence of argument strings.

    Returns:
        True if --pager/-P requested, False if --no-pager requested, None for auto.
    """
    if ctx is not None:
        params = getattr(ctx, "params", {})
        if "pager" in params and params["pager"] is not None:
            return bool(params["pager"])

    raw_args = _extract_raw_args(ctx, args)
    for arg in reversed(raw_args):
        if arg == "--no-pager":
            return False

        if arg in ("--pager", "-P"):
            return True

    return None


def resolve_color_flag(
    ctx: object = None,
    *,
    args: Sequence[str] | None = None,
) -> bool | None:
    """Resolve explicit color output request from context, arguments, or environment.

    Args:
        ctx: Click/Typer context, if available.
        args: Optional explicit sequence of argument strings.

    Returns:
        True if --color/-C requested, False if --no-color/-n requested, None for auto.
    """
    if ctx is not None:
        params = getattr(ctx, "params", {})
        if "color" in params and params["color"] is not None:
            return bool(params["color"])

    raw_args = _extract_raw_args(ctx, args)
    for arg in reversed(raw_args):
        if arg in ("--no-color", "-n"):
            return False

        if arg in ("--color", "-C"):
            return True

    return None


def display_with_pager(  # noqa: PLR0913
    content: str,
    *,
    ctx: object = None,
    stream: TextIO | None = None,
    term_height: int | None = None,
    pager_impl: Pager | None = None,
    force_color: bool | None = None,
) -> None:
    """Display informational text via PagerController, honoring CLI flags and TTY.

    Args:
        content: Formatted multi-line text to display.
        ctx: Click/Typer context, if available.
        stream: Target output text stream (defaults to sys.stdout).
        term_height: Terminal height override for testing.
        pager_impl: Optional custom Rich Pager instance.
        force_color: Explicit color enable override flag.
    """
    pager_flag = resolve_pager_flag(ctx)
    color_flag = force_color if force_color is not None else resolve_color_flag(ctx)
    target_stream = stream if stream is not None else sys.stdout
    controller = PagerController(
        pager=pager_flag,
        stream=target_stream,
        term_height=term_height,
        pager_impl=pager_impl,
        force_color=color_flag,
    )
    controller.display(content)


def _capture_help_output(
    cmd: typer.core.TyperCommand,
    ctx: _click.Context,
    formatter: _click.HelpFormatter,
) -> str:
    """Capture formatted command help while preserving terminal ANSI color sequences.

    Args:
        cmd: Typer command instance to format help for.
        ctx: Active Click context.
        formatter: Click help formatter.

    Returns:
        Rendered help string.
    """
    color_flag = resolve_color_flag(ctx)
    color_on = is_color_enabled(sys.stdout, force_color=color_flag)

    orig_force = getattr(rich_utils, "FORCE_TERMINAL", None)
    orig_cs = getattr(rich_utils, "COLOR_SYSTEM", None)

    try:
        if color_on:
            rich_utils.FORCE_TERMINAL = True
            real_console = get_console(sys.stdout, force_color=color_flag)
            cs = real_console.color_system
            if cs in ("standard", "256", "truecolor", "windows"):
                rich_utils.COLOR_SYSTEM = cast(
                    "Literal['auto', 'standard', '256', 'truecolor', 'windows']",
                    cs,
                )
            else:
                rich_utils.COLOR_SYSTEM = "standard"
        else:
            rich_utils.FORCE_TERMINAL = False

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            typer.core.TyperCommand.format_help(cmd, ctx, formatter)
    finally:
        rich_utils.FORCE_TERMINAL = orig_force
        rich_utils.COLOR_SYSTEM = orig_cs

    content = buf.getvalue()
    if not content and formatter.getvalue():
        return formatter.getvalue()

    return content


class FindfmtCommand(typer.core.TyperCommand):
    """Custom TyperCommand routing help output through interactive pager on TTY."""

    @override
    def format_help(self, ctx: _click.Context, formatter: _click.HelpFormatter) -> None:
        """Format and page command help text when appropriate.

        Args:
            ctx: Active Click context.
            formatter: Click help formatter.
        """
        content = _capture_help_output(self, ctx, formatter)
        if content:
            display_with_pager(content, ctx=ctx)
