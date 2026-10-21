"""Unit and pipeline integration tests for Unix signal and broken pipe handling."""

from __future__ import annotations

import io
import os
import signal
import subprocess
import sys
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO, cast
from unittest.mock import MagicMock, patch

import pytest
import typer
import typer.core
from click.utils import _PacifyFlushWrapper
from typer.testing import CliRunner

from findfmt.cli import (
    FindfmtCommand,
    app,
    display_with_pager,
    execute_findfmt,
    handle_broken_pipe,
    handle_keyboard_interrupt,
    install_signal_handlers,
    is_broken_pipe_wrapper,
    trap_cli_signals,
)
from findfmt.cli.runner import _deliver_output
from findfmt.cli.signals import _sigint_handler
from findfmt.entrypoints import _invoke_with_defaults
from findfmt.formatters import OutputFormat, get_formatter
from findfmt.models import FileInfo, TraversalConfig
from findfmt.terminal import PagerController


@pytest.fixture(autouse=True)
def _protect_pytest_stdout():
    """Safely mock os.dup2 during in-process tests to protect pytest."""
    with patch("os.dup2") as mock_dup2:
        yield mock_dup2


def test_handle_broken_pipe_default():
    """Verify handle_broken_pipe flushes and exits cleanly with code 0."""
    with pytest.raises(typer.Exit) as exc:
        handle_broken_pipe()

    assert exc.value.exit_code == 0


def test_handle_broken_pipe_real_dup2():
    """Verify handle_broken_pipe executes real os.dup2 without error."""
    orig_fd = os.dup(1)
    try:
        with patch("os.dup2", side_effect=os.dup2):
            with pytest.raises(typer.Exit) as exc:
                handle_broken_pipe()

            assert exc.value.exit_code == 0
    finally:
        os.dup2(orig_fd, 1)
        os.close(orig_fd)


def test_handle_broken_pipe_with_stream():
    """Verify handle_broken_pipe flushes custom stream and exits with 0."""
    mock_stream = MagicMock()
    with pytest.raises(typer.Exit) as exc:
        handle_broken_pipe(mock_stream)

    mock_stream.flush.assert_called_once()
    assert exc.value.exit_code == 0


def test_handle_broken_pipe_stream_flush_raises():
    """Verify handle_broken_pipe ignores flush errors on broken streams."""
    mock_stream = MagicMock()
    mock_stream.flush.side_effect = BrokenPipeError("Pipe broken")
    with pytest.raises(typer.Exit) as exc:
        handle_broken_pipe(mock_stream)

    assert exc.value.exit_code == 0


def test_handle_broken_pipe_os_dup_error():
    """Verify handle_broken_pipe gracefully handles os.dup2 failures."""
    with patch("os.dup2", side_effect=OSError("dup2 failed")):
        with pytest.raises(typer.Exit) as exc:
            handle_broken_pipe()

        assert exc.value.exit_code == 0


def test_handle_broken_pipe_no_fileno():
    """Verify handle_broken_pipe handles streams without fileno."""
    with patch("sys.stdout", io.StringIO()):
        with pytest.raises(typer.Exit) as exc:
            handle_broken_pipe()

        assert exc.value.exit_code == 0


def test_handle_keyboard_interrupt():
    """Verify handle_keyboard_interrupt exits cleanly with status 130."""
    with pytest.raises(typer.Exit) as exc:
        handle_keyboard_interrupt()

    assert exc.value.exit_code == 130


def test_trap_cli_signals_normal():
    """Verify trap_cli_signals allows normal execution without exception."""
    executed = False
    with trap_cli_signals():
        executed = True

    assert executed is True


def test_trap_cli_signals_broken_pipe_non_standalone():
    """Verify trap_cli_signals raises typer.Exit(0) when not standalone."""
    with pytest.raises(typer.Exit) as exc, trap_cli_signals():
        raise BrokenPipeError

    assert exc.value.exit_code == 0


def test_trap_cli_signals_broken_pipe_standalone():
    """Verify trap_cli_signals exits via sys.exit(0) when in standalone mode."""
    with pytest.raises(SystemExit) as exc, trap_cli_signals(standalone_mode=True):
        raise BrokenPipeError

    assert exc.value.code == 0


def test_trap_cli_signals_keyboard_interrupt_non_standalone():
    """Verify trap_cli_signals raises typer.Exit(130) when not standalone."""
    with pytest.raises(typer.Exit) as exc, trap_cli_signals():
        raise KeyboardInterrupt

    assert exc.value.exit_code == 130


def test_trap_cli_signals_keyboard_interrupt_standalone():
    """Verify trap_cli_signals exits via sys.exit(130) when in standalone mode."""
    with pytest.raises(SystemExit) as exc, trap_cli_signals(standalone_mode=True):
        raise KeyboardInterrupt

    assert exc.value.code == 130


def test_deliver_output_broken_pipe():
    """Verify _deliver_output traps BrokenPipeError and exits cleanly."""
    formatter = get_formatter(OutputFormat.TEXT)
    pager_ctrl = PagerController()

    class BrokenStream:
        def isatty(self) -> bool:
            return False

        def write(self, _s: str) -> int:
            raise BrokenPipeError

        def writelines(self, _lines: object) -> None:
            raise BrokenPipeError

        def flush(self) -> None:
            raise BrokenPipeError

    with pytest.raises(typer.Exit) as exc:
        _deliver_output(
            formatter,
            [],
            pager_ctrl,
            cast("TextIO", BrokenStream()),
            pager=False,
            custom_controller=False,
        )

    assert exc.value.exit_code == 0


def test_execute_findfmt_keyboard_interrupt(tmp_path: Path):
    """Verify execute_findfmt catches KeyboardInterrupt, closes sink, and leaves no partial file."""
    out_file = tmp_path / "out.txt"

    def _interrupted_find(_config: TraversalConfig) -> Iterable[FileInfo]:
        raise KeyboardInterrupt

    with pytest.raises(typer.Exit) as exc:
        execute_findfmt(
            paths=[tmp_path],
            tags=None,
            exclude_tags=None,
            all_tags=False,
            shebang=None,
            no_ignore=False,
            hidden=False,
            follow_symlinks=False,
            output_format=OutputFormat.TEXT,
            output=out_file,
            print0=False,
            list_tags=False,
            summary=False,
            find_files_func=_interrupted_find,
        )

    assert exc.value.exit_code == 130
    assert not out_file.exists()
    assert list(tmp_path.iterdir()) == []


def test_execute_findfmt_summary_broken_pipe(tmp_path: Path):
    """Verify execute_findfmt catches BrokenPipeError during summary reporting."""
    with patch("findfmt.cli.runner.write_summary", side_effect=BrokenPipeError):
        with pytest.raises(typer.Exit) as exc:
            execute_findfmt(
                paths=[tmp_path],
                tags=None,
                exclude_tags=None,
                all_tags=False,
                shebang=None,
                no_ignore=False,
                hidden=False,
                follow_symlinks=False,
                output_format=OutputFormat.TEXT,
                print0=False,
                list_tags=False,
                summary=True,
                find_files_func=lambda _cfg: [],
            )

        assert exc.value.exit_code == 0


def test_display_with_pager_broken_pipe():
    """Verify display_with_pager catches BrokenPipeError and exits cleanly."""
    mock_ctrl = MagicMock()
    mock_ctrl.display.side_effect = BrokenPipeError("Closed pipe")
    with patch("findfmt.cli.pager.PagerController", return_value=mock_ctrl):
        with pytest.raises(typer.Exit) as exc:
            display_with_pager("Sample Help Content")

        assert exc.value.exit_code == 0


def test_pager_controller_display_pager_broken_pipe():
    """Verify PagerController.display swallows BrokenPipeError during paging."""
    controller = PagerController(pager=True, stream=sys.stdout)
    mock_pager = MagicMock()
    mock_pager.show.side_effect = BrokenPipeError("Closed pager")
    controller.pager_impl = mock_pager
    with patch.object(controller, "should_page", return_value=True):
        controller.display("Test content\nLine 2\n")


def test_entrypoints_invoke_with_defaults_broken_pipe():
    """Verify _invoke_with_defaults catches BrokenPipeError and returns 0."""
    with patch("findfmt.cli.runner.execute_findfmt", side_effect=BrokenPipeError):
        code = _invoke_with_defaults("findfmt", {}, argv=["."])
        assert code == 0


def test_entrypoints_invoke_with_defaults_keyboard_interrupt():
    """Verify _invoke_with_defaults catches KeyboardInterrupt and returns 130."""
    with patch("findfmt.cli.runner.execute_findfmt", side_effect=KeyboardInterrupt):
        code = _invoke_with_defaults("findfmt", {}, argv=["."])
        assert code == 130


def test_cli_runner_invoke_broken_pipe():
    """Verify CliRunner invocation handles BrokenPipeError cleanly."""
    runner = CliRunner()
    with patch("findfmt.cli.runner.execute_findfmt", side_effect=BrokenPipeError):
        result = runner.invoke(app, ["."])
        assert result.exit_code == 0


def test_cli_runner_invoke_keyboard_interrupt():
    """Verify CliRunner invocation handles KeyboardInterrupt cleanly."""
    runner = CliRunner()
    with patch("findfmt.cli.runner.execute_findfmt", side_effect=KeyboardInterrupt):
        result = runner.invoke(app, ["."])
        assert result.exit_code == 130


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal tests")
def test_subprocess_pipeline_head_truncation(tmp_path: Path):
    """Verify findfmt piped to closed reader exits with code 0 and no traceback."""
    for i in range(50):
        (tmp_path / f"file_{i}.txt").write_text("content\n")

    cmd = [sys.executable, "-m", "findfmt", str(tmp_path)]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    first_line = proc.stdout.readline()
    assert len(first_line) > 0
    proc.stdout.close()
    _, err = proc.communicate(timeout=5)
    assert proc.returncode == 0
    assert b"BrokenPipeError" not in err
    assert b"Traceback" not in err


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal tests")
def test_subprocess_sigint_clean_exit(tmp_path: Path):
    """Verify findfmt interrupted by SIGINT exits with code 130 and no traceback."""
    target = "/usr" if Path("/usr").is_dir() else str(tmp_path)
    cmd = [sys.executable, "-m", "findfmt", target]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    first_line = proc.stdout.readline()
    assert len(first_line) > 0
    proc.send_signal(signal.SIGINT)
    _, err = proc.communicate(timeout=5)
    assert proc.returncode == 130
    assert b"KeyboardInterrupt" not in err
    assert b"Traceback" not in err


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal tests")
def test_subprocess_help_pipeline_truncation():
    """Verify findfmt --help piped to closed reader exits with code 0."""
    cmd = [sys.executable, "-m", "findfmt", "--help"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    first_line = proc.stdout.readline()
    assert len(first_line) > 0
    proc.stdout.close()
    _, err = proc.communicate(timeout=5)
    assert proc.returncode == 0, f"Error: {err.decode()}"
    assert b"BrokenPipeError" not in err
    assert b"Traceback" not in err


def test_sigint_handler():
    """Verify _sigint_handler exits with Unix status 130."""
    with pytest.raises(SystemExit) as exc:
        _sigint_handler(signal.SIGINT, None)

    assert exc.value.code == 130


def test_install_signal_handlers_worker_thread():
    """Verify install_signal_handlers is skipped outside main thread."""
    result: list[None] = []
    thread = threading.Thread(target=lambda: result.append(install_signal_handlers()))
    thread.start()
    thread.join()
    assert result == [None]


def test_install_signal_handlers_value_error():
    """Verify install_signal_handlers gracefully handles ValueError."""
    with patch("signal.signal", side_effect=ValueError("Invalid signal")):
        install_signal_handlers()


def test_entrypoints_invoke_with_defaults_typer_exit():
    """Verify _invoke_with_defaults returns exit_code when cmd raises typer.Exit."""
    with patch("typer.main.get_command") as mock_get_cmd:
        mock_cmd = MagicMock()
        mock_cmd.main.side_effect = typer.Exit(code=42)
        mock_get_cmd.return_value = mock_cmd
        code = _invoke_with_defaults("findfmt", {}, argv=["."])
        assert code == 42


def test_findfmt_command_main_click_pacify_flush_standalone():
    """Verify FindfmtCommand.main exits 0 when Click raises SystemExit(1) on broken pipe."""
    cmd = FindfmtCommand(name="test")
    wrapped_stdout = _PacifyFlushWrapper(sys.stdout)
    with (
        patch.object(typer.core.TyperCommand, "main", side_effect=SystemExit(1)),
        patch("sys.stdout", wrapped_stdout),
        pytest.raises(SystemExit) as exc,
    ):
        cmd.main(args=["."], standalone_mode=True)

    assert exc.value.code == 0


def test_findfmt_command_main_click_pacify_flush_non_standalone():
    """Verify FindfmtCommand.main returns 0 when Click raises SystemExit(1) non-standalone."""
    cmd = FindfmtCommand(name="test")
    wrapped_stdout = _PacifyFlushWrapper(sys.stdout)
    with (
        patch.object(typer.core.TyperCommand, "main", side_effect=SystemExit(1)),
        patch("sys.stdout", wrapped_stdout),
    ):
        code = cmd.main(args=["."], standalone_mode=False)
        assert code == 0


def test_findfmt_command_main_reraises_other_system_exit():
    """Verify FindfmtCommand.main re-raises regular SystemExit error."""
    cmd = FindfmtCommand(name="test")
    with (
        patch.object(typer.core.TyperCommand, "main", side_effect=SystemExit(2)),
        pytest.raises(SystemExit) as exc,
    ):
        cmd.main(args=["."], standalone_mode=True)

    assert exc.value.code == 2


def test_entrypoints_invoke_with_defaults_click_pacify_flush():
    """Verify _invoke_with_defaults returns 0 when Click raises SystemExit(1) on broken pipe."""
    wrapped_stdout = _PacifyFlushWrapper(sys.stdout)
    with (
        patch("typer.main.get_command") as mock_get_cmd,
        patch("sys.stdout", wrapped_stdout),
    ):
        mock_cmd = MagicMock()
        mock_cmd.main.side_effect = SystemExit(1)
        mock_get_cmd.return_value = mock_cmd
        code = _invoke_with_defaults("findfmt", {}, argv=["."])
        assert code == 0


def test_entrypoints_invoke_with_defaults_reraises_other_system_exit():
    """Verify _invoke_with_defaults returns non-zero code on other SystemExit."""
    with patch("typer.main.get_command") as mock_get_cmd:
        mock_cmd = MagicMock()
        mock_cmd.main.side_effect = SystemExit(2)
        mock_get_cmd.return_value = mock_cmd
        code = _invoke_with_defaults("findfmt", {}, argv=["."])
        assert code == 2


def test_entrypoints_invoke_with_defaults_system_exit_1_regular():
    """Verify _invoke_with_defaults returns 1 when SystemExit(1) is not from broken pipe."""
    with patch("typer.main.get_command") as mock_get_cmd:
        mock_cmd = MagicMock()
        mock_cmd.main.side_effect = SystemExit(1)
        mock_get_cmd.return_value = mock_cmd
        code = _invoke_with_defaults("findfmt", {}, argv=["."])
        assert code == 1


def test_is_broken_pipe_wrapper():
    """Verify is_broken_pipe_wrapper detects wrapper classes and ignores normal streams."""
    assert not is_broken_pipe_wrapper(None)
    assert not is_broken_pipe_wrapper(io.StringIO())

    class FakePacifyFlushWrapper:
        pass

    assert is_broken_pipe_wrapper(FakePacifyFlushWrapper())
