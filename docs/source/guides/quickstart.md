# Quickstart

## 1. Basic File Discovery

Find all Python files in the current repository, honoring `.gitignore`:

```bash
findfmt -t python
```

## 2. Shebang-Based Discovery

Find all executable scripts invoking bash or python via shebang:

```bash
findfmt --shebang bash
findfmt --shebang python
```

## 3. Listing Identified Tags

Inspect all classification tags assigned to files:

```bash
findfmt -l -t python
```

Sample output:

```text
src/findfmt/cli.py [file, mime:text/x-python, non-executable, python, text]
scripts/runner.sh [bash, executable, file, mime:text/x-shellscript, shell, text]
```

## 4. Pipelining with `xargs`

Safely pipe matching files with NUL delimiters:

```bash
findfmt -t python -0 | xargs -0 ruff check
findfmt -t yaml -0 | xargs -0 yamllint
```

## 5. Display Summary Statistics

Print matching frequencies and top detected tags to stderr:

```bash
findfmt -s
```
