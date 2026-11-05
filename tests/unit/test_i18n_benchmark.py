"""Unit tests for gettext AI translation benchmark and evaluation suite (#303)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from tools.i18n_benchmark import (
    BASELINE_LOCALES,
    analyze_catalog,
    benchmark_baseline_locales,
    evaluate_candidate_tools,
    evaluate_providers,
    main,
    run_benchmark,
)

if TYPE_CHECKING:
    import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCALE_DIR = PROJECT_ROOT / "src" / "findfmt" / "locale"
POT_FILE = LOCALE_DIR / "findfmt.pot"


def test_analyze_catalog_real_and_empty(tmp_path: Path) -> None:
    """Verify catalog metrics on shipped findfmt.pot and empty fallback paths."""
    metrics = analyze_catalog(pot_file=POT_FILE, locale_dir=LOCALE_DIR)
    assert metrics.total_entries >= 140
    assert metrics.total_chars >= 15000
    assert metrics.total_words >= 1800
    assert metrics.brace_placeholder_entries >= 20
    assert metrics.rich_markup_entries >= 2
    assert metrics.plural_entries >= 1
    assert metrics.multiline_entries >= 4
    assert metrics.estimated_source_tokens >= 4000
    assert set(metrics.baseline_translated.keys()) == set(BASELINE_LOCALES)
    for loc in BASELINE_LOCALES:
        assert metrics.baseline_translated[loc] >= 15

    empty_metrics = analyze_catalog(
        pot_file=tmp_path / "missing.pot",
        locale_dir=tmp_path / "missing_locales",
    )
    assert empty_metrics.total_entries == 0
    assert empty_metrics.estimated_source_tokens == 0
    assert all(count == 0 for count in empty_metrics.baseline_translated.values())


def test_evaluate_providers_cost_and_latency() -> None:
    """Verify token, latency, and cost projections across LLM, NMT, and local backends."""
    metrics = analyze_catalog(pot_file=POT_FILE, locale_dir=LOCALE_DIR)
    providers = evaluate_providers(metrics, batch_size=25)
    by_id = {p.provider_id: p for p in providers}

    assert {
        "openai-gpt-4o-mini",
        "openai-gpt-4o",
        "anthropic-claude-3-5-haiku",
        "anthropic-claude-3-5-sonnet",
        "azure-ai-translator",
        "google-translate-v2",
        "local-ollama-qwen2.5-14b",
    } <= set(by_id.keys())

    mini = by_id["openai-gpt-4o-mini"]
    gpt4o = by_id["openai-gpt-4o"]
    ollama = by_id["local-ollama-qwen2.5-14b"]
    azure = by_id["azure-ai-translator"]

    assert mini.batches_per_catalog == 6
    assert mini.cost_per_catalog_usd > 0.0
    assert mini.cost_per_catalog_usd < gpt4o.cost_per_catalog_usd
    assert mini.cost_52_locales_usd < 1.0
    assert azure.cost_per_catalog_usd > 0.0
    assert ollama.supports_offline is True
    assert ollama.cost_per_catalog_usd == 0.0
    assert ollama.cost_52_locales_usd == 0.0


def test_evaluate_candidate_tools_ranking() -> None:
    """Verify architectural comparison scores and capabilities for candidate tools."""
    tools = evaluate_candidate_tools()
    by_id = {t.tool_id: t for t in tools}

    assert list(by_id.keys()) == [
        "findfmt-masked-llm",
        "gettext-translator",
        "pytlai",
        "auto-gettext-translator",
    ]
    top = by_id["findfmt-masked-llm"]
    assert top.protects_brace_placeholders is True
    assert top.protects_rich_markup is True
    assert top.sanitizes_po_locations is True
    assert top.zero_runtime_deps is True
    assert top.weighted_score > by_id["gettext-translator"].weighted_score
    assert by_id["gettext-translator"].weighted_score > by_id["pytlai"].weighted_score
    assert by_id["pytlai"].weighted_score > by_id["auto-gettext-translator"].weighted_score


def test_benchmark_baseline_locales_fidelity() -> None:
    """Verify baseline locale quality checks and masked vs unmasked placeholder survival."""
    results = benchmark_baseline_locales(locale_dir=LOCALE_DIR)
    assert len(results) == 4
    for res in results:
        assert res.locale in BASELINE_LOCALES
        assert res.catalog_entries >= 140
        assert res.translated_entries >= 15
        assert res.catalog_validation_errors == 0
        assert res.masked_pipeline_pass_rate == 100.0
        assert res.unmasked_nmt_pass_rate == 0.0


def test_cli_markdown_and_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify run_benchmark and CLI entrypoint support Markdown, JSON, and file output."""
    report = run_benchmark(pot_file=POT_FILE, locale_dir=LOCALE_DIR, batch_size=30)
    assert report.recommended_tool == "findfmt-masked-llm"

    assert main(["--pot", str(POT_FILE), "--localedir", str(LOCALE_DIR)]) == 0
    md_out = capsys.readouterr().out
    assert "Recommended: findfmt-masked-llm" in md_out
    assert "gettext-translator" in md_out

    json_file = tmp_path / "out" / "benchmark.json"
    assert (
        main(
            [
                "--pot",
                str(POT_FILE),
                "--localedir",
                str(LOCALE_DIR),
                "--json",
                "--output",
                str(json_file),
            ],
        )
        == 0
    )
    parsed = json.loads(json_file.read_text(encoding="utf-8"))
    assert parsed["recommended_tool"] == "findfmt-masked-llm"
    assert len(parsed["tools"]) == 4
    assert len(parsed["providers"]) == 7
    assert len(parsed["locales"]) == 4
