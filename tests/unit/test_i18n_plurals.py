"""Unit tests for gettext pluralization rules across plural rule families."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from findfmt.i18n import _, ngettext, override_locale
from tests.unit.test_i18n_runtime import _create_plural_catalog

if TYPE_CHECKING:
    from pathlib import Path


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
    ("rule_name", "header", "forms", "expected_groups"),
    [
        (
            "polish_3_form",
            (
                "nplurals=3; plural=(n==1 ? 0 : "
                "n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);"
            ),
            ["plik", "pliki", "plikow"],
            (((1,), 0), ((2, 3, 4, 22, 24, 102), 1), ((0, 5, 10, 11, 19, 20, 21, 25, 100, 101), 2)),
        ),
        (
            "czech_3_form",
            "nplurals=3; plural=(n==1 ? 0 : (n>=2 && n<=4) ? 1 : 2);",
            ["soubor", "soubory", "souboru"],
            (((1,), 0), ((2, 3, 4), 1), ((0, 5, 10, 11, 19, 20, 21, 22, 24, 100, 101), 2)),
        ),
        (
            "slovenian_4_form",
            "nplurals=4; plural=(n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3);",
            ["ena", "dve", "tri", "ostalo"],
            (
                ((1, 101), 0),
                ((2, 102), 1),
                ((3, 4, 103, 104), 2),
                ((0, 5, 10, 11, 19, 20, 21, 22, 24, 100, 105), 3),
            ),
        ),
    ],
)
def test_extended_plural_families_boundary_matrix(
    tmp_path: Path,
    rule_name: str,
    header: str,
    forms: list[str],
    expected_groups: tuple[tuple[tuple[int, ...], int], ...],
) -> None:
    """Verify boundary values on Polish, Czech, and Slovenian plural families."""
    _create_plural_catalog(tmp_path, rule_name, header, forms)
    with override_locale(rule_name, localedir=tmp_path):
        for counts, expected_idx in expected_groups:
            for n in counts:
                assert ngettext("file", "files", n) == forms[expected_idx]


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
