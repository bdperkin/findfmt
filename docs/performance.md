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

## 2. Automated Benchmark Harness (`tools/benchmark.py`)

The repository includes a dedicated, automated benchmark suite at `tools/benchmark.py` that
generates reproducible synthetic datasets and measures traversal performance across standard tiers.

### 2.1. Tiered Datasets

The harness supports three standardized dataset tiers alongside custom directory targeting:

- **Small Tier (\<1,000 files)**: Generates approximately 800 files across nested directories with
  `.gitignore` exclusion rules. Designed for fast local feedback (\<1 second execution).

- **Medium Tier (10,000–50,000 files)**: Generates approximately 12,000 files across multiple
  package subtrees, simulating standard enterprise codebases.

- **Monorepo Tier (>100,000 files)**: Stress test dataset simulating large monorepo structures with
  deep hierarchies and mixed file types.

- **Custom Directory Target (`-d, --target-dir`)**: Benchmarks real-world directory trees directly,
  such as the `findfmt` repository or user-specified projects.

### 2.2. Deterministic Reproducibility

Synthetic trees are generated deterministically using a fixed random seed (`--seed 42` by default).
The generator constructs realistic directory trees with diverse file extensions (`.py`, `.sh`,
`.md`, `.json`, `.yaml`, `.txt`, `.bin`), executable scripts without extensions containing shebang
headers, and root `.gitignore` exclusion specifications.

______________________________________________________________________

## 3. Command-Line Interface & Usage

### 3.1. Basic Execution

Execute the default benchmark suite on the small tier:

```bash
uv run python tools/benchmark.py
```

### 3.2. Tier Selection & File Overrides

Run specific or all dataset tiers:

```bash
# Execute medium tier benchmark
uv run python tools/benchmark.py --tier medium

# Execute all standard tiers (small, medium, monorepo)
uv run python tools/benchmark.py --tier all

# Custom file count override
uv run python tools/benchmark.py --tier small --files 500
```

### 3.3. Benchmarking Existing Directories

Benchmark an existing repository or directory path:

```bash
uv run python tools/benchmark.py --target-dir .
```

### 3.4. Multiple Iterations & Warmup

Execute multiple iterations with warmup runs to compute averaged metrics:

```bash
uv run python tools/benchmark.py --runs 3 --warmup 1
```

### 3.5. Baseline Recording & Regression Tracking

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

### 3.6. Machine-Readable JSON Output

Emit JSON directly to stdout or export to a file for CI regression tracking:

```bash
# Print structured JSON to stdout
uv run python tools/benchmark.py --json

# Save structured JSON report to file
uv run python tools/benchmark.py --output benchmark_report.json
```

______________________________________________________________________

## 4. Baseline Performance Metrics

The following baseline metrics were recorded on an x86_64 Linux environment (Python 3.13):

| Benchmark Tier   | Total Files | Traversed Directories | Duration (s) | Throughput (files/s) | Dirs/sec | TTFR Latency (ms) | Peak Heap (MB) |
| :--------------- | :---------- | :-------------------- | :----------- | :------------------- | :------- | :---------------- | :------------- |
| **Small**        | 518         | 60                    | 0.5055 s     | 1,024.6 f/s          | 118.7    | 20.15 ms          | 0.38 MB        |
| **Medium**       | 7,901       | 60                    | 6.8758 s     | 1,149.1 f/s          | 8.7      | 35.98 ms          | 2.49 MB        |
| **findfmt Repo** | 152         | 1,841                 | 0.2217 s     | 685.5 f/s            | 8,303.2  | 36.92 ms          | 0.43 MB        |

______________________________________________________________________

## 5. Regression Testing in CI

The benchmarking harness supports automated regression detection in continuous integration:

1. Baselines are established and preserved as versioned JSON artifacts.
2. Pull requests execute `tools/benchmark.py --baseline <baseline.json> --threshold <pct>`.
3. If throughput degrades by more than the specified threshold percentage, the tool emits a
   comparison table and exits with non-zero status code `1`, halting the quality gate.
