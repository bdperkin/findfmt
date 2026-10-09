"""findfmt: A .gitignore-aware file discovery and classification suite."""

from __future__ import annotations

from findfmt.classifier import classify_file, get_known_tags
from findfmt.cli import get_version, main
from findfmt.entrypoints import (
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
)
from findfmt.formatters import Formatter, OutputFormat, get_formatter
from findfmt.models import FileInfo, TraversalConfig
from findfmt.traversal import find_files, traverse_directory

__version__ = get_version()

__all__ = [
    "FileInfo",
    "Formatter",
    "OutputFormat",
    "TraversalConfig",
    "__version__",
    "classify_file",
    "find_files",
    "get_formatter",
    "get_known_tags",
    "get_version",
    "main",
    "main_findfilefmt",
    "main_findfilemime",
    "main_findfiles",
    "main_findfmt0",
    "main_findshebang",
    "main_findsummary",
    "traverse_directory",
]
