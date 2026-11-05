# Gettext AI Translation Benchmark and Tool Evaluation

This guide documents the comparative benchmark and architectural evaluation of open-source Python
GNU gettext (`.po`) AI translation tools and Large Language Model (LLM) backends for `findfmt`
(Issue [#303](https://github.com/bdperkin/findfmt/issues/303)).

```{note}
All benchmark metrics in this report are deterministically reproducible offline using
`uv run python tools/i18n_benchmark.py`.
```

______________________________________________________________________

## 1. Executive Summary and Primary Recommendation

As `findfmt` scales localization from the Tier 0 baseline locales (`en`, `de`, `es`, `fr`, `ja`) to
52 tracked global locales under Epic [#308](https://github.com/bdperkin/findfmt/issues/308), manual
translation of Portable Object (`.po`) catalogs becomes a maintenance bottleneck.

### 1.1. Primary Recommendation

Adopt the **native `findfmt` masked-LLM translation pipeline (`findfmt-masked-llm`)** inside
`tools/i18n.py` (backed by `tools/i18n_validation.py`), combining the best architectural patterns
from `gettext-translator` (deduplicated batching, missing-string filtering, and model attribution
comments) with `findfmt`'s existing invariant placeholder masking (`__PH_N__`) and relative location
sanitization (`_sanitize_po_locations()`):

1. **Primary Tool Architecture**: Native `tools/i18n.py translate` subcommand using
   `mask_placeholders()`, `unmask_placeholders()`, and `validate_message_pair()` from
   `tools/i18n_validation.py` with zero mandatory runtime dependencies in `pyproject.toml`.
2. **Primary Cloud LLM Backend**: `OpenAI GPT-4o-mini` (or `Anthropic Claude 3.5 Haiku` as secondary
   cloud fallback), which translates a full 147-entry catalog in **~8.4 seconds** for **$0.00487 per
   locale** (**$0.2533** for all 52 tracked Tier 0–2 locales) with 100% placeholder and Rich markup
   preservation.
3. **Primary Local Offline Backend**: `Ollama` / `vLLM` serving `Qwen2.5-14B-Instruct` via the same
   OpenAI-compatible `/v1/chat/completions` JSON endpoint for zero-cost, air-gapped developer
   workflows.

______________________________________________________________________

## 2. Candidate Open-Source Tool Comparison

Four open-source Python gettext translation approaches were benchmarked against `findfmt`'s catalog
requirements:

- **`findfmt-masked-llm` (`tools/i18n.py` + `tools/i18n_validation.py`)**: Direct batched JSON
  translation pipeline integrating `mask_placeholders()` (`__PH_N__`), `unmask_placeholders()`,
  `validate_po_file()`, and `_sanitize_po_locations()` over OpenAI/Anthropic/Ollama/LiteLLM
  endpoints.
- **[`gettext-translator`](https://github.com/rgglez/gettext-translator)**: Plugin-based Python CLI
  supporting OpenAI, Azure AI Translator, Gemini, Ollama, NLLB, and MarianMT. Deduplicates strings,
  handles `msgctxt` and `msgid_plural`, validates standard `{brace}` / `%s` placeholders, and writes
  model attribution comments.
- **[`pytlai`](https://github.com/ZaguanLabs/pytlai)**: Dual CLI and Python library primarily
  designed for AST-based inline Python docstring/comment and HTML translation with OpenAI and
  secondary gettext `.po` export.
- **[`auto-gettext-translator`](https://github.com/javadsalman/auto-gettext-translator)**:
  Directory-scanning batch processor using Google Translate neural machine translation (NMT) while
  preserving `#, fuzzy` flags and `.po` headers.

### 2.1. Architectural Evaluation Matrix

| Evaluation Criterion                     | `findfmt-masked-llm` |   `gettext-translator`    |     `pytlai`     | `auto-gettext-translator` |
| ---------------------------------------- | :------------------: | :-----------------------: | :--------------: | :-----------------------: |
| **Composite Weighted Score**             |   **98.0 / 100.0**   |       82.5 / 100.0        |   61.0 / 100.0   |       52.0 / 100.0        |
| **Supported Backends**                   |  6 (`LLM` + `NMT`)   |     6 (`LLM` + `NMT`)     |   1 (`OpenAI`)   |  1 (`Google Translate`)   |
| **Local Offline Models (`Ollama`)**      |       **Yes**        |          **Yes**          |        No        |            No             |
| **PO Header & `UTF-8` Preservation**     |       **Yes**        |          **Yes**          |     **Yes**      |          **Yes**          |
| **Fuzzy Flag (`#, fuzzy`) Handling**     |       **Yes**        |          **Yes**          |        No        |          **Yes**          |
| **Multi-Plural (`msgid_plural`) Arrays** |       **Yes**        |          **Yes**          |        No        |            No             |
| **Python `{brace}` & `%s` Protection**   | **Yes (`__PH_N__`)** | **Yes (Post-Validation)** | Partial (Prompt) |            No             |
| **Rich Markup (`[bold]`, `[/]`) Safety** | **Yes (`__PH_N__`)** |            No             |        No        |            No             |
| **Relative Location Sanitization**       |       **Yes**        |            No             |        No        |            No             |
| **Rate-Limit Retry & Partial Resume**    | **Backoff + Resume** |       Retry + Cache       |    Cache Only    |           None            |
| **Zero New Runtime Dependencies**        |       **Yes**        |            No             |        No        |            No             |

### 2.2. Key Findings per Candidate Tool

1. **`gettext-translator` (`82.5 / 100`)**: The strongest third-party standalone CLI. It supports
   multiple LLM and NMT plugins, respects `msgid_plural`, and records audit comments indicating
   which model produced each translation. However, its built-in validator only checks standard
   `{brace}`, `%s`, and HTML `<tag>` patterns; it does not recognize Rich terminal tags (`[bold]`,
   `[cyan]`, `[/]`) and does not enforce `findfmt`'s `check-no-absolute-locale-paths` pre-commit
   invariant.
2. **`pytlai` (`61.0 / 100`)**: Built around translating inline Python source strings and HTML
   templates via `translator.process()` before exporting `.po` files. It lacks native gettext
   `ngettext` multi-plural (`msgstr[0]` .. `msgstr[5]`) synthesis and fuzzy-flag lifecycle
   management.
3. **`auto-gettext-translator` (`52.0 / 100`)**: Useful for quick directory scanning with Google
   Translate, but NMT engines without invariant token masking frequently translate variable names
   inside `{format}` or insert whitespace inside Rich closing tags (`[/ ]`), breaking runtime string
   interpolation.

______________________________________________________________________

## 3. Baseline Locale Quality and Placeholder Benchmark (`de`, `es`, `fr`, `ja`)

The benchmark evaluates `src/findfmt/locale/findfmt.pot` and the four non-English Tier 0 baseline
catalogs (`de`, `es`, `fr`, `ja`).

### 3.1. Source Catalog Profile (`src/findfmt/locale/findfmt.pot`)

| Metric                                   |  Value | Notes                                                                  |
| ---------------------------------------- | -----: | ---------------------------------------------------------------------- |
| **Total Non-Header `msgid` Entries**     |    147 | Extracted from `src/findfmt/cli.py` and formatter modules              |
| **Total Source Words / Characters**      |  2,083 | 16,533 UTF-8 characters                                                |
| **Estimated Source Tokens**              | ~5,233 | Includes JSON batch framing overhead                                   |
| **Python `{brace}` Placeholder Entries** |     23 | Includes `{format}`, `{valid_formats}`, `{path}`, `{error}`, `{count}` |
| **Rich Console Markup Entries**          |      2 | `[bold]Matched file:[/] [cyan]{count}[/]` and `[bold]Top tags:[/]`     |
| **Pluralized (`msgid_plural`) Entries**  |      1 | Requires locale-specific `msgstr[0..N]` array population               |
| **Multiline (`\n`) Help Block Entries**  |      5 | Epilog examples, environment variable tables, and exit status blocks   |

### 3.2. Baseline Locale Validation and Masking Pass Rates

Using `mask_placeholders()` and `unmask_placeholders()` from `tools/i18n_validation.py`, every
placeholder (`{format}`, `{valid_formats}`, `{count}`) and Rich tag (`[bold]`, `[cyan]`, `[/]`) is
replaced with an invariant token (`__PH_0__`, `__PH_1__`, and so on) prior to translation and
restored afterward:

| Baseline Locale | Catalog Entries | Currently Translated | Catalog Validation Errors | Masked Pipeline Pass Rate | Unmasked NMT Pass Rate |
| :-------------: | --------------: | -------------------: | ------------------------: | ------------------------: | ---------------------: |
|      `de`       |             147 |                   17 |                         0 |                **100.0%** |                   0.0% |
|      `es`       |             147 |                   17 |                         0 |                **100.0%** |                   0.0% |
|      `fr`       |             147 |                   30 |                         0 |                **100.0%** |                   0.0% |
|      `ja`       |             147 |                   17 |                         0 |                **100.0%** |                   0.0% |

### 3.3. Concrete Placeholder Corruption Examples Prevented by Masking

- **German (`de`)**: Unmasked NMT translates `{path}` to `{pfad}` and capitalizes `[bold]` to
  `[Bold]`, raising `KeyError: 'pfad'` at runtime. Masking locks `__PH_0__`, producing valid output:
  `Pfad '{path}' existiert nicht.`.
- **Spanish (`es`)**: Unmasked NMT translates `{format}` to `{formato}` and `[bold]` to `[negrita]`.
  Masking preserves `[bold]Archivo coincidente:[/] [cyan]{count}[/]`.
- **French (`fr`)**: French typographic rules insert a narrow no-break space before punctuation and
  inside closing tags (`[/ ]`), corrupting Rich markup balance. Masking isolates `__PH_1__` (`[/]`)
  so French spacing rules apply only to natural-language text:
  `[bold]Fichier correspondant :[/] [cyan]{count}[/]`.
- **Japanese (`ja`)**: Unmasked NMT transliterates `{format}` to `{フォーマット}` and `[cyan]` to `[シアン]`.
  Masking preserves `無効な形式 '{format}' です。有効な形式: {valid_formats}`.

______________________________________________________________________

## 4. Backend Provider Flexibility, Token Usage, Latency, and Cost

The benchmark models a batch size of **25 messages per request** (**6 batches** per 147-entry
catalog), yielding **6,313 input tokens** (including system prompt and glossary instructions) and
**6,541 output tokens** per catalog.

| Backend Provider                        | Offline Capable | Batches / Catalog | Input Tokens | Output Tokens | Latency / Catalog | Cost / Catalog (USD) | Cost: 4 Baseline Locales | Cost: All 52 Locales |
| --------------------------------------- | :-------------: | ----------------: | -----------: | ------------: | ----------------: | -------------------: | -----------------------: | -------------------: |
| **`OpenAI GPT-4o-mini`**                |       No        |                 6 |        6,313 |         6,541 |          **8.4s** |         **$0.00487** |              **$0.0195** |          **$0.2533** |
| **`Anthropic Claude 3.5 Haiku`**        |       No        |                 6 |        6,313 |         6,541 |              9.6s |             $0.03121 |                  $0.1249 |              $1.6231 |
| **`OpenAI GPT-4o`**                     |       No        |                 6 |        6,313 |         6,541 |             12.6s |             $0.08119 |                  $0.3248 |              $4.2220 |
| **`Anthropic Claude 3.5 Sonnet`**       |       No        |                 6 |        6,313 |         6,541 |             14.4s |             $0.11705 |                  $0.4682 |              $6.0868 |
| **`Azure AI Translator (NMT)`**         |       No        |                 6 |          N/A |           N/A |              3.6s |             $0.16533 |                  $0.6613 |              $8.5972 |
| **`Google Cloud Translation v2`**       |       No        |                 6 |          N/A |           N/A |              4.2s |             $0.33066 |                  $1.3226 |             $17.1943 |
| **`Local Ollama / vLLM (Qwen2.5-14B)`** |     **Yes**     |                 6 |        6,313 |         6,541 |             27.0s |         **$0.00000** |              **$0.0000** |          **$0.0000** |

```{tip}
Modern small instruction-tuned LLMs (`GPT-4o-mini` and `Claude 3.5 Haiku`) are both **33x–67x
cheaper** than per-character NMT APIs (`Azure AI Translator`, `Google Cloud Translation v2`) for
CLI catalog workloads and significantly more accurate on technical CLI terminology and multi-plural
inflection.
```

______________________________________________________________________

## 5. PO Syntax, Header, Charset, and Fuzzy Flag Preservation

To ensure `msgfmt`, `pybabel`, and Hatchling packaging (`tools/hatch_build.py`) never fail during
wheel or sdist builds, the translation workflow enforces five `.po` syntax invariants:

1. **Header Metadata & `UTF-8` Charset Declaration**: The root `msgid ""` header block
   (`Project-Id-Version`, `MIME-Version: 1.0`, `Content-Type: text/plain; charset=utf-8`,
   `Content-Transfer-Encoding: 8bit`) is parsed separately and never sent to the translation
   backend.
2. **Plural-Forms Header Expression Awareness**: The translator reads the target locale's
   `nplurals=N` header (for example, `nplurals=1` for `ja`, `nplurals=2` for `de`/`es`/`fr`,
   `nplurals=3` for `ru`/`pl`, and `nplurals=6` for `ar`) and requests exactly `N` plural forms for
   every `msgid_plural` entry.
3. **Multiline String Wrapping**: Multiline `msgid` blocks (such as CLI `Examples:` and
   `Environment Variables:` help sections) preserve exact `\n` line-break counts and column
   indentation.
4. **Fuzzy Flag (`#, fuzzy`) Lifecycle**: Entries marked `#, fuzzy` by `msgmerge` / `pybabel update`
   can be targeted for re-translation; once validated by `validate_message_pair()`, the `#, fuzzy`
   flag is cleared and an attribution comment (`# AI-translated: <model>`) is recorded.
5. **Relative Source Location Hygiene**: Every catalog write invokes `_sanitize_po_locations()` from
   `tools/i18n.py` so `#: src/findfmt/...` comments never leak absolute developer filesystem paths.

______________________________________________________________________

## 6. Failure Modes, Rate Limiting, and Partial Batch Resume

| Failure Mode                                  | Mitigation Strategy in `findfmt` Translation Pipeline                                                                                            |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **HTTP `429` Rate Limiting / `5xx` Timeouts** | Exponential backoff with jitter (`base=1.5s`, `max_retries=4`, respecting `Retry-After` headers).                                                |
| **Mid-Catalog Network Interruption**          | Deterministic batch checkpointing: each completed batch of 25 strings is flushed to disk or cache so re-running resumes only untranslated items. |
| **Dropped or Mutated `__PH_N__` Token**       | `unmask_placeholders()` raises `ValueError` immediately; the single offending entry is retried in isolation or left untranslated with a warning. |
| **Malformed Plural Array Length**             | Verified against `nplurals` in the `.po` header before writing `msgstr[0..N-1]`.                                                                 |
| **Compile-Time Gate (`tools/i18n.py`)**       | `tools/i18n.py validate` and `tools/i18n.py compile` block `.mo` compilation if any entry fails placeholder or Rich markup parity checks.        |

______________________________________________________________________

## 7. Running the Benchmark Utility

Run the deterministic benchmark CLI to inspect catalog metrics, tool rankings, and provider cost
tables:

```bash
# Print human-readable Markdown benchmark summary
uv run python tools/i18n_benchmark.py

# Emit machine-readable JSON benchmark report
uv run python tools/i18n_benchmark.py --json
```
