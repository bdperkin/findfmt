# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
[unreleased]: https://github.com/bdperkin/findfmt/compare/v0.8.0...HEAD
