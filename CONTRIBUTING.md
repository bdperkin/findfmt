# Contributing to findfmt

Thank you for your interest in contributing to `findfmt`! We welcome contributions ranging from bug
reports and documentation fixes to major features.

For architecture guides, API reference, and user tutorials, consult our online documentation at
[https://bdperkin.github.io/findfmt](https://bdperkin.github.io/findfmt).

## Development Setup

`findfmt` uses `uv` for package and dependency management.

1. **Fork and Clone**:

   ```bash
   git clone https://github.com/bdperkin/findfmt.git
   cd findfmt
   ```

2. **Sync Dependencies**:

   ```bash
   uv sync --all-groups
   ```

3. **Install Pre-Commit Hooks**:

   ```bash
   uv run pre-commit install
   ```

## Quality and Testing Standards

All pull requests must satisfy our quality gate before merging:

- **100% Test Coverage**: Every line and branch must be covered.
  ```bash
  uv run pytest
  ```
- **Strict Linting and Formatting**:
  ```bash
  uv run ruff check
  uv run ruff format --check
  ```
- **Strict Type Checking**:
  ```bash
  uv run ty check
  ```
- **Full Verification Suite**:
  ```bash
  uv run python tools/verify_quality.py
  ```

## Commit Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/) to power our automated semantic
release and changelog pipelines:

- `feat:` A new feature (triggers minor release)
- `fix:` A bug fix (triggers patch release)
- `docs:` Documentation only changes
- `style:` Code style / formatting changes
- `refactor:` Code restructuring without behavior changes
- `perf:` Performance improvements
- `test:` Test additions or fixes
- `ci:` CI workflow changes
- `chore:` Maintenance tasks

Please sign off on your commits:

```bash
git commit -s -m "feat: add support for MIME categories"
```

## Pull Request Process

1. Create a feature branch off `main`.
2. Ensure all tests and quality checks pass locally.
3. Open a Pull Request on GitHub. Direct pushes to `main` are disabled.
4. Address any CI check feedback or code review comments.
