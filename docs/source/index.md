# findfmt Documentation

```{image} _static/logo.svg
:alt: findfmt Logo
:align: center
:width: 600px
```

**findfmt** is a high-performance, `.gitignore`-aware file discovery and classification suite. It
locates files by content format, shebang, and MIME tag rather than relying strictly on file
extensions.

## Core Capabilities

- **Intelligent Classification**: Powered by the `identify` engine and content heuristics to
  identify file types (e.g. Python, Shell, YAML, JSON, Executable) even when filenames lack
  extensions.
- **Git-Aware Traversal**: Automatically prunes directories and files matched by `.gitignore` and
  `.git/info/exclude` rules early in traversal.
- **Deterministic Output**: Always produces clean, relative, alphabetically sorted file paths ready
  for Unix pipelines and `xargs`.
- **Modern Python Architecture**: Built with a strict `uv`-first methodology, 100% test coverage,
  and strict static type checking.

```{toctree}
:maxdepth: 2
:caption: User Guide

guides/index
```

```{toctree}
:maxdepth: 2
:caption: CLI Reference

cli/index
```

```{toctree}
:maxdepth: 2
:caption: API Documentation

api/index
```

```{toctree}
:maxdepth: 1
:caption: Quality & Architecture

quality/index
```
