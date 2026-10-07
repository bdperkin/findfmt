# CLI Reference

`findfmt` provides a Unix-style command-line interface with options for tagging, filtering, and
output formatting.

## Synopsis

```text
findfmt [OPTIONS] [PATHS...]
```

## Options

### Tag Filtering

`-t, --type, --tag TAG` : Filter files by tag (e.g. `python`, `yaml`, `json`, `shell`,
`executable`). Can be specified multiple times or comma-separated (`-t python,shell`).

`-e, --exclude, --exclude-tag TAG` : Exclude files matching this tag.

`--all-tags` : Require matching files to contain **all** specified include tags rather than at least
one.

`--shebang INTERPRETER` : Filter files whose shebang line contains the specified interpreter name or
substring.

### Traversal Controls

`--no-ignore` : Do not prune paths matching `.gitignore` or `.git/info/exclude`.

`--hidden` : Traverse hidden files and directories (names starting with `.`).

`-L, --follow-symlinks` : Follow symbolic links during directory traversal.

### Output Controls

`--absolute` : Output absolute filesystem paths rather than relative paths.

`-0, --print0` : Delimit paths with a NUL (`\0`) byte instead of a newline for safe consumption by
`xargs -0`.

`-l, --list-tags` : Print identified format and content tags alongside each matched path.

`-s, --summary` : Print summary match statistics and top format tags to `stderr`.

`--known-tags` : List all tags supported by the classifier engine and exit immediately.

`-v, --version` : Display the version of `findfmt` and exit.

`-h, --help` : Show the help message and exit.
