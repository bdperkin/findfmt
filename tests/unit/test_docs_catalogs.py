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


def test_localization_platforms_adr_documentation() -> None:
    """Verify the managed localization platform evaluation and ADR guide (#307)."""
    adr_path = SOURCE / "guides" / "localization_platforms.md"
    assert adr_path.is_file(), "docs/source/guides/localization_platforms.md must exist"
    content = adr_path.read_text(encoding="utf-8")
    for required_term in (
        "POEditor",
        "Crowdin",
        "Localazy",
        "tools/i18n.py translate",
        "Architecture Decision Record (ADR)",
        "Option A",
        "Option B",
        "End-to-End AI Localization Runbook",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "_REGIONAL_DEFAULTS",
    ):
        assert required_term in content, f"Missing {required_term!r} in {adr_path}"

    guides_index = (SOURCE / "guides" / "index.md").read_text(encoding="utf-8")
    assert "localization_platforms" in guides_index


def test_multilingual_sphinx_ci_and_language_switcher() -> None:
    """Verify CI docs workflow, Makefile html-all, conf.py languages, and switcher (#233, #574)."""
    docs_workflow = (ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    assert "html-all" in docs_workflow

    makefile = (DOCS / "Makefile").read_text(encoding="utf-8")
    assert "html-all: html intl-build" in makefile
    assert "-A in_lang_subdir=1" in makefile

    expected_flags = {
        "en": ("English", "🇬🇧"),
        "de": ("Deutsch", "🇩🇪"),
        "es": ("Español", "🇪🇸"),
        "fr": ("Français", "🇫🇷"),
        "ja": ("日本語", "🇯🇵"),
    }
    conf_text = (SOURCE / "conf.py").read_text(encoding="utf-8")
    assert 'templates_path = ["_templates"]' in conf_text
    for lang in _languages():
        label, flag = expected_flags[lang]
        assert f'("{lang}", "{label}", "{flag}")' in conf_text
        svg_path = SOURCE / "_static" / "flags" / f"{lang}.svg"
        assert svg_path.is_file(), f"Missing flag SVG for {lang}: {svg_path}"
        assert "<svg" in svg_path.read_text(encoding="utf-8")

    switcher = (SOURCE / "_templates" / "sidebar" / "variant-selector.html").read_text(
        encoding="utf-8",
    )
    assert "findfmt-language-switcher" in switcher
    assert "findfmt-language-select" in switcher
    assert "findfmt-language-flag" in switcher
    assert "for code, label, flag in languages" in switcher
    assert "_static/flags/" in switcher
    assert 'aria-hidden="true"' in switcher
    assert "in_lang_subdir" in switcher

    custom_css = (SOURCE / "_static" / "custom.css").read_text(encoding="utf-8")
    assert ".findfmt-language-switcher" in custom_css
    assert ".findfmt-language-select" in custom_css
    assert ".findfmt-language-flag" in custom_css
