# Security Policy

## 1. Supported Versions

Only the latest release of `findfmt` is actively supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| < 0.3.0 | :x:                |

## 2. Reporting a Vulnerability

We take the security of `findfmt` seriously. If you discover a security vulnerability:

1. **Private Vulnerability Reporting**: Please submit a report through
   [GitHub Private Vulnerability Reporting](https://github.com/bdperkin/findfmt/security/advisories/new).
2. **Email**: If you are unable to use GitHub Advisories, email `bdperkin@gmail.com` with the
   subject `[SECURITY] findfmt vulnerability report`.

Please include:

- A description of the issue and potential impact.
- Steps to reproduce or proof-of-concept code.
- Any suggested fixes or mitigations.

We will acknowledge receipt within 48 hours and work with you to coordinate a disclosure and patch
release.

______________________________________________________________________

## 3. Security Threat Model & Audit Report

This section documents the formal security architecture, threat vectors analyzed, and defensive
mitigations implemented in `findfmt`.

### 3.1. Filesystem Traversal & Path Security

#### 3.1.1. Symlink Loops & Resource Exhaustion (DoS)

- **Threat Vector**: Malicious or accidental recursive symbolic directory structures (e.g.,
  `dir/loop -> dir`) can cause unbounded recursion, stack overflow (`RecursionError`), or heap
  exhaustion during deep filesystem traversal.
- **Mitigation**: When `--follow-symlinks` (`-L`) is active, `findfmt` tracks canonical directory
  paths via `visited_dirs: set[Path]` initialized with the resolved traversal root. Each candidate
  subdirectory's canonical target (`subdir.resolve()`) is checked prior to descent. If already
  visited, traversal immediately skips the entry, breaking cyclic graphs and avoiding duplicate
  processing.

#### 3.1.2. Arbitrary Path Traversal & Boundary Containment

- **Threat Vector**: Ingested paths or nested `.gitignore` files could attempt directory traversal
  outside intended directory boundaries (e.g., path traversal sequences `../../`).
- **Mitigation**: All path comparisons and exclude rules verify boundary alignment using
  `entry_path.is_relative_to(base_dir)` and `_resolve_relative`. Path operations are scoped strictly
  within configured root paths.

#### 3.1.3. TOCTOU (Time-of-Check to Time-of-Use) Resiliency

- **Threat Vector**: Asynchronous filesystem modifications occurring between directory scanning and
  file inspection (e.g., a file is deleted, renamed, or unlinked) could raise uncaught filesystem
  exceptions.
- **Mitigation**: All stat, scan, and read operations in `traversal.py` and `classifier.py` are
  resiliently wrapped in guarded exception blocks (`OSError`, `ValueError`). Inaccessible or
  vanished entries are safely skipped or fall back to metadata defaults without crashing the runtime
  engine.

### 3.2. File Inspection & Content Engine Security

#### 3.2.1. Bounded Content Reads

- **Threat Vector**: Reading untrusted, multi-gigabyte or stream-backed files into memory to inspect
  shebangs or content signatures can trigger out-of-memory (OOM) denial-of-service conditions.
- **Mitigation**: Content inspection in `classifier.py` never reads entire files. Interpreter
  shebang extraction strictly reads a bounded buffer chunk of at most 512 bytes (`f.readline(512)`).
  Filename identification heuristics bypass disk reads entirely for known file types.

#### 3.2.2. Special Files & Device Nodes

- **Threat Vector**: Encountering named pipes (FIFOs), character devices (`/dev/random`,
  `/dev/zero`), UNIX domain sockets, or block devices could block execution indefinitely on read
  calls without an active writer.
- **Mitigation**: Directory scanning inspects directory entries using `os.DirEntry.is_file()` and
  `os.DirEntry.is_dir()`, which evaluate to `False` for FIFOs, device nodes, and sockets.
  Additionally, `extract_shebang` and `classify_file` explicitly check `path.is_file()` prior to
  opening any file descriptor, guaranteeing that `findfmt` never blocks on unwritten FIFOs or
  unbounded device streams.

#### 3.2.3. Regular Expression & Pattern Safety (ReDoS)

- **Threat Vector**: User-supplied glob patterns or complex `.gitignore` rules could induce
  exponential backtracking in regular expression engines.
- **Mitigation**: `findfmt` utilizes `pathspec` to compile `.gitignore` rules into linear-time
  matching automata, mitigating catastrophic backtracking risks.

### 3.3. Terminal Presentation & Injection Attacks (CWE-150)

#### 3.3.1. ANSI Escape Sequence Injection

- **Threat Vector**: Files named with terminal control characters or ANSI escape sequences (e.g.,
  `\033[2J`, carriage returns, bell codes) can manipulate terminal state, clear history, or spoof
  command output when rendered to an interactive terminal emulator.
- **Mitigation**: `findfmt` provides `-0` / `--print0` to delimit paths with NUL (`\0`) bytes,
  ensuring safe ingestion by downstream tools such as `xargs -0` without word splitting or shell
  expansion. Quoting and sanitization features (`-q` / `--quote`) are tracked on the roadmap (#20
  and #22).

### 3.4. Supply Chain & Dependency Hygiene

#### 3.4.1. Automated Vulnerability Audits

- **Threat Vector**: Known Common Vulnerabilities and Exposures (CVEs) in transitive dependencies
  could introduce vulnerabilities into the toolchain.
- **Mitigation**: Continuous dependency vulnerability scanning is integrated into the primary
  verification quality gate via `uv audit --preview-features audit-command`, cross-referencing all
  91 resolved dependencies against the Python Packaging Advisory Database.

#### 3.4.2. Absence of Dangerous Shell Executions

- **Threat Vector**: Executing untrusted system commands or shells (`os.system`, `shell=True`) can
  lead to command injection.
- **Mitigation**: The `findfmt` runtime contains zero invocations of `os.system` or shell-based
  subprocesses. All path operations and traversals are conducted strictly via Python's standard `os`
  and `pathlib` primitives.

### 3.5. GitHub Actions & CI/CD Hardening

#### 3.5.1. Principle of Least Privilege

- **Threat Vector**: Over-permissioned GitHub Actions tokens can allow compromised dependencies or
  scripts to modify repositories, create tags, or access secrets.
- **Mitigation**: All GitHub Actions workflows configure default `permissions: contents: read`.
  Elevated permissions (such as `id-token: write`) are strictly confined to release jobs utilizing
  ephemeral OpenID Connect (OIDC) tokens for PyPI Trusted Publishing.

#### 3.5.2. OIDC Trusted Publisher Environment Scoping

- **Threat Vector**: Unconstrained OIDC trusted publishers allow workflows executing from arbitrary
  environments or untrusted branches to mint PyPI and TestPyPI release tokens.
- **Mitigation**: OpenID Connect (OIDC) trusted publishers on PyPI and TestPyPI are strictly
  constrained to dedicated GitHub environments (`pypi` and `testpypi`). Only release workflows
  explicitly associated with these environments in `.github/workflows/release.yml` can mint
  short-lived publication tokens, eliminating ambient privilege and scoping credentials to verified
  release jobs.

#### 3.5.3. Multi-Tier Secret Scanning & Static Analysis

- **Threat Vector**: Accidental inclusion of API keys, private certificates, or credentials in git
  history.
- **Mitigation**: Every commit and pull request is verified against `detect-secrets`,
  `detect-private-key`, `GitGuardian` (`.gitguardian.yaml`), and GitHub CodeQL semantic analysis.

### 3.6. Supply Chain Governance & OpenSSF Scorecard Posture

#### 3.6.1. Branch Protection & Mandatory Code Review (CodeReviewID)

- **Threat Vector**: Unreviewed, malicious, or erroneous commits pushed directly to primary release
  branches bypass automated verification gates.
- **Mitigation**: Direct pushes to `main` are strictly blocked using GitHub branch protection rules
  enforced for all users including administrators (`enforce_admins: true`). Every change requires a
  feature branch and a Pull Request. All CI matrix checks (multi-platform tests across Python
  3.10–3.14 on Linux, macOS, and Windows, 100% statement and branch coverage, strict static typing,
  and linters) must pass before a merge can occur. For solo maintainer development, changesets are
  audited and verified via isolated feature branches and squash-merged to preserve linear history;
  external contributions require mandatory maintainer code review and approval.

#### 3.6.2. OpenSSF Best Practices Program (CIIBestPracticesID)

- **Threat Vector**: Inconsistent open-source development and security practices.
- **Mitigation**: The `findfmt` project is enrolled in the OpenSSF Best Practices Program
  ([Project 15282](https://www.bestpractices.dev/projects/15282)). The project adheres to OpenSSF
  criteria including open-source licensing, cryptographic release tags, automated static analysis,
  vulnerability reporting procedures, and strict test coverage.

#### 3.6.3. Continuous Fuzz Testing Architecture & ClusterFuzzLite (FuzzingID)

- **Threat Vector**: Maliciously crafted inputs, corrupted file headers, truncated shebang
  sequences, or nested cyclic filesystem structures triggering unhandled edge cases or unexpected
  interpreter crashes.
- **Mitigation**: Continuous fuzz testing is actively deployed using Google's **ClusterFuzzLite**
  and **Atheris**:
  1. **Classification Engine Fuzzing** (`tests/fuzz/fuzz_classifier.py`): Continuous coverage-guided
     fuzz testing targeting `classify_file`, `extract_shebang`, and MIME signature heuristics with
     random byte sequences, corrupted headers, and synthetic files.
  2. **Traversal Engine Fuzzing** (`tests/fuzz/fuzz_traversal.py`): Automated fuzzing of complex
     directory trees with irregular permission bits, symlink hierarchies, `.gitignore` pathspec
     rules, and deep directory nestings to verify bounded traversal invariants.
  3. **Continuous CI Integration**: Deployed via `.clusterfuzzlite/` configuration and automated
     GitHub Actions workflow (`.github/workflows/cflite.yml` for scheduled batch and main-branch
     fuzzing), resolving OpenSSF Scorecard `FuzzingID`
     ([Code Scanning Alert #48](https://github.com/bdperkin/findfmt/security/code-scanning/48)).

#### 3.6.4. Active Maintenance & Release Hygiene (MaintainedID)

- **Threat Vector**: Abandoned dependencies or unmaintained libraries failing to address upstream
  security advisories.
- **Mitigation**: `findfmt` follows Semantic Versioning with automated multi-platform CI, scheduled
  weekly dependency security audits (`uv audit`), automated CodeQL scanning, and automated changelog
  generation via `git-cliff`.
