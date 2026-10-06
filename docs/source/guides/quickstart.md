# Quickstart

## Basic File Discovery

Find all Python files in the current repository, honoring `.gitignore`:

```bash
findfmt -t python
```

## Shebang-Based Discovery

Find all executable scripts invoking bash or python via shebang:

```bash
findfmt --shebang bash
findfmt --shebang python
```

## Listing Identified Tags

Inspect all classification tags assigned to files:

```bash
findfmt -l -t python
```

Sample output:

```text
src/findfmt/cli.py [file, mime:text/x-python, non-executable, python, text]
scripts/runner.sh [bash, executable, file, mime:text/x-shellscript, shell, text]
```

## Pipelining with `xargs`

Safely pipe matching files with NUL delimiters:

```bash
findfmt -t python -0 | xargs -0 ruff check
findfmt -t yaml -0 | xargs -0 yamllint
```

## Display Summary Statistics

Print matching frequencies and top detected tags to stderr:

```bash
findfmt -s
```
