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

#### 4.1.1. Deterministic Reproducibility

Synthetic trees are generated deterministically using a fixed random seed (`--seed 42` by default).
The generator constructs realistic directory trees with diverse file extensions (`.py`, `.sh`,
`.md`, `.json`, `.yaml`, `.txt`, `.bin`), executable scripts without extensions containing shebang
headers, and root `.gitignore` exclusion specifications.

### 4.2. Filesystem Topologies

To model realistic disk structures, the benchmark harness supports representative topologies via
`--topology` (`-T`):

- **Standard (`standard`)**: A balanced multi-tier package tree (60 directories) simulating a
  typical project directory hierarchy.
- **Flat (`flat`)**: A single directory containing all generated files (for example, 10,000 files in
  one folder), isolating raw directory stream parsing throughput from recursive traversal overhead.
- **Deep (`deep`)**: A deeply nested hierarchy (20 levels of nesting with a branching factor of 2),
  testing recursion depth limits, call-stack efficiency, and path concatenation overhead.
- **Real-World Monorepo (`real-world`)**: A realistic monorepo topology featuring multiple
  sub-projects alongside massive ignored directories (`node_modules/`, `.venv/`, `dist/`, `build/`)
  containing thousands of excluded files, verifying early `.gitignore` directory pruning efficiency
  in $O(1)$ time.

### 4.3. Output Formatters & Classification Modes

The harness benchmarks output formatting throughput, streaming efficiency, and Time-to-First-Result
(TTFR) latency via `--format` (`-F`) and `--list-tags`:

- **Streaming Formats (`text`, `jsonl`, `tsv`, `csv`)**: Streams entries lazily directly to the sink
  without buffering matching inventories into RAM, maintaining bounded $O(1)$ heap overhead.
- **Buffered Formats (`json`, `tree`, `table`)**: Ingests all matching records before building
  structured trees or serialized tabular representations.
- **Tag & MIME Inspection (`--list-tags`)**: Measures content inspection overhead when resolving
  MIME classifications and tag metadata across discovered files.

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

### 5.3. Topology Benchmarking

Benchmark specific filesystem topologies:

```bash
# Benchmark flat topology with 10,000 files
uv run python tools/benchmark.py --topology flat --files 10000

# Benchmark deeply nested hierarchy (20 levels)
uv run python tools/benchmark.py --topology deep --files 5000

# Benchmark real-world monorepo topology with ignored dependencies
uv run python tools/benchmark.py --topology real-world
```

### 5.4. Formatter Comparison & Classification

Compare streaming vs buffered output formats:

```bash
# Compare all output formatters on small tier
uv run python tools/benchmark.py --tier small --format all

# Measure MIME and tag classification overhead
uv run python tools/benchmark.py --tier small --format text --list-tags
```

### 5.5. Benchmarking Existing Directories

Benchmark an existing repository or directory path:

```bash
uv run python tools/benchmark.py --target-dir .
```

### 5.6. Multiple Iterations & Warmup

Execute multiple iterations with warmup runs to compute averaged metrics:

```bash
uv run python tools/benchmark.py --runs 3 --warmup 1
```

### 5.7. Baseline Recording & Regression Tracking

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

### 5.8. Machine-Readable JSON Output

Emit JSON directly to stdout or export to a file for CI regression tracking:

```bash
# Print structured JSON to stdout
uv run python tools/benchmark.py --json

# Save structured JSON report to file
uv run python tools/benchmark.py --output benchmark_report.json
```

______________________________________________________________________

## 6. Official v1.0.0 Baseline Performance Metrics

The canonical v1.0.0 baselines were recorded on an x86_64 Linux environment (CPython 3.13.15, Linux
6.12+):

### 6.1. Filesystem Topology Baselines

| Topology / Benchmark Tier         | Matched Files | Traversed Directories | Duration (s) | Throughput (files/s) | TTFR Latency (ms) | Peak Heap (MB) |
| :-------------------------------- | :------------ | :-------------------- | :----------- | :------------------- | :---------------- | :------------- |
| **Standard Small (800 files)**    | 518           | 60                    | 0.1785 s     | 2,902.4 f/s          | 3.87 ms           | 0.09 MB        |
| **Standard Medium (12k files)**   | 7,901         | 60                    | 2.4989 s     | 3,162.0 f/s          | 10.24 ms          | 0.71 MB        |
| **Flat (10k files in 1 dir)**     | 8,261         | 0                     | 2.3497 s     | 3,522.9 f/s          | 348.84 ms         | 11.94 MB       |
| **Deep (20 levels, 5k files)**    | 4,119         | 286                   | 3.4016 s     | 1,211.8 f/s          | 3.68 ms           | 0.57 MB        |
| **Real-World Monorepo (Ignored)** | 826           | 35                    | 0.3734 s     | 2,213.1 f/s          | 5.93 ms           | 0.19 MB        |
| **findfmt Repository**            | 233           | 1,933                 | 0.1575 s     | 1,480.3 f/s          | 9.24 ms           | 0.13 MB        |

*Note: In the Real-World Monorepo benchmark, 5,000+ files located in `node_modules/` and `.venv/`
were pruned in $O(1)$ time at the directory root level, completing in 0.37 seconds.*

### 6.2. Output Formatter & Classification Performance (Medium Tier, 7,901 Files)

| Formatter / Mode    | Category   | Duration (s) | Throughput (files/s) | TTFR Latency (ms) | Peak Heap (MB) | Memory Scaling |
| :------------------ | :--------- | :----------- | :------------------- | :---------------- | :------------- | :------------- |
| **Raw Traversal**   | Engine     | 2.5437 s     | 3,106.1 f/s          | 24.75 ms          | 2.89 MB        | $O(1)$ Bounded |
| **Text (`text`)**   | Streaming  | 2.6332 s     | 3,000.6 f/s          | 11.07 ms          | 0.72 MB        | $O(1)$ Bounded |
| **JSONL (`jsonl`)** | Streaming  | 3.1472 s     | 2,510.4 f/s          | 10.43 ms          | 0.72 MB        | $O(1)$ Bounded |
| **TSV (`tsv`)**     | Streaming  | 2.5570 s     | 3,089.9 f/s          | 0.02 ms           | 0.72 MB        | $O(1)$ Bounded |
| **CSV (`csv`)**     | Streaming  | 2.5785 s     | 3,064.2 f/s          | 0.04 ms           | 0.84 MB        | $O(1)$ Bounded |
| **JSON (`json`)**   | Buffered   | 2.9981 s     | 2,635.3 f/s          | 2,997.77 ms       | 15.25 MB       | $O(N)$ Linear  |
| **Tree (`tree`)**   | Buffered   | 16.3280 s    | 483.9 f/s            | 16,265.90 ms      | 36.30 MB       | $O(N)$ Linear  |
| **Table (`table`)** | Buffered   | 57.7142 s    | 136.9 f/s            | 57,581.79 ms      | 64.80 MB       | $O(N)$ Linear  |
| **Text + Tags**     | Classified | 3.5339 s     | 2,235.8 f/s          | 14.60 ms          | 0.72 MB        | $O(1)$ Bounded |

______________________________________________________________________

## 7. Regression Testing in CI

The benchmarking harness and automated test suite ensure continuous regression protection:

1. Canonical v1.0.0 baselines are committed and versioned at `tests/fixtures/v1_baseline.json`.
2. Automated integration tests in `tests/integration/test_performance_baselines.py` continuously
   assert that:
   - Streaming formatters (`text`, `jsonl`, `tsv`, `csv`) maintain bounded $O(1)$ heap memory.
   - Early `.gitignore` pruning bounds traversal time and memory when skipping massive directory
     trees.
   - Continuous multi-run traversals exhibit zero unbounded memory leaks.
3. Pull requests can execute regression checks via:

```bash
uv run python tools/benchmark.py --baseline tests/fixtures/v1_baseline.json --threshold 10.0
```

If throughput degrades by more than the specified threshold percentage, the tool emits a comparison
table and exits with non-zero status code `1`, halting the quality gate.
