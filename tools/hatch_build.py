"""Hatchling custom build hook for findfmt message catalog compilation."""

from __future__ import annotations

import ast
import contextlib
import re
import struct
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override  # pragma: no cover

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

try:
    from babel.messages import mofile, pofile
except ImportError:
    mofile = None  # type: ignore[assignment]
    pofile = None  # type: ignore[assignment]


def _unescape_po_str(escaped: str) -> str:
    """Safely unescape a quoted PO string token."""
    stripped = escaped.strip()
    if not (stripped.startswith('"') and stripped.endswith('"')):
        return stripped

    try:
        evaluated = ast.literal_eval(stripped)
        return str(evaluated)
    except (ValueError, SyntaxError):
        return stripped.strip('"')


class _PoEntryBuilder:
    """Helper class to accumulate PO message entries with low complexity."""

    def __init__(self) -> None:
        self.entries: dict[str, str] = {}
        self.current_key: str | None = None
        self.current_msgid: str = ""
        self.current_msgstr: str = ""

    def flush(self) -> None:
        """Store the current pending message entry."""
        if self.current_msgid and self.current_msgstr:
            self.entries[self.current_msgid] = self.current_msgstr

        self.current_msgid = ""
        self.current_msgstr = ""
        self.current_key = None

    def _append_string(self, line: str) -> None:
        val = _unescape_po_str(line)
        if self.current_key in ("msgid", "msgid_plural"):
            self.current_msgid += val
        elif self.current_key == "msgstr":
            self.current_msgstr += val

    def feed_line(self, line: str) -> None:
        """Process a non-empty, non-comment line."""
        if line.startswith("msgid "):
            self.flush()
            self.current_key = "msgid"
            self.current_msgid = _unescape_po_str(line[6:])
        elif line.startswith("msgid_plural "):
            self.current_key = "msgid_plural"
            self.current_msgid += "\x00" + _unescape_po_str(line[13:])
        elif line.startswith(("msgstr ", "msgstr[0] ")):
            self.current_key = "msgstr"
            space_idx = line.find(" ")
            self.current_msgstr = _unescape_po_str(line[space_idx + 1 :])
        elif re.match(r"^msgstr\[\d+\]\s+", line):
            self.current_key = "msgstr"
            space_idx = line.find(" ")
            self.current_msgstr += "\x00" + _unescape_po_str(line[space_idx + 1 :])
        elif line.startswith('"') and line.endswith('"'):
            self._append_string(line)


def _parse_po_entries(po_text: str) -> dict[str, str]:
    """Parse entries from PO file content into msgid -> msgstr mapping.

    Args:
        po_text: Raw content of .po file.

    Returns:
        Mapping of msgid to msgstr.
    """
    builder = _PoEntryBuilder()
    for raw_line in po_text.splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            builder.feed_line(line)

    builder.flush()
    return builder.entries


def _generate_mo_bytes(entries: dict[str, str]) -> bytes:
    """Generate binary GNU gettext .mo file payload in pure Python.

    Args:
        entries: Mapping of msgid to msgstr.

    Returns:
        Bytes representing a valid binary .mo catalog.
    """
    items = sorted(entries.items())
    num_strings = len(items)

    orig_tab_offset = 28
    trans_tab_offset = orig_tab_offset + num_strings * 8
    strings_offset = trans_tab_offset + num_strings * 8

    orig_tab: list[tuple[int, int]] = []
    trans_tab: list[tuple[int, int]] = []
    data = bytearray()

    for orig, _msgstr in items:
        orig_bytes = orig.encode("utf-8") + b"\x00"
        orig_tab.append((len(orig_bytes) - 1, strings_offset + len(data)))
        data.extend(orig_bytes)

    for _orig, trans in items:
        trans_bytes = trans.encode("utf-8") + b"\x00"
        trans_tab.append((len(trans_bytes) - 1, strings_offset + len(data)))
        data.extend(trans_bytes)

    header = struct.pack(
        "<Iiiiiii",
        0x950412DE,
        0,
        num_strings,
        orig_tab_offset,
        trans_tab_offset,
        0,
        0,
    )

    orig_bytes_tab = bytearray()
    for length, offset in orig_tab:
        orig_bytes_tab.extend(struct.pack("<ii", length, offset))

    trans_bytes_tab = bytearray()
    for length, offset in trans_tab:
        trans_bytes_tab.extend(struct.pack("<ii", length, offset))

    return header + orig_bytes_tab + trans_bytes_tab + bytes(data)


def _compile_po_pure_python(po_path: Path, mo_path: Path) -> None:
    """Compile a .po file to .mo using pure Python fallback."""
    text = po_path.read_text(encoding="utf-8")
    entries = _parse_po_entries(text)
    mo_bytes = _generate_mo_bytes(entries)
    mo_path.parent.mkdir(parents=True, exist_ok=True)
    mo_path.write_bytes(mo_bytes)


def compile_po_to_mo(po_path: Path, mo_path: Path) -> None:
    """Compile a gettext .po file to a binary .mo catalog.

    Attempts to use Babel first; falls back to pure-Python implementation
    if Babel is unavailable or compilation encounters an error.

    Args:
        po_path: Path to source .po file.
        mo_path: Path to target .mo file.
    """
    if pofile is not None and mofile is not None:
        try:
            with po_path.open("r", encoding="utf-8") as f_in:
                catalog = pofile.read_po(f_in)

            mo_path.parent.mkdir(parents=True, exist_ok=True)
            with mo_path.open("wb") as f_out:
                mofile.write_mo(f_out, catalog)
        except (OSError, ValueError):
            pass
        else:
            return

    _compile_po_pure_python(po_path, mo_path)


class CatalogBuildHook(BuildHookInterface[Any]):
    """Custom Hatchling build hook that compiles gettext .po catalogs to .mo."""

    PLUGIN_NAME = "custom"

    @override
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Compile all .po catalogs found in src/findfmt/locale into binary .mo files."""
        locale_root = Path(self.root) / "src" / "findfmt" / "locale"
        if not locale_root.is_dir():
            return

        mo_artifacts: list[str] = []
        for po_path in locale_root.glob("*/LC_MESSAGES/*.po"):
            mo_path = po_path.with_suffix(".mo")
            compile_po_to_mo(po_path, mo_path)
            mo_artifacts.append(str(mo_path))

        build_data.setdefault("artifacts", []).extend(mo_artifacts)

    @override
    def clean(self, versions: list[str]) -> None:
        """Remove compiled .mo files when cleaning build targets."""
        locale_root = Path(self.root) / "src" / "findfmt" / "locale"
        if not locale_root.is_dir():
            return

        for mo_path in locale_root.glob("*/LC_MESSAGES/*.mo"):
            with contextlib.suppress(OSError):
                mo_path.unlink()
