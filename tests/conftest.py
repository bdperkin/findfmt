"""Shared fixtures and test configuration for findfmt tests."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a populated mock repository with gitignore, scripts, and various file types."""
    repo = tmp_path / "mock_repo"
    repo.mkdir()

    # Git directory structure
    git_dir = repo / ".git" / "info"
    git_dir.mkdir(parents=True)
    (git_dir / "exclude").write_text("*.gitexcluded\n", encoding="utf-8")

    # .gitignore
    (repo / ".gitignore").write_text(
        "# Ignored paths\nbuild/\n*.log\nnode_modules/\n",
        encoding="utf-8",
    )

    # Source files
    src_dir = repo / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (src_dir / "config.json").write_text('{"key": "value"}\n', encoding="utf-8")

    # Nested directory with local gitignore
    nested = src_dir / "nested"
    nested.mkdir()
    (nested / ".gitignore").write_text("*.nestedignore\n", encoding="utf-8")
    (nested / "nested.py").write_text("def run(): pass\n", encoding="utf-8")
    (nested / "ignored.nestedignore").write_text("skip me\n", encoding="utf-8")

    # Ignored directory and files
    build_dir = repo / "build"
    build_dir.mkdir()
    (build_dir / "output.bin").write_bytes(b"\x00\x01\x02\x03")
    (repo / "debug.log").write_text("log data\n", encoding="utf-8")
    (repo / "test.gitexcluded").write_text("git exclude test\n", encoding="utf-8")

    # Executable shell script with shebang
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir()
    sh_file = scripts_dir / "runner.sh"
    sh_file.write_text("#!/bin/bash\necho 'running'\n", encoding="utf-8")
    current_mode = sh_file.stat().st_mode
    sh_file.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Python script with shebang and no extension
    cli_tool = scripts_dir / "mytool"
    cli_tool.write_text("#!/usr/bin/env python3\nimport sys\n", encoding="utf-8")
    cli_mode = cli_tool.stat().st_mode
    cli_tool.chmod(cli_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Hidden directory and file
    hidden_dir = repo / ".config"
    hidden_dir.mkdir()
    (hidden_dir / "settings.yaml").write_text("debug: true\n", encoding="utf-8")

    # Plain text readme
    (repo / "README.md").write_text("# Readme\n", encoding="utf-8")

    return repo
