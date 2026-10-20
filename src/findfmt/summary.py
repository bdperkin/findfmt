"""CLI summary reporting and tag argument normalization helpers."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

from findfmt.formatters.visual import format_summary_panel
from findfmt.terminal import get_console

if TYPE_CHECKING:
    from collections import Counter
    from collections.abc import Sequence

__all__ = [
    "parse_tag_arguments",
    "write_summary",
]


def parse_tag_arguments(tag_args: Sequence[str] | None) -> frozenset[str]:
    """Parse repeatable or comma-delimited tag arguments into a normalized frozenset.

    Args:
        tag_args: Raw arguments provided to tag filter flags.

    Returns:
        frozenset of lowercase tag strings.
    """
    if not tag_args:
        return frozenset[str]()

    result: set[str] = set()
    for arg in tag_args:
        for tag in arg.split(","):
            cleaned = tag.strip().lower()
            if cleaned:
                result.add(cleaned)

    return frozenset(result)


def write_summary(
    match_count: int,
    tag_counter: Counter[str],
    *,
    total_bytes: int | None = None,
    stream: TextIO | None = None,
    force_color: bool | None = None,
) -> None:
    """Write Rich-formatted execution summary to stderr.

    Args:
        match_count: Total number of files matched.
        tag_counter: Frequency counter of tags matched.
        total_bytes: Optional total size in bytes of matched files.
        stream: Optional target output stream (defaults to sys.stderr).
        force_color: Explicit color enable override flag.
    """
    target = stream if stream is not None else sys.stderr
    panel = format_summary_panel(match_count, tag_counter, total_bytes=total_bytes)
    console = get_console(target, force_color=force_color)
    console.print(panel)
