"""Command-line interface package for findfmt."""

from __future__ import annotations

from findfmt.cli.help import (
    get_help_all,
    help_all_callback,
    known_tags_callback,
)
from findfmt.cli.main import app, findfmt
from findfmt.cli.pager import FindfmtCommand, display_with_pager
from findfmt.cli.runner import execute_findfmt
from findfmt.diagnostics import (
    diagnostics_callback,
    get_diagnostics,
    get_git_version,
    get_version,
    version_callback,
)
from findfmt.entrypoints import (
    main,
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
)
from findfmt.terminal import PagerController

__all__ = [
    "FindfmtCommand",
    "PagerController",
    "app",
    "diagnostics_callback",
    "display_with_pager",
    "execute_findfmt",
    "findfmt",
    "get_diagnostics",
    "get_git_version",
    "get_help_all",
    "get_version",
    "help_all_callback",
    "known_tags_callback",
    "main",
    "main_findfilefmt",
    "main_findfilemime",
    "main_findfiles",
    "main_findfmt0",
    "main_findshebang",
    "main_findsummary",
    "version_callback",
]
