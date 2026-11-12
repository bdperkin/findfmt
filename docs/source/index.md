# findfmt Documentation

````{only} not (latex or latexpdf)
```{image} _static/logo.svg
:alt: findfmt Logo
:align: center
:width: 600px
```
````

````{only} latex or latexpdf
```{image} _static/logo.pdf
:alt: findfmt Logo
:align: center
:width: 400px
```
````

```{only} not (latex or latexpdf or epub or texinfo)
[![PyPI Version](https://img.shields.io/pypi/v/findfmt?logo=pypi&logoColor=white)](https://pypi.org/project/findfmt/)
[![Python Versions](https://img.shields.io/pypi/pyversions/findfmt?logo=python&logoColor=white)](https://pypi.org/project/findfmt/)
[![PyPI Wheel](https://img.shields.io/pypi/wheel/findfmt?logo=pypi&logoColor=white)](https://pypi.org/project/findfmt/#files)
[![PyPI Status](https://img.shields.io/pypi/status/findfmt?logo=pypi&logoColor=white)](https://pypi.org/project/findfmt/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/findfmt?logo=pypi&logoColor=white)](https://pypistats.org/packages/findfmt)
[![GitHub Release](https://img.shields.io/github/v/release/bdperkin/findfmt?logo=github)](https://github.com/bdperkin/findfmt/releases/latest)
[![GHCR Container](https://img.shields.io/badge/GHCR-ghcr.io%2Fbdperkin%2Ffindfmt-2496ED?logo=docker&logoColor=white)](https://github.com/bdperkin/findfmt/pkgs/container/findfmt)
[![Platforms](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-informational?logo=linux&logoColor=white)](https://github.com/bdperkin/findfmt/actions/workflows/ci.yml)
[![Hatch](https://img.shields.io/badge/build%20system-hatch-orange?logo=python&logoColor=white)](https://hatch.pypa.io/)

[![CI Status](https://img.shields.io/github/actions/workflow/status/bdperkin/findfmt/ci.yml?branch=main&label=CI&logo=github)](https://github.com/bdperkin/findfmt/actions/workflows/ci.yml)
[![Dependency Matrix](https://img.shields.io/github/actions/workflow/status/bdperkin/findfmt/dependency-matrix.yml?branch=main&label=deps%20matrix&logo=github)](https://github.com/bdperkin/findfmt/actions/workflows/dependency-matrix.yml)
[![Docs Build](https://img.shields.io/github/actions/workflow/status/bdperkin/findfmt/docs.yml?branch=main&label=docs&logo=readthedocs&logoColor=white)](https://github.com/bdperkin/findfmt/actions/workflows/docs.yml)
[![Vale Prose Lint](https://img.shields.io/github/actions/workflow/status/bdperkin/findfmt/vale.yml?branch=main&label=vale&logo=markdown&logoColor=white)](https://github.com/bdperkin/findfmt/actions/workflows/vale.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/bdperkin/findfmt/main.svg)](https://results.pre-commit.ci/latest/github/bdperkin/findfmt/main)
[![Last Commit](https://img.shields.io/github/last-commit/bdperkin/findfmt/main?logo=git&logoColor=white)](https://github.com/bdperkin/findfmt/commits/main)

[![Coverage](https://codecov.io/gh/bdperkin/findfmt/branch/main/graph/badge.svg)](https://codecov.io/gh/bdperkin/findfmt)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![Docstring Coverage: 100%](https://img.shields.io/badge/interrogate-100%25-brightgreen?logo=readthedocs&logoColor=white)](https://interrogate.readthedocs.io/)
[![Tested with Hypothesis](https://img.shields.io/badge/hypothesis-tested-brightgreen?logo=python&logoColor=white)](https://hypothesis.readthedocs.io/)
[![PEP 561 Typed](https://img.shields.io/badge/typing-PEP%20561%20py.typed-3776AB?logo=python&logoColor=white)](https://peps.python.org/pep-0561/)
[![Deptry](https://img.shields.io/badge/deptry-checked-informational)](https://deptry.com/)
[![Vulture](https://img.shields.io/badge/vulture-checked-informational)](https://github.com/jendrikseipp/vulture)
[![Xenon](https://img.shields.io/badge/xenon-monitored-informational)](https://xenon.readthedocs.io/)
[![Codespell](https://img.shields.io/badge/codespell-checked-informational)](https://github.com/codespell-project/codespell)
[![PyMarkdown](https://img.shields.io/badge/pymarkdown-linted-informational?logo=markdown&logoColor=white)](https://pymarkdown.readthedocs.io/)

[![CodeQL](https://img.shields.io/github/actions/workflow/status/bdperkin/findfmt/codeql.yml?branch=main&label=CodeQL&logo=github)](https://github.com/bdperkin/findfmt/actions/workflows/codeql.yml)
[![zizmor](https://img.shields.io/github/actions/workflow/status/bdperkin/findfmt/zizmor.yml?branch=main&label=zizmor&logo=githubactions&logoColor=white)](https://github.com/bdperkin/findfmt/actions/workflows/zizmor.yml)
[![ClusterFuzzLite](https://img.shields.io/github/actions/workflow/status/bdperkin/findfmt/cflite.yml?branch=main&label=ClusterFuzzLite&logo=google&logoColor=white)](https://github.com/bdperkin/findfmt/actions/workflows/cflite.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/bdperkin/findfmt/badge)](https://securityscorecards.dev/viewer/?uri=github.com/bdperkin/findfmt)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/15282/badge)](https://www.bestpractices.dev/projects/15282)
[![SLSA Provenance](https://img.shields.io/badge/SLSA-build%20provenance-2088FF?logo=githubactions&logoColor=white)](https://github.com/bdperkin/findfmt/attestations)
[![Security Policy](https://img.shields.io/badge/security-policy-blue?logo=securityscorecard&logoColor=white)](https://github.com/bdperkin/findfmt/blob/main/SECURITY.md)

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue?logo=sphinx&logoColor=white)](https://bdperkin.github.io/findfmt/)
[![i18n Languages](https://img.shields.io/badge/i18n-en%20%C2%B7%20es%20%C2%B7%20fr%20%C2%B7%20de%20%C2%B7%20ja-blue)](https://bdperkin.github.io/findfmt/)
[![License: MIT](https://img.shields.io/github/license/bdperkin/findfmt?color=blue&logo=opensourceinitiative&logoColor=white)](https://github.com/bdperkin/findfmt/blob/main/LICENSE)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-FE5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/)
[![Keep a Changelog](https://img.shields.io/badge/changelog-Keep%20a%20Changelog-E05735?logo=keepachangelog&logoColor=white)](https://github.com/bdperkin/findfmt/blob/main/CHANGELOG.md)
[![Accessibility WCAG 2.1 AA](https://img.shields.io/badge/WCAG-2.1%20AA-005A9C?logo=w3c&logoColor=white)](accessibility.md)
[![GitHub Issues](https://img.shields.io/github/issues/bdperkin/findfmt?logo=github)](https://github.com/bdperkin/findfmt/issues)
[![GitHub Stars](https://img.shields.io/github/stars/bdperkin/findfmt?style=flat&logo=github)](https://github.com/bdperkin/findfmt/stargazers)
```

**findfmt** is a high-performance, `.gitignore`-aware file discovery and classification suite. It
locates files by content format, shebang, and MIME tag rather than relying strictly on file
extensions.

## 1. Core Capabilities

- **Intelligent Classification**: Powered by the `identify` engine and content heuristics to
  identify file types (e.g. Python, Shell, YAML, JSON, Executable) even when filenames lack
  extensions.
- **Git-Aware Traversal**: Automatically prunes directories and files matched by `.gitignore` and
  `.git/info/exclude` rules early in traversal.
- **Deterministic Output**: Always produces clean, relative, alphabetically sorted file paths ready
  for Unix pipelines and `xargs`.
- **Modern Python Architecture**: Built with a strict `uv`-first methodology, 100% test coverage,
  and strict static type checking.

## 2. Quickstart

### 2.1. Direct Execution & Installation

Execute immediately with `uvx` without an explicit installation step:

```bash
uvx findfmt --help
uvx findfmt -t python
```

Install as an isolated user tool or project dependency:

```bash
# Global tool installation via uv
uv tool install findfmt

# Add to managed Python project
uv add findfmt

# Standard pip installation
pip install findfmt
```

### 2.2. Core Discovery Workflows

```bash
# Locate all Python files
findfmt -t python

# Locate files matching either Python or Shell scripts
findfmt -t python,shell

# Discover executable scripts by shebang pattern
findfmt --shebang bash

# Filter by glob pattern while honoring .gitignore
findfmt -P "*.py|*.md"

# Safe piping with NUL delimiters for xargs
findfmt -t python -0 | xargs -0 ruff format
```

### 2.3. Programmatic Python Library Usage

Integrate `findfmt` directly into Python scripts and automated pipelines:

```python
from findfmt import FileInfo, TraversalConfig, find_files, get_formatter

# Configure traversal scope and format filtering
config = TraversalConfig(include_tags={"python"}, root_paths=["src"])

# Iterate through discovered FileInfo objects
for file_info in find_files(config):
    print(f"{file_info.path} ({file_info.size_bytes} bytes)")

# Format output using any built-in serializer (e.g. table, json, tree)
formatter = get_formatter("table")
print(formatter.format(find_files(config)))
```

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
security
```

______________________________________________________________________

## 3. Community & Feedback

- **Source Code**: [github.com/bdperkin/findfmt](https://github.com/bdperkin/findfmt)
- **Issue Tracker**: Report bugs, request formats, or propose features on
  [GitHub Issues](https://github.com/bdperkin/findfmt/issues).
- **Contributing**: Review the
  [Contributing Guidelines](https://github.com/bdperkin/findfmt/blob/main/CONTRIBUTING.md) to get
  started with local development.
- **Accessibility**: See our [Accessibility Statement](accessibility.md) for supported assistive
  technologies and barrier reporting.
- **Security Policy**: See our [Security Policy](security.md) for reporting vulnerabilities and
  threat modeling details.
