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
from findfmt.metadata import extract_metadata, format_permissions
from findfmt.models import FileInfo, SortKey, TraversalConfig
from findfmt.sizes import (
    calculate_accumulated_sizes,
    format_size,
    format_size_binary,
    format_size_bytes,
    format_size_si,
)
from findfmt.traversal import find_files, traverse_directory

__version__ = get_version()

__all__ = [
    "FileInfo",
    "Formatter",
    "OutputFormat",
    "SortKey",
    "TraversalConfig",
    "__version__",
    "calculate_accumulated_sizes",
    "classify_file",
    "extract_metadata",
    "find_files",
    "format_permissions",
    "format_size",
    "format_size_binary",
    "format_size_bytes",
    "format_size_si",
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
