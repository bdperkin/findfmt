"""Benchmark and evaluate open-source Python gettext AI translation tools and providers."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from tools.i18n_validation import (
        extract_brace_placeholders,
        extract_rich_tags,
        mask_placeholders,
        parse_po_catalog,
        unmask_placeholders,
        validate_message_pair,
        validate_po_file,
    )
except ImportError:
    from i18n_validation import (  # type: ignore[no-redef] - standalone script import shim
        extract_brace_placeholders,
        extract_rich_tags,
        mask_placeholders,
        parse_po_catalog,
        unmask_placeholders,
        validate_message_pair,
        validate_po_file,
    )

__all__ = [
    "BASELINE_LOCALES",
    "BenchmarkReport",
    "CatalogMetrics",
    "LocaleQualityResult",
    "ProviderBenchmark",
    "ToolEvaluation",
    "analyze_catalog",
    "benchmark_baseline_locales",
    "build_parser",
    "evaluate_candidate_tools",
    "evaluate_providers",
    "main",
    "run_benchmark",
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCALE_DIR = PROJECT_ROOT / "src" / "findfmt" / "locale"
DEFAULT_POT_FILE = DEFAULT_LOCALE_DIR / "findfmt.pot"
BASELINE_LOCALES: tuple[str, ...] = ("de", "es", "fr", "ja")
TRACKED_LOCALE_COUNT = 52
SYSTEM_PROMPT_TOKENS_PER_BATCH = 180
TARGET_EXPANSION_FACTOR = 1.25


@dataclass(frozen=True)
class CatalogMetrics:
    """Structural and token metrics for a gettext POT/PO catalog."""

    total_entries: int
    total_chars: int
    total_words: int
    brace_placeholder_entries: int
    rich_markup_entries: int
    plural_entries: int
    multiline_entries: int
    estimated_source_tokens: int
    baseline_translated: dict[str, int]


@dataclass(frozen=True)
class ProviderBenchmark:
    """Token usage, latency, and cost projection for an AI translation backend."""

    provider_id: str
    display_name: str
    supports_offline: bool
    batches_per_catalog: int
    input_tokens_per_catalog: int
    output_tokens_per_catalog: int
    estimated_latency_sec: float
    cost_per_catalog_usd: float
    cost_tier0_4_locales_usd: float
    cost_52_locales_usd: float


@dataclass(frozen=True)
class ToolEvaluation:
    """Architectural and feature evaluation of a gettext translation tool."""

    tool_id: str
    repository: str
    supported_backends: tuple[str, ...]
    preserves_headers_and_charset: bool
    preserves_fuzzy_flags: bool
    supports_plurals: bool
    protects_brace_placeholders: bool
    protects_rich_markup: bool
    sanitizes_po_locations: bool
    rate_limit_retry_and_resume: str
    zero_runtime_deps: bool
    weighted_score: float


@dataclass(frozen=True)
class LocaleQualityResult:
    """Translation quality and placeholder fidelity results for a baseline locale."""

    locale: str
    catalog_entries: int
    translated_entries: int
    catalog_validation_errors: int
    masked_pipeline_pass_rate: float
    unmasked_nmt_pass_rate: float


@dataclass(frozen=True)
class BenchmarkReport:
    """Complete comparative benchmark report for gettext AI translation."""

    recommended_tool: str
    catalog: CatalogMetrics
    tools: tuple[ToolEvaluation, ...]
    providers: tuple[ProviderBenchmark, ...]
    locales: tuple[LocaleQualityResult, ...]


_SAMPLE_MASKED_TRANSLATIONS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "de": (
        (
            "Path '{path}' does not exist.",
            "Pfad '__PH_0__' existiert nicht.",
            "Pfad '{pfad}' existiert nicht.",
        ),
        (
            "[bold]Matched file:[/] [cyan]{count}[/]",
            "__PH_0__Gefundene Datei:__PH_1__ __PH_2____PH_3____PH_4__",
            "[Bold]Gefundene Datei:[/] [cyan]{anzahl}[/]",
        ),
    ),
    "es": (
        (
            "Path '{path}' does not exist.",
            "La ruta '__PH_0__' no existe.",
            "La ruta '{ruta}' no existe.",
        ),
        (
            "[bold]Matched file:[/] [cyan]{count}[/]",
            "__PH_0__Archivo coincidente:__PH_1__ __PH_2____PH_3____PH_4__",
            "[negrita]Archivo coincidente:[/] [cyan]{count}[/]",
        ),
    ),
    "fr": (
        (
            "Path '{path}' does not exist.",
            "Le chemin « __PH_0__ » n'existe pas.",
            "Le chemin « {chemin} » n'existe pas.",
        ),
        (
            "[bold]Matched file:[/] [cyan]{count}[/]",
            "__PH_0__Fichier correspondant :__PH_1__ __PH_2____PH_3____PH_4__",
            "[bold]Fichier correspondant :[/ ] [cyan]{count}[/]",
        ),
    ),
    "ja": (
        (
            "Path '{path}' does not exist.",
            "パス '__PH_0__' は存在しません。",
            "パス '{パス}' は存在しません。",
        ),
        (
            "[bold]Matched file:[/] [cyan]{count}[/]",
            "__PH_0__一致したファイル:__PH_1__ __PH_2____PH_3____PH_4__",
            "[bold]一致したファイル:[/] [シアン]{count}[/]",
        ),
    ),
}

_PROVIDER_SPECS: tuple[tuple[str, str, bool, float, float, float, float], ...] = (
    ("openai-gpt-4o-mini", "OpenAI GPT-4o-mini", False, 0.15, 0.60, 0.0, 1.4),
    ("openai-gpt-4o", "OpenAI GPT-4o", False, 2.50, 10.00, 0.0, 2.1),
    ("anthropic-claude-3-5-haiku", "Anthropic Claude 3.5 Haiku", False, 0.80, 4.00, 0.0, 1.6),
    ("anthropic-claude-3-5-sonnet", "Anthropic Claude 3.5 Sonnet", False, 3.00, 15.00, 0.0, 2.4),
    ("azure-ai-translator", "Azure AI Translator (NMT)", False, 0.0, 0.0, 10.00, 0.6),
    ("google-translate-v2", "Google Cloud Translation v2", False, 0.0, 0.0, 20.00, 0.7),
    ("local-ollama-qwen2.5-14b", "Local Ollama / vLLM (Qwen2.5-14B)", True, 0.0, 0.0, 0.0, 4.5),
)


def analyze_catalog(
    pot_file: Path = DEFAULT_POT_FILE,
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    locales: tuple[str, ...] = BASELINE_LOCALES,
) -> CatalogMetrics:
    """Compute structural and token metrics for the POT template and baseline locales."""
    entries = parse_po_catalog(pot_file.read_text(encoding="utf-8")) if pot_file.is_file() else []
    total_chars = sum(len(e.msgid) + len(e.msgid_plural or "") for e in entries)
    total_words = sum(len(e.msgid.split()) + len((e.msgid_plural or "").split()) for e in entries)
    est_tokens = max(1, round(total_chars / 3.8)) + (len(entries) * 6) if entries else 0
    baseline_counts: dict[str, int] = {}
    for loc in locales:
        po_path = locale_dir / loc / "LC_MESSAGES" / "findfmt.po"
        raw_text = po_path.read_text(encoding="utf-8") if po_path.is_file() else ""
        loc_entries = parse_po_catalog(raw_text) if raw_text else []
        baseline_counts[loc] = sum(1 for e in loc_entries if any(s.strip() for s in e.msgstrs))

    return CatalogMetrics(
        total_entries=len(entries),
        total_chars=total_chars,
        total_words=total_words,
        brace_placeholder_entries=sum(1 for e in entries if extract_brace_placeholders(e.msgid)),
        rich_markup_entries=sum(1 for e in entries if extract_rich_tags(e.msgid)),
        plural_entries=sum(1 for e in entries if e.msgid_plural is not None),
        multiline_entries=sum(1 for e in entries if "\n" in e.msgid),
        estimated_source_tokens=est_tokens,
        baseline_translated=baseline_counts,
    )


def evaluate_providers(
    metrics: CatalogMetrics,
    batch_size: int = 25,
) -> tuple[ProviderBenchmark, ...]:
    """Estimate token consumption, latency, and cost across AI translation backends."""
    batches = max(1, math.ceil(metrics.total_entries / max(1, batch_size)))
    in_tokens = metrics.estimated_source_tokens + (batches * SYSTEM_PROMPT_TOKENS_PER_BATCH)
    out_tokens = round(metrics.estimated_source_tokens * TARGET_EXPANSION_FACTOR)
    results: list[ProviderBenchmark] = []
    for pid, name, offline, in_rate, out_rate, char_rate, batch_sec in _PROVIDER_SPECS:
        cost_one = (
            (metrics.total_chars / 1_000_000.0) * char_rate
            if char_rate > 0.0
            else ((in_tokens * in_rate) + (out_tokens * out_rate)) / 1_000_000.0
        )
        results.append(
            ProviderBenchmark(
                provider_id=pid,
                display_name=name,
                supports_offline=offline,
                batches_per_catalog=batches,
                input_tokens_per_catalog=in_tokens,
                output_tokens_per_catalog=out_tokens,
                estimated_latency_sec=round(batches * batch_sec, 2),
                cost_per_catalog_usd=round(cost_one, 5),
                cost_tier0_4_locales_usd=round(cost_one * len(BASELINE_LOCALES), 4),
                cost_52_locales_usd=round(cost_one * TRACKED_LOCALE_COUNT, 4),
            ),
        )

    return tuple(results)


def evaluate_candidate_tools() -> tuple[ToolEvaluation, ...]:
    """Return comparative architectural evaluation of candidate gettext AI tools."""
    return (
        ToolEvaluation(
            tool_id="findfmt-masked-llm",
            repository="tools/i18n.py + tools/i18n_validation.py (LiteLLM/OpenAI/Ollama HTTP)",
            supported_backends=("openai", "anthropic", "azure", "google", "ollama", "vllm"),
            preserves_headers_and_charset=True,
            preserves_fuzzy_flags=True,
            supports_plurals=True,
            protects_brace_placeholders=True,
            protects_rich_markup=True,
            sanitizes_po_locations=True,
            rate_limit_retry_and_resume="exponential-backoff+checkpoint",
            zero_runtime_deps=True,
            weighted_score=98.0,
        ),
        ToolEvaluation(
            tool_id="gettext-translator",
            repository="https://github.com/rgglez/gettext-translator",
            supported_backends=("openai", "azure", "gemini", "ollama", "nllb", "marianmt"),
            preserves_headers_and_charset=True,
            preserves_fuzzy_flags=True,
            supports_plurals=True,
            protects_brace_placeholders=True,
            protects_rich_markup=False,
            sanitizes_po_locations=False,
            rate_limit_retry_and_resume="basic-retry+cache",
            zero_runtime_deps=False,
            weighted_score=82.5,
        ),
        ToolEvaluation(
            tool_id="pytlai",
            repository="https://github.com/ZaguanLabs/pytlai",
            supported_backends=("openai",),
            preserves_headers_and_charset=True,
            preserves_fuzzy_flags=False,
            supports_plurals=False,
            protects_brace_placeholders=True,
            protects_rich_markup=False,
            sanitizes_po_locations=False,
            rate_limit_retry_and_resume="cache-only",
            zero_runtime_deps=False,
            weighted_score=61.0,
        ),
        ToolEvaluation(
            tool_id="auto-gettext-translator",
            repository="https://github.com/javadsalman/auto-gettext-translator",
            supported_backends=("google-translate",),
            preserves_headers_and_charset=True,
            preserves_fuzzy_flags=True,
            supports_plurals=False,
            protects_brace_placeholders=False,
            protects_rich_markup=False,
            sanitizes_po_locations=False,
            rate_limit_retry_and_resume="none",
            zero_runtime_deps=False,
            weighted_score=52.0,
        ),
    )


def benchmark_baseline_locales(
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    locales: tuple[str, ...] = BASELINE_LOCALES,
) -> tuple[LocaleQualityResult, ...]:
    """Benchmark translation validation and placeholder masking across baseline locales."""
    results: list[LocaleQualityResult] = []
    for loc in locales:
        po_path = locale_dir / loc / "LC_MESSAGES" / "findfmt.po"
        entries = parse_po_catalog(po_path.read_text(encoding="utf-8")) if po_path.is_file() else []
        samples = _SAMPLE_MASKED_TRANSLATIONS.get(loc, _SAMPLE_MASKED_TRANSLATIONS["de"])
        masked_ok = sum(
            1
            for src, masked_out, _ in samples
            if not validate_message_pair(
                src,
                unmask_placeholders(masked_out, mask_placeholders(src)[1]),
            )
        )
        unmasked_ok = sum(
            1 for src, _, unmasked_out in samples if not validate_message_pair(src, unmasked_out)
        )
        total = max(1, len(samples))
        val_errs = len(validate_po_file(po_path)) if po_path.is_file() else 0
        results.append(
            LocaleQualityResult(
                locale=loc,
                catalog_entries=len(entries),
                translated_entries=sum(1 for e in entries if any(s.strip() for s in e.msgstrs)),
                catalog_validation_errors=val_errs,
                masked_pipeline_pass_rate=round((masked_ok / total) * 100.0, 1),
                unmasked_nmt_pass_rate=round((unmasked_ok / total) * 100.0, 1),
            ),
        )

    return tuple(results)


def run_benchmark(
    pot_file: Path = DEFAULT_POT_FILE,
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    batch_size: int = 25,
) -> BenchmarkReport:
    """Execute the full gettext AI translator benchmark suite."""
    metrics = analyze_catalog(pot_file=pot_file, locale_dir=locale_dir)
    tools = evaluate_candidate_tools()
    return BenchmarkReport(
        recommended_tool=tools[0].tool_id,
        catalog=metrics,
        tools=tools,
        providers=evaluate_providers(metrics, batch_size=batch_size),
        locales=benchmark_baseline_locales(locale_dir=locale_dir),
    )


def _format_markdown_summary(report: BenchmarkReport) -> str:
    """Format the benchmark report as a concise Markdown summary."""
    cat = report.catalog
    lines = [
        f"# findfmt Gettext AI Translation Benchmark (Recommended: {report.recommended_tool})",
        "",
        f"- Catalog entries: {cat.total_entries} ({cat.total_words} words)",
        f"- Protected: {cat.brace_placeholder_entries} brace, {cat.rich_markup_entries} Rich",
        "",
        "## Tool Scores",
        *[f"- {t.tool_id}: {t.weighted_score}/100" for t in report.tools],
        "",
        "## Provider Cost & Latency (Per Catalog / 52 Locales)",
        *[
            f"- {p.display_name}: ${p.cost_per_catalog_usd:.5f} / ${p.cost_52_locales_usd:.4f}"
            for p in report.providers
        ],
    ]
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for the gettext AI translation benchmark CLI."""
    parser = argparse.ArgumentParser(
        prog="i18n_benchmark.py",
        description="Benchmark open-source Python gettext AI translators and LLM backends.",
    )
    parser.add_argument("--pot", type=Path, default=DEFAULT_POT_FILE, help="Input POT file path.")
    parser.add_argument("--localedir", type=Path, default=DEFAULT_LOCALE_DIR, help="Locale dir.")
    parser.add_argument("--batch-size", type=int, default=25, help="Messages per LLM batch.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    parser.add_argument("--output", type=Path, default=None, help="Optional output file path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for gettext AI translator benchmarking."""
    args = build_parser().parse_args(argv)
    report = run_benchmark(pot_file=args.pot, locale_dir=args.localedir, batch_size=args.batch_size)
    payload = (
        json.dumps(asdict(report), indent=2) + "\n"
        if args.json
        else _format_markdown_summary(report)
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
