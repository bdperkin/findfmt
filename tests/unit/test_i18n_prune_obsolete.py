"""Tests for pruning untranslated obsolete catalog entries in tools/i18n.py (#494)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from tools import i18n
from tools.i18n import prune_untranslated_obsolete, update_catalogs

CATALOG = """\
msgid ""
msgstr ""
"Language: fr\\n"

msgid "Active"
msgstr ""

msgid "Translated"
msgstr "Traduit"

#~ msgid "KB"
#~ msgstr "Ko"

#~ msgid "Gone"
#~ msgstr ""

#~ msgid ""
#~ "Usage: findfmt [OPTIONS]\\n"
#~ "long manual text\\n"
#~ msgstr ""

#~ msgid "Long translation"
#~ msgstr ""
#~ "Une traduction "
#~ "sur deux lignes"

#, fuzzy
#~ msgid "One file"
#~ msgid_plural "%d files"
#~ msgstr[0] ""
#~ msgstr[1] ""
"""


def _write(tmp_path: Path) -> Path:
    po = tmp_path / "findfmt.po"
    po.write_text(CATALOG, encoding="utf-8")
    return po


def test_prune_drops_only_untranslated_obsolete_entries(tmp_path: Path) -> None:
    """Untranslated obsolete entries go; translations and active entries stay."""
    po = _write(tmp_path)
    assert prune_untranslated_obsolete(po) == 3
    text = po.read_text(encoding="utf-8")
    assert "Gone" not in text
    assert "long manual text" not in text
    assert "%d files" not in text
    for kept in ('msgid "Active"', 'msgstr "Traduit"', '#~ msgstr "Ko"', "sur deux lignes"):
        assert kept in text


def test_prune_is_idempotent(tmp_path: Path) -> None:
    """A second pass removes nothing and leaves the file unchanged."""
    po = _write(tmp_path)
    prune_untranslated_obsolete(po)
    once = po.read_text(encoding="utf-8")
    assert prune_untranslated_obsolete(po) == 0
    assert po.read_text(encoding="utf-8") == once


@pytest.mark.parametrize("tool", ["pybabel", "msgmerge"])
def test_update_catalogs_prunes_after_updating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
) -> None:
    """Both update paths (pybabel and msgmerge) prune untranslated obsolete entries."""
    locale_dir = tmp_path / "locale"
    po = locale_dir / "fr" / "LC_MESSAGES" / "findfmt.po"
    po.parent.mkdir(parents=True)
    po.write_text(CATALOG, encoding="utf-8")
    pot = tmp_path / "findfmt.pot"
    pot.write_text('msgid ""\nmsgstr ""\n', encoding="utf-8")
    monkeypatch.setattr(
        i18n.shutil,
        "which",
        lambda name: f"/usr/bin/{tool}" if name == tool else None,
    )
    monkeypatch.setattr(
        i18n.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(args=[], returncode=0),
    )
    assert update_catalogs(pot_file=pot, locale_dir=locale_dir) == 0
    text = po.read_text(encoding="utf-8")
    assert "Gone" not in text
    assert '#~ msgstr "Ko"' in text
