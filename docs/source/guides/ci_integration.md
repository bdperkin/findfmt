# CI/CD Integration

`findfmt` is optimized for integration into automated continuous integration workflows.

## 1. GitHub Actions

Run automated linting across all discovered shell scripts:

```yaml
name: Lint Shell Scripts
on: [push, pull_request]

jobs:
  shellcheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Run shellcheck via findfmt
        run: |
          uvx findfmt -t shell -0 | xargs -r -0 shellcheck
```

## 2. Matrix Testing Strategy

Using `findfmt` allows tests and static analysis to dynamically discover targets without maintaining
redundant hard-coded file lists across configuration files.
