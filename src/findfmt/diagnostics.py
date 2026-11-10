"""Deprecated compatibility shim for ``findfmt.cli.diagnostics`` (#453)."""

from __future__ import annotations

import importlib
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from findfmt.cli.diagnostics import (
        diagnostics_callback,
        get_diagnostics,
        get_git_version,
        get_version,
        show_config_callback,
        version_callback,
    )

__all__ = [
    "diagnostics_callback",
    "get_diagnostics",
    "get_git_version",
    "get_version",
    "show_config_callback",
    "version_callback",
]


def __getattr__(name: str) -> object:
    """Lazily resolve attributes from ``findfmt.cli.diagnostics`` with a DeprecationWarning."""
    diagnostics = importlib.import_module("findfmt.cli.diagnostics")
    attr = getattr(diagnostics, name)
    warnings.warn(
        f"'findfmt.diagnostics.{name}' is deprecated and will be removed in v2.0.0; "
        f"import '{name}' from 'findfmt.cli.diagnostics' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return attr
