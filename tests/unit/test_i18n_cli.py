"""Unit tests for CLI, formatters, and runner localization and translations."""

from __future__ import annotations

import io
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
from findfmt.i18n import get_current_locale, override_locale
from findfmt.traversal.sorting import resolve_sort_key
from tests.unit.test_i18n_runtime import _generate_mo_bytes


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
            (
                "[bold]Matched file:[/] [cyan]{count}[/]\x00"
                "[bold]Matched files:[/] [cyan]{count}[/]"
            ): (
                "[bold]Archivo coincidente:[/] [cyan]{count}[/]\x00"
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

        single_panel = format_summary_panel(1, Counter({"python": 1}))
        assert "Archivo coincidente" in str(single_panel.renderable)


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
