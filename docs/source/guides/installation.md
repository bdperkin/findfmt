# Installation

`findfmt` can be installed in several ways depending on your environment.

## 1. Using `uv` (Recommended)

To run `findfmt` as a standalone tool via `uvx`:

```bash
uvx findfmt --help
```

To install it into your local user tools:

```bash
uv tool install findfmt
```

Or add it to a project virtual environment:

```bash
uv add findfmt
```

## 2. Using `pip`

```bash
pip install findfmt
```

## 3. Using Container Image

Pre-built slim containers are published to GitHub Container Registry:

```bash
docker pull ghcr.io/bdperkin/findfmt:latest
docker run --rm -v $(pwd):/workspace -w /workspace ghcr.io/bdperkin/findfmt:latest -t python
```
