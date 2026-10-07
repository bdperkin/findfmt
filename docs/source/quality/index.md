# Quality Metrics & Architecture

`findfmt` is engineered under the strictest software quality standards.

## 1. Code Quality Standards

- **100% Code Coverage**: Enforced through `pytest-cov` and Codecov CI checks.
- **Strict Static Typing**: Verified with `ty` in pedantic mode (`all = "error"`) and
  `pyproject.toml` configuration.
- **Ruff Strictness**: Formatted and linted using `ruff` with `ALL` rules selected.
- **Cyclomatic Complexity**: Monitored using `radon` and capped via `xenon`.
- **Documentation Completeness**: Monitored via `interrogate` ensuring 100% docstring coverage.

## 2. Traversal Complexity Optimization

Repository traversal performs early pruning of `.gitignore` hierarchies to prevent recursing into
expansive unneeded directory trees such as `node_modules`, `.venv`, or compilation artifact
directories.

## 3. Python Runtime Compatibility

`findfmt` officially supports Python 3.10 through 3.15, with automated CI matrices testing Ubuntu,
macOS, and Windows. See the complete analysis and version matrix:

```{toctree}
:maxdepth: 1

compatibility
```
