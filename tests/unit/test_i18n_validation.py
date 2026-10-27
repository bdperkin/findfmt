"""Unit tests for gettext PO placeholder validation and masking utilities (#304)."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.i18n import compile_catalogs, main
from tools.i18n_validation import (
    _unescape_po_str,
    extract_brace_placeholders,
    extract_printf_placeholders,
    extract_rich_tags,
    mask_placeholders,
    parse_po_catalog,
    unmask_placeholders,
    validate_catalogs,
    validate_message_pair,
    validate_po_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCALE_DIR = PROJECT_ROOT / "src" / "findfmt" / "locale"


def test_extract_brace_placeholders_valid_and_invalid() -> None:
    """Verify brace placeholder extraction handles named, nested, escaped, and invalid braces."""
    assert extract_brace_placeholders("Plain text") == set()
    assert extract_brace_placeholders("Escaped {{braces}} only") == set()
    assert extract_brace_placeholders("Path '{path}' has {count} items") == {"path", "count"}
    assert extract_brace_placeholders("Formatted {val:{width}d}") == {"val", "width"}

    with pytest.raises(ValueError, match=r"expected '\}'"):
        extract_brace_placeholders("Unclosed {path")

    with pytest.raises(ValueError, match="Single"):
        extract_brace_placeholders("Unmatched closing } brace")

    with pytest.raises(ValueError, match="Anonymous empty placeholder"):
        extract_brace_placeholders("Anonymous {} placeholder")


def test_extract_printf_and_rich_tags() -> None:
    """Verify printf specifier and Rich style tag extraction ignore CLI help metasyntax."""
    assert extract_printf_placeholders("100%% complete for %s (%d files)") == ["%s", "%d"]
    assert extract_printf_placeholders("Named %(path)s and %(count)02d") == [
        "%(path)s",
        "%(count)02d",
    ]
    assert extract_printf_placeholders("No specifiers or 50%% literal") == []

    assert extract_rich_tags("[bold]Matched file:[/] [cyan]{count}[/]") == [
        "[bold]",
        "[/]",
        "[cyan]",
        "[/]",
    ]
    # CLI help metasyntax in get_help_all() must not be misclassified as Rich style tags
    assert extract_rich_tags("Usage: findfmt [OPTIONS] [PATHS]... [default: no-print0]") == []


def test_mask_and_unmask_placeholders_roundtrip() -> None:
    """Verify pre-translation masking and post-translation unmasking preserve all tokens."""
    source = "[bold]Matched files:[/] [cyan]{count}[/] in {{literal}} (100%% %s)"
    masked, token_map = mask_placeholders(source)

    assert "{count}" not in masked
    assert "[bold]" not in masked
    assert "%s" not in masked
    assert "{{literal}}" in masked
    assert "100%%" in masked
    assert len(token_map) == 6

    # Simulate AI translation reordering words while keeping invariant tokens intact
    simulated_translation = masked.replace("Matched files:", "Archivos coincidentes:")
    unmasked = unmask_placeholders(simulated_translation, token_map)
    assert unmasked == "[bold]Archivos coincidentes:[/] [cyan]{count}[/] in {{literal}} (100%% %s)"


def test_mask_and_unmask_all_pot_template_entries() -> None:
    """Verify every msgid in findfmt.pot masks and unmasks with 100% fidelity."""
    pot_path = LOCALE_DIR / "findfmt.pot"
    entries = parse_po_catalog(pot_path.read_text(encoding="utf-8"))
    assert len(entries) >= 80

    for entry in entries:
        masked, mapping = mask_placeholders(entry.msgid)
        restored = unmask_placeholders(masked, mapping)
        assert restored == entry.msgid
        assert validate_message_pair(entry.msgid, restored) == []


def test_unmask_placeholders_corruption_errors() -> None:
    """Verify unmask_placeholders raises ValueError on dropped, unknown, or duplicated tokens."""
    masked, mapping = mask_placeholders("Cannot read {path}: {error}")

    with pytest.raises(ValueError, match="Missing placeholder token"):
        unmask_placeholders("No se puede leer __PH_0__", mapping)

    with pytest.raises(ValueError, match="Unknown placeholder token"):
        unmask_placeholders(f"{masked} __PH_99__", mapping)

    with pytest.raises(ValueError, match="Duplicate placeholder token"):
        unmask_placeholders(f"{masked} __PH_0__", mapping)


def test_validate_message_pair_detections() -> None:
    """Verify validate_message_pair catches missing, extra, malformed, and unbalanced tokens."""
    # Empty msgid or untranslated msgstr is ignored
    assert validate_message_pair("", "header") == []
    assert validate_message_pair("Hello {name}", "") == []

    # Valid pair
    assert validate_message_pair("Hello {name}", "Hola {name}") == []

    # Missing brace placeholder
    errs = validate_message_pair("Path '{path}' does not exist.", "La ruta no existe.")
    assert any("Missing brace placeholder" in e for e in errs)

    # Translated / extra brace placeholder
    errs = validate_message_pair("Path '{path}' does not exist.", "La ruta '{ruta}' no existe.")
    assert any("Missing brace placeholder" in e for e in errs)
    assert any("Unexpected brace placeholder" in e for e in errs)

    # Malformed single brace
    errs = validate_message_pair("Path '{path}'", "Ruta '{path'")
    assert any("Malformed brace syntax" in e for e in errs)

    # Runtime .format() failure (e.g. invalid attribute/index access on string dummy value)
    errs = validate_message_pair("Value {val}", "Valor {val[invalid]}")
    assert any("Unexpected brace" in e or "Formatting" in e or "Runtime" in e for e in errs)

    # Printf mismatch
    errs = validate_message_pair("Found %d files in %s", "Encontrados %d archivos")
    assert any("Printf placeholder mismatch" in e for e in errs)

    # Rich tag mismatch
    errs = validate_message_pair("[bold]Top tags:[/]", "Etiquetas principales:")
    assert any("Rich markup tag mismatch" in e for e in errs)

    # Unbalanced Rich tags (closing before opening)
    errs = validate_message_pair("[bold]Top tags:[/]", "[/]Etiquetas principales:[bold]")
    assert any("Unbalanced Rich markup tags" in e for e in errs)


def test_parse_and_validate_po_file(tmp_path: Path) -> None:
    """Verify parse_po_catalog and validate_po_file handle plurals, multiline, and errors."""
    assert _unescape_po_str("plain") == "plain"
    assert _unescape_po_str('"\\xinvalid"') == "\\xinvalid"

    missing_po = tmp_path / "missing.po"
    assert len(validate_po_file(missing_po)) == 1

    corrupted_po = tmp_path / "corrupted.po"
    corrupted_po.write_text(
        'msgid ""\n'
        'msgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        'msgid "Cannot read "\n'
        '"{path}"\n'
        'msgstr "No se puede leer "\n'
        '"{ruta}"\n\n'
        'msgid "[bold]Matched file:[/] [cyan]{count}[/]"\n'
        'msgid_plural "[bold]Matched files:[/] [cyan]{count}[/]"\n'
        'msgstr[0] "[bold]Archivo:[/] [cyan]{count}[/]"\n'
        'msgstr[1] "Archivos: {count}"\n',
        encoding="utf-8",
    )

    errors = validate_po_file(corrupted_po)
    assert len(errors) == 3
    assert any("Missing brace placeholder" in e for e in errors)
    assert any("Unexpected brace placeholder" in e for e in errors)
    assert any("msgstr[1]" in e and "Rich markup tag mismatch" in e for e in errors)


def test_validate_cli_and_compile_gate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify `tools/i18n.py validate` and `compile` block corrupted catalogs."""
    # Shipped catalogs pass validation
    assert main(["validate", "--localedir", str(LOCALE_DIR)]) == 0

    # Corrupted catalog in temporary locale directory fails validate and compile
    bad_po = tmp_path / "es" / "LC_MESSAGES" / "findfmt.po"
    bad_po.parent.mkdir(parents=True)
    bad_po.write_text(
        'msgid "Error in {path}"\nmsgstr "Error en {ruta}"\n',
        encoding="utf-8",
    )

    assert validate_catalogs(tmp_path) == 1
    captured = capsys.readouterr()
    assert "Validation error:" in captured.err

    assert main(["validate", "--localedir", str(tmp_path)]) == 1
    assert compile_catalogs(locale_dir=tmp_path) == 1
