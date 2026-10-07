# Contributing to findfmt

Thank you for your interest in contributing to `findfmt`! We welcome contributions ranging from bug
reports and documentation fixes to major features.

For architecture guides, API reference, and user tutorials, consult our online documentation at
[https://bdperkin.github.io/findfmt](https://bdperkin.github.io/findfmt).

## Reporting Issues & Proposing Features

We use structured GitHub Issue Forms to ensure essential reproduction details and context are
provided upfront:

- **[Bug Reports](https://github.com/bdperkin/findfmt/issues/new?template=bug_report.yml)**: Report
  unexpected behavior, incorrect exit codes, or CLI crashes with command invocations and environment
  details.
- **[New Format / Tag Requests](https://github.com/bdperkin/findfmt/issues/new?template=new_format_request.yml)**:
  Propose new classification tags, MIME types, or shebang patterns with a minimal snippet or
  fixture.
- **[Misclassification Reports](https://github.com/bdperkin/findfmt/issues/new?template=misclassification_report.yml)**:
  Report misidentified files or directory traversal edge cases (`.gitignore`, `--hidden`,
  `--no-ignore`).
- **[Feature Requests](https://github.com/bdperkin/findfmt/issues/new?template=feature_request.yml)**:
  Propose new CLI flags, output formatters, or Python API enhancements.
- **[Documentation Improvements](https://github.com/bdperkin/findfmt/issues/new?template=documentation.yml)**:
  Report typos, unclear phrasing, or missing documentation guides.
- **Security Inquiries**: For security vulnerabilities, follow our private reporting process via
  [GitHub Security Advisories](https://github.com/bdperkin/findfmt/security/advisories/new).

## Issue & Pull Request Label Taxonomy

We organize issues and pull requests using a structured, prefixed label taxonomy:

- **`area:*` (Codebase Subsystems)**:
  - `area:cli`: Command line interface, arguments, output formatters.
  - `area:classifier`: File content inspection, MIME detection, shebang parsing.
  - `area:traversal`: Directory walking, `.gitignore` rules, symlinks, filtering.
  - `area:packaging`: PyPI packages, wheels, Docker images, dependencies.
  - `area:docs`: Documentation guides, API reference, man pages, README.
- **`os:*` (Operating Systems)**:
  - `os:linux`, `os:macos`, `os:windows`: Platform-specific behaviors and tests.
- **`status:*` (Triage & Review Workflow)**:
  - `status:needs-info`: Awaiting author reproduction details or answers.
  - `status:needs-reproduction`: Bug requires a confirmed minimal reproduction.
  - `status:blocked`: Blocked on an external dependency or prerequisite PR.
  - `status:in-review`: Actively under code review.
  - `status:ready-to-merge`: Approved and queued for merge upon CI success.
- **`priority:*` (Urgency & Severity)**:
  - `priority:critical`, `priority:high`, `priority:medium`, `priority:low`.
- **`format:*` (Classification Families)**:
  - `format:python`, `format:shell`, `format:data`, `format:binary`, `format:markup`.
- **`type:*` & Core Tags**:
  - `type:chore`, `type:rfc`, `bug`, `enhancement`, `documentation`, `security`.

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
