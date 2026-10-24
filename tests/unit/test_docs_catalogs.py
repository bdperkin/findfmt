"""Keep the Sphinx documentation translation catalogs in step with their sources (#469)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SOURCE = DOCS / "source"
LOCALE = SOURCE / "locale"
# Catalog references ("#: ../../source/index.md:1") are relative to the gettext builder output.
GETTEXT_DIR = DOCS / "_build" / "gettext"
REMOVED_STRINGS = ("--dereference", "(`-L`) is active")
# "path:12" or "path:docstring of module.name:3" (autodoc); capture the source file path.
REFERENCE = re.compile(r"(\S+?\.(?:md|rst|py|txt|toml)):")


def _languages() -> list[str]:
    """Return the documentation languages configured in docs/Makefile."""
    match = re.search(
        r"^LANGUAGES\s*\?=\s*(.+)$",
        (DOCS / "Makefile").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert match, "docs/Makefile must define LANGUAGES"
    return str(match.group(1)).split()


def _doc_pages() -> set[str]:
    """Return Sphinx docnames (paths without suffix) for every documentation page."""
    return {
        path.relative_to(SOURCE).with_suffix("").as_posix()
        for path in SOURCE.rglob("*")
        if path.suffix in {".md", ".rst"}
        and not {"locale", "_build", "_static", "_templates"} & set(path.relative_to(SOURCE).parts)
    }


def _catalogs(language: str) -> list[Path]:
    """Return the documentation .po catalogs for one language."""
    return sorted((LOCALE / language / "LC_MESSAGES").rglob("*.po"))


def _active_entries(po_file: Path) -> list[tuple[list[str], str]]:
    """Return ``(references, msgid)`` for each non-obsolete entry, skipping the header."""
    entries: list[tuple[list[str], str]] = []
    refs: list[str] = []
    msgid: list[str] | None = None
    for line in [*po_file.read_text(encoding="utf-8").splitlines(), ""]:
        if line.startswith("#:"):
            refs.extend(REFERENCE.findall(line[2:]))
        elif line.startswith('msgid "'):
            msgid = [line[7:-1]]
        elif line.startswith('"') and msgid is not None:
            msgid.append(line[1:-1])
        elif line.startswith("msgstr") or not line.strip():
            if msgid is not None and "".join(msgid):
                entries.append((refs, "".join(msgid)))

            refs, msgid = ([] if not line.strip() else refs), None

    return entries


@pytest.mark.parametrize("language", _languages())
def test_every_doc_page_has_a_catalog(language: str) -> None:
    """Every documentation page has a translation catalog in every configured language."""
    catalogs = {
        path.relative_to(LOCALE / language / "LC_MESSAGES").with_suffix("").as_posix()
        for path in _catalogs(language)
    }
    missing = sorted(_doc_pages() - catalogs)
    assert not missing, (
        f"{language}: pages without a catalog (run `make -C docs intl-update`): {missing}"
    )


@pytest.mark.parametrize("language", _languages())
def test_catalog_references_point_to_existing_sources(language: str) -> None:
    """Every active catalog entry references a documentation source file that still exists."""
    dangling = sorted(
        {
            f"{po.relative_to(LOCALE)}: {ref}"
            for po in _catalogs(language)
            for refs, _ in _active_entries(po)
            for ref in refs
            if not (GETTEXT_DIR / ref).resolve().is_file()
        },
    )
    assert not dangling, f"{language}: references to missing sources: {dangling[:10]}"


@pytest.mark.parametrize("language", _languages())
def test_catalogs_do_not_translate_removed_flags(language: str) -> None:
    """No active entry still carries option text that #467 removed from the documentation."""
    stale = sorted(
        f"{po.relative_to(LOCALE)}: {msgid[:60]}"
        for po in _catalogs(language)
        for _, msgid in _active_entries(po)
        if any(text in msgid for text in REMOVED_STRINGS)
    )
    assert not stale, f"{language}: catalogs still contain removed text: {stale}"
