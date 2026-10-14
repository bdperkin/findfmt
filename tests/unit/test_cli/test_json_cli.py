"""CLI integration tests for JSON document output flag (-J, --json)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from findfmt.cli import app

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_json_short_flag(sample_repo: Path) -> None:
    """Verify -J flag outputs structured JSON representation equivalent to --format json."""
    runner = CliRunner()
    res = runner.invoke(app, ["-J", str(sample_repo)])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert isinstance(data, list)
    assert any("app.py" in str(item.get("path", "")) for item in data)


def test_cli_json_long_flag(sample_repo: Path) -> None:
    """Verify --json flag outputs structured JSON representation."""
    runner = CliRunner()
    res = runner.invoke(app, ["--json", str(sample_repo)])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert isinstance(data, list)
    assert any("app.py" in str(item.get("path", "")) for item in data)


def test_cli_no_json_flag(sample_repo: Path) -> None:
    """Verify --no-json disables JSON mode and uses default text format."""
    runner = CliRunner()
    res = runner.invoke(app, ["--no-json", str(sample_repo)])
    assert res.exit_code == 0
    assert not res.stdout.strip().startswith("[")
    assert "app.py" in res.stdout


def test_cli_json_conflicts(sample_repo: Path) -> None:
    """Verify -J conflicts with other exclusive format shortcut flags."""
    runner = CliRunner()

    res_jx = runner.invoke(app, ["-J", "-X", str(sample_repo)])
    assert res_jx.exit_code == 2
    assert "Error: Conflicting format options" in res_jx.stderr

    res_jh = runner.invoke(app, ["-J", "-H", "http://localhost:8000", str(sample_repo)])
    assert res_jh.exit_code == 2
    assert "Error: Conflicting format options" in res_jh.stderr

    res_jtree = runner.invoke(app, ["-J", "--tree", str(sample_repo)])
    assert res_jtree.exit_code == 2
    assert "Error: Conflicting format options" in res_jtree.stderr


def test_cli_json_output_redirect(sample_repo: Path, tmp_path: Path) -> None:
    """Verify -J works together with -o file redirection."""
    out_json = tmp_path / "out.json"
    runner = CliRunner()
    res = runner.invoke(app, ["-J", "-o", str(out_json), str(sample_repo)])
    assert res.exit_code == 0
    assert out_json.is_file()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert any("app.py" in str(item.get("path", "")) for item in data)
