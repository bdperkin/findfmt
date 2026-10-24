"""Tests for the installed-wheel smoke test, tools/smoke_wheel.py (#496)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from tools import smoke_wheel
from tools.smoke_wheel import SmokeError, main, run, script, wheel_version


def test_wheel_version_parses_wheel_file_names() -> None:
    """The version is the second dash-separated field of a wheel file name."""
    assert wheel_version(Path("dist/findfmt-1.1.0-py3-none-any.whl")) == "1.1.0"
    assert wheel_version(Path("findfmt-1.1.1.dev3+gabc-py3-none-any.whl")) == "1.1.1.dev3+gabc"
    with pytest.raises(SmokeError, match="not a wheel"):
        wheel_version(Path("findfmt-1.1.0.tar.gz"))


def test_smoke_test_passes_on_the_development_install(capsys: pytest.CaptureFixture[str]) -> None:
    """Every check passes against the console scripts installed in this environment."""
    assert main(["--allow-source"]) == 0
    out = capsys.readouterr().out
    for check in ("installed package", "console scripts", "translations"):
        assert f"ok: {check}" in out


def test_smoke_test_rejects_the_source_tree(capsys: pytest.CaptureFixture[str]) -> None:
    """Without --allow-source, importing findfmt from src/ fails: the wheel was not tested."""
    assert main([]) == 1
    assert "imported from the source tree" in capsys.readouterr().err


def test_smoke_test_checks_the_wheel_version(capsys: pytest.CaptureFixture[str]) -> None:
    """A wheel whose version differs from the installed package fails the smoke test."""
    assert main(["--allow-source", "--wheel", "findfmt-0.0.1-py3-none-any.whl"]) == 1
    assert "expected 0.0.1" in capsys.readouterr().err


def test_missing_console_script_is_reported() -> None:
    """A console script that is not installed fails with its name."""
    with pytest.raises(SmokeError, match="no-such-script"):
        script("no-such-script")


@pytest.mark.parametrize(
    ("returncode", "stderr", "message"),
    [(0, "Traceback (most recent call last):", "traceback"), (2, "Error: bad", "exited 2")],
)
def test_run_rejects_tracebacks_and_unexpected_status(
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stderr: str,
    message: str,
) -> None:
    """A traceback, or an exit status other than the expected one, fails the check."""
    monkeypatch.setattr(
        smoke_wheel.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], returncode, "", stderr),
    )
    with pytest.raises(SmokeError, match=message):
        run("findfmt", "--help")
