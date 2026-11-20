# Quality Metrics & Architecture

`findfmt` is engineered under the strictest software quality standards.

## 1. Code Quality Standards

- **100% Code Coverage**: Enforced through `pytest-cov` and Codecov CI checks.
- **Strict Static Typing**: Verified with `ty` in pedantic mode (`all = "error"`) and `pyproject.toml`
  configuration.
- **Ruff Strictness**: Formatted and linted using `ruff` with `ALL` rules selected.
- **Cyclomatic Complexity**: Monitored using `radon` and capped via `xenon`.
- **Documentation Completeness**: Monitored via `interrogate` ensuring 100% docstring coverage.
- **Prose & Style Linting**: Enforced on all Markdown documentation using Vale with Google and Proselint style
  standards.

## 2. Traversal Complexity Optimization & Performance Baselines

Repository traversal performs early pruning of `.gitignore` hierarchies to prevent recursing into expansive
unneeded directory trees such as `node_modules`, `.venv`, or compilation artifact directories in $O(1)$ time.

Official v1.0.0 benchmarks establish traversal throughput exceeding 3,000 files/second on standard hierarchies
and confirm bounded $O(1)$ memory usage across streaming output formatters (`text`, `jsonl`, `tsv`, `csv`).
See [Performance Architecture & Benchmarks](performance.md) for full topology baselines and regression testing
procedures.

## 3. Hybrid Python-Rust Architecture & Fallback Guarantees

`findfmt` pairs its strictly typed Python CLI and serializer suite with the `findfmt_rs` PyO3 native extension
(`findfmt._rust_ext`), coordinated by `src/findfmt/core.py` and backed by automatic `ImportError`,
`FINDFMT_NO_EXTENSIONS=1`, and `pyo3_runtime.PanicException` fallback to `src/findfmt/_fallback.py` (see
[Hybrid Python-Rust Architecture & Fallback FAQ](hybrid_architecture.md)).

## 4. Python Runtime Compatibility

`findfmt` officially supports Python 3.11 through 3.15, with automated CI matrices testing Ubuntu, macOS, and
Windows. A non-gating `3.16-dev` job gives early warning for the next Python release. Direct and transitive
dependency bounds in `pyproject.toml` are continuously verified across `uv` resolution strategies (`highest`,
`lowest`, `lowest-direct`), pre-release modes, and fork strategies in CI and via `tools/verify_quality.py`
(see [Dependency Resolution Matrix & Orchestration ADR](dependency_matrix.md)). See the complete analysis and
version matrix:

```{toctree}
:maxdepth: 4

compatibility
dependency_matrix
hybrid_architecture
performance
sidebar_navigation
```
