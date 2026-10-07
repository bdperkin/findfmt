# Contributing to findfmt

Thank you for your interest in contributing to `findfmt`! We welcome contributions ranging from bug
reports and documentation fixes to major features.

For architecture guides, API reference, and user tutorials, consult our online documentation at
[https://bdperkin.github.io/findfmt](https://bdperkin.github.io/findfmt).

## 1. Reporting Issues & Proposing Features

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

## 2. Issue & Pull Request Label Taxonomy

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

## 3. Development Setup

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

## 4. Quality and Testing Standards

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
- **Prose and Documentation Linting**: All Markdown files (`.md`) are linted using
  [Vale](https://vale.sh/) with style rules defined in `.vale.ini` and project vocabulary in
  `.github/styles/`, automatically ignoring code blocks and URLs. Run Vale locally before submitting
  changes:
  ```bash
  vale *.md docs/
  ```

## 5. Commit Guidelines

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

## 6. Pull Request & Review Process

1. **Branch Protection**: Direct pushes to `main` are strictly disabled and blocked for all
   collaborators (including administrators via `enforce_admins: true`). All modifications must be
   submitted via a Pull Request.
2. **Feature Branches**: Create a dedicated feature branch off the latest `main` (e.g.,
   `feature/issue-number-short-description`).
3. **Local Verification**: Ensure all tests, typing, and quality gates pass locally before opening a
   PR:
   ```bash
   uv run pre-commit run --all-files
   uv run python tools/verify_quality.py
   vale *.md docs/
   ```
4. **Code Review & Quality Gates**:
   - Every PR triggers our full automated CI suite (Linux, macOS, Windows across Python 3.10–3.14,
     100% test and branch coverage, strict `ty` type checking, pre-commit suite, CodeQL,
     ClusterFuzzLite, Vale prose linting, and dependency review). All status checks must pass before
     merging.
   - Community contributions require thorough code review and approval from repository maintainers.
   - For solo maintainer development, changesets are tracked via individual feature branches and
     validated through GitHub Actions CI prior to squash-merging.
5. **Linear History**: All pull requests are merged using GitHub Squash & Merge to maintain a clean,
   linear commit history.
