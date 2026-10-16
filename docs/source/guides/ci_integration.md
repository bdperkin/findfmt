# CI/CD Integration

`findfmt` streamlines continuous integration pipelines by providing dynamic, content-aware file
discovery. Rather than maintaining brittle, hard-coded file lists across configuration files, CI
jobs can locate target files on the fly while respecting `.gitignore` rules.

## 1. CI/CD Design Principles with `findfmt`

When integrating `findfmt` into automated workflows, adhere to the following best practices:

- **Use Pipe-Safe NUL Delimiters (`-0` or `findfmt0`)**: Filesystems may contain files with spaces,
  hyphens, or special characters. Always pair `-0` with `xargs -0` or `xargs -r -0` to prevent
  argument splitting and injection issues.
- **Leverage Ephemeral Execution via `uvx`**: Tools can run instantly in CI runners without a
  separate virtual environment setup step using `uvx findfmt`.
- **Mount Workspaces as Read-Only**: When running containerized jobs, mount project directories with
  `:ro` to ensure discovery operations cannot inadvertently modify source trees.

## 2. GitHub Actions Workflows

### 2.1. Dynamic Shell Script Linting with ShellCheck

The following workflow discovers all shell scripts—including scripts without file extensions that
invoke bash or sh shebangs—and verifies them with `shellcheck`:

```yaml
name: Lint Shell Scripts

on:
  push:
    branches: [main]
  pull_request:

jobs:
  shellcheck:
    name: ShellCheck Analysis
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"

      - name: Install shellcheck
        run: sudo apt-get update && sudo apt-get install -y shellcheck

      - name: Run shellcheck on discovered shell scripts
        run: |
          uvx findfmt -t shell -0 | xargs -r -0 shellcheck
```

### 2.2. Multi-Format Static Analysis Pipeline

Validate Python, YAML, and Markdown files in parallel using dynamic discovery:

```yaml
name: Multi-Format Verification

on:
  push:
    branches: [main]
  pull_request:

jobs:
  format-check:
    name: Validate Formats
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Check Python Files
        run: |
          uvx findfmt -t python -0 | xargs -r -0 uvx ruff check

      - name: Check YAML Files
        run: |
          uvx findfmt -t yaml -0 | xargs -r -0 uvx yamllint --strict
```

### 2.3. Generating Repository Inventory Artifacts

Generate a comprehensive JSON inventory of repository files and upload it as a build artifact:

```yaml
      - name: Generate Repository Inventory
        run: |
          uvx findfmt -f json -o repository-inventory.json

      - name: Upload Inventory Artifact
        uses: actions/upload-artifact@v4
        with:
          name: repository-inventory
          path: repository-inventory.json
```

## 3. GitLab CI Pipelines

In GitLab CI, `findfmt` can be executed within a Python container or using the pre-built `findfmt`
container image.

### 3.1. Using the `uv` Python Image

```yaml
stages:
  - lint
  - test

variables:
  UV_CACHE_DIR: "$CI_PROJECT_DIR/.uv-cache"

cache:
  paths:
    - .uv-cache

shellcheck:
  stage: lint
  image: ghcr.io/astral-sh/uv:python3.12-bookworm-slim
  before_script:
    - apt-get update && apt-get install -y shellcheck
  script:
    - uvx findfmt -t shell -0 | xargs -r -0 shellcheck

yaml-validation:
  stage: lint
  image: ghcr.io/astral-sh/uv:python3.12-bookworm-slim
  script:
    - uvx findfmt -t yaml -0 | xargs -r -0 uvx yamllint -s
```

### 3.2. Using the Dedicated `findfmt` Container Image

```yaml
inventory-audit:
  stage: test
  image:
    name: ghcr.io/bdperkin/findfmt:latest
    entrypoint: [""]
  script:
    - findfmt --summary
    - findfmt -f json -o /tmp/manifest.json
  artifacts:
    paths:
      - /tmp/manifest.json
    expire_in: 1 week
```

## 4. Pre-commit Hooks Integration

Integrate `findfmt` directly into local developer workflows using `.pre-commit-config.yaml`.

### 4.1. Local Repository Hook

Configure `findfmt` as a local hook to enforce that all Python files are formatted with Ruff:

```yaml
repos:
  - repo: local
    hooks:
      - id: findfmt-python-lint
        name: Lint Python Files Discovered by findfmt
        entry: bash -c 'uvx findfmt -t python -0 | xargs -r -0 uvx ruff check'
        language: system
        pass_filenames: false
        always_run: true
```

### 4.2. File Inventory Check

Ensure an up-to-date repository inventory document is maintained:

```yaml
      - id: findfmt-inventory
        name: Verify Documentation Inventory
        entry: uvx findfmt -f rst --table-style grid -o docs/source/_inventory.rst
        language: system
        pass_filenames: false
        files: ^(src/|docs/)
```

## 5. Docker & Containerized CI Workflows

For generic container platforms (Jenkins, CircleCI, Argo Workflows), execute `findfmt` as a
containerized command:

```bash
# Execute within a Docker pipeline stage
docker run --rm \
  -v "$(pwd):/workspace:ro" \
  -w /workspace \
  ghcr.io/bdperkin/findfmt:latest -t python -0 | xargs -0 ruff check

# Execute with Podman in rootless environments
podman run --rm \
  -v "$(pwd):/workspace:ro,Z" \
  -w /workspace \
  ghcr.io/bdperkin/findfmt:latest -s
```
