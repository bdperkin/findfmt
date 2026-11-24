# Hybrid Python-Rust Architecture & Fallback FAQ

This document describes the hybrid Python-Rust architecture introduced across Milestone `v1.4.0` (Epic
[#576](https://github.com/bdperkin/findfmt/issues/576), Issues
[#577](https://github.com/bdperkin/findfmt/issues/577)–[#580](https://github.com/bdperkin/findfmt/issues/580))
and Milestone `v1.4.1` (Epic [#581](https://github.com/bdperkin/findfmt/issues/581), Issues
[#582](https://github.com/bdperkin/findfmt/issues/582)–[#586](https://github.com/bdperkin/findfmt/issues/586)),
including the native traversal and classification engines, runtime dispatch gateway, pure-Python fallback
guarantees, build and environment switches, parity verification, and contributor workflows.

______________________________________________________________________

## 1. Architectural Motivation & Subsystem Layout

Directory traversal, hierarchical `.gitignore` evaluation, shebang extraction, and magic-byte header
inspection execute once per candidate filesystem entry. On large monorepos containing tens of thousands of
files, Python object allocation and per-file I/O overhead dominate total wall-clock execution time. At the
same time, `findfmt`'s command-line interface (`Typer` and `Rich`), 14 structured and visual output
serializers, layered TOML/environment configuration, and GNU `gettext` localization benefit directly from
Python's library ecosystem and PEP 561 static typing.

To combine native I/O throughput with zero-regression portability, `findfmt` separates native acceleration,
runtime dispatch, and pure-Python fallback across four explicit layers:

| Component                       | Path                                                                  | Responsibility                                                                                                                                                   |
| :------------------------------ | :-------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **PyO3 Native Crate**           | `findfmt_rs/` (`Cargo.toml`, `src/lib.rs`, `deny.toml`, `about.toml`) | Rust 2024 edition (`>=1.88`) library (`cdylib` + `rlib`) compiled to `findfmt._rust_ext` with PyO3 `abi3-py311` stable ABI compatibility across Python `3.11+`.  |
| **PEP 484 Type Stub**           | `src/findfmt/_rust_ext.pyi`                                           | Declares static call signatures for symbols exported by `findfmt._rust_ext` so `ty` verifies Python-to-Rust call sites without runtime introspection.            |
| **Runtime Dispatch Gateway**    | `src/findfmt/core.py`                                                 | Loads `findfmt._rust_ext` (unless disabled via `FINDFMT_NO_EXTENSIONS`), inspects usable entrypoints, and wraps calls in `pyo3_runtime.PanicException` recovery. |
| **Pure-Python Fallback Engine** | `src/findfmt/_fallback.py`                                            | Re-exports pure-Python `find_files` (`src/findfmt/traversal/engine.py`) and `classify_file` (`src/findfmt/classifier.py`) with 100% behavioral parity.           |

______________________________________________________________________

## 2. Build-Time vs. Runtime Controls

`findfmt` provides independent controls for package builders (`HATCH_MATURIN_DISABLE`) and end users or test
suites (`FINDFMT_NO_EXTENSIONS`):

| Variable                | Phase                                 | Accepted Enabling Values                    | Effect                                                                                                                                                                        |
| :---------------------- | :------------------------------------ | :------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HATCH_MATURIN_DISABLE` | Package build (`uv build`, Hatchling) | `1`, `true`, `yes`, `on` (case-insensitive) | Skips `MaturinBuildHook.initialize()` and `clean()` in `tools/hatch_build.py`, producing a Cargo-free `py3-none-any` wheel containing compiled `.mo` catalogs and `py.typed`. |
| `FINDFMT_NO_EXTENSIONS` | Runtime execution (CLI & Python API)  | `1`, `true`, `yes`, `on` (case-insensitive) | Skips importing or dispatching to `findfmt._rust_ext` in `src/findfmt/core.py`, routing all operations to `src/findfmt/_fallback.py`.                                         |

### 2.1. Runtime Inspection API & CLI Diagnostics

Callers can inspect extension availability and execution-backend selection from both the CLI and Python:

- **CLI Diagnostics**: `findfmt --diagnostics` (and `findfmt --version --verbose`) prints `Backend: rust` when
  native gateway entrypoints are active or `Backend: python` when running via `src/findfmt/_fallback.py`.
- **`findfmt.is_rust_extension_loaded() -> bool`**: Returns `True` when `findfmt._rust_ext` imported cleanly
  and `FINDFMT_NO_EXTENSIONS` is not enabled.
- **`findfmt.is_rust_backend_active() -> bool`**: Returns `True` when `findfmt._rust_ext` is enabled and
  exposes callable gateway entrypoints (`find_files` or `classify_file`).
- **`findfmt.get_active_backend() -> Literal["rust", "python"]`**: Returns `"rust"` when
  `is_rust_backend_active()` is `True`, or `"python"` otherwise.

______________________________________________________________________

## 3. Architecture & Fallback FAQ

### 3.1. What happens if no prebuilt binary wheel exists for a target platform?

`findfmt` remains 100% functional on every Python `>=3.11` platform. Once installed from a pure-Python wheel
or on an architecture without `findfmt._rust_ext`, `src/findfmt/core.py` catches `ImportError` during
initialization and delegates all `find_files()` and `classify_file()` calls to `src/findfmt/_fallback.py` with
zero user intervention. Note that runtime fallback applies after installation succeeds: building from source
without a matching prebuilt wheel runs the Maturin build hook and requires Cargo by default. In environments
without Cargo, set `HATCH_MATURIN_DISABLE=1` before building or installing to produce the pure-Python package.

### 3.2. Why does `findfmt_rs` use PyO3 `abi3-py311`?

Enabling `abi3-py311` targets CPython's Stable Limited API for Python `3.11` and newer. A single compiled
wheel per OS/architecture (`cp311-abi3-*`) installs and runs across Python `3.11`, `3.12`, `3.13`, `3.14`, and
`3.15+` without recompiling separate binaries per minor interpreter release.

### 3.3. What happens if native Rust code panics during execution?

PyO3 converts Rust thread panics across FFI boundaries into `pyo3_runtime.PanicException`, which inherits
directly from Python's `BaseException` (alongside `SystemExit` and `KeyboardInterrupt`). Both
`classify_file()` and `find_files()` in `src/findfmt/core.py` intercept `pyo3_runtime.PanicException` while
allowing all non-panic `BaseException` and `Exception` subclasses to propagate normally. During `find_files()`
iteration, already-emitted `(path, relative_path)` occurrences are tracked with a multiplicity counter so
fallback replay through `src/findfmt/_fallback.py` neither duplicates delivered records nor drops distinct
entries from overlapping search roots.

### 3.4. How is MIT license compliance enforced across Rust crate dependencies?

Binary wheels bundle compiled code from `findfmt_rs` and its transitive Cargo dependencies. Every crate in
`findfmt_rs/Cargo.lock` is audited by `cargo-deny` (`findfmt_rs/deny.toml`) to permit only OSI-approved
permissive licenses (`MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`, `Unicode-3.0`, `Zlib`), and full
third-party attribution notices are generated into `THIRD_PARTY_LICENSES.md` via `cargo-about` and packaged
under `.dist-info/licenses/`.

______________________________________________________________________

## 4. Local Developer Setup & Debugging Runbook

Install `uv` alongside a stable Rust `>=1.88` toolchain via [`rustup`](https://rustup.rs/):

```bash
# Install Rust stable toolchain and static analysis components
rustup toolchain install stable
rustup component add rustfmt clippy

# Sync Python dependency groups and compile the editable findfmt._rust_ext module
uv sync --all-groups

# Fast incremental rebuild during Rust edits in findfmt_rs/
uv run maturin develop --manifest-path findfmt_rs/Cargo.toml

# Execute standalone Rust unit tests via the rlib crate target
cargo test --manifest-path findfmt_rs/Cargo.toml --no-default-features

# Compare native and pure-Python fallback test runs with panic backtraces enabled
RUST_BACKTRACE=1 uv run pytest
FINDFMT_NO_EXTENSIONS=1 uv run pytest

# Compare Rust vs. pure-Python throughput and memory in isolated subprocesses
uv run python tools/benchmark.py --backend compare --tier medium --runs 3 --warmup 1
```

______________________________________________________________________

## 5. Native Engine Capabilities, Parity & Fuzzing Verification

Milestone `v1.4.1` delivers the complete native execution pipeline in `findfmt_rs`
(`#![forbid(unsafe_code)]`):

- **Streaming Directory Walker (`find_files_rs` / `find_files`)**: Executes recursive traversal in Rust while
  releasing the Python `GIL` (`py.detach`). Supports hierarchical `.gitignore`, `.git/info/exclude` (including
  submodules and linked worktree `commondir` pointers), global ignore files, `--gitignore-file`, linear-time
  PEP 383 `surrogateescape` glob evaluation (`-P`, `-I`, `--ignore-case`, `--match-dirs`), depth and entry
  boundaries (`-L`, `--filelimit`), single-filesystem confinement (`-x`), symlink cycle detection (`-l`),
  resumable `--prune` discovery, `--du` disk-usage accumulation, and deterministic natural version sorting.
- **File Classification (`classify_file_rs` / `classify_file` / `classify_batch_rs`)**: Opens regular files in
  `O_NONBLOCK` mode with `fstat` regular-file verification to prevent hangs on swapped `FIFO` pipes, extracts
  `#!` shebang tokens (including `env -S` and multiline `nix-shell -i` headers), sniffs text vs. binary magic
  bytes, and resolves `identify` format and `MIME` tags without holding the `GIL`.
- **Parity, Property Testing & Continuous Fuzzing**: `tests/test_parity.py` asserts 100% field-by-field
  `FileInfo` identity between `findfmt._rust_ext` and `src/findfmt/_fallback.py`. Property-based `proptest`
  suites (`findfmt_rs/tests/`), `cargo-fuzz` targets (`findfmt_rs/fuzz/`), and `ClusterFuzzLite` harnesses
  (`tests/fuzz/`) continuously stress-test arbitrary path bytes, malformed globs, shebang headers, and binary
  buffers against panics and memory leaks.
