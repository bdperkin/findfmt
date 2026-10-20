"""Shared control-sequence pattern for terminal text and URI sanitization."""

from __future__ import annotations

import re

__all__ = ["ANSI_ESCAPE_RE"]

ANSI_ESCAPE_RE = re.compile(
    r"""
    \x1b\[[0-?]*[ -/]*[@-~]                  # 7-bit CSI sequence
    | \x1b\][^\x07\x1b]*(?:\x07|\x1b\\)        # 7-bit OSC sequence
    | \x1b[ -/]*[0-~]                        # 7-bit Fe/Fs/Fp sequence
    | \x9b[0-?]*[ -/]*[@-~]                  # 8-bit C1 CSI sequence
    # Consume unfinished OSC payloads too, avoiding retries at each nested \x9d.
    | \x9d[^\x07\x1b\x9c]*(?:\x07|\x1b\\|\x9c)?   # 8-bit C1 OSC sequence
    """,
    re.VERBOSE,
)
