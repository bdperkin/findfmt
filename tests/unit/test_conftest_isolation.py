"""Unit tests verifying conftest test environment and git configuration isolation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from findfmt.traversal.ignore import find_global_gitignore_path


def test_home_is_isolated(tmp_path: Path) -> None:
    """Verify Path.home() is isolated under tmp_path by isolate_git_environment."""
    home = Path.home().resolve()
    expected = tmp_path.resolve()
    assert home == expected or home.is_relative_to(expected)
    assert os.environ.get("HOME") == str(tmp_path)
    assert os.environ.get("XDG_CONFIG_HOME") == str(tmp_path)
    assert os.environ.get("GIT_CONFIG_NOSYSTEM") == "1"


@pytest.mark.skipif(shutil.which("git") is None, reason="git binary not available")
def test_git_global_config_is_isolated() -> None:
    """Verify GIT_CONFIG_GLOBAL is os.devnull and git config --global --list has no entries."""
    assert os.environ.get("GIT_CONFIG_GLOBAL") == os.devnull
    proc = subprocess.run(
        ["git", "config", "--global", "--list"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1)
    assert proc.stdout.strip() == ""


def test_global_gitignore_defaults_to_none_in_isolated_environment() -> None:
    """Verify standard global gitignore resolution returns None in isolated environment."""
    assert find_global_gitignore_path() is None
