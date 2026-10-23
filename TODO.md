<!-- vale off -->

# Project TODO & Implementation Roadmap

> **Repository:** [bdperkin/findfmt](https://github.com/bdperkin/findfmt) **Generated:** 2026-10-22
> **Tracking:** 121 Closed Issues | 146 Actionable Open Tasks | 35 Active Umbrella Epics **Last
> audit:** 2026-10-21 (full open-issue triage: closures, corrections, decomposition, epic and
> milestone re-balancing); 2026-10-22 (triaged #468-#476 and added milestone v1.2.2)

______________________________________________________________________

## 1. Completed Issues

Note: Ordered chronologically by completion date.

- [x] **[#30](https://github.com/bdperkin/findfmt/issues/30)** - ci(pre-commit): consolidate
  .pre-commit-ci.yaml into .pre-commit-config.yaml and add pre-commit-ci-config hook (Closed:
  2026-10-07 via PR [#65](https://github.com/bdperkin/findfmt/pull/65))
- [x] **[#28](https://github.com/bdperkin/findfmt/issues/28)** - ci(pre-commit): migrate local
  workspace hooks to upstream repositories (ty, interrogate, deptry, vulture, xenon,
  sync-pre-commit-deps) (Closed: 2026-10-07 via PR
  [#66](https://github.com/bdperkin/findfmt/pull/66))
- [x] **[#27](https://github.com/bdperkin/findfmt/issues/27)** - ci(pre-commit): audit and configure
  comprehensive pre-commit hooks and rule overrides (Closed: 2026-10-07 via PR
  [#67](https://github.com/bdperkin/findfmt/pull/67))
- [x] **[#29](https://github.com/bdperkin/findfmt/issues/29)** - ci(pre-commit): integrate advanced
  uv, packaging, markdown, and code hygiene hooks (Closed: 2026-10-07 via PR
  [#67](https://github.com/bdperkin/findfmt/pull/67))
- [x] **[#11](https://github.com/bdperkin/findfmt/issues/11)** - docs: configure accessibility
  statement (ACCESSIBILITY.md) (Closed: 2026-10-07 via PR
  [#68](https://github.com/bdperkin/findfmt/pull/68))
- [x] **[#10](https://github.com/bdperkin/findfmt/issues/10)** - ci(security): configure GitGuardian
  (ggshield CI action, pre-commit hook, and .gitguardian.yaml) (Closed: 2026-10-07 via PR
  [#69](https://github.com/bdperkin/findfmt/pull/69))
- [x] **[#9](https://github.com/bdperkin/findfmt/issues/9)** - ci: configure Codecov (codecov.yml,
  upload token, and coverage targets) (Closed: 2026-10-07 via PR
  [#69](https://github.com/bdperkin/findfmt/pull/69))
- [x] **[#39](https://github.com/bdperkin/findfmt/issues/39)** - docs(readme): identify and evaluate
  additional badges for README and documentation (Closed: 2026-10-07 via PR
  [#70](https://github.com/bdperkin/findfmt/pull/70))
- [x] **[#6](https://github.com/bdperkin/findfmt/issues/6)** - docs: cross-link documentation site
  (GitHub Pages) and GitHub repository/issue tracker (Closed: 2026-10-07 via PR
  [#71](https://github.com/bdperkin/findfmt/pull/71))
- [x] **[#8](https://github.com/bdperkin/findfmt/issues/8)** - feat(community): expand and refine
  GitHub issue templates to streamline contributor feedback (Closed: 2026-10-07 via PR
  [#72](https://github.com/bdperkin/findfmt/pull/72))
- [x] **[#7](https://github.com/bdperkin/findfmt/issues/7)** - feat(assets): create asset generation
  tool and generate social media preview card (Closed: 2026-10-07 via PR
  [#73](https://github.com/bdperkin/findfmt/pull/73))
- [x] **[#13](https://github.com/bdperkin/findfmt/issues/13)** - meta(labels): investigate and
  define extended repository label taxonomy for issues and PRs (Closed: 2026-10-07 via PR
  [#74](https://github.com/bdperkin/findfmt/pull/74))
- [x] **[#12](https://github.com/bdperkin/findfmt/issues/12)** - ci: evaluate and integrate new
  GitHub Actions workflows across core categories (Closed: 2026-10-07 via PR
  [#75](https://github.com/bdperkin/findfmt/pull/75))
- [x] **[#37](https://github.com/bdperkin/findfmt/issues/37)** - sec(audit): comprehensive security
  review and vulnerability assessment of codebase and workflows (Closed: 2026-10-07 via PR
  [#77](https://github.com/bdperkin/findfmt/pull/77))
- [x] **[#14](https://github.com/bdperkin/findfmt/issues/14)** - meta: audit and validate full
  implementation of original master prompt requirements (Closed: 2026-10-07 via manual audit
  verification)
- [x] **[#15](https://github.com/bdperkin/findfmt/issues/15)** - release: configure PyPI and
  TestPyPI Trusted Publishers (OIDC) manual setup (Closed: 2026-10-07 via OIDC workflow
  verification)
- [x] **[#41](https://github.com/bdperkin/findfmt/issues/41)** - release: execute initial release
  v0.1.0 to PyPI, TestPyPI, and GHCR container registry (Closed: 2026-10-07 via v0.1.0 release
  workflow)
- [x] **[#79](https://github.com/bdperkin/findfmt/issues/79)** - ci(testing): configure Codecov Test
  Analytics for test execution insights and flaky test detection (Closed: 2026-10-07 via PR
  [#80](https://github.com/bdperkin/findfmt/pull/80))
- [x] **[#89](https://github.com/bdperkin/findfmt/issues/89)** - ci(pre-commit): switch mdformat
  repo URL from redirected executablebooks/mdformat to canonical hukkin/mdformat (Closed: 2026-10-07
  via PR [#90](https://github.com/bdperkin/findfmt/pull/90))
- [x] **[#91](https://github.com/bdperkin/findfmt/issues/91)** - ci(pre-commit): add
  markdown-heading-numbering hook from jsh9/markdown-heading-numbering (Closed: 2026-10-07 via PR
  [#92](https://github.com/bdperkin/findfmt/pull/92))
- [x] **[#93](https://github.com/bdperkin/findfmt/issues/93)** - ci(pre-commit): add pymarkdown
  linter hook and configuration from jackdewinter/pymarkdown (Closed: 2026-10-07 via PR
  [#94](https://github.com/bdperkin/findfmt/pull/94))
- [x] **[#84](https://github.com/bdperkin/findfmt/issues/84)** - docs(packaging): fix broken logo
  image URL on PyPI and TestPyPI by using absolute raw asset URL (Closed: 2026-10-07 via PR
  [#95](https://github.com/bdperkin/findfmt/pull/95))
- [x] **[#83](https://github.com/bdperkin/findfmt/issues/83)** - docs(badges): investigate and fix
  "package or version not found" errors on PyPI, Python, and Wheel badges (Closed: 2026-10-07 via PR
  [#96](https://github.com/bdperkin/findfmt/pull/96))
- [x] **[#81](https://github.com/bdperkin/findfmt/issues/81)** - ci(coverage): configure Codecov
  Components to organize coverage data by file paths (Closed: 2026-10-07 via PR
  [#97](https://github.com/bdperkin/findfmt/pull/97))
- [x] **[#88](https://github.com/bdperkin/findfmt/issues/88)** - sec(scorecard): address OpenSSF
  Scorecard repository posture findings (Code-Review, CII-Best-Practices, Fuzzing, Maintained)
  (Closed: 2026-10-07 via PR [#98](https://github.com/bdperkin/findfmt/pull/98))
- [x] **[#82](https://github.com/bdperkin/findfmt/issues/82)** - ci(deployments): configure GitHub
  repository environments and deployment tracking for GitHub Pages, TestPyPI, and PyPI (Closed:
  2026-10-07 via PR [#99](https://github.com/bdperkin/findfmt/pull/99))
- [x] **[#87](https://github.com/bdperkin/findfmt/issues/87)** - sec(scorecard): enforce
  least-privilege token permissions across GitHub Actions workflows (Closed: 2026-10-07 via PR
  [#100](https://github.com/bdperkin/findfmt/pull/100))
- [x] **[#86](https://github.com/bdperkin/findfmt/issues/86)** - sec(scorecard): pin GitHub Actions
  workflows and Docker base images to immutable commit SHAs and digests (Closed: 2026-10-07 via PR
  [#101](https://github.com/bdperkin/findfmt/pull/101))
- [x] **[#85](https://github.com/bdperkin/findfmt/issues/85)** - ci(release): confirm and validate
  automated changelog generation with git-cliff (Closed: 2026-10-07 via PR
  [#102](https://github.com/bdperkin/findfmt/pull/102))
- [x] **[#16](https://github.com/bdperkin/findfmt/issues/16)** - refactor(cli): migrate CLI parser
  from argparse to Typer with automated docgen (Closed: 2026-10-07 via PR
  [#105](https://github.com/bdperkin/findfmt/pull/105))
- [x] **[#17](https://github.com/bdperkin/findfmt/issues/17)** - feat(cli): map multiple CLI entry
  points in pyproject.toml to thin Typer wrapper functions (Closed: 2026-10-07 via PR
  [#106](https://github.com/bdperkin/findfmt/pull/106))
- [x] **[#25](https://github.com/bdperkin/findfmt/issues/25)** - feat(cli): investigate and
  implement miscellaneous options (option toggling/negation, detailed usage, version, and -- option
  terminator) (Closed: 2026-10-07 via PR [#108](https://github.com/bdperkin/findfmt/pull/108))
- [x] **[#26](https://github.com/bdperkin/findfmt/issues/26)** - feat(packaging): investigate
  minimum and maximum supported Python versions (3.6, 3.9 through 3.15) for requires-python and
  classifiers (Closed: 2026-10-07 via PR [#115](https://github.com/bdperkin/findfmt/pull/115))
- [x] **[#104](https://github.com/bdperkin/findfmt/issues/104)** - test(fuzz): integrate
  ClusterFuzzLite continuous fuzzing (Closed: 2026-10-07 via PR
  [#116](https://github.com/bdperkin/findfmt/pull/116))
- [x] **[#109](https://github.com/bdperkin/findfmt/issues/109)** - ci(docs): integrate Vale prose
  linter for Markdown documentation (Closed: 2026-10-07 via PR
  [#117](https://github.com/bdperkin/findfmt/pull/117))
- [x] **[#110](https://github.com/bdperkin/findfmt/issues/110)** - feat(tools): add file line length
  enforcement tool (tools/) (Closed: 2026-10-07 via PR
  [#118](https://github.com/bdperkin/findfmt/pull/118))
- [x] **[#124](https://github.com/bdperkin/findfmt/issues/124)** - fix(tools): enforce total file
  line count limits and modularize CLI (Closed: 2026-10-08 via PR
  [#125](https://github.com/bdperkin/findfmt/pull/125))
- [x] **[#126](https://github.com/bdperkin/findfmt/issues/126)** - sec(clusterfuzzlite): pin
  dependencies by hash to resolve OpenSSF Scorecard alert #79 (Closed: 2026-10-08 via PR
  [#127](https://github.com/bdperkin/findfmt/pull/127))
- [x] **[#128](https://github.com/bdperkin/findfmt/issues/128)** - ci(clusterfuzzlite): restrict
  fuzzing workflow to merges on main, scheduled runs, and manual dispatch (Closed: 2026-10-08 via PR
  [#129](https://github.com/bdperkin/findfmt/pull/129))
- [x] **[#130](https://github.com/bdperkin/findfmt/issues/130)** - ci(vale): resolve flaky Vale
  workflow by pinning binary version and disabling dynamic sync (Closed: 2026-10-08 via PR
  [#131](https://github.com/bdperkin/findfmt/pull/131))
- [x] **[#132](https://github.com/bdperkin/findfmt/issues/132)** - ci(vale): scope .vale.ini with
  negative glob to exclude internal directories (Closed: 2026-10-08 via PR
  [#133](https://github.com/bdperkin/findfmt/pull/133))
- [x] **[#134](https://github.com/bdperkin/findfmt/issues/134)** - ci(vale): resolve flaky Vale
  workflow with style caching, trigger scoping, and alert limits (Closed: 2026-10-08 via PR
  [#135](https://github.com/bdperkin/findfmt/pull/135))
- [x] **[#46](https://github.com/bdperkin/findfmt/issues/46)** - feat(format): implement structured
  data serializers (json, jsonl, yaml, ipynb) (Closed: 2026-10-09 via PR
  [#119](https://github.com/bdperkin/findfmt/pull/119))
- [x] **[#48](https://github.com/bdperkin/findfmt/issues/48)** - feat(format): implement tabular,
  delimited, and markup serializers (csv, tsv, markdown, rst) (Closed: 2026-10-09 via PR
  [#120](https://github.com/bdperkin/findfmt/pull/120))
- [x] **[#137](https://github.com/bdperkin/findfmt/issues/137)** - fix(traversal): handle re.error
  when compiling invalid gitignore patterns (Closed: 2026-10-09 via PR
  [#138](https://github.com/bdperkin/findfmt/pull/138))
- [x] **[#49](https://github.com/bdperkin/findfmt/issues/49)** - feat(format): implement Rich visual
  formatters (tables, custom border styles, tree view) (Closed: 2026-10-09 via PR
  [#139](https://github.com/bdperkin/findfmt/pull/139))
- [x] **[#50](https://github.com/bdperkin/findfmt/issues/50)** - feat(cli): implement interactive
  terminal pager integration and TTY/NO_COLOR handling (Closed: 2026-10-09 via PR
  [#140](https://github.com/bdperkin/findfmt/pull/140))
- [x] **[#22](https://github.com/bdperkin/findfmt/issues/22)** - feat(cli): investigate and
  implement graphics, indentation, and colorization options (-i, -A, -S, -n, -C) (Closed: 2026-10-09
  via PR [#141](https://github.com/bdperkin/findfmt/pull/141))
- [x] **[#18](https://github.com/bdperkin/findfmt/issues/18)** - feat(cli): comprehensive
  multi-format output suite (Rich tables, tree view, markup, data formats, and pager) (Closed:
  2026-10-09 via PR [#142](https://github.com/bdperkin/findfmt/pull/142))
- [x] **[#147](https://github.com/bdperkin/findfmt/issues/147)** - sec(release): constrain PyPI and
  TestPyPI Trusted Publishers to dedicated GitHub environments (Closed: 2026-10-09 via PR
  [#148](https://github.com/bdperkin/findfmt/pull/148))
- [x] **[#144](https://github.com/bdperkin/findfmt/issues/144)** - feat(cli): add interactive pager
  for --help, --help-all, and tall TTY diagnostic outputs (Closed: 2026-10-10 via PR
  [#149](https://github.com/bdperkin/findfmt/pull/149))
- [x] **[#151](https://github.com/bdperkin/findfmt/issues/151)** - fix(cli): preserve ANSI
  colorization when paging --help output (Closed: 2026-10-10 via PR
  [#152](https://github.com/bdperkin/findfmt/pull/152))
- [x] **[#145](https://github.com/bdperkin/findfmt/issues/145)** - feat(cli): add relative path
  prefix option to preserve target path in listings (--relative / --no-relative) (Closed: 2026-10-12
  via PR [#154](https://github.com/bdperkin/findfmt/pull/154))
- [x] **[#146](https://github.com/bdperkin/findfmt/issues/146)** - feat(traversal): expand
  .gitignore and .git/info/exclude discovery across ancestor hierarchy and nested subtrees (Closed:
  2026-10-12 via PR [#155](https://github.com/bdperkin/findfmt/pull/155))
- [x] **[#51](https://github.com/bdperkin/findfmt/issues/51)** - feat(traversal): implement
  traversal boundaries, depth limits, and empty directory pruning (-d, -l, -x, -L, --filelimit,
  --prune) (Closed: 2026-10-12 via PR [#156](https://github.com/bdperkin/findfmt/pull/156))
- [x] **[#52](https://github.com/bdperkin/findfmt/issues/52)** - feat(traversal): implement wildcard
  and glob pattern matching (-P, -I, --ignore-case, --match-dirs) (Closed: 2026-10-13 via PR
  [#157](https://github.com/bdperkin/findfmt/pull/157))
- [x] **[#150](https://github.com/bdperkin/findfmt/issues/150)** - refactor(cli): modularize flat
  CLI modules into dedicated cli package (Closed: 2026-10-13 via PR
  [#159](https://github.com/bdperkin/findfmt/pull/159))
- [x] **[#160](https://github.com/bdperkin/findfmt/issues/160)** - refactor(traversal): modularize
  flat traversal modules into dedicated traversal package (Closed: 2026-10-13 via PR
  [#161](https://github.com/bdperkin/findfmt/pull/161))
- [x] **[#53](https://github.com/bdperkin/findfmt/issues/53)** - feat(traversal): implement ignore
  engine extensions and file output redirection (--gitignore-file, global gitignore, -o) (Closed:
  2026-10-13 via PR [#162](https://github.com/bdperkin/findfmt/pull/162))
- [x] **[#21](https://github.com/bdperkin/findfmt/issues/21)** - feat(traversal): investigate and
  implement comprehensive sorting options (name, time, size, version, dirs-first) (Closed:
  2026-10-13 via PR [#163](https://github.com/bdperkin/findfmt/pull/163))
- [x] **[#24](https://github.com/bdperkin/findfmt/issues/24)** - feat(cli): investigate and
  implement input options (--from-file, tab-indented parsing, symlink processing) (Closed:
  2026-10-13 via PR [#164](https://github.com/bdperkin/findfmt/pull/164))
- [x] **[#19](https://github.com/bdperkin/findfmt/issues/19)** - feat(traversal): investigate and
  implement advanced listing, filtering, and traversal options (Closed: 2026-10-13 via PR
  [#165](https://github.com/bdperkin/findfmt/pull/165))
- [x] **[#54](https://github.com/bdperkin/findfmt/issues/54)** - feat(metadata): implement
  permissions, ownership, and system identifiers (-p, -u, -g, --inodes, --device) (Closed:
  2026-10-14 via PR [#167](https://github.com/bdperkin/findfmt/pull/167))
- [x] **[#55](https://github.com/bdperkin/findfmt/issues/55)** - feat(metadata): implement file size
  formatting and disk usage accumulation (--size, -h, --si, --du) (Closed: 2026-10-14 via PR
  [#168](https://github.com/bdperkin/findfmt/pull/168))
- [x] **[#56](https://github.com/bdperkin/findfmt/issues/56)** - feat(metadata): implement
  timestamps, classification indicators, and quoting (-D, --ctime, -F, -q, -N, -Q) (Closed:
  2026-10-14 via PR [#169](https://github.com/bdperkin/findfmt/pull/169))
- [x] **[#20](https://github.com/bdperkin/findfmt/issues/20)** - feat(cli): investigate and
  implement extended file metadata and display options (Closed: 2026-10-14 via PR
  [#170](https://github.com/bdperkin/findfmt/pull/170))
- [x] **[#57](https://github.com/bdperkin/findfmt/issues/57)** - feat(format): implement XML and
  HTML document serializers with intro/outro templating (-X, -H, --intro, --outro, -T, --nolinks)
  (Closed: 2026-10-14 via PR [#172](https://github.com/bdperkin/findfmt/pull/172))
- [x] **[#58](https://github.com/bdperkin/findfmt/issues/58)** - feat(cli): implement OSC 8
  clickable terminal hyperlinks with schema and authority overrides (--hyperlink) (Closed:
  2026-10-14 via PR [#173](https://github.com/bdperkin/findfmt/pull/173))
- [x] **[#23](https://github.com/bdperkin/findfmt/issues/23)** - feat(format): investigate and
  implement XML, HTML, JSON, and terminal hyperlink (OSC 8) options (Closed: 2026-10-14 via PR
  [#174](https://github.com/bdperkin/findfmt/pull/174))
- [x] **[#61](https://github.com/bdperkin/findfmt/issues/61)** - perf(benchmark): create automated
  benchmark harness (tools/benchmark.py) tracking throughput and memory (Closed: 2026-10-14 via PR
  [#176](https://github.com/bdperkin/findfmt/pull/176))
- [x] **[#62](https://github.com/bdperkin/findfmt/issues/62)** - perf(engine): optimize filesystem
  traversal, eliminate redundant resolve() calls, and single-buffer content reads (Closed:
  2026-10-14 via PR [#182](https://github.com/bdperkin/findfmt/pull/182))
- [x] **[#38](https://github.com/bdperkin/findfmt/issues/38)** - perf(engine): analyze traversal and
  classification performance bottlenecks and implement optimizations (Closed: 2026-10-14 via PR
  [#183](https://github.com/bdperkin/findfmt/pull/183))
- [x] **[#31](https://github.com/bdperkin/findfmt/issues/31)** - docs(sphinx): implement and verify
  Web & Digital formats (html, dirhtml, singlehtml, epub) (Closed: 2026-10-14 via PR
  [#185](https://github.com/bdperkin/findfmt/pull/185))
- [x] **[#32](https://github.com/bdperkin/findfmt/issues/32)** - docs(sphinx): implement and verify
  Print & Offline formats (latexpdf, text, man, texinfo) (Closed: 2026-10-14 via PR
  [#186](https://github.com/bdperkin/findfmt/pull/186))
- [x] **[#33](https://github.com/bdperkin/findfmt/issues/33)** - docs(sphinx): implement and verify
  Help System formats (htmlhelp, qthelp, devhelp) (Closed: 2026-10-14 via PR
  [#187](https://github.com/bdperkin/findfmt/pull/187))
- [x] **[#34](https://github.com/bdperkin/findfmt/issues/34)** - docs(sphinx): implement and verify
  Data & Serialization formats (json, pickle, xml, pseudoxml) (Closed: 2026-10-15 via PR
  [#188](https://github.com/bdperkin/findfmt/pull/188))
- [x] **[#35](https://github.com/bdperkin/findfmt/issues/35)** - docs(sphinx): implement and verify
  Localization & Quality Control builders (gettext, linkcheck, changes) (Closed: 2026-10-15 via PR
  [#189](https://github.com/bdperkin/findfmt/pull/189))
- [x] **[#59](https://github.com/bdperkin/findfmt/issues/59)** - feat(i18n): implement core gettext
  runtime engine, CLI message wrapping, and locale detection (Closed: 2026-10-15 via PR
  [#191](https://github.com/bdperkin/findfmt/pull/191))
- [x] **[#60](https://github.com/bdperkin/findfmt/issues/60)** - feat(i18n): implement message
  catalog extraction, Hatchling MO compilation build hook, and Sphinx-intl (Closed: 2026-10-15 via
  PR [#192](https://github.com/bdperkin/findfmt/pull/192))
- [x] **[#36](https://github.com/bdperkin/findfmt/issues/36)** - feat(i18n): implement
  internationalization (i18n) and localization (l10n) across CLI, engine, and documentation (Closed:
  2026-10-15 via PR [#193](https://github.com/bdperkin/findfmt/pull/193))
- [x] **[#63](https://github.com/bdperkin/findfmt/issues/63)** - docs(community): update root
  governance, security, contributing, and changelog documents (Closed: 2026-10-16 via PR
  [#272](https://github.com/bdperkin/findfmt/pull/272))
- [x] **[#64](https://github.com/bdperkin/findfmt/issues/64)** - docs(sphinx): audit and expand user
  guides, CLI reference, and man page (Closed: 2026-10-16 via PR
  [#273](https://github.com/bdperkin/findfmt/pull/273))
- [x] **[#40](https://github.com/bdperkin/findfmt/issues/40)** - docs: comprehensively analyze and
  update all project documentation to match state and best practices (Closed: 2026-10-16 via PR
  [#274](https://github.com/bdperkin/findfmt/pull/274))
- [x] **[#281](https://github.com/bdperkin/findfmt/issues/281)** - feat(config): implement or
  reconcile FINDFMT_CONFIG configuration file support (Closed: 2026-10-16 via PR
  [#285](https://github.com/bdperkin/findfmt/pull/285))
- [x] **[#282](https://github.com/bdperkin/findfmt/issues/282)** - fix(cli): graceful Unix signal
  handling (SIGPIPE/SIGINT) and pipeline resilience (Closed: 2026-10-16 via PR
  [#286](https://github.com/bdperkin/findfmt/pull/286))
- [x] **[#283](https://github.com/bdperkin/findfmt/issues/283)** - sec(terminal): audit and enforce
  ANSI/control-character sanitization for untrusted filenames (Closed: 2026-10-19 via PR
  [#287](https://github.com/bdperkin/findfmt/pull/287))
- [x] **[#277](https://github.com/bdperkin/findfmt/issues/277)** - refactor(api): API surface
  stability & public contract verification (Closed: 2026-10-19 via PR
  [#288](https://github.com/bdperkin/findfmt/pull/288))
- [x] **[#280](https://github.com/bdperkin/findfmt/issues/280)** - test(audit): final smoke testing
  & edge-case quality audit for v1.0.0 (Closed: 2026-10-19 via PR
  [#289](https://github.com/bdperkin/findfmt/pull/289))
- [x] **[#284](https://github.com/bdperkin/findfmt/issues/284)** - perf(benchmark): establish
  official v1.0.0 traversal throughput and memory baselines (Closed: 2026-10-19 via PR
  [#290](https://github.com/bdperkin/findfmt/pull/290))
- [x] **[#278](https://github.com/bdperkin/findfmt/issues/278)** - docs(sphinx): documentation &
  discoverability polish for v1.0.0 (Closed: 2026-10-19 via PR
  [#293](https://github.com/bdperkin/findfmt/pull/293))
- [x] **[#279](https://github.com/bdperkin/findfmt/issues/279)** - sec(packaging): packaging,
  distribution & supply chain security verification for v1.0.0 (Closed: 2026-10-19 via PR
  [#294](https://github.com/bdperkin/findfmt/pull/294))
- [x] **[#315](https://github.com/bdperkin/findfmt/issues/315)** - fix(format): non-UTF-8 filenames
  crash all output modes with UnicodeEncodeError (Closed: 2026-10-19 via PR
  [#387](https://github.com/bdperkin/findfmt/pull/387))
- [x] **[#316](https://github.com/bdperkin/findfmt/issues/316)** - fix(cli): -0/findfmt0 and piped
  text output silently rewrite filenames (Closed: 2026-10-20 via PR
  [#390](https://github.com/bdperkin/findfmt/pull/390))
- [x] **[#317](https://github.com/bdperkin/findfmt/issues/317)** - fix(i18n): wheels built in
  isolation ship .mo files without a charset, so translations silently fall back to English (Closed:
  2026-10-20 via PR [#391](https://github.com/bdperkin/findfmt/pull/391))
- [x] **[#318](https://github.com/bdperkin/findfmt/issues/318)** - fix(traversal): symlink-follow
  mode crashes on OSError, and --prune has no cycle guard (Closed: 2026-10-20 via PR
  [#393](https://github.com/bdperkin/findfmt/pull/393))
- [x] **[#370](https://github.com/bdperkin/findfmt/issues/370)** - [Core] Prevent crash in --sort
  version when encountering Unicode superscript and non-decimal digits (Closed: 2026-10-20 via PR
  [#395](https://github.com/bdperkin/findfmt/pull/395))
- [x] **[#371](https://github.com/bdperkin/findfmt/issues/371)** - [Core] Eliminate os.scandir
  handle leaks on early termination and enable ResourceWarning in test suite (Closed: 2026-10-20 via
  PR [#396](https://github.com/bdperkin/findfmt/pull/396))
- [x] **[#231](https://github.com/bdperkin/findfmt/issues/231)** - feat(i18n): localize file sizes,
  numeric separators, and timestamps per regional locale standards (Closed: 2026-10-20 via PR
  [#397](https://github.com/bdperkin/findfmt/pull/397))
- [x] **[#232](https://github.com/bdperkin/findfmt/issues/232)** - test(i18n): create automated
  verification suite for complex multi-tier gettext pluralization rules (Closed: 2026-10-20 via PR
  [#399](https://github.com/bdperkin/findfmt/pull/399))
- [x] **[#361](https://github.com/bdperkin/findfmt/issues/361)** - [Security] Eliminate quadratic
  ReDoS vulnerability in C1-OSC terminal control-sequence regex (Closed: 2026-10-20 via PR
  [#402](https://github.com/bdperkin/findfmt/pull/402))
- [x] **[#362](https://github.com/bdperkin/findfmt/issues/362)** - [Security] Mask Unicode
  bidirectional (bidi) override characters in TTY display mode (Closed: 2026-10-20 via PR
  [#403](https://github.com/bdperkin/findfmt/pull/403))
- [x] **[#363](https://github.com/bdperkin/findfmt/issues/363)** - [Security] Prevent infinite hang
  during file classification when target is swapped for a FIFO (Closed: 2026-10-20 via PR
  [#404](https://github.com/bdperkin/findfmt/pull/404))
- [x] **[#333](https://github.com/bdperkin/findfmt/issues/333)** - fix(format): Markdown output does
  not escape raw HTML in filenames (Closed: 2026-10-20 via PR
  [#410](https://github.com/bdperkin/findfmt/pull/410))
- [x] **[#339](https://github.com/bdperkin/findfmt/issues/339)** - feat(format): add --csv-safe to
  neutralise spreadsheet formula injection (Closed: 2026-10-20 via PR
  [#411](https://github.com/bdperkin/findfmt/pull/411))
- [x] **[#368](https://github.com/bdperkin/findfmt/issues/368)** - [CLI] Ensure atomic file output
  for -o/--output flag using temporary file and atomic replace (Closed: 2026-10-20 via PR
  [#413](https://github.com/bdperkin/findfmt/pull/413))
- [x] **[#415](https://github.com/bdperkin/findfmt/issues/415)** - [CI] Configure Dependabot
  dependency groups for codeql-action and package ecosystem updates (Closed: 2026-10-21 via PR
  [#416](https://github.com/bdperkin/findfmt/pull/416))
- [x] **[#230](https://github.com/bdperkin/findfmt/issues/230)** - fix(format): audit and enforce
  cell-width alignment for CJK double-width characters across formatters (Closed: 2026-10-21 via PR
  [#420](https://github.com/bdperkin/findfmt/pull/420))
- [x] **[#214](https://github.com/bdperkin/findfmt/issues/214)** - feat(i18n): add language support
  for English (en) (~1.46 billion) (Closed: 2026-10-21 via PR
  [#421](https://github.com/bdperkin/findfmt/pull/421))
- [x] **[#338](https://github.com/bdperkin/findfmt/issues/338)** - [Epic] Security Hardening:
  Terminal Sanitization, ReDoS Prevention, and Filesystem FIFO Safety (Closed: 2026-10-21 via PR
  [#422](https://github.com/bdperkin/findfmt/pull/422))
- [x] **[#428](https://github.com/bdperkin/findfmt/issues/428)** - ci(deps): add curated dependency
  resolution smoke matrix to PR workflow (Closed: 2026-10-21 via PR
  [#432](https://github.com/bdperkin/findfmt/pull/432))
- [x] **[#326](https://github.com/bdperkin/findfmt/issues/326)** - test: make the suite hermetic
  against the developer's global git config (Closed: 2026-10-21 via PR
  [#433](https://github.com/bdperkin/findfmt/pull/433))
- [x] **[#356](https://github.com/bdperkin/findfmt/issues/356)** - [CI] Enforce --locked flag on all
  uv sync workflow invocations (Closed: 2026-10-21 via PR
  [#434](https://github.com/bdperkin/findfmt/pull/434))
- [x] **[#357](https://github.com/bdperkin/findfmt/issues/357)** - [CI] Configure full-history
  fetch-depth (fetch-depth: 0) for release and version-sensitive jobs (Closed: 2026-10-21 via PR
  [#435](https://github.com/bdperkin/findfmt/pull/435))
- [x] **[#352](https://github.com/bdperkin/findfmt/issues/352)** - [Core] Align format_size
  base-1024 unit labels to binary standards (Closed: 2026-10-21 via PR
  [#436](https://github.com/bdperkin/findfmt/pull/436))
- [x] **[#367](https://github.com/bdperkin/findfmt/issues/367)** - [CLI] Add --exit-status flag to
  return exit code 1 when no matching files are found (Closed: 2026-10-21 via PR
  [#437](https://github.com/bdperkin/findfmt/pull/437))
- [x] **[#373](https://github.com/bdperkin/findfmt/issues/373)** - [CLI] Align console wrapper
  entrypoint exit code mapping for SystemExit exceptions (Closed: 2026-10-21 via PR
  [#438](https://github.com/bdperkin/findfmt/pull/438))
- [x] **[#354](https://github.com/bdperkin/findfmt/issues/354)** - [Core] Preserve significant
  leading and escaped trailing whitespace in gitignore parser (Closed: 2026-10-22 via PR
  [#439](https://github.com/bdperkin/findfmt/pull/439))
- [x] **[#213](https://github.com/bdperkin/findfmt/issues/213)** - [Epic] Add Language Support:
  Extinct (0 Living Speakers) (Closed: 2026-10-21 as not planned; no CLDR locale data for `got`)
- [x] **[#443](https://github.com/bdperkin/findfmt/issues/443)** - fix(packaging): correct
  "A.gitignore-aware" typo in the PyPI summary (Closed: 2026-10-22 via PR
  [#466](https://github.com/bdperkin/findfmt/pull/466))
- [x] **[#364](https://github.com/bdperkin/findfmt/issues/364)** - [Docs] Correct inaccurate and
  duplicated CLI option flags across documentation guides and README (Closed: 2026-10-22 via PR
  [#467](https://github.com/bdperkin/findfmt/pull/467))
- [x] **[#473](https://github.com/bdperkin/findfmt/issues/473)** - ci(pre-commit): evaluate autopep8
  hook (conflicts with ruff-format; recommend not adopting) (Closed: 2026-10-22 as not planned;
  conflicts with `ruff-format` and is redundant with `ruff`)

______________________________________________________________________

## 2. Prioritized Open Implementation Roadmap

Note: Sorted strictly by Value:Effort ratio (highest ROI first), independent of milestone or epic
ordering. Value weights High=5, Medium=3, Low=1; effort weights S=1, M=2, L=4, XL=8. Buckets are ROI
bands: Quick Wins >= 2.5, Core Deliverables 0.75-2.5, Backlog < 0.75. Ties break by milestone, then
issue number. Decomposed tracking issues are listed in Section 3 and are delivered through their
sub-issues. Respect `Blocked by` links when picking up work.

### 2.1. High Priority / Quick Wins

- [ ] **[#322](https://github.com/bdperkin/findfmt/issues/322)** - fix(traversal):
  traverse_directory() ignores .gitignore when given a relative root *(Rank: 1 | Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.3)* - **Value:** High | **Effort:** S - **Rationale:** Library API ignores
  .gitignore for relative roots; small fix.
- [ ] **[#330](https://github.com/bdperkin/findfmt/issues/330)** - fix(format): -f ipynb emits JSON
  literals (null/false) that raise NameError when run *(Rank: 2 | Epic:
  [[Epic] Formatter Integrity: Encoding Robustness, Stream Sanitization & Format Parity](https://github.com/bdperkin/findfmt/issues/384)
  | Milestone: v1.0.4)* - **Value:** High | **Effort:** S - **Rationale:** Generated notebooks
  crash; tiny fix.
- [ ] **[#454](https://github.com/bdperkin/findfmt/issues/454)** - fix(config): wrapper entry-point
  defaults override values from the config file *(Rank: 3 | Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Parent: [#332](https://github.com/bdperkin/findfmt/issues/332) | Milestone: v1.0.4)* -
  **Value:** High | **Effort:** S - **Rationale:** Real user-facing bug (config silently ignored);
  small fix.
- [ ] **[#325](https://github.com/bdperkin/findfmt/issues/325)** - build(deps): make the
  lowest-direct dependency job required and verify floors on the minimum interpreter *(Rank: 4 |
  Epic:
  [[Epic] Packaging Integrity, Release Automation & Dependency Verification](https://github.com/bdperkin/findfmt/issues/385)
  | Milestone: v1.0.6)* - **Value:** High | **Effort:** S - **Rationale:** Job is now a required
  check; remaining: run floors on the minimum interpreter and re-verify rich/pathspec/identify.
- [ ] **[#327](https://github.com/bdperkin/findfmt/issues/327)** - ci(release): workflow_dispatch
  ignores the "tag" input and can publish a .devN build to PyPI *(Rank: 5 | Epic:
  [[Epic] Packaging Integrity, Release Automation & Dependency Verification](https://github.com/bdperkin/findfmt/issues/385)
  | Milestone: v1.0.6)* - **Value:** High | **Effort:** S - **Rationale:** Release safety: can
  publish a dev build to PyPI.
- [ ] **[#460](https://github.com/bdperkin/findfmt/issues/460)** - fix(parsers): read --from-file
  stdin and files as bytes with os.fsdecode (no crash on non-UTF-8 names) *(Rank: 6 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Parent: [#334](https://github.com/bdperkin/findfmt/issues/334) | Milestone: v1.1.2)* -
  **Value:** High | **Effort:** S - **Rationale:** Crash on real-world input; small fix.
- [ ] **[#369](https://github.com/bdperkin/findfmt/issues/369)** - [Docs] Document formal CLI
  exit-code contract with exhaustive test matrix *(Rank: 7 | Epic:
  [[Epic] CLI Exit Code Contract, Status Code Flags, and Atomic Output Writing](https://github.com/bdperkin/findfmt/issues/347)
  | Milestone: v1.0.4)* - **Value:** Medium | **Effort:** S - **Rationale:** Formalises the
  exit-code contract scripts rely on. Blocked by
  [#341](https://github.com/bdperkin/findfmt/issues/341).
- [ ] **[#335](https://github.com/bdperkin/findfmt/issues/335)** - ci: make the Python 3.15 CI job
  gating and add a non-gating Python 3.16 job *(Rank: 8 | Epic:
  [[Epic] Python Version Support Lifecycle: 3.11–3.15 Supported, 3.16 Preview](https://github.com/bdperkin/findfmt/issues/442)
  | Milestone: v1.0.6)* - **Value:** Medium | **Effort:** S - **Rationale:** 3.15 is advertised but
  untested; small CI change.
- [ ] **[#468](https://github.com/bdperkin/findfmt/issues/468)** - ci(security): add zizmor static
  analysis for GitHub Actions, Dependabot, and pre-commit configs *(Rank: 9 | Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.0.6)* - **Value:** Medium | **Effort:** S - **Rationale:** Audits workflow
  security; only `scorecard.yml` sets `persist-credentials: false`, so the first run will flag the
  other workflows.
- [ ] **[#475](https://github.com/bdperkin/findfmt/issues/475)** - ci(packaging): verify built
  sdist/wheel with twine check and check-wheel-contents on every PR *(Rank: 10 | Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.6)* - **Value:** Medium | **Effort:** S - **Rationale:** `twine check` runs only
  at release time and `check-wheel-contents` nowhere. Both pass today, so gating PRs is cheap.
  Complements [#358](https://github.com/bdperkin/findfmt/issues/358).
- [ ] **[#452](https://github.com/bdperkin/findfmt/issues/452)** - refactor(api): lazy-load main,
  main\_\* and _ from the package root via module \_\_getattr\_\_ *(Rank: 11 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Parent: [#324](https://github.com/bdperkin/findfmt/issues/324) | Milestone: v1.1.0)* -
  **Value:** Medium | **Effort:** S - **Rationale:** Small change that removes most import cost and
  unblocks [#377](https://github.com/bdperkin/findfmt/issues/377).
- [ ] **[#459](https://github.com/bdperkin/findfmt/issues/459)** - fix(parsers): strip ASCII tree
  branches and the summary trailer in --from-file tree input *(Rank: 12 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Parent: [#334](https://github.com/bdperkin/findfmt/issues/334) | Milestone: v1.1.2)* -
  **Value:** Medium | **Effort:** S - **Rationale:** Wrong output for a common input format; small
  fix.
- [ ] **[#461](https://github.com/bdperkin/findfmt/issues/461)** - feat(parsers): add NUL-delimited
  --from-file input mode (-0 / find -print0 compatibility) *(Rank: 13 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Parent: [#334](https://github.com/bdperkin/findfmt/issues/334) | Milestone: v1.1.2)* -
  **Value:** Medium | **Effort:** S - **Rationale:** Standard Unix interop; small.
- [ ] **[#462](https://github.com/bdperkin/findfmt/issues/462)** - fix(parsers): ctime sorting of
  --from-file entries uses st_mtime instead of st_ctime *(Rank: 14 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Parent: [#334](https://github.com/bdperkin/findfmt/issues/334) | Milestone: v1.1.2)* -
  **Value:** Medium | **Effort:** S - **Rationale:** Silent wrong ordering; trivial fix.
- [ ] **[#456](https://github.com/bdperkin/findfmt/issues/456)** - feat(config): add a FINDFMT\_\*
  environment-variable configuration layer *(Rank: 15 | Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Parent: [#332](https://github.com/bdperkin/findfmt/issues/332) | Milestone: v1.2.0)* -
  **Value:** Medium | **Effort:** S - **Rationale:** Standard CI ergonomics; small once layering
  exists.
- [ ] **[#457](https://github.com/bdperkin/findfmt/issues/457)** - feat(config): deprecate
  tree/json/xml boolean config keys in favour of format = *(Rank: 16 | Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Parent: [#332](https://github.com/bdperkin/findfmt/issues/332) | Milestone: v1.2.0)* -
  **Value:** Medium | **Effort:** S - **Rationale:** Simplifies the config surface; small.
- [ ] **[#470](https://github.com/bdperkin/findfmt/issues/470)** - ci(pre-commit): add
  check-jsonschema hooks to validate workflows, Dependabot, issue forms, and Codecov config *(Rank:
  17 | Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.2)* - **Value:** Medium | **Effort:** S - **Rationale:** Schema-validates
  workflows, Dependabot, issue forms and Codecov. 19 jobs lack `timeout-minutes` (6-hour default);
  set each from observed run times.
- [ ] **[#472](https://github.com/bdperkin/findfmt/issues/472)** - ci(markdown): run mdformat with
  frontmatter, gfm (incl. tables), and ruff plugins everywhere it is invoked *(Rank: 18 | Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.2)* - **Value:** Medium | **Effort:** S - **Rationale:** Adds `mdformat-ruff`,
  pins plugins and a shared `.mdformat.toml`. `mdformat-tables` is archived and merged into
  `mdformat-gfm`. Verified zero reformat diff. `wrap` follows
  [#314](https://github.com/bdperkin/findfmt/issues/314).
- [ ] **[#448](https://github.com/bdperkin/findfmt/issues/448)** - docs(i18n): decide the terminal
  BiDi rendering strategy (implicit terminal vs python-bidi vs none) *(Rank: 19 | Epic:
  [[Epic] i18n Platform Infrastructure: RTL/BiDi Rendering & Multilingual Documentation Builds](https://github.com/bdperkin/findfmt/issues/276)
  | Parent: [#229](https://github.com/bdperkin/findfmt/issues/229) | Milestone: v1.4.0)* -
  **Value:** Medium | **Effort:** S - **Rationale:** Cheap decision that de-risks all RTL work
  before Urdu/Arabic catalogs.
- [ ] **[#450](https://github.com/bdperkin/findfmt/issues/450)** - test(i18n): add RTL rendering
  fixtures and snapshot tests for ar, he, and fa *(Rank: 20 | Epic:
  [[Epic] i18n Platform Infrastructure: RTL/BiDi Rendering & Multilingual Documentation Builds](https://github.com/bdperkin/findfmt/issues/276)
  | Parent: [#229](https://github.com/bdperkin/findfmt/issues/229) | Milestone: v1.4.1)* -
  **Value:** Medium | **Effort:** S - **Rationale:** Locks in RTL behaviour cheaply; guards the
  Urdu/Arabic releases.
- [ ] **[#320](https://github.com/bdperkin/findfmt/issues/320)** - fix(traversal): missing or
  unreadable paths are silently skipped with exit 0 *(Rank: 21 | Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.3)* - **Value:** High | **Effort:** M - **Rationale:** Silent exit 0 on missing
  paths breaks scripts and CI.
- [ ] **[#323](https://github.com/bdperkin/findfmt/issues/323)** - fix(traversal): align global
  gitignore discovery with git (drop ~/.gitignore, use repo cwd, stop at repo root) *(Rank: 22 |
  Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.3)* - **Value:** High | **Effort:** M - **Rationale:** Global gitignore
  discovery diverges from git. Blocked by [#322](https://github.com/bdperkin/findfmt/issues/322).
- [ ] **[#304](https://github.com/bdperkin/findfmt/issues/304)** - feat(i18n): design and implement
  Python format placeholder & variable protection validation for AI translation *(Rank: 23 | Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.4)* - **Value:** High | **Effort:** M - **Rationale:** Protects existing human
  catalogs now; independent of AI.
- [ ] **[#319](https://github.com/bdperkin/findfmt/issues/319)** - fix(cli): wrapper entry points
  misparse value options; findfilefmt -o x tag truncates a file named "tag" *(Rank: 24 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.0)* - **Value:** High | **Effort:** M - **Rationale:** Wrapper commands
  mis-parse common options; can create stray files.
- [ ] **[#451](https://github.com/bdperkin/findfmt/issues/451)** - fix(i18n): defer locale
  initialisation so "import findfmt" does not change process locale *(Rank: 25 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Parent: [#324](https://github.com/bdperkin/findfmt/issues/324) | Milestone: v1.1.0)* -
  **Value:** High | **Effort:** M - **Rationale:** Silent library-side behaviour change for
  embedders; high value.
- [ ] **[#372](https://github.com/bdperkin/findfmt/issues/372)** - [Core] Replace recursive
  directory traversal and size calculation with iterative depth-safe implementations *(Rank: 26 |
  Epic:
  [[Epic] Traversal Engine Stability: Unicode Sorting, Scandir Leak Prevention, and Deep Tree Recursion Safety](https://github.com/bdperkin/findfmt/issues/336)
  | Milestone: v1.1.1)* - **Value:** High | **Effort:** M - **Rationale:** Deep trees silently
  return zero results.
- [ ] **[#463](https://github.com/bdperkin/findfmt/issues/463)** - fix(parsers): confine --from-file
  paths to the traversal root unless explicitly allowed *(Rank: 27 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Parent: [#334](https://github.com/bdperkin/findfmt/issues/334) | Milestone: v1.1.2)* -
  **Value:** High | **Effort:** M - **Rationale:** Security hardening for untrusted input lists.

### 2.2. Medium Priority / Core Deliverables

- [ ] **[#215](https://github.com/bdperkin/findfmt/issues/215)** - feat(i18n): add language support
  for German (de) (~133 million) *(Rank: 28 | Epic:
  [[Epic] Add Language Support: Germanic (~1.83 Billion)](https://github.com/bdperkin/findfmt/issues/197)
  | Milestone: v1.0.3)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for German (`de`, ~133 million); extends reach of the CLI to a large speaker base.
- [ ] **[#303](https://github.com/bdperkin/findfmt/issues/303)** - feat(i18n): benchmark and
  evaluate open-source Python gettext AI translators (gettext-translator, pytlai,
  auto-gettext-translator) *(Rank: 29 | Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.4)* - **Value:** Medium | **Effort:** M - **Rationale:** Evaluation prerequisite
  for the AI translation chain.
- [ ] **[#341](https://github.com/bdperkin/findfmt/issues/341)** - fix(format): consistent
  broken-pipe exit codes and respect --sort/--reverse in tree/HTML/XML *(Rank: 30 | Epic:
  [[Epic] Formatter Integrity: Encoding Robustness, Stream Sanitization & Format Parity](https://github.com/bdperkin/findfmt/issues/384)
  | Milestone: v1.0.4)* - **Value:** Medium | **Effort:** M - **Rationale:** Inconsistent
  broken-pipe exits break pipelines.
- [ ] **[#221](https://github.com/bdperkin/findfmt/issues/221)** - feat(i18n): add language support
  for Spanish (es) (~559 million) *(Rank: 31 | Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: v1.0.5)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Spanish (`es`, ~559 million); extends reach of the CLI to a large speaker base.
- [ ] **[#337](https://github.com/bdperkin/findfmt/issues/337)** - perf(traversal): eliminate
  redundant per-file syscalls and double classification under --prune *(Rank: 32 | Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.5)* - **Value:** Medium | **Effort:** M - **Rationale:** Rescoped to syscall
  reduction; quadratic prune already fixed. Blocked by
  [#345](https://github.com/bdperkin/findfmt/issues/345),
  [#321](https://github.com/bdperkin/findfmt/issues/321).
- [ ] **[#426](https://github.com/bdperkin/findfmt/issues/426)** - ci(deps): evaluate matrix tooling
  orchestration and define pruned resolution parameter matrix *(Rank: 33 | Epic:
  [[Epic] Exhaustive Dependency Resolution Matrix Testing via uv in CI and Tooling](https://github.com/bdperkin/findfmt/issues/425)
  | Milestone: v1.0.5)* - **Value:** Medium | **Effort:** M - **Rationale:** ADR that drives
  [#349](https://github.com/bdperkin/findfmt/issues/349),
  [#427](https://github.com/bdperkin/findfmt/issues/427) and
  [#429](https://github.com/bdperkin/findfmt/issues/429).
- [ ] **[#328](https://github.com/bdperkin/findfmt/issues/328)** - build(docker): image reports
  1.0.0.dev0, ignores uv.lock, ships uv, and lacks provenance *(Rank: 34 | Epic:
  [[Epic] Packaging Integrity, Release Automation & Dependency Verification](https://github.com/bdperkin/findfmt/issues/385)
  | Milestone: v1.0.6)* - **Value:** Medium | **Effort:** M - **Rationale:** Container
  reproducibility and supply chain. Blocked by
  [#327](https://github.com/bdperkin/findfmt/issues/327).
- [ ] **[#306](https://github.com/bdperkin/findfmt/issues/306)** - feat(i18n): integrate AI
  translation command into developer tooling (tools/i18n.py translate) *(Rank: 35 | Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.7)* - **Value:** Medium | **Effort:** M - **Rationale:** Integrates the chosen
  translator into tools/i18n.py. Blocked by [#305](https://github.com/bdperkin/findfmt/issues/305),
  [#304](https://github.com/bdperkin/findfmt/issues/304).
- [ ] **[#427](https://github.com/bdperkin/findfmt/issues/427)** - tools(deps): implement local
  dependency resolution matrix runner with failure diagnostics *(Rank: 36 | Epic:
  [[Epic] Exhaustive Dependency Resolution Matrix Testing via uv in CI and Tooling](https://github.com/bdperkin/findfmt/issues/425)
  | Milestone: v1.0.7)* - **Value:** Medium | **Effort:** M - **Rationale:** Local matrix runner;
  shares tooling with [#349](https://github.com/bdperkin/findfmt/issues/349). Blocked by
  [#426](https://github.com/bdperkin/findfmt/issues/426).
- [ ] **[#429](https://github.com/bdperkin/findfmt/issues/429)** - ci(deps): create exhaustive
  scheduled and dispatch dependency resolution matrix workflow *(Rank: 37 | Epic:
  [[Epic] Exhaustive Dependency Resolution Matrix Testing via uv in CI and Tooling](https://github.com/bdperkin/findfmt/issues/425)
  | Milestone: v1.0.7)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled exhaustive
  matrix. Blocked by [#426](https://github.com/bdperkin/findfmt/issues/426).
- [ ] **[#222](https://github.com/bdperkin/findfmt/issues/222)** - feat(i18n): add language support
  for French (fr) (~310 million) *(Rank: 38 | Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: v1.0.8)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for French (`fr`, ~310 million); extends reach of the CLI to a large speaker base.
- [ ] **[#228](https://github.com/bdperkin/findfmt/issues/228)** - feat(i18n): add language support
  for Japanese (ja) (~123 million) *(Rank: 39 | Epic:
  [[Epic] Add Language Support: Japonic & Koreanic (~205 Million)](https://github.com/bdperkin/findfmt/issues/205)
  | Milestone: v1.0.8)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Japanese (`ja`, ~123 million); extends reach of the CLI to a large speaker base.
- [ ] **[#329](https://github.com/bdperkin/findfmt/issues/329)** - fix(cli): invalid --table-style
  and other domain errors print full tracebacks *(Rank: 40 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for this language; extends reach of the CLI to a large speaker base.
- [ ] **[#440](https://github.com/bdperkin/findfmt/issues/440)** - build: set Python 3.15 as maximum
  supported version (3.11–3.15) and add non-gating Python 3.16 CI testing *(Rank: 41 | Epic:
  [[Epic] Python Version Support Lifecycle: 3.11–3.15 Supported, 3.16 Preview](https://github.com/bdperkin/findfmt/issues/442)
  | Milestone: v1.1.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Completes the 3.15
  maximum-version rollout. Blocked by [#335](https://github.com/bdperkin/findfmt/issues/335).
- [ ] **[#441](https://github.com/bdperkin/findfmt/issues/441)** - build: raise minimum supported
  Python version to 3.11 and remove Python 3.10 compatibility code *(Rank: 42 | Epic:
  [[Epic] Python Version Support Lifecycle: 3.11–3.15 Supported, 3.16 Preview](https://github.com/bdperkin/findfmt/issues/442)
  | Milestone: v1.1.0)* - **Value:** Medium | **Effort:** M - **Rationale:** 3.10 is EOL; removes
  compat code.
- [ ] **[#453](https://github.com/bdperkin/findfmt/issues/453)** - refactor(cli): move CLI-only
  modules (diagnostics, entrypoints, summary, terminal) under findfmt.cli with compatibility shims
  *(Rank: 43 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Parent: [#324](https://github.com/bdperkin/findfmt/issues/324) | Milestone: v1.1.0)* -
  **Value:** Medium | **Effort:** M - **Rationale:** Completes the core/CLI split; medium effort and
  risk.
- [ ] **[#310](https://github.com/bdperkin/findfmt/issues/310)** - feat(config): provide sample
  config.toml, annotated reference configuration, and --generate-config CLI option *(Rank: 44 |
  Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Milestone: v1.2.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Depends on the
  layered-config work. Blocked by [#455](https://github.com/bdperkin/findfmt/issues/455).
- [ ] **[#455](https://github.com/bdperkin/findfmt/issues/455)** - feat(config): merge user and
  project config layers and discover pyproject.toml up to the VCS root *(Rank: 45 | Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Parent: [#332](https://github.com/bdperkin/findfmt/issues/332) | Milestone: v1.2.0)* -
  **Value:** Medium | **Effort:** M - **Rationale:** Core of the layered-config feature.
- [ ] **[#292](https://github.com/bdperkin/findfmt/issues/292)** - refactor(types): resolve Ty
  truthiness-test-of-none-union diagnostics to upgrade past v0.0.84 *(Rank: 46 | Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.1)* - **Value:** Medium | **Effort:** M - **Rationale:** Unblocks Ty upgrades;
  mechanical but spread over 23 files.
- [ ] **[#216](https://github.com/bdperkin/findfmt/issues/216)** - feat(i18n): add language support
  for Chinese - China / Mandarin (zh_CN) (~1.14 billion) *(Rank: 47 | Epic:
  [[Epic] Add Language Support: Sino-Tibetan (~1.42 Billion)](https://github.com/bdperkin/findfmt/issues/198)
  | Milestone: v1.4.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Chinese - China / Mandarin (`zh_CN`, ~1.14 billion); extends reach of the CLI to a
  large speaker base.
- [ ] **[#217](https://github.com/bdperkin/findfmt/issues/217)** - feat(i18n): add language support
  for Hindi (hi) (~610 million) *(Rank: 48 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: v1.4.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Hindi (`hi`, ~610 million); extends reach of the CLI to a large speaker base.
- [ ] **[#218](https://github.com/bdperkin/findfmt/issues/218)** - feat(i18n): add language support
  for Bengali (bn) (~273 million) *(Rank: 49 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: v1.4.1)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Bengali (`bn`, ~273 million); extends reach of the CLI to a large speaker base.
- [ ] **[#219](https://github.com/bdperkin/findfmt/issues/219)** - feat(i18n): add language support
  for Urdu (ur) (~232 million) *(Rank: 50 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: v1.4.1)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Urdu (`ur`, ~232 million); extends reach of the CLI to a large speaker base. Blocked
  by [#449](https://github.com/bdperkin/findfmt/issues/449).
- [ ] **[#223](https://github.com/bdperkin/findfmt/issues/223)** - feat(i18n): add language support
  for Portuguese (pt) (~264 million) *(Rank: 51 | Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: v1.4.1)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Portuguese (`pt`, ~264 million); extends reach of the CLI to a large speaker base.
- [ ] **[#449](https://github.com/bdperkin/findfmt/issues/449)** - fix(format): correct Rich table
  and tree width and alignment for mixed RTL/LTR cell content *(Rank: 52 | Epic:
  [[Epic] i18n Platform Infrastructure: RTL/BiDi Rendering & Multilingual Documentation Builds](https://github.com/bdperkin/findfmt/issues/276)
  | Parent: [#229](https://github.com/bdperkin/findfmt/issues/229) | Milestone: v1.4.1)* -
  **Value:** Medium | **Effort:** M - **Rationale:** Required before RTL catalogs (ur, ar) ship.
  Blocked by [#448](https://github.com/bdperkin/findfmt/issues/448).
- [ ] **[#225](https://github.com/bdperkin/findfmt/issues/225)** - feat(i18n): add language support
  for Arabic (ar) (~370 million) *(Rank: 53 | Epic:
  [[Epic] Add Language Support: Afroasiatic (~480 Million)](https://github.com/bdperkin/findfmt/issues/201)
  | Milestone: v1.4.2)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Arabic (`ar`, ~370 million); extends reach of the CLI to a large speaker base. Blocked
  by [#449](https://github.com/bdperkin/findfmt/issues/449).
- [ ] **[#226](https://github.com/bdperkin/findfmt/issues/226)** - feat(i18n): add language support
  for Russian (ru) (~255 million) *(Rank: 54 | Epic:
  [[Epic] Add Language Support: Slavic (~415 Million)](https://github.com/bdperkin/findfmt/issues/202)
  | Milestone: v1.4.2)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Russian (`ru`, ~255 million); extends reach of the CLI to a large speaker base.
- [ ] **[#227](https://github.com/bdperkin/findfmt/issues/227)** - feat(i18n): add language support
  for Indonesian (id) (~199 million) *(Rank: 55 | Epic:
  [[Epic] Add Language Support: Austronesian (~295 Million)](https://github.com/bdperkin/findfmt/issues/203)
  | Milestone: v1.4.2)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Indonesian (`id`, ~199 million); extends reach of the CLI to a large speaker base.
- [ ] **[#220](https://github.com/bdperkin/findfmt/issues/220)** - feat(i18n): add language support
  for Punjabi (pa) (~125 million) *(Rank: 56 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: v1.5.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Punjabi (`pa`, ~125 million); extends reach of the CLI to a large speaker base.
- [ ] **[#224](https://github.com/bdperkin/findfmt/issues/224)** - feat(i18n): add language support
  for Portuguese - Brazil (pt_BR) (~208 million (subset of total Portuguese)) *(Rank: 57 | Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: v1.5.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Portuguese - Brazil (`pt_BR`, ~208 million (subset of total Portuguese); extends reach
  of the CLI to a large speaker base.
- [ ] **[#246](https://github.com/bdperkin/findfmt/issues/246)** - feat(i18n): add language support
  for Italian (it) (~68 million) *(Rank: 58 | Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: v1.5.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Italian (`it`, ~68 million); extends reach of the CLI to a large speaker base.
- [ ] **[#258](https://github.com/bdperkin/findfmt/issues/258)** - feat(i18n): add language support
  for Korean (ko) (~82 million) *(Rank: 59 | Epic:
  [[Epic] Add Language Support: Japonic & Koreanic (~205 Million)](https://github.com/bdperkin/findfmt/issues/205)
  | Milestone: v1.5.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Korean (`ko`, ~82 million); extends reach of the CLI to a large speaker base.
- [ ] **[#261](https://github.com/bdperkin/findfmt/issues/261)** - feat(i18n): add language support
  for Turkish (tr) (~90 million) *(Rank: 60 | Epic:
  [[Epic] Add Language Support: Turkic (~165 Million)](https://github.com/bdperkin/findfmt/issues/207)
  | Milestone: v1.5.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Turkish (`tr`, ~90 million); extends reach of the CLI to a large speaker base.
- [ ] **[#267](https://github.com/bdperkin/findfmt/issues/267)** - feat(i18n): add language support
  for Vietnamese (vi) (~86 million) *(Rank: 61 | Epic:
  [[Epic] Add Language Support: All Other (~200 Million)](https://github.com/bdperkin/findfmt/issues/211)
  | Milestone: v1.5.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Scheduled localization
  catalog for Vietnamese (`vi`, ~86 million); extends reach of the CLI to a large speaker base.
- [ ] **[#296](https://github.com/bdperkin/findfmt/issues/296)** - feat(packaging): investigate
  Briefcase configuration and feasibility for findfmt console application *(Rank: 62 | Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Prerequisite
  feasibility study for the Briefcase chain.
- [ ] **[#300](https://github.com/bdperkin/findfmt/issues/300)** - docs(packaging): document
  standalone binary installation options and Briefcase evaluation trade-offs *(Rank: 63 | Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)* - **Value:** Medium | **Effort:** M - **Rationale:** Decision gate for the
  whole Briefcase chain.
- [ ] **[#321](https://github.com/bdperkin/findfmt/issues/321)** - fix(traversal): symlinks are
  omitted by default and misclassified/mis-pathed with -l *(Rank: 64 | Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.3)* - **Value:** High | **Effort:** L - **Rationale:** Symlink handling produces
  wrong paths and duplicate entries.
- [ ] **[#355](https://github.com/bdperkin/findfmt/issues/355)** - [Core] Fix symlink parser
  handling of filenames containing arrow ('->') delimiters *(Rank: 65 | Epic:
  [[Epic] Core Refactoring & API Hygiene Cleanup](https://github.com/bdperkin/findfmt/issues/348) |
  Milestone: v1.0.3)* - **Value:** Low | **Effort:** S - **Rationale:** Edge-case parser fix.
- [ ] **[#343](https://github.com/bdperkin/findfmt/issues/343)** - fix(format): --cp437 writes
  Latin-1 code points, which show as mojibake *(Rank: 66 | Epic:
  [[Epic] Formatter Integrity: Encoding Robustness, Stream Sanitization & Format Parity](https://github.com/bdperkin/findfmt/issues/384)
  | Milestone: v1.0.4)* - **Value:** Low | **Effort:** S - **Rationale:** Small encoding fix.
- [ ] **[#305](https://github.com/bdperkin/findfmt/issues/305)** - feat(i18n): formulate domain
  context prompt engineering and ngettext pluralization rules for AI translation *(Rank: 67 | Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.5)* - **Value:** Low | **Effort:** S - **Rationale:** Small; only one plural
  msgid today. Blocked by [#304](https://github.com/bdperkin/findfmt/issues/304),
  [#303](https://github.com/bdperkin/findfmt/issues/303).
- [ ] **[#353](https://github.com/bdperkin/findfmt/issues/353)** - [Tests] Tighten coverage pragmas
  and eliminate reachable/dead code pragmas *(Rank: 68 | Epic:
  [[Epic] Core Refactoring & API Hygiene Cleanup](https://github.com/bdperkin/findfmt/issues/348) |
  Milestone: v1.0.5)* - **Value:** Low | **Effort:** S - **Rationale:** Small coverage hygiene.
- [ ] **[#359](https://github.com/bdperkin/findfmt/issues/359)** - [Tests] Complete pyproject.toml
  test dependency group and isolate catalog compilation fixture *(Rank: 69 | Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.5)* - **Value:** Low | **Effort:** S - **Rationale:** Small test-isolation fix.
- [ ] **[#358](https://github.com/bdperkin/findfmt/issues/358)** - [Packaging] Expand packaging
  smoke matrix to build and verify sdist installations *(Rank: 70 | Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.6)* - **Value:** Low | **Effort:** S - **Rationale:** Small CI addition.
- [ ] **[#360](https://github.com/bdperkin/findfmt/issues/360)** - [CI] Align tool versions across
  pre-commit and uv.lock, and schedule docs linkcheck *(Rank: 71 | Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.6)* - **Value:** Low | **Effort:** S - **Rationale:** Prevents tool-version
  drift.
- [ ] **[#430](https://github.com/bdperkin/findfmt/issues/430)** - docs(deps): document dependency
  matrix testing and bound troubleshooting in contributing guide *(Rank: 72 | Epic:
  [[Epic] Exhaustive Dependency Resolution Matrix Testing via uv in CI and Tooling](https://github.com/bdperkin/findfmt/issues/425)
  | Milestone: v1.0.7)* - **Value:** Low | **Effort:** S - **Rationale:** Docs for the matrix
  tooling. Blocked by [#429](https://github.com/bdperkin/findfmt/issues/429),
  [#427](https://github.com/bdperkin/findfmt/issues/427).
- [ ] **[#469](https://github.com/bdperkin/findfmt/issues/469)** - docs(i18n): regenerate locale
  catalogs after symlink flag corrections in #467 *(Rank: 73 | Epic:
  [[Epic] i18n Platform Infrastructure: RTL/BiDi Rendering & Multilingual Documentation Builds](https://github.com/bdperkin/findfmt/issues/276)
  | Milestone: v1.0.8)* - **Value:** Low | **Effort:** S - **Rationale:** Catalogs still carry the
  old `-L`/`--dereference` msgids from before [#467](https://github.com/bdperkin/findfmt/pull/467).
  No reader impact (empty `msgstr`), but refresh before the
  [#222](https://github.com/bdperkin/findfmt/issues/222)/[#228](https://github.com/bdperkin/findfmt/issues/228)
  translation work.
- [ ] **[#351](https://github.com/bdperkin/findfmt/issues/351)** - [Core] Remove test-only traversal
  aliases and unused \_load_active_specs; review findfmt.traversal public \_\_all\_\_ *(Rank: 74 |
  Epic:
  [[Epic] Core Refactoring & API Hygiene Cleanup](https://github.com/bdperkin/findfmt/issues/348) |
  Milestone: v1.1.1)* - **Value:** Low | **Effort:** S - **Rationale:** Small API hygiene cleanup.
- [ ] **[#366](https://github.com/bdperkin/findfmt/issues/366)** - [CLI] Validate numeric CLI
  parameters (min=0) and clarify misleading option help descriptions *(Rank: 75 | Epic:
  [[Epic] CLI Documentation Accuracy, Dynamic --help-all Generation, and Option Validation](https://github.com/bdperkin/findfmt/issues/346)
  | Milestone: v1.1.1)* - **Value:** Low | **Effort:** S - **Rationale:** Small validation fix.
- [ ] **[#458](https://github.com/bdperkin/findfmt/issues/458)** - feat(config): show value
  provenance (default/config/env/CLI) in --show-config *(Rank: 76 | Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Parent: [#332](https://github.com/bdperkin/findfmt/issues/332) | Milestone: v1.2.0)* -
  **Value:** Low | **Effort:** S - **Rationale:** Debuggability nicety once layering exists.
- [ ] **[#302](https://github.com/bdperkin/findfmt/issues/302)** - feat(docs): replace top-left
  Sphinx sidebar logo with high-resolution square icon *(Rank: 77 | Epic:
  [[Epic] Documentation Architecture, Sphinx Navigation & Project Branding](https://github.com/bdperkin/findfmt/issues/379)
  | Milestone: v1.2.1)* - **Value:** Low | **Effort:** S - **Rationale:** Tiny docs polish; good
  first issue.
- [ ] **[#311](https://github.com/bdperkin/findfmt/issues/311)** - refactor(config): investigate
  consolidating standalone repository configuration files into pyproject.toml *(Rank: 78 | Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Milestone: v1.2.1)* - **Value:** Low | **Effort:** S - **Rationale:** Low ROI; mostly not
  feasible.
- [ ] **[#312](https://github.com/bdperkin/findfmt/issues/312)** - docs(readme): audit and expand
  high-value status, security, and metadata badges in README and documentation header *(Rank: 79 |
  Epic:
  [[Epic] Documentation Architecture, Sphinx Navigation & Project Branding](https://github.com/bdperkin/findfmt/issues/379)
  | Milestone: v1.2.1)* - **Value:** Low | **Effort:** S - **Rationale:** Small docs task; badge
  list already mostly done.
- [ ] **[#313](https://github.com/bdperkin/findfmt/issues/313)** - chore(pre-commit): configure
  yamlfix formatting rules in pyproject.toml *(Rank: 80 | Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.1)* - **Value:** Low | **Effort:** S - **Rationale:** Small config task;
  prerequisite for [#314](https://github.com/bdperkin/findfmt/issues/314).
- [ ] **[#471](https://github.com/bdperkin/findfmt/issues/471)** - ci(pre-commit): enable
  check-hooks-apply and manual-stage identity meta hooks *(Rank: 81 | Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.2)* - **Value:** Low | **Effort:** S - **Rationale:** `check-hooks-apply`
  currently fails on `check-symlinks` (no tracked symlinks); remove that hook in the same PR.
- [ ] **[#474](https://github.com/bdperkin/findfmt/issues/474)** - ci(pre-commit): add gitlint
  commit-msg hook for title/body length and message structure *(Rank: 82 | Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.2)* - **Value:** Low | **Effort:** S - **Rationale:** Tuned config flags 21/100
  recent commits (91 with defaults). Enforcement is local only and upstream is barely maintained.
  Title limit follows [#314](https://github.com/bdperkin/findfmt/issues/314).
- [ ] **[#476](https://github.com/bdperkin/findfmt/issues/476)** - docs(pre-commit): add
  --show-diff-on-failure to every pre-commit run --all-files invocation *(Rank: 83 | Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.2)* - **Value:** Low | **Effort:** S - **Rationale:** Docs-only change to four
  `pre-commit run --all-files` invocations; good first issue.
- [ ] **[#445](https://github.com/bdperkin/findfmt/issues/445)** - feat(cli): add --ignore-file /
  --ignore-type options and matching config keys *(Rank: 84 | Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Parent: [#111](https://github.com/bdperkin/findfmt/issues/111) | Milestone: v1.3.1)* -
  **Value:** Low | **Effort:** S - **Rationale:** Small wiring task once the abstraction exists.
  Blocked by [#444](https://github.com/bdperkin/findfmt/issues/444).
- [ ] **[#447](https://github.com/bdperkin/findfmt/issues/447)** - feat(traversal): add
  gitignore-dialect presets for .eslintignore, .prettierignore, .npmignore, and .stylelintignore
  *(Rank: 85 | Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Parent: [#111](https://github.com/bdperkin/findfmt/issues/111) | Milestone: v1.3.1)* -
  **Value:** Low | **Effort:** S - **Rationale:** Cheap once the abstraction exists; reuses the
  gitignore dialect. Blocked by [#444](https://github.com/bdperkin/findfmt/issues/444).
- [ ] **[#374](https://github.com/bdperkin/findfmt/issues/374)** - [CLI] v2.0: Reserve -h short flag
  exclusively for --help and deprecate for --human-readable *(Rank: 86 | Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)* - **Value:** Low | **Effort:** S - **Rationale:** v2.0 prep.
- [ ] **[#375](https://github.com/bdperkin/findfmt/issues/375)** - [CLI] v2.0: Rename
  double-negative --nolinks/--no-nolinks to positive --links/--no-links flag *(Rank: 87 | Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)* - **Value:** Low | **Effort:** S - **Rationale:** v2.0 prep.
- [ ] **[#376](https://github.com/bdperkin/findfmt/issues/376)** - [CLI] v2.0: Disambiguate -v and
  -V CLI flags with distinct semantics *(Rank: 88 | Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)* - **Value:** Low | **Effort:** S - **Rationale:** v2.0 prep.
- [ ] **[#377](https://github.com/bdperkin/findfmt/issues/377)** - [Core] v2.0: Remove deprecated
  top-level main\_\* entry points and _ helper exports from findfmt package root *(Rank: 89 | Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)* - **Value:** Low | **Effort:** S - **Rationale:** v2.0 removal of shims
  introduced by [#324](https://github.com/bdperkin/findfmt/issues/324). Blocked by
  [#452](https://github.com/bdperkin/findfmt/issues/452).
- [ ] **[#331](https://github.com/bdperkin/findfmt/issues/331)** - perf(cli): TTY output is fully
  buffered for the pager, so nothing streams *(Rank: 90 | Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.1)* - **Value:** Medium | **Effort:** L - **Rationale:** Streaming UX
  improvement; sizeable refactor.

### 2.3. Future / Low-Priority / Backlog

- [ ] **[#345](https://github.com/bdperkin/findfmt/issues/345)** - test(perf): replace wall-clock
  assertions with deterministic counters and re-baseline memory *(Rank: 91 | Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.5)* - **Value:** Low | **Effort:** M - **Rationale:** Removes flaky timing
  tests; enables [#337](https://github.com/bdperkin/findfmt/issues/337).
- [ ] **[#307](https://github.com/bdperkin/findfmt/issues/307)** - feat(i18n): evaluate managed
  localization platforms with native AI (POEditor, Crowdin, Localazy) vs local CI automation *(Rank:
  92 | Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.7)* - **Value:** Low | **Effort:** M - **Rationale:** Platform evaluation;
  informs [#306](https://github.com/bdperkin/findfmt/issues/306).
- [ ] **[#349](https://github.com/bdperkin/findfmt/issues/349)** - chore: add a multi-Python local
  runner (evaluate nox, tox, Hatch, uv) *(Rank: 93 | Epic:
  [[Epic] Packaging Integrity, Release Automation & Dependency Verification](https://github.com/bdperkin/findfmt/issues/385)
  | Milestone: v1.0.7)* - **Value:** Low | **Effort:** M - **Rationale:** Evaluation should follow
  the [#426](https://github.com/bdperkin/findfmt/issues/426) ADR. Blocked by
  [#426](https://github.com/bdperkin/findfmt/issues/426).
- [ ] **[#233](https://github.com/bdperkin/findfmt/issues/233)** - ci(docs): configure automated
  multilingual Sphinx documentation builds in CI pipeline *(Rank: 94 | Epic:
  [[Epic] i18n Platform Infrastructure: RTL/BiDi Rendering & Multilingual Documentation Builds](https://github.com/bdperkin/findfmt/issues/276)
  | Milestone: v1.0.8)* - **Value:** Low | **Effort:** M - **Rationale:** Infrastructure mostly
  exists; remaining CI wiring and switcher.
- [ ] **[#342](https://github.com/bdperkin/findfmt/issues/342)** - refactor(cli): pass click.Context
  explicitly instead of walking stack frames; validate TraversalConfig *(Rank: 95 | Epic:
  [[Epic] Core Refactoring & API Hygiene Cleanup](https://github.com/bdperkin/findfmt/issues/348) |
  Milestone: v1.1.1)* - **Value:** Low | **Effort:** M - **Rationale:** Internal cleanup; reduces
  fragility.
- [ ] **[#365](https://github.com/bdperkin/findfmt/issues/365)** - [CLI] Dynamically generate
  --help-all output directly from Click command introspection *(Rank: 96 | Epic:
  [[Epic] CLI Documentation Accuracy, Dynamic --help-all Generation, and Option Validation](https://github.com/bdperkin/findfmt/issues/346)
  | Milestone: v1.1.1)* - **Value:** Low | **Effort:** M - **Rationale:** Prevents help drift.
- [ ] **[#340](https://github.com/bdperkin/findfmt/issues/340)** - feat(cli): improve config
  validation diagnostics (all errors, did-you-mean, reprs, alias collisions) *(Rank: 97 | Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Milestone: v1.2.0)* - **Value:** Low | **Effort:** M - **Rationale:** Diagnostics polish after
  layering. Blocked by [#455](https://github.com/bdperkin/findfmt/issues/455).
- [ ] **[#309](https://github.com/bdperkin/findfmt/issues/309)** - feat(docs): investigate
  expandable hierarchical heading navigation in Sphinx left sidebar *(Rank: 98 | Epic:
  [[Epic] Documentation Architecture, Sphinx Navigation & Project Branding](https://github.com/bdperkin/findfmt/issues/379)
  | Milestone: v1.2.1)* - **Value:** Low | **Effort:** M - **Rationale:** Needs a Furo template
  override; modest value.
- [ ] **[#314](https://github.com/bdperkin/findfmt/issues/314)** - refactor(lint): standardize line
  length limit to 110 columns across all linters, checkers, and formatters *(Rank: 99 | Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.1)* - **Value:** Low | **Effort:** M - **Rationale:** Large reformat diff for
  consistency only. Blocked by [#313](https://github.com/bdperkin/findfmt/issues/313).
- [ ] **[#112](https://github.com/bdperkin/findfmt/issues/112)** - feat(classifier): support
  optional mimetypes backend for fast extension-based classification *(Rank: 100 | Epic:
  [[Epic] Pluggable Content Classification Engines & MIME Inspection Backends](https://github.com/bdperkin/findfmt/issues/382)
  | Milestone: v1.3.0)* - **Value:** Low | **Effort:** M - **Rationale:** Defines the backend
  interface that
  [#113](https://github.com/bdperkin/findfmt/issues/113)/[#114](https://github.com/bdperkin/findfmt/issues/114)
  reuse.
- [ ] **[#113](https://github.com/bdperkin/findfmt/issues/113)** - feat(classifier): support
  optional filetype backend for fast magic number signature inspection *(Rank: 101 | Epic:
  [[Epic] Pluggable Content Classification Engines & MIME Inspection Backends](https://github.com/bdperkin/findfmt/issues/382)
  | Milestone: v1.3.0)* - **Value:** Low | **Effort:** M - **Rationale:** Optional backend; depends
  on [#112](https://github.com/bdperkin/findfmt/issues/112). Blocked by
  [#112](https://github.com/bdperkin/findfmt/issues/112).
- [ ] **[#114](https://github.com/bdperkin/findfmt/issues/114)** - feat(classifier): support
  optional puremagic backend for deep magic signature analysis *(Rank: 102 | Epic:
  [[Epic] Pluggable Content Classification Engines & MIME Inspection Backends](https://github.com/bdperkin/findfmt/issues/382)
  | Milestone: v1.3.0)* - **Value:** Low | **Effort:** M - **Rationale:** Optional backend; depends
  on [#112](https://github.com/bdperkin/findfmt/issues/112). Blocked by
  [#112](https://github.com/bdperkin/findfmt/issues/112).
- [ ] **[#444](https://github.com/bdperkin/findfmt/issues/444)** - refactor(traversal): introduce a
  pluggable IgnoreSource abstraction for non-gitignore ignore files *(Rank: 103 | Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Parent: [#111](https://github.com/bdperkin/findfmt/issues/111) | Milestone: v1.3.1)* -
  **Value:** Low | **Effort:** M - **Rationale:** Enabler for every extra ignore format; no
  user-visible change on its own.
- [ ] **[#446](https://github.com/bdperkin/findfmt/issues/446)** - feat(traversal): support
  .dockerignore semantics (root-only, Go filepath.Match patterns) *(Rank: 104 | Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Parent: [#111](https://github.com/bdperkin/findfmt/issues/111) | Milestone: v1.3.1)* -
  **Value:** Low | **Effort:** M - **Rationale:** Most-requested extra ignore format; distinct
  semantics need care. Blocked by [#444](https://github.com/bdperkin/findfmt/issues/444).
- [ ] **[#299](https://github.com/bdperkin/findfmt/issues/299)** - feat(web): evaluate Web /
  PyScript client-side distribution for interactive browser demonstration *(Rank: 105 | Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)* - **Value:** Low | **Effort:** M - **Rationale:** Time-boxed evaluation; low
  ROI. Blocked by [#296](https://github.com/bdperkin/findfmt/issues/296).
- [ ] **[#234](https://github.com/bdperkin/findfmt/issues/234)** - feat(i18n): add language support
  for English - United Kingdom (en_GB) (~60 million) *(Rank: 106 | Epic:
  [[Epic] Add Language Support: Germanic (~1.83 Billion)](https://github.com/bdperkin/findfmt/issues/197)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for English - United Kingdom (`en_GB`, ~60 million); schedule once Tier 1-3
  catalogs and AI tooling land.
- [ ] **[#235](https://github.com/bdperkin/findfmt/issues/235)** - feat(i18n): add language support
  for Dutch (nl) (~24 million) *(Rank: 107 | Epic:
  [[Epic] Add Language Support: Germanic (~1.83 Billion)](https://github.com/bdperkin/findfmt/issues/197)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Dutch (`nl`, ~24 million); schedule once Tier 1-3 catalogs and AI tooling
  land.
- [ ] **[#236](https://github.com/bdperkin/findfmt/issues/236)** - feat(i18n): add language support
  for Swedish (sv) (~10 million) *(Rank: 108 | Epic:
  [[Epic] Add Language Support: Germanic (~1.83 Billion)](https://github.com/bdperkin/findfmt/issues/197)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Swedish (`sv`, ~10 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#237](https://github.com/bdperkin/findfmt/issues/237)** - feat(i18n): add language support
  for Burmese (my) (~33 million) *(Rank: 109 | Epic:
  [[Epic] Add Language Support: Sino-Tibetan (~1.42 Billion)](https://github.com/bdperkin/findfmt/issues/198)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Burmese (`my`, ~33 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#238](https://github.com/bdperkin/findfmt/issues/238)** - feat(i18n): add language support
  for Chinese - Taiwan / Mandarin (zh_TW) (~23 million) *(Rank: 110 | Epic:
  [[Epic] Add Language Support: Sino-Tibetan (~1.42 Billion)](https://github.com/bdperkin/findfmt/issues/198)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Chinese - Taiwan / Mandarin (`zh_TW`, ~23 million); schedule once Tier
  1-3 catalogs and AI tooling land.
- [ ] **[#239](https://github.com/bdperkin/findfmt/issues/239)** - feat(i18n): add language support
  for Marathi (mr) (~99 million) *(Rank: 111 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Marathi (`mr`, ~99 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#240](https://github.com/bdperkin/findfmt/issues/240)** - feat(i18n): add language support
  for Gujarati (gu) (~62 million) *(Rank: 112 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Gujarati (`gu`, ~62 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#241](https://github.com/bdperkin/findfmt/issues/241)** - feat(i18n): add language support
  for Odia (or) (~35 million) *(Rank: 113 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Odia (`or`, ~35 million); schedule once Tier 1-3 catalogs and AI tooling
  land.
- [ ] **[#242](https://github.com/bdperkin/findfmt/issues/242)** - feat(i18n): add language support
  for Maithili (mai) (~34 million) *(Rank: 114 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Maithili (`mai`, ~34 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#243](https://github.com/bdperkin/findfmt/issues/243)** - feat(i18n): add language support
  for Assamese (as) (~15 million) *(Rank: 115 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Assamese (`as`, ~15 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#244](https://github.com/bdperkin/findfmt/issues/244)** - feat(i18n): add language support
  for Sinhala (si) (~17 million) *(Rank: 116 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Sinhala (`si`, ~17 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#245](https://github.com/bdperkin/findfmt/issues/245)** - feat(i18n): add language support
  for Nepali (ne) (~16 million) *(Rank: 117 | Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Nepali (`ne`, ~16 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#247](https://github.com/bdperkin/findfmt/issues/247)** - feat(i18n): add language support
  for Romanian (ro) (~24 million) *(Rank: 118 | Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Romanian (`ro`, ~24 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#248](https://github.com/bdperkin/findfmt/issues/248)** - feat(i18n): add language support
  for Catalan (ca) (~10 million) *(Rank: 119 | Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Catalan (`ca`, ~10 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#249](https://github.com/bdperkin/findfmt/issues/249)** - feat(i18n): add language support
  for Amharic (am) (~58 million) *(Rank: 120 | Epic:
  [[Epic] Add Language Support: Afroasiatic (~480 Million)](https://github.com/bdperkin/findfmt/issues/201)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Amharic (`am`, ~58 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#250](https://github.com/bdperkin/findfmt/issues/250)** - feat(i18n): add language support
  for Polish (pl) (~40 million) *(Rank: 121 | Epic:
  [[Epic] Add Language Support: Slavic (~415 Million)](https://github.com/bdperkin/findfmt/issues/202)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Polish (`pl`, ~40 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#251](https://github.com/bdperkin/findfmt/issues/251)** - feat(i18n): add language support
  for Ukrainian (uk) (~40 million) *(Rank: 122 | Epic:
  [[Epic] Add Language Support: Slavic (~415 Million)](https://github.com/bdperkin/findfmt/issues/202)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Ukrainian (`uk`, ~40 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#252](https://github.com/bdperkin/findfmt/issues/252)** - feat(i18n): add language support
  for Czech (cs) (~10.7 million) *(Rank: 123 | Epic:
  [[Epic] Add Language Support: Slavic (~415 Million)](https://github.com/bdperkin/findfmt/issues/202)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Czech (`cs`, ~10.7 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#253](https://github.com/bdperkin/findfmt/issues/253)** - feat(i18n): add language support
  for Malay (ms) (~30 million) *(Rank: 124 | Epic:
  [[Epic] Add Language Support: Austronesian (~295 Million)](https://github.com/bdperkin/findfmt/issues/203)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Malay (`ms`, ~30 million); schedule once Tier 1-3 catalogs and AI tooling
  land.
- [ ] **[#254](https://github.com/bdperkin/findfmt/issues/254)** - feat(i18n): add language support
  for Telugu (te) (~96 million) *(Rank: 125 | Epic:
  [[Epic] Add Language Support: Dravidian (~270 Million)](https://github.com/bdperkin/findfmt/issues/204)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Telugu (`te`, ~96 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#255](https://github.com/bdperkin/findfmt/issues/255)** - feat(i18n): add language support
  for Tamil (ta) (~87 million) *(Rank: 126 | Epic:
  [[Epic] Add Language Support: Dravidian (~270 Million)](https://github.com/bdperkin/findfmt/issues/204)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Tamil (`ta`, ~87 million); schedule once Tier 1-3 catalogs and AI tooling
  land.
- [ ] **[#256](https://github.com/bdperkin/findfmt/issues/256)** - feat(i18n): add language support
  for Kannada (kn) (~59 million) *(Rank: 127 | Epic:
  [[Epic] Add Language Support: Dravidian (~270 Million)](https://github.com/bdperkin/findfmt/issues/204)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Kannada (`kn`, ~59 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#257](https://github.com/bdperkin/findfmt/issues/257)** - feat(i18n): add language support
  for Malayalam (ml) (~38 million) *(Rank: 128 | Epic:
  [[Epic] Add Language Support: Dravidian (~270 Million)](https://github.com/bdperkin/findfmt/issues/204)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Malayalam (`ml`, ~38 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#259](https://github.com/bdperkin/findfmt/issues/259)** - feat(i18n): add language support
  for N'Ko / Manding (nqo) (~40 million) *(Rank: 129 | Epic:
  [[Epic] Add Language Support: Niger–Congo (~210 Million)](https://github.com/bdperkin/findfmt/issues/206)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for N'Ko / Manding (`nqo`, ~40 million); schedule once Tier 1-3 catalogs and
  AI tooling land.
- [ ] **[#260](https://github.com/bdperkin/findfmt/issues/260)** - feat(i18n): add language support
  for Zulu (zu) (~14 million) *(Rank: 130 | Epic:
  [[Epic] Add Language Support: Niger–Congo (~210 Million)](https://github.com/bdperkin/findfmt/issues/206)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Zulu (`zu`, ~14 million); schedule once Tier 1-3 catalogs and AI tooling
  land.
- [ ] **[#262](https://github.com/bdperkin/findfmt/issues/262)** - feat(i18n): add language support
  for Kazakh (kk) (~15 million) *(Rank: 131 | Epic:
  [[Epic] Add Language Support: Turkic (~165 Million)](https://github.com/bdperkin/findfmt/issues/207)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Kazakh (`kk`, ~15 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#263](https://github.com/bdperkin/findfmt/issues/263)** - feat(i18n): add language support
  for Persian (fa) (~79 million) *(Rank: 132 | Epic:
  [[Epic] Add Language Support: Other Indo-European (~124 Million)](https://github.com/bdperkin/findfmt/issues/208)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Persian (`fa`, ~79 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#264](https://github.com/bdperkin/findfmt/issues/264)** - feat(i18n): add language support
  for Kurdish (ku) (~30 million) *(Rank: 133 | Epic:
  [[Epic] Add Language Support: Other Indo-European (~124 Million)](https://github.com/bdperkin/findfmt/issues/208)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Kurdish (`ku`, ~30 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#265](https://github.com/bdperkin/findfmt/issues/265)** - feat(i18n): add language support
  for Hungarian (hu) (~13 million) *(Rank: 134 | Epic:
  [[Epic] Add Language Support: Uralic (~18 Million)](https://github.com/bdperkin/findfmt/issues/209)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Hungarian (`hu`, ~13 million); schedule once Tier 1-3 catalogs and AI
  tooling land.
- [ ] **[#266](https://github.com/bdperkin/findfmt/issues/266)** - feat(i18n): add language support
  for Greek (el) (~13 million) *(Rank: 135 | Epic:
  [[Epic] Add Language Support: Hellenic (~13 Million)](https://github.com/bdperkin/findfmt/issues/210)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Greek (`el`, ~13 million); schedule once Tier 1-3 catalogs and AI tooling
  land.
- [ ] **[#268](https://github.com/bdperkin/findfmt/issues/268)** - feat(i18n): add language support
  for Thai (th) (~61 million) *(Rank: 136 | Epic:
  [[Epic] Add Language Support: All Other (~200 Million)](https://github.com/bdperkin/findfmt/issues/211)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Thai (`th`, ~61 million); schedule once Tier 1-3 catalogs and AI tooling
  land.
- [ ] **[#269](https://github.com/bdperkin/findfmt/issues/269)** - feat(i18n): add language support
  for Lao (lo) (~30 million) *(Rank: 137 | Epic:
  [[Epic] Add Language Support: All Other (~200 Million)](https://github.com/bdperkin/findfmt/issues/211)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Lao (`lo`, ~30 million); schedule once Tier 1-3 catalogs and AI tooling
  land.
- [ ] **[#270](https://github.com/bdperkin/findfmt/issues/270)** - feat(i18n): add language support
  for Khmer (km) (~16 million) *(Rank: 138 | Epic:
  [[Epic] Add Language Support: All Other (~200 Million)](https://github.com/bdperkin/findfmt/issues/211)
  | Milestone: Future Features)* - **Value:** Low | **Effort:** M - **Rationale:** Backlog
  localization catalog for Khmer (`km`, ~16 million); schedule once Tier 1-3 catalogs and AI tooling
  land.
- [ ] **[#297](https://github.com/bdperkin/findfmt/issues/297)** - feat(packaging): evaluate
  Briefcase desktop & system packaging formats (macOS, Windows, Linux) *(Rank: 139 | Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)* - **Value:** Low | **Effort:** L - **Rationale:** Gated on the
  [#300](https://github.com/bdperkin/findfmt/issues/300) adopt/skip decision. Blocked by
  [#300](https://github.com/bdperkin/findfmt/issues/300),
  [#296](https://github.com/bdperkin/findfmt/issues/296).
- [ ] **[#298](https://github.com/bdperkin/findfmt/issues/298)** - ci(packaging): design and
  prototype automated Briefcase multi-platform CI build pipeline with GitHub Actions *(Rank: 140 |
  Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)* - **Value:** Low | **Effort:** L - **Rationale:** CI pipeline only worth
  building after an adopt decision. Blocked by
  [#300](https://github.com/bdperkin/findfmt/issues/300),
  [#297](https://github.com/bdperkin/findfmt/issues/297),
  [#296](https://github.com/bdperkin/findfmt/issues/296).
- [ ] **[#378](https://github.com/bdperkin/findfmt/issues/378)** - [CLI] v2.0: Replace
  argv-rewriting console script wrappers with dedicated Click command entry points *(Rank: 141 |
  Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)* - **Value:** Low | **Effort:** L - **Rationale:** v2.0 redesign of wrapper
  entry points. Blocked by [#319](https://github.com/bdperkin/findfmt/issues/319).

______________________________________________________________________

## 3. Decomposed Tracking Issues

Note: Oversized issues split into sub-issues during the 2026-10-21 audit; each closes when all of
its sub-issues close.

- [ ] **[#111](https://github.com/bdperkin/findfmt/issues/111)** - feat(traversal): support
  additional common ignore file types (.dockerignore, .eslintignore, .prettierignore, .npmignore)
  *(Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.3.1)* - **Sub-issues:** [#444](https://github.com/bdperkin/findfmt/issues/444),
  [#445](https://github.com/bdperkin/findfmt/issues/445),
  [#446](https://github.com/bdperkin/findfmt/issues/446),
  [#447](https://github.com/bdperkin/findfmt/issues/447)
- [ ] **[#229](https://github.com/bdperkin/findfmt/issues/229)** - feat(i18n): implement
  right-to-left (RTL) and bidirectional (BiDi) terminal formatting support *(Epic:
  [[Epic] i18n Platform Infrastructure: RTL/BiDi Rendering & Multilingual Documentation Builds](https://github.com/bdperkin/findfmt/issues/276)
  | Milestone: v1.4.1)* - **Sub-issues:** [#448](https://github.com/bdperkin/findfmt/issues/448),
  [#449](https://github.com/bdperkin/findfmt/issues/449),
  [#450](https://github.com/bdperkin/findfmt/issues/450)
- [ ] **[#324](https://github.com/bdperkin/findfmt/issues/324)** - refactor(api): make "import
  findfmt" side-effect free and decouple the core from the CLI *(Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.0)* - **Sub-issues:** [#451](https://github.com/bdperkin/findfmt/issues/451),
  [#452](https://github.com/bdperkin/findfmt/issues/452),
  [#453](https://github.com/bdperkin/findfmt/issues/453)
- [ ] **[#332](https://github.com/bdperkin/findfmt/issues/332)** - feat(cli): layered config
  precedence (user < project < env < CLI) and remove format booleans from config *(Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Milestone: v1.2.0)* - **Sub-issues:** [#454](https://github.com/bdperkin/findfmt/issues/454),
  [#455](https://github.com/bdperkin/findfmt/issues/455),
  [#456](https://github.com/bdperkin/findfmt/issues/456),
  [#457](https://github.com/bdperkin/findfmt/issues/457),
  [#458](https://github.com/bdperkin/findfmt/issues/458)
- [ ] **[#334](https://github.com/bdperkin/findfmt/issues/334)** - fix(parsers): --from-file
  mis-parses ASCII tree output, crashes on non-UTF-8 stdin, and lacks NUL input *(Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.2)* - **Sub-issues:** [#459](https://github.com/bdperkin/findfmt/issues/459),
  [#460](https://github.com/bdperkin/findfmt/issues/460),
  [#461](https://github.com/bdperkin/findfmt/issues/461),
  [#462](https://github.com/bdperkin/findfmt/issues/462),
  [#463](https://github.com/bdperkin/findfmt/issues/463)

______________________________________________________________________

## 4. Active Umbrella Epics

Note: Each epic's milestone equals the latest milestone among its open sub-issues. Sub-issues are
linked natively on GitHub.

- [ ] **[#347](https://github.com/bdperkin/findfmt/issues/347)** - [Epic] CLI Exit Code Contract,
  Status Code Flags, and Atomic Output Writing *(Milestone: v1.0.4 | Open sub-issues: 1)* -
  [#369](https://github.com/bdperkin/findfmt/issues/369)
- [ ] **[#384](https://github.com/bdperkin/findfmt/issues/384)** - [Epic] Formatter Integrity:
  Encoding Robustness, Stream Sanitization & Format Parity *(Milestone: v1.0.4 | Open sub-issues:
  3)* - [#330](https://github.com/bdperkin/findfmt/issues/330),
  [#341](https://github.com/bdperkin/findfmt/issues/341),
  [#343](https://github.com/bdperkin/findfmt/issues/343)
- [ ] **[#344](https://github.com/bdperkin/findfmt/issues/344)** - [Epic] CI Pipeline Determinism,
  Packaging Smoke Tests, and Tooling Alignment *(Milestone: v1.0.6 | Open sub-issues: 5)* -
  [#345](https://github.com/bdperkin/findfmt/issues/345),
  [#358](https://github.com/bdperkin/findfmt/issues/358),
  [#359](https://github.com/bdperkin/findfmt/issues/359),
  [#360](https://github.com/bdperkin/findfmt/issues/360),
  [#475](https://github.com/bdperkin/findfmt/issues/475)
- [ ] **[#308](https://github.com/bdperkin/findfmt/issues/308)** - [Epic] Investigate Open-Source
  Python AI Translators & Automation for GNU gettext .po Files *(Milestone: v1.0.7 | Open
  sub-issues: 5)* - [#303](https://github.com/bdperkin/findfmt/issues/303),
  [#304](https://github.com/bdperkin/findfmt/issues/304),
  [#305](https://github.com/bdperkin/findfmt/issues/305),
  [#306](https://github.com/bdperkin/findfmt/issues/306),
  [#307](https://github.com/bdperkin/findfmt/issues/307)
- [ ] **[#385](https://github.com/bdperkin/findfmt/issues/385)** - [Epic] Packaging Integrity,
  Release Automation & Dependency Verification *(Milestone: v1.0.7 | Open sub-issues: 4)* -
  [#325](https://github.com/bdperkin/findfmt/issues/325),
  [#327](https://github.com/bdperkin/findfmt/issues/327),
  [#328](https://github.com/bdperkin/findfmt/issues/328),
  [#349](https://github.com/bdperkin/findfmt/issues/349)
- [ ] **[#425](https://github.com/bdperkin/findfmt/issues/425)** - [Epic] Exhaustive Dependency
  Resolution Matrix Testing via uv in CI and Tooling *(Milestone: v1.0.7 | Open sub-issues: 4)* -
  [#426](https://github.com/bdperkin/findfmt/issues/426),
  [#427](https://github.com/bdperkin/findfmt/issues/427),
  [#429](https://github.com/bdperkin/findfmt/issues/429),
  [#430](https://github.com/bdperkin/findfmt/issues/430)
- [ ] **[#442](https://github.com/bdperkin/findfmt/issues/442)** - [Epic] Python Version Support
  Lifecycle: 3.11–3.15 Supported, 3.16 Preview *(Milestone: v1.1.0 | Open sub-issues: 3)* -
  [#335](https://github.com/bdperkin/findfmt/issues/335),
  [#440](https://github.com/bdperkin/findfmt/issues/440),
  [#441](https://github.com/bdperkin/findfmt/issues/441)
- [ ] **[#336](https://github.com/bdperkin/findfmt/issues/336)** - [Epic] Traversal Engine
  Stability: Unicode Sorting, Scandir Leak Prevention, and Deep Tree Recursion Safety *(Milestone:
  v1.1.1 | Open sub-issues: 1)* - [#372](https://github.com/bdperkin/findfmt/issues/372)
- [ ] **[#346](https://github.com/bdperkin/findfmt/issues/346)** - [Epic] CLI Documentation
  Accuracy, Dynamic --help-all Generation, and Option Validation *(Milestone: v1.1.1 | Open
  sub-issues: 2)* - [#365](https://github.com/bdperkin/findfmt/issues/365),
  [#366](https://github.com/bdperkin/findfmt/issues/366)
- [ ] **[#348](https://github.com/bdperkin/findfmt/issues/348)** - [Epic] Core Refactoring & API
  Hygiene Cleanup *(Milestone: v1.1.1 | Open sub-issues: 4)* -
  [#342](https://github.com/bdperkin/findfmt/issues/342),
  [#351](https://github.com/bdperkin/findfmt/issues/351),
  [#353](https://github.com/bdperkin/findfmt/issues/353),
  [#355](https://github.com/bdperkin/findfmt/issues/355)
- [ ] **[#386](https://github.com/bdperkin/findfmt/issues/386)** - [Epic] CLI Architecture, Terminal
  Interactivity & Execution Ergonomics *(Milestone: v1.1.2 | Open sub-issues: 5)* -
  [#319](https://github.com/bdperkin/findfmt/issues/319),
  [#324](https://github.com/bdperkin/findfmt/issues/324),
  [#329](https://github.com/bdperkin/findfmt/issues/329),
  [#331](https://github.com/bdperkin/findfmt/issues/331),
  [#334](https://github.com/bdperkin/findfmt/issues/334)
- [ ] **[#379](https://github.com/bdperkin/findfmt/issues/379)** - [Epic] Documentation
  Architecture, Sphinx Navigation & Project Branding *(Milestone: v1.2.1 | Open sub-issues: 3)* -
  [#302](https://github.com/bdperkin/findfmt/issues/302),
  [#309](https://github.com/bdperkin/findfmt/issues/309),
  [#312](https://github.com/bdperkin/findfmt/issues/312)
- [ ] **[#381](https://github.com/bdperkin/findfmt/issues/381)** - [Epic] Configuration
  Architecture: Layered Precedence, Schemas & Validation Diagnostics *(Milestone: v1.2.1 | Open
  sub-issues: 4)* - [#310](https://github.com/bdperkin/findfmt/issues/310),
  [#311](https://github.com/bdperkin/findfmt/issues/311),
  [#332](https://github.com/bdperkin/findfmt/issues/332),
  [#340](https://github.com/bdperkin/findfmt/issues/340)
- [ ] **[#380](https://github.com/bdperkin/findfmt/issues/380)** - [Epic] Developer Tooling, Static
  Analysis & Linting Standardization *(Milestone: v1.2.2 | Open sub-issues: 9)* -
  [#292](https://github.com/bdperkin/findfmt/issues/292),
  [#313](https://github.com/bdperkin/findfmt/issues/313),
  [#314](https://github.com/bdperkin/findfmt/issues/314),
  [#468](https://github.com/bdperkin/findfmt/issues/468),
  [#470](https://github.com/bdperkin/findfmt/issues/470),
  [#471](https://github.com/bdperkin/findfmt/issues/471),
  [#472](https://github.com/bdperkin/findfmt/issues/472),
  [#474](https://github.com/bdperkin/findfmt/issues/474),
  [#476](https://github.com/bdperkin/findfmt/issues/476)
- [ ] **[#382](https://github.com/bdperkin/findfmt/issues/382)** - [Epic] Pluggable Content
  Classification Engines & MIME Inspection Backends *(Milestone: v1.3.0 | Open sub-issues: 3)* -
  [#112](https://github.com/bdperkin/findfmt/issues/112),
  [#113](https://github.com/bdperkin/findfmt/issues/113),
  [#114](https://github.com/bdperkin/findfmt/issues/114)
- [ ] **[#383](https://github.com/bdperkin/findfmt/issues/383)** - [Epic] Directory Traversal
  Robustness, Symlink Safety & Ignore Rule Parity *(Milestone: v1.3.1 | Open sub-issues: 6)* -
  [#111](https://github.com/bdperkin/findfmt/issues/111),
  [#320](https://github.com/bdperkin/findfmt/issues/320),
  [#321](https://github.com/bdperkin/findfmt/issues/321),
  [#322](https://github.com/bdperkin/findfmt/issues/322),
  [#323](https://github.com/bdperkin/findfmt/issues/323),
  [#337](https://github.com/bdperkin/findfmt/issues/337)
- [ ] **[#276](https://github.com/bdperkin/findfmt/issues/276)** - [Epic] i18n Platform
  Infrastructure: RTL/BiDi Rendering & Multilingual Documentation Builds *(Milestone: v1.4.1 | Open
  sub-issues: 3)* - [#229](https://github.com/bdperkin/findfmt/issues/229),
  [#233](https://github.com/bdperkin/findfmt/issues/233),
  [#469](https://github.com/bdperkin/findfmt/issues/469)
- [ ] **[#205](https://github.com/bdperkin/findfmt/issues/205)** - [Epic] Add Language Support:
  Japonic & Koreanic (~205 Million) *(Milestone: v1.5.0 | Open sub-issues: 2)* -
  [#228](https://github.com/bdperkin/findfmt/issues/228),
  [#258](https://github.com/bdperkin/findfmt/issues/258)
- [ ] **[#301](https://github.com/bdperkin/findfmt/issues/301)** - [Epic] Investigate BeeWare
  Briefcase for Native Standalone Binary & Console Application Distribution *(Milestone: v1.6.0 |
  Open sub-issues: 5)* - [#296](https://github.com/bdperkin/findfmt/issues/296),
  [#297](https://github.com/bdperkin/findfmt/issues/297),
  [#298](https://github.com/bdperkin/findfmt/issues/298),
  [#299](https://github.com/bdperkin/findfmt/issues/299),
  [#300](https://github.com/bdperkin/findfmt/issues/300)
- [ ] **[#350](https://github.com/bdperkin/findfmt/issues/350)** - [Epic] v2.0 Breaking CLI Cleanups
  (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing) *(Milestone: v1.6.1 | Open
  sub-issues: 5)* - [#374](https://github.com/bdperkin/findfmt/issues/374),
  [#375](https://github.com/bdperkin/findfmt/issues/375),
  [#376](https://github.com/bdperkin/findfmt/issues/376),
  [#377](https://github.com/bdperkin/findfmt/issues/377),
  [#378](https://github.com/bdperkin/findfmt/issues/378)
- [ ] **[#197](https://github.com/bdperkin/findfmt/issues/197)** - [Epic] Add Language Support:
  Germanic (~1.83 Billion) *(Milestone: Future Features | Open sub-issues: 4)* -
  [#215](https://github.com/bdperkin/findfmt/issues/215),
  [#234](https://github.com/bdperkin/findfmt/issues/234),
  [#235](https://github.com/bdperkin/findfmt/issues/235),
  [#236](https://github.com/bdperkin/findfmt/issues/236)
- [ ] **[#198](https://github.com/bdperkin/findfmt/issues/198)** - [Epic] Add Language Support:
  Sino-Tibetan (~1.42 Billion) *(Milestone: Future Features | Open sub-issues: 3)* -
  [#216](https://github.com/bdperkin/findfmt/issues/216),
  [#237](https://github.com/bdperkin/findfmt/issues/237),
  [#238](https://github.com/bdperkin/findfmt/issues/238)
- [ ] **[#199](https://github.com/bdperkin/findfmt/issues/199)** - [Epic] Add Language Support:
  Indo-Aryan (~1.39 Billion) *(Milestone: Future Features | Open sub-issues: 11)* -
  [#217](https://github.com/bdperkin/findfmt/issues/217),
  [#218](https://github.com/bdperkin/findfmt/issues/218),
  [#219](https://github.com/bdperkin/findfmt/issues/219),
  [#220](https://github.com/bdperkin/findfmt/issues/220),
  [#239](https://github.com/bdperkin/findfmt/issues/239),
  [#240](https://github.com/bdperkin/findfmt/issues/240),
  [#241](https://github.com/bdperkin/findfmt/issues/241),
  [#242](https://github.com/bdperkin/findfmt/issues/242),
  [#243](https://github.com/bdperkin/findfmt/issues/243),
  [#244](https://github.com/bdperkin/findfmt/issues/244),
  [#245](https://github.com/bdperkin/findfmt/issues/245)
- [ ] **[#200](https://github.com/bdperkin/findfmt/issues/200)** - [Epic] Add Language Support:
  Romance (~1.25 Billion) *(Milestone: Future Features | Open sub-issues: 7)* -
  [#221](https://github.com/bdperkin/findfmt/issues/221),
  [#222](https://github.com/bdperkin/findfmt/issues/222),
  [#223](https://github.com/bdperkin/findfmt/issues/223),
  [#224](https://github.com/bdperkin/findfmt/issues/224),
  [#246](https://github.com/bdperkin/findfmt/issues/246),
  [#247](https://github.com/bdperkin/findfmt/issues/247),
  [#248](https://github.com/bdperkin/findfmt/issues/248)
- [ ] **[#201](https://github.com/bdperkin/findfmt/issues/201)** - [Epic] Add Language Support:
  Afroasiatic (~480 Million) *(Milestone: Future Features | Open sub-issues: 2)* -
  [#225](https://github.com/bdperkin/findfmt/issues/225),
  [#249](https://github.com/bdperkin/findfmt/issues/249)
- [ ] **[#202](https://github.com/bdperkin/findfmt/issues/202)** - [Epic] Add Language Support:
  Slavic (~415 Million) *(Milestone: Future Features | Open sub-issues: 4)* -
  [#226](https://github.com/bdperkin/findfmt/issues/226),
  [#250](https://github.com/bdperkin/findfmt/issues/250),
  [#251](https://github.com/bdperkin/findfmt/issues/251),
  [#252](https://github.com/bdperkin/findfmt/issues/252)
- [ ] **[#203](https://github.com/bdperkin/findfmt/issues/203)** - [Epic] Add Language Support:
  Austronesian (~295 Million) *(Milestone: Future Features | Open sub-issues: 2)* -
  [#227](https://github.com/bdperkin/findfmt/issues/227),
  [#253](https://github.com/bdperkin/findfmt/issues/253)
- [ ] **[#204](https://github.com/bdperkin/findfmt/issues/204)** - [Epic] Add Language Support:
  Dravidian (~270 Million) *(Milestone: Future Features | Open sub-issues: 4)* -
  [#254](https://github.com/bdperkin/findfmt/issues/254),
  [#255](https://github.com/bdperkin/findfmt/issues/255),
  [#256](https://github.com/bdperkin/findfmt/issues/256),
  [#257](https://github.com/bdperkin/findfmt/issues/257)
- [ ] **[#206](https://github.com/bdperkin/findfmt/issues/206)** - [Epic] Add Language Support:
  Niger–Congo (~210 Million) *(Milestone: Future Features | Open sub-issues: 2)* -
  [#259](https://github.com/bdperkin/findfmt/issues/259),
  [#260](https://github.com/bdperkin/findfmt/issues/260)
- [ ] **[#207](https://github.com/bdperkin/findfmt/issues/207)** - [Epic] Add Language Support:
  Turkic (~165 Million) *(Milestone: Future Features | Open sub-issues: 2)* -
  [#261](https://github.com/bdperkin/findfmt/issues/261),
  [#262](https://github.com/bdperkin/findfmt/issues/262)
- [ ] **[#208](https://github.com/bdperkin/findfmt/issues/208)** - [Epic] Add Language Support:
  Other Indo-European (~124 Million) *(Milestone: Future Features | Open sub-issues: 2)* -
  [#263](https://github.com/bdperkin/findfmt/issues/263),
  [#264](https://github.com/bdperkin/findfmt/issues/264)
- [ ] **[#209](https://github.com/bdperkin/findfmt/issues/209)** - [Epic] Add Language Support:
  Uralic (~18 Million) *(Milestone: Future Features | Open sub-issues: 1)* -
  [#265](https://github.com/bdperkin/findfmt/issues/265)
- [ ] **[#210](https://github.com/bdperkin/findfmt/issues/210)** - [Epic] Add Language Support:
  Hellenic (~13 Million) *(Milestone: Future Features | Open sub-issues: 1)* -
  [#266](https://github.com/bdperkin/findfmt/issues/266)
- [ ] **[#211](https://github.com/bdperkin/findfmt/issues/211)** - [Epic] Add Language Support: All
  Other (~200 Million) *(Milestone: Future Features | Open sub-issues: 4)* -
  [#267](https://github.com/bdperkin/findfmt/issues/267),
  [#268](https://github.com/bdperkin/findfmt/issues/268),
  [#269](https://github.com/bdperkin/findfmt/issues/269),
  [#270](https://github.com/bdperkin/findfmt/issues/270)
- [ ] **[#212](https://github.com/bdperkin/findfmt/issues/212)** - [Epic] Add Language Support:
  Constructive & Artificial (~2 Million) *(Milestone: Future Features | Open sub-issues: 0)* - none
  yet

______________________________________________________________________

## 5. Milestone Plan

Note: Re-balanced on 2026-10-21 to roughly 3-8 open issues per release. Added v1.0.7, v1.0.8, v1.1.2
and v1.3.1. Added v1.2.2 on 2026-10-22 for pre-commit and CI config hardening (#470-#474, #476), so
v1.2.1 is not overloaded. Counts include epics and tracking issues.

| Milestone       | Theme                                                                                                                                  | Open Issues |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| v1.0.3          | Directory Traversal Parity: Missing-Path Errors, Symlink Semantics & Gitignore Compliance (+ German catalog)                           | 6           |
| v1.0.4          | Output Correctness & Exit-Code Contract: ipynb/cp437 fixes, Broken-Pipe Parity, Config-Default Bug, Translation Placeholder Validation | 9           |
| v1.0.5          | Test Determinism & Hermeticity: Deterministic Perf Counters, Coverage Hygiene, Dependency-Matrix ADR (+ Spanish catalog)               | 7           |
| v1.0.6          | Release Safety & Packaging Hygiene: Tag-Pinned Releases, Reproducible Container, Required Floor Checks, 3.15 Gating                    | 9           |
| v1.0.7          | Dependency-Matrix Automation, Local Multi-Python Runner & AI Translation Tooling                                                       | 9           |
| v1.0.8          | Localization Wave: French & Japanese Catalogs and Multilingual Docs Builds                                                             | 4           |
| v1.1.0          | Python 3.11 Baseline & Core/CLI Decoupling: Side-Effect-Free Import, Wrapper Parsing, Friendly Errors                                  | 9           |
| v1.1.1          | CLI Help/Docs Accuracy, Pager Streaming, Depth-Safe Traversal & API Hygiene                                                            | 9           |
| v1.1.2          | --from-file Input Parser Hardening: Tree Parsing, Byte-Safe Input, NUL Mode, Path Confinement                                          | 7           |
| v1.2.0          | Configuration Architecture: Layered Precedence, Env Layer, Sample Config & Validation Diagnostics                                      | 7           |
| v1.2.1          | Docs Site Navigation & Branding, Ty Upgrade, Lint/Format Standardisation                                                               | 9           |
| v1.2.2          | Pre-commit & CI Config Hardening: Schema Validation, Workflow Timeouts, Meta Hooks, Markdown & Commit-Message Linting                  | 6           |
| v1.3.0          | Pluggable Content Classification Backends (mimetypes, filetype, puremagic)                                                             | 4           |
| v1.3.1          | Extended Ignore File Formats (.dockerignore, eslint/prettier/npm/stylelint presets)                                                    | 6           |
| v1.4.0          | Tier 1 Localizations (zh_CN, hi) & BiDi Rendering Strategy                                                                             | 3           |
| v1.4.1          | Tier 2 Localizations (bn, ur, pt) & RTL Table/Tree Rendering                                                                           | 7           |
| v1.4.2          | Tier 2 Localizations (ar, ru, id)                                                                                                      | 3           |
| v1.5.0          | Tier 3 Localizations (pa, pt_BR, it, ko, tr, vi)                                                                                       | 7           |
| v1.6.0          | Native Standalone Binary Distribution Evaluation (BeeWare Briefcase) — gated on #300 decision                                          | 6           |
| v1.6.1          | v2.0 Transition Prep: Deprecation Warnings & Breaking CLI Cleanups                                                                     | 6           |
| Future Features | Future feature enhancements and unplanned capabilities deferred beyond the scheduled roadmap.                                          | 48          |
