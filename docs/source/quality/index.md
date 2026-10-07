# Quality Metrics & Architecture

`findfmt` is engineered under the strictest software quality standards.

## Code Quality Standards

- **100% Code Coverage**: Enforced through `pytest-cov` and Codecov CI checks.
- **Strict Static Typing**: Verified with `ty` in pedantic mode (`all = "error"`) and
  `pyproject.toml` configuration.
- **Ruff Strictness**: Formatted and linted using `ruff` with `ALL` rules selected.
- **Cyclomatic Complexity**: Monitored using `radon` and capped via `xenon`.
- **Documentation Completeness**: Monitored via `interrogate` ensuring 100% docstring coverage.

## Traversal Complexity Optimization

Repository traversal performs early pruning of `.gitignore` hierarchies to prevent recursing into
expansive unneeded directory trees such as `node_modules`, `.venv`, or compilation artifact
directories.
