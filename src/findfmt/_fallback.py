"""Pure-Python fallback engine re-exporting directory traversal and file classification (#578)."""

from __future__ import annotations

from findfmt.classifier import classify_file
from findfmt.traversal.engine import find_files

__all__ = [
    "classify_file",
    "find_files",
]
