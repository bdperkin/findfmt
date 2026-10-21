"""Unit tests for internationalization (i18n) runtime engine and pluralization rules."""

from __future__ import annotations

import gettext
import struct
from pathlib import Path

import pytest

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


def test_slavic_three_form_plural_logic(tmp_path: Path) -> None:
    """Verify Slavic 3-form plural logic for 1 file, 2-4 files, 5-10 files, and 21 files."""
    header = (
        "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
        "n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);"
    )
    forms = ["1 файл", "2-4 файла", "5-10 файлов"]
    _create_plural_catalog(tmp_path, "ru", header, forms)

    with override_locale("ru", localedir=tmp_path):
        # Form 0: ending in 1 except 11
        for n in (1, 21, 31, 41, 101, 121, 201):
            assert ngettext("file", "files", n) == "1 файл"

        # Form 1: ending in 2..4 except 12..14
        for n in (2, 3, 4, 22, 23, 24, 102, 103, 104):
            assert ngettext("file", "files", n) == "2-4 файла"

        # Form 2: 0, 5..10, 11..19, 20, 25..30, 100, 111, 112
        for n in (0, 5, 8, 10, 11, 14, 19, 20, 25, 99, 100, 105, 111, 112, 1000):
            assert ngettext("file", "files", n) == "5-10 файлов"


def test_arabic_six_form_plural_logic(tmp_path: Path) -> None:
    """Verify Arabic 6-form plural logic (zero, one, two, few, many, other)."""
    header = (
        "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : "
        "n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5);"
    )
    forms = ["zero", "one", "two", "few", "many", "other"]
    _create_plural_catalog(tmp_path, "ar", header, forms)

    with override_locale("ar", localedir=tmp_path):
        assert ngettext("file", "files", 0) == "zero"
        assert ngettext("file", "files", 1) == "one"
        assert ngettext("file", "files", 2) == "two"

        # Form 3 (few): n%100 in 3..10
        for n in (3, 4, 5, 8, 10, 103, 104, 105, 110, 203):
            assert ngettext("file", "files", n) == "few"

        # Form 4 (many): n%100 in 11..99
        for n in (11, 14, 19, 20, 21, 22, 24, 25, 99, 111, 112, 121, 199):
            assert ngettext("file", "files", n) == "many"

        # Form 5 (other): 100, 101, 102, 200, 1000, 1001
        for n in (100, 101, 102, 200, 1000, 1001, 1002):
            assert ngettext("file", "files", n) == "other"


def test_french_and_portuguese_zero_one_singular_logic(tmp_path: Path) -> None:
    """Verify French and Brazilian Portuguese rule where 0 and 1 are singular."""
    header = "nplurals=2; plural=(n > 1);"
    _create_plural_catalog(tmp_path, "fr", header, ["fichier", "fichiers"])
    _create_plural_catalog(tmp_path, "pt_BR", header, ["arquivo", "arquivos"])

    for lang, (sg, pl) in (("fr", ("fichier", "fichiers")), ("pt_BR", ("arquivo", "arquivos"))):
        with override_locale(lang, localedir=tmp_path):
            assert ngettext("file", "files", 0) == sg
            assert ngettext("file", "files", 1) == sg
            for n in (2, 3, 4, 5, 10, 11, 19, 21, 24, 100, 101):
                assert ngettext("file", "files", n) == pl


def test_cjk_and_indonesian_single_form_plural_logic(tmp_path: Path) -> None:
    """Verify CJK and Indonesian single-form plural rules where no inflection exists."""
    header = "nplurals=1; plural=0;"
    _create_plural_catalog(tmp_path, "ja", header, ["ファイル"])
    _create_plural_catalog(tmp_path, "id", header, ["berkas"])

    for lang, word in (("ja", "ファイル"), ("id", "berkas")):
        with override_locale(lang, localedir=tmp_path):
            for n in (0, 1, 2, 3, 4, 5, 10, 11, 19, 21, 24, 100, 101):
                assert ngettext("file", "files", n) == word


@pytest.mark.parametrize(
    ("rule_name", "header", "forms", "expected_indices"),
    [
        (
            "polish_3_form",
            (
                "nplurals=3; plural=(n==1 ? 0 : "
                "n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);"
            ),
            ["plik", "pliki", "plikow"],
            {
                1: 0,
                2: 1,
                3: 1,
                4: 1,
                22: 1,
                24: 1,
                102: 1,
                0: 2,
                5: 2,
                10: 2,
                11: 2,
                19: 2,
                20: 2,
                21: 2,
                25: 2,
                100: 2,
                101: 2,
            },
        ),
        (
            "czech_3_form",
            "nplurals=3; plural=(n==1 ? 0 : (n>=2 && n<=4) ? 1 : 2);",
            ["soubor", "soubory", "souboru"],
            {
                1: 0,
                2: 1,
                3: 1,
                4: 1,
                0: 2,
                5: 2,
                10: 2,
                11: 2,
                19: 2,
                20: 2,
                21: 2,
                22: 2,
                24: 2,
                100: 2,
                101: 2,
            },
        ),
        (
            "slovenian_4_form",
            "nplurals=4; plural=(n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3);",
            ["ena", "dve", "tri", "ostalo"],
            {
                1: 0,
                101: 0,
                2: 1,
                102: 1,
                3: 2,
                4: 2,
                103: 2,
                104: 2,
                0: 3,
                5: 3,
                10: 3,
                11: 3,
                19: 3,
                20: 3,
                21: 3,
                22: 3,
                24: 3,
                100: 3,
                105: 3,
            },
        ),
    ],
)
def test_extended_plural_families_boundary_matrix(
    tmp_path: Path,
    rule_name: str,
    header: str,
    forms: list[str],
    expected_indices: dict[int, int],
) -> None:
    """Verify boundary values on Polish, Czech, and Slovenian plural families."""
    _create_plural_catalog(tmp_path, rule_name, header, forms)
    with override_locale(rule_name, localedir=tmp_path):
        for n, expected_idx in expected_indices.items():
            expected_str = forms[expected_idx]
            assert ngettext("file", "files", n) == expected_str


def test_real_findfmt_catalogs_pluralization() -> None:
    """Verify built-in findfmt message catalogs plural rules for en, fr, de, es, ja."""
    with override_locale("en"):
        sg_en = "[bold]Matched file:[/] [cyan]{count}[/]"
        pl_en = "[bold]Matched files:[/] [cyan]{count}[/]"
        assert ngettext(sg_en, pl_en, 1) == "[bold]Matched file:[/] [cyan]{count}[/]"
        assert ngettext(sg_en, pl_en, 0) == "[bold]Matched files:[/] [cyan]{count}[/]"
        assert ngettext(sg_en, pl_en, 2) == "[bold]Matched files:[/] [cyan]{count}[/]"
        assert _("Total size:") == "Total size:"
        assert _("Path") == "Path"

    with override_locale("en_US"):
        assert ngettext(sg_en, pl_en, 1) == "[bold]Matched file:[/] [cyan]{count}[/]"
        assert ngettext(sg_en, pl_en, 2) == "[bold]Matched files:[/] [cyan]{count}[/]"
        assert _("Inode") == "Inode"

    with override_locale("fr"):
        sg_fr = "[bold]Matched file:[/] [cyan]{count}[/]"
        pl_fr = "[bold]Matched files:[/] [cyan]{count}[/]"
        assert ngettext(sg_fr, pl_fr, 0).startswith("[bold]Fichier")
        assert ngettext(sg_fr, pl_fr, 1).startswith("[bold]Fichier")
        assert ngettext(sg_fr, pl_fr, 2).startswith("[bold]Fichiers")
        assert ngettext(sg_fr, pl_fr, 5).startswith("[bold]Fichiers")

    with override_locale("de"):
        sg_de = "[bold]Matched file:[/] [cyan]{count}[/]"
        pl_de = "[bold]Matched files:[/] [cyan]{count}[/]"
        assert ngettext(sg_de, pl_de, 1).startswith("[bold]Passende Datei")
        assert ngettext(sg_de, pl_de, 0).startswith("[bold]Passende Dateien")
        assert ngettext(sg_de, pl_de, 2).startswith("[bold]Passende Dateien")

    with override_locale("es"):
        sg_es = "[bold]Matched file:[/] [cyan]{count}[/]"
        pl_es = "[bold]Matched files:[/] [cyan]{count}[/]"
        assert ngettext(sg_es, pl_es, 1).startswith("[bold]Archivo")
        assert ngettext(sg_es, pl_es, 0).startswith("[bold]Archivos")
        assert ngettext(sg_es, pl_es, 2).startswith("[bold]Archivos")

    with override_locale("ja"):
        sg_ja = "[bold]Matched file:[/] [cyan]{count}[/]"
        pl_ja = "[bold]Matched files:[/] [cyan]{count}[/]"
        assert ngettext(sg_ja, pl_ja, 0).startswith("[bold]一致したファイル")
        assert ngettext(sg_ja, pl_ja, 1).startswith("[bold]一致したファイル")
        assert ngettext(sg_ja, pl_ja, 5).startswith("[bold]一致したファイル")


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
