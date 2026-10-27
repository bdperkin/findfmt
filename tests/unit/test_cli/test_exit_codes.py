"""Exhaustive test matrix for the formal CLI exit-code contract (#369)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.entrypoints import (
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

runner = CliRunner()


@dataclass(frozen=True)
class _ExitCase:
    """Single row in the CLI exit-code verification matrix."""

    scenario: str
    args: list[str]
    expected_code: int
    patch_target: str | None = None
    side_effect: BaseException | None = None
    expect_out: bool = False
    expect_err: bool = False


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    """Create a sample directory tree with a Python script for exit-code testing."""
    script = tmp_path / "hello.py"
    script.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    "case",
    [
        _ExitCase("match-default", ["{tree}", "-t", "python"], 0, expect_out=True),
        _ExitCase("no-match-default", ["{tree}", "-t", "no-such-tag"], 0),
        _ExitCase(
            "match-exit-status",
            ["{tree}", "-t", "python", "--exit-status"],
            0,
            expect_out=True,
        ),
        _ExitCase("help-short", ["--help"], 0, expect_out=True),
        _ExitCase("help-all", ["--help-all"], 0, expect_out=True),
        _ExitCase("version", ["--version"], 0, expect_out=True),
        _ExitCase("diagnostics", ["--diagnostics"], 0, expect_out=True),
        _ExitCase("known-tags", ["--known-tags"], 0, expect_out=True),
        _ExitCase("show-config", ["--show-config", "--no-config"], 0, expect_out=True),
        _ExitCase(
            "broken-pipe",
            ["{tree}"],
            0,
            patch_target="findfmt.cli.runner._deliver_output",
            side_effect=BrokenPipeError("broken pipe"),
        ),
        _ExitCase("no-match-exit-status", ["{tree}", "-t", "nonexistent-tag", "--exit-status"], 1),
        _ExitCase(
            "runtime-traversal-error",
            ["{tree}"],
            1,
            patch_target="findfmt.cli.runner._deliver_output",
            side_effect=typer.Exit(code=1),
        ),
        _ExitCase("invalid-output-path-is-dir", ["{tree}", "-o", "{tree}"], 2, expect_err=True),
        _ExitCase("invalid-option", ["--no-such-flag"], 2, expect_err=True),
        _ExitCase("invalid-sort-key", ["{tree}", "--sort", "not-a-sort-key"], 2, expect_err=True),
        _ExitCase(
            "conflicting-dir-order-flags",
            ["{tree}", "--dirsfirst", "--filesfirst"],
            2,
            expect_err=True,
        ),
        _ExitCase(
            "missing-config-file",
            ["{tree}", "--config", "{tree}/missing.toml"],
            2,
            expect_err=True,
        ),
        _ExitCase(
            "sigint-interrupt",
            ["{tree}"],
            130,
            patch_target="findfmt.cli.runner.find_files",
            side_effect=KeyboardInterrupt(),
        ),
    ],
    ids=lambda c: c.scenario,
)
def test_documented_exit_codes(sample_tree: Path, case: _ExitCase) -> None:
    """Verify exit code, stdout, and stderr match the documented contract across all rows."""
    resolved_args = [arg.format(tree=sample_tree) for arg in case.args]
    if case.patch_target is not None:
        with patch(case.patch_target, side_effect=case.side_effect):
            result = runner.invoke(app, resolved_args)
    else:
        result = runner.invoke(app, resolved_args)

    assert result.exit_code == case.expected_code, f"{case.scenario}: {result.output}"
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr
    assert bool(result.stdout.strip()) is case.expect_out, f"{case.scenario}: {result.stdout!r}"
    assert bool(result.stderr.strip()) is case.expect_err, f"{case.scenario}: {result.stderr!r}"


@pytest.mark.parametrize(
    ("entry_fn", "base_args"),
    [
        (main_findfiles, []),
        (main_findfilemime, []),
        (main_findfilefmt, ["python"]),
        (main_findshebang, ["python"]),
        (main_findfmt0, []),
        (main_findsummary, []),
    ],
)
def test_wrapper_entrypoints_exit_code_contract(
    sample_tree: Path,
    capsys: pytest.CaptureFixture[str],
    entry_fn: Callable[[list[str]], int],
    base_args: list[str],
) -> None:
    """Verify console wrapper entry points obey the 0 / 1 / 2 / 130 exit-code contract."""
    assert entry_fn([*base_args, str(sample_tree), "--no-pager"]) == 0
    capsys.readouterr()

    assert entry_fn([*base_args, str(sample_tree), "-P", "no_match_*", "--exit-status"]) == 1
    captured_1 = capsys.readouterr()
    assert captured_1.out == ""
    assert "Traceback" not in captured_1.err
    if entry_fn is main_findsummary:
        assert "Matched files: 0" in captured_1.err
    else:
        assert captured_1.err == ""

    assert entry_fn([*base_args, str(sample_tree), "--sort", "invalid"]) == 2
    captured_2 = capsys.readouterr()
    assert captured_2.out == ""
    assert captured_2.err != ""
    assert "Traceback" not in captured_2.err

    with patch("findfmt.cli.runner.find_files", side_effect=KeyboardInterrupt):
        assert entry_fn([*base_args, str(sample_tree)]) == 130

    captured_130 = capsys.readouterr()
    assert captured_130.out == ""
    assert captured_130.err == ""
