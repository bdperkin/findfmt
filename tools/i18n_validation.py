"""Placeholder and markup validation and masking utilities for gettext PO catalogs."""

from __future__ import annotations

import ast
import re
import string
import sys
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_FORMATTER = string.Formatter()
_PRINTF_SPEC_PATTERN = (
    r"%%|%(?:\([a-zA-Z_]\w*\))?[#0 +\-]?(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlL]?[diouxXeEfFgGcrsab]"
)
_RICH_STYLE_WORDS = (
    r"bold|dim|italic|underline|blink|reverse|strike|red|green|yellow|blue|magenta|cyan|white"
)
_RICH_TAG_PATTERN = rf"\[(?:/[a-z_ ]*|(?=(?:{_RICH_STYLE_WORDS})\b)[a-z_ ]+)\]"

_PRINTF_RE = re.compile(_PRINTF_SPEC_PATTERN)
_RICH_TAG_RE = re.compile(_RICH_TAG_PATTERN)
_MASK_TARGET_RE = re.compile(
    rf"(?P<esc>\{{\{{|\}}\}}|%%)|(?P<token>\{{[^{{}}]+\}}|{_PRINTF_SPEC_PATTERN}|{_RICH_TAG_PATTERN})",
)
_MASK_TOKEN_RE = re.compile(r"__PH_\d+__")
_MSGSTR_PLURAL_RE = re.compile(r"^msgstr\[(\d+)\]\s+(.*)$")


@dataclass(frozen=True)
class PoCatalogEntry:
    """Parsed gettext PO entry with source strings, translations, and line number."""

    msgid: str
    msgid_plural: str | None
    msgstrs: tuple[str, ...]
    line_number: int = 1


def _unescape_po_str(escaped: str) -> str:
    """Unescape a double-quoted PO string literal."""
    stripped = escaped.strip()
    if not (stripped.startswith('"') and stripped.endswith('"')):
        return stripped

    try:
        return str(ast.literal_eval(stripped))
    except (ValueError, SyntaxError):
        return stripped.strip('"')


class _CatalogParser:
    """State machine for parsing active entries from a gettext PO catalog."""

    def __init__(self) -> None:
        self.entries: list[PoCatalogEntry] = []
        self._field: str | int | None = None
        self._msgid: str = ""
        self._msgid_plural: str | None = None
        self._msgstrs: dict[int, str] = {}
        self._line: int = 1

    def flush(self) -> None:
        """Finalize and append the active PO entry if non-header."""
        if self._field is not None and self._msgid:
            ordered = tuple(self._msgstrs[k] for k in sorted(self._msgstrs))
            self.entries.append(
                PoCatalogEntry(self._msgid, self._msgid_plural, ordered, self._line),
            )

        self._field = None
        self._msgid = ""
        self._msgid_plural = None
        self._msgstrs = {}

    def _append_continuation(self, val: str) -> None:
        if self._field == "msgid":
            self._msgid += val
        elif self._field == "msgid_plural" and self._msgid_plural is not None:
            self._msgid_plural += val
        elif isinstance(self._field, int):
            self._msgstrs[self._field] = self._msgstrs.get(self._field, "") + val

    def feed(self, line_no: int, line: str) -> None:
        """Process one stripped, non-comment line from a PO file."""
        if line.startswith("msgid "):
            self.flush()
            self._line = line_no
            self._field = "msgid"
            self._msgid = _unescape_po_str(line[6:])
        elif line.startswith("msgid_plural "):
            self._field = "msgid_plural"
            self._msgid_plural = _unescape_po_str(line[13:])
        elif line.startswith("msgstr "):
            self._field = 0
            self._msgstrs[0] = _unescape_po_str(line[7:])
        elif (match := _MSGSTR_PLURAL_RE.match(line)) is not None:
            idx = int(match.group(1))
            self._field = idx
            self._msgstrs[idx] = _unescape_po_str(match.group(2))
        elif line.startswith('"') and line.endswith('"'):
            self._append_continuation(_unescape_po_str(line))


def parse_po_catalog(po_text: str) -> list[PoCatalogEntry]:
    """Parse all non-header, non-obsolete entries from PO file text."""
    parser = _CatalogParser()
    for line_no, raw_line in enumerate(po_text.splitlines(), start=1):
        line = raw_line.strip()
        if line and not line.startswith("#"):
            parser.feed(line_no, line)

    parser.flush()
    return parser.entries


def extract_brace_placeholders(text: str) -> set[str]:
    """Extract Python brace format field names from text."""
    placeholders: set[str] = set()
    for _literal, field_name, format_spec, _conversion in _FORMATTER.parse(text):
        if field_name is None:
            continue

        stripped_name = field_name.strip()
        if not stripped_name:
            msg = "Anonymous empty placeholder '{}' is not permitted in translatable strings"
            raise ValueError(msg)

        if format_spec is not None and format_spec != "":
            for _lit, sub_field, _spec, _conv in _FORMATTER.parse(format_spec):
                if sub_field is not None and sub_field.strip():
                    placeholders.add(sub_field.strip())

        placeholders.add(stripped_name)

    return placeholders


def extract_printf_placeholders(text: str) -> list[str]:
    """Extract printf-style format specifiers (excluding escaped `%%`) in order."""
    return [m.group(0) for m in _PRINTF_RE.finditer(text) if m.group(0) != "%%"]


def extract_rich_tags(text: str) -> list[str]:
    """Extract Rich console style markup tags (e.g. `[bold]`, `[cyan]`, `[/]`)."""
    return [m.group(0) for m in _RICH_TAG_RE.finditer(text)]


def _are_rich_tags_balanced(tags: list[str]) -> bool:
    """Return True if every opening Rich style tag is closed by a closing tag."""
    depth = 0
    for tag in tags:
        if tag.startswith("[/"):
            depth -= 1
            if depth < 0:
                return False
        else:
            depth += 1

    return depth == 0


def mask_placeholders(text: str) -> tuple[str, dict[str, str]]:
    """Replace format placeholders and Rich markup tags with invariant `__PH_N__` tokens."""
    extract_brace_placeholders(text)
    mapping: dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        esc = match.group("esc")
        if esc is not None:
            return str(esc)

        token = f"__PH_{len(mapping)}__"
        mapping[token] = str(match.group("token"))
        return token

    return _MASK_TARGET_RE.sub(_replace, text), mapping


def unmask_placeholders(translated_text: str, token_map: dict[str, str]) -> str:
    """Restore original placeholders and Rich tags from invariant `__PH_N__` tokens."""
    missing = [token for token in token_map if token not in translated_text]
    if missing:
        raise ValueError(f"Missing placeholder token(s) in translated text: {missing}")  # noqa: EM102, TRY003

    found_tokens = [m.group(0) for m in _MASK_TOKEN_RE.finditer(translated_text)]
    unknown = [token for token in found_tokens if token not in token_map]
    if unknown:
        raise ValueError(f"Unknown placeholder token(s) in translated text: {unknown}")  # noqa: EM102, TRY003

    if Counter(found_tokens) != Counter(token_map.keys()):
        raise ValueError(f"Duplicate placeholder token(s) in translated text: {found_tokens}")  # noqa: EM102, TRY003

    for token, original in token_map.items():
        translated_text = translated_text.replace(token, original)

    return translated_text


def _validate_brace_parity(expected: set[str], msgstr: str) -> list[str]:
    """Validate brace syntax, placeholder set parity, and trial formatting on msgstr."""
    try:
        actual = extract_brace_placeholders(msgstr)
    except ValueError as err:
        return [f"Malformed brace syntax in msgstr: {err}"]

    errors: list[str] = []
    missing = sorted(expected - actual)
    if missing:
        errors.append(f"Missing brace placeholder(s) {missing} in msgstr")

    extra = sorted(actual - expected)
    if extra:
        errors.append(f"Unexpected brace placeholder(s) {extra} in msgstr")

    if not errors and expected:
        dummy_kwargs = {name.split(".")[0].split("[")[0]: "1" for name in expected}
        try:
            msgstr.format(**dummy_kwargs)
        except (KeyError, ValueError, IndexError) as err:
            errors.append(f"Runtime string formatting failed on msgstr: {err}")

    return errors


def _validate_printf_and_rich(msgid: str, msgstr: str, msgid_plural: str | None) -> list[str]:
    """Validate printf specifiers and Rich console markup tags on msgstr."""
    errors: list[str] = []
    exp_pf = extract_printf_placeholders(msgid)
    pl_pf = extract_printf_placeholders(msgid_plural) if msgid_plural is not None else exp_pf
    act_pf = extract_printf_placeholders(msgstr)
    if act_pf not in (exp_pf, pl_pf):
        errors.append(f"Printf placeholder mismatch: expected {exp_pf}, got {act_pf}")

    exp_rich = extract_rich_tags(msgid)
    pl_rich = extract_rich_tags(msgid_plural) if msgid_plural is not None else exp_rich
    act_rich = extract_rich_tags(msgstr)
    if Counter(act_rich) not in (Counter(exp_rich), Counter(pl_rich)):
        errors.append(f"Rich markup tag mismatch: expected {exp_rich}, got {act_rich}")
    elif act_rich and not _are_rich_tags_balanced(act_rich):
        errors.append(f"Unbalanced Rich markup tags in msgstr: {act_rich}")

    return errors


def validate_message_pair(msgid: str, msgstr: str, *, msgid_plural: str | None = None) -> list[str]:
    """Validate format placeholders and Rich markup tags for a single (msgid, msgstr) pair."""
    if not msgid or not msgstr:
        return []

    expected = extract_brace_placeholders(msgid)
    if msgid_plural is not None:
        expected |= extract_brace_placeholders(msgid_plural)

    return [
        *_validate_brace_parity(expected, msgstr),
        *_validate_printf_and_rich(msgid, msgstr, msgid_plural),
    ]


def validate_po_file(po_path: Path) -> list[str]:
    """Validate all translated entries in a gettext .po file."""
    if not po_path.is_file():
        return [f"{po_path}: PO file does not exist"]

    entries = parse_po_catalog(po_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for entry in entries:
        for idx, msgstr in enumerate(entry.msgstrs):
            pair_errs = validate_message_pair(entry.msgid, msgstr, msgid_plural=entry.msgid_plural)
            suffix = f"[{idx}]" if entry.msgid_plural is not None else ""
            errors.extend(
                f"{po_path}:{entry.line_number}: msgstr{suffix} ({entry.msgid!r}): {err}"
                for err in pair_errs
            )

    return errors


def validate_catalogs(locale_dir: Path, domain: str = "findfmt") -> int:
    """Validate all locale PO catalogs under `locale_dir` and report errors to stderr."""
    all_errors = [
        err
        for po_path in sorted(locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"))
        for err in validate_po_file(po_path)
    ]
    if all_errors:
        for err in all_errors:
            sys.stderr.write(f"Validation error: {err}\n")

        return 1

    return 0
