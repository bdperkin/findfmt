# Quickstart

`findfmt` identifies files by format, shebang pattern, and MIME type rather than relying strictly on
filename extensions. This guide demonstrates common discovery, filtering, and reporting workflows.

## 1. Installation & Direct Execution

### 1.1. Standalone Execution with `uvx`

Execute `findfmt` immediately without an explicit installation step using `uvx`:

```bash
uvx findfmt --help
uvx findfmt -t python
```

### 1.2. Global User Tool Installation

Install `findfmt` globally into an isolated user environment using `uv tool install`:

```bash
uv tool install findfmt
```

Upgrade to the latest version at any time:

```bash
uv tool upgrade findfmt
```

### 1.3. Project Dependency

Add `findfmt` as a dependency to your managed Python project:

```bash
# Using uv
uv add findfmt

# Using pip
pip install findfmt
```

## 2. Basic File Discovery & Tag Matching

### 2.1. Single Tag Matching

Discover files by format tag, honoring `.gitignore` rules automatically:

```bash
# Find all Python files
findfmt -t python

# Find all YAML and Markdown files
findfmt -t yaml
findfmt -t markdown
```

### 2.2. Multiple Tags (OR Condition)

Match files that contain *any* of the specified tags by providing multiple `-t` flags or a
comma-separated list:

```bash
# Find files that are either Python or Shell scripts
findfmt -t python -t shell
findfmt -t python,shell
```

### 2.3. Conjunction Matching (AND Condition)

Require matching files to satisfy *all* specified tags simultaneously using `--all-tags`:

```bash
# Find files that are both Python scripts and marked executable
findfmt -t python -t executable --all-tags
```

### 2.4. Tag Exclusion

Exclude files containing specific tags using `-e` or `--exclude-tag`:

```bash
# Find Python files while excluding test files
findfmt -t python -e test
```

### 2.5. Listing Detected Tags

Inspect the complete list of tags assigned to each file:

```bash
findfmt -t python --list-tags
```

Sample output:

```text
src/findfmt/cli/main.py [file, mime:text/x-python, non-executable, python, text]
tools/verify_quality.py [executable, file, mime:text/x-python, python, text]
```

## 3. Shebang Detection & Interpreters

`findfmt` inspects the initial line of executable files for `#!` shebang declarations. This enables
discovering scripts that omit file extensions (such as `bin/deploy` or `scripts/runner`):

```bash
# Find scripts invoking bash via shebang
findfmt --shebang bash

# Find scripts invoking python or python3
findfmt --shebang python

# Target a specific subdirectory
findfmt --shebang bash scripts/
```

Use the `findshebang` command wrapper for convenient shebang queries:

```bash
findshebang bash
findshebang sh
```

## 4. MIME Tag Classification & Prefix Filtering

Files analyzed by `findfmt` receive specific MIME classification tags prefixed with `mime:`:

```bash
# Find files by MIME type
findfmt -t mime:text/x-python
findfmt -t mime:application/json
findfmt -t mime:text/x-shellscript
```

Use the `findfilemime` wrapper to display detected MIME tags for all files across the repository:

```bash
findfilemime
```

### 4.1. Offline Mode

When running in environments where file contents cannot or should not be read from disk (e.g.
analyzing remote directory manifests or when filesystem reads must be avoided), enable `--offline`:

```bash
findfmt --offline -t python
```

Offline mode classifies files strictly through filename and extension heuristics.

## 5. Wildcard, Pattern, and Traversal Controls

### 5.1. Glob Patterns and Alternations

Filter files by filename pattern using `-P` (`--pattern`), supporting alternation via `|`:

```bash
# Match Python and Markdown files
findfmt -P "*.py|*.md"

# Exclude temporary and backup files
findfmt -I "*.tmp|*.bak"

# Case-insensitive pattern matching
findfmt -P "*.jpeg|*.jpg" --ignore-case
```

### 5.2. Directory Inheritance & Filtering

Match directory names and inherit matching status across child entries with `--match-dirs`:

```bash
# Match directories named 'tests' and all files within them
findfmt -P "tests" --match-dirs
```

Restrict traversal to directory entries only using `-d` (`--dirs-only`):

```bash
findfmt -d
```

### 5.3. Maximum Traversal Depth

Limit directory descent level using `-L` (`--max-depth`):

```bash
# Scan only root and immediate children
findfmt -L 1
```

### 5.4. Ignore Rules & External Ignore Files

By default, `findfmt` honors `.gitignore` and `.git/info/exclude`. You can customize this behavior:

```bash
# Disable .gitignore filtering to inspect all files
findfmt --no-ignore

# Apply a custom external ignore file
findfmt --gitignore-file .config/custom-ignore
```

## 6. File Metadata & Attribute Inspection

Inspect detailed filesystem attributes alongside discovered files:

```bash
# Display permissions, user ownership, group ownership, and human-readable sizes
findfmt -p -u -g -h

# Display modification timestamps using strftime format
findfmt -D --time-format "%Y-%m-%d %H:%M:%S"

# Display classification indicators (* for executable, / for directory, @ for symlink)
findfmt -F

# Mask non-printable control characters with '?'
findfmt -q

# Double-quote filenames for shell safety
findfmt -Q
```

### 6.1. Clickable Terminal Hyperlinks

On modern terminal emulators supporting OSC 8 escape sequences (such as iTerm2, Windows Terminal,
and VS Code), enable interactive click-to-open navigation:

```bash
# Generate file:// terminal hyperlinks
findfmt --hyperlink

# Target specific editor URI schemes
findfmt --hyperlink --hyperlink-schema "vscode://file/"
```

## 7. Directory Disk Usage & Tree View

Render files in a visual hierarchy with disk usage accumulation:

```bash
# Display directory tree
findfmt --tree

# Display directory tree with accumulated disk usage per folder
findfmt --tree --du -h

# Customize border style
findfmt --tree --table-style rounded
```

## 8. Multi-Format Serialization Suite

`findfmt` supports 14 output serialization formats for terminal visualization, documentation, and
automation pipelines:

### 8.1. Line & Streaming Formats

Stream paths and lightweight records for high-throughput Unix pipelines:

```bash
# Line-delimited plain text paths (default)
findfmt -f text -t python

# Streaming NDJSON (one JSON record per line)
findfmt -f jsonl -t yaml
```

### 8.2. Structured Data Documents

Generate structured documents for configuration, machine ingestion, and data analysis:

```bash
# JSON array of file objects with full metadata
findfmt -f json -t python

# Clean block-style YAML document
findfmt -f yaml -t shell

# Jupyter Notebook with pandas DataFrame ingestion cells
findfmt -f ipynb > discovery.ipynb
```

### 8.3. Delimited Tabular Formats

Export delimited records for shell tools (`awk`, `cut`) and spreadsheet analysis:

```bash
# RFC 4180 compliant CSV with header row
findfmt -f csv -t python

# Tab-separated values for Unix pipelines
findfmt -f tsv -t shell
```

### 8.4. Visual & Documentation Tables

Render formatted tables in terminals or generate documentation includes:

```bash
# Rich styled terminal table with badge colors
findfmt -f table -t python

# Aligned CSV table for terminal review
findfmt -f csv-table --table-style rounded

# GitHub Flavored Markdown table
findfmt -f markdown -t python

# reStructuredText table for Sphinx inclusion
findfmt -f rst --table-style grid > inventory.rst
```

### 8.5. Hierarchical Documents

Represent project structures as trees and markup documents:

```bash
# Hierarchical directory tree
findfmt -f tree

# Hierarchical XML document with tag attributes
findfmt -f xml -L 2

# Standalone semantic HTML5 document tree
findfmt -f html -H "https://github.com/myorg/repo/blob/main/" -o tree.html
```

## 9. Pipelining & Automation

`findfmt` integrates seamlessly into automated shell pipelines:

### 9.1. Pipe-Safe Execution with `xargs`

Safely handle filenames containing spaces, newlines, or quotes by delimiting paths with NUL bytes:

```bash
# Format discovered Python files
findfmt -t python -0 | xargs -0 ruff format

# Lint discovered shell scripts
findfmt -t shell -0 | xargs -r -0 shellcheck
```

The `findfmt0` shortcut wrapper automatically enables `--print0` and includes hidden files:

```bash
findfmt0 -t python | xargs -0 flake8
```

### 9.2. JSON Filtering with `jq`

Process deterministic metadata records using `jq`:

```bash
# Extract executable script paths
findfmt -f json | jq -r '.[] | select(.is_executable == true) | .path'

# Query files larger than 100 KB
findfmt -f json | jq '.[] | select(.size_bytes > 102400) | {path, size: .size_bytes}'
```

### 9.3. Match Summaries

Print match statistics and tag frequency counts directly to standard error:

```bash
findfmt -s
```

Or use the `findsummary` wrapper shortcut:

```bash
findsummary
```

## 10. Programmatic Python Library Usage

Integrate `findfmt` directly into Python tools, test suites, and automation scripts:

### 10.1. Basic Discovery & FileInfo Inspection

Query files and inspect detected metadata attributes:

```python
from findfmt import FileInfo, OutputFormat, TraversalConfig, find_files, get_formatter

# Configure directory traversal and tag filtering
config = TraversalConfig(
    include_tags={"python"},
    exclude_tags={"test"},
    max_depth=2,
    respect_gitignore=True,
    root_paths=["."],
)

# Iterate through discovered FileInfo objects
for file_info in find_files(config):
    print(f"Path: {file_info.path}")
    print(f"  MIME: {file_info.mime_type}")
    print(f"  Tags: {', '.join(sorted(file_info.tags))}")
    print(f"  Size: {file_info.size_bytes} bytes")
    print(f"  Executable: {file_info.is_executable}")
```

### 10.2. Output Formatting with Built-In Serializers

Render results programmatically into any supported format:

```python
# Format output programmatically with built-in formatters
formatter = get_formatter(OutputFormat.TABLE)
table_output = formatter.format(find_files(config))
print(table_output)

# Export as JSON document string
json_formatter = get_formatter(OutputFormat.JSON)
json_output = json_formatter.format(find_files(config))
```

## 11. Command Wrappers Reference

The following specialized wrappers provide convenient shortcuts for common workflows:

| Wrapper Command                   | Equivalent Invocation               | Primary Purpose                                                   |
| :-------------------------------- | :---------------------------------- | :---------------------------------------------------------------- |
| `findfiles [PATHS...]`            | `findfmt --hidden`                  | Discover all files including hidden files respecting `.gitignore` |
| `findfilemime [PATHS...]`         | `findfmt --hidden --list-tags`      | List files with detected format and MIME tags                     |
| `findfilefmt [TAG] [PATHS...]`    | `findfmt --hidden --tag TAG`        | Filter files by format tag                                        |
| `findshebang [INTERP] [PATHS...]` | `findfmt --hidden --shebang INTERP` | Discover executable scripts by shebang pattern                    |
| `findfmt0 [PATHS...]`             | `findfmt --hidden --print0`         | Produce NUL-delimited paths for `xargs -0`                        |
| `findsummary [PATHS...]`          | `findfmt --hidden --summary`        | Print match frequencies and top tags to stderr                    |
