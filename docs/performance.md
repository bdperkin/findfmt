# Performance Architecture & Benchmarks

This document outlines the performance characteristics, benchmarking architecture, and baseline
performance metrics for `findfmt`.

______________________________________________________________________

## 1. Performance Goals & Architecture

`findfmt` is engineered to deliver high-throughput filesystem traversal and intelligent content
classification across large codebases and monorepos (>100,000 files).

The performance model focuses on three primary metrics:

1. **Traversal Throughput (files/sec and dirs/sec)**: Maximizing file discovery and content
   inspection throughput across large repository hierarchies while pruning excluded trees early via
   `.gitignore` specifications.

2. **Latency to First Yielded Result (TTFR)**: Measuring first-byte responsiveness (in milliseconds)
   from execution start until the first matching item is yielded. Low TTFR is critical for pipe
   streaming and interactive subshells.

3. **Peak Heap Memory Footprint**: Tracking peak heap memory allocation using Python's `tracemalloc`
   standard library to ensure low, bounded memory usage during multi-level directory traversal.

______________________________________________________________________

## 2. Core Optimization Vectors

The traversal and classification pipeline incorporates several targeted optimizations to maximize
throughput across large repository hierarchies:

### 2.1. Redundant Syscalls & `Path.resolve()` Elimination

Earlier implementations resolved relative paths by invoking `Path.resolve()` on every discovered
file. In deep directory structures, resolving paths generates tens of thousands of redundant
`readlink` and `stat` system calls.

`findfmt` optimizes this by computing directory-relative paths with `os.path.relpath()` and prefix
operations derived from pre-computed root strings. File classification operates on the entry's
original path without resolving symlinks for regular files, avoiding per-file link resolution
overhead.

### 2.2. `DirEntry` Metadata Preservation & Single-Buffer Content Reads

Python's `os.scandir()` yields `os.DirEntry` objects whose cached file type (`is_file`, `is_dir`,
`is_symlink`) and `stat()` attributes are populated directly from the operating system's directory
stream.

`findfmt` preserves and forwards `os.DirEntry` instances throughout traversal and classification:

- **Zero-Stat Verification**: Avoids secondary `os.stat()` syscalls by reusing cached entry
  metadata.
- **Single-Buffer Content Inspection**: When content inspection is required (for shebang or MIME
  detection), `findfmt` reads an initial buffer (the first 2,048 to 4,096 bytes) once into memory.
  This buffer is shared across shebang parsing, MIME type sniffing, and tag classification,
  eliminating duplicate `open()` and `read()` syscalls on candidate files.

### 2.3. Zero-Allocation Gitignore Rule Matching Hot Loop

In traversal loops evaluating multiple active `.gitignore` specifications:

- Path operations avoid redundant `Path.is_relative_to()` and `Path.relative_to()` allocations.
- Relative path representations are passed as normalized strings, leveraging fast string prefix
  matching to evaluate directory boundaries and pruning rules.

### 2.4. Fast-Path Filter Short-Circuiting

When specific tags are requested (for example, `--tag python`):

- `can_skip_file_by_tags()` inspects the filename extension before opening the file.
- If an extension definitively excludes the requested tags and indicates no executable shebang is
  possible (such as known binary formats or fixed non-script extensions), the file read is bypassed
  entirely.

______________________________________________________________________

## 3. Parallel Batch Execution & Concurrency Analysis

Parallelizing the content-inspection phase using `concurrent.futures.ThreadPoolExecutor` was
evaluated against the streaming generator architecture on modern multi-core NVMe systems.

### 3.1. ThreadPoolExecutor vs. Streaming Generator Benchmarks

Empirical profiling evaluated a 4-worker `ThreadPoolExecutor` against the sequential streaming
generator across a test suite of 1,000 files:

- **Sequential Streaming Generator**: Processed 1,000 files in 0.0584 seconds (~17,131
  files/second).
- **ThreadPoolExecutor (4 Workers)**: Processed 1,000 files in 0.1076 seconds (~9,295 files/second).

Multi-threading introduced an approximate 1.84x slowdown compared to the single-threaded
implementation.

### 3.2. Concurrency Trade-Off Rationale

Several architectural factors explain why single-threaded traversal outperforms thread pools for
local filesystem inspection in Python:

1. **OS Page Cache & SSD Latency**: Reading initial file buffers (2 KB) from modern NVMe storage and
   operating system page caches executes in microseconds. I/O wait times are negligible compared to
   thread scheduling costs.
2. **GIL Contention & Dispatch Overhead**: Submitting tasks to thread pools, queuing futures,
   context switching, and Global Interpreter Lock (GIL) contention in CPython introduce
   synchronization overhead that dwarfs the cost of reading small file headers sequentially.
3. **Time-to-First-Result (TTFR) Degradation**: Batch thread dispatching chunks results, delaying
   initial yields. The single-threaded generator yields matching entries immediately
   (sub-millisecond TTFR), which is essential for interactive subshells and piping into tools like
   `fzf` or `head`.
4. **Bounded Memory Guarantees**: A pure generator maintains constant memory, whereas parallel
   thread pools accumulate collections of pending futures and buffers.

Based on these empirical results, `findfmt` retains its single-threaded streaming generator design
as the optimal performance architecture.

______________________________________________________________________

## 4. Automated Benchmark Harness (`tools/benchmark.py`)

The repository includes a dedicated, automated benchmark suite at `tools/benchmark.py` that
generates reproducible synthetic datasets and measures traversal performance across standard tiers.

### 4.1. Tiered Datasets

The harness supports three standardized dataset tiers alongside custom directory targeting:

- **Small Tier (\<1,000 files)**: Generates approximately 800 files across nested directories with
  `.gitignore` exclusion rules. Designed for fast local feedback (\<1 second execution).

- **Medium Tier (10,000–50,000 files)**: Generates approximately 12,000 files across multiple
  package subtrees, simulating standard enterprise codebases.

- **Monorepo Tier (>100,000 files)**: Stress test dataset simulating large monorepo structures with
  deep hierarchies and mixed file types.

- **Custom Directory Target (`-d, --target-dir`)**: Benchmarks real-world directory trees directly,
  such as the `findfmt` repository or user-specified projects.

### 4.2. Deterministic Reproducibility

Synthetic trees are generated deterministically using a fixed random seed (`--seed 42` by default).
The generator constructs realistic directory trees with diverse file extensions (`.py`, `.sh`,
`.md`, `.json`, `.yaml`, `.txt`, `.bin`), executable scripts without extensions containing shebang
headers, and root `.gitignore` exclusion specifications.

______________________________________________________________________

## 5. Command-Line Interface & Usage

### 5.1. Basic Execution

Execute the default benchmark suite on the small tier:

```bash
uv run python tools/benchmark.py
```

### 5.2. Tier Selection & File Overrides

Run specific or all dataset tiers:

```bash
# Execute medium tier benchmark
uv run python tools/benchmark.py --tier medium

# Execute all standard tiers (small, medium, monorepo)
uv run python tools/benchmark.py --tier all

# Custom file count override
uv run python tools/benchmark.py --tier small --files 500
```

### 5.3. Benchmarking Existing Directories

Benchmark an existing repository or directory path:

```bash
uv run python tools/benchmark.py --target-dir .
```

### 5.4. Multiple Iterations & Warmup

Execute multiple iterations with warmup runs to compute averaged metrics:

```bash
uv run python tools/benchmark.py --runs 3 --warmup 1
```

### 5.5. Baseline Recording & Regression Tracking

Save baseline metrics to a JSON report:

```bash
uv run python tools/benchmark.py --tier small --save-baseline baseline.json
```

Compare current performance against a recorded baseline:

```bash
uv run python tools/benchmark.py --tier small --baseline baseline.json
```

Fail execution if throughput degrades beyond an allowable percentage threshold:

```bash
uv run python tools/benchmark.py --tier small --baseline baseline.json --threshold 10.0
```

### 5.6. Machine-Readable JSON Output

Emit JSON directly to stdout or export to a file for CI regression tracking:

```bash
# Print structured JSON to stdout
uv run python tools/benchmark.py --json

# Save structured JSON report to file
uv run python tools/benchmark.py --output benchmark_report.json
```

______________________________________________________________________

## 6. Baseline Performance Metrics

The following baseline metrics were recorded on an x86_64 Linux environment (Python 3.13):

| Benchmark Tier   | Total Files | Traversed Directories | Duration (s) | Throughput (files/s) | Dirs/sec | TTFR Latency (ms) | Peak Heap (MB) |
| :--------------- | :---------- | :-------------------- | :----------- | :------------------- | :------- | :---------------- | :------------- |
| **Small**        | 518         | 60                    | 0.2240 s     | 2,312.6 f/s          | 267.9    | 22.15 ms          | 0.41 MB        |
| **Medium**       | 7,901       | 60                    | 5.1981 s     | 1,520.0 f/s          | 11.5     | 39.30 ms          | 2.90 MB        |
| **findfmt Repo** | 154         | 1,846                 | 0.1084 s     | 1,420.8 f/s          | 17,031.5 | 39.06 ms          | 0.47 MB        |

______________________________________________________________________

## 7. Regression Testing in CI

The benchmarking harness supports automated regression detection in continuous integration:

1. Baselines are established and preserved as versioned JSON artifacts.
2. Pull requests execute `tools/benchmark.py --baseline <baseline.json> --threshold <pct>`.
3. If throughput degrades by more than the specified threshold percentage, the tool emits a
   comparison table and exits with non-zero status code `1`, halting the quality gate.
