"""Unit tests for locale-aware formatting, plurals, and multi-locale CLI behavior."""

from __future__ import annotations

import locale
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from findfmt.cli.main import app
from findfmt.formatters import RichTableFormatter, TextFormatter
from findfmt.formatters.visual import format_summary_panel
from findfmt.i18n import (
    _sync_system_locale,
    format_integer,
    format_number,
    override_locale,
)
from findfmt.models import FileInfo
from findfmt.sizes import format_size, format_size_binary, format_size_si
from findfmt.utils.strings import format_timestamp


def test_format_integer_and_number() -> None:
    """Verify format_integer and format_number formatting and fallbacks."""
    # Grouping false
    assert format_integer(12345, grouping=False) == "12345"
    assert format_integer(0, grouping=False) == "0"

    # Grouping true under C locale
    with override_locale("C"):
        assert format_integer(12345, grouping=True) in ("12345", "12,345")
        assert format_number(12.3456, decimals=2) == "12.35"
        assert format_number(0.0, decimals=1) == "0.0"

    # Error fallbacks
    real_format_string = locale.format_string
    try:
        locale.format_string = MagicMock(side_effect=ValueError("Mock format error"))  # type: ignore[assignment]
        assert format_integer(999, grouping=True) == "999"
        assert format_number(1.23, decimals=1) == "1.2"
    finally:
        locale.format_string = real_format_string  # type: ignore[assignment]


def test_sync_system_locale_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _sync_system_locale handles None, C/POSIX, 2-letter codes, and fallbacks."""
    calls: list[tuple[int, str]] = []

    def mock_setlocale(category: int, loc: str | None = None) -> str:
        if loc is not None:
            calls.append((category, loc))

        return "C"

    monkeypatch.setattr(locale, "setlocale", mock_setlocale)

    _sync_system_locale(None)
    assert (locale.LC_ALL, "") in calls

    calls.clear()
    _sync_system_locale("C")
    assert (locale.LC_ALL, "C") in calls

    calls.clear()
    _sync_system_locale("POSIX")
    assert (locale.LC_ALL, "C") in calls

    calls.clear()
    _sync_system_locale("es")
    assert (locale.LC_ALL, "es") in calls

    # Test candidate iteration with partial failures
    calls.clear()

    def mock_failing_setlocale(category: int, loc: str | None = None) -> str:
        if loc is not None:
            calls.append((category, loc))

        if category == locale.LC_ALL:
            err_msg = "unsupported"
            raise locale.Error(err_msg)

        return "C"

    monkeypatch.setattr(locale, "setlocale", mock_failing_setlocale)
    _sync_system_locale("es")
    # Verifies fallback to LC_TIME and LC_NUMERIC
    assert any(cat == locale.LC_TIME for cat, _loc in calls)
    assert any(cat == locale.LC_NUMERIC for cat, _loc in calls)


def test_override_locale_saved_system_locale_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify override_locale when initial setlocale raises an error."""

    def mock_setlocale(_category: int, loc: str | None = None) -> str:
        if loc is None:
            err_msg = "initial failure"
            raise locale.Error(err_msg)

        return "C"

    monkeypatch.setattr(locale, "setlocale", mock_setlocale)
    with override_locale("C") as loc:
        assert loc == "C"


def test_locale_aware_date_and_time() -> None:
    """Verify format_timestamp respects LC_TIME across supported languages."""
    # January 15, 2024 12:00:00 UTC
    fixed_ts = 1705320000.0

    # Default C / English
    with override_locale("C"):
        formatted_c = format_timestamp(fixed_ts, fmt="%b %d")
        assert "Jan" in formatted_c

    # Try Spanish if installed on host
    try:
        locale.setlocale(locale.LC_TIME, "es_ES.utf8")
        with override_locale("es"):
            formatted_es = format_timestamp(fixed_ts, fmt="%b %d")
            assert "ene" in formatted_es.lower()
    except (locale.Error, ValueError, OSError):
        pass
    finally:
        with override_locale("C"):
            pass

    # Try French if installed on host
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.utf8")
        with override_locale("fr"):
            formatted_fr = format_timestamp(fixed_ts, fmt="%b %d")
            assert ("janv" in formatted_fr.lower()) or ("jan" in formatted_fr.lower())
    except (locale.Error, ValueError, OSError):
        pass
    finally:
        with override_locale("C"):
            pass


def test_locale_aware_numbers_and_sizes() -> None:
    """Verify format_size, format_size_binary, and format_size_si format decimal separators."""
    # Under C / POSIX, period decimal separator
    with override_locale("C"):
        assert format_size_binary(1536) == "1.5 K"
        assert format_size_si(1500) == "1.5 kB"
        assert format_size(1536, human_readable=True) == "1.5 K"
        assert format_size(1500, si=True) == "1.5 kB"
        assert format_size(1536 * 1024) == "1.5 MB"

    # Under German locale (if installed), comma decimal separator
    try:
        locale.setlocale(locale.LC_NUMERIC, "de_DE.utf8")
        assert format_size_binary(1536) == "1,5 K"
        assert format_size_si(1500) == "1,5 kB"
        assert format_size(1536, human_readable=True) == "1,5 K"
        assert format_size(1500, si=True) == "1,5 kB"
        assert format_size(1536 * 1024) == "1,5 MB"
    except (locale.Error, ValueError, OSError):
        pass
    finally:
        locale.setlocale(locale.LC_ALL, "C")


def test_pluralization_logic() -> None:
    """Verify ngettext and format_summary_panel distinguish singular vs plural."""
    # In C locale
    with override_locale("C"):
        panel_one = format_summary_panel(1, Counter({"txt": 1}))
        assert "Matched file:" in str(panel_one.renderable)

        panel_two = format_summary_panel(2, Counter({"txt": 2}))
        assert "Matched files:" in str(panel_two.renderable)

    # In Spanish catalog
    with override_locale("es"):
        panel_es_one = format_summary_panel(1, Counter({"txt": 1}))
        assert "Archivo coincidente:" in str(panel_es_one.renderable)

        panel_es_two = format_summary_panel(2, Counter({"txt": 2}))
        assert "Archivos coincidentes:" in str(panel_es_two.renderable)

    # In French catalog
    with override_locale("fr"):
        panel_fr_one = format_summary_panel(1, Counter({"txt": 1}))
        assert "Fichier correspondant:" in str(panel_fr_one.renderable)

        panel_fr_two = format_summary_panel(2, Counter({"txt": 2}))
        assert "Fichiers correspondants:" in str(panel_fr_two.renderable)

    # In German catalog
    with override_locale("de"):
        panel_de_one = format_summary_panel(1, Counter({"txt": 1}))
        assert "Passende Datei:" in str(panel_de_one.renderable)

        panel_de_two = format_summary_panel(2, Counter({"txt": 2}))
        assert "Passende Dateien:" in str(panel_de_two.renderable)

    # In Japanese catalog (nplurals=1)
    with override_locale("ja"):
        panel_ja_one = format_summary_panel(1, Counter({"txt": 1}))
        assert "一致したファイル:" in str(panel_ja_one.renderable)

        panel_ja_two = format_summary_panel(2, Counter({"txt": 2}))
        assert "一致したファイル:" in str(panel_ja_two.renderable)


def test_non_ascii_cjk_output_formatters(tmp_path: Path) -> None:
    """Verify non-ASCII, accented, and CJK characters format properly in tables and text."""
    # Create files with various multilingual characters
    ja_file = tmp_path / "日本語ファイル.txt"
    es_file = tmp_path / "árbol_mañana.py"
    de_file = tmp_path / "über_größe.md"
    fr_file = tmp_path / "élève_français.json"

    for f in (ja_file, es_file, de_file, fr_file):
        f.write_text("content", encoding="utf-8")

    files = [
        FileInfo(
            path=ja_file,
            relative_path=Path(ja_file.name),
            tags=frozenset({"text"}),
            size_bytes=7,
        ),
        FileInfo(
            path=es_file,
            relative_path=Path(es_file.name),
            tags=frozenset({"python"}),
            size_bytes=7,
        ),
        FileInfo(
            path=de_file,
            relative_path=Path(de_file.name),
            tags=frozenset({"markdown"}),
            size_bytes=7,
        ),
        FileInfo(
            path=fr_file,
            relative_path=Path(fr_file.name),
            tags=frozenset({"json"}),
            size_bytes=7,
        ),
    ]

    # Test TextFormatter handles CJK and non-ASCII names
    text_formatter = TextFormatter()
    output_text = text_formatter.format(files)
    assert "日本語ファイル.txt" in output_text
    assert "árbol_mañana.py" in output_text
    assert "über_größe.md" in output_text
    assert "élève_français.json" in output_text

    # Test RichTableFormatter renders and aligns without crash
    table_formatter = RichTableFormatter(
        show_size=True,
        show_mtime=True,
        human_readable=True,
    )
    table_output = table_formatter.format(files)
    assert "日本語ファイル.txt" in table_output
    assert "árbol_mañana.py" in table_output
    assert "über_größe.md" in table_output
    assert "élève_français.json" in table_output


@pytest.mark.parametrize(
    ("locale_code", "expected_summary_title"),
    [
        ("es", "resumen findfmt"),
        ("fr", "résumé findfmt"),
        ("de", "Zusammenfassung"),
        ("ja", "findfmt 要約"),
        ("C", "findfmt summary"),
    ],
)
def test_parameterized_cli_locales(
    tmp_path: Path,
    locale_code: str,
    expected_summary_title: str,
) -> None:
    """Verify CLI --summary and --locale flags across multiple supported locales."""
    sample_file = tmp_path / "test.py"
    sample_file.write_text("print('hello')", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [str(sample_file), "--summary", "--locale", locale_code],
    )
    assert result.exit_code == 0
    # Summary title is translated in stderr
    assert expected_summary_title in result.stderr
