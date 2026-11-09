# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Features

- *(i18n)* Complete the canonical German (`de`) localization catalog
  (`src/findfmt/locale/de/LC_MESSAGES/findfmt.po`, 147/147 messages) and localized Sphinx homepage
  (`docs/source/locale/de/LC_MESSAGES/index.po`), and enroll `de` in `COMPLETE_LOCALES` for
  pre-commit catalog completeness enforcement (#215).
- *(i18n)* Complete the canonical French (`fr`) localization catalog
  (`src/findfmt/locale/fr/LC_MESSAGES/findfmt.po`, 147/147 messages with non-breaking spaces before
  high punctuation and verified elisions) and localized Sphinx homepage
  (`docs/source/locale/fr/LC_MESSAGES/index.po`), and enroll `fr` in `COMPLETE_LOCALES` (#222).
- *(i18n)* Complete the canonical Japanese (`ja`) localization catalog
  (`src/findfmt/locale/ja/LC_MESSAGES/findfmt.po`, 147/147 messages with single-form pluralization
  and half-width/full-width CJK typography) and localized Sphinx homepage
  (`docs/source/locale/ja/LC_MESSAGES/index.po`), and enroll `ja` in `COMPLETE_LOCALES` (#228).

## [1.1.4] - 2026-11-08

### Features

- *(i18n)* Add `tools/i18n_translate.py` and `uv run python -m tools.i18n translate` for batch AI
  translation of GNU `gettext` `.po` message catalogs via OpenAI, Anthropic, Ollama, and
  deterministic mock backends with placeholder/markup validation and retry fallback (#306).
- *(i18n)* Add `tools/i18n_sync.py`, the `i18n-catalog-check` pre-commit hook, and
  `uv run python -m tools.i18n sync` to enforce POT/PO synchronization and 100% translation
  completeness across completed locales (`en`, `es`) and automate one-command extraction, update, AI
  translation, validation, and `.mo` compilation (#566).
- *(deps)* Add `tools/dep_matrix.py` and extend `tools/verify_quality.py` (`--smoke`, `--full`,
  `--resolution`, `--prerelease`, `--fork-strategy`) with a local `uv` dependency resolution matrix
  runner and 3-stage failure diagnostic engine (#427).

### Documentation

- *(agents)* Add `AGENTS.md` developer and AI coding agent architecture guide, testing/linting
  standards, and 350/500-line file decomposition policy (#556).
- *(deps)* Document local and CI dependency resolution matrix testing and lower-bound/pre-release
  remediation workflows in `CONTRIBUTING.md` (#430, #425).
- *(i18n)* Add `docs/source/guides/localization_platforms.md` evaluating managed SaaS localization
  platforms (POEditor, Crowdin, Localazy) versus local open-source CLI automation (#307, #308), and
  document the end-to-end AI translation runbook and locale onboarding steps (#564).

### Changed

- *(release)* Automatically close the matching GitHub milestone in `.github/workflows/release.yml`
  once a release is published (#546).
- *(ci)* Add `.github/workflows/dependency-matrix.yml` for nightly scheduled and `workflow_dispatch`
  execution of the 6-cell pruned `uv` dependency resolution matrix with step summaries, and raise
  test dependency lower bounds (`click>=8.2`, `pytest>=8.4`, `pytest-cov>=7`, `hatchling>=1.25`) for
  `--resolution lowest` compatibility (#429, #425).
- *(tools)* Add multi-Python local test runner support (`--all-pythons`, `--pythons`, `--list`) to
  `tools/verify_quality.py` reading supported interpreters (`3.11`–`3.15`) from `pyproject.toml`,
  and de-duplicate the `quality-gate` job in `.github/workflows/ci.yml` (#349, #385).

## [1.1.3] - 2026-11-08

### Documentation

- *(release)* Document GitHub milestone closure and `TODO.md` roadmap tracking in the maintainer
  release checklist in `CONTRIBUTING.md` (#545).

### Security

- *(ci)* Add `zizmor` static analysis pre-commit hook and `.github/workflows/zizmor.yml` SARIF
  code-scanning workflow for GitHub Actions, Dependabot, and pre-commit configurations, and harden
  workflows with `persist-credentials: false`, job-scoped permissions, and environment-bound
  template expressions (#468).

### Changed

- *(deps)* Pin `dependency-smoke-matrix` in `.github/workflows/ci.yml` to the minimum supported
  Python (`3.11`), add `typing-extensions>=4.4; python_version<'3.12'` to `[build-system].requires`,
  and make `Dependency Smoke Matrix` a required status check on `main` (#325).
- *(packaging)* Add `package-check` CI job (`Package Metadata & Wheel Contents`) running `uv build`,
  `twine check --strict`, and `check-wheel-contents --no-config` on every PR and in `release.yml`,
  and register it as a required status check on `main` (#475, #344).
- *(packaging)* Expand `packaging-smoke-test` in `.github/workflows/ci.yml` and
  `tools/smoke_wheel.py` (`--sdist`) to install and smoke-test source distributions
  (`dist/*.tar.gz`) on Linux across supported Python extremes (#358, #344).
- *(ci)* Align `ruff` (`0.17.3`) and shared lint tool versions across `.pre-commit-config.yaml` and
  `uv.lock`, implement drift enforcement and `--write` synchronization in
  `tools/sync_pre_commit_deps.py` wired into `tools/verify_quality.py`, standardize
  `codecov/codecov-action` comments, and move Sphinx `linkcheck` in `.github/workflows/docs.yml` to
  scheduled and manual dispatch runs (#360, #344).

## [1.1.2] - 2026-11-06

### Features

- *(i18n)* Expand Spanish (`es`) gettext message catalog to 100% coverage and localize documentation
  index (#221).
- *(i18n)* Add `tools/i18n_prompts.py` with domain context system prompt builder, CLI terminology
  glossary, `ngettext` multi-form pluralization prompt rules, and CLI flag preservation validator
  (#305).

### Bug Fixes

- *(traversal)* Resolve relative `root` paths in `traverse_directory` so `.gitignore` rules match
  relative roots and subdirectories (#322).
- *(traversal)* Align global and ancestor `.gitignore` discovery with Git: drop the `~/.gitignore`
  fallback, run `git -C <root> config --get core.excludesFile`, and stop ancestor `.gitignore`
  collection at the Git repository root (#323).
- *(api)* Add optional `root: Path | None = None` parameter to `find_global_gitignore_path` and
  `load_global_gitignore_spec` (#323).
- *(traversal)* Emit symbolic links by default with `FileInfo.path` preserved at the link location,
  populate `symlink_target` via `os.readlink`, and classify target content when `follow_symlinks`
  (`-l`) is active (#321).
- *(api)* Add optional keyword-only `follow_symlinks: bool = False` parameter to `classify_file`
  (#321).
- *(api)* Add optional keyword-only `entry` and `follow_symlinks` parameters to
  `check_device_boundary` (#337).

### Performance

- *(traversal)* Eliminate redundant per-file `os.stat`, `os.access`, and `Path.is_dir` syscalls
  across classification, pattern matching, and `-x` device boundary checks, and eliminate double
  classification of files under `--prune` (#337).

### Documentation

- *(deps)* Add Architecture Decision Record (`docs/source/quality/dependency_matrix.md`) evaluating
  matrix orchestration runners and defining the pruned 6-cell `uv` dependency resolution matrix and
  failure diagnostic pipeline (#426).

### Changed

- *(tests)* Eliminate all 53 `# pragma: no cover` annotations across `src/`, `tests/`, and `tools/`,
  remove the unreachable trailing `return 0` in `entrypoints.py`, add unit tests covering
  `terminal.py` height fallbacks, `__main__` execution (`findfmt.__main__` and `findfmt.cli.main`),
  `< 3.12` / `>= 3.12` `override` version gates, and POSIX `ImportError` (`pwd`, `grp`, `resource`)
  shims, and enforce zero `# pragma: no cover` usage in `test_api_stability.py` (#353).
- *(lint)* Add `tools/suppression_auditor.py`, `[tool.suppression-auditor]` configuration in
  `pyproject.toml`, and the `suppression-audit` pre-commit hook to audit and enforce justification
  for all inline linter and type-checker suppression directives across `src/`, `tests/`, and
  `tools/` (#540).
- *(tests)* Isolate `compile_locale_catalogs_for_tests` session fixture in `tests/conftest.py` to
  compile `.mo` catalogs into `tmp_path_factory` instead of `src/findfmt/locale/` and verify test
  dependency group sufficiency (#359).

## [1.1.1] - 2026-11-05

### Features

- *(api)* Add optional keyword-only `on_error: Callable[[OSError], None] | None = None` callback to
  `find_files`, `traverse_directory`, `collect_directory_entries`, `has_matching_descendants`, and
  `yield_matching_items` (#320).
- *(i18n)* Add `tools/validate_po_placeholders.py` and `--mask` / `--unmask` utilities to validate
  and protect Python format placeholders, CLI flags, Rich markup tags, and ANSI escapes during AI
  translation (#304).

### Bug Fixes

- *(traversal)* Report missing root paths and unreadable subdirectories to stderr
  (`findfmt: cannot open '<path>': <reason>`) and exit with status 1 while continuing to list
  accessible paths (#320).
- *(api)* Raise `TraversalError` on negative `max_depth` or `file_limit` and `ParserError` when
  `--from-file` cannot read the input file (#320).
- *(config)* Wrapper entry-point defaults (`findfiles`, `findfilefmt`, `findfilemime`, `findfmt0`,
  `findshebang`, `findsummary`) no longer override values configured in `.findfmt.toml` or
  `pyproject.toml` (#454).
- *(format)* Enforce consistent broken-pipe (`SIGPIPE` / `BrokenPipeError`) exit codes across Rich
  visual formatters and honor `--sort` and `--reverse` in `--tree`, `--format html`, and
  `--format xml` (#341, #384).
- *(format)* Encode `--cp437` (`-S`) and `--table-style cp437` box-drawing glyphs as CP437 bytes
  (`0xB3`, `0xC4`, `0xC3`, `0xC0`, etc.) instead of Latin-1 code points that rendered as mojibake
  (#343, #384).
- *(format)* XML output keeps the `mtime` and `ctime` attributes for files whose timestamp is the
  Unix epoch (`0.0`) instead of dropping them (#513).

### Documentation

- *(cli)* Document the formal CLI exit-code contract (`0`, `1`, `2`, `130`, `141`) in the README,
  CLI reference, and `--help-all` with an exhaustive test matrix (#369, #347).
- *(i18n)* Add the comparative benchmark and evaluation guide for open-source Python gettext AI
  translators (`gettext-translator`, `pytlai`, `auto-gettext-translator`, and LiteLLM/Ollama)
  (#303).

### Changed

- *(api)* `findfmt.cli.trap_cli_signals` is annotated as returning `Generator[None]` instead of
  `Iterator[None]`, which ty deprecates for `@contextmanager`. Runtime behavior is unchanged (#513).
- *(traversal)* Remove unused internal `_load_active_specs` helper and test-only engine aliases
  while preserving `findfmt.traversal.__all__` (#351).

## [1.1.0] - 2026-10-24

findfmt 1.1.0 requires Python 3.11 or newer; Python 3.10 users should pin `findfmt<1.1`. Upgrading
from 1.0.x? See [Upgrading to 1.1](https://bdperkin.github.io/findfmt/guides/upgrading.html) for
what changes and what to do.

### Breaking Changes

- *(build)* Dropped support for Python 3.10 (EOL 2026-10-01); the minimum supported version is now
  Python 3.11. Removed the `tomli` dependency and the 3.10 compatibility shims (#441).
- *(api)* `SortKey` and `OutputFormat` are now `enum.StrEnum` subclasses, so `str()`, `format()`,
  and f-strings render a member's value (`"size"`) instead of `"SortKey.SIZE"`. Equality with
  strings, hashing, JSON output, CLI help, and configuration handling are unchanged (#441).
- *(format)* Human-readable sizes use IEC binary unit labels: CLI `-h` output changes from `1.5 K`
  to `1.5 KiB`, and `findfmt.sizes.format_size()` from `1.5 KB` to `1.5 KiB`. Values are unchanged
  (#352).
- *(cli)* Wrapper commands (`findfiles`, `findfilefmt`, `findfilemime`, `findfmt0`, `findshebang`,
  `findsummary`) exit with status 1 instead of 0 when they stop with an error that carries a message
  (#373).

### Features

- *(cli)* Add `--exit-status` to exit with status 1 when no files match (#367).

### Bug Fixes

- *(traversal)* Preserve significant leading whitespace and escaped trailing whitespace in
  `.gitignore` patterns, matching git (#354).
- *(parsers)* Sort `--from-file` entries by status-change time for `--sort ctime` instead of
  modification time (#462).
- *(format)* `-f ipynb` notebooks run: the manifest cell loads its data with `json.loads` (#330).
- *(packaging)* Correct the "A.gitignore-aware" typo in the PyPI summary (#443).
- *(cli)* On Windows with Python 3.11–3.14, piped or redirected output no longer fails with
  `UnicodeEncodeError` when it contains characters the ANSI code page (such as cp1252) cannot
  encode, such as the `--help` panel borders or non-Latin file names. findfmt writes UTF-8, as
  Python 3.15 does by default, unless `PYTHONIOENCODING` or `PYTHONUTF8=0` is set (#496).
- *(benchmark)* `tools/benchmark.py --keep-temp` keeps the generated tree instead of deleting it
  (#489).

### Documentation

- *(guides)* Add the "Upgrading to 1.1" guide (#499), state the supported Python range in the
  README, installation guide, and quickstart, and complete the README CLI options table (#494).
- *(cli)* Correct symlink flag references in the configuration guide, CLI reference, and security
  policy (#364), and list `--csv-safe` in `--help-all` (#494).
- *(i18n)* Regenerate the documentation translation catalogs, drop obsolete entries on update, and
  guard catalogs against missing pages (#469).
- *(quality)* Document the Python version support lifecycle procedure (#442), and use
  `--show-diff-on-failure` in every documented `pre-commit run --all-files` (#476).
- *(api)* Document the public API stability policy, and pin the public API in a snapshot test so
  changes are caught in review (#493).
- *(cli)* Correct the exit-code tables in `--help-all` and the CLI reference: no matches exits 0
  unless `--exit-status` is given (#493).

### CI/CD & Packaging

- *(ci)* Python 3.15 is the supported maximum and now gates every merge on Linux, macOS, and
  Windows; the quality gate, documentation build, release, and wheel smoke test run on 3.15. A
  non-gating `3.16-dev` job gives early warning for the next release (#335, #440).
- *(docker)* The container image now runs Python 3.14 (was 3.13), still on Debian bookworm (#440).
- *(docker)* The container image installs the release wheel (the same one published to PyPI), so
  `findfmt --version` reports the release version instead of `1.0.2.dev0`. Dependencies are
  installed from `uv.lock`, and the image no longer ships `uv`. Releases verify the image's version
  before pushing it and publish an SBOM, build provenance, and a signed attestation. A new CI job
  builds and tests the image on every pull request. To build it locally, run `uv build --wheel`
  first (#328).
- *(release)* The release workflow always builds the requested tag (also when re-run via
  `workflow_dispatch`), refuses anything but a `vMAJOR.MINOR.PATCH` tag, verifies that the built
  wheel and sdist carry the tag's version before publishing, no longer skips duplicate production
  PyPI uploads, and tags dispatched container images with the release version instead of only
  `latest` (#327).
- *(release)* GitHub Release notes now come from the version's CHANGELOG section instead of
  generated commit summaries, and the release fails before building anything if that section is
  missing (#498).
- *(ci)* Run `uv sync --locked` everywhere (#356), fetch full history for version-sensitive jobs
  (#357), add a dependency-resolution smoke matrix to pull requests (#428), make the test suite
  hermetic against the developer's global git config (#326), and guard the supported Python range
  with policy tests (#442).
- *(ci)* The packaging smoke test installs the built wheel on the minimum and maximum supported
  Python (3.11 and 3.15) on Linux, macOS, and Windows, runs `tools/smoke_wheel.py` against it, and
  checks that `pip` refuses to install it on Python 3.10. End-to-end tests cover every behavior
  change since 1.0 (#496).
- *(packaging)* The wheel no longer ships the `*.po`/`*.pot` catalog sources (only the compiled
  `*.mo` catalogs, which are all it reads), and the sdist no longer picks up `*.mo` files built
  under `docs/` (#495).

### Security

- *(deps)* Update dev-only dependencies to resolve security advisories: `virtualenv` 21.14.13
  (`GHSA-cx6f-vjhg-g3cc`), `setuptools` 84.2.1 (`GHSA-xmj3-9gf7-h52w`), and `filelock` 4.2.4
  (`GHSA-v4x8-3wr5-3wq8`, `GHSA-9vhv-jxww-xfm5`, `GHSA-567q-5qvw-pf92`, `GHSA-2g95-wg33-c5x2`,
  `GHSA-jqc4-5cvw-7w85`, `GHSA-crv4-6mhj-j5jh`). The `filelock` fixes require Python 3.11+ (#441).
- *(release)* The `pypi` and `testpypi` deployment environments only admit `v*.*.*` tags, and the
  release workflow fails unless it runs on the requested tag, so a branch can't mint a PyPI
  publishing token (#495).

## [1.0.2] - 2026-10-21

### Security

- *(security)* Complete Security Hardening Epic covering terminal sanitization, ReDoS prevention,
  filesystem FIFO safety, and threat model documentation (#338, #422).
- *(classifier)* Prevent infinite hang during file type classification when regular files are
  swapped for FIFOs/named pipes (#363, #404).
- *(format)* Mask Unicode bidirectional control/override characters (`U+202A`–`U+202E`,
  `U+2066`–`U+2069`) in TTY mode to prevent Trojan Source visual spoofing (#362, #403).
- *(format)* Eliminate quadratic ReDoS vulnerability in C1-OSC terminal escape regex by strictly
  bounding inner characters to linear-time evaluation (#361, #402).
- *(format)* Neutralize spreadsheet formula injection by prefixing formula trigger characters (`=`,
  `+`, `-`, `@`, `\t`, `\r`) with single quotes via `--csv-safe` flag (#339, #411, #412).
- *(format)* Escape raw HTML metacharacters (`<`, `>`, `&`) in Markdown output table and list
  formatters (#333, #410).

### Features

- *(cli)* Ensure atomic file output for `-o`/`--output` flag using staging temporary files and
  atomic filesystem replacement (#368, #413, #414).
- *(i18n)* Add canonical gettext translation catalogs and Sphinx-intl localized documentation
  support for English (`en`) (#214, #421).

### Bug Fixes

- *(format)* Audit and enforce cell-width alignment for CJK double-width characters and emoji across
  table and tree formatters (#230, #420).

### CI/CD & Dependencies

- *(ci)* Configure Dependabot groups for `codeql-action` and package ecosystems (#415, #416).
- *(deps)* Bump `virtualenv` from 21.14.5 to 21.14.12 addressing GHSA-vxj4-q4g9-crj7.
- *(deps)* Bump `astral-sh/setup-uv` from 5.4.2 to 10.3.0 (#419).
- *(deps)* Bump actions group across GitHub Actions workflows (#418).
- *(deps)* Bump codeql-action group (#417).
- *(deps)* Bump `codecov/codecov-action` from 5.5.5 to 7.1.1 (#405).

## [1.0.1] - 2026-10-20

### Features

- *(i18n)* Localize file sizes, numeric separators, and timestamps per regional locale standards
  (#231, #397).

### Bug Fixes

- *(format)* Handle non-UTF-8 filenames with `surrogateescape` error handling and binary stdout
  dispatch across all output serializers and formatting modes (#315, #387, #388, #389).
- *(cli)* Preserve raw control characters under `-0` and piped text output to avoid truncating
  filenames containing newlines or tabs, while retaining sanitization on interactive terminals
  (#316, #390).
- *(i18n)* Emit `Content-Type: text/plain; charset=UTF-8` header in pure-Python MO compiler so
  wheels built without GNU `msgfmt` decode non-ASCII translations properly (#317, #391).
- *(traversal)* Guard symlink traversal against `OSError` and cyclic link loops across platforms,
  preventing recursive prune loops and Windows loop `RuntimeError` (#318, #393, #394).
- *(traversal)* Prevent crash in `--sort version` when handling non-ASCII numeric Unicode characters
  such as superscript digits (#370, #395).
- *(traversal)* Eliminate `os.scandir` iterator handle leaks on early traversal termination and
  enforce `ResourceWarning` error tracking in tests (#371, #396).
- *(test)* Support platforms without native POSIX `nl_langinfo` constants in localized timestamp
  tests (#398).

### Testing

- *(i18n)* Automated verification suite for complex multi-tier gettext pluralization rules covering
  English, German, French, Spanish, Russian, Polish, and Arabic (#232, #399).

### Documentation

- *(roadmap)* Realign internationalization roadmap across open 1.0.Z release milestones (#392).

## [1.0.0] - 2026-10-19

### Overview & Stability Commitment

This release represents the first major production-ready release of **findfmt** (v1.0.0 GA).
Starting with v1.0.0, `findfmt` strictly adheres to
[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). All public Python APIs exported
from the top-level `findfmt` package (`find_files`, `FileInfo`, `TraversalConfig`, `get_formatter`,
`classify_file`, `OutputFormat`, `FindFmtError`), as well as all CLI command options, configuration
schemas, environment variables, and exit codes, are guaranteed backwards-compatible across future
1.x releases.

### Flagship Highlights

- **Intelligent Content Classification**: File classification powered by `identify` and shebang
  heuristics, reliably detecting script interpreters and MIME types even in the absence of file
  extensions.
- **Hierarchical Traversal Engine**: High-performance, `.gitignore`-aware directory walker with
  early subtree pruning, maintaining constant $O(1)$ streaming memory across massive repositories.
- **Multi-Format Serialization Suite**: Built-in support for 14 serialization formats (`text`,
  `json`, `jsonl`, `yaml`, `ipynb`, `csv`, `csv-table`, `tsv`, `markdown`, `rst`, `table`, `tree`,
  `xml`, `html`) with Rich terminal styling, customizable borders, and OSC 8 terminal hyperlinks.
- **Hierarchical Configuration System**: Cascading configuration resolution supporting CLI
  arguments, environment variables, user configuration files (`~/.config/findfmt/config.toml` or
  Windows `%APPDATA%`), and `pyproject.toml` (`[tool.findfmt]`).
- **Terminal Security & Signal Resilience**: Automatic ANSI escape sequence stripping and
  control-character masking for untrusted filenames by default, paired with graceful Unix signal
  handling (`SIGPIPE`, `SIGINT`).
- **Internationalization & Localization**: Native `gettext` runtime architecture (`findfmt.i18n`)
  supporting localized console messages, help descriptions, and locale-aware number/date formatting.

### Added

- *(config)* Hierarchical configuration file support with `--config`, `--no-config`,
  `--show-config`, `FINDFMT_CONFIG` environment variable, XDG and Windows AppData discovery, and
  `pyproject.toml` `[tool.findfmt]` table integration (#281, #285).
- *(perf)* Official v1.0.0 traversal throughput and memory baselines establishing canonical
  performance benchmarks across flat (10k), deep (20-level hierarchy), and monorepo topologies
  (#284, #290).
- *(api)* Public module boundary audit, explicit `__all__` across all 49 submodules under `findfmt`,
  and top-level package exports for seamless library integration (#277, #288).
- *(format)* Full multi-format serialization suite supporting 14 output targets with intro/outro
  templating and OSC 8 terminal hyperlinks (#172, #173, #174).

### Changed

- *(security)* Enforce automatic ANSI escape sequence stripping and control-character masking for
  untrusted filenames by default across all formatters, Rich tables, tree views, Markdown, and XML
  serializers, with `--literal`/`-N` for raw output (#283, #287).
- *(signals)* Robust Unix signal handling (`SIGPIPE`, `SIGINT`) across CLI runner, entrypoints, and
  pager dispatch, terminating gracefully with zero Python tracebacks when piped to `head`, `sed`, or
  closed downstream processes (#282, #286).
- *(deps)* Updated pre-commit hooks and pinned stable dependencies (`uv-pre-commit 0.13.1`,
  `ruff-pre-commit v0.17.1`, `pymarkdown v0.9.41`, `pyroma 5.0.1`, `ty-pre-commit v0.0.84`) (#291).

### Fixed

- *(audit)* Comprehensive cross-platform edge cases, broken symlink resilience, cyclic symlink loop
  detection, and Windows drive path normalization in `build_file_uri` (#280, #289).

### Documentation

- *(sphinx)* Documentation, discoverability, quickstart guides, CLI reference synchronization, and
  manual pages polish for v1.0.0 release (#278, #293).

### Packaging & Security

- *(packaging)* Comprehensive packaging, distribution, and supply chain security verification for
  v1.0.0, including OIDC Trusted Publishing, global MO catalog compilation in wheels and source
  distributions, and release quality gate automation (#279, #294).

## [0.9.0] - 2026-10-15

### Bug Fixes

- *(i18n)* Sanitize absolute paths in message catalogs and enforce relative paths (#196)

### Documentation

- *(i18n)* Add comprehensive localization plan guide and language epic prompt (#271)
- *(community)* Update root governance, security, contributing, and changelog documents (#272)
- *(sphinx)* Audit and expand user guides, CLI reference, and man page (#273)
- Complete repository documentation audit and synchronization (#40) (#274)

## [0.8.0] - 2026-10-15

### Features

- *(i18n)* Implement core `gettext` runtime engine and message wrapping (#59) (#191)
- *(i18n)* Implement message catalog extraction, Hatchling MO compilation build hook, and
  Sphinx-intl (#60) (#192)
- *(i18n)* Implement locale-aware date/number formatting, pluralization, and multi-locale support
  (#36) (#193)

## [0.7.0] - 2026-10-14

### Documentation

- *(sphinx)* Implement and verify Web & Digital formats (`html`, `dirhtml`, `singlehtml`, `epub`)
  (#31) (#185)
- *(sphinx)* Implement and verify Print & Offline formats (`latexpdf`, `text`, `man`, `texinfo`)
  (#32) (#186)
- *(sphinx)* Implement and verify Help System formats (`htmlhelp`, `qthelp`, `devhelp`) (#33) (#187)
- *(sphinx)* Implement and verify Data & Serialization formats (`json`, `pickle`, `xml`,
  `pseudoxml`) (#34) (#188)
- *(sphinx)* Implement and verify Localization & Quality Control builders (#35) (#189)

## [0.6.0] - 2026-10-14

### Performance

- *(benchmark)* Create automated benchmark harness (`tools/benchmark.py`) tracking throughput and
  memory (#61) (#176)
- *(engine)* Optimize filesystem traversal, eliminate redundant `resolve()` calls, and single-buffer
  content reads (#62) (#182)
- *(engine)* Analyze traversal and classification performance bottlenecks and implement
  optimizations (#38) (#183)

### Dependencies

- Bump `actions/download-artifact` from 4.3.0 to 8.0.2 (#177)
- Bump `ossf/scorecard-action` from 2.4.1 to 2.5.0 (#178)
- Bump `actions/labeler` from 5.0.0 to 7.0.0 (#179)
- Bump `softprops/action-gh-release` from 2.6.2 to 3.0.3 (#180)
- Bump `github/codeql-action/upload-sarif` from 4.38.2 to 4.38.3 (#181)

## [0.5.1] - 2026-10-14

### Features

- *(format)* Implement XML and HTML document serializers with intro/outro templating (#57) (#172)
- *(cli)* Implement OSC 8 clickable terminal hyperlinks with schema and authority overrides (#58)
  (#173)
- *(cli)* Implement JSON document serialization shortcut flag (-J, --json) (#23) (#174)

## [0.5.0] - 2026-10-14

### Features

- *(metadata)* Implement permissions, ownership, and system identifiers (#54) (#167)
- *(metadata)* Implement file size formatting and disk usage accumulation (#55) (#168)
- *(metadata)* Implement timestamps, classification indicators, and quoting (#56) (#169)
- *(cli)* Complete extended file metadata and display options (#20) (#170)

## [0.4.1] - 2026-10-13

### Features

- *(cli)* Implement input options (`--from-file`, tab-indented parsing, symlink processing) (#24)
  (#164)
- *(traversal)* Add `-a`/`--all` alias and comprehensive traversal integration tests (#19) (#165)
- *(traversal)* Implement ignore engine extensions and file output redirection (#53) (#162)
- *(traversal)* Implement Unix-inspired sorting options (#21) (#163)

### Refactoring

- *(cli)* Modularize flat CLI modules into dedicated `cli` package (#159)
- *(traversal)* Modularize flat traversal modules into dedicated `traversal` package (#161)

## [0.4.0] - 2026-10-12

### Features

- *(cli)* Add interactive pager for `--help`, `--help-all`, and tall TTY diagnostic outputs (#149)
- *(cli)* Add relative path prefix option to preserve target path in listings (#145) (#154)
- *(traversal)* Expand `.gitignore` and `.git/info/exclude` discovery across ancestor hierarchy and
  nested subtrees (#146) (#155)
- *(traversal)* Implement traversal boundaries, depth limits, and pruning (#156)
- *(traversal)* Implement wildcard and glob pattern matching (-P, -I, --ignore-case, --match-dirs)
  (#157)

### Bug Fixes

- *(cli)* Preserve ANSI colorization when paging `--help` output (#151) (#152)

### Documentation

- *(security)* Document constrained PyPI and TestPyPI environment scoping (#148)

### Dependencies

- *(deps)* Update pre-commit hooks (#153)

## [0.3.0] - 2026-10-09

### Features

- *(format)* Implement structured data serializers (`json`, `jsonl`, `yaml`, `ipynb`) (#122)
- *(format)* Implement tabular, delimited, and markup serializers (`csv`, `tsv`, `md`, `rst`) (#123)
- *(format)* Implement Rich visual formatters (tables, border styles, tree view) (#49)
- *(cli)* Implement interactive terminal pager integration and TTY/NO_COLOR handling (#50)
- *(cli)* Implement graphics, indentation, and colorization options (-i, -A, -S, -n, -C) (#22)
- *(format)* Complete multi-format output suite with `csv-table` and `ndjson` (#142)

### Bug Fixes

- *(traversal)* Handle `re.error` when compiling invalid gitignore patterns (#138)

## [0.2.0] - 2026-10-07

### Features

- *(cli)* Map multiple CLI entry points to thin Typer context wrappers (#106)
- *(cli)* Investigate and implement miscellaneous options (toggling, usage, version, --) (#108)
- *(packaging)* Document Python 3.6-3.15 compatibility matrix and add classifiers (#115)
- *(tools)* Add file line length enforcement tool (tools/) (#118)

### Bug Fixes

- *(tools)* Enforce file line counts in line linter and modularize CLI (#125)
- *(clusterfuzzlite)* Pin dependencies by hash to resolve OpenSSF Scorecard alert #79 (#127)

### CI/CD

- *(docs)* Integrate Vale prose linter for Markdown documentation (#117)
- *(clusterfuzzlite)* Restrict fuzzing workflow to merges on main, scheduled runs, and manual
  dispatch (#129)
- *(vale)* Pin Vale binary version to 3.20.0 and provide GITHUB_TOKEN (#131)
- *(vale)* Scope .vale.ini with negative glob to exclude internal directories (#133)
- *(vale)* Resolve flaky Vale workflow with style caching, trigger scoping, and alert limits (#135)

### Refactor

- *(cli)* Migrate CLI parser from `argparse` to `Typer` with automated `docgen` (#105)

### Testing

- *(cli)* Normalize path separators in wrapper tests for Windows compatibility (#107)
- *(fuzz)* Integrate ClusterFuzzLite continuous fuzzing and Atheris targets (#116)

## [0.1.1] - 2026-10-07

### CI/CD

- *(testing)* Configure Codecov Test Analytics for test telemetry (#80)
- *(pre-commit)* Switch mdformat repo URL from redirected executablebooks/mdformat to canonical
  hukkin/mdformat (#90)
- *(pre-commit)* Add markdown-heading-numbering hook from jsh9/markdown-heading-numbering (#92)
- *(pre-commit)* Add pymarkdown linter hook and configuration from jackdewinter/pymarkdown (#94)
- *(coverage)* Configure Codecov individual components and comment layout (#97)
- *(deployments)* Configure GitHub Environments for deployments tracking (#99)
- *(scorecard)* Enforce least-privilege token permissions across workflows (#100)
- *(scorecard)* Pin GitHub Actions to commit SHAs and container images to digests (#101)
- *(release)* Confirm and validate automated changelog generation with git-cliff (#102)

### Documentation

- *(packaging)* Use absolute raw GitHub URLs for logo and links in README (#95)
- *(badges)* Use canonical Shields.io syntax for PyPI, Python, and Wheel badges (#96)
- *(scorecard)* Address OpenSSF Best Practices Program badge and Scorecard posture (#98)

### Dependencies

- *(deps)* Bump actions/checkout from 4 to 7 (#42)
- *(deps)* Bump docker/metadata-action from 5 to 6 (#43)
- *(deps)* Bump docker/login-action from 3 to 4 (#44)
- *(deps)* Bump github/codeql-action from 3 to 4 (#45)
- *(deps)* Bump codecov/codecov-action from 5 to 7 (#47)

## [0.1.0] - 2026-10-07

### Features

- Initial release and architecture scaffolding for findfmt
- *(community)* Expand and refine GitHub issue and PR templates (closes #8) (#72)
- *(assets)* Create asset generation tool and social preview card suite (closes #7) (#73)
- *(community)* Automate label taxonomy and PR labeler workflow (closes #13) (#74)

### Bug Fixes

- Refactor classifier and cli helpers to reduce complexity and ensure cross-python compatibility
- Support cross-platform path handling and windows executable resolution

### CI/CD

- *(pre-commit)* Consolidate .pre-commit-ci.yaml into .pre-commit-config.yaml (#65)
- *(pre-commit)* Migrate local workspace hooks to upstream repositories (#66)
- *(pre-commit)* Audit and configure comprehensive advanced pre-commit hooks (#67)
- Configure Codecov targets and GitGuardian secret scanning (#69)
- Evaluate and integrate workflows across core categories (closes #12) (#75)
- Fix pre-commit.ci pyroma environment and sphinx epub favicon warning (#76)
- *(release)* Clean attestations between TestPyPI and PyPI publishing (#78)

### Documentation

- *(a11y)* Add ACCESSIBILITY.md and document accessibility commitments (#68)
- *(readme)* Add comprehensive structured badge grids to README and docs (#70)
- Cross-link documentation site and GitHub repository (closes #6) (#71)

### Testing

- Add posix execution unit test for cross-platform coverage parity

### Security

- *(audit)* Document threat model audit and harden filesystem inspection (#77)

### Dependencies

- *(deps)* Update GitHub Actions workflow versions

<!-- generated by git-cliff -->

[0.1.0]: https://github.com/bdperkin/findfmt/releases/tag/v0.1.0
[0.1.1]: https://github.com/bdperkin/findfmt/compare/v0.1.0...v0.1.1
[0.2.0]: https://github.com/bdperkin/findfmt/compare/v0.1.1...v0.2.0
[0.3.0]: https://github.com/bdperkin/findfmt/compare/v0.2.0...v0.3.0
[0.4.0]: https://github.com/bdperkin/findfmt/compare/v0.3.0...v0.4.0
[0.4.1]: https://github.com/bdperkin/findfmt/compare/v0.4.0...v0.4.1
[0.5.0]: https://github.com/bdperkin/findfmt/compare/v0.4.1...v0.5.0
[0.5.1]: https://github.com/bdperkin/findfmt/compare/v0.5.0...v0.5.1
[0.6.0]: https://github.com/bdperkin/findfmt/compare/v0.5.1...v0.6.0
[0.7.0]: https://github.com/bdperkin/findfmt/compare/v0.6.0...v0.7.0
[0.8.0]: https://github.com/bdperkin/findfmt/compare/v0.7.0...v0.8.0
[0.9.0]: https://github.com/bdperkin/findfmt/compare/v0.8.0...v0.9.0
[1.0.0]: https://github.com/bdperkin/findfmt/compare/v0.9.0...v1.0.0
[1.0.1]: https://github.com/bdperkin/findfmt/compare/v1.0.0...v1.0.1
[1.0.2]: https://github.com/bdperkin/findfmt/compare/v1.0.1...v1.0.2
[1.1.0]: https://github.com/bdperkin/findfmt/compare/v1.0.2...v1.1.0
[1.1.1]: https://github.com/bdperkin/findfmt/compare/v1.1.0...v1.1.1
[1.1.2]: https://github.com/bdperkin/findfmt/compare/v1.1.1...v1.1.2
[1.1.3]: https://github.com/bdperkin/findfmt/compare/v1.1.2...v1.1.3
[1.1.4]: https://github.com/bdperkin/findfmt/compare/v1.1.3...v1.1.4
[unreleased]: https://github.com/bdperkin/findfmt/compare/v1.1.4...HEAD
