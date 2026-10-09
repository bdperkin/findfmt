# CLI Reference

`findfmt` provides a Unix-style command-line interface with options for tagging, filtering, and
output formatting.

## 1. Synopsis

```{typer} findfmt.cli:app
:prog: findfmt
```

## 2. Options

### 2.1. Tag Filtering

`-t, --type, --tag TAG` : Filter files by tag (e.g. `python`, `yaml`, `json`, `shell`,
`executable`). Can be specified multiple times or comma-separated (`-t python,shell`).

`-e, --exclude, --exclude-tag TAG` : Exclude files matching this tag.

`--all-tags / --no-all-tags` : Require matching files to contain **all** specified include tags
rather than at least one (`--no-all-tags` disables this requirement).

`--shebang INTERPRETER` : Filter files whose shebang line contains the specified interpreter name or
substring.

### 2.2. Traversal Controls

`--no-ignore / --ignore` : Do not prune paths matching `.gitignore` or `.git/info/exclude`. Use
`--ignore` to restore `.gitignore` honoring.

`--hidden / --no-hidden` : Traverse hidden files and directories (names starting with `.`). Use
`--no-hidden` to exclude hidden paths.

`-L, --follow-symlinks / --no-follow-symlinks` (alias: `--symlinks / --no-symlinks`) : Follow
symbolic links during directory traversal. Use `--no-follow-symlinks` to disable.

### 2.3. Output Controls

- `-f, --format FORMAT` : Choose the output serialization format (`text`, `json`, `jsonl`, `yaml`,
  `ipynb`, `csv`, `tsv`, `markdown`, `rst`, `table`, `tree`). Defaults to `text`.

- `text`: Standard line-oriented or NUL-delimited plain text paths.

- `json`: Deterministic JSON array of file objects with full metadata attributes.

- `jsonl`: Line-delimited JSON (NDJSON) records for streaming pipelines.

- `yaml`: Clean, readable block-style YAML document.

- `ipynb`: Jupyter Notebook (`.ipynb`) format pre-populated with data analysis code cells.

- `csv`: RFC 4180 compliant comma-separated values with header row.

- `tsv`: Tab-separated values optimized for Unix shell pipelines (`awk`, `cut`).

- `markdown` (or `md`): GitHub Flavored Markdown (GFM) column-aligned table with alignment
  indicators.

- `rst`: reStructuredText grid or simple table format compatible with Sphinx `.. include::`
  directives.

- `table`: Rich styled terminal table with colorful badges for tags, sizes, and MIME types.

- `tree`: Hierarchical directory tree rendering files within their directory branches.

`--tree / --no-tree` : Render output in a hierarchical directory tree (equivalent to
`--format tree`).

`--table-style STYLE` : Configure table border styles (`rounded`, `simple`, `minimal`, `double`,
`heavy`, `markdown`, `ascii`, `square`, `grid`). Defaults to `rounded`.

`--absolute / --no-absolute` : Output absolute filesystem paths rather than relative paths.

`-0, --print0 / --no-print0` : Delimit paths with a NUL (`\0`) byte instead of a newline for safe
consumption by `xargs -0`.

`-l, --list-tags / --no-list-tags` : Print identified format and content tags alongside each matched
path.

`-s, --summary / --no-summary` : Print summary match statistics and top format tags to `stderr`.

### 2.4. Information & Diagnostics

`--known-tags` : List all tags supported by the classifier engine and exit immediately.

`-v, -V, --version` : Display the version of `findfmt` and exit. When combined with `--verbose`,
prints runtime environment diagnostics (Python runtime, OS platform, identify engine, and Git).

`--verbose` : Enable verbose diagnostic output when paired with `--version`.

`--diagnostics` : Display runtime environment diagnostics and exit immediately.

`--help-all` : Display the comprehensive CLI manual, environment variables, and exit codes.

`-h, --help` : Show the categorized help message and exit.

## 3. Command Wrappers & Aliases

In addition to `findfmt`, several specialized command-line entry points are provided to streamline
common workflows:

- **`findfiles [PATHS...]`** : Traverse all files and directories including hidden files (`.*`),
  respecting `.gitignore` (equivalent to `findfmt --hidden`). Negate with `--no-hidden`.
- **`findfilemime [PATHS...]`** : List matched paths alongside their detected MIME and format tags,
  including hidden files (equivalent to `findfmt --hidden --list-tags`). Negate with
  `--no-list-tags`.
- **`findfilefmt [TAG] [PATHS...]`** : Locate files matching a format tag (e.g.
  `findfilefmt python`), including hidden files (equivalent to `findfmt --hidden --tag [TAG]`).
- **`findshebang [INTERPRETER] [PATHS...]`** : Discover scripts by shebang interpreter pattern (e.g.
  `findshebang bash`), including hidden files (equivalent to
  `findfmt --hidden --shebang [INTERPRETER]`).
- **`findfmt0 [PATHS...]`** : Produce NUL-delimited output for pipe-safe consumption with
  `xargs -0`, including hidden files (equivalent to `findfmt --hidden --print0`). Negate with
  `--no-print0`.
- **`findsummary [PATHS...]`** : Print format tag frequency statistics directly to `stderr`,
  including hidden files (equivalent to `findfmt --hidden --summary`). Negate with `--no-summary`.

## 4. POSIX Option Terminator (--)

A standalone double-dash (`--`) halts option processing per POSIX Guideline 10. All subsequent
tokens are treated strictly as positional filesystem paths, even if their names begin with a hyphen:

```bash
findfmt -- -weird-directory/
findfilefmt python -- -hyphenated-dir/
```

## 5. Environment Variables

- `NO_COLOR`: When set to any value, colored output is suppressed per
  [no-color.org](https://no-color.org).
- `CLICOLOR`: When set to `0`, ANSI color codes are disabled; when `1`, colors are enabled.
- `CLICOLOR_FORCE`: When non-zero, forces color output even when redirected or piped.
- `FINDFMT_CONFIG`: Path to a custom user configuration file overriding defaults.

## 6. Exit Codes

- `0`: Success (files matched or help/version queried).
- `1`: Runtime traversal or classification error.
- `2`: Invalid command-line arguments or syntax error.
