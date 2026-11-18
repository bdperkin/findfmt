"""Unit tests for .readthedocs.yaml configuration and multi-language post_build (#633)."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_yaml(rel_path: str) -> dict[str, Any]:
    """Load and parse a YAML mapping relative to repository root."""
    path = _repo_root() / rel_path
    assert path.is_file(), f"Missing YAML file at {path}"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), f"{rel_path} must parse to a YAML mapping"
    return data


def test_readthedocs_yaml_and_pre_commit_hook() -> None:
    """Validate .readthedocs.yaml configuration, canonical URL, and check-readthedocs hook (#633)."""
    rtd = _load_yaml(".readthedocs.yaml")
    assert rtd.get("version") == 2

    build = rtd.get("build", {})
    assert build.get("os") == "ubuntu-24.04"
    assert build.get("tools") == {"python": "3.14"}

    jobs = build.get("jobs", {})
    assert any("uv venv" in cmd for cmd in jobs.get("create_environment", []))
    install_cmds = jobs.get("install", [])
    assert len(install_cmds) == 1
    assert "uv sync --locked --no-default-groups --group docs" in install_cmds[0]

    sphinx_cfg = rtd.get("sphinx", {})
    assert sphinx_cfg == {
        "builder": "html",
        "configuration": "docs/source/conf.py",
        "fail_on_warning": True,
    }
    assert (_repo_root() / sphinx_cfg["configuration"]).is_file()
    assert rtd.get("formats") == ["htmlzip"]

    pre_commit = _load_yaml(".pre-commit-config.yaml")
    hook_ids = {
        str(h.get("id"))
        for repo in pre_commit.get("repos", [])
        if isinstance(repo, dict)
        for h in repo.get("hooks", [])
        if isinstance(h, dict)
    }
    assert "check-readthedocs" in hook_ids

    pyproject = tomllib.loads((_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["urls"]["Documentation"] == "https://bdperkin.github.io/findfmt"


def test_readthedocs_post_build_languages_and_fail_fast(tmp_path: Path) -> None:
    """Validate post_build builds all conf.py languages and stops immediately on failure (#633)."""
    rtd = _load_yaml(".readthedocs.yaml")
    post_build_cmds = [str(cmd) for cmd in rtd["build"]["jobs"].get("post_build", [])]
    assert len(post_build_cmds) == 2
    assert "sphinx-intl" in post_build_cmds[0]
    assert "docs/source/locale" in post_build_cmds[0]

    loop_cmd = post_build_cmds[1]
    loop_match = re.search(r"for lang in ([^;]+);", loop_cmd)
    assert loop_match is not None
    rtd_langs = set(loop_match.group(1).split())
    conf_text = (_repo_root() / "docs" / "source" / "conf.py").read_text(encoding="utf-8")
    conf_langs = set(re.findall(r'\("([a-z]{2})",\s*"[^"]+",\s*"[^"]+"\)', conf_text))
    assert rtd_langs == {"en", "es", "fr", "de", "ja"}
    assert rtd_langs == conf_langs
    assert "-D" in loop_cmd
    assert "language=${lang}" in loop_cmd
    assert "-A in_lang_subdir=1" in loop_cmd
    assert "${READTHEDOCS_OUTPUT}/html/${lang}" in loop_cmd
    assert "-W --keep-going || exit $?;" in loop_cmd

    sh_bin = shutil.which("sh")
    if os.name != "nt" and sh_bin is not None:
        fake_venv = tmp_path / "venv"
        (fake_venv / "bin").mkdir(parents=True)
        seen_log = tmp_path / "seen_langs.txt"
        fake_sphinx = fake_venv / "bin" / "sphinx-build"
        fake_sphinx.write_text(
            f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{seen_log}"\n'
            'case "$*" in *language=es*) exit 7 ;; esac\nexit 0\n',
            encoding="utf-8",
        )
        fake_sphinx.chmod(fake_sphinx.stat().st_mode | stat.S_IXUSR)
        loop_proc = subprocess.run(
            [sh_bin, "-c", loop_cmd],
            env={
                **os.environ,
                "READTHEDOCS_VIRTUALENV_PATH": str(fake_venv),
                "READTHEDOCS_OUTPUT": str(tmp_path / "out"),
            },
            capture_output=True,
            text=True,
            check=False,
        )
        assert loop_proc.returncode == 7
        invocations = seen_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(invocations) == 2
        assert "language=en" in invocations[0]
        assert "language=es" in invocations[1]
