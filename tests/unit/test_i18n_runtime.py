"""Unit tests for internationalization (i18n) runtime engine and string wrapping."""

from __future__ import annotations

import gettext
import io
import struct
from collections import Counter
from pathlib import Path

import pytest
import typer
from rich.table import Table
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.cli.config import (
    _validate_file_exists,
    _validate_format_conflicts,
    _validate_from_file,
    _validate_ordering,
    build_traversal_config,
)
from findfmt.cli.runner import _open_output_sink, execute_findfmt
from findfmt.formatters import OutputFormat
from findfmt.formatters.base import UnsupportedFormatError
from findfmt.formatters.markup import UnsupportedTableStyleError
from findfmt.formatters.visual import (
    RichTableFormatter,
    UnsupportedBoxStyleError,
    format_summary_panel,
)
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
from findfmt.traversal.sorting import resolve_sort_key


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


@pytest.fixture
def mock_locale_catalog(tmp_path: Path) -> Path:
    """Create a temporary message catalog directory with a compiled Spanish .mo file."""
    po_dir = tmp_path / "es" / "LC_MESSAGES"
    po_dir.mkdir(parents=True, exist_ok=True)
    mo_path = po_dir / "findfmt.mo"

    mo_data = _generate_mo_bytes(
        {
            "": (
                "Content-Type: text/plain; charset=UTF-8\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"
            ),
            "Path": "Ruta",
            "Inode": "Inodo",
            "Device": "Dispositivo",
            "Permissions": "Permisos",
            "User": "Usuario",
            "Group": "Grupo",
            "Modified": "Modificado",
            "Status Changed": "Estado cambiado",
            "Tags": "Etiquetas",
            "MIME Type": "Tipo MIME",
            "Size": "Tamano",
            "Executable": "Ejecutable",
            "Symlink": "Enlace simbolico",
            "Shebang": "Directiva shebang",
            "--- findfmt summary ---": "--- resumen findfmt ---",
            "[bold]Matched files:[/] [cyan]{count}[/]": (
                "[bold]Archivos coincidentes:[/] [cyan]{count}[/]"
            ),
            "[bold]Top tags:[/ /]": "[bold]Etiquetas principales:[/]",
            "Unsupported output format: '{format}'. Expected one of: {valid_formats}": (
                "Formato no soportado: '{format}'."
            ),
            "Unsupported table style: '{style}'. Expected one of: {valid_styles}": (
                "Estilo de tabla no soportado: '{style}'."
            ),
            "Unsupported RST table style: '{style}'. Expected 'grid' or 'simple'.": (
                "Estilo RST no soportado: '{style}'."
            ),
            (
                "Invalid sort criteria '{criteria}'. "
                "Choose from: name, version, time, mtime, ctime, size, none."
            ): "Criterio de ordenacion invalido '{criteria}'.",
            "Error: Conflicting format options: {options}.": (
                "Error: Opciones de formato conflictivas: {options}."
            ),
            "Error: Cannot specify both --dirsfirst and --filesfirst.": (
                "Error: No se puede especificar ambos --dirsfirst y --filesfirst."
            ),
            "Error opening output file '{path}': {error}": (
                "Error al abrir archivo de salida '{path}': {error}"
            ),
            "not installed": "no instalado",
            "not found": "no encontrado",
            "file\x00files": "archivo\x00archivos",
        },
    )
    mo_path.write_bytes(mo_data)
    return tmp_path


def test_detect_locale_posix_precedence() -> None:
    """Verify standard POSIX precedence order: LANGUAGE -> LC_ALL -> LC_MESSAGES -> LANG -> C."""
    # LANGUAGE takes highest precedence
    env1 = {"LANGUAGE": "es_ES:es", "LC_ALL": "fr_FR", "LC_MESSAGES": "de_DE", "LANG": "it_IT"}
    assert detect_locale(env1) == "es_ES"

    # LC_ALL takes precedence when LANGUAGE is unset
    env2 = {"LC_ALL": "fr_FR", "LC_MESSAGES": "de_DE", "LANG": "it_IT"}
    assert detect_locale(env2) == "fr_FR"

    # LC_MESSAGES takes precedence when LANGUAGE and LC_ALL are unset
    env3 = {"LC_MESSAGES": "de_DE", "LANG": "it_IT"}
    assert detect_locale(env3) == "de_DE"

    # LANG is used when higher ones are unset
    env4 = {"LANG": "it_IT"}
    assert detect_locale(env4) == "it_IT"

    # Fallback to C when all are empty or missing
    env5 = {"LANGUAGE": "", "LC_ALL": "", "LC_MESSAGES": "", "LANG": ""}
    assert detect_locale(env5) == "C"
    assert detect_locale({}) == "C"

    # Default without env uses os.environ
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

    # When all empty, returns ['C']
    assert detect_locales({}) == ["C"]

    # Default without args uses os.environ
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

    # Reset with C
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

    # Ensure restoration on exception
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

        # None does not overwrite
        assert locale_callback(None) is None
        assert get_current_locale() == "es_ES"


def test_gettext_and_ngettext_fallback() -> None:
    """Verify _ and ngettext work with English fallback when no catalog is present."""
    with override_locale("C"):
        assert _("Hello world") == "Hello world"
        assert ngettext("{n} file", "{n} files", 1) == "{n} file"
        assert ngettext("{n} file", "{n} files", 0) == "{n} files"
        assert ngettext("{n} file", "{n} files", 5) == "{n} files"


def test_catalog_translation_with_mo(mock_locale_catalog: Path) -> None:
    """Verify translation lookup using an active mock MO catalog."""
    with override_locale("es", localedir=mock_locale_catalog):
        assert _("Path") == "Ruta"
        assert _("Inode") == "Inodo"
        assert _("Permissions") == "Permisos"
        # Untranslated string falls back cleanly to original message
        assert _("Unknown message") == "Unknown message"
        # Plural forms
        assert ngettext("file", "files", 1) == "archivo"
        assert ngettext("file", "files", 2) == "archivos"


def test_rich_table_formatter_columns_translated(mock_locale_catalog: Path) -> None:
    """Verify RichTableFormatter column headers are localized using active catalog."""
    with override_locale("es", localedir=mock_locale_catalog):
        formatter = RichTableFormatter(
            show_inodes=True,
            show_device=True,
            show_permissions=True,
            show_user=True,
            show_group=True,
            show_mtime=True,
        )
        table = Table()
        formatter._setup_columns(table)  # noqa: SLF001
        col_names = [col.header for col in table.columns]
        assert "Inodo" in col_names
        assert "Dispositivo" in col_names
        assert "Permisos" in col_names
        assert "Usuario" in col_names
        assert "Grupo" in col_names
        assert "Modificado" in col_names
        assert "Ruta" in col_names
        assert "Etiquetas" in col_names


def test_summary_panel_translated(mock_locale_catalog: Path) -> None:
    """Verify summary panel titles and labels are localized."""
    with override_locale("es", localedir=mock_locale_catalog):
        panel = format_summary_panel(3, Counter({"python": 3}))
        assert panel.title is not None
        assert "resumen findfmt" in str(panel.title)
        assert "Archivos coincidentes" in str(panel.renderable)


def test_exceptions_translated(mock_locale_catalog: Path) -> None:
    """Verify exception messages are localized."""
    with override_locale("es", localedir=mock_locale_catalog):
        err1 = UnsupportedFormatError("bad_fmt", "text, json")
        assert "Formato no soportado: 'bad_fmt'." in str(err1)

        err2 = UnsupportedBoxStyleError("bad_box", "rounded")
        assert "Estilo de tabla no soportado: 'bad_box'." in str(err2)

        err3 = UnsupportedTableStyleError("bad_rst")
        assert "Estilo RST no soportado: 'bad_rst'." in str(err3)

        with pytest.raises(ValueError, match=r"Criterio de ordenacion invalido 'bad_sort'\."):
            resolve_sort_key("bad_sort")


def test_cli_config_validation_translated(mock_locale_catalog: Path) -> None:
    """Verify CLI configuration validation error messages are localized."""
    with override_locale("es", localedir=mock_locale_catalog):
        # Format conflict
        with pytest.raises(typer.Exit) as exc:
            _validate_format_conflicts(tree=True, xml=True, html=None)

        assert exc.value.exit_code == 2

        # Ordering conflict
        with pytest.raises(typer.Exit) as exc2:
            _validate_ordering(dirs_first=True, files_first=True)

        assert exc2.value.exit_code == 2

        # Missing input file
        with pytest.raises(typer.Exit) as exc3:
            _validate_from_file("nonexistent_path_findfmt_test.txt")

        assert exc3.value.exit_code == 2

        # Missing file exists
        with pytest.raises(typer.Exit) as exc4:
            _validate_file_exists(Path("nonexistent_gitignore_test"), "Gitignore file")

        assert exc4.value.exit_code == 2


def test_runner_open_output_sink_error_translated(
    tmp_path: Path,
    mock_locale_catalog: Path,
) -> None:
    """Verify runner _open_output_sink error message is wrapped and localized."""
    # Attempting to open a directory as a file produces OSError
    bad_output = tmp_path / "a_directory"
    bad_output.mkdir()

    with override_locale("es", localedir=mock_locale_catalog), pytest.raises(typer.Exit):
        _open_output_sink(bad_output, None)


def test_build_traversal_config_locale_argument() -> None:
    """Verify build_traversal_config accepts locale and applies it."""
    with override_locale("C"):
        config = build_traversal_config(
            paths=None,
            tags=None,
            exclude_tags=None,
            all_tags=False,
            shebang=None,
            no_ignore=False,
            hidden=False,
            follow_symlinks=False,
            dirs_only=False,
            one_file_system=False,
            max_depth=None,
            file_limit=None,
            prune=False,
            pattern=None,
            exclude_pattern=None,
            ignore_case=False,
            match_dirs=False,
            absolute=False,
            relative=False,
            print0=False,
            list_tags=False,
            summary=False,
            output_format=OutputFormat.TEXT,
            locale="POSIX",
        )
        assert config.locale == "POSIX"


def test_detect_locale_empty_tokens() -> None:
    """Verify detect_locale skips empty and whitespace tokens in colon-separated variables."""
    # All tokens empty in LANGUAGE -> falls through to LC_ALL
    env1 = {"LANGUAGE": " : : ", "LC_ALL": "es_ES"}
    assert detect_locale(env1) == "es_ES"

    # All tokens empty across all vars -> falls back to C
    env2 = {"LANGUAGE": "::", "LC_ALL": "  :  "}
    assert detect_locale(env2) == "C"


def test_execute_findfmt_locale_argument(tmp_path: Path) -> None:
    """Verify execute_findfmt accepts locale and applies it."""
    test_file = tmp_path / "hello.py"
    test_file.write_text("print('hello')\n")

    buf = io.StringIO()
    with override_locale("C"):
        execute_findfmt(
            paths=[tmp_path],
            tags=None,
            exclude_tags=None,
            all_tags=False,
            shebang=None,
            no_ignore=False,
            hidden=False,
            follow_symlinks=False,
            output_format=OutputFormat.TEXT,
            print0=False,
            list_tags=False,
            summary=False,
            stream=buf,
            locale="POSIX",
        )
        assert get_current_locale() == "POSIX"


def test_cli_flags_locale_and_lang(tmp_path: Path) -> None:
    """Verify CLI flags --locale and --lang work on command line."""
    runner = CliRunner()

    with override_locale("C"):
        res1 = runner.invoke(app, ["--locale", "POSIX", str(tmp_path)])
        assert res1.exit_code == 0
        assert get_current_locale() == "POSIX"

        res2 = runner.invoke(app, ["--lang", "C", str(tmp_path)])
        assert res2.exit_code == 0
        assert get_current_locale() == "C"
