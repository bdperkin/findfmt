"""Unit tests for gettext catalog extraction, Hatchling build hook, and sphinx-intl."""

from __future__ import annotations

import gettext
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.hatch_build  # noqa: E402
import tools.i18n  # noqa: E402
from tools.hatch_build import (  # noqa: E402
    CatalogBuildHook,
    _compile_po_pure_python,
    _generate_mo_bytes,
    _parse_po_entries,
    _unescape_po_str,
    compile_po_to_mo,
)
from tools.i18n import (  # noqa: E402
    compile_catalogs,
    extract_messages,
    init_catalog,
    main,
    update_catalogs,
)

from findfmt.i18n import _, override_locale  # noqa: E402


def test_unescape_po_str() -> None:
    """Verify PO string unescaping handles valid, escaped, and unquoted strings."""
    assert _unescape_po_str('"hello"') == "hello"
    assert _unescape_po_str('"line1\\nline2"') == "line1\nline2"
    assert _unescape_po_str('"tab\\tspace"') == "tab\tspace"
    assert _unescape_po_str("unquoted") == "unquoted"
    assert _unescape_po_str('  "spaced"  ') == "spaced"
    # Fallback on invalid escape / syntax error
    assert _unescape_po_str('"unclosed') == '"unclosed'


def test_parse_po_entries() -> None:
    """Verify parsing PO content into message identifier and translation pairs."""
    po_text = """
    # Translation header or comment
    msgid ""
    msgstr ""
    "Content-Type: text/plain; charset=UTF-8\\n"

    # Comment 1
    msgid "hello"
    msgstr "hola"

    # Multi-line string
    msgid "multi"
    "line"
    msgstr "multi"
    "linea"

    # Plural form
    msgid "file"
    msgid_plural "files"
    msgstr[0] "archivo"
    msgstr[1] "archivos"
    """
    entries = _parse_po_entries(po_text)
    assert entries["hello"] == "hola"
    assert entries["multiline"] == "multilinea"
    assert entries["file\x00files"] == "archivo\x00archivos"


def test_generate_mo_bytes_and_pure_python_compile(tmp_path: Path) -> None:
    """Verify pure-Python MO binary generator creates valid gettext catalogs."""
    entries = {
        "apple": "manzana",
        "orange": "naranja",
    }
    mo_bytes = _generate_mo_bytes(entries)
    assert mo_bytes.startswith(b"\xde\x12\x04\x95")  # Little-endian magic

    po_file = tmp_path / "messages.po"
    mo_file = tmp_path / "messages.mo"

    po_file.write_text(
        'msgid "apple"\nmsgstr "manzana"\n\nmsgid "orange"\nmsgstr "naranja"\n',
        encoding="utf-8",
    )

    _compile_po_pure_python(po_file, mo_file)
    assert mo_file.is_file()

    with mo_file.open("rb") as f:
        catalog = gettext.GNUTranslations(f)

    assert catalog.gettext("apple") == "manzana"
    assert catalog.gettext("orange") == "naranja"
    assert catalog.gettext("banana") == "banana"


def test_compile_po_to_mo_babel_and_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify compile_po_to_mo functions with Babel and falls back gracefully."""
    po_file = tmp_path / "test.po"
    mo_file1 = tmp_path / "test1.mo"
    mo_file2 = tmp_path / "test2.mo"

    po_file.write_text(
        'msgid ""\nmsgstr ""\n\nmsgid "hello"\nmsgstr "bonjour"\n',
        encoding="utf-8",
    )

    # Standard path (uses Babel)
    compile_po_to_mo(po_file, mo_file1)
    assert mo_file1.is_file()

    # Trigger fallback by simulating ImportError
    monkeypatch.setitem(sys.modules, "babel.messages", None)
    compile_po_to_mo(po_file, mo_file2)
    assert mo_file2.is_file()

    with mo_file2.open("rb") as f:
        catalog = gettext.GNUTranslations(f)

    assert catalog.gettext("hello") == "bonjour"


def test_catalog_build_hook_initialize_and_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify CatalogBuildHook initializes catalogs and cleans them."""
    hook = CatalogBuildHook(
        root=str(tmp_path),
        config={},
        build_config=MagicMock(),
        metadata=MagicMock(),
        directory=str(tmp_path),
        target_name="wheel",
    )

    # Test initialize when locale root does not exist
    build_data: dict[str, list[str]] = {}
    hook.initialize("0.8.0", build_data)
    assert "artifacts" not in build_data

    # Test clean when locale root does not exist
    hook.clean([])

    # Create dummy locale catalog structure
    po_dir = tmp_path / "src" / "findfmt" / "locale" / "es" / "LC_MESSAGES"
    po_dir.mkdir(parents=True)
    po_file = po_dir / "findfmt.po"
    po_file.write_text('msgid "test"\nmsgstr "prueba"\n', encoding="utf-8")

    hook.initialize("0.8.0", build_data)
    mo_file = po_dir / "findfmt.mo"
    assert mo_file.is_file()
    assert str(mo_file) in build_data["artifacts"]

    # Test clean removes .mo files
    hook.clean([])
    assert not mo_file.is_file()

    # Test clean error handling when unlink fails
    mo_file.touch()
    monkeypatch.setattr(Path, "unlink", MagicMock(side_effect=OSError("Permission denied")))
    hook.clean([])  # Should not raise exception


def test_tools_i18n_extract_messages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify extract_messages with pybabel, xgettext, and failure fallback."""
    pot_file = tmp_path / "findfmt.pot"
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "sample.py").write_text('_("hello")\n', encoding="utf-8")

    # 1. pybabel path
    mock_run = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/" + cmd if cmd == "pybabel" else None)
    assert extract_messages(source_dir=src_dir, pot_file=pot_file) == 0

    # 2. xgettext path
    monkeypatch.setattr(
        "shutil.which",
        lambda cmd: "/usr/bin/" + cmd if cmd == "xgettext" else None,
    )
    assert extract_messages(source_dir=src_dir, pot_file=pot_file) == 0

    # 3. Neither found
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    assert extract_messages(source_dir=src_dir, pot_file=pot_file) == 1


def test_tools_i18n_init_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify init_catalog with pybabel, msginit, and fallback."""
    pot_file = tmp_path / "findfmt.pot"
    locale_dir = tmp_path / "locale"

    # Missing POT file error
    assert init_catalog("fr", pot_file=pot_file, locale_dir=locale_dir) == 1

    pot_file.write_text('msgid ""\nmsgstr ""\n"Language: \\n"\n', encoding="utf-8")

    mock_run = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(subprocess, "run", mock_run)

    # 1. pybabel path
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/" + cmd if cmd == "pybabel" else None)
    assert init_catalog("fr", pot_file=pot_file, locale_dir=locale_dir) == 0

    # 2. msginit path
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/" + cmd if cmd == "msginit" else None)
    assert init_catalog("fr", pot_file=pot_file, locale_dir=locale_dir) == 0

    # 3. Pure Python fallback
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    assert init_catalog("de", pot_file=pot_file, locale_dir=locale_dir) == 0
    de_po = locale_dir / "de" / "LC_MESSAGES" / "findfmt.po"
    assert de_po.is_file()
    assert "Language: de" in de_po.read_text(encoding="utf-8")


def test_tools_i18n_update_catalogs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify update_catalogs with pybabel, msgmerge, and fallback."""
    pot_file = tmp_path / "findfmt.pot"
    locale_dir = tmp_path / "locale"

    # Missing POT file error
    assert update_catalogs(pot_file=pot_file, locale_dir=locale_dir) == 1

    pot_file.touch()
    mock_run = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(subprocess, "run", mock_run)

    # 1. pybabel path
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/" + cmd if cmd == "pybabel" else None)
    assert update_catalogs(pot_file=pot_file, locale_dir=locale_dir) == 0

    # 2. msgmerge path
    po_file = locale_dir / "es" / "LC_MESSAGES" / "findfmt.po"
    po_file.parent.mkdir(parents=True)
    po_file.touch()

    monkeypatch.setattr(
        "shutil.which",
        lambda cmd: "/usr/bin/" + cmd if cmd == "msgmerge" else None,
    )
    assert update_catalogs(pot_file=pot_file, locale_dir=locale_dir) == 0

    # msgmerge error propagation
    mock_err_run = MagicMock(return_value=MagicMock(returncode=2))
    monkeypatch.setattr(subprocess, "run", mock_err_run)
    assert update_catalogs(pot_file=pot_file, locale_dir=locale_dir) == 2

    # 3. Neither found
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    assert update_catalogs(pot_file=pot_file, locale_dir=locale_dir) == 0


def test_tools_i18n_compile_catalogs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify compile_catalogs with pybabel, msgfmt, and fallback."""
    locale_dir = tmp_path / "locale"
    po_file = locale_dir / "es" / "LC_MESSAGES" / "findfmt.po"
    po_file.parent.mkdir(parents=True)
    po_file.write_text('msgid "hi"\nmsgstr "hola"\n', encoding="utf-8")

    mock_run = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(subprocess, "run", mock_run)

    # 1. pybabel path
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/" + cmd if cmd == "pybabel" else None)
    assert compile_catalogs(locale_dir=locale_dir) == 0

    # 2. msgfmt path
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/" + cmd if cmd == "msgfmt" else None)
    assert compile_catalogs(locale_dir=locale_dir) == 0

    # msgfmt error propagation
    mock_err_run = MagicMock(return_value=MagicMock(returncode=3))
    monkeypatch.setattr(subprocess, "run", mock_err_run)
    assert compile_catalogs(locale_dir=locale_dir) == 3

    # 3. Pure Python fallback via hatch_build
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    assert compile_catalogs(locale_dir=locale_dir) == 0
    assert (locale_dir / "es" / "LC_MESSAGES" / "findfmt.mo").is_file()

    # 4. Error during fallback compilation
    monkeypatch.setattr(
        tools.i18n,
        "compile_po_to_mo",
        MagicMock(side_effect=RuntimeError("Fail")),
    )
    assert compile_catalogs(locale_dir=locale_dir) == 1


def test_tools_i18n_main_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify tools/i18n.py main CLI dispatcher."""
    monkeypatch.setattr(tools.i18n, "extract_messages", MagicMock(return_value=0))
    monkeypatch.setattr(tools.i18n, "init_catalog", MagicMock(return_value=0))
    monkeypatch.setattr(tools.i18n, "update_catalogs", MagicMock(return_value=0))
    monkeypatch.setattr(tools.i18n, "compile_catalogs", MagicMock(return_value=0))

    assert main(["extract"]) == 0
    assert main(["init", "es"]) == 0
    assert main(["update"]) == 0
    assert main(["compile"]) == 0
    assert main(["all"]) == 0

    # Test failure propagation in 'all'
    monkeypatch.setattr(tools.i18n, "extract_messages", MagicMock(return_value=1))
    assert main(["all"]) == 1

    monkeypatch.setattr(tools.i18n, "extract_messages", MagicMock(return_value=0))
    monkeypatch.setattr(tools.i18n, "update_catalogs", MagicMock(return_value=2))
    assert main(["all"]) == 2


def test_starter_locale_catalogs_exist_and_translate() -> None:
    """Verify that all starter catalogs (es, fr, de, ja) exist and function."""
    locale_dir = PROJECT_ROOT / "src" / "findfmt" / "locale"
    assert (locale_dir / "findfmt.pot").is_file()

    # Compile catalogs to test runtime loading
    compile_catalogs(locale_dir=locale_dir)

    expected_translations = {
        "es": ("not installed", "no instalado"),
        "fr": ("not installed", "non installé"),
        "de": ("not installed", "nicht installiert"),
        "ja": ("not installed", "未インストール"),
    }

    for lang, (msgid, expected_msgstr) in expected_translations.items():
        po_path = locale_dir / lang / "LC_MESSAGES" / "findfmt.po"
        mo_path = locale_dir / lang / "LC_MESSAGES" / "findfmt.mo"
        assert po_path.is_file(), f"Missing PO file for {lang}"
        assert mo_path.is_file(), f"Missing MO file for {lang}"

        with override_locale(lang, localedir=locale_dir):
            assert _(msgid) == expected_msgstr


def test_sphinx_intl_configuration() -> None:
    """Verify sphinx-intl configuration in docs/source/locale."""
    docs_locale = PROJECT_ROOT / "docs" / "source" / "locale"
    assert docs_locale.is_dir()

    for lang in ("es", "fr", "de", "ja"):
        lang_dir = docs_locale / lang / "LC_MESSAGES"
        assert lang_dir.is_dir(), f"Missing Sphinx docs locale for {lang}"
        po_files = list(lang_dir.glob("*.po"))
        assert len(po_files) > 0, f"No Sphinx PO files found for {lang}"
