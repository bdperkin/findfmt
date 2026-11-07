# Dependency Resolution Matrix & Orchestration ADR

This document records the Architecture Decision Record (ADR) and technical specification for
multi-dimensional dependency resolution and Python interpreter matrix testing in `findfmt` (Issues
[#426](https://github.com/bdperkin/findfmt/issues/426),
[#425](https://github.com/bdperkin/findfmt/issues/425), and
[#349](https://github.com/bdperkin/findfmt/issues/349)).

______________________________________________________________________

## 1. Context, Problem Statement & Architecture Decision

### 1.1. Context & Problem Statement

`findfmt` uses `hatchling` as its PEP 517 build backend in `pyproject.toml` and relies on `uv` for
virtual environment creation, lock file synchronization (`uv.lock`), and test execution. Standard CI
jobs execute `uv sync --locked --all-groups`, which validates only a single resolution point:
`--resolution highest --prerelease disallow --fork-strategy fewest`.

Relying solely on the default lock file leaves three failure modes untested:

1. **Lower-Bound Drift**: Direct dependency floors declared in `pyproject.toml` (`identify>=2.6`,
   `pathspec>=1.0.1`, `pyyaml>=6.0.1`, `rich>=13.8`, `typer>=0.16`, `typing-extensions>=4.4`) can
   silently bit-rot when new code relies on features added in later minor releases.
2. **Upstream Pre-Release Breakages**: Upcoming alpha, beta, or release-candidate versions of direct
   or transitive dependencies (`click`, `rich`, `typer`, `pathspec`, `pytest`) can introduce
   breaking API changes before stable publication.
3. **Multi-Interpreter & Fork-Strategy Divergence**: Marker evaluation across supported Python
   interpreters (`3.11` through `3.15`) and `uv` resolver fork strategies can yield distinct package
   selections on minimum versus maximum runtimes.

### 1.2. Architecture Decision Summary

- **Status**: Accepted (Milestone `v1.1.2`, Issue
  [#426](https://github.com/bdperkin/findfmt/issues/426)).
- **CI Orchestrator**: Use native GitHub Actions `strategy.matrix` (`fail-fast: false`) for parallel
  cloud execution:
  - **PR Smoke Gate**: 2-cell `dependency-smoke-matrix` job in `.github/workflows/ci.yml`
    (`lowest-direct` + `disallow` and `highest` + `allow`).
  - **Scheduled Exhaustive Matrix**: 6-cell pruned matrix in
    `.github/workflows/dependency-matrix.yml` triggered nightly via `schedule` and on-demand via
    `workflow_dispatch` (Issue [#429](https://github.com/bdperkin/findfmt/issues/429)).
- **Local Orchestrator**: Extend `tools/verify_quality.py` with native `uv` process orchestration
  covering both the dependency resolution axis (Issue
  [#427](https://github.com/bdperkin/findfmt/issues/427)) and the multi-Python interpreter axis
  (Issue [#349](https://github.com/bdperkin/findfmt/issues/349)), adding zero external task-runner
  dependencies or secondary configuration files.

______________________________________________________________________

## 2. Orchestration Tooling Assessment

Five orchestration mechanisms were evaluated across both the dependency resolution axis
(`--resolution`, `--prerelease`, `--fork-strategy`) and the Python interpreter axis (`3.11`–`3.15`):

| Orchestrator Candidate                         | Configuration Surface                              | CI Integration & Parallelism                                                       | Local Ergonomics & Caching                                                                 | Dependency & Config Overhead                                       | Verdict              |
| :--------------------------------------------- | :------------------------------------------------- | :--------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------- | :----------------------------------------------------------------- | :------------------- |
| **GitHub Actions `strategy.matrix`**           | `.github/workflows/*.yml`                          | **Native**: parallel virtual machines, step summaries, and `setup-uv` cache reuse. | Not runnable locally without external container emulation.                                 | **Zero** extra packages; standard workflow YAML.                   | **Selected (CI)**    |
| **Native `uv` in `tools/verify_quality.py`**   | `tools/verify_quality.py` + `pyproject.toml`       | Invoked directly by CI quality gate and smoke steps.                               | **High**: reuses local `uv` wheel cache and auto-skips or provisions missing interpreters. | **Zero** new dependencies or config files.                         | **Selected (Local)** |
| **Hatch Matrix (`[tool.hatch.envs]`)**         | `pyproject.toml` (`[tool.hatch.envs.test.matrix]`) | Requires separate GHA matrix mapping to avoid serial execution on one runner.      | Requires global `hatch` CLI (only `hatchling` is installed in `dev` group).                | Adds `hatch` CLI requirement and custom `uv pip` override scripts. | **Rejected**         |
| **`nox` (`noxfile.py` with `uv` backend)**     | `noxfile.py`                                       | Requires `nox-to-gha` action or duplicate matrix definitions in YAML.              | Good imperative matrix generation via `@nox.parametrize`.                                  | Adds `nox` dependency and a new top-level `noxfile.py`.            | **Rejected**         |
| **`tox` + `tox-uv` (`[tool.tox]`)**            | `pyproject.toml` or `tox.ini`                      | Requires `tox-gh-actions` plugin to map factors to GHA jobs.                       | Fast virtualenv creation via `tox-uv`, but awkward factor syntax for `uv` flags.           | Adds `tox` and `tox-uv` dependencies; duplicates version lists.    | **Rejected**         |
| **Command Runners (`Make`, `just`, `invoke`)** | `Makefile` / `justfile` / `tasks.py`               | No native environment or matrix lifecycle management.                              | Shell aliases only; must still delegate to `uv` or Python scripts.                         | Adds non-Python binary or task file without solving isolation.     | **Rejected**         |

### 2.1. Rationale for Hybrid GitHub Actions + `tools/verify_quality.py`

1. **Single Resolver & Zero Lock Drift**: `uv` is the sole environment manager and package resolver.
   Driving ephemeral virtual environments (`uv venv` + `uv pip install`) directly from
   `tools/verify_quality.py` locally and `strategy.matrix` in GitHub Actions guarantees identical
   resolver semantics without translating flags through `tox` or `hatch` wrapper layers.
2. **Single Source of Truth for Python Versions**: `tools/verify_quality.py` reads the supported
   interpreter list (`3.11`, `3.12`, `3.13`, `3.14`, `3.15`) directly from the
   `Programming Language :: Python :: 3.X` Trove classifiers in `pyproject.toml`, preventing drift
   between `pyproject.toml`, `.github/workflows/ci.yml`, and local runner definitions.
3. **Minimal Dependency Surface**: Keeping orchestration inside `tools/verify_quality.py` avoids
   adding `nox`, `tox`, `tox-uv`, or the full `hatch` CLI to `[dependency-groups].dev`.

______________________________________________________________________

## 3. Combinatorial Space & Matrix Pruning Analysis

### 3.1. Raw Combinatorial Space (30 Permutations)

`uv` exposes three primary resolution control dimensions:

- **`--resolution`** (3 values): `highest`, `lowest`, `lowest-direct`
- **`--prerelease`** (5 values): `disallow`, `allow`, `if-necessary`, `explicit`,
  `if-necessary-or-explicit`
- **`--fork-strategy`** (2 values): `fewest`, `requires-python`

The full Cartesian product yields $3 \\times 5 \\times 2 = 30$ permutations per Python interpreter
(150 combinations across all 5 supported Python versions).

### 3.2. Pruning `--prerelease` Permutations

Inspecting `[project].dependencies` and `[dependency-groups].test` in `pyproject.toml` shows that
every dependency specifier uses a stable lower bound (`>=X.Y` or `>=X.Y.Z`) with zero explicit
pre-release specifiers (such as `>=1.0a1` or `>=2.0.0rc1`):

1. **Eliminate `explicit` and `if-necessary-or-explicit` (-12 combinations)**: Because no specifier
   in `pyproject.toml` opts into an explicit pre-release tag, `--prerelease explicit` is
   mathematically identical to `--prerelease disallow`, and `--prerelease if-necessary-or-explicit`
   is identical to `--prerelease if-necessary` across all resolutions and fork strategies.
2. **Eliminate `if-necessary` under `highest` and `lowest-direct` (-4 combinations)**: Every direct
   and transitive dependency of `findfmt` has published stable wheels satisfying `>=3.11`. Under
   `highest` and `lowest-direct`, the solver never lacks a stable candidate, so `if-necessary`
   produces the exact same resolution graph as `disallow`.
3. **Retain `(lowest, if-necessary, fewest)` and eliminate `(lowest, disallow, *)` /
   `(lowest, allow, *)` (-5 combinations)**: Full transitive `--resolution lowest` attempts to pick
   the oldest historical release of every transitive package (`click`, `pygments`, `markdown-it-py`,
   `mdurl`, `packaging`). Using `if-necessary` allows the solver to fall back only when an ancient
   transitive sdist lacks metadata, whereas `lowest` + `allow` selects broken historical alpha tags
   from transitive dependencies that are unrelated to `findfmt`'s own version bounds.

### 3.3. Pruning `--fork-strategy` Permutations

`uv`'s `--fork-strategy` flag (`fewest` versus `requires-python`) controls how the universal
resolver splits resolution forks across disjoint Python version ranges:

- When resolving into a single target interpreter environment (`uv pip install --python <env>`),
  environment markers (`python_version < '3.12'` for `typing-extensions>=4.4`) evaluate to a fixed
  boolean for that interpreter.
- Consequently, varying `--fork-strategy` across all `lowest-direct` and `allow` permutations
  produces identical per-interpreter package sets (-8 combinations).
- Retaining a single `(highest, disallow, requires-python)` cell verifies that
  `--fork-strategy requires-python` succeeds cleanly against `findfmt`'s
  `requires-python = ">=3.11"` metadata.

### 3.4. Formal Pruned Matrix Specification

Pruning reduces the 30 raw combinations by **80%** to **6 canonical non-redundant cells** for the
exhaustive matrix and **2 cells** for the fast PR smoke gate:

| Cell ID | `--resolution`  | `--prerelease` | `--fork-strategy` | Execution Tier          | Primary Verification Target                                                                     |
| :-----: | :-------------- | :------------- | :---------------- | :---------------------- | :---------------------------------------------------------------------------------------------- |
| **M1**  | `lowest-direct` | `disallow`     | `fewest`          | **PR Smoke** & **Full** | Verifies declared direct minimum bounds in `pyproject.toml` against stable transitive packages. |
| **M2**  | `highest`       | `allow`        | `fewest`          | **PR Smoke** & **Full** | Detects breaking changes in upstream alpha, beta, and release-candidate releases early.         |
| **M3**  | `highest`       | `disallow`     | `fewest`          | **Full (Nightly)**      | Validates the latest stable upstream releases unpinned from `uv.lock`.                          |
| **M4**  | `lowest-direct` | `allow`        | `fewest`          | **Full (Nightly)**      | Verifies direct dependency floors when paired with pre-release transitive dependencies.         |
| **M5**  | `lowest`        | `if-necessary` | `fewest`          | **Full (Nightly)**      | Stress-tests full transitive dependency floors across the entire dependency graph.              |
| **M6**  | `highest`       | `disallow`     | `requires-python` | **Full (Nightly)**      | Validates `requires-python` marker fork-strategy resolution semantics.                          |

______________________________________________________________________

## 4. Failure Diagnostic Architecture

When any resolution or `pytest` step fails in CI or local matrix execution, the runner executes a
three-stage diagnostic pipeline:

### 4.1. Stage 1 — Ephemeral Dependency Tree Capture

Immediately upon resolution or test failure (`if: failure()` in GitHub Actions or non-zero exit code
in `tools/verify_quality.py`), the runner captures the resolved dependency graph from the isolated
environment:

```bash
uv pip tree --python <env_path>
```

In GitHub Actions, this output is appended as a fenced Markdown block to `$GITHUB_STEP_SUMMARY`
under the failing cell heading
(`### Dependency Tree (<resolution> / <prerelease> / <fork-strategy>)`).

### 4.2. Stage 2 — Baseline Lock File Version Diffing

To isolate which package version triggered the regression, the runner compares the failing
environment's installed package list (`uv pip list --format json --python <env_path>`) against the
pinned versions in `uv.lock`, reporting a concise delta table of downgraded or pre-release packages.

### 4.3. Stage 3 — Offending Bound Pinpointing & Remediation

The diagnostic reporter cross-references installed direct package versions against the specifiers in
`pyproject.toml` (`[project].dependencies` and `[dependency-groups].test`):

- If a failure occurs under `lowest-direct` (`M1` or `M4`), the report identifies the direct
  dependencies pinned at their floor versions and outputs the exact `pyproject.toml` lower bound
  that requires bumping.
- If a failure occurs under `prerelease=allow` (`M2` or `M4`), the report highlights every installed
  package whose version matches a pre-release segment (`a`, `b`, `rc`, `dev`) so maintainers can
  file upstream reports or add temporary upper-bound exclusions.
