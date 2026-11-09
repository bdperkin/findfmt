"""Catalog drift/completeness verification and automated AI translation sync pipeline."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from tools.i18n_translate import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_TEMPERATURE,
    SUPPORTED_BACKENDS,
    TranslationConfig,
    is_untranslated_block,
    translate_catalogs,
    update_block_msgstrs,
)
from tools.i18n_validation import parse_po_catalog, validate_catalogs

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Sequence

__all__ = [
    "COMPLETE_LOCALES",
    "add_translation_cli_args",
    "check_catalog_completeness",
    "find_fuzzy_entries",
    "populate_english_identity",
    "scan_source_msgids",
    "sync_pending_locales",
    "validate_and_check_catalogs",
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOMAIN = "findfmt"
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "src" / "findfmt"
DEFAULT_LOCALE_DIR = PROJECT_ROOT / "src" / "findfmt" / "locale"
COMPLETE_LOCALES: tuple[str, ...] = ("en", "es")
_NGETTEXT_MIN_ARGS = 2


def _extract_call_msgid(node: ast.Call) -> str | None:
    """Return the singular `msgid` string literal from a `_()` or `ngettext()` AST call node."""
    if not isinstance(node.func, ast.Name) or not node.args:
        return None

    first_arg = node.args[0]
    if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
        return None

    if node.func.id == "_":
        return first_arg.value

    if node.func.id == "ngettext" and len(node.args) >= _NGETTEXT_MIN_ARGS:
        return first_arg.value

    return None


def scan_source_msgids(source_dir: Path = DEFAULT_SOURCE_DIR) -> set[str]:
    """Scan Python source files under `source_dir` for `_()` and `ngettext()` message IDs."""
    msgids: set[str] = set()
    for py_path in sorted(source_dir.rglob("*.py")):
        tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                msgid = _extract_call_msgid(node)
                if msgid is not None and msgid != "":
                    msgids.add(msgid)

    return msgids


def find_fuzzy_entries(po_text: str) -> list[tuple[int, str]]:
    """Return `(line_number, msgid)` for active PO blocks carrying a `#, fuzzy` flag."""
    fuzzy: list[tuple[int, str]] = []
    for block in po_text.split("\n\n"):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines or any(ln.startswith("#~") for ln in lines):
            continue

        is_fuzzy = any(
            ln.startswith("#,") and "fuzzy" in {tok.strip() for tok in ln[2:].split(",")}
            for ln in lines
        )
        if is_fuzzy:
            fuzzy.extend((entry.line_number, entry.msgid) for entry in parse_po_catalog(block))

    return fuzzy


def _check_pot_and_po_sync(
    locale_dir: Path,
    domain: str,
    source_dir: Path | None,
) -> list[str]:
    """Check that `findfmt.pot` matches Python sources and `.po` catalogs match `findfmt.pot`."""
    pot_path = locale_dir / f"{domain}.pot"
    if not pot_path.is_file():
        return []

    errors: list[str] = []
    pot_ids = {e.msgid for e in parse_po_catalog(pot_path.read_text(encoding="utf-8"))}
    if source_dir is not None and source_dir.is_dir():
        missing_in_pot = sorted(scan_source_msgids(source_dir) - pot_ids)
        errors.extend(
            f"{pot_path}: missing source string {msgid!r} "
            "(run 'uv run python -m tools.i18n extract')"
            for msgid in missing_in_pot
        )

    for po_path in sorted(locale_dir.glob(f"*/LC_MESSAGES/{domain}.po")):
        po_ids = {e.msgid for e in parse_po_catalog(po_path.read_text(encoding="utf-8"))}
        missing_in_po = sorted(pot_ids - po_ids)
        errors.extend(
            f"{po_path}: missing POT entry {msgid!r} (run 'uv run python -m tools.i18n update')"
            for msgid in missing_in_po
        )

    return errors


def check_catalog_completeness(
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    domain: str = DEFAULT_DOMAIN,
    *,
    source_dir: Path | None = None,
    complete_locales: Sequence[str] = COMPLETE_LOCALES,
) -> list[str]:
    """Verify POT/PO synchronization and 100% non-fuzzy translation for `complete_locales`."""
    active_source = (
        source_dir
        if source_dir is not None
        else (DEFAULT_SOURCE_DIR if locale_dir.resolve() == DEFAULT_LOCALE_DIR.resolve() else None)
    )
    errors = _check_pot_and_po_sync(locale_dir, domain, active_source)
    for loc in complete_locales:
        po_path = locale_dir / loc / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.is_file():
            continue

        po_text = po_path.read_text(encoding="utf-8")
        for entry in parse_po_catalog(po_text):
            if not entry.msgstrs or any(s == "" for s in entry.msgstrs):
                errors.append(
                    f"{po_path}:{entry.line_number}: untranslated entry {entry.msgid!r} "
                    f"in completed locale '{loc}' (run 'uv run python -m tools.i18n sync')",
                )

        for line_no, msgid in find_fuzzy_entries(po_text):
            errors.append(
                f"{po_path}:{line_no}: fuzzy entry {msgid!r} in completed locale '{loc}'",
            )

    return errors


def validate_and_check_catalogs(
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    domain: str = DEFAULT_DOMAIN,
    *,
    source_dir: Path | None = None,
    complete_locales: Sequence[str] = COMPLETE_LOCALES,
) -> int:
    """Validate format placeholders/markup and check catalog completeness for `locale_dir`."""
    code = validate_catalogs(locale_dir, domain)
    completeness_errors = check_catalog_completeness(
        locale_dir,
        domain,
        source_dir=source_dir,
        complete_locales=complete_locales,
    )
    if completeness_errors:
        for err in completeness_errors:
            sys.stderr.write(f"Validation error: {err}\n")

        return 1

    return code


def populate_english_identity(
    po_path: Path,
    sanitize_fn: Callable[[Path], None] | None = None,
) -> int:
    """Populate untranslated entries in the canonical `en` catalog with identity `msgid` strings."""
    if not po_path.is_file():
        return 0

    blocks = po_path.read_text(encoding="utf-8").split("\n\n")
    updated = 0
    for idx, blk in enumerate(blocks):
        entry = is_untranslated_block(blk)
        if entry is None:
            continue

        is_pl = entry.msgid_plural is not None
        msgstrs = (entry.msgid, entry.msgid_plural or entry.msgid) if is_pl else (entry.msgid,)
        blocks[idx] = update_block_msgstrs(blk, msgstrs, is_plural=is_pl)
        updated += 1

    if updated > 0:
        po_path.write_text("\n\n".join(blocks), encoding="utf-8")
        if sanitize_fn is not None:
            sanitize_fn(po_path)

    return updated


def add_translation_cli_args(parser: argparse.ArgumentParser) -> None:
    """Attach shared AI translation flags (`--all`, `--backend`, `--model`, etc.) to `parser`."""
    parser.add_argument("--all", dest="all_locales", action="store_true", help="All locales.")
    parser.add_argument("--backend", choices=SUPPORTED_BACKENDS, default="openai", help="Backend.")
    parser.add_argument("--model", default=None, help="Optional LLM model override.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Batch size.")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="Temp.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying files.")


def sync_pending_locales(
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    domain: str = DEFAULT_DOMAIN,
    *,
    all_locales: bool = False,
    complete_locales: Sequence[str] = COMPLETE_LOCALES,
    config: TranslationConfig | None = None,
) -> int:
    """Fill `en` identity strings and AI-translate pending entries in target locales."""
    cfg = config or TranslationConfig()
    if not cfg.dry_run:
        en_po = locale_dir / "en" / "LC_MESSAGES" / f"{domain}.po"
        populate_english_identity(en_po, sanitize_fn=cfg.sanitize_fn)

    target_locales = (
        [
            p.parent.parent.name
            for p in sorted(locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"))
            if p.parent.parent.name != "en"
        ]
        if all_locales
        else [loc for loc in complete_locales if loc != "en"]
    )
    for loc in target_locales:
        po_path = locale_dir / loc / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.is_file():
            continue

        has_pending = any(
            is_untranslated_block(blk) is not None
            for blk in po_path.read_text(encoding="utf-8").split("\n\n")
        )
        if has_pending:
            tr_code = translate_catalogs(loc, locale_dir=locale_dir, domain=domain, config=cfg)
            if tr_code != 0:
                return tr_code

    return 0
