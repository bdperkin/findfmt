# `AGENTS.md`: Developer & AI Agent Guidelines for findfmt

Welcome to the `findfmt` repository. This document serves as the authoritative technical reference,
architecture guide, and behavioral standard for all AI coding agents and human developers
contributing to this codebase.

## 1. Project Overview & Architecture

`findfmt` is a modern, high-performance Python command-line utility and library designed for
`.gitignore`-aware file discovery and content format, shebang, and MIME tag classification.

### 1.1. Core Module Layout

- `src/findfmt/__init__.py` & `src/findfmt/__main__.py`: Package root exporting the public Python
  API (`FileInfo`, `TraversalConfig`, `find_files`, `classify_file`, `get_formatter`,
  `FormatRegistry`) and `python -m findfmt` execution entry point.
- `src/findfmt/cli/`: Command-line interface powered by `Typer` and `Rich`:
  - `main.py`: Primary `Typer` application (`app`) and CLI invocation entry point.
  - `options.py`: CLI option declarations (`--hidden`, `--tag`, `--list-tags`, `--format`, etc.).
  - `runner.py`: Execution pipeline coordinating traversal, classification, formatting, and paging.
  - `config.py`, `config_schema.py`, `file_config.py`: Layered configuration resolution and schema
    validation (`pyproject.toml`, `.findfmt.toml`, XDG user configuration, and CLI overrides).
  - `help.py`: Categorized `--help`, `--help-all`, and man-page help rendering.
  - `output_sink.py`, `pager.py`, `signals.py`: Atomic `--output` file writing, TTY auto-paging, and
    POSIX signal handling (`SIGINT` exit code `130`, `SIGPIPE` clean teardown).
  - `entrypoints.py`: Specialized CLI wrapper commands (`findfiles`, `findfilefmt`, `findfilemime`,
    `findfmt0`, `findshebang`, `findsummary`).
  - `diagnostics.py`, `summary.py`, `terminal.py`: Structured error diagnostics, summary frequency
    tables, and terminal sanitization.
- `src/findfmt/traversal/`: Directory walking and filtering engine:
  - `engine.py`: Core traversal loop yielding matched `FileInfo` records.
  - `ignore.py`: Hierarchical `.gitignore`, `.git/info/exclude`, and global ignore evaluation via
    `pathspec`.
  - `patterns.py`, `filters.py`, `tags.py`: Glob pattern matching (`-P`, `-I`), tag/shebang filters,
    and directory pruning (`--prune`).
  - `boundaries.py`, `devices.py`, `symlinks.py`, `sorting.py`: Depth limits (`-L`), `--filelimit`,
    single-filesystem confinement (`-x`), symlink loop detection (`-l`), and deterministic sorting.
- `src/findfmt/classifier.py`: File content inspection, extension/filename lookup, magic-byte
  sniffing, shebang interpreter extraction, and `identify` tag/MIME classification.
- `src/findfmt/formatters/`: Pluggable output serializers (`base.py`, `text.py`, `delimited.py`,
  `structured.py`, `tree.py`, `visual.py`, `markup.py`, `html_formatter.py`, `xml_formatter.py`,
  `badges.py`, `glyphs.py`) supporting `text`, `table`, `tree`, `json`, `jsonl`, `yaml`, `ipynb`,
  `csv`, `csv-table`, `tsv`, `markdown`, `rst`, `xml`, and `html`.
- `src/findfmt/parsers/`: `--from-file` and `stdin` path-list parsers (`engine.py`,
  `flat_parser.py`, `tab_parser.py`, `symlink_parser.py`) supporting `--offline` virtual
  classification, NUL-delimited input, and root-boundary confinement (`--allow-outside-root`).
- `src/findfmt/models.py`, `metadata.py`, `sizes.py`, `exceptions.py`, `i18n.py`, `utils/`: Core
  data models, POSIX metadata formatting, IEC/SI size formatting, domain exceptions, and GNU
  `gettext` internationalization (`src/findfmt/locale/`).
- `tools/`: Maintainer and CI automation scripts (`verify_quality.py`, `dep_matrix.py`,
  `line_linter.py`, `suppression_auditor.py`, `api_surface.py`, `i18n.py`, `i18n_sync.py`,
  `i18n_translate.py`, `i18n_validation.py`, `i18n_prompts.py`, `hatch_build.py`, `smoke_wheel.py`,
  `release_notes.py`, `verify_release_version.py`, `benchmark.py`).
- `tests/`: Comprehensive `pytest` suites mirroring the source layout (`tests/unit/`,
  `tests/integration/`, `tests/fuzz/`).

### 1.2. CLI Entry Points & Wrapper Commands

Defined under `[project.scripts]` in `pyproject.toml`:

| Command        | Entry Point                     | Default Behavior                                  |
| -------------- | ------------------------------- | ------------------------------------------------- |
| `findfmt`      | `findfmt.cli:app`               | Primary CLI with full flag and format control     |
| `findfiles`    | `findfmt.cli:main_findfiles`    | Equivalent to `findfmt --hidden`                  |
| `findfilemime` | `findfmt.cli:main_findfilemime` | Equivalent to `findfmt --hidden --list-tags`      |
| `findfilefmt`  | `findfmt.cli:main_findfilefmt`  | Equivalent to `findfmt --hidden --tag <TAG>`      |
| `findshebang`  | `findfmt.cli:main_findshebang`  | Equivalent to `findfmt --hidden --shebang <EXPR>` |
| `findfmt0`     | `findfmt.cli:main_findfmt0`     | Equivalent to `findfmt --hidden --print0`         |
| `findsummary`  | `findfmt.cli:main_findsummary`  | Equivalent to `findfmt --hidden --summary`        |

## 2. Development & Test Workflow

This project uses a `uv`-first Python toolchain alongside strict static analysis and `pre-commit`
hooks.

### 2.1. Environment Setup & Dependencies

```bash
# Sync virtual environment and all development, test, lint, and docs dependency groups
uv sync --all-groups

# Or sync with all extras and dev dependencies
uv sync --all-extras --dev
```

### 2.2. Running Tests

```bash
# Execute the complete test suite with pytest (enforces 100% statement and branch coverage)
uv run pytest

# Run the full local quality verification suite
uv run python tools/verify_quality.py
```

### 2.3. Linting, Formatting, and Pre-Commit

Before committing code, ensure all static analysis checks and `pre-commit` hooks pass cleanly:

```bash
# Run all 25+ pre-commit hooks across the repository
uv run pre-commit run --all-files --show-diff-on-failure

# Run Ruff linter, formatter check, and ty static type checker directly
uv run ruff check
uv run ruff format --check
uv run ty check
```

When modifying public symbols in `__all__` or translatable strings wrapped in `_()` / `ngettext()`:

```bash
# Regenerate public API surface snapshot after intentional public API updates
uv run python tools/api_surface.py --write

# Extract, AI-translate, validate, and compile gettext message catalogs
uv run python -m tools.i18n extract
uv run python -m tools.i18n translate <locale> --dry-run
uv run python -m tools.i18n validate
uv run python -m tools.i18n compile
```

## 3. Coding Standards & Conventions

- **Python Version & Type Hinting:** Target Python `>=3.11` (tested through Python `3.15` and
  `3.16-dev`). Include `from __future__ import annotations` in every Python module and provide
  complete, strict type annotations verified by `ty`.
- **CLI & Output:** Use `Typer` for command definitions and `Rich` (via
  `src/findfmt/cli/diagnostics.py`, `src/findfmt/cli/terminal.py`, and
  `src/findfmt/cli/output_sink.py`) for terminal tables, panels, streams, and error displays. Do not
  use raw `print()` statements for core CLI output or errors.
- **Error Handling & Exit Codes:** Fail gracefully with descriptive, localized diagnostics via
  `src/findfmt/cli/diagnostics.py` rather than unhandled tracebacks, honoring the formal exit-code
  contract (`0` success, `1` runtime error or `--exit-status` no-match, `2` usage/configuration
  error, `130` `SIGINT`).
- **Zero Unjustified Suppressions:** `tools/suppression_auditor.py` runs in strict mode. Never add
  blanket or unapproved `# noqa`, `# type: ignore`, or `# pragma: no cover` comments; resolve root
  causes directly in code and types.
- **Internationalization & Prose:** Wrap user-facing CLI strings in `_()` or `ngettext()` from
  `findfmt.i18n`, keep `.po`/`.pot` location comments relative (`tools/i18n.py`), and ensure
  Markdown files pass `mdformat`, `pymarkdown`, `codespell`, and `vale`.

## 4. Refactoring & File Decomposition Policy

- **Hard Ceiling vs. Target:** While the hard system limit is 500 lines per file
  (`tools/line_linter.py`), treat **350 lines** as your operational ceiling.
- **No Obfuscation:** If a file grows too large, **do not** resort to one-liners, nested inline
  helper functions, or dense compression to stay under the limit.
- **Mandatory File Splitting:** Proactively create new files (for example, splitting utilities out
  of monolithic entry points or breaking down large test suites) and import them cleanly. Modular
  readability always overrides file-count minimization.

## 5. AI Agent Guidelines & Behavioral Boundaries

- **Preserve Modularity:** Never dump new CLI flags, matchers, or format rules into monolithic
  functions. Keep concerns strictly separated between discovery (`src/findfmt/traversal/`),
  classification (`src/findfmt/classifier.py`), and presentation (`src/findfmt/formatters/` and
  `src/findfmt/cli/`).
- **Test Coverage:** Every bug fix, new file format tag, or CLI feature must be accompanied by
  corresponding unit tests in `tests/` maintaining **100% statement and branch coverage**.
- **Atomic Changes:** Make clean, isolated modifications that respect `pre-commit` formatting,
  linting, line-count (`tools/line_linter.py`), suppression-audit (`tools/suppression_auditor.py`),
  and type-checking (`ty`) rules.
