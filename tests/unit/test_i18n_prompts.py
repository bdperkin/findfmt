"""Unit tests for domain context prompt engineering, glossary, and ngettext plural rules (#305)."""

from __future__ import annotations

from pathlib import Path

from tools.i18n import (
    CLI_GLOSSARY,
    PLURAL_RULE_SPECS,
    build_plural_prompt,
    build_system_prompt,
    extract_cli_flags,
    get_plural_rule_spec,
    parse_plural_forms_header,
    parse_po_catalog,
    validate_cli_flags_preserved,
)
from tools.i18n_prompts import (
    estimate_prompt_token_overhead,
    evaluate_temperature_profiles,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCALE_DIR = PROJECT_ROOT / "src" / "findfmt" / "locale"


def test_cli_glossary_completeness_and_system_prompt() -> None:
    """Verify authoritative glossary terms and system prompt construction across locales."""
    terms = {entry.term for entry in CLI_GLOSSARY}
    expected_terms = {
        "shebang",
        "MIME tag",
        "POSIX",
        "regex",
        "glob",
        "symlink",
        "traversal",
        "pruning",
        "hidden files",
        "pager",
    }
    assert expected_terms <= terms

    for entry in CLI_GLOSSARY:
        assert set(entry.translations.keys()) == {"de", "es", "fr", "ja"}
        assert all(val.strip() for val in entry.translations.values())

    es_prompt = build_system_prompt("es_ES.UTF-8", include_glossary=True)
    assert "locale 'es_ES.UTF-8'" in es_prompt
    assert ".gitignore" in es_prompt
    assert "__PH_0__" in es_prompt
    assert "--format" in es_prompt
    assert "enlace simbólico" in es_prompt
    assert "archivos ocultos" in es_prompt

    compact_prompt = build_system_prompt("xx", include_glossary=False)
    assert "Technical Terminology Glossary:" not in compact_prompt
    assert "Strict Formatting & Invariant Rules:" in compact_prompt


def test_parse_plural_forms_header_and_rule_specs() -> None:
    """Verify 1-form, 2-form, 3-form Slavic/Polish, 6-form Arabic, and custom header rules."""
    assert parse_plural_forms_header("No header here") == (2, "(n != 1)")
    nplurals, expr = parse_plural_forms_header("Plural-Forms: nplurals=1; plural=0;\\n")
    assert nplurals == 1
    assert expr == "0"

    assert get_plural_rule_spec("ja").family == "one-form"
    assert get_plural_rule_spec("zh_CN").nplurals == 1
    assert get_plural_rule_spec("ko").nplurals == 1

    assert get_plural_rule_spec("es").family == "two-form-standard"
    assert get_plural_rule_spec("de").nplurals == 2
    assert get_plural_rule_spec("fr").family == "two-form-zero-singular"
    assert get_plural_rule_spec("pt_BR").plural_expr == "(n > 1)"

    ru_spec = get_plural_rule_spec("ru")
    assert ru_spec.family == "three-form-slavic"
    assert ru_spec.nplurals == 3
    assert len(ru_spec.form_descriptions) == 3

    pl_spec = get_plural_rule_spec("pl")
    assert pl_spec.family == "three-form-polish"
    assert pl_spec.nplurals == 3

    ar_spec = get_plural_rule_spec("ar")
    assert ar_spec.family == "six-form-arabic"
    assert ar_spec.nplurals == 6
    assert len(ar_spec.form_descriptions) == 6

    # Verify PO header overrides and custom nplurals fallback
    ja_po = (LOCALE_DIR / "ja" / "LC_MESSAGES" / "findfmt.po").read_text(encoding="utf-8")
    assert get_plural_rule_spec("ja", po_text=ja_po).nplurals == 1

    # Matching header expression on unknown locale resolves to standard family
    assert (
        get_plural_rule_spec("xx", po_text="Plural-Forms: nplurals=1; plural=0;\n").family
        == "one-form"
    )
    # Custom 4-form header on unknown locale constructs custom spec
    custom_spec = get_plural_rule_spec(
        "cy",
        po_text="Plural-Forms: nplurals=4; plural=(n==1) ? 0 : (n==2) ? 1 : (n != 8) ? 2 : 3;\n",
    )
    assert custom_spec.family == "custom-4-form"
    assert custom_spec.nplurals == 4
    assert len(custom_spec.form_descriptions) == 4

    # Unknown locale with no header falls back to two-form-standard
    assert get_plural_rule_spec("unknown_LOCALE").family == "two-form-standard"
    assert len(PLURAL_RULE_SPECS) == 6


def test_build_plural_prompt_masks_placeholders_and_requests_exact_forms() -> None:
    """Verify build_plural_prompt masks Rich/brace tokens and specifies target nplurals."""
    msgid = "[bold]Matched file:[/] [cyan]{count}[/]"
    msgid_plural = "[bold]Matched files:[/] [cyan]{count}[/]"

    for locale, expected_n in (("ja", 1), ("es", 2), ("ru", 3), ("pl", 3), ("ar", 6)):
        prompt = build_plural_prompt(msgid, msgid_plural, locale)
        assert f"nplurals={expected_n}" in prompt
        assert f"JSON array of exactly {expected_n} strings" in prompt
        assert f"msgstr[{expected_n - 1}]" in prompt
        assert "__PH_0__" in prompt
        assert "{count}" not in prompt
        assert "[bold]" not in prompt

    plain_prompt = build_plural_prompt("One item", "Many items", "en")
    assert "Invariant placeholder tokens to preserve in EVERY form: none" in plain_prompt


def test_extract_and_validate_cli_flags_on_shipped_catalogs() -> None:
    """Verify CLI flag extraction and confirm zero translated flags across all PO catalogs."""
    sample = "Use --format json, --no-hidden, or -t python (not hyphen-word)."
    assert extract_cli_flags(sample) == {"--format", "--no-hidden", "-t"}
    assert extract_cli_flags("No flags in this sentence.") == set()

    assert validate_cli_flags_preserved("", "anything") == []
    assert validate_cli_flags_preserved("Plain text", "Texto plano") == []
    assert (
        validate_cli_flags_preserved(
            "Output NUL-delimited paths (--print0).",
            "Emitir rutas delimitadas por NUL (--print0).",
        )
        == []
    )

    errs = validate_cli_flags_preserved(
        "Filter by --format or -t tag.",
        "Filtrar por --formato o etiqueta.",
    )
    assert len(errs) == 1
    assert "--format" in errs[0]
    assert "-t" in errs[0]

    # Verify all shipped catalogs preserve 100% of CLI flags in translated entries
    po_files = sorted(LOCALE_DIR.glob("*/LC_MESSAGES/findfmt.po"))
    assert len(po_files) >= 5
    for po_path in po_files:
        entries = parse_po_catalog(po_path.read_text(encoding="utf-8"))
        for entry in entries:
            for msgstr in entry.msgstrs:
                assert validate_cli_flags_preserved(entry.msgid, msgstr) == [], (
                    f"Translated or dropped CLI flag in {po_path}:{entry.line_number}"
                )


def test_temperature_and_token_overhead_evaluation() -> None:
    """Verify prompt token overhead calculation and temperature consistency profiles."""
    overhead = estimate_prompt_token_overhead(batch_size=25, total_entries=147)
    assert overhead["system_prompt_chars"] > 1000
    assert overhead["system_prompt_tokens_per_batch"] >= 250
    assert overhead["batches_per_catalog"] == 6
    assert (
        overhead["total_prompt_overhead_tokens"]
        == overhead["system_prompt_tokens_per_batch"] * overhead["batches_per_catalog"]
    )

    profiles = evaluate_temperature_profiles()
    assert len(profiles) == 4
    recommended = [p for p in profiles if p.recommended]
    assert len(recommended) == 1
    assert recommended[0].temperature == 0.0
    assert recommended[0].determinism_score == 100.0
    assert recommended[0].flag_preservation_rate == 100.0
    assert recommended[0].glossary_adherence_rate == 100.0
    assert profiles[0].determinism_score > profiles[-1].determinism_score
