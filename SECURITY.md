# Security Policy

## Supported Versions

Only the latest release of `findfmt` is actively supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

## Reporting a Vulnerability

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

## Security Threat Model & Audit Report

This section documents the formal security architecture, threat vectors analyzed, and defensive
mitigations implemented in `findfmt`.

### 1. Filesystem Traversal & Path Security

#### Symlink Loops & Resource Exhaustion (DoS)

- **Threat Vector**: Malicious or accidental recursive symbolic directory structures (e.g.,
  `dir/loop -> dir`) can cause unbounded recursion, stack overflow (`RecursionError`), or heap
  exhaustion during deep filesystem traversal.
- **Mitigation**: When `--follow-symlinks` (`-L`) is active, `findfmt` tracks canonical directory
  paths via `visited_dirs: set[Path]` initialized with the resolved traversal root. Each candidate
  subdirectory's canonical target (`subdir.resolve()`) is checked prior to descent. If already
  visited, traversal immediately skips the entry, breaking cyclic graphs and avoiding duplicate
  processing.

#### Arbitrary Path Traversal & Boundary Containment

- **Threat Vector**: Ingested paths or nested `.gitignore` files could attempt directory traversal
  outside intended directory boundaries (e.g., path traversal sequences `../../`).
- **Mitigation**: All path comparisons and exclude rules verify boundary alignment using
  `entry_path.is_relative_to(base_dir)` and `_resolve_relative`. Path operations are scoped strictly
  within configured root paths.

#### TOCTOU (Time-of-Check to Time-of-Use) Resiliency

- **Threat Vector**: Asynchronous filesystem modifications occurring between directory scanning and
  file inspection (e.g., a file is deleted, renamed, or unlinked) could raise uncaught filesystem
  exceptions.
- **Mitigation**: All stat, scan, and read operations in `traversal.py` and `classifier.py` are
  resiliently wrapped in guarded exception blocks (`OSError`, `ValueError`). Inaccessible or
  vanished entries are safely skipped or fall back to metadata defaults without crashing the runtime
  engine.

### 2. File Inspection & Content Engine Security

#### Bounded Content Reads

- **Threat Vector**: Reading untrusted, multi-gigabyte or stream-backed files into memory to inspect
  shebangs or content signatures can trigger out-of-memory (OOM) denial-of-service conditions.
- **Mitigation**: Content inspection in `classifier.py` never reads entire files. Interpreter
  shebang extraction strictly reads a bounded buffer chunk of at most 512 bytes (`f.readline(512)`).
  Filename identification heuristics bypass disk reads entirely for known file types.

#### Special Files & Device Nodes

- **Threat Vector**: Encountering named pipes (FIFOs), character devices (`/dev/random`,
  `/dev/zero`), UNIX domain sockets, or block devices could block execution indefinitely on read
  calls without an active writer.
- **Mitigation**: Directory scanning inspects directory entries using `os.DirEntry.is_file()` and
  `os.DirEntry.is_dir()`, which evaluate to `False` for FIFOs, device nodes, and sockets.
  Additionally, `extract_shebang` and `classify_file` explicitly check `path.is_file()` prior to
  opening any file descriptor, guaranteeing that `findfmt` never blocks on unwritten FIFOs or
  unbounded device streams.

#### Regular Expression & Pattern Safety (ReDoS)

- **Threat Vector**: User-supplied glob patterns or complex `.gitignore` rules could induce
  exponential backtracking in regular expression engines.
- **Mitigation**: `findfmt` utilizes `pathspec` to compile `.gitignore` rules into linear-time
  matching automata, mitigating catastrophic backtracking risks.

### 3. Terminal Presentation & Injection Attacks (CWE-150)

#### ANSI Escape Sequence Injection

- **Threat Vector**: Files named with terminal control characters or ANSI escape sequences (e.g.,
  `\033[2J`, carriage returns, bell codes) can manipulate terminal state, clear history, or spoof
  command output when rendered to an interactive terminal emulator.
- **Mitigation**: `findfmt` provides `-0` / `--print0` to delimit paths with NUL (`\0`) bytes,
  ensuring safe ingestion by downstream tools such as `xargs -0` without word splitting or shell
  expansion. Quoting and sanitization features (`-q` / `--quote`) are tracked on the roadmap (#20,
  #22).

### 4. Supply Chain & Dependency Hygiene

#### Automated Vulnerability Audits

- **Threat Vector**: Known Common Vulnerabilities and Exposures (CVEs) in transitive dependencies
  could introduce vulnerabilities into the toolchain.
- **Mitigation**: Continuous dependency vulnerability scanning is integrated into the primary
  verification quality gate via `uv audit --preview-features audit-command`, cross-referencing all
  91 resolved dependencies against the Python Packaging Advisory Database.

#### Absence of Dangerous Shell Executions

- **Threat Vector**: Executing untrusted system commands or shells (`os.system`, `shell=True`) can
  lead to command injection.
- **Mitigation**: The `findfmt` runtime contains zero invocations of `os.system` or shell-based
  subprocesses. All path operations and traversals are conducted strictly via Python's standard `os`
  and `pathlib` primitives.

### 5. GitHub Actions & CI/CD Hardening

#### Principle of Least Privilege

- **Threat Vector**: Over-permissioned GitHub Actions tokens can allow compromised dependencies or
  scripts to modify repositories, create tags, or access secrets.
- **Mitigation**: All GitHub Actions workflows configure default `permissions: contents: read`.
  Elevated permissions (such as `id-token: write`) are strictly confined to release jobs utilizing
  ephemeral OpenID Connect (OIDC) tokens for PyPI Trusted Publishing.

#### Multi-Tier Secret Scanning & Static Analysis

- **Threat Vector**: Accidental inclusion of API keys, private certificates, or credentials in git
  history.
- **Mitigation**: Every commit and pull request is verified against `detect-secrets`,
  `detect-private-key`, `GitGuardian` (`.gitguardian.yaml`), and GitHub CodeQL semantic analysis.
