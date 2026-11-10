"""Deprecated compatibility shim for ``findfmt.cli.entrypoints`` (#453)."""

from __future__ import annotations

import importlib
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from findfmt.cli.entrypoints import (
        main,
        main_findfilefmt,
        main_findfilemime,
        main_findfiles,
        main_findfmt0,
        main_findshebang,
        main_findsummary,
    )

__all__ = [
    "main",
    "main_findfilefmt",
    "main_findfilemime",
    "main_findfiles",
    "main_findfmt0",
    "main_findshebang",
    "main_findsummary",
]


def __getattr__(name: str) -> object:
    """Lazily resolve attributes from ``findfmt.cli.entrypoints`` with a DeprecationWarning."""
    entrypoints = importlib.import_module("findfmt.cli.entrypoints")
    attr = getattr(entrypoints, name)
    warnings.warn(
        f"'findfmt.entrypoints.{name}' is deprecated and will be removed in v2.0.0; "
        f"import '{name}' from 'findfmt.cli.entrypoints' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return attr
