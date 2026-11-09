"""Unit tests for gettext catalog drift/completeness checks and auto-AI sync (#566)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from tools.i18n import main
from tools.i18n_sync import (
    COMPLETE_LOCALES,
    check_catalog_completeness,
    find_fuzzy_entries,
    populate_english_identity,
    scan_source_msgids,
    sync_pending_locales,
    validate_and_check_catalogs,
)
from tools.i18n_translate import TranslationConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCALE_DIR = PROJECT_ROOT / "src" / "findfmt" / "locale"


def test_scan_source_msgids_real_and_synthetic(tmp_path: Path) -> None:
    """Verify AST scanner extracts `_()` and `ngettext()` literals and ignores non-literals."""
    real_ids = scan_source_msgids()
    assert len(real_ids) >= 140
    assert "Total size:" in real_ids
    assert "[bold]Matched file:[/] [cyan]{count}[/]" in real_ids

    sample_py = tmp_path / "sample.py"
    sample_py.write_text(
        "from findfmt.i18n import _, ngettext\n"
        'x = _("Hello {name}")\n'
        'y = ngettext("One item", "{n} items", count)\n'
        "z = _(dynamic_var)\n"
        'w = ngettext("Only one arg")\n'
        'other = some_func("Ignored")\n'
        'obj.method("Also ignored")\n',
        encoding="utf-8",
    )
    assert scan_source_msgids(tmp_path) == {"Hello {name}", "One item"}


def test_find_fuzzy_entries() -> None:
    """Verify fuzzy flag detection ignores obsolete blocks and non-fuzzy flags."""
    po_text = (
        'msgid ""\n'
        'msgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        "#, python-brace-format\n"
        'msgid "Clean {name}"\n'
        'msgstr "Limpio {name}"\n\n'
        "#, fuzzy, python-brace-format\n"
        'msgid "Fuzzy {name}"\n'
        'msgstr "Borroso {name}"\n\n'
        "#, fuzzy\n"
        '#~ msgid "Obsolete fuzzy"\n'
        '#~ msgstr "Obsoleto"\n'
    )
    fuzzy = find_fuzzy_entries(po_text)
    assert len(fuzzy) == 1
    assert fuzzy[0][1] == "Fuzzy {name}"


def test_shipped_catalogs_pass_completeness_and_sync() -> None:
    """Verify shipped catalogs pass AST source sync and COMPLETE_LOCALES checks."""
    assert COMPLETE_LOCALES == ("de", "en", "es", "fr")
    assert check_catalog_completeness(LOCALE_DIR) == []
    assert validate_and_check_catalogs(LOCALE_DIR) == 0


def test_check_catalog_completeness_detects_drift_untranslated_and_fuzzy(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify completeness check flags unextracted source strings, missing POs, and fuzzy/empty."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "mod.py").write_text(
        'from findfmt.i18n import _\nmsg1 = _("In POT")\nmsg2 = _("Missing from POT")\n',
        encoding="utf-8",
    )

    loc_dir = tmp_path / "locale"
    loc_dir.mkdir()
    (loc_dir / "findfmt.pot").write_text(
        'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        'msgid "In POT"\nmsgstr ""\n\n'
        'msgid "Also in POT"\nmsgstr ""\n',
        encoding="utf-8",
    )

    es_po = loc_dir / "es" / "LC_MESSAGES" / "findfmt.po"
    es_po.parent.mkdir(parents=True)
    es_po.write_text(
        'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        'msgid "In POT"\nmsgstr ""\n\n'
        "#, fuzzy\n"
        'msgid "Fuzzy item"\nmsgstr "Borroso"\n',
        encoding="utf-8",
    )

    errors = check_catalog_completeness(
        loc_dir,
        source_dir=src_dir,
        complete_locales=("en", "es"),
    )
    assert any("missing source string 'Missing from POT'" in e for e in errors)
    assert any("missing POT entry 'Also in POT'" in e for e in errors)
    assert any("untranslated entry 'In POT' in completed locale 'es'" in e for e in errors)
    assert any("fuzzy entry 'Fuzzy item' in completed locale 'es'" in e for e in errors)

    assert validate_and_check_catalogs(loc_dir, source_dir=src_dir) == 1
    captured = capsys.readouterr()
    assert "Validation error:" in captured.err


def test_populate_english_identity(tmp_path: Path) -> None:
    """Verify populate_english_identity fills singular and plural English entries."""
    missing_po = tmp_path / "missing.po"
    assert populate_english_identity(missing_po) == 0

    en_po = tmp_path / "en" / "LC_MESSAGES" / "findfmt.po"
    en_po.parent.mkdir(parents=True)
    en_po.write_text(
        'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        'msgid "Already done"\nmsgstr "Already done"\n\n'
        'msgid "New singular"\nmsgstr ""\n\n'
        'msgid "One file"\nmsgid_plural "{count} files"\nmsgstr[0] ""\nmsgstr[1] ""\n',
        encoding="utf-8",
    )

    sanitized: list[Path] = []
    updated = populate_english_identity(en_po, sanitize_fn=sanitized.append)
    assert updated == 2
    assert sanitized == [en_po]

    # Second run is a no-op because all entries are now populated
    assert populate_english_identity(en_po) == 0
    text = en_po.read_text(encoding="utf-8")
    assert 'msgstr "New singular"' in text
    assert 'msgstr[0] "One file"' in text
    assert 'msgstr[1] "{count} files"' in text


def test_sync_pending_locales_and_cli_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify sync_pending_locales and `tools/i18n.py sync` orchestrate en fill and AI translate."""
    loc_dir = tmp_path / "locale"
    loc_dir.mkdir()

    en_po = loc_dir / "en" / "LC_MESSAGES" / "findfmt.po"
    en_po.parent.mkdir(parents=True)
    en_po.write_text(
        'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        'msgid "Hello {name}"\nmsgstr ""\n',
        encoding="utf-8",
    )

    es_po = loc_dir / "es" / "LC_MESSAGES" / "findfmt.po"
    es_po.parent.mkdir(parents=True)
    es_po.write_text(
        'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        'msgid "Hello {name}"\nmsgstr ""\n',
        encoding="utf-8",
    )

    # 1. Dry-run mode previews without modifying en or es catalogs
    dry_cfg = TranslationConfig(backend="mock", dry_run=True)
    assert sync_pending_locales(loc_dir, config=dry_cfg) == 0
    assert 'msgstr ""' in en_po.read_text(encoding="utf-8")

    # 2. Full sync populates en and translates es with mock AI
    cfg = TranslationConfig(backend="mock")
    assert sync_pending_locales(loc_dir, all_locales=True, config=cfg) == 0
    assert 'msgstr "Hello {name}"' in en_po.read_text(encoding="utf-8")
    assert 'msgstr "[es] Hello {name}"' in es_po.read_text(encoding="utf-8")

    # 3. CLI `sync` subcommand invokes extract, update, sync_pending_locales, and compile
    monkeypatch.setattr("tools.i18n.extract_messages", MagicMock(return_value=0))
    monkeypatch.setattr("tools.i18n.update_catalogs", MagicMock(return_value=0))
    mock_compile = MagicMock(return_value=0)
    monkeypatch.setattr("tools.i18n.compile_catalogs", mock_compile)
    assert main(["sync", "--localedir", str(loc_dir), "--backend", "mock", "--dry-run"]) == 0
    assert mock_compile.call_count == 0
    assert main(["sync", "--localedir", str(loc_dir), "--backend", "mock"]) == 0
    assert mock_compile.call_count == 1
