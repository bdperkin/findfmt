"""Unit tests for internationalization (i18n) runtime engine and pluralization rules."""

from __future__ import annotations

import gettext
import struct
from pathlib import Path

import pytest
from tools.i18n_validation import parse_po_catalog

from findfmt.i18n import (
    _,
    detect_locale,
    detect_locales,
    get_current_locale,
    get_current_translation,
    locale_callback,
    ngettext,
    override_locale,
    reset_locale,
    set_locale,
)


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
        "<7I",
        0x950412DE,  # magic
        0,  # format revision
        num_strings,
        orig_tab_offset,
        trans_tab_offset,
        0,  # hash table size
        0,  # hash table offset
    )

    tab1 = b"".join(struct.pack("<2I", length, offset) for length, offset in orig_tab)
    tab2 = b"".join(struct.pack("<2I", length, offset) for length, offset in trans_tab)

    return header + tab1 + tab2 + bytes(data)


def _create_plural_catalog(
    tmp_path: Path,
    lang: str,
    plural_header: str,
    forms: list[str],
) -> Path:
    """Create a temporary .mo catalog with custom plural forms header."""
    po_dir = tmp_path / lang / "LC_MESSAGES"
    po_dir.mkdir(parents=True, exist_ok=True)
    mo_path = po_dir / "findfmt.mo"

    mo_data = _generate_mo_bytes(
        {
            "": f"Content-Type: text/plain; charset=UTF-8\nPlural-Forms: {plural_header}\n",
            "file\x00files": "\x00".join(forms),
        },
    )
    mo_path.write_bytes(mo_data)
    return tmp_path


def test_detect_locale_posix_precedence() -> None:
    """Verify standard POSIX precedence order: LANGUAGE -> LC_ALL -> LC_MESSAGES -> LANG -> C."""
    env1 = {"LANGUAGE": "es_ES:es", "LC_ALL": "fr_FR", "LC_MESSAGES": "de_DE", "LANG": "it_IT"}
    assert detect_locale(env1) == "es_ES"

    env2 = {"LC_ALL": "fr_FR", "LC_MESSAGES": "de_DE", "LANG": "it_IT"}
    assert detect_locale(env2) == "fr_FR"

    env3 = {"LC_MESSAGES": "de_DE", "LANG": "it_IT"}
    assert detect_locale(env3) == "de_DE"

    env4 = {"LANG": "it_IT"}
    assert detect_locale(env4) == "it_IT"

    env5 = {"LANGUAGE": "", "LC_ALL": "", "LC_MESSAGES": "", "LANG": ""}
    assert detect_locale(env5) == "C"
    assert detect_locale({}) == "C"

    detected = detect_locale()
    assert isinstance(detected, str)
    assert len(detected) > 0


def test_detect_locales_deduplication_and_order() -> None:
    """Verify detect_locales handles colon-separated lists and deduplication."""
    env = {
        "LANGUAGE": "es_ES:es:es_ES",
        "LC_ALL": "fr_FR",
        "LC_MESSAGES": "de_DE",
        "LANG": "es",
    }
    locales = detect_locales(env)
    assert locales == ["es_ES", "es", "fr_FR", "de_DE"]
    assert detect_locales({}) == ["C"]

    active_locales = detect_locales()
    assert isinstance(active_locales, list)
    assert len(active_locales) >= 1


def test_get_current_locale_and_translation() -> None:
    """Verify get_current_locale and get_current_translation return active state."""
    with override_locale("C"):
        assert get_current_locale() == "C"
        trans = get_current_translation()
        assert isinstance(trans, gettext.NullTranslations)


def test_set_locale_explicit_c_and_posix() -> None:
    """Verify setting C or POSIX initializes NullTranslations without disk lookup."""
    assert set_locale("C") == "C"
    assert isinstance(get_current_translation(), gettext.NullTranslations)

    assert set_locale("POSIX") == "POSIX"
    assert isinstance(get_current_translation(), gettext.NullTranslations)


def test_set_locale_none_and_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify set_locale(None) and reset_locale detect from environment."""
    monkeypatch.setenv("LANGUAGE", "ja_JP")
    res = reset_locale()
    assert res == "ja_JP"
    assert get_current_locale() == "ja_JP"

    monkeypatch.delenv("LANGUAGE", raising=False)
    monkeypatch.setenv("LC_ALL", "C")
    assert reset_locale() == "C"


def test_override_locale_context_manager() -> None:
    """Verify override_locale temporarily modifies locale and restores original on exit."""
    set_locale("C")
    assert get_current_locale() == "C"

    with override_locale("fr_FR") as active:
        assert active == "fr_FR"
        assert get_current_locale() == "fr_FR"

    assert get_current_locale() == "C"

    def _raise_error() -> None:
        msg = "test error"
        raise RuntimeError(msg)

    with override_locale("de_DE"):
        assert get_current_locale() == "de_DE"
        with pytest.raises(RuntimeError, match="test error"):
            _raise_error()

    assert get_current_locale() == "C"


def test_locale_callback() -> None:
    """Verify Typer eager callback sets the active locale when given."""
    with override_locale("C"):
        assert locale_callback("es_ES") == "es_ES"
        assert get_current_locale() == "es_ES"
        assert locale_callback(None) is None
        assert get_current_locale() == "es_ES"


def test_gettext_and_ngettext_fallback() -> None:
    """Verify _ and ngettext work with English fallback when no catalog is present."""
    with override_locale("C"):
        assert _("Hello world") == "Hello world"
        assert ngettext("{n} file", "{n} files", 1) == "{n} file"
        assert ngettext("{n} file", "{n} files", 0) == "{n} files"
        assert ngettext("{n} file", "{n} files", 5) == "{n} files"


def test_catalog_translation_with_mo(tmp_path: Path) -> None:
    """Verify translation lookup using an active mock MO catalog."""
    _create_plural_catalog(
        tmp_path,
        "es",
        "nplurals=2; plural=(n != 1);",
        ["archivo", "archivos"],
    )
    with override_locale("es", localedir=tmp_path):
        assert _("Unknown message") == "Unknown message"
        assert ngettext("file", "files", 1) == "archivo"
        assert ngettext("file", "files", 2) == "archivos"


def test_detect_locale_empty_tokens() -> None:
    """Verify detect_locale skips empty and whitespace tokens in colon-separated variables."""
    env1 = {"LANGUAGE": " : : ", "LC_ALL": "es_ES"}
    assert detect_locale(env1) == "es_ES"

    env2 = {"LANGUAGE": "::", "LC_ALL": "  :  "}
    assert detect_locale(env2) == "C"


def test_set_locale_logs_or_raises_on_undecodable_catalog(tmp_path: Path) -> None:
    """Verify set_locale issues a warning and falls back when catalog has undecodable strings."""
    mo_path = tmp_path / "de" / "LC_MESSAGES" / "findfmt.mo"
    mo_path.parent.mkdir(parents=True, exist_ok=True)
    mo_bytes = _generate_mo_bytes({"size": "Größe"})
    mo_path.write_bytes(mo_bytes)

    with override_locale(None):
        with pytest.warns(UserWarning, match="Failed to load translation catalog"):
            active = set_locale("de", localedir=tmp_path)

        assert active == "de"
        assert get_current_translation().gettext("size") == "size"


def test_english_canonical_catalog_runtime() -> None:
    """Verify English (en) catalog loads GNUTranslations and handles overrides."""
    with override_locale("en") as loc:
        assert loc == "en"
        assert get_current_locale() == "en"
        trans = get_current_translation()
        assert isinstance(trans, gettext.GNUTranslations)
        assert _("not installed") == "not installed"
        assert _("not found") == "not found"
        assert _("Total size:") == "Total size:"
        for n in (0, 2, 5, 100):
            assert ngettext("file", "files", n) == "files"

        assert ngettext("file", "files", 1) == "file"


def test_german_canonical_catalog_runtime(tmp_path: Path) -> None:
    """Verify German (de) catalog coverage, compound nouns, umlauts/eszett, and plurals (#215)."""
    de_po_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "findfmt"
        / "locale"
        / "de"
        / "LC_MESSAGES"
        / "findfmt.po"
    )
    entries = parse_po_catalog(de_po_path.read_text(encoding="utf-8"))
    assert len(entries) >= 145
    assert all(e.msgstrs and all(bool(s) for s in e.msgstrs) for e in entries)

    with override_locale("de") as loc:
        assert loc == "de"
        assert get_current_locale() == "de"
        trans = get_current_translation()
        assert isinstance(trans, gettext.GNUTranslations)

        # Diagnostics and German compound nouns / umlauts / eszett
        assert _("not installed") == "nicht installiert"
        assert _("not found") == "nicht gefunden"
        assert _("none") == "keine"
        assert _("Total size:") == "Gesamtgröße:"
        assert _("Traversal Controls") == "Verzeichnisdurchlauf"
        assert _("Output Formatting") == "Ausgabeformatierung"

        err_msg = _("Error: Cannot specify both --dirsfirst and --filesfirst.")
        assert err_msg.startswith("Fehler:")
        assert "--dirsfirst" in err_msg

        # Pluralization rules: nplurals=2; plural=(n != 1);
        sg = "[bold]Matched file:[/] [cyan]{count}[/]"
        pl = "[bold]Matched files:[/] [cyan]{count}[/]"
        assert ngettext(sg, pl, 1) == "[bold]Passende Datei:[/] [cyan]{count}[/]"
        for n in (0, 2, 5, 100):
            assert ngettext(sg, pl, n) == "[bold]Passende Dateien:[/] [cyan]{count}[/]"

    mo_dir = tmp_path / "de" / "LC_MESSAGES"
    mo_dir.mkdir(parents=True, exist_ok=True)
    (mo_dir / "findfmt.mo").write_bytes(
        _generate_mo_bytes(
            {
                "": "Content-Type: text/plain; charset=UTF-8\n",
                "File size check": "Dateigrößenprüfung",
            },
        ),
    )
    with override_locale("de_DE.UTF-8", localedir=tmp_path):
        assert _("File size check") == "Dateigrößenprüfung"


def test_spanish_canonical_catalog_runtime(tmp_path: Path) -> None:
    """Verify Spanish (es) catalog coverage, gender agreement, inverted punctuation, and plurals."""
    es_po_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "findfmt"
        / "locale"
        / "es"
        / "LC_MESSAGES"
        / "findfmt.po"
    )
    entries = parse_po_catalog(es_po_path.read_text(encoding="utf-8"))
    assert len(entries) >= 145
    assert all(e.msgstrs and all(bool(s) for s in e.msgstrs) for e in entries)

    with override_locale("es") as loc:
        assert loc == "es"
        assert get_current_locale() == "es"
        trans = get_current_translation()
        assert isinstance(trans, gettext.GNUTranslations)

        # Gender agreement in diagnostics (identify -> masculino, Git -> masculino, Config -> fem.)
        assert _("not installed") == "no instalado"
        assert _("not found") == "no encontrado"
        assert _("none") == "ninguna"

        # Inverted exclamation marks in Spanish error reporting
        err_msg = _("Error: Cannot specify both --dirsfirst and --filesfirst.")
        assert err_msg.startswith("¡Error:")
        assert err_msg.endswith("!")

        # Pluralization rules: nplurals=2; plural=(n != 1);
        sg = "[bold]Matched file:[/] [cyan]{count}[/]"
        pl = "[bold]Matched files:[/] [cyan]{count}[/]"
        assert ngettext(sg, pl, 1) == "[bold]Archivo coincidente:[/] [cyan]{count}[/]"
        for n in (0, 2, 5, 100):
            assert ngettext(sg, pl, n) == "[bold]Archivos coincidentes:[/] [cyan]{count}[/]"

    # Verify inverted question and exclamation marks (¿, ¡) in custom error catalog
    mo_dir = tmp_path / "es" / "LC_MESSAGES"
    mo_dir.mkdir(parents=True, exist_ok=True)
    (mo_dir / "findfmt.mo").write_bytes(
        _generate_mo_bytes(
            {
                "": "Content-Type: text/plain; charset=UTF-8\n",
                "Retry operation?": "¿Reintentar la operación?",
                "Operation failed!": "¡Falló la operación!",
            },
        ),
    )
    with override_locale("es_ES.UTF-8", localedir=tmp_path):
        assert _("Retry operation?") == "¿Reintentar la operación?"
        assert _("Operation failed!") == "¡Falló la operación!"


def test_french_canonical_catalog_runtime(tmp_path: Path) -> None:
    """Verify French (fr) catalog coverage, non-breaking spaces, elisions, and plurals (#222)."""
    fr_po_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "findfmt"
        / "locale"
        / "fr"
        / "LC_MESSAGES"
        / "findfmt.po"
    )
    entries = parse_po_catalog(fr_po_path.read_text(encoding="utf-8"))
    assert len(entries) >= 145
    assert all(e.msgstrs and all(bool(s) for s in e.msgstrs) for e in entries)

    with override_locale("fr") as loc:
        assert loc == "fr"
        assert get_current_locale() == "fr"
        trans = get_current_translation()
        assert isinstance(trans, gettext.GNUTranslations)

        # Diagnostics, French typography (non-breaking space before ':'), and elisions
        assert _("not installed") == "non installé"
        assert _("not found") == "non trouvé"
        assert _("none") == "aucune"
        assert _("Total size:") == "Taille totale\u00a0:"
        assert _("[bold]Top tags:[/]") == "[bold]Principales balises\u00a0:[/]"
        assert _("Invert the active sort order.") == "Inverser l'ordre de tri actif."

        err_msg = _("Error: Cannot specify both --dirsfirst and --filesfirst.")
        assert err_msg.startswith("Erreur\u00a0:")
        assert "--dirsfirst" in err_msg

        # French pluralization rules: nplurals=2; plural=(n > 1); (0 and 1 are singular)
        sg = "[bold]Matched file:[/] [cyan]{count}[/]"
        pl = "[bold]Matched files:[/] [cyan]{count}[/]"
        for n in (0, 1):
            assert ngettext(sg, pl, n) == "[bold]Fichier correspondant\u00a0:[/] [cyan]{count}[/]"

        for n in (2, 5, 100):
            assert ngettext(sg, pl, n) == "[bold]Fichiers correspondants\u00a0:[/] [cyan]{count}[/]"

    mo_dir = tmp_path / "fr" / "LC_MESSAGES"
    mo_dir.mkdir(parents=True, exist_ok=True)
    (mo_dir / "findfmt.mo").write_bytes(
        _generate_mo_bytes(
            {
                "": "Content-Type: text/plain; charset=UTF-8\n",
                "Operation failed!": "Échec de l'opération\u00a0!",
            },
        ),
    )
    with override_locale("fr_FR.UTF-8", localedir=tmp_path):
        assert _("Operation failed!") == "Échec de l'opération\u00a0!"


def test_japanese_canonical_catalog_runtime(tmp_path: Path) -> None:
    """Verify Japanese (ja) catalog coverage, single-form plurals, and CJK/ASCII balance (#228)."""
    ja_po_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "findfmt"
        / "locale"
        / "ja"
        / "LC_MESSAGES"
        / "findfmt.po"
    )
    entries = parse_po_catalog(ja_po_path.read_text(encoding="utf-8"))
    assert len(entries) >= 145
    assert all(e.msgstrs and all(bool(s) for s in e.msgstrs) for e in entries)

    with override_locale("ja") as loc:
        assert loc == "ja"
        assert get_current_locale() == "ja"
        trans = get_current_translation()
        assert isinstance(trans, gettext.GNUTranslations)

        # Diagnostics, half-width ASCII units, and Japanese full-width prose
        assert _("not installed") == "未インストール"
        assert _("not found") == "見つかりません"
        assert _("none") == "なし"
        assert _("Total size:") == "合計サイズ:"
        assert _("[bold]Top tags:[/]") == "[bold]上位のタグ:[/]"
        assert _("KiB") == "KiB"
        assert _("MB") == "MB"

        err_msg = _("Error: Cannot specify both --dirsfirst and --filesfirst.")
        assert err_msg.startswith("エラー:")
        assert "--dirsfirst" in err_msg

        # Japanese single-form pluralization: nplurals=1; plural=0;
        sg = "[bold]Matched file:[/] [cyan]{count}[/]"
        pl = "[bold]Matched files:[/] [cyan]{count}[/]"
        for n in (0, 1, 2, 5, 100):
            assert ngettext(sg, pl, n) == "[bold]一致したファイル:[/] [cyan]{count}[/]"

    mo_dir = tmp_path / "ja" / "LC_MESSAGES"
    mo_dir.mkdir(parents=True, exist_ok=True)
    (mo_dir / "findfmt.mo").write_bytes(
        _generate_mo_bytes(
            {
                "": "Content-Type: text/plain; charset=UTF-8\n",
                "Operation failed!": "操作に失敗しました。",
            },
        ),
    )
    with override_locale("ja_JP.UTF-8", localedir=tmp_path):
        assert _("Operation failed!") == "操作に失敗しました。"
