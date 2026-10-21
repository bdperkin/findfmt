"""Unit tests for locale-aware formatting, plurals, and multi-locale CLI behavior."""

from __future__ import annotations

import datetime as dt
import locale
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

import findfmt.utils.strings
from findfmt.cli.main import app
from findfmt.formatters import RichTableFormatter, TextFormatter
from findfmt.formatters.visual import format_summary_panel
from findfmt.i18n import (
    _format_grouped_digits,
    _get_numeric_conventions,
    _sync_system_locale,
    format_integer,
    format_number,
    override_locale,
)
from findfmt.models import FileInfo
from findfmt.sizes import format_size, format_size_binary, format_size_si
from findfmt.utils.strings import format_timestamp, resolve_time_format


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
        assert format_size_binary(1536) == "1.5 KiB"
        assert format_size_si(1500) == "1.5 kB"
        assert format_size(1536, human_readable=True) == "1.5 KiB"
        assert format_size(1500, si=True) == "1.5 kB"
        assert format_size(1536 * 1024) == "1.5 MiB"

    # Under German locale (if installed), comma decimal separator
    try:
        locale.setlocale(locale.LC_NUMERIC, "de_DE.utf8")
        assert format_size_binary(1536) == "1,5 KiB"
        assert format_size_si(1500) == "1,5 kB"
        assert format_size(1536, human_readable=True) == "1,5 KiB"
        assert format_size(1500, si=True) == "1,5 kB"
        assert format_size(1536 * 1024) == "1,5 MiB"
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


def test_south_asian_and_regional_groupings() -> None:
    """Verify regional numbering systems including South Asian lakh/crore and European periods."""
    # South Asian lakh/crore grouping (hi, bn)
    with override_locale("hi"):
        assert format_integer(1234567, grouping=True) == "12,34,567"
        assert format_integer(500, grouping=True) == "500"
        assert format_integer(-1234567, grouping=True) == "-12,34,567"
        assert format_number(1234567.89, decimals=2, grouping=True) == "12,34,567.89"
        assert format_number(12.4, decimals=1) == "12.4"

    with override_locale("bn"):
        assert format_integer(12345678, grouping=True) == "1,23,45,678"

    # Spanish period-separated thousands and comma decimal
    with override_locale("es"):
        assert format_integer(1234567, grouping=True) == "1.234.567"
        assert format_number(1234567.89, decimals=2, grouping=True) == "1.234.567,89"
        assert format_number(12.4, decimals=1) == "12,4"
        assert format_number(42.0, decimals=0) == "42"

    # German period-separated thousands and comma decimal
    with override_locale("de"):
        assert format_integer(1234567, grouping=True) == "1.234.567"
        assert format_number(12.4, decimals=1) == "12,4"

    # French narrow no-break space thousands and comma decimal
    with override_locale("fr"):
        assert format_integer(1234567, grouping=True) in ("1\u202f234\u202f567", "1 234 567")
        assert format_number(12.4, decimals=1) == "12,4"
        assert format_number(-12.4, decimals=1) == "-12,4"

    # Grouping helpers edge cases
    assert _format_grouped_digits("123", "", []) == "123"
    assert _format_grouped_digits("12345", ",", [3, 2]) == "12,345"
    assert _format_grouped_digits("123456", ",", [2, 0]) == "12,34,56"


def test_format_number_and_integer_mock_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify mock locale fallbacks when system locale cannot be loaded or raises error."""
    # Mock localeconv returning custom conventions
    monkeypatch.setattr(
        locale,
        "localeconv",
        lambda: {"decimal_point": "#", "thousands_sep": "_", "grouping": [3, 3, 0]},
    )
    assert _get_numeric_conventions() == ("#", "_", [3, 3, 0])

    # Mock format_string failure in format_integer and format_number
    monkeypatch.setattr(locale, "format_string", MagicMock(side_effect=locale.Error("mock err")))
    assert format_integer(1234567, grouping=True) == "1_234_567"
    assert format_number(1234.5, decimals=1, grouping=True) == "1_234#5"
    assert format_number(42.0, decimals=0) == "42"
    assert format_number(-42.5, decimals=1) == "-42#5"


def test_sync_system_locale_all_candidates_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _sync_system_locale handles the case where all candidate locales fail."""
    monkeypatch.setattr(locale, "setlocale", MagicMock(side_effect=locale.Error("fail")))
    _sync_system_locale("xx_YY")


def test_timestamp_localization_and_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify timestamp formatting respects nl_langinfo and falls back across platforms."""
    ts = dt.datetime(2026, 10, 20, 14, 30, 0, tzinfo=dt.timezone.utc).timestamp()

    # C / POSIX default
    with override_locale("C"):
        assert format_timestamp(ts) != "-"
        assert resolve_time_format() == "%b %d %H:%M"

    # POSIX nl_langinfo custom format (using raising=False for Windows compatibility)
    monkeypatch.setattr(locale, "D_T_FMT", getattr(locale, "D_T_FMT", 131155), raising=False)
    monkeypatch.setattr(locale, "nl_langinfo", lambda _code: "%Y-%m-%d %H:%M:%S", raising=False)
    with override_locale("fr"):
        res = format_timestamp(ts)
        assert res.startswith("2026-10-20")

    # Empty lang_fmt falls through to regional fallback
    monkeypatch.setattr(locale, "nl_langinfo", lambda _code: "", raising=False)
    with override_locale("es"):
        assert resolve_time_format() == "%d/%m/%Y %H:%M:%S"

    # POSIX C default format falls back to DEFAULT_TIME_FORMAT
    monkeypatch.setattr(locale, "nl_langinfo", lambda _code: "%a %b %e %H:%M:%S %Y", raising=False)
    with override_locale("C"):
        assert resolve_time_format() == "%b %d %H:%M"

    # Simulate platform without nl_langinfo (like Windows)
    monkeypatch.delattr(locale, "nl_langinfo", raising=False)
    with override_locale("ja"):
        fmt_ja = resolve_time_format()
        assert "年" in fmt_ja
        res_ja = format_timestamp(ts)
        assert "年" in res_ja

    with override_locale("de"):
        assert resolve_time_format() == "%d.%m.%Y %H:%M:%S"

    with override_locale("fr"):
        assert resolve_time_format() == "%d/%m/%Y %H:%M:%S"

    with override_locale("es"):
        assert resolve_time_format() == "%d/%m/%Y %H:%M:%S"

    with override_locale("unknown"):
        assert resolve_time_format() == "%b %d %H:%M"

    # Test ValueError in strftime falls back to DEFAULT_TIME_FORMAT
    bad_fmt_result = format_timestamp(ts, fmt="%Q %invalid")
    assert bad_fmt_result != "-"


def test_summary_panel_total_bytes_localized() -> None:
    """Verify format_summary_panel includes localized total size when total_bytes provided."""
    bytes_12_4_mb = int(12.4 * 1024 * 1024)
    # In French
    with override_locale("fr"):
        panel = format_summary_panel(15, Counter({"python": 10}), total_bytes=bytes_12_4_mb)
        render_text = str(panel.renderable)
        assert "12,4 Mio" in render_text
        assert "Taille totale :" in render_text

    # In German
    with override_locale("de"):
        panel_de = format_summary_panel(15, Counter({"python": 10}), total_bytes=bytes_12_4_mb)
        render_text_de = str(panel_de.renderable)
        assert "12,4 MiB" in render_text_de
        assert "Gesamtgröße:" in render_text_de

    # In Spanish
    with override_locale("es"):
        panel_es = format_summary_panel(1000, Counter({"python": 1000}), total_bytes=1048576)
        render_text_es = str(panel_es.renderable)
        assert "Tamaño total:" in render_text_es
        assert "1.000" in render_text_es


def test_get_numeric_conventions_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify numeric convention fallbacks for languages without host system locales."""
    monkeypatch.setattr(locale, "localeconv", dict)
    with override_locale("it"):
        assert _get_numeric_conventions() == (",", ".", [3, 3, 0])

    with override_locale("fr"):
        assert _get_numeric_conventions() == (",", "\u202f", [3, 3, 0])

    with override_locale("zh"):
        assert _get_numeric_conventions() == (".", ",", [3, 3, 0])

    with override_locale("unknown"):
        assert _get_numeric_conventions() == (".", "", [])

    # Tail remaining in _format_grouped_digits via CHAR_MAX
    char_max = getattr(locale, "CHAR_MAX", 127)
    assert _format_grouped_digits("1234567", ",", [3, char_max]) == "1234,567"

    # Negative integer fallback without system locale
    monkeypatch.setattr(locale, "format_string", MagicMock(return_value="-1234567"))
    with override_locale("es"):
        assert format_integer(-1234567, grouping=True) == "-1.234.567"


def test_resolve_time_format_exceptions_and_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify resolve_time_format and format_timestamp handle errors gracefully."""
    ts = 1700000000.0
    monkeypatch.setattr(locale, "D_T_FMT", getattr(locale, "D_T_FMT", 131155), raising=False)
    monkeypatch.setattr(
        locale,
        "nl_langinfo",
        MagicMock(side_effect=locale.Error("nl_langinfo failed")),
        raising=False,
    )
    with override_locale("fr"):
        assert resolve_time_format() == "%d/%m/%Y %H:%M:%S"

    # Mock date_obj.strftime raising ValueError on first call then succeeding on fallback
    mock_date = MagicMock()
    mock_date.strftime.side_effect = [ValueError("Invalid format"), "fallback_time"]
    mock_dt = MagicMock()
    mock_dt.timezone.utc = dt.timezone.utc
    mock_dt.fromtimestamp.return_value.astimezone.return_value = mock_date
    monkeypatch.setattr(findfmt.utils.strings.dt, "datetime", mock_dt)

    res = format_timestamp(ts, fmt="%unknown")
    assert res == "fallback_time"
