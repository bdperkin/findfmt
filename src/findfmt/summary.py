"""Deprecated compatibility shim for ``findfmt.cli.summary`` (#453)."""

from __future__ import annotations

import importlib
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from findfmt.cli.summary import (
        parse_tag_arguments,
        write_summary,
    )

__all__ = [
    "parse_tag_arguments",
    "write_summary",
]


def __getattr__(name: str) -> object:
    """Lazily resolve attributes from ``findfmt.cli.summary`` with a DeprecationWarning."""
    summary = importlib.import_module("findfmt.cli.summary")
    attr = getattr(summary, name)
    warnings.warn(
        f"'findfmt.summary.{name}' is deprecated and will be removed in v2.0.0; "
        f"import '{name}' from 'findfmt.cli.summary' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return attr
