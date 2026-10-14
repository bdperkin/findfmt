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

`-d, --dirs-only` : List directories only, suppressing regular file entries.

`-l, --follow-links, --follow-symlinks / --no-follow-links, --no-follow-links` (alias:
`--symlinks / --no-symlinks`) : Follow directory symlinks with cycle and loop detection.

`-x, --one-file-system` : Confine traversal to the filesystem device of the starting directory.

`-L, --max-depth LEVEL` : Restrict directory traversal descent to a maximum depth level.

`--filelimit LIMIT` : Skip directories whose immediate child entry count exceeds this threshold.

`--prune` : Omit empty directories and directories containing zero matching files from output.

`-P, --pattern, --include-pattern PATTERN` : List only files matching the wildcard or glob
expression. Supports multiple `-P` flags and `|` alternation (e.g. `*.py|*.md`).

`-I, --exclude-pattern PATTERN` : Omit files and directories matching the wildcard or glob
expression. Supports multiple `-I` flags and `|` alternation (e.g. `*.tmp|*.bak`).

`--ignore-case / --no-ignore-case` : Apply case-insensitive matching across `-P` and `-I` patterns.

`--match-dirs, --matchdirs / --no-match-dirs, --no-matchdirs` : Match directory names against
patterns. If a directory matches, pattern restrictions are disabled for its children.

`--gitignore-file PATH` : Apply a specific external ignore file across the traversal scope.

`--from-file, --fromfile PATH` : Ingest directory listings and path structures from an external file
or standard input (`-`) instead of scanning the local filesystem. Supports both flat
newline-delimited paths (e.g. from `find` or `git ls-files`) and tab- or space-indented outlines
with automatic hierarchy and symlink (`link -> target`) detection.

`--offline` : Enforce offline classification without inspecting the local filesystem. Identifies
file formats and types strictly via extension and filename heuristics, operating gracefully when
analyzing remote manifests or containers without raising filesystem IO errors.

`--no-ignore / --ignore` : Do not prune paths matching `.gitignore` or `.git/info/exclude`. Use
`--ignore` to restore `.gitignore` honoring.

`-a, --all / --no-all` (alias: `--hidden / --no-hidden`) : Traverse hidden files and directories
(names starting with `.`). Use `--no-all` or `--no-hidden` to exclude hidden paths.

`--sort CRITERIA` : Sort entries by criteria: `name` (default), `version` (natural numbers), `time`
(or `mtime`, newest first), `ctime` (status change, newest first), `size` (largest first), or `none`
(unsorted).

`-r, --reverse` : Invert active sort order (e.g. oldest first for time, smallest first for size,
reverse alphabetical for name).

`-U, --unsorted` : Do not sort entries; yield files in raw filesystem order (equivalent to
`--sort=none`). Bypasses sorting overhead and memory buffering for massive trees.

`--dirsfirst, --group-directories-first` : Group all directories before files within each directory
level, sorting each group by active criteria.

`--filesfirst` : Group all regular files before directories within each directory level.

### 2.3. Output Controls

- `-f, --format FORMAT` : Choose the output serialization format (`text`, `json`, `jsonl`, `yaml`,
  `ipynb`, `csv`, `csv-table`, `tsv`, `markdown`, `rst`, `table`, `tree`). Defaults to `text`.

- `text`: Standard line-oriented or NUL-delimited plain text paths.

- `json`: Deterministic JSON array of file objects with full metadata attributes.

- `jsonl`: Line-delimited JSON (NDJSON) records for streaming pipelines.

- `ndjson`: Alias for `jsonl` line-delimited JSON stream.

- `yaml`: Clean, readable block-style YAML document.

- `ipynb`: Jupyter Notebook (`.ipynb`) format pre-populated with data analysis code cells.

- `csv`: RFC 4180 compliant comma-separated values with header row.

- `csv-table`: Aligned ASCII or Unicode table constructed directly from CSV schema for terminal
  review.

- `tsv`: Tab-separated values optimized for Unix shell pipelines (`awk`, `cut`).

- `markdown` (or `md`): GitHub Flavored Markdown (GFM) column-aligned table with alignment
  indicators.

- `rst`: reStructuredText grid or simple table format compatible with Sphinx `.. include::`
  directives.

- `table`: Rich styled terminal table with colorful badges for tags, sizes, and MIME types.

- `tree`: Hierarchical directory tree rendering files within their directory branches.

- `xml`: Well-formed hierarchical XML document capturing directories, files, tags, and metadata
  attributes.

- `html`: Semantic, accessible HTML5 document with styled directory tree and hyperlinks.

`--tree / --no-tree` : Render output in a hierarchical directory tree (equivalent to
`--format tree`).

`-J, --json / --no-json` : Render output as structured JSON records (equivalent to `--format json`).

`-X, --xml / --no-xml` : Render output as a hierarchical XML document (equivalent to
`--format xml`).

`-H, --html BASEHREF` : Render output as a semantic HTML5 document with clickable hyperlinks
prefixed with `BASEHREF` (equivalent to `--format html`).

`--intro PATH` : Prepend custom HTML fragment file before the directory listing in HTML mode.

`--outro PATH` : Append custom HTML fragment file after the directory listing in HTML mode.

`-T, --title TITLE` : Configure document `<title>` and `<h1>` heading for HTML output (defaults to
`Directory Tree`).

`--nolinks / --no-nolinks` : Suppress hyperlink anchors in HTML output, rendering paths as styled
plain text.

`-o, --output PATH` : Send command output directly to a file rather than standard output.

`--table-style STYLE` : Configure table border styles for `table`, `csv-table`, and `rst` formats
(`rounded`, `simple`, `minimal`, `double`, `heavy`, `markdown`, `ascii`, `cp437`, `square`, `grid`).
Defaults to `rounded`.

`--pager / --no-pager` : Control interactive terminal paging. Defaults to auto-paging on interactive
terminals when output line count exceeds terminal height. Applies to formatted file listings,
`--help`, `--help-all`, `--known-tags`, and tall `--diagnostics` outputs. Bypassed automatically
when piped or redirected.

`-i, --no-indent / --indent` : Omit branch indentation characters in tree format and strip
extraneous whitespace and padding in structured formats.

`-A, --ansi-lines / --no-ansi-lines` : Use ANSI/VT100 alternate character set line drawing escapes
(`\033(0...`) for tree indentation lines.

`-S, --cp437 / --no-cp437` : Use Code Page 437 (IBM-PC) console graphics characters for tree
indentation lines.

`-C, --color / -n, --no-color` : Force enable or disable ANSI color styling across all output
channels unconditionally.

`--absolute, --full-path / --no-absolute, --no-full-path` : Output absolute filesystem paths rather
than relative paths.

`--relative, --relative-path / --no-relative, --no-relative-path` : Prepend input search path prefix
to relative output paths rather than stripping the traversal root.

`-p, --permissions / --no-permissions` : Print file type and permissions in standard `ls -l` format
(e.g. `-rw-r--r--`, `drwxr-xr-x`).

`-u, --user / --no-user` : Print file owner username, falling back to numeric UID if username is
unresolvable.

`-g, --group / --no-group` : Print file owner group name, falling back to numeric GID if group name
is unresolvable.

`--inodes / --no-inodes` : Print filesystem inode number (`st_ino`).

`--device / --no-device` : Print filesystem device number (`st_dev`).

`--size / --no-size` : Print file size in bytes (`st_size`).

`-h, --human-readable / --no-human-readable` : Print sizes in human-readable format with IEC/binary
unit prefixes (`K`, `M`, `G`, `T`, `P`, `E`) using powers of 1024.

`--si / --no-si` : Print sizes in human-readable format with SI unit prefixes (`kB`, `MB`, `GB`,
`TB`, `PB`, `EB`) using powers of 1000.

`--du, --accumulate-size / --no-du, --no-accumulate-size` : Recursively calculate and accumulate
directory disk usage sizes across all contained files and child directories. In tree format, prints
accumulated directory sizes alongside folder nodes. In non-tree formats, lists directories with
their total accumulated sizes.

`-D, --mtime / --no-mtime` : Print the date and time of the last modification (`st_mtime`).

`--ctime / --no-ctime` : Print the date and time of the last status change (`st_ctime`).

`--time-format, --timefmt FORMAT` : Specify custom date and time output format using `strftime`
syntax (implies `-D` unless `--ctime` is explicitly specified).

`-F, --classify / --no-classify` : Append a file classification indicator character to each filename
(`*` for executable, `/` for directory, `@` for symbolic link, `=` for socket, `|` for FIFO, `>` for
door).

`-q, --hide-control-chars / --no-hide-control-chars` : Replace non-printable control characters in
filenames with question marks (`?`).

`-N, --literal / --no-literal` : Print non-printable control characters literally as raw bytes
without masking.

`-Q, --quote-name / --no-quote-name` : Enclose filenames in double quotes (`"..."`), escaping any
embedded double quotes (`\"`) and backslashes (`\\`).

`--hyperlink / --no-hyperlink` : Wrap rendered file and directory paths in standard OSC 8 terminal
hyperlink escape sequences (`\033]8;;URI\033\TEXT\033]8;;\033\`), enabling direct click-to-open
navigation in modern terminal emulators.

`--hyperlink-schema SCHEMA` : Custom URI schema prefix for terminal hyperlinks (defaults to
`file://`). Supports standard local file schemes as well as editor URI schemas such as
`vscode://file/`, `cursor://file/`, or `subl://`.

`--hyperlink-authority AUTHORITY` : Optional authority or hostname component for terminal hyperlinks
(e.g., `localhost` or remote workstation hostnames).

`-0, --print0 / --no-print0` : Delimit paths with a NUL (`\0`) byte instead of a newline for safe
consumption by `xargs -0`.

`--list-tags / --no-list-tags` : Print identified format and content tags alongside each matched
path.

`-s, --summary / --no-summary` : Print summary match statistics and top format tags to `stderr`.

### 2.4. Information & Diagnostics

`--known-tags` : List all tags supported by the classifier engine and exit immediately (routed
through the interactive pager on TTY sessions exceeding terminal height).

`-v, -V, --version` : Display the version of `findfmt` and exit. When combined with `--verbose`,
prints runtime environment diagnostics (Python runtime, OS platform, identify engine, and Git) via
the interactive pager when exceeding terminal height.

`--verbose` : Enable verbose diagnostic output when paired with `--version`.

`--diagnostics` : Display runtime environment diagnostics and exit immediately (routed through the
interactive pager on TTY sessions exceeding terminal height).

`--help-all` : Display the comprehensive CLI manual, environment variables, and exit codes (routed
through the interactive pager on TTY sessions exceeding terminal height).

`--help` : Show the categorized help message and exit (automatically routed through the interactive
pager on TTY sessions exceeding terminal height).

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

## 7. Pipeline Integration Examples

`findfmt` integrates smoothly with automated Unix pipelines, linters, data processing utilities, and
documentation generators.

### 7.1. Safe Command Execution with `xargs`

Safely pipe matching file paths to linters or formatters using NUL delimiters (`-0` / `--print0`):

```bash
# Format discovered Python files
findfmt -t python -0 | xargs -0 ruff format

# Lint shell scripts safely
findfmt -t shell -0 | xargs -r -0 shellcheck
```

### 7.2. JSON Filtering with `jq`

Process deterministic metadata records using `jq`:

```bash
# Extract executable script paths
findfmt -f json | jq -r '.[] | select(.is_executable == true) | .path'

# Query files larger than 100 KB
findfmt -f json | jq '.[] | select(.size_bytes > 102400) | {path, size: .size_bytes}'
```

### 7.3. Delimited Data Processing with `csvkit`

Inspect and slice CSV records with `csvkit`:

```bash
# Select path, tags, and size columns
findfmt -f csv | csvcut -c path,tags,size_bytes

# Filter files by executable status
findfmt -f csv | csvgrep -c is_executable -m true
```

### 7.4. Sphinx Documentation Inclusion

Export tables directly into documentation build directories for Sphinx inclusion:

```bash
# Export reStructuredText table for Sphinx .. include::
findfmt -f rst --table-style grid > docs/source/_generated_inventory.rst

# Render aligned CSV table for terminal review
findfmt -f csv-table --table-style rounded
```

### 7.5. HTML Documentation Export with Templating

Generate a semantic HTML document tree with customized headers, footers, and hyperlinks:

```bash
# Generate standalone HTML document tree with custom header and footer
findfmt -H "https://github.com/myorg/myproject/blob/main/" \
  --title "Project Inventory" \
  --intro assets/header.html \
  --outro assets/footer.html \
  -o site/inventory.html
```

### 7.6. Terminal Navigation with Clickable Hyperlinks

Navigate directory structures directly in modern terminal emulators using OSC 8 escape sequences:

```bash
# Browse files with click-to-open hyperlinks in editor
findfmt --hyperlink --hyperlink-schema "vscode://file/"

# Render hierarchical tree with OSC 8 hyperlinks
findfmt --tree --hyperlink
```
