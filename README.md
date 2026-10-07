<p align="center">
  <img src="https://raw.githubusercontent.com/bdperkin/findfmt/main/assets/logo.svg" alt="findfmt Logo" width="600" />
</p>

<p align="center">
  <a href="https://github.com/bdperkin/findfmt/actions/workflows/ci.yml"><img src="https://github.com/bdperkin/findfmt/actions/workflows/ci.yml/badge.svg" alt="CI Status" /></a>
  <a href="https://github.com/bdperkin/findfmt/actions/workflows/codeql.yml"><img src="https://github.com/bdperkin/findfmt/actions/workflows/codeql.yml/badge.svg" alt="CodeQL Analysis" /></a>
  <a href="https://github.com/bdperkin/findfmt/actions/workflows/docs.yml"><img src="https://github.com/bdperkin/findfmt/actions/workflows/docs.yml/badge.svg" alt="Documentation Status" /></a>
  <a href="https://results.pre-commit.ci/latest/github/bdperkin/findfmt/main"><img src="https://results.pre-commit.ci/badge/github/bdperkin/findfmt/main.svg" alt="pre-commit.ci status" /></a>
  <a href="https://codecov.io/gh/bdperkin/findfmt"><img src="https://codecov.io/gh/bdperkin/findfmt/branch/main/graph/badge.svg" alt="Coverage" /></a>
  <a href="https://www.bestpractices.dev/projects/15282"><img src="https://www.bestpractices.dev/projects/15282/badge" alt="OpenSSF Best Practices" /></a>
</p>

<p align="center">
  <a href="https://pypi.org/project/findfmt/"><img src="https://img.shields.io/pypi/v/findfmt?logo=pypi&logoColor=white" alt="PyPI Version" /></a>
  <a href="https://pypi.org/project/findfmt/"><img src="https://img.shields.io/pypi/pyversions/findfmt?logo=python&logoColor=white" alt="Python Versions" /></a>
  <a href="https://pypi.org/project/findfmt/"><img src="https://img.shields.io/pypi/wheel/findfmt?logo=pypi&logoColor=white" alt="PyPI Wheel" /></a>
  <a href="https://github.com/bdperkin/findfmt/pkgs/container/findfmt"><img src="https://img.shields.io/badge/GHCR-container-blue?logo=docker&logoColor=white" alt="GHCR Container" /></a>
  <a href="https://github.com/bdperkin/findfmt/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
</p>

<p align="center">
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv" /></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" /></a>
  <a href="https://github.com/astral-sh/ty"><img src="https://img.shields.io/badge/type--checked-ty-blueviolet" alt="Type-checked: ty" /></a>
  <a href="https://interrogate.readthedocs.io/"><img src="https://img.shields.io/badge/interrogate-100%25-brightgreen" alt="Docstring Coverage: 100%" /></a>
  <a href="https://conventionalcommits.org"><img src="https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg" alt="Conventional Commits" /></a>
  <a href="https://github.com/bdperkin/findfmt/blob/main/ACCESSIBILITY.md"><img src="https://img.shields.io/badge/accessibility-WCAG%202.1%20AA-blue" alt="Accessibility WCAG 2.1 AA" /></a>
</p>

______________________________________________________________________

> **A `.gitignore`-aware file discovery and classification suite that locates files by content
> format, shebang, and MIME tag for automated linting, formatting, and CI pipelines.**

## 1. Why findfmt?

Unlike traditional `find` or globbing tools that rely strictly on file extensions, `findfmt`:

- **Understands file content**: Identifies format by content, shebang (`#!/usr/bin/env python3`),
  and MIME types using the `identify` engine.
- **Respects Git**: Traverses trees hierarchically while pruning `.gitignore` and
  `.git/info/exclude` paths early before descending into large directories (e.g. `node_modules/`,
  `.venv/`).
- **Deterministic**: Always returns clean, relative, deterministically sorted paths optimized for
  subshells, xargs, and automation.

______________________________________________________________________

## 2. Installation

### 2.1. With `uv` (Recommended)

Run directly with `uvx`:

```bash
uvx findfmt --help
```

Install globally:

```bash
uv tool install findfmt
```

Or add to your project:

```bash
uv add findfmt
```

### 2.2. With `pip`

```bash
pip install findfmt
```

### 2.3. With Docker / Container

```bash
docker pull ghcr.io/bdperkin/findfmt:latest
docker run --rm -v "$(pwd)":/workspace -w /workspace ghcr.io/bdperkin/findfmt:latest -t python
```

______________________________________________________________________

## 3. Usage

### 3.1. Locate Files by Tag / Format

```bash
# Locate all Python files
findfmt -t python

# Locate all YAML and JSON files
findfmt -t yaml,json

# Locate shell scripts
findfmt -t shell
```

### 3.2. Shebang Filtering

```bash
# Locate files with bash shebang
findfmt --shebang bash

# Locate scripts executing with python
findfmt --shebang python
```

### 3.3. Pipe Safely to Linters and Tools

Use `-0` for NUL-delimited output with `xargs -0`:

```bash
# Format discovered Python files
findfmt -t python -0 | xargs -0 ruff format

# Lint shell scripts with shellcheck
findfmt -t shell -0 | xargs -r -0 shellcheck
```

### 3.4. Inspect Tags & Summaries

```bash
# Print matched files and their classification tags
findfmt -l -t python

# Print summary statistics to stderr
findfmt -s
```

### 3.5. Structured Data Serialization

Export discovery results to machine-readable formats for pipelines, analysis, and notebooks:

```bash
# Export JSON array of file metadata
findfmt -t python --format json

# Stream NDJSON (one JSON record per line)
findfmt -f jsonl

# Generate clean YAML document
findfmt -t yaml -f yaml

# Generate Jupyter Notebook with pandas DataFrame ingestion
findfmt -f ipynb > discovery.ipynb
```

### 3.6. Command Aliases & Entry Points

`findfmt` installs dedicated executable wrappers for frequent operations:

| Command                                | Equivalent To                              | Description                               |
| -------------------------------------- | ------------------------------------------ | ----------------------------------------- |
| `findfiles [PATHS...]`                 | `findfmt --hidden`                         | Traverse all files including hidden files |
| `findfilemime [PATHS...]`              | `findfmt --hidden --list-tags`             | List files with MIME & format tags        |
| `findfilefmt [TAG] [PATHS...]`         | `findfmt --hidden --tag [TAG]`             | Filter files by format tag                |
| `findshebang [INTERPRETER] [PATHS...]` | `findfmt --hidden --shebang [INTERPRETER]` | Filter scripts by shebang pattern         |
| `findfmt0 [PATHS...]`                  | `findfmt --hidden --print0`                | NUL-delimited output for `xargs -0`       |
| `findsummary [PATHS...]`               | `findfmt --hidden --summary`               | Output summary statistics to `stderr`     |

______________________________________________________________________

## 4. CLI Options

| Flag                                             | Description                                                |
| ------------------------------------------------ | ---------------------------------------------------------- |
| `-t, --tag, --type TAG`                          | Match files containing specified tag(s)                    |
| `-e, --exclude, --exclude-tag TAG`               | Exclude files containing specified tag(s)                  |
| `--all-tags` / `--no-all-tags`                   | Require match against all include tags (AND logic)         |
| `--shebang INTERPRETER`                          | Match shebang interpreter name or pattern                  |
| `--no-ignore` / `--ignore`                       | Toggle respecting `.gitignore` files                       |
| `--hidden` / `--no-hidden`                       | Toggle inspecting hidden files and directories             |
| `-L, --follow-symlinks` / `--no-follow-symlinks` | Toggle following filesystem symbolic links                 |
| `-f, --format FORMAT`                            | Output format (`text`, `json`, `jsonl`, `yaml`, `ipynb`)   |
| `-0, --print0` / `--no-print0`                   | NUL-delimited output for `xargs -0`                        |
| `-l, --list-tags` / `--no-list-tags`             | Toggle printing tags alongside file paths                  |
| `-s, --summary` / `--no-summary`                 | Toggle summary frequency statistics to `stderr`            |
| `--absolute` / `--no-absolute`                   | Toggle absolute vs relative output paths                   |
| `--known-tags`                                   | List all supported classification tags and exit            |
| `-v, -V, --version`                              | Display version (`--verbose` adds runtime diagnostics)     |
| `--diagnostics`                                  | Display runtime environment diagnostics and exit           |
| `--help-all`                                     | Display comprehensive manual, env vars, and exit codes     |
| `-- [PATHS...]`                                  | POSIX terminator: treat following tokens strictly as paths |

______________________________________________________________________

## 5. Development & Testing

This project enforces 100% test coverage and strict type checking:

```bash
# Clone the repository
git clone https://github.com/bdperkin/findfmt.git
cd findfmt

# Install dependencies with uv
uv sync --all-groups

# Run tests and verify 100% coverage
uv run pytest

# Run linting and typing
uv run ruff check
uv run ty check

# Run full verification suite
uv run python tools/verify_quality.py
```

______________________________________________________________________

## 6. Governance & Community

- [Contributing Guidelines](https://github.com/bdperkin/findfmt/blob/main/CONTRIBUTING.md)
- [Code of Conduct](https://github.com/bdperkin/findfmt/blob/main/CODE_OF_CONDUCT.md)
- [Security Policy](https://github.com/bdperkin/findfmt/blob/main/SECURITY.md)
- [Support Information](https://github.com/bdperkin/findfmt/blob/main/SUPPORT.md)
- [Accessibility Statement](https://github.com/bdperkin/findfmt/blob/main/ACCESSIBILITY.md)

## 7. License

[MIT License](https://github.com/bdperkin/findfmt/blob/main/LICENSE) © 2026 Brandon Perkins.
