<!-- vale off -->

# Project TODO & Implementation Roadmap

> **Repository:** [bdperkin/findfmt](https://github.com/bdperkin/findfmt) **Generated:** 2026-10-21
> **Tracking:** 109 Closed Issues | 125 Actionable Open Tasks | 35 Active Umbrella Epics

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

______________________________________________________________________

## 2. Prioritized Open Implementation Roadmap

Note: Sorted by Value:Effort ratio, independent of strict milestone/epic ordering.

### 2.1. High Priority / Quick Wins

- [x] **[#428](https://github.com/bdperkin/findfmt/issues/428)** - ci(deps): add curated dependency
  resolution smoke matrix to PR workflow *(Epic:
  [[Epic] Exhaustive Dependency Resolution Matrix Testing via uv in CI and Tooling](https://github.com/bdperkin/findfmt/issues/425)
  | Milestone: v1.0.6)* - **Rationale:** High CI quality ROI; enforces declared dependency minimums
  and tests upstream pre-release compatibility directly on PRs.
- [x] **[#326](https://github.com/bdperkin/findfmt/issues/326)** - test: make the suite hermetic
  against the developer's global git config *(Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.5)* - **Rationale:** High developer experience ROI; conftest autouse fixture
  isolates test suite from host git configuration.
- [x] **[#356](https://github.com/bdperkin/findfmt/issues/356)** - [CI] Enforce --locked flag on all
  uv sync workflow invocations *(Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.5)* - **Rationale:** High build determinism ROI; enforcing --locked flag on all
  uv sync steps ensures reproducible CI runs.
- [x] **[#357](https://github.com/bdperkin/findfmt/issues/357)** - [CI] Configure full-history
  fetch-depth (fetch-depth: 0) for release and version-sensitive jobs *(Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.5)* - **Rationale:** High release safety ROI; fetch-depth: 0 checkout ensures
  VCS tag versioning is accurate across all jobs.
- [x] **[#352](https://github.com/bdperkin/findfmt/issues/352)** - [Core] Align format_size
  base-1024 unit labels to binary standards *(Epic:
  [[Epic] Core Refactoring & API Hygiene Cleanup](https://github.com/bdperkin/findfmt/issues/348) |
  Milestone: v1.0.4)* - **Rationale:** Low effort quick win; standardizes base-1024 binary units to
  KiB/K consistent with format_size_binary.
- [ ] **[#367](https://github.com/bdperkin/findfmt/issues/367)** - [CLI] Add --exit-status flag to
  return exit code 1 when no matching files are found *(Epic:
  [[Epic] CLI Exit Code Contract, Status Code Flags, and Atomic Output Writing](https://github.com/bdperkin/findfmt/issues/347)
  | Milestone: v1.0.4)* - **Rationale:** High utility CLI win; provides standard grep-like exit
  status code 1 for zero matches without overhead.
- [ ] **[#373](https://github.com/bdperkin/findfmt/issues/373)** - [CLI] Align console wrapper
  entrypoint exit code mapping for SystemExit exceptions *(Epic:
  [[Epic] Traversal Engine Stability: Unicode Sorting, Scandir Leak Prevention, and Deep Tree Recursion Safety](https://github.com/bdperkin/findfmt/issues/336)
  | Milestone: v1.0.4)* - **Rationale:** Low effort quick fix; aligns SystemExit string argument
  mapping in wrappers to return standard exit code 1.
- [ ] **[#354](https://github.com/bdperkin/findfmt/issues/354)** - [Core] Preserve significant
  leading and escaped trailing whitespace in gitignore parser *(Epic:
  [[Epic] Core Refactoring & API Hygiene Cleanup](https://github.com/bdperkin/findfmt/issues/348) |
  Milestone: v1.0.3)* - **Rationale:** Low effort compliance fix; preserves significant leading and
  escaped trailing whitespace in gitignore patterns.
- [ ] **[#355](https://github.com/bdperkin/findfmt/issues/355)** - [Core] Fix symlink parser
  handling of filenames containing arrow ('->') delimiters *(Epic:
  [[Epic] Core Refactoring & API Hygiene Cleanup](https://github.com/bdperkin/findfmt/issues/348) |
  Milestone: v1.0.3)* - **Rationale:** Low effort parser fix; robust arrow partitioning preserves
  symlink filenames containing '->' delimiters.
- [ ] **[#335](https://github.com/bdperkin/findfmt/issues/335)** - build: remove the Python 3.15
  classifier until the 3.15 CI job is gating *(Epic:
  [[Epic] Packaging Integrity, Release Automation & Dependency Verification](https://github.com/bdperkin/findfmt/issues/385)
  | Milestone: v1.0.6)* - **Rationale:** Trivial metadata hygiene; removes premature Python 3.15
  classifier until CI matrix job is gating.
- [ ] **[#349](https://github.com/bdperkin/findfmt/issues/349)** - chore: fix PyPI summary typo and
  add a nox/multi-Python local runner *(Epic:
  [[Epic] Packaging Integrity, Release Automation & Dependency Verification](https://github.com/bdperkin/findfmt/issues/385)
  | Milestone: v1.0.6)* - **Rationale:** Developer experience quick win; fixes PyPI summary typo and
  provides local multi-Python testing runner.
- [ ] **[#364](https://github.com/bdperkin/findfmt/issues/364)** - [Docs] Correct inaccurate and
  duplicated CLI option flags across documentation guides and README *(Epic:
  [[Epic] CLI Documentation Accuracy, Dynamic --help-all Generation, and Option Validation](https://github.com/bdperkin/findfmt/issues/346)
  | Milestone: v1.1.1)* - **Rationale:** Documentation accuracy quick win; corrects option flag
  discrepancies between documentation and Click command.
- [ ] **[#314](https://github.com/bdperkin/findfmt/issues/314)** - refactor(lint): standardize line
  length limit to 110 columns across all linters, checkers, and formatters *(Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.0)* - **Rationale:** Code quality quick win; standardizes line length to 110
  columns across all linters, checkers, and formatters.
- [ ] **[#313](https://github.com/bdperkin/findfmt/issues/313)** - chore(pre-commit): configure
  yamlfix formatting rules in pyproject.toml *(Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.0)* - **Rationale:** Tooling configuration quick win; centralizes yamlfix rules
  in pyproject.toml.
- [ ] **[#302](https://github.com/bdperkin/findfmt/issues/302)** - feat(docs): replace top-left
  Sphinx sidebar logo with high-resolution square icon *(Epic:
  [[Epic] Documentation Architecture, Sphinx Navigation & Project Branding](https://github.com/bdperkin/findfmt/issues/379)
  | Milestone: v1.2.1)* - **Rationale:** Visual branding quick win; configures high-resolution
  square logo icon in Sphinx documentation sidebar.

### 2.2. Medium Priority / Core Deliverables

- [ ] **[#320](https://github.com/bdperkin/findfmt/issues/320)** - fix(traversal): missing or
  unreadable paths are silently skipped with exit 0 *(Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.3)*
- [ ] **[#321](https://github.com/bdperkin/findfmt/issues/321)** - fix(traversal): symlinks are
  omitted by default and misclassified/mis-pathed with -l *(Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.3)*
- [ ] **[#322](https://github.com/bdperkin/findfmt/issues/322)** - fix(traversal):
  traverse_directory() ignores .gitignore when given a relative root *(Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.3)*
- [ ] **[#323](https://github.com/bdperkin/findfmt/issues/323)** - fix(traversal): align global
  gitignore discovery with git (drop ~/.gitignore, use repo cwd, stop at repo root) *(Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.3)*
- [ ] **[#337](https://github.com/bdperkin/findfmt/issues/337)** - perf(traversal): eliminate
  redundant per-file syscalls and quadratic --prune scanning *(Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.0.3)*
- [ ] **[#372](https://github.com/bdperkin/findfmt/issues/372)** - [Core] Replace recursive
  directory traversal and size calculation with iterative depth-safe implementations *(Epic:
  [[Epic] Traversal Engine Stability: Unicode Sorting, Scandir Leak Prevention, and Deep Tree Recursion Safety](https://github.com/bdperkin/findfmt/issues/336)
  | Milestone: v1.1.1)*
- [ ] **[#111](https://github.com/bdperkin/findfmt/issues/111)** - feat(traversal): support
  additional common ignore file types (.dockerignore, .eslintignore, .prettierignore, .npmignore)
  *(Epic:
  [[Epic] Directory Traversal Robustness, Symlink Safety & Ignore Rule Parity](https://github.com/bdperkin/findfmt/issues/383)
  | Milestone: v1.3.0)*
- [ ] **[#319](https://github.com/bdperkin/findfmt/issues/319)** - fix(cli): wrapper entry points
  misparse value options; findfilefmt -o x tag truncates a file named "tag" *(Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.0)*
- [ ] **[#324](https://github.com/bdperkin/findfmt/issues/324)** - refactor(api): make "import
  findfmt" side-effect free and decouple the core from the CLI *(Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.0)*
- [ ] **[#329](https://github.com/bdperkin/findfmt/issues/329)** - fix(cli): invalid --table-style
  and other domain errors print full tracebacks *(Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.0)*
- [ ] **[#331](https://github.com/bdperkin/findfmt/issues/331)** - perf(cli): TTY output is fully
  buffered for the pager, so nothing streams *(Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.0)*
- [ ] **[#334](https://github.com/bdperkin/findfmt/issues/334)** - fix(parsers): --from-file
  mis-parses ASCII tree output, crashes on non-UTF-8 stdin, and lacks NUL input *(Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.0)*
- [ ] **[#342](https://github.com/bdperkin/findfmt/issues/342)** - refactor(cli): pass click.Context
  explicitly instead of walking stack frames; validate TraversalConfig *(Epic:
  [[Epic] CLI Architecture, Terminal Interactivity & Execution Ergonomics](https://github.com/bdperkin/findfmt/issues/386)
  | Milestone: v1.1.0)*
- [ ] **[#351](https://github.com/bdperkin/findfmt/issues/351)** - [Core] Prune internal helper
  re-exports from `findfmt.traversal.__all__` *(Epic:
  [[Epic] Core Refactoring & API Hygiene Cleanup](https://github.com/bdperkin/findfmt/issues/348) |
  Milestone: v1.1.0)*
- [ ] **[#365](https://github.com/bdperkin/findfmt/issues/365)** - [CLI] Dynamically generate
  --help-all output directly from Click command introspection *(Epic:
  [[Epic] CLI Documentation Accuracy, Dynamic --help-all Generation, and Option Validation](https://github.com/bdperkin/findfmt/issues/346)
  | Milestone: v1.1.1)*
- [ ] **[#366](https://github.com/bdperkin/findfmt/issues/366)** - [CLI] Validate numeric CLI
  parameters (min=0) and clarify misleading option help descriptions *(Epic:
  [[Epic] CLI Documentation Accuracy, Dynamic --help-all Generation, and Option Validation](https://github.com/bdperkin/findfmt/issues/346)
  | Milestone: v1.1.1)*
- [ ] **[#330](https://github.com/bdperkin/findfmt/issues/330)** - fix(format): -f ipynb emits JSON
  literals (null/false) that raise NameError when run *(Epic:
  [[Epic] Formatter Integrity: Encoding Robustness, Stream Sanitization & Format Parity](https://github.com/bdperkin/findfmt/issues/384)
  | Milestone: v1.0.4)*
- [ ] **[#341](https://github.com/bdperkin/findfmt/issues/341)** - fix(format): consistent
  broken-pipe exit codes and respect --sort/--reverse in tree/HTML/XML *(Epic:
  [[Epic] Formatter Integrity: Encoding Robustness, Stream Sanitization & Format Parity](https://github.com/bdperkin/findfmt/issues/384)
  | Milestone: v1.0.4)*
- [ ] **[#343](https://github.com/bdperkin/findfmt/issues/343)** - fix(format): --cp437 writes
  Latin-1 code points, which show as mojibake *(Epic:
  [[Epic] Formatter Integrity: Encoding Robustness, Stream Sanitization & Format Parity](https://github.com/bdperkin/findfmt/issues/384)
  | Milestone: v1.0.4)*
- [ ] **[#369](https://github.com/bdperkin/findfmt/issues/369)** - [Docs] Document formal CLI
  exit-code contract with exhaustive test matrix *(Epic:
  [[Epic] CLI Exit Code Contract, Status Code Flags, and Atomic Output Writing](https://github.com/bdperkin/findfmt/issues/347)
  | Milestone: v1.0.4)*
- [ ] **[#310](https://github.com/bdperkin/findfmt/issues/310)** - feat(config): provide sample
  config.toml, annotated reference configuration, and --generate-config CLI option *(Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Milestone: v1.2.0)*
- [ ] **[#311](https://github.com/bdperkin/findfmt/issues/311)** - refactor(config): investigate
  consolidating standalone repository configuration files into pyproject.toml *(Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Milestone: v1.2.0)*
- [ ] **[#332](https://github.com/bdperkin/findfmt/issues/332)** - feat(cli): layered config
  precedence (user < project < env < CLI) and remove format booleans from config *(Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Milestone: v1.2.0)*
- [ ] **[#340](https://github.com/bdperkin/findfmt/issues/340)** - feat(cli): improve config
  validation diagnostics (all errors, did-you-mean, reprs, alias collisions) *(Epic:
  [[Epic] Configuration Architecture: Layered Precedence, Schemas & Validation Diagnostics](https://github.com/bdperkin/findfmt/issues/381)
  | Milestone: v1.2.0)*
- [ ] **[#345](https://github.com/bdperkin/findfmt/issues/345)** - test(perf): replace wall-clock
  assertions with deterministic counters and re-baseline memory *(Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.5)*
- [ ] **[#353](https://github.com/bdperkin/findfmt/issues/353)** - [Tests] Tighten coverage pragmas
  and eliminate reachable/dead code pragmas *(Epic:
  [[Epic] Core Refactoring & API Hygiene Cleanup](https://github.com/bdperkin/findfmt/issues/348) |
  Milestone: v1.0.5)*
- [ ] **[#358](https://github.com/bdperkin/findfmt/issues/358)** - [Packaging] Expand packaging
  smoke matrix to build and verify sdist installations *(Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.5)*
- [ ] **[#359](https://github.com/bdperkin/findfmt/issues/359)** - [Tests] Complete pyproject.toml
  test dependency group and isolate catalog compilation fixture *(Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.5)*
- [ ] **[#325](https://github.com/bdperkin/findfmt/issues/325)** - build(deps): raise false
  dependency minimums and add a lowest-direct CI job *(Epic:
  [[Epic] Packaging Integrity, Release Automation & Dependency Verification](https://github.com/bdperkin/findfmt/issues/385)
  | Milestone: v1.0.6)*
- [ ] **[#327](https://github.com/bdperkin/findfmt/issues/327)** - ci(release): workflow_dispatch
  ignores the "tag" input and can publish a .devN build to PyPI *(Epic:
  [[Epic] Packaging Integrity, Release Automation & Dependency Verification](https://github.com/bdperkin/findfmt/issues/385)
  | Milestone: v1.0.6)*
- [ ] **[#328](https://github.com/bdperkin/findfmt/issues/328)** - build(docker): image reports
  1.0.0.dev0, ignores uv.lock, ships uv, and lacks provenance *(Epic:
  [[Epic] Packaging Integrity, Release Automation & Dependency Verification](https://github.com/bdperkin/findfmt/issues/385)
  | Milestone: v1.0.6)*
- [ ] **[#360](https://github.com/bdperkin/findfmt/issues/360)** - [CI] Align tool versions across
  pre-commit and uv.lock, and schedule docs linkcheck *(Epic:
  [[Epic] CI Pipeline Determinism, Packaging Smoke Tests, and Tooling Alignment](https://github.com/bdperkin/findfmt/issues/344)
  | Milestone: v1.0.6)*
- [ ] **[#426](https://github.com/bdperkin/findfmt/issues/426)** - ci(deps): evaluate matrix tooling
  orchestration and define pruned resolution parameter matrix *(Epic:
  [[Epic] Exhaustive Dependency Resolution Matrix Testing via uv in CI and Tooling](https://github.com/bdperkin/findfmt/issues/425)
  | Milestone: v1.0.5)*
- [ ] **[#427](https://github.com/bdperkin/findfmt/issues/427)** - tools(deps): implement local
  dependency resolution matrix runner with failure diagnostics *(Epic:
  [[Epic] Exhaustive Dependency Resolution Matrix Testing via uv in CI and Tooling](https://github.com/bdperkin/findfmt/issues/425)
  | Milestone: v1.0.5)*
- [ ] **[#429](https://github.com/bdperkin/findfmt/issues/429)** - ci(deps): create exhaustive
  scheduled and dispatch dependency resolution matrix workflow *(Epic:
  [[Epic] Exhaustive Dependency Resolution Matrix Testing via uv in CI and Tooling](https://github.com/bdperkin/findfmt/issues/425)
  | Milestone: v1.0.6)*
- [ ] **[#430](https://github.com/bdperkin/findfmt/issues/430)** - docs(deps): document dependency
  matrix testing and bound troubleshooting in contributing guide *(Epic:
  [[Epic] Exhaustive Dependency Resolution Matrix Testing via uv in CI and Tooling](https://github.com/bdperkin/findfmt/issues/425)
  | Milestone: v1.0.6)*
- [ ] **[#309](https://github.com/bdperkin/findfmt/issues/309)** - feat(docs): investigate
  expandable hierarchical heading navigation in Sphinx left sidebar *(Epic:
  [[Epic] Documentation Architecture, Sphinx Navigation & Project Branding](https://github.com/bdperkin/findfmt/issues/379)
  | Milestone: v1.2.1)*
- [ ] **[#312](https://github.com/bdperkin/findfmt/issues/312)** - docs(readme): audit and expand
  high-value status, security, and metadata badges in README and documentation header *(Epic:
  [[Epic] Documentation Architecture, Sphinx Navigation & Project Branding](https://github.com/bdperkin/findfmt/issues/379)
  | Milestone: v1.2.1)*
- [ ] **[#292](https://github.com/bdperkin/findfmt/issues/292)** - refactor(types): resolve Ty
  truthiness-test-of-none-union diagnostics to upgrade past v0.0.84 *(Epic:
  [[Epic] Developer Tooling, Static Analysis & Linting Standardization](https://github.com/bdperkin/findfmt/issues/380)
  | Milestone: v1.2.1)*
- [ ] **[#112](https://github.com/bdperkin/findfmt/issues/112)** - feat(classifier): support
  optional mimetypes backend for fast extension-based classification *(Epic:
  [[Epic] Pluggable Content Classification Engines & MIME Inspection Backends](https://github.com/bdperkin/findfmt/issues/382)
  | Milestone: v1.3.0)*
- [ ] **[#113](https://github.com/bdperkin/findfmt/issues/113)** - feat(classifier): support
  optional filetype backend for fast magic number signature inspection *(Epic:
  [[Epic] Pluggable Content Classification Engines & MIME Inspection Backends](https://github.com/bdperkin/findfmt/issues/382)
  | Milestone: v1.3.0)*
- [ ] **[#114](https://github.com/bdperkin/findfmt/issues/114)** - feat(classifier): support
  optional puremagic backend for deep magic signature analysis *(Epic:
  [[Epic] Pluggable Content Classification Engines & MIME Inspection Backends](https://github.com/bdperkin/findfmt/issues/382)
  | Milestone: v1.3.0)*
- [ ] **[#215](https://github.com/bdperkin/findfmt/issues/215)** - feat(i18n): add language support
  for German (de) (~133 million) *(Epic:
  [[Epic] Add Language Support: Germanic (~1.83 Billion)](https://github.com/bdperkin/findfmt/issues/197)
  | Milestone: v1.0.3)*
- [ ] **[#303](https://github.com/bdperkin/findfmt/issues/303)** - feat(i18n): benchmark and
  evaluate open-source Python gettext AI translators (gettext-translator, pytlai,
  auto-gettext-translator) *(Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.3)*
- [ ] **[#304](https://github.com/bdperkin/findfmt/issues/304)** - feat(i18n): design and implement
  Python format placeholder & variable protection validation for AI translation *(Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.4)*
- [ ] **[#305](https://github.com/bdperkin/findfmt/issues/305)** - feat(i18n): formulate domain
  context prompt engineering and ngettext pluralization rules for AI translation *(Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.4)*
- [ ] **[#306](https://github.com/bdperkin/findfmt/issues/306)** - feat(i18n): integrate AI
  translation command into developer tooling (tools/i18n.py translate) *(Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.5)*
- [ ] **[#307](https://github.com/bdperkin/findfmt/issues/307)** - feat(i18n): evaluate managed
  localization platforms with native AI (POEditor, Crowdin, Localazy) vs local CI automation *(Epic:
  [[Epic] Investigate Open-Source Python AI Translators & Automation for GNU gettext .po Files](https://github.com/bdperkin/findfmt/issues/308)
  | Milestone: v1.0.5)*
- [ ] **[#221](https://github.com/bdperkin/findfmt/issues/221)** - feat(i18n): add language support
  for Spanish (es) (~559 million) *(Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: v1.0.5)*
- [ ] **[#222](https://github.com/bdperkin/findfmt/issues/222)** - feat(i18n): add language support
  for French (fr) (~310 million) *(Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: v1.0.6)*
- [ ] **[#228](https://github.com/bdperkin/findfmt/issues/228)** - feat(i18n): add language support
  for Japanese (ja) (~123 million) *(Epic:
  [[Epic] Add Language Support: Japonic & Koreanic (~205 Million)](https://github.com/bdperkin/findfmt/issues/205)
  | Milestone: v1.0.6)*
- [ ] **[#229](https://github.com/bdperkin/findfmt/issues/229)** - feat(i18n): implement
  right-to-left (RTL) and bidirectional (BiDi) terminal formatting support *(Epic:
  [[Epic] Infrastructure & Architecture Issues](https://github.com/bdperkin/findfmt/issues/276) |
  Milestone: v1.0.6)*
- [ ] **[#233](https://github.com/bdperkin/findfmt/issues/233)** - ci(docs): configure automated
  multilingual Sphinx documentation builds in CI pipeline *(Epic:
  [[Epic] Infrastructure & Architecture Issues](https://github.com/bdperkin/findfmt/issues/276) |
  Milestone: v1.4.0)*

### 2.3. Future / Low-Priority / Backlog

- [ ] **[#216](https://github.com/bdperkin/findfmt/issues/216)** - feat(i18n): add language support
  for Chinese - China / Mandarin (zh_CN) (~1.14 billion) *(Epic:
  [[Epic] Add Language Support: Sino-Tibetan (~1.42 Billion)](https://github.com/bdperkin/findfmt/issues/198)
  | Milestone: v1.4.1)*
- [ ] **[#217](https://github.com/bdperkin/findfmt/issues/217)** - feat(i18n): add language support
  for Hindi (hi) (~610 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: v1.4.1)*
- [ ] **[#218](https://github.com/bdperkin/findfmt/issues/218)** - feat(i18n): add language support
  for Bengali (bn) (~273 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: v1.4.2)*
- [ ] **[#219](https://github.com/bdperkin/findfmt/issues/219)** - feat(i18n): add language support
  for Urdu (ur) (~232 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: v1.4.2)*
- [ ] **[#220](https://github.com/bdperkin/findfmt/issues/220)** - feat(i18n): add language support
  for Punjabi (pa) (~125 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)*
- [ ] **[#223](https://github.com/bdperkin/findfmt/issues/223)** - feat(i18n): add language support
  for Portuguese (pt) (~264 million) *(Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: v1.4.2)*
- [ ] **[#224](https://github.com/bdperkin/findfmt/issues/224)** - feat(i18n): add language support
  for Portuguese - Brazil (pt_BR) (~208 million (subset of total Portuguese)) *(Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: Future Features)*
- [ ] **[#225](https://github.com/bdperkin/findfmt/issues/225)** - feat(i18n): add language support
  for Arabic (ar) (~370 million) *(Epic:
  [[Epic] Add Language Support: Afroasiatic (~480 Million)](https://github.com/bdperkin/findfmt/issues/201)
  | Milestone: v1.4.2)*
- [ ] **[#226](https://github.com/bdperkin/findfmt/issues/226)** - feat(i18n): add language support
  for Russian (ru) (~255 million) *(Epic:
  [[Epic] Add Language Support: Slavic (~415 Million)](https://github.com/bdperkin/findfmt/issues/202)
  | Milestone: v1.4.2)*
- [ ] **[#227](https://github.com/bdperkin/findfmt/issues/227)** - feat(i18n): add language support
  for Indonesian (id) (~199 million) *(Epic:
  [[Epic] Add Language Support: Austronesian (~295 Million)](https://github.com/bdperkin/findfmt/issues/203)
  | Milestone: v1.4.2)*
- [ ] **[#234](https://github.com/bdperkin/findfmt/issues/234)** - feat(i18n): add language support
  for English - United Kingdom (en_GB) (~60 million) *(Epic:
  [[Epic] Add Language Support: Germanic (~1.83 Billion)](https://github.com/bdperkin/findfmt/issues/197)
  | Milestone: Future Features)*
- [ ] **[#235](https://github.com/bdperkin/findfmt/issues/235)** - feat(i18n): add language support
  for Dutch (nl) (~24 million) *(Epic:
  [[Epic] Add Language Support: Germanic (~1.83 Billion)](https://github.com/bdperkin/findfmt/issues/197)
  | Milestone: Future Features)*
- [ ] **[#236](https://github.com/bdperkin/findfmt/issues/236)** - feat(i18n): add language support
  for Swedish (sv) (~10 million) *(Epic:
  [[Epic] Add Language Support: Germanic (~1.83 Billion)](https://github.com/bdperkin/findfmt/issues/197)
  | Milestone: Future Features)*
- [ ] **[#237](https://github.com/bdperkin/findfmt/issues/237)** - feat(i18n): add language support
  for Burmese (my) (~33 million) *(Epic:
  [[Epic] Add Language Support: Sino-Tibetan (~1.42 Billion)](https://github.com/bdperkin/findfmt/issues/198)
  | Milestone: Future Features)*
- [ ] **[#238](https://github.com/bdperkin/findfmt/issues/238)** - feat(i18n): add language support
  for Chinese - Taiwan / Mandarin (zh_TW) (~23 million) *(Epic:
  [[Epic] Add Language Support: Sino-Tibetan (~1.42 Billion)](https://github.com/bdperkin/findfmt/issues/198)
  | Milestone: Future Features)*
- [ ] **[#239](https://github.com/bdperkin/findfmt/issues/239)** - feat(i18n): add language support
  for Marathi (mr) (~99 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)*
- [ ] **[#240](https://github.com/bdperkin/findfmt/issues/240)** - feat(i18n): add language support
  for Gujarati (gu) (~62 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)*
- [ ] **[#241](https://github.com/bdperkin/findfmt/issues/241)** - feat(i18n): add language support
  for Odia (or) (~35 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)*
- [ ] **[#242](https://github.com/bdperkin/findfmt/issues/242)** - feat(i18n): add language support
  for Maithili (mai) (~34 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)*
- [ ] **[#243](https://github.com/bdperkin/findfmt/issues/243)** - feat(i18n): add language support
  for Assamese (as) (~15 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)*
- [ ] **[#244](https://github.com/bdperkin/findfmt/issues/244)** - feat(i18n): add language support
  for Sinhala (si) (~17 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)*
- [ ] **[#245](https://github.com/bdperkin/findfmt/issues/245)** - feat(i18n): add language support
  for Nepali (ne) (~16 million) *(Epic:
  [[Epic] Add Language Support: Indo-Aryan (~1.39 Billion)](https://github.com/bdperkin/findfmt/issues/199)
  | Milestone: Future Features)*
- [ ] **[#246](https://github.com/bdperkin/findfmt/issues/246)** - feat(i18n): add language support
  for Italian (it) (~68 million) *(Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: Future Features)*
- [ ] **[#247](https://github.com/bdperkin/findfmt/issues/247)** - feat(i18n): add language support
  for Romanian (ro) (~24 million) *(Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: Future Features)*
- [ ] **[#248](https://github.com/bdperkin/findfmt/issues/248)** - feat(i18n): add language support
  for Catalan (ca) (~10 million) *(Epic:
  [[Epic] Add Language Support: Romance (~1.25 Billion)](https://github.com/bdperkin/findfmt/issues/200)
  | Milestone: Future Features)*
- [ ] **[#249](https://github.com/bdperkin/findfmt/issues/249)** - feat(i18n): add language support
  for Amharic (am) (~58 million) *(Epic:
  [[Epic] Add Language Support: Afroasiatic (~480 Million)](https://github.com/bdperkin/findfmt/issues/201)
  | Milestone: Future Features)*
- [ ] **[#250](https://github.com/bdperkin/findfmt/issues/250)** - feat(i18n): add language support
  for Polish (pl) (~40 million) *(Epic:
  [[Epic] Add Language Support: Slavic (~415 Million)](https://github.com/bdperkin/findfmt/issues/202)
  | Milestone: Future Features)*
- [ ] **[#251](https://github.com/bdperkin/findfmt/issues/251)** - feat(i18n): add language support
  for Ukrainian (uk) (~40 million) *(Epic:
  [[Epic] Add Language Support: Slavic (~415 Million)](https://github.com/bdperkin/findfmt/issues/202)
  | Milestone: Future Features)*
- [ ] **[#252](https://github.com/bdperkin/findfmt/issues/252)** - feat(i18n): add language support
  for Czech (cs) (~10.7 million) *(Epic:
  [[Epic] Add Language Support: Slavic (~415 Million)](https://github.com/bdperkin/findfmt/issues/202)
  | Milestone: Future Features)*
- [ ] **[#253](https://github.com/bdperkin/findfmt/issues/253)** - feat(i18n): add language support
  for Malay (ms) (~30 million) *(Epic:
  [[Epic] Add Language Support: Austronesian (~295 Million)](https://github.com/bdperkin/findfmt/issues/203)
  | Milestone: Future Features)*
- [ ] **[#254](https://github.com/bdperkin/findfmt/issues/254)** - feat(i18n): add language support
  for Telugu (te) (~96 million) *(Epic:
  [[Epic] Add Language Support: Dravidian (~270 Million)](https://github.com/bdperkin/findfmt/issues/204)
  | Milestone: Future Features)*
- [ ] **[#255](https://github.com/bdperkin/findfmt/issues/255)** - feat(i18n): add language support
  for Tamil (ta) (~87 million) *(Epic:
  [[Epic] Add Language Support: Dravidian (~270 Million)](https://github.com/bdperkin/findfmt/issues/204)
  | Milestone: Future Features)*
- [ ] **[#256](https://github.com/bdperkin/findfmt/issues/256)** - feat(i18n): add language support
  for Kannada (kn) (~59 million) *(Epic:
  [[Epic] Add Language Support: Dravidian (~270 Million)](https://github.com/bdperkin/findfmt/issues/204)
  | Milestone: Future Features)*
- [ ] **[#257](https://github.com/bdperkin/findfmt/issues/257)** - feat(i18n): add language support
  for Malayalam (ml) (~38 million) *(Epic:
  [[Epic] Add Language Support: Dravidian (~270 Million)](https://github.com/bdperkin/findfmt/issues/204)
  | Milestone: Future Features)*
- [ ] **[#258](https://github.com/bdperkin/findfmt/issues/258)** - feat(i18n): add language support
  for Korean (ko) (~82 million) *(Epic:
  [[Epic] Add Language Support: Japonic & Koreanic (~205 Million)](https://github.com/bdperkin/findfmt/issues/205)
  | Milestone: Future Features)*
- [ ] **[#259](https://github.com/bdperkin/findfmt/issues/259)** - feat(i18n): add language support
  for N'Ko / Manding (nqo) (~40 million) *(Epic:
  [[Epic] Add Language Support: Niger–Congo (~210 Million)](https://github.com/bdperkin/findfmt/issues/206)
  | Milestone: Future Features)*
- [ ] **[#260](https://github.com/bdperkin/findfmt/issues/260)** - feat(i18n): add language support
  for Zulu (zu) (~14 million) *(Epic:
  [[Epic] Add Language Support: Niger–Congo (~210 Million)](https://github.com/bdperkin/findfmt/issues/206)
  | Milestone: Future Features)*
- [ ] **[#261](https://github.com/bdperkin/findfmt/issues/261)** - feat(i18n): add language support
  for Turkish (tr) (~90 million) *(Epic:
  [[Epic] Add Language Support: Turkic (~165 Million)](https://github.com/bdperkin/findfmt/issues/207)
  | Milestone: Future Features)*
- [ ] **[#262](https://github.com/bdperkin/findfmt/issues/262)** - feat(i18n): add language support
  for Kazakh (kk) (~15 million) *(Epic:
  [[Epic] Add Language Support: Turkic (~165 Million)](https://github.com/bdperkin/findfmt/issues/207)
  | Milestone: Future Features)*
- [ ] **[#263](https://github.com/bdperkin/findfmt/issues/263)** - feat(i18n): add language support
  for Persian (fa) (~79 million) *(Epic:
  [[Epic] Add Language Support: Other Indo-European (~124 Million)](https://github.com/bdperkin/findfmt/issues/208)
  | Milestone: Future Features)*
- [ ] **[#264](https://github.com/bdperkin/findfmt/issues/264)** - feat(i18n): add language support
  for Kurdish (ku) (~30 million) *(Epic:
  [[Epic] Add Language Support: Other Indo-European (~124 Million)](https://github.com/bdperkin/findfmt/issues/208)
  | Milestone: Future Features)*
- [ ] **[#265](https://github.com/bdperkin/findfmt/issues/265)** - feat(i18n): add language support
  for Hungarian (hu) (~13 million) *(Epic:
  [[Epic] Add Language Support: Uralic (~18 Million)](https://github.com/bdperkin/findfmt/issues/209)
  | Milestone: Future Features)*
- [ ] **[#266](https://github.com/bdperkin/findfmt/issues/266)** - feat(i18n): add language support
  for Greek (el) (~13 million) *(Epic:
  [[Epic] Add Language Support: Hellenic (~13 Million)](https://github.com/bdperkin/findfmt/issues/210)
  | Milestone: Future Features)*
- [ ] **[#267](https://github.com/bdperkin/findfmt/issues/267)** - feat(i18n): add language support
  for Vietnamese (vi) (~86 million) *(Epic:
  [[Epic] Add Language Support: All Other (~200 Million)](https://github.com/bdperkin/findfmt/issues/211)
  | Milestone: Future Features)*
- [ ] **[#268](https://github.com/bdperkin/findfmt/issues/268)** - feat(i18n): add language support
  for Thai (th) (~61 million) *(Epic:
  [[Epic] Add Language Support: All Other (~200 Million)](https://github.com/bdperkin/findfmt/issues/211)
  | Milestone: Future Features)*
- [ ] **[#269](https://github.com/bdperkin/findfmt/issues/269)** - feat(i18n): add language support
  for Lao (lo) (~30 million) *(Epic:
  [[Epic] Add Language Support: All Other (~200 Million)](https://github.com/bdperkin/findfmt/issues/211)
  | Milestone: Future Features)*
- [ ] **[#270](https://github.com/bdperkin/findfmt/issues/270)** - feat(i18n): add language support
  for Khmer (km) (~16 million) *(Epic:
  [[Epic] Add Language Support: All Other (~200 Million)](https://github.com/bdperkin/findfmt/issues/211)
  | Milestone: Future Features)*
- [ ] **[#296](https://github.com/bdperkin/findfmt/issues/296)** - feat(packaging): investigate
  Briefcase configuration and feasibility for findfmt console application *(Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)*
- [ ] **[#297](https://github.com/bdperkin/findfmt/issues/297)** - feat(packaging): evaluate
  Briefcase desktop & system packaging formats (macOS, Windows, Linux) *(Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)*
- [ ] **[#298](https://github.com/bdperkin/findfmt/issues/298)** - ci(packaging): design and
  prototype automated Briefcase multi-platform CI build pipeline with GitHub Actions *(Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)*
- [ ] **[#299](https://github.com/bdperkin/findfmt/issues/299)** - feat(web): evaluate Web /
  PyScript client-side distribution for interactive browser demonstration *(Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)*
- [ ] **[#300](https://github.com/bdperkin/findfmt/issues/300)** - docs(packaging): document
  standalone binary installation options and Briefcase evaluation trade-offs *(Epic:
  [[Epic] Investigate BeeWare Briefcase for Native Standalone Binary & Console Application Distribution](https://github.com/bdperkin/findfmt/issues/301)
  | Milestone: v1.6.0)*
- [ ] **[#374](https://github.com/bdperkin/findfmt/issues/374)** - [CLI] v2.0: Reserve -h short flag
  exclusively for --help and deprecate for --human-readable *(Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)*
- [ ] **[#375](https://github.com/bdperkin/findfmt/issues/375)** - [CLI] v2.0: Rename
  double-negative --nolinks/--no-nolinks to positive --links/--no-links flag *(Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)*
- [ ] **[#376](https://github.com/bdperkin/findfmt/issues/376)** - [CLI] v2.0: Disambiguate -v and
  -V CLI flags with distinct semantics *(Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)*
- [ ] **[#377](https://github.com/bdperkin/findfmt/issues/377)** - [Core] v2.0: Remove deprecated
  top-level main\_\* entry points and _ helper exports from findfmt package root *(Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)*
- [ ] **[#378](https://github.com/bdperkin/findfmt/issues/378)** - [CLI] v2.0: Replace
  argv-rewriting console script wrappers with dedicated Click command entry points *(Epic:
  [[Epic] v2.0 Breaking CLI Cleanups (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing)](https://github.com/bdperkin/findfmt/issues/350)
  | Milestone: v1.6.1)*

______________________________________________________________________

## 3. Active Umbrella Epics

Note: Architectural initiatives tracking decomposed subtasks.

- [ ] **[#197](https://github.com/bdperkin/findfmt/issues/197)** - [Epic] Add Language Support:
  Germanic (~1.83 Billion) *(Milestone: Future Features)*
- [ ] **[#198](https://github.com/bdperkin/findfmt/issues/198)** - [Epic] Add Language Support:
  Sino-Tibetan (~1.42 Billion) *(Milestone: Future Features)*
- [ ] **[#199](https://github.com/bdperkin/findfmt/issues/199)** - [Epic] Add Language Support:
  Indo-Aryan (~1.39 Billion) *(Milestone: Future Features)*
- [ ] **[#200](https://github.com/bdperkin/findfmt/issues/200)** - [Epic] Add Language Support:
  Romance (~1.25 Billion) *(Milestone: Future Features)*
- [ ] **[#201](https://github.com/bdperkin/findfmt/issues/201)** - [Epic] Add Language Support:
  Afroasiatic (~480 Million) *(Milestone: Future Features)*
- [ ] **[#202](https://github.com/bdperkin/findfmt/issues/202)** - [Epic] Add Language Support:
  Slavic (~415 Million) *(Milestone: Future Features)*
- [ ] **[#203](https://github.com/bdperkin/findfmt/issues/203)** - [Epic] Add Language Support:
  Austronesian (~295 Million) *(Milestone: Future Features)*
- [ ] **[#204](https://github.com/bdperkin/findfmt/issues/204)** - [Epic] Add Language Support:
  Dravidian (~270 Million) *(Milestone: Future Features)*
- [ ] **[#205](https://github.com/bdperkin/findfmt/issues/205)** - [Epic] Add Language Support:
  Japonic & Koreanic (~205 Million) *(Milestone: Future Features)*
- [ ] **[#206](https://github.com/bdperkin/findfmt/issues/206)** - [Epic] Add Language Support:
  Niger–Congo (~210 Million) *(Milestone: Future Features)*
- [ ] **[#207](https://github.com/bdperkin/findfmt/issues/207)** - [Epic] Add Language Support:
  Turkic (~165 Million) *(Milestone: Future Features)*
- [ ] **[#208](https://github.com/bdperkin/findfmt/issues/208)** - [Epic] Add Language Support:
  Other Indo-European (~124 Million) *(Milestone: Future Features)*
- [ ] **[#209](https://github.com/bdperkin/findfmt/issues/209)** - [Epic] Add Language Support:
  Uralic (~18 Million) *(Milestone: Future Features)*
- [ ] **[#210](https://github.com/bdperkin/findfmt/issues/210)** - [Epic] Add Language Support:
  Hellenic (~13 Million) *(Milestone: Future Features)*
- [ ] **[#211](https://github.com/bdperkin/findfmt/issues/211)** - [Epic] Add Language Support: All
  Other (~200 Million) *(Milestone: Future Features)*
- [ ] **[#212](https://github.com/bdperkin/findfmt/issues/212)** - [Epic] Add Language Support:
  Constructive & Artificial (~2 Million) *(Milestone: Future Features)*
- [ ] **[#213](https://github.com/bdperkin/findfmt/issues/213)** - [Epic] Add Language Support:
  Extinct (0 Living Speakers) *(Milestone: Future Features)*
- [ ] **[#276](https://github.com/bdperkin/findfmt/issues/276)** - [Epic] Infrastructure &
  Architecture Issues *(Milestone: Future Features)*
- [ ] **[#301](https://github.com/bdperkin/findfmt/issues/301)** - [Epic] Investigate BeeWare
  Briefcase for Native Standalone Binary & Console Application Distribution *(Milestone: Future
  Features)*
- [ ] **[#308](https://github.com/bdperkin/findfmt/issues/308)** - [Epic] Investigate Open-Source
  Python AI Translators & Automation for GNU gettext .po Files *(Milestone: Future Features)*
- [ ] **[#336](https://github.com/bdperkin/findfmt/issues/336)** - [Epic] Traversal Engine
  Stability: Unicode Sorting, Scandir Leak Prevention, and Deep Tree Recursion Safety *(Milestone:
  Future Features)*
- [x] **[#338](https://github.com/bdperkin/findfmt/issues/338)** - [Epic] Security Hardening:
  Terminal Sanitization, ReDoS Prevention, and Filesystem FIFO Safety *(Milestone: v1.0.2)*
- [ ] **[#344](https://github.com/bdperkin/findfmt/issues/344)** - [Epic] CI Pipeline Determinism,
  Packaging Smoke Tests, and Tooling Alignment *(Milestone: Future Features)*
- [ ] **[#346](https://github.com/bdperkin/findfmt/issues/346)** - [Epic] CLI Documentation
  Accuracy, Dynamic --help-all Generation, and Option Validation *(Milestone: Future Features)*
- [ ] **[#347](https://github.com/bdperkin/findfmt/issues/347)** - [Epic] CLI Exit Code Contract,
  Status Code Flags, and Atomic Output Writing *(Milestone: Future Features)*
- [ ] **[#348](https://github.com/bdperkin/findfmt/issues/348)** - [Epic] Core Refactoring & API
  Hygiene Cleanup *(Milestone: Future Features)*
- [ ] **[#350](https://github.com/bdperkin/findfmt/issues/350)** - [Epic] v2.0 Breaking CLI Cleanups
  (-h, --nolinks, -v/-V, top-level re-exports, wrapper parsing) *(Milestone: Future Features)*
- [ ] **[#379](https://github.com/bdperkin/findfmt/issues/379)** - [Epic] Documentation
  Architecture, Sphinx Navigation & Project Branding *(Milestone: Future Features)*
- [ ] **[#380](https://github.com/bdperkin/findfmt/issues/380)** - [Epic] Developer Tooling, Static
  Analysis & Linting Standardization *(Milestone: Future Features)*
- [ ] **[#381](https://github.com/bdperkin/findfmt/issues/381)** - [Epic] Configuration
  Architecture: Layered Precedence, Schemas & Validation Diagnostics *(Milestone: Future Features)*
- [ ] **[#382](https://github.com/bdperkin/findfmt/issues/382)** - [Epic] Pluggable Content
  Classification Engines & MIME Inspection Backends *(Milestone: Future Features)*
- [ ] **[#383](https://github.com/bdperkin/findfmt/issues/383)** - [Epic] Directory Traversal
  Robustness, Symlink Safety & Ignore Rule Parity *(Milestone: Future Features)*
- [ ] **[#384](https://github.com/bdperkin/findfmt/issues/384)** - [Epic] Formatter Integrity:
  Encoding Robustness, Stream Sanitization & Format Parity *(Milestone: Future Features)*
- [ ] **[#385](https://github.com/bdperkin/findfmt/issues/385)** - [Epic] Packaging Integrity,
  Release Automation & Dependency Verification *(Milestone: Future Features)*
- [ ] **[#386](https://github.com/bdperkin/findfmt/issues/386)** - [Epic] CLI Architecture, Terminal
  Interactivity & Execution Ergonomics *(Milestone: Future Features)*
- [ ] **[#425](https://github.com/bdperkin/findfmt/issues/425)** - [Epic] Exhaustive Dependency
  Resolution Matrix Testing via uv in CI and Tooling *(Milestone: Future Features)*
