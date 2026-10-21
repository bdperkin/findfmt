"""Unit tests for gettext catalog extraction, Hatchling build hook, and sphinx-intl."""

from __future__ import annotations

import gettext
import io
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
    _get_working_dir,
    _sanitize_po_locations,
    _to_rel_path_str,
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
    assert "" in entries
    assert "charset=UTF-8" in entries[""]


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
    """Verify that all starter catalogs (en, es, fr, de, ja) exist and function."""
    locale_dir = PROJECT_ROOT / "src" / "findfmt" / "locale"
    assert (locale_dir / "findfmt.pot").is_file()

    # Compile catalogs to test runtime loading
    compile_catalogs(locale_dir=locale_dir)

    expected_translations = {
        "en": ("not installed", "not installed"),
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

    for lang in ("en", "es", "fr", "de", "ja"):
        lang_dir = docs_locale / lang / "LC_MESSAGES"
        assert lang_dir.is_dir(), f"Missing Sphinx docs locale for {lang}"
        po_files = list(lang_dir.glob("*.po"))
        assert len(po_files) > 0, f"No Sphinx PO files found for {lang}"


def test_sanitize_po_locations(tmp_path: Path) -> None:
    """Verify _sanitize_po_locations strips absolute prefixes and normalizes locations."""
    # 1. Non-existent file handled without error
    _sanitize_po_locations(tmp_path / "nonexistent.po")

    # 2. File with various location formats and non-location lines
    sample_po = tmp_path / "sample.po"
    content = (
        '# Header comment with /home/user/path\nmsgid "/not/a/location/file.py"\n'
        'msgstr "/also/not/a/location"\n#: /home/user/git/findfmt/src/findfmt/diagnostics.py:78\n'
        'msgid "test1"\nmsgstr "test1"\n'
        "#: /home/user/git/findfmt/src/findfmt/a.py:10 /home/user/git/findfmt/src/findfmt/b.py:20\n"
        'msgid "test2"\nmsgstr "test2"\n#: C:\\Users\\user\\findfmt\\src\\findfmt\\c.py:30\n'
        'msgid "test3"\nmsgstr "test3"\n#: src/findfmt/already_clean.py:40\n'
        'msgid "test4"\nmsgstr "test4"\n'
    )
    sample_po.write_text(content, encoding="utf-8")

    _sanitize_po_locations(sample_po, root=Path("/home/user/git/findfmt"))

    cleaned = sample_po.read_text(encoding="utf-8")
    assert "#: src/findfmt/diagnostics.py:78" in cleaned
    assert "#: src/findfmt/a.py:10 src/findfmt/b.py:20" in cleaned
    assert "#: src/findfmt/c.py:30" in cleaned
    assert "#: src/findfmt/already_clean.py:40" in cleaned
    assert "# Header comment with /home/user/path" in cleaned
    assert 'msgid "/not/a/location/file.py"' in cleaned
    assert "/home/user/git/findfmt" not in cleaned


def test_i18n_path_helpers(tmp_path: Path) -> None:
    """Verify _to_rel_path_str and _get_working_dir behaviors."""
    assert _to_rel_path_str(PROJECT_ROOT / "src" / "findfmt") == "src/findfmt"
    assert _to_rel_path_str(tmp_path) == str(tmp_path)

    assert _get_working_dir(PROJECT_ROOT / "src", PROJECT_ROOT / "tests") == PROJECT_ROOT
    assert _get_working_dir(PROJECT_ROOT / "src", tmp_path) is None


def test_no_absolute_paths_in_tracked_locale_catalogs() -> None:
    """Verify no tracked PO/POT catalogs contain absolute path comments."""
    locale_dir = PROJECT_ROOT / "src" / "findfmt" / "locale"
    pot_file = locale_dir / "findfmt.pot"
    assert pot_file.is_file()

    catalogs = [pot_file, *list(locale_dir.glob("*/LC_MESSAGES/*.po"))]
    assert len(catalogs) >= 6  # pot + 5 languages (en, es, fr, de, ja)

    for catalog in catalogs:
        lines = catalog.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            if line.startswith("#: "):
                assert not line.startswith("#: /"), (
                    f"Absolute path location comment found in {catalog.name}:{idx}: {line}"
                )
                tokens = line[3:].split()
                for token in tokens:
                    path_part = token.split(":")[0]
                    assert not path_part.startswith("/"), (
                        f"Absolute path token found in {catalog.name}:{idx}: {token}"
                    )
                    is_windows_drive = (
                        len(path_part) > 2 and path_part[1] == ":" and path_part[2] in "/\\"
                    )
                    assert not is_windows_drive, (
                        f"Windows absolute path found in {catalog.name}:{idx}: {token}"
                    )


def test_pure_python_compiler_emits_charset_header(tmp_path: Path) -> None:
    """Verify _compile_po_pure_python emits charset header so gettext decodes UTF-8."""
    po_file = tmp_path / "test.po"
    mo_file = tmp_path / "test.mo"
    po_file.write_text('msgid "size"\nmsgstr "Größe"\n', encoding="utf-8")
    _compile_po_pure_python(po_file, mo_file)
    mo_data = mo_file.read_bytes()
    translations = gettext.GNUTranslations(io.BytesIO(mo_data))
    assert translations.gettext("size") == "Größe"
    assert "charset=UTF-8" in translations.info()["content-type"]


SHIPPED_PO_FILES = sorted(
    (PROJECT_ROOT / "src" / "findfmt" / "locale").glob("*/LC_MESSAGES/findfmt.po"),
)


@pytest.mark.parametrize("po_path", SHIPPED_PO_FILES, ids=lambda p: p.parent.parent.name)
def test_pure_python_and_babel_compilers_agree(tmp_path: Path, po_path: Path) -> None:
    """Verify pure-Python fallback and Babel produce identical translations for all shipped POs."""
    if tools.hatch_build.pofile is None or tools.hatch_build.mofile is None:
        pytest.skip("Babel is not installed")

    pure_mo = tmp_path / "pure.mo"
    babel_mo = tmp_path / "babel.mo"
    _compile_po_pure_python(po_path, pure_mo)

    with po_path.open("r", encoding="utf-8") as f_in:
        catalog = tools.hatch_build.pofile.read_po(f_in)

    with babel_mo.open("wb") as f_out:
        tools.hatch_build.mofile.write_mo(f_out, catalog)

    with pure_mo.open("rb") as f_pure:
        pure_t = gettext.GNUTranslations(f_pure)

    with babel_mo.open("rb") as f_babel:
        babel_t = gettext.GNUTranslations(f_babel)

    entries = _parse_po_entries(po_path.read_text(encoding="utf-8"))
    for msgid in entries:
        if not msgid:
            continue

        if "\x00" in msgid:
            singular, plural = msgid.split("\x00", 1)
            for n in (0, 1, 2, 5):
                assert pure_t.ngettext(singular, plural, n) == babel_t.ngettext(singular, plural, n)
        else:
            assert pure_t.gettext(msgid) == babel_t.gettext(msgid)
