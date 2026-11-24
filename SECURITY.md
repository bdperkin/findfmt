# Security Policy

## 1. Supported Versions

Only the latest release of `findfmt` is actively supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.4.x   | :white_check_mark: |
| < 1.4.0 | :x:                |

## 2. Reporting a Vulnerability

We take the security of `findfmt` seriously. If you discover a security vulnerability:

1. **Private Vulnerability Reporting**: Please submit a report through
   [GitHub Private Vulnerability Reporting](https://github.com/bdperkin/findfmt/security/advisories/new).
2. **Email**: If you are unable to use GitHub Advisories, email `bdperkin@gmail.com` with the subject
   `[SECURITY] findfmt vulnerability report`.

Please include:

- A description of the issue and potential impact.
- Steps to reproduce or proof-of-concept code.
- Any suggested fixes or mitigations.

We will acknowledge receipt within 48 hours, provide an initial triage and severity assessment within 7 days,
and work with you to coordinate a patch release (targeting 14 days for Critical/High findings and 30–60 days
for Medium/Low findings) under a standard 90-day coordinated disclosure window.

______________________________________________________________________

## 3. Security Threat Model & Audit Report

This section documents the formal security architecture, threat vectors analyzed, and defensive mitigations
implemented across `findfmt`'s hybrid Python (`src/findfmt/`) and Rust (`findfmt_rs/`) engines.

### 3.1. Filesystem Traversal & Path Security

#### 3.1.1. Symlink Loops & Resource Exhaustion (DoS)

- **Threat Vector**: Malicious or accidental recursive symbolic directory structures (e.g., `dir/loop -> dir`)
  can cause unbounded recursion, stack overflow (`RecursionError`), or heap exhaustion during deep filesystem
  traversal.
- **Mitigation**: When `--follow-links` (`-l`) is active, the pure-Python walker tracks canonical directory
  paths (`visited_dirs: set[Path]`) and `(st_dev, st_ino)` ancestor keys, while `findfmt_rs` tracks physical
  directory identity (`DirKey` on POSIX and canonical file identifiers on Windows) across both active
  traversal and `--prune` descendant inspection, immediately skipping cyclic entries.

#### 3.1.2. Arbitrary Path Traversal & Boundary Containment

- **Threat Vector**: Ingested paths (via `--from-file`) or nested `.gitignore` files could attempt directory
  traversal outside intended directory boundaries (e.g., absolute paths `/etc/passwd`, path traversal
  sequences `../../`, or symlinks resolving outside the root).
- **Mitigation**: All path comparisons and exclude rules verify boundary alignment using
  `entry_path.is_relative_to(base_dir)` and `_resolve_relative`. For `--from-file` ingestion, `findfmt`
  enforces lexical and canonical (`Path.resolve()`) root confinement by default via `_is_within_root()`,
  skipping out-of-root entries with a warning to `stderr` before opening or inspecting file contents unless
  `--allow-outside-root` is explicitly enabled.

#### 3.1.3. TOCTOU (Time-of-Check to Time-of-Use) Resiliency & Native Boundary Safety

- **Threat Vector**: Asynchronous filesystem modifications occurring between directory scanning and file
  inspection (e.g., a file is deleted, renamed, or unlinked) could raise uncaught exceptions or trigger native
  extension panics across the FFI boundary.
- **Mitigation**: All stat, scan, and read operations in `src/findfmt/traversal/`,
  `src/findfmt/classifier.py`, and `findfmt_rs/` gracefully handle `OSError` / `std::io::Error` conditions.
  `findfmt_rs` enforces `#![forbid(unsafe_code)]` and
  `deny(clippy::unwrap_used, clippy::expect_used, clippy::panic)`, and `src/findfmt/core.py` catches
  `pyo3_runtime.PanicException` with automatic fallback to `src/findfmt/_fallback.py`.

### 3.2. File Inspection & Content Engine Security

#### 3.2.1. Bounded Content Reads

- **Threat Vector**: Reading untrusted, multi-gigabyte or stream-backed files into memory to inspect shebangs
  or content signatures can trigger out-of-memory (OOM) denial-of-service conditions.
- **Mitigation**: Content inspection never reads entire files. Both `classifier.py` (`_read_initial_buffer`)
  and `findfmt_rs/src/header.rs` (`MAX_HEADER_BYTES`) cap regular-file header inspection to a single bounded
  `2,048`-byte read (`512` bytes for standalone `extract_shebang` calls).

#### 3.2.2. Special Files, Named Pipes (FIFOs), & TOCTOU FIFO Swapping

- **Threat Vector**: Encountering named pipes (FIFOs), character devices (`/dev/random`, `/dev/zero`), UNIX
  domain sockets, or block devices could block execution indefinitely on read calls without an active writer.
  Furthermore, a TOCTOU race where a regular file is replaced with a named pipe between directory discovery
  and file inspection could cause the process to hang indefinitely waiting for a pipe writer.
- **Mitigation**: Directory scanning inspects directory entries using `os.DirEntry.is_file()` and
  `os.DirEntry.is_dir()` (and `FileType::is_file()` / `is_dir()` in `findfmt_rs`), which evaluate to `False`
  for FIFOs, device nodes, and sockets. On POSIX platforms where `O_NONBLOCK` is supported, `extract_shebang`,
  `classify_file`, and `findfmt_rs` open descriptors with `O_NONBLOCK | O_RDONLY` and verify regular-file mode
  (`S_ISREG`) via `fstat(fd)` before reading; on Windows (where `O_NONBLOCK` is unavailable), Python opens
  with `O_RDONLY | O_BINARY` followed by `os.fstat(fd)` `S_ISREG` checks, and `findfmt_rs` verifies
  regular-file metadata (`is_file()`) before reading any header bytes.

#### 3.2.3. Regular Expression & Pattern Safety (ReDoS Prevention)

- **Threat Vector**: User-supplied glob patterns, complex `.gitignore` rules, or crafted terminal escape
  sequences in filenames could induce exponential or quadratic backtracking in regular expression engines,
  causing Denial of Service (ReDoS).
- **Mitigation**: `findfmt` mitigates catastrophic backtracking through multi-layered defensive measures:
  1. Compiles `.gitignore` and CLI glob rules via `pathspec` in Python and a linear-time Thompson `NFA`
     automaton (`glob_nfa.rs` / `glob_u32.rs`) in `findfmt_rs`, eliminating exponential backtracking.
  2. Bounded linear-time regular expressions for ANSI CSI, OSC, and C1-OSC terminal escape sequences
     (`_ANSI_ESCAPE_RE` unified across `utils.strings`, `cli.terminal`, and `utils.hyperlinks`). The C1-OSC
     pattern eliminates nested quantified character classes, guaranteeing $O(N)$ linear-time sanitization even
     on repetitive control sequences (e.g., 50,000+ repetitive `\x9d` bytes).

### 3.3. Terminal Presentation & Injection Attacks (CWE-150)

#### 3.3.1. ANSI Escape Sequence Injection

- **Threat Vector**: Files named with terminal control characters or ANSI escape sequences (e.g., `\033[2J`,
  carriage returns, bell codes) can manipulate terminal state, clear history, or spoof command output when
  rendered to an interactive terminal emulator.
- **Mitigation**: `findfmt` provides `-0` / `--print0` to delimit paths with NUL (`\0`) bytes, ensuring safe
  ingestion by downstream tools such as `xargs -0` without word splitting or shell expansion. In addition,
  `-q` / `--hide-control-chars` masks control characters with `?` and `-Q` / `--quote-name` safely wraps paths
  in double quotes with backslash escaping to protect terminal emulators against control injection.

#### 3.3.2. Unicode Bidirectional (BiDi) Override Masking & Trojan Source Defense

- **Threat Vector**: Untrusted filenames containing Unicode bidirectional formatting controls (category `Cf`,
  including U+202E Right-to-Left Override, U+2066–U+2069 isolates, and U+200E/U+200F directional marks) can
  visually reverse filenames or extensions in terminal displays (Trojan Source attacks, e.g. displaying
  `payload.exe` visually as `payload_exe.png`).
- **Mitigation**: In interactive TTY display mode, `findfmt` automatically masks all Unicode `Cf`
  bidirectional control characters with `?` via `mask_control_characters()`, neutralizing visual reordering
  spoofing while preserving legitimate non-`Cf` right-to-left scripts (such as Arabic and Hebrew). When output
  is piped, or when literal modes (`-N` / `--literal` or `-0` / `--print0`) are explicitly requested, raw byte
  preservation is maintained for downstream pipeline interoperability.

### 3.4. Supply Chain & Dependency Hygiene

#### 3.4.1. Automated Vulnerability Audits

- **Threat Vector**: Known Common Vulnerabilities and Exposures (CVEs) in transitive dependencies could
  introduce vulnerabilities into the toolchain.
- **Mitigation**: Continuous Python dependency vulnerability scanning is integrated into the verification
  quality gate via `uv audit --preview-features audit-command` against the Python Packaging Advisory Database,
  paired with `cargo-deny` (`findfmt_rs/deny.toml`) `licenses`, `bans`, and `sources` checks and SHA-256
  `Cargo.lock` verification for native Rust crates (with automated RustSec advisory and yanked-crate gates
  tracked in [Issue #597](https://github.com/bdperkin/findfmt/issues/597)).

#### 3.4.2. Absence of Dangerous Shell Executions

- **Threat Vector**: Executing untrusted system commands or shells (`os.system`, `shell=True`) can lead to
  command injection.
- **Mitigation**: Both `src/findfmt/` and `findfmt_rs/` contain zero invocations of `os.system` or
  shell-evaluated subprocesses. Filesystem operations use Python `os`/`pathlib` and memory-safe Rust `std::fs`
  primitives; the sole external process lookup (`git config --get core.excludesFile` when no XDG global ignore
  file exists) executes an explicit argument vector (`shell=False` / `Command::new`) with
  `GIT_TERMINAL_PROMPT=0` and a bounded 2-second timeout.

### 3.5. GitHub Actions & CI/CD Hardening

#### 3.5.1. Principle of Least Privilege

- **Threat Vector**: Over-permissioned GitHub Actions tokens can allow compromised dependencies or scripts to
  modify repositories, create tags, or access secrets.
- **Mitigation**: All GitHub Actions workflows configure default `permissions: contents: read`. Elevated
  permissions (such as `id-token: write`) are strictly confined to release jobs utilizing ephemeral OpenID
  Connect (OIDC) tokens for PyPI Trusted Publishing and for signing the container image's provenance
  attestation.

#### 3.5.2. OIDC Trusted Publisher Environment Scoping

- **Threat Vector**: Unconstrained OIDC trusted publishers allow workflows executing from arbitrary
  environments or untrusted branches to mint PyPI and TestPyPI release tokens.
- **Mitigation**: OpenID Connect (OIDC) trusted publishers on PyPI and TestPyPI are strictly constrained to
  dedicated GitHub environments (`pypi` and `testpypi`). The two publish jobs in
  `.github/workflows/release.yml` each run in one of these environments. The only other job that requests
  `id-token: write` is the container job, which uses it to sign its build provenance attestation. It runs
  outside both environments, so its token cannot publish to PyPI. The environments' deployment policies only
  admit `v*.*.*` tags, so a workflow run from a branch cannot deploy to them or mint a publication token. The
  release workflow also fails unless it runs on the requested tag and the built version matches it.

#### 3.5.3. Container Image Provenance

- **Threat Vector**: A container image built separately from the release could carry different code or
  dependencies than the published package, or ship build tooling that widens its attack surface.
- **Mitigation**: The release image installs the exact wheel published to PyPI, with dependencies at the
  versions pinned in `uv.lock`, into a virtual environment. The runtime stage copies only that environment, so
  the image contains no `uv` or build tooling, and it runs as an unprivileged user. The release workflow
  checks that the image reports the release version before pushing it, then publishes an SBOM, build
  provenance, and a signed attestation, which `gh attestation verify` checks:
  ```bash
  gh attestation verify oci://ghcr.io/bdperkin/findfmt:1.4.1 --owner bdperkin
  ```

#### 3.5.4. Multi-Tier Secret Scanning & Static Analysis

- **Threat Vector**: Accidental inclusion of API keys, private certificates, or credentials in git history.
- **Mitigation**: Every commit and pull request is verified against `detect-secrets`, `detect-private-key`,
  `GitGuardian` (`.gitguardian.yaml`), and GitHub CodeQL semantic analysis.

### 3.6. Supply Chain Governance & OpenSSF Scorecard Posture

#### 3.6.1. Branch Protection & Mandatory Code Review (CodeReviewID)

- **Threat Vector**: Unreviewed, malicious, or erroneous commits pushed directly to primary release branches
  bypass automated verification gates.
- **Mitigation**: Direct pushes to `main` are strictly blocked using GitHub branch protection rules enforced
  for all users including administrators (`enforce_admins: true`). Every change requires a feature branch and
  a Pull Request. All CI matrix checks (multi-platform tests across Python 3.11–3.15 on Linux, macOS, and
  Windows, 100% statement and branch coverage, strict static typing, and linters) must pass before a merge can
  occur. For solo maintainer development, changesets are audited and verified via isolated feature branches
  and squash-merged to preserve linear history; external contributions require mandatory maintainer code
  review and approval.

#### 3.6.2. OpenSSF Best Practices Program (CIIBestPracticesID)

- **Threat Vector**: Inconsistent open-source development and security practices.
- **Mitigation**: The `findfmt` project is enrolled in the OpenSSF Best Practices Program
  ([Project 15282](https://www.bestpractices.dev/projects/15282)). The project adheres to OpenSSF criteria
  including open-source licensing, cryptographic release tags, automated static analysis, vulnerability
  reporting procedures, and strict test coverage.

#### 3.6.3. Continuous Fuzz Testing Architecture & ClusterFuzzLite (FuzzingID)

- **Threat Vector**: Maliciously crafted inputs, corrupted file headers, truncated shebang sequences, or
  nested cyclic filesystem structures triggering unhandled edge cases, panics, or unexpected crashes.
- **Mitigation**: Continuous fuzz and property-based testing spans both the Python and Rust engines:
  1. **Classification & Traversal Fuzzing** (`tests/fuzz/fuzz_classifier.py`, `tests/fuzz/fuzz_traversal.py`):
     Coverage-guided **Atheris** harnesses bundled with the compiled `findfmt._rust_ext` extension under
     **ClusterFuzzLite** (`address` sanitizer on the Atheris Python runtime, while the stable `abi3` Rust
     wheel builds without sanitizer flags and relies on `cargo-fuzz` for native Rust instrumentation).
  2. **Rust Property & `libFuzzer` Suites** (`findfmt_rs/tests/`, `findfmt_rs/fuzz/`): Deterministic
     `proptest` suites and `cargo-fuzz` targets stress-testing arbitrary byte slices across shebang
     extraction, magic-byte sniffing, natural version sort keys, `.gitignore` glob automata, and synthetic
     directory trees.
  3. **Continuous CI Integration**: Deployed via SHA-256 digest-pinned `.clusterfuzzlite/` builders and
     `.github/workflows/cflite.yml`, resolving OpenSSF Scorecard `FuzzingID`
     ([Code Scanning Alert #48](https://github.com/bdperkin/findfmt/security/code-scanning/48)).

#### 3.6.4. Active Maintenance & Release Hygiene (MaintainedID)

- **Threat Vector**: Abandoned dependencies or unmaintained libraries failing to address upstream security
  advisories.
- **Mitigation**: `findfmt` follows Semantic Versioning with automated multi-platform CI, scheduled weekly
  dependency security audits (`uv audit`), automated CodeQL scanning, and a curated changelog whose section
  for each version becomes that release's GitHub Release notes.

#### 3.6.5. Third-Party Rust Crate License & Source Auditing

- **Threat Vector**: Copyleft or unapproved transitive Rust crates, wildcard version specifiers, or unverified
  git/registry sources entering native PyO3 binary wheels (`findfmt_rs`).
- **Mitigation**: `findfmt_rs/deny.toml` enforces [`cargo-deny`](https://github.com/EmbarkStudios/cargo-deny)
  policy checks (`cargo deny --manifest-path findfmt_rs/Cargo.toml check licenses bans sources`) permitting
  only OSI-approved permissive SPDX licenses (`MIT`, `Apache-2.0`, `Apache-2.0 WITH LLVM-exception`,
  `BSD-2-Clause`, `BSD-3-Clause`, `Unicode-3.0`, and `Zlib`), rejecting duplicate or wildcard crate versions,
  and restricting crate sources exclusively to `crates.io`. Complete third-party crate license texts and
  copyright attributions are deterministically generated via
  [`cargo-about`](https://github.com/EmbarkStudios/cargo-about) (`findfmt_rs/about.toml` and
  `findfmt_rs/about.hbs`) into `THIRD_PARTY_LICENSES.md` and bundled alongside `LICENSE` in wheel
  `.dist-info/licenses/` metadata (`project.license-files` in `pyproject.toml`).
