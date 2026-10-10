"""CLI interactive pager dispatching, eager flag resolution, and help formatting."""

from __future__ import annotations

import contextlib
import inspect
import io
import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

import typer
import typer.core

from findfmt.terminal import PagerController

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


def _extract_from_frame_ctx(frame: FrameType) -> list[str] | None:
    """Extract argv from ctx in frame locals.

    Args:
        frame: Call stack frame to inspect.

    Returns:
        List of argument strings, or None if not found.
    """
    c = frame.f_locals.get("ctx")
    c_obj = getattr(c, "obj", None)
    if isinstance(c_obj, dict):
        cand = c_obj.get("argv")
        if isinstance(cand, list | tuple):
            return [str(x) for x in cand]

    return None


def _extract_from_frame_args(frame: FrameType) -> list[str] | None:
    """Extract argv from argv or args_list in frame locals.

    Args:
        frame: Call stack frame to inspect.

    Returns:
        List of argument strings, or None if not found.
    """
    for key in ("argv", "args_list"):
        cand = frame.f_locals.get(key)
        if isinstance(cand, list | tuple) and all(isinstance(x, str) for x in cand):
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

    return _extract_from_frame_ctx(frame) or _extract_from_frame_args(frame)


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

    if ctx is not None:
        ctx_obj = getattr(ctx, "obj", None)
        if isinstance(ctx_obj, dict):
            argv_cand = ctx_obj.get("argv")
            if isinstance(argv_cand, list | tuple):
                return [str(x) for x in argv_cand]

    from_stack = _extract_from_stack()
    if from_stack is not None:
        return from_stack

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


class FindfmtCommand(typer.core.TyperCommand):
    """Custom TyperCommand routing help output through interactive pager on TTY."""

    @override
    def format_help(self, ctx: _click.Context, formatter: _click.HelpFormatter) -> None:
        """Format and page command help text when appropriate.

        Args:
            ctx: Active Click context.
            formatter: Click help formatter.
        """
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            super().format_help(ctx, formatter)

        content = buf.getvalue()
        if content:
            display_with_pager(content, ctx=ctx)
        elif formatter.getvalue():
            display_with_pager(formatter.getvalue(), ctx=ctx)
