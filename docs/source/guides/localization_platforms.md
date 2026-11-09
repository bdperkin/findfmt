# Managed Localization Platforms vs. Local CI Automation (ADR)

As `findfmt` scales localization coverage across Tier 1 through Tier 4 languages (see
[Multi-Language Localization Architecture & Phased Rollout Plan](localization_plan.md) and
[Open-Source Python AI Translation Benchmark & Architecture](ai_translation_benchmark.md)), this
document evaluates managed cloud localization platforms with native AI assistants (**POEditor**,
**Crowdin**, and **Localazy**) against `findfmt`'s self-hosted CLI pipeline
(`tools/i18n.py translate`) and records our Architecture Decision Record (ADR).

______________________________________________________________________

## 1. Platform Feature Evaluation

The table below compares **POEditor**, **Crowdin**, **Localazy**, and **`tools/i18n.py translate`**
across the technical requirements of `findfmt`'s GNU `gettext` catalog pipeline:

| Capability / Requirement                            | POEditor                                                                                      | Crowdin                                                                                               | Localazy                                                                             | Local CLI (`tools/i18n.py translate`)                                                                 |
| :-------------------------------------------------- | :-------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- |
| **PO Import/Export & `UTF-8` Fidelity**             | Native `.po`/`.pot` import/export; preserves `UTF-8` but can reflow line wrapping and headers | High-fidelity `.po` parser/exporter; preserves `UTF-8` and standard gettext headers                   | Native `.po` plugin via CLI/GitHub integration; preserves `UTF-8` encoding           | Direct `polib` AST manipulation; preserves exact headers, wrapping, and `charset=UTF-8`               |
| **Relative Source Location Comments (`#:`)**        | Preserves reference comments, though export formatting can differ from `babel`                | Preserves `#:` location comments; configurable export templates                                       | Preserves `#:` references when configured in `localazy.json`                         | Strictly enforces relative `src/findfmt/...` paths compatible with `check-no-absolute-locale-paths`   |
| **Python Placeholders (`{name}`, `%s`)**            | Highlights `%s` and `{name}` tokens in UI; QA checks warn on missing placeholders             | Native `python-format` / brace placeholder detection with automated QA checks before export           | Highlights placeholders and runs automated placeholder validation in review queues   | Pre-commit and runtime validator (`tools/i18n_validation.py`) rejects any mismatched `{...}` or `%s`  |
| **Rich Markup Preservation (`[bold]`, `[/]`)**      | Treats Rich `[style]` tags as plain text unless custom regex QA rules are configured          | Supports custom QA regex rules, but AI assistants can still translate inside bracketed tags           | Requires custom glossary/exclusion rules to prevent translating `[bold]` or `[cyan]` | Native Rich tag validator (`extract_rich_tags`) + system prompt constraints guarantee 100% tag safety |
| **Multi-Form `ngettext` Plurals (`nplurals=1..6`)** | Supports gettext plural forms (`msgid_plural` / `msgstr[N]`) mapped to target locale rules    | Full CLDR & GNU `gettext` plural support (`nplurals=1..6`, including Slavic 3-form and Arabic 6-form) | Native CLDR plural rules mapped to `msgstr[0..N-1]` slots on `.po` export            | Parses catalog `Plural-Forms` header directly (`tools/i18n_prompts.py`) and validates array arity     |
| **Built-in AI Translation Assistants**              | Automated AI translation via OpenAI/DeepL/Google (consumes plan or BYOK credits)              | Crowdin AI Assistant with context harvesting, TM leverage, and BYOK LLM provider support              | Localazy AI & ShareTM automated pre-translation pipelines                            | Built-in `polib` + OpenAI-compatible / local Ollama client with deterministic `T=0.0` batching        |
| **Continuous GitHub Synchronization**               | Webhook and GitHub repo connector opening automated sync PRs or commits                       | Official GitHub App and `crowdin/github-action` with bidirectional branch/PR synchronization          | Official GitHub Action (`localazy/upload` & `download`) and webhook sync             | Runs natively in local dev (`uv run python tools/i18n.py`) and GitHub Actions without external state  |

### 1.1. Key Technical Findings

1. **Rich Markup & CLI Flag Invariants:** Managed platforms natively understand `%s` and `{name}`
   placeholders when `#, python-format` or `#, python-brace-format` flags are present, but none
   natively parse Rich console markup (`[bold]`, `[cyan]`, `[/]`) out of the box. In contrast,
   `tools/i18n_validation.py` and `tools/i18n_prompts.py` enforce exact parity for `{brace}`
   placeholders, `%s` tokens, Rich markup tags, and `--cli-flags` before any `msgstr` is written to
   disk.
2. **Header & Diff Hygiene:** Cloud platforms regenerate `.po` files on export using their own
   serializers, which frequently alters header ordering, line wrapping, or `#:` source comment
   formatting. `findfmt`'s pre-commit hooks (`i18n-validate` and `check-no-absolute-locale-paths`)
   require deterministic `babel`/`polib` formatting with workspace-relative paths.

______________________________________________________________________

## 2. Cost, Privacy, and Open-Source Licensing Comparison

All three commercial platforms offer free plans for qualifying open-source projects, subject to
vendor approval and usage caps:

| Dimension                         | POEditor Open Source Plan                                                     | Crowdin for Open Source                                                      | Localazy OSS Plan                                                      | Local CLI (`tools/i18n.py translate`)                                              |
| :-------------------------------- | :---------------------------------------------------------------------------- | :--------------------------------------------------------------------------- | :--------------------------------------------------------------------- | :--------------------------------------------------------------------------------- |
| **Open-Source Eligibility**       | Manual application per public OSI-licensed repository                         | Manual application; requires active public OSI-licensed repo and attribution | OSS application program or community tier credits                      | Included in repository under MIT license; zero vendor approval required            |
| **String / Word Capacity**        | Up to 10,000 strings on standard OSS approval (renewable upon request)        | Unlimited strings and collaborators for approved non-commercial OSS projects | Tiered source-string limits depending on OSS sponsorship level         | Unlimited strings, locales, and branches                                           |
| **AI Translation Quotas**         | Limited built-in machine translation character quota; requires BYOK for scale | Requires BYOK API keys (OpenAI, Anthropic, Gemini, DeepL) for AI translation | Automated MT/AI requires paid tier or consumed translation credits     | Supports free local inference (`Ollama`) or low-cost BYOK API (~$0.35/100 locales) |
| **Data Privacy & Air-Gap Safety** | Source strings and contributor metadata stored on vendor cloud                | Source strings and translation memory hosted in Crowdin cloud                | Source strings shared with Localazy cloud and optional ShareTM network | 100% local execution with `Ollama` or direct ephemeral API calls                   |
| **Vendor Lock-In Risk**           | Medium (review history, comments, and glossary live in POEditor database)     | Medium (TM, review votes, and QA rules live in Crowdin project state)        | Medium (workflow queues and review states live in Localazy cloud)      | Zero (all prompts, glossaries, validators, and `.po` catalogs live in Git)         |

______________________________________________________________________

## 3. Contributor Auditing & Community Review Workflows

As `findfmt` expands across 100+ locales, native-speaker community contributors need a clear path to
audit, correct, and approve AI-generated translations:

### 3.1. Managed Cloud Platform Workflow

- **Strengths:** Non-technical translators can log into a web UI, filter by `fuzzy` or unapproved
  strings, view side-by-side translation memory suggestions, vote on alternatives, and leave
  per-string comments without installing Git or Python.
- **Drawbacks:**
  - Introduces dual sources of truth (Git PRs vs. cloud platform state), creating merge conflicts
    when developers run `uv run python tools/i18n.py extract` and update `.pot`/`.po` catalogs in
    feature branches.
  - Cloud exports can bypass local pre-commit checks until a sync PR fails in CI, requiring manual
    maintainer intervention to fix broken Rich tags or CLI flags.

### 3.2. Local Git + CI Auditing Workflow (`findfmt` Standard)

- **Strengths:**
  - AI-generated translations produced by `tools/i18n.py translate` can be marked with the standard
    GNU `gettext` `fuzzy` flag (`--mark-fuzzy`) or reviewed directly as clean `.po` diffs in GitHub
    Pull Requests.
  - Native speakers can edit `.po` files directly in the GitHub Web Editor (`github.dev`), Poedit
    desktop, or any text editor and submit a standard Pull Request.
  - Every contribution is automatically audited in CI by `uv run python tools/i18n.py validate` and
    `msgfmt --check`, guaranteeing zero broken placeholders, Rich tags, or plural forms.

______________________________________________________________________

## 4. Architecture Decision Record (ADR): Localization Pipeline

- **Status:** Accepted
- **Issue:** [#307](https://github.com/bdperkin/findfmt/issues/307) (Parent Epic:
  [#308](https://github.com/bdperkin/findfmt/issues/308))

### 4.1. Context

`findfmt` maintains a concise, highly technical CLI catalog (~150 entries) containing Python brace
placeholders (`{path}`, `{count}`), `printf` tokens (`%s`), Rich terminal markup (`[bold]`, `[/]`),
and CLI flags (`--format`, `--hidden`), alongside multi-language Sphinx documentation catalogs under
`docs/source/locale/`. We must choose between two primary localization architectures:

- **Option A (Local Open-Source CLI Automation + Git PRs):** Use `tools/i18n.py` (`extract`,
  `translate`, `validate`, `compile`, `status`) backed by `polib`, `babel`, and deterministic LLM
  batch translation (`tools/i18n_translate.py`), with all review and auditing conducted via GitHub
  Pull Requests and CI gates.
- **Option B (Managed Cloud Localization Platform with Bidirectional GitHub Sync):** Adopt a hosted
  platform (Crowdin, POEditor, or Localazy) as the primary translation hub synchronized to GitHub
  via webhooks or GitHub Actions.

### 4.2. Decision

We select **Option A: Fully local, open-source CLI automation via `tools/i18n.py translate` + Git
Pull Requests** as `findfmt`'s authoritative localization architecture.

### 4.3. Rationale

1. **Strict Structural Validation:** `tools/i18n_validation.py` enforces `findfmt`-specific
   invariants (Rich `[bold]`/`[/]` markup parity, `{brace}` and `%s` placeholder sets, `ngettext`
   plural array counts across `nplurals=1..6`, and relative `#:` location paths) both during LLM
   generation and in pre-commit/CI.
2. **Single Source of Truth & Zero Lock-In:** Keeping `.pot` templates, `.po` catalogs, domain
   glossaries (`tools/i18n_prompts.py`), and validation logic inside the Git repository eliminates
   bidirectional sync conflicts and external SaaS dependencies.
3. **Negligible Cost & Offline Reproducibility:** Translating the entire 150-message CLI catalog
   across 100 locales costs **~$0.35** via hosted APIs or **$0.00** using local `Ollama` models,
   with deterministic `T = 0.0` temperature and automatic fuzzy fallback.

### 4.4. Future Re-Evaluation Trigger (Optional Hybrid Overlay)

If community translation contributions from non-developer native speakers exceed **10+ active
external translators per release cycle** or if managing Sphinx documentation `.po` reviews via
GitHub PRs becomes a bottleneck, `findfmt` may enable **Crowdin for Open Source** (the strongest
managed candidate due to its full `nplurals=1..6` CLDR support and official GitHub Action) strictly
as a **downstream PR generator**—where all exported commits must still pass
`uv run python tools/i18n.py validate` and `pre-commit` in CI before merging.

______________________________________________________________________

## 5. End-to-End AI Localization Runbook

The steps below cover the complete workflow for localizing an existing or newly added language
catalog under **Option A**.

### 5.1. Configuring AI Backends

`tools/i18n_translate.py` uses Python's standard-library `urllib.request` with zero external SDK
dependencies. Configure your preferred provider via environment variables:

| Provider / Mode                         | Required Environment Variables                                                                                           | Example Invocation                                                                                                               |
| :-------------------------------------- | :----------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------- |
| **OpenAI** *(default)*                  | `OPENAI_API_KEY` (and optional `OPENAI_BASE_URL`)                                                                        | `uv run python -m tools.i18n translate de --backend openai --model gpt-4o-mini`                                                  |
| **Google Gemini** *(OpenAI-compatible)* | `OPENAI_API_KEY` and `OPENAI_BASE_URL` set to `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` | `uv run python -m tools.i18n translate de --backend openai --model gemini-2.5-flash`                                             |
| **Anthropic Claude**                    | `ANTHROPIC_API_KEY`                                                                                                      | `uv run python -m tools.i18n translate de --backend anthropic --model claude-3-5-haiku-latest`                                   |
| **Local Ollama** *(offline)*            | None (`ollama serve` running locally, or `OLLAMA_HOST`)                                                                  | `uv run python -m tools.i18n translate de --backend ollama --model qwen2.5:14b`                                                  |
| **Direct AI Coding Agent Translation**  | None (when working inside an offline AI coding assistant session)                                                        | Populate untranslated `msgstr` entries in `src/findfmt/locale/<locale>/LC_MESSAGES/findfmt.po` following `tools/i18n_prompts.py` |

### 5.2. Step-by-Step Catalog Translation Workflow

```bash
# Extract latest translatable strings into src/findfmt/locale/findfmt.pot
uv run python -m tools.i18n extract

# 2a. Initialize a brand-new locale catalog (e.g., pt_BR)
uv run python -m tools.i18n init pt_BR

# 2b. Or synchronize existing locale catalogs (e.g., de, fr, ja) with findfmt.pot
uv run python -m tools.i18n update

# Preview untranslated entry and batch counts without modifying files
uv run python -m tools.i18n translate de --dry-run

# Run batch AI translation (checkpoints progress after every 25-entry batch)
uv run python -m tools.i18n translate de --backend openai

# Validate placeholders ({name}, %s), Rich markup ([bold], [/]), POT sync, and completed-locale coverage
uv run python -m tools.i18n validate

# Compile .po catalogs into binary .mo catalogs
uv run python -m tools.i18n compile

# Or run the one-command sync pipeline (extract -> update -> fill en -> AI-translate COMPLETE_LOCALES -> compile)
uv run python -m tools.i18n sync --backend openai
```

### 5.3. Runtime Locale Conventions & Test Registration

When onboarding a new language `<locale>`, verify the following runtime fallbacks and test suites so
localized formatting works even on minimal container or CI hosts without OS locale packs installed:

1. **Completed-Locale Gate (`tools/i18n_sync.py`):**
   - Once `<locale>` is 100% translated, add it to `COMPLETE_LOCALES` in `tools/i18n_sync.py` so the
     `i18n-catalog-check` pre-commit hook and `uv run python -m tools.i18n sync` enforce zero
     untranslated or `fuzzy` entries whenever new source strings are added.
2. **Territory & Numeric Grouping Fallbacks (`src/findfmt/i18n.py`):**
   - Add `<locale>` to `_LANG_TO_TERRITORY` if its primary ISO territory code differs from
     `<LOCALE>.upper()` (for example, `"ja": "JP"`, `"zh": "CN"`, `"hi": "IN"`).
   - Add `<locale>`'s decimal separator, thousands separator, and digit grouping to
     `_REGIONAL_DEFAULTS` in `src/findfmt/i18n.py` (or South Asian `[3, 2, 0]` grouping in
     `_get_numeric_conventions()`).
3. **Timestamp Format Fallback (`src/findfmt/utils/strings.py`):**
   - Add `<locale>`'s `strftime` fallback pattern to `fallback_formats` in `resolve_time_format()`.
4. **Unit & Integration Tests (`tests/unit/test_i18n_localization.py`):**
   - Include `<locale>` in `test_catalog_entries_placeholder_parity_and_runtime_formatting` and add
     assertions for localized CLI `--help`, summary panels, and plural boundaries.
