# Python Compatibility & Runtime Matrix

This document defines the formal Python runtime compatibility matrix for `findfmt`, detailing
verified runtimes, dependency constraints, language-level requirements, and technical justifications
across Python 3.6 through 3.15.

______________________________________________________________________

## 1. Compatibility Overview & Runtime Matrix

`findfmt` enforces `requires-python = ">=3.10"`. The runtime compatibility status across modern and
legacy Python interpreters is summarized below:

| Python Version |  Release / EOL Status  | Tested on Fedora 44 | Build & CLI Execution | Test Suite & 100% Coverage | Compatibility Verdict & Primary Rationale                                                                                                              |
| :------------: | :--------------------: | :-----------------: | :-------------------: | :------------------------: | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
|    **3.6**     |     EOL (Dec 2021)     |    Yes (3.6.15)     |        Blocked        |            N/A             | **Unsupported**: Missing `@dataclass(slots=True)`; `identify>=2.6` and `typer>=0.12` drop 3.6; lacks runtime PEP 604 type support.                     |
|    **3.7**     |     EOL (Jun 2023)     |         N/A         |        Blocked        |            N/A             | **Unsupported**: Missing `@dataclass(slots=True)`; `identify>=2.6` and `typer>=0.12` drop 3.7.                                                         |
|    **3.8**     |     EOL (Oct 2024)     |         N/A         |        Blocked        |            N/A             | **Unsupported**: Missing `@dataclass(slots=True)`; `identify>=2.6.2` drops 3.8; lacks standard library `typing.Annotated`.                             |
|    **3.9**     |     EOL (Oct 2025)     |    Yes (3.9.25)     |        Blocked        |            N/A             | **Unsupported**: `@dataclass(slots=True)` raises `TypeError`; `identify>=2.6.16` and `typer>=0.24` require `>=3.10`; runtime PEP 604 reflection fails. |
|    **3.10**    | Security (to Oct 2026) |    Yes (3.10.21)    |      **Passed**       |         **Passed**         | **Supported (Minimum)**: Baseline runtime; `@dataclass(slots=True)` and PEP 604 supported; requires `tomli` shim for TOML config parsing.              |
|    **3.11**    |   Bugfix / Security    |    Yes (3.11.16)    |      **Passed**       |         **Passed**         | **Supported**: Native `tomllib` available; exceptional performance and stability.                                                                      |
|    **3.12**    |   Bugfix / Security    |    Yes (3.12.14)    |      **Passed**       |         **Passed**         | **Supported**: Full native support; standard CI testing target.                                                                                        |
|    **3.13**    |   Current Mainstream   |    Yes (3.13.15)    |      **Passed**       |         **Passed**         | **Supported**: Primary local development target; wheel smoke-test target.                                                                              |
|    **3.14**    |    Certified Modern    |    Yes (3.14.7)     |      **Passed**       |         **Passed**         | **Supported (Certified)**: Primary CI quality gate target; PyPI Trove classifier active; 100% statement and branch coverage.                           |
|    **3.15**    | Preview / Dev (rc/dev) |   Yes (3.15.0rc2)   |      **Passed**       |         **Passed**         | **Supported (Preview)**: Validated against 3.15.0rc2 and CI `3.15-dev`; PyPI Trove classifier active; 100% statement and branch coverage.              |

______________________________________________________________________

## 2. Minimum Python Version Analysis (3.6 – 3.9)

### 2.1. Upstream Dependency Ecosystem Floors

A critical factor in determining the minimum supported runtime is the upstream dependency ecosystem:

1. **`identify` (pre-commit team)**:

   - `identify>=2.6.16` explicitly specifies `requires-python = ">=3.10"`.
   - Versions `2.6.2` to `2.6.15` require `>=3.9`.
   - Versions `2.6.0` to `2.6.1` require `>=3.8`.
   - No version within the `identify>=2.6` range supports Python 3.6 or 3.7. Attempting to install
     dependencies on Python 3.6 fails immediately at the resolver stage.

2. **`typer` (CLI Framework)**:

   - `typer>=0.24.0` specifies `requires-python = ">=3.10"`.
   - `typer>=0.21.0` requires `>=3.9`.
   - `typer>=0.19.2` requires `>=3.8`.
   - Python 3.6 is unsupported by any modern Typer release.

3. **`pathspec` & `rich`**:

   - `pathspec>=0.12` requires Python `>=3.8`.
   - `rich` releases drop Python `<3.8` and leverage modern terminal and typing enhancements.

### 2.2. Language Features and Runtime Typing Constraints

1. **`@dataclass(slots=True)` (PEP 557 / PEP 654)**:

   - `src/findfmt/models.py` defines core data structures (`FileInfo`, `TraversalStats`) using
     `@dataclass(frozen=True, slots=True)` for high performance and reduced memory footprint.
   - The `slots` argument was introduced in Python 3.10. On Python 3.9 and earlier, invoking
     `@dataclass(slots=True)` raises
     `TypeError: dataclass() got an unexpected keyword argument 'slots'`.

2. **PEP 604 Union Syntax (`str | None`, `Path | str`)**:

   - While `from __future__ import annotations` postpones evaluation of type annotations in standard
     code on Python 3.7+, frameworks like Typer and Click inspect type annotations at runtime to
     construct CLI options and type coercion logic.
   - Evaluating union syntax (`str | None`) at runtime in Python 3.9 and earlier triggers
     `TypeError: unsupported operand type(s) for |: 'type' and 'type'`.

3. **Standard Library Configuration Parsing**:

   - Python 3.11+ includes `tomllib` in the standard library.
   - Python 3.10 is cleanly supported using the conditional dependency
     `tomli>=2.0.1; python_version<'3.11'`.

### 2.3. Tooling and Linter Floors

The project's verification suite relies on modern developer tooling:

- `sphinx>=8` requires Python `>=3.10`.
- `deptry>=0.20` requires Python `>=3.10`.
- `ty>=0.0.80`, `radon`, `xenon`, and `vulture` require modern AST parsers and Python `>=3.10`.

### 2.4. Maintenance Cost vs. Upstream EOL Status

- Python 3.6 reached End-of-Life (EOL) in December 2021.
- Python 3.7 reached EOL in June 2023.
- Python 3.8 reached EOL in October 2024.
- Python 3.9 reached EOL in October 2025.
- Python 3.10 is the oldest currently maintained Python version receiving security updates (through
  October 2026).

Supporting Python < 3.10 would require downgrading data models, discarding `slots=True`, introducing
verbose `typing.Union` constructs, and freezing dependencies to outdated versions with unpatched
vulnerabilities. Therefore, maintaining `requires-python = ">=3.10"` is technically sound and
necessary.

______________________________________________________________________

## 3. Modern & Future Python Certification (3.14 – 3.15)

### 3.1. Python 3.14 Certification

Python 3.14 is certified as a tier-1 supported runtime:

- **CI Quality Gate**: Serves as the primary Python version for the `quality-gate` workflow in
  GitHub Actions.
- **Test Suite Pass**: 91 of 91 unit and integration tests pass with 100.00% statement and branch
  coverage.
- **CLI Verification**: Built distribution wheels install and execute all entry points without
  warnings.
- **Trove Classifier**: Officially published on PyPI as `Programming Language :: Python :: 3.14`.

### 3.2. Python 3.15 Preview / Dev Certification

Python 3.15 is validated and certified for development and preview:

- **Local Testing**: Verified under Fedora 44 with `CPython 3.15.0rc2`.
- **Test Suite Pass**: 91 of 91 unit and integration tests pass with 100.00% statement and branch
  coverage with zero deprecation warnings.
- **CI Test Matrix**: Runs as an experimental builder on `ubuntu-latest` with
  `python-version: 3.15-dev`.
- **Trove Classifier**: Officially published on PyPI as `Programming Language :: Python :: 3.15`.

______________________________________________________________________

## 4. Multi-Platform CI Matrix

Automated verification runs across all certified runtimes and operating systems:

```yaml
matrix:
  os: [ubuntu-latest, macos-latest, windows-latest]
  python-version: ['3.10', '3.11', '3.12', '3.13', '3.14']
  include:
    - os: ubuntu-latest
      python-version: 3.15-dev
      experimental: true
```
