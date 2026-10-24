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

- **Full Verification Suite**:
  ```bash
  uv run python tools/verify_quality.py
  ```
- **Pre-Commit Quality Suite**: Run all 25+ pre-commit hooks across the repository:
  ```bash
  uv run pre-commit run --all-files --show-diff-on-failure
  ```
  The flag prints the diff when hooks modify files. Stage the fixes and run the command again.
  Include `--show-diff-on-failure` in new automated invocations of `pre-commit run --all-files`.
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
- **Documentation Build Verification**: Ensure Sphinx HTML builds cleanly with zero warnings (`-W`):
  ```bash
  uv run sphinx-build -M html docs/source docs/build -W
  ```
- **Prose and Documentation Linting**: All Markdown files (`.md`) are linted using
  [Vale](https://vale.sh/) with style rules defined in `.vale.ini` and project vocabulary in
  `.github/styles/`:
  ```bash
  vale *.md docs/
  ```
- **Public API Snapshot**: `tests/unit/test_api_surface.py` fails when a name in any module's
  `__all__` (or its signature) changes. For intentional changes, regenerate the snapshot and record
  the change in `CHANGELOG.md` (see the API stability policy in the documentation):
  ```bash
  uv run python tools/api_surface.py --write
  ```
- **Localization Tooling & Message Catalogs**: If updating translatable strings or locale catalogs,
  extract and compile message catalogs:
  ```bash
  uv run python tools/i18n.py extract
  uv run python tools/i18n.py compile
  ```
  The documentation has its own Sphinx catalogs under `docs/source/locale/`. After changing
  documentation text, regenerate and check them:
  ```bash
  make -C docs intl-update   # extract strings and update every language's .po catalog
  make -C docs html-all      # compile catalogs and build all languages
  ```
  `intl-update` drops obsolete `#~` entries (`--no-obsolete`). Changed paragraphs are kept and
  marked fuzzy for review, but a translation whose source text was removed is deleted.
  `tests/unit/test_docs_catalogs.py` fails when a page has no catalog in some language.

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
   uv run pre-commit run --all-files --show-diff-on-failure
   uv run python tools/verify_quality.py
   vale *.md docs/
   ```
4. **Code Review & Quality Gates**:
   - Every PR triggers our full automated CI suite (Linux, macOS, Windows across Python 3.11–3.15,
     100% test and branch coverage, strict `ty` type checking, pre-commit suite, CodeQL,
     ClusterFuzzLite, Vale prose linting, and dependency review). All status checks must pass before
     merging.
   - Community contributions require thorough code review and approval from repository maintainers.
   - For solo maintainer development, changesets are tracked via individual feature branches and
     validated through GitHub Actions CI prior to squash-merging.
5. **Linear History**: All pull requests are merged using GitHub Squash & Merge to maintain a clean,
   linear commit history.

## 7. Release Process (Maintainers)

Releases are built and published by `.github/workflows/release.yml`. The version comes from the git
tag through `hatch-vcs`, so a release always starts from an annotated `vMAJOR.MINOR.PATCH` tag:

1. Merge the release-preparation pull request and confirm CI is green on `main`. It turns the
   CHANGELOG `[Unreleased]` entries into a `## [X.Y.Z] - YYYY-MM-DD` section, adds the comparison
   link, and raises `version.fallback-version` to `X.Y.Z.dev0`. That section becomes the GitHub
   Release notes (`tools/release_notes.py`), and the workflow fails before building anything if it
   is missing. `uvx git-cliff --unreleased --tag vX.Y.Z` drafts entries from the commit history.
2. Check the distributions locally. `twine` must report no warnings, and the wheel must hold only
   the `findfmt` package (with `py.typed` and the compiled `*.mo` catalogs) and its metadata:
   ```bash
   uv build --clear
   uvx twine check --strict dist/*
   unzip -l dist/*.whl
   ```
   CI's packaging smoke test installs the wheel on the minimum and maximum supported Python on
   Linux, macOS, and Windows, runs `tools/smoke_wheel.py`, and checks that `pip` refuses Python
   3.10. To repeat it locally:
   ```bash
   uv venv --python 3.11 /tmp/smoke && uv pip install --python /tmp/smoke dist/*.whl
   /tmp/smoke/bin/python tools/smoke_wheel.py --wheel dist/*.whl
   ```
3. Tag the release commit and push the tag, which starts the workflow:
   ```bash
   git tag -a v1.1.0 -m "findfmt 1.1.0"
   git push origin v1.1.0
   ```
4. The workflow publishes to TestPyPI before production PyPI, so the TestPyPI upload is the dry run:
   if it fails, nothing reaches PyPI. Once the release is out, confirm that TestPyPI lists the new
   version and that PyPI installs it (don't install from TestPyPI, which would also take the
   dependencies from there):
   ```bash
   curl -s https://test.pypi.org/pypi/findfmt/1.1.0/json | jq -r .info.version
   uvx --from findfmt==1.1.0 findfmt --version
   ```
5. To re-run a release for an existing tag, start the workflow **on the tag**: choose the tag in
   **Actions → Release & Publish → Run workflow → Use workflow from**, and enter the same tag (for
   example `v1.1.0`), or run `gh workflow run release.yml --ref v1.1.0 -f tag=v1.1.0`. The `pypi`
   and `testpypi` environments only deploy `v*.*.*` tags, so a run started from a branch fails.

The workflow refuses to publish a mismatched build. It fails before the quality gate unless the
input is a `vMAJOR.MINOR.PATCH` tag, the workflow runs on that tag, and the checked-out commit is
that tag, and it fails before any upload unless the built wheel and sdist both carry the tag's
version (`tools/verify_release_version.py`). TestPyPI uploads skip files that already exist, so a
failed release can be re-run; production PyPI uploads do not, so a duplicate upload fails loudly.
The container image is built from the same wheel (the `dist` artifact), and the workflow checks that
it reports the release version before pushing it to GHCR with an SBOM and a signed provenance
attestation. CI's container smoke test builds and runs the image on every pull request; run it
locally with `FINDFMT_CONTAINER_TESTS=1 uv run pytest tests/integration/test_container.py --no-cov`.
