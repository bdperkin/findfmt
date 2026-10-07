<p align="center">
  <img src="assets/logo.svg" alt="findfmt Logo" width="600" />
</p>

<p align="center">
  <a href="https://github.com/bdperkin/findfmt/actions/workflows/ci.yml"><img src="https://github.com/bdperkin/findfmt/actions/workflows/ci.yml/badge.svg" alt="CI Status" /></a>
  <a href="https://codecov.io/gh/bdperkin/findfmt"><img src="https://codecov.io/gh/bdperkin/findfmt/branch/main/graph/badge.svg" alt="Coverage" /></a>
  <a href="https://pypi.org/project/findfmt/"><img src="https://img.shields.io/pypi/v/findfmt.svg" alt="PyPI Version" /></a>
  <a href="https://pypi.org/project/findfmt/"><img src="https://img.shields.io/pypi/pyversions/findfmt.svg" alt="Python Versions" /></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" /></a>
  <a href="https://github.com/bdperkin/findfmt/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
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

______________________________________________________________________

## 4. CLI Options

| Flag                           | Description                                        |
| ------------------------------ | -------------------------------------------------- |
| `-t, --tag, --type`            | Match files containing specified tag(s)            |
| `-e, --exclude, --exclude-tag` | Exclude files containing specified tag(s)          |
| `--all-tags`                   | Require match against all include tags (AND logic) |
| `--shebang`                    | Match shebang interpreter name or pattern          |
| `--no-ignore`                  | Do not prune paths matching `.gitignore`           |
| `--hidden`                     | Inspect hidden files and directories               |
| `-0, --print0`                 | NUL-delimited output for `xargs -0`                |
| `-l, --list-tags`              | Print tags alongside file paths                    |
| `-s, --summary`                | Print match frequencies to stderr                  |
| `--absolute`                   | Output absolute rather than relative paths         |
| `--known-tags`                 | List all supported classification tags             |
| `-v, --version`                | Display version and exit                           |

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

- [Contributing Guidelines](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)
- [Support Information](SUPPORT.md)
- [Accessibility Statement](ACCESSIBILITY.md)

## 7. License

[MIT License](LICENSE) © 2026 Brandon Perkins.
