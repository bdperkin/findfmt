# Installation

`findfmt` supports multiple installation methods across Linux, macOS, Windows, and containerized
environments.

## 1. Installation Methods

### 1.1. Standalone Execution with `uvx` (Recommended)

Run `findfmt` immediately without an explicit installation step using `uvx`:

```bash
uvx findfmt --help
uvx findfmt -t python
```

### 1.2. Isolated User Installation with `uv`

Install `findfmt` into an isolated user tool environment managed by `uv`:

```bash
uv tool install findfmt
```

Upgrade to the latest release at any time:

```bash
uv tool upgrade findfmt
```

### 1.3. Isolated User Installation with `pipx`

Install `findfmt` as an isolated application using `pipx`:

```bash
pipx install findfmt
pipx upgrade findfmt
```

### 1.4. Project Dependency with `uv` or `pip`

Add `findfmt` as a project dependency in a managed virtual environment:

```bash
# Using uv
uv add findfmt

# Using pip
pip install findfmt
```

### 1.5. Container Image via GitHub Container Registry

Pre-built minimal container images are published to the GitHub Container Registry (`ghcr.io`):

```bash
docker pull ghcr.io/bdperkin/findfmt:latest
```

### 1.6. Source Installation

For local development or building from source:

```bash
git clone https://github.com/bdperkin/findfmt.git
cd findfmt
uv sync --all-groups
uv run findfmt --help
```

## 2. Platform Notes

### 2.1. Linux

`findfmt` is compatible with all modern Linux distributions across `x86_64`, `aarch64`, and `armv7l`
architectures:

- **Library Compatibility**: Works seamlessly on both `glibc`-based distributions (Ubuntu, Debian,
  Fedora, openSUSE, Arch) and `musl`-based distributions (Alpine Linux).

- **User Binary PATH**: When installing via `uv tool install` or `pipx`, ensure `~/.local/bin` is
  present in your shell `PATH`:

  ```bash
  export PATH="$HOME/.local/bin:$PATH"
  ```

- **Paging Support**: Terminal paging automatically leverages your system `PAGER` or `LESS`
  environment settings when output exceeds the terminal window height.

### 2.2. macOS

`findfmt` supports macOS 12 (Monterey) and later across both Apple Silicon (`arm64`) and Intel
(`x86_64`) hardware:

- **Terminal Emulators**: Native macOS Terminal.app and third-party emulators such as iTerm2 support
  ANSI color styling and clickable OSC 8 terminal hyperlinks (`--hyperlink`).

- **File System Case-Sensitivity**: macOS defaults to APFS case-preserving but case-insensitive
  semantics. Pattern searches (`-P`, `-I`) evaluate patterns strictly unless `--ignore-case` is
  specified.

- **Homebrew Python**: Ensure that `uv` or `pipx` references your preferred Python installation:

  ```bash
  brew install uv
  uv tool install findfmt
  ```

### 2.3. Windows & Windows Subsystem for Linux (WSL)

`findfmt` executes natively on Windows 10/11 and within Windows Subsystem for Linux (WSL/WSL2):

- **Native Windows Execution**: Run `findfmt` within PowerShell, Command Prompt, or Windows
  Terminal:

  ```powershell
  uv tool install findfmt
  findfmt -t python
  ```

- **Path Separators**: Both forward slashes (`/`) and backslashes (`\`) are recognized in path
  arguments. Output listings adhere to POSIX style for cross-platform script consistency.

- **Symbolic Link Permissions**: Following directory symlinks (`-l` or `--follow-links`) on native
  Windows requires either Windows Developer Mode enabled or an elevated Administrator prompt due to
  underlying Windows security policies.

- **Windows Subsystem for Linux (WSL2)**: For workflows tightly coupled with Unix pipes and shell
  scripts, running `findfmt` inside WSL2 provides native Linux filesystem performance and POSIX
  semantics.

### 2.4. Docker & Container Environments

When executing `findfmt` within containerized pipelines, mount your project directory into the
container workspace:

```bash
# Docker invocation
docker run --rm \
  -v "$(pwd):/workspace:ro" \
  -w /workspace \
  ghcr.io/bdperkin/findfmt:latest -t python

# Podman invocation with rootless user namespace
podman run --rm \
  -v "$(pwd):/workspace:ro,Z" \
  -w /workspace \
  ghcr.io/bdperkin/findfmt:latest -t shell -0
```

> [!TIP] Mount project source directories with the read-only flag (`:ro` or `:ro,Z` for container
> volume labels) to guarantee that discovery operations cannot mutate repository files.

## 3. Verification & Diagnostics

Verify that your installation is functioning and display runtime diagnostic information:

```bash
# Display version and release tag
findfmt --version

# Display comprehensive runtime diagnostics
findfmt --diagnostics

# List all supported format and content tags
findfmt --known-tags
```
