# findfmt Documentation

```{image} _static/logo.svg
:alt: findfmt Logo
:align: center
:width: 600px
```

<p align="center">
  <a href="https://github.com/bdperkin/findfmt/actions/workflows/ci.yml"><img src="https://github.com/bdperkin/findfmt/actions/workflows/ci.yml/badge.svg" alt="CI Status" /></a>
  <a href="https://github.com/bdperkin/findfmt/actions/workflows/codeql.yml"><img src="https://github.com/bdperkin/findfmt/actions/workflows/codeql.yml/badge.svg" alt="CodeQL Analysis" /></a>
  <a href="https://github.com/bdperkin/findfmt/actions/workflows/docs.yml"><img src="https://github.com/bdperkin/findfmt/actions/workflows/docs.yml/badge.svg" alt="Documentation Status" /></a>
  <a href="https://results.pre-commit.ci/latest/github/bdperkin/findfmt/main"><img src="https://results.pre-commit.ci/badge/github/bdperkin/findfmt/main.svg" alt="pre-commit.ci status" /></a>
  <a href="https://codecov.io/gh/bdperkin/findfmt"><img src="https://codecov.io/gh/bdperkin/findfmt/branch/main/graph/badge.svg" alt="Coverage" /></a>
</p>

<p align="center">
  <a href="https://pypi.org/project/findfmt/"><img src="https://img.shields.io/pypi/v/findfmt.svg?logo=pypi&logoColor=white" alt="PyPI Version" /></a>
  <a href="https://pypi.org/project/findfmt/"><img src="https://img.shields.io/pypi/pyversions/findfmt.svg?logo=python&logoColor=white" alt="Python Versions" /></a>
  <a href="https://pypi.org/project/findfmt/"><img src="https://img.shields.io/pypi/wheel/findfmt.svg" alt="PyPI Wheel" /></a>
  <a href="https://github.com/bdperkin/findfmt/pkgs/container/findfmt"><img src="https://img.shields.io/badge/GHCR-container-blue?logo=docker&logoColor=white" alt="GHCR Container" /></a>
  <a href="https://github.com/bdperkin/findfmt/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
</p>

<p align="center">
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv" /></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" /></a>
  <a href="https://github.com/astral-sh/ty"><img src="https://img.shields.io/badge/type--checked-ty-blueviolet" alt="Type-checked: ty" /></a>
  <a href="https://interrogate.readthedocs.io/"><img src="https://img.shields.io/badge/interrogate-100%25-brightgreen" alt="Docstring Coverage: 100%" /></a>
  <a href="https://conventionalcommits.org"><img src="https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg" alt="Conventional Commits" /></a>
  <a href="accessibility.html"><img src="https://img.shields.io/badge/accessibility-WCAG%202.1%20AA-blue" alt="Accessibility WCAG 2.1 AA" /></a>
</p>

**findfmt** is a high-performance, `.gitignore`-aware file discovery and classification suite. It
locates files by content format, shebang, and MIME tag rather than relying strictly on file
extensions.

## Core Capabilities

- **Intelligent Classification**: Powered by the `identify` engine and content heuristics to
  identify file types (e.g. Python, Shell, YAML, JSON, Executable) even when filenames lack
  extensions.
- **Git-Aware Traversal**: Automatically prunes directories and files matched by `.gitignore` and
  `.git/info/exclude` rules early in traversal.
- **Deterministic Output**: Always produces clean, relative, alphabetically sorted file paths ready
  for Unix pipelines and `xargs`.
- **Modern Python Architecture**: Built with a strict `uv`-first methodology, 100% test coverage,
  and strict static type checking.

```{toctree}
:maxdepth: 2
:caption: User Guide

guides/index
```

```{toctree}
:maxdepth: 2
:caption: CLI Reference

cli/index
```

```{toctree}
:maxdepth: 2
:caption: API Documentation

api/index
```

```{toctree}
:maxdepth: 1
:caption: Quality & Architecture

quality/index
```

```{toctree}
:maxdepth: 1
:caption: Community & Governance

accessibility
```

______________________________________________________________________

## Community & Feedback

- **Source Code**: [github.com/bdperkin/findfmt](https://github.com/bdperkin/findfmt)
- **Issue Tracker**: Report bugs, request formats, or propose features on
  [GitHub Issues](https://github.com/bdperkin/findfmt/issues).
- **Contributing**: Review the
  [Contributing Guidelines](https://github.com/bdperkin/findfmt/blob/main/CONTRIBUTING.md) to get
  started with local development.
- **Accessibility**: See our [Accessibility Statement](accessibility.md) for supported assistive
  technologies and barrier reporting.
