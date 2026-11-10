"""Deprecated compatibility shim for ``findfmt.cli.terminal`` (#453)."""

from __future__ import annotations

import importlib
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from findfmt.cli.terminal import (
        PagerController,
        get_console,
        get_terminal_height,
        is_color_enabled,
        should_use_pager,
        strip_ansi,
    )

__all__ = [
    "PagerController",
    "get_console",
    "get_terminal_height",
    "is_color_enabled",
    "should_use_pager",
    "strip_ansi",
]


def __getattr__(name: str) -> object:
    """Lazily resolve attributes from ``findfmt.cli.terminal`` with a DeprecationWarning."""
    terminal = importlib.import_module("findfmt.cli.terminal")
    attr = getattr(terminal, name)
    warnings.warn(
        f"'findfmt.terminal.{name}' is deprecated and will be removed in v2.0.0; "
        f"import '{name}' from 'findfmt.cli.terminal' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return attr
