# Configuration

`findfmt` supports flexible, structured configuration loading through standard TOML files. This
enables setting persistent personal defaults or project-level standards for output formatting,
visual styling, traversal boundaries, and tag filtering.

______________________________________________________________________

## 1. Configuration Resolution Hierarchy

When `findfmt` executes, it determines effective settings according to a strict six-tier hierarchy
where higher-priority sources override lower-priority sources:

1. **Explicit CLI arguments and flags** (Highest Priority): Direct options passed on the command
   line (e.g. `--format table`, `--no-hidden`, `-t python`) always override environment variables
   and file settings.
2. **Environment Variables**: System environment settings such as `NO_COLOR`, `CLICOLOR`,
   `CLICOLOR_FORCE`, `LANGUAGE`, and `LC_*` override file defaults.
3. **Explicit Configuration File**: A custom configuration path specified via `--config <path>` or
   the `FINDFMT_CONFIG` environment variable.
4. **Standard User Configuration Path**: User-level configuration located at
   `$XDG_CONFIG_HOME/findfmt/config.toml` (or `~/.config/findfmt/config.toml` on POSIX systems;
   `%APPDATA%\findfmt\config.toml` on Windows).
5. **Project Local Configuration**: A `pyproject.toml` file containing a `[tool.findfmt]` table
   located in the current working directory.
6. **Built-in Defaults** (Lowest Priority): Factory default options (`format = "text"`,
   `color = "auto"`, `pager = "auto"`, etc.).

```{note}
Passing `--no-config` on the command line or setting `FINDFMT_CONFIG=""` completely
suppresses discovery and loading of configuration files, forcing `findfmt` to rely strictly on
built-in defaults and command-line flags.
```

______________________________________________________________________

## 2. Configuration Inspection

To inspect the currently active configuration file and resolved settings:

```bash
findfmt --show-config
```

When custom options are loaded, `findfmt` outputs the active path and effective configuration table:

```text
Active configuration: /home/user/.config/findfmt/config.toml

[tool.findfmt]
color = "always"
format = "table"
hidden = true
table_style = "rounded"
```

To view configuration status as part of general system diagnostics:

```bash
findfmt --diagnostics
```

______________________________________________________________________

## 3. Configuration File Formats

`findfmt` natively parses configuration using standard TOML. Configuration can be defined either in
a standalone `config.toml` file or embedded inside a repository's `pyproject.toml`.

### 3.1. Standalone `config.toml`

A standalone file can place options at top level or under a `[tool.findfmt]` table:

```toml
# ~/.config/findfmt/config.toml

# Default output serialization format (text, table, tree, json, etc.)
format = "table"

# Border style for table and tree formatters (rounded, grid, ascii, etc.)
table_style = "rounded"

# ANSI color policy: "auto", "always", or "never"
color = "auto"

# Terminal pager policy: "auto", "always", or "never"
pager = "auto"

# Include hidden files (dotfiles) by default
hidden = false

# Honor .gitignore and global gitignore files (true) or ignore them (false)
ignore = true

# Default tags to include
tags = ["python", "shell"]

# Maximum directory descent depth
max_depth = 5

# Group directories first
dirs_first = true
```

### 3.2. Project Configuration (`pyproject.toml`)

In repositories managed by modern Python tooling (`uv`, `hatch`, `flit`, `poetry`), `findfmt` reads
the `[tool.findfmt]` table:

```toml
# pyproject.toml

[tool.findfmt]
format = "tree"
table_style = "rounded"
tags = ["python"]
exclude_tags = ["text"]
ignore = true
hidden = false
dirs_first = true
```

______________________________________________________________________

## 4. Configuration Schema Reference

| Setting           | Type            | CLI Equivalent                           | Description                                                                                                                                  | Default  |
| :---------------- | :-------------- | :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------- | :------- |
| `format`          | string          | `-f, --format`                           | Output serialization format (`text`, `table`, `tree`, `json`, `yaml`, `csv`, `tsv`, `xml`, `html`, `markdown`, `rst`, `jsonl`, `csv-table`). | `"text"` |
| `csv_safe`        | bool            | `--csv-safe / --no-csv-safe`             | Prefix formula triggers in CSV/TSV cells with single quote to prevent spreadsheet formula injection.                                         | `false`  |
| `table_style`     | string          | `--table-style`                          | Table border style (`rounded`, `grid`, `ascii`, `minimal`, etc.).                                                                            | `None`   |
| `color`           | string / bool   | `-C / -n`                                | Color policy: `"auto"`, `"always"`, `"never"`, or boolean.                                                                                   | `"auto"` |
| `pager`           | string / bool   | `--pager / --no-pager`                   | Terminal paging policy: `"auto"`, `"always"`, `"never"`, or boolean.                                                                         | `"auto"` |
| `hidden`          | bool            | `-a, --all / --no-all`                   | Include dotfiles and hidden directories in traversal.                                                                                        | `false`  |
| `ignore`          | bool            | `--no-ignore / --ignore`                 | Respect `.gitignore` and global gitignore rules (`true` to honor, `false` to disable).                                                       | `true`   |
| `tags`            | list[str] / str | `-t, --tag`                              | Default tag inclusions.                                                                                                                      | `[]`     |
| `exclude_tags`    | list[str] / str | `-e, --exclude-tag`                      | Default tag exclusions.                                                                                                                      | `[]`     |
| `all_tags`        | bool            | `--all-tags`                             | Require all specified tags to match rather than any tag.                                                                                     | `false`  |
| `sort`            | string          | `--sort`                                 | Sort key criterion (`name`, `size`, `mtime`, `ctime`, `version`, `none`).                                                                    | `"name"` |
| `reverse`         | bool            | `-r, --reverse`                          | Reverse sort ordering.                                                                                                                       | `false`  |
| `dirs_first`      | bool            | `--dirsfirst`                            | Group directories before files.                                                                                                              | `false`  |
| `files_first`     | bool            | `--filesfirst`                           | Group files before directories.                                                                                                              | `false`  |
| `follow_symlinks` | bool            | `-l, --follow-links / --follow-symlinks` | Follow directory symlinks during traversal.                                                                                                  | `false`  |
| `dirs_only`       | bool            | `-d, --dirs-only`                        | Emit directories only and suppress files.                                                                                                    | `false`  |
| `max_depth`       | int             | `-L, --max-depth`                        | Maximum directory descent depth limit.                                                                                                       | `None`   |
| `file_limit`      | int             | `--filelimit`                            | Directory entry count threshold.                                                                                                             | `None`   |
| `prune`           | bool            | `--prune`                                | Omit directories containing zero matching items.                                                                                             | `false`  |
| `pattern`         | list[str] / str | `-P, --pattern`                          | Wildcard filename include patterns.                                                                                                          | `[]`     |
| `exclude_pattern` | list[str] / str | `-I, --exclude-pattern`                  | Wildcard filename exclude patterns.                                                                                                          | `[]`     |
| `ignore_case`     | bool            | `--ignore-case`                          | Case-insensitive pattern matching.                                                                                                           | `false`  |
| `match_dirs`      | bool            | `--match-dirs`                           | Inherit pattern matches to subdirectories.                                                                                                   | `false`  |
| `shebang`         | string          | `--shebang`                              | Interpreter shebang pattern filter.                                                                                                          | `None`   |
| `absolute`        | bool            | `--absolute`                             | Output absolute paths instead of relative paths.                                                                                             | `false`  |
| `relative`        | bool            | `--relative`                             | Prepend search prefix to relative paths.                                                                                                     | `false`  |
| `print0`          | bool            | `-0, --print0`                           | Delimit paths with NUL (`\0`) character for `xargs -0`.                                                                                      | `false`  |
| `list_tags`       | bool            | `--list-tags`                            | Display detected format and content tags.                                                                                                    | `false`  |
| `summary`         | bool            | `-s, --summary`                          | Print match count statistics to stderr.                                                                                                      | `false`  |
| `exit_status`     | bool            | `--exit-status`                          | Exit with code 1 if no matching files are found.                                                                                             | `false`  |
| `permissions`     | bool            | `-p, --permissions`                      | Format file permissions in `ls -l` style.                                                                                                    | `false`  |
| `user`            | bool            | `-u, --user`                             | Display file owner username or UID.                                                                                                          | `false`  |
| `group`           | bool            | `-g, --group`                            | Display file group name or GID.                                                                                                              | `false`  |
| `size`            | bool            | `--size`                                 | Print file size in bytes.                                                                                                                    | `false`  |
| `human_readable`  | bool            | `-h, --human-readable`                   | Format file sizes using binary units (KiB, MiB).                                                                                             | `false`  |
| `si`              | bool            | `--si`                                   | Format file sizes using SI metric units (kB, MB).                                                                                            | `false`  |
| `du`              | bool            | `--du`                                   | Accumulate recursive directory disk usage.                                                                                                   | `false`  |
| `mtime`           | bool            | `-D, --mtime`                            | Display file last modification date and time.                                                                                                | `false`  |
| `ctime`           | bool            | `--ctime`                                | Display last file status change date and time.                                                                                               | `false`  |
| `time_format`     | string          | `--time-format`                          | Custom strftime syntax format string.                                                                                                        | `None`   |
| `classify`        | bool            | `-F, --classify`                         | Append file type indicators (`/`, `*`, `@`, etc.).                                                                                           | `false`  |
| `quote_name`      | bool            | `-Q, --quote-name`                       | Enclose filenames in double quotes.                                                                                                          | `false`  |
| `hyperlink`       | bool            | `--hyperlink`                            | Render paths as OSC 8 terminal hyperlinks.                                                                                                   | `false`  |
| `locale`          | string          | `--locale`                               | Default display and translation locale.                                                                                                      | `None`   |

______________________________________________________________________

## 5. Troubleshooting & Diagnostics

- **Syntax Errors**: If a configuration file contains invalid TOML syntax, `findfmt` displays an
  informative syntax error and exits with code `2`:
  ```text
  Error: Invalid TOML in configuration file '/home/user/.config/findfmt/config.toml': Expected '=' after a key in a key/value pair (at line 4, column 1)
  ```
- **Unknown Keys**: If an unsupported or misspelled key is provided, `findfmt` rejects the
  configuration:
  ```text
  Error: Unknown configuration key 'frmat' in '/home/user/.config/findfmt/config.toml'.
  ```
- **Type Mismatches**: Supplying an unexpected type (e.g., a string where a boolean is required)
  triggers a clear validation error:
  ```text
  Error: Invalid value for 'hidden' in '/home/user/.config/findfmt/config.toml': expected boolean (true/false), got str
  ```
- **Bypassing Configuration**: In scripts or CI environments where deterministic, clean-room
  behavior is required regardless of existing user configurations, supply `--no-config`:
  ```bash
  findfmt --no-config -t python
  ```
