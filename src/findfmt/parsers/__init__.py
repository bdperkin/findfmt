"""External listing parsers and stream ingestion package."""

from __future__ import annotations

from findfmt.exceptions import ParserError
from findfmt.parsers.engine import (
    classify_file_offline,
    detect_input_format,
    ingest_from_file,
)
from findfmt.parsers.flat_parser import ParsedEntry, parse_flat_listing
from findfmt.parsers.symlink_parser import parse_symlink_target
from findfmt.parsers.tab_parser import parse_tab_outline

__all__ = [
    "ParsedEntry",
    "ParserError",
    "classify_file_offline",
    "detect_input_format",
    "ingest_from_file",
    "parse_flat_listing",
    "parse_symlink_target",
    "parse_tab_outline",
]
