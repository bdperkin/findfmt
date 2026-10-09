"""Terminal control, interactive paging, and ANSI color management."""

from __future__ import annotations

import os
import re
import shutil
import sys
from typing import TYPE_CHECKING, TextIO

from rich.console import Console

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rich.pager import Pager

__all__ = [
    "PagerController",
    "get_console",
    "get_terminal_height",
    "is_color_enabled",
    "should_use_pager",
    "strip_ansi",
]

_ANSI_REGEX = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text string.

    Args:
        text: Input string potentially containing ANSI escapes.

    Returns:
        Clean string free of ANSI escape sequences.
    """
    return _ANSI_REGEX.sub("", text)


def is_color_enabled(
    stream: TextIO | None = None,
    *,
    env: Mapping[str, str] | None = None,
    force_color: bool | None = None,
) -> bool:
    """Evaluate whether ANSI color sequences should be emitted.

    Precedence order:
    1. If force_color is explicitly set, its boolean value is honored.
    2. If NO_COLOR is present and non-empty, color is disabled.
    3. If CLICOLOR_FORCE is set and non-zero, color is forced.
    4. If CLICOLOR is set to "0", color is disabled.
    5. Otherwise, color is enabled only if stream is an interactive TTY.

    Args:
        stream: Target output text stream (defaults to sys.stdout).
        env: Environment variable mapping override.
        force_color: Explicit color enable override flag.

    Returns:
        True if colors should be emitted, False otherwise.
    """
    if force_color is not None:
        return force_color

    active_env = os.environ if env is None else env
    no_color_val = active_env.get("NO_COLOR")
    if no_color_val is not None and no_color_val != "":
        return False

    force_val = active_env.get("CLICOLOR_FORCE")
    if force_val is not None and force_val not in ("", "0"):
        return True

    clicolor_val = active_env.get("CLICOLOR")
    if clicolor_val == "0":
        return False

    target = stream if stream is not None else sys.stdout
    return bool(getattr(target, "isatty", lambda: False)())


def get_console(
    stream: TextIO | None = None,
    *,
    env: Mapping[str, str] | None = None,
    width: int | None = None,
    force_color: bool | None = None,
) -> Console:
    """Construct a Rich Console honoring environment variables and TTY settings.

    Args:
        stream: Target output text stream (defaults to sys.stdout).
        env: Environment variable mapping override.
        width: Optional terminal output column width override.
        force_color: Explicit color enable override flag.

    Returns:
        Configured Rich Console instance.
    """
    target = stream if stream is not None else sys.stdout
    color_on = force_color if force_color is not None else is_color_enabled(target, env=env)
    is_tty = getattr(target, "isatty", lambda: False)()

    if not color_on:
        return Console(
            file=target,
            no_color=True,
            force_terminal=False,
            width=width,
            highlight=False,
        )

    if is_tty:
        return Console(
            file=target,
            no_color=False,
            width=width,
            highlight=False,
        )

    return Console(
        file=target,
        no_color=False,
        force_terminal=True,
        color_system="standard",
        width=width,
        highlight=False,
    )


def get_terminal_height(fallback: int = 24) -> int:
    """Return current terminal height in lines with fallback.

    Args:
        fallback: Fallback row count when terminal size query fails.

    Returns:
        Detected terminal height row count.
    """
    try:
        height = shutil.get_terminal_size(fallback=(80, fallback)).lines
    except (OSError, ValueError):  # pragma: no cover
        return fallback
    else:
        return height if height > 0 else fallback


def should_use_pager(
    output_lines: int,
    *,
    pager: bool | None = None,
    stream: TextIO | None = None,
    term_height: int | None = None,
) -> bool:
    """Determine whether output should be routed through an interactive pager.

    Args:
        output_lines: Number of lines in the rendered output.
        pager: Explicit CLI override (True=force, False=disable, None=auto).
        stream: Target output stream (defaults to sys.stdout).
        term_height: Terminal height override (defaults to detected terminal height).

    Returns:
        True if interactive pager should be activated, False otherwise.
    """
    if pager is False:
        return False

    target = stream if stream is not None else sys.stdout
    if not bool(getattr(target, "isatty", lambda: False)()):
        return False

    if pager is True:
        return True

    height = term_height if term_height is not None else get_terminal_height()
    return output_lines > height


class PagerController:
    """Controller for interactive terminal paging and TTY/color handling."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        pager: bool | None = None,
        stream: TextIO | None = None,
        term_height: int | None = None,
        console: Console | None = None,
        pager_impl: Pager | None = None,
        env: Mapping[str, str] | None = None,
        force_color: bool | None = None,
    ) -> None:
        """Initialize PagerController.

        Args:
            pager: Pager override flag (True=force, False=disable, None=auto).
            stream: Target output text stream (defaults to sys.stdout).
            term_height: Terminal height override for testing.
            console: Optional pre-configured Rich Console.
            pager_impl: Optional custom Rich Pager instance.
            env: Optional environment mapping for color resolution.
            force_color: Explicit color enable override flag.
        """
        self.pager = pager
        self.stream = stream if stream is not None else sys.stdout
        self.term_height = term_height
        self.pager_impl = pager_impl
        self.env = env
        self.force_color = force_color
        self.console = (
            console
            if console is not None
            else get_console(self.stream, env=env, force_color=force_color)
        )

    def should_page(self, line_count: int) -> bool:
        """Determine whether output with line_count should be routed through a pager.

        Args:
            line_count: Number of lines in output.

        Returns:
            True if pager should be invoked, False otherwise.
        """
        return should_use_pager(
            line_count,
            pager=self.pager,
            stream=self.stream,
            term_height=self.term_height,
        )

    def display(self, content: str) -> None:
        """Route formatted content to pager or write directly to target stream.

        Args:
            content: Formatted output string to display.
        """
        color_active = is_color_enabled(
            self.stream,
            env=self.env,
            force_color=self.force_color,
        )
        out = content if color_active else strip_ansi(content)
        lines = len(out.splitlines())
        if self.should_page(lines):
            with self.console.pager(pager=self.pager_impl, styles=True):
                self.console.print(out, end="", markup=False, highlight=False)
        else:
            self.stream.write(out)
            self.stream.flush()
