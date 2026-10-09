"""CLI integration tests for terminal pager controls and TTY/NO_COLOR handling."""

from __future__ import annotations

import io
import sys
from pathlib import Path

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from rich.pager import Pager
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.cli_runner import execute_findfmt
from findfmt.formatters import OutputFormat
from findfmt.models import FileInfo
from findfmt.terminal import PagerController


class MockInteractiveStream(io.StringIO):
    """Simulated interactive TTY stream."""

    @override
    def isatty(self) -> bool:
        """Report stream as interactive terminal."""
        return True


class MockCapturePager(Pager):
    """Capture pager output for assertions."""

    def __init__(self) -> None:
        """Initialize capture buffer."""
        self.contents: list[str] = []

    @override
    def show(self, content: str) -> None:
        """Record paged content."""
        self.contents.append(content)


def _generate_test_files(count: int) -> list[FileInfo]:
    """Generate n dummy FileInfo objects for testing."""
    return [
        FileInfo(
            path=Path(f"/workspace/file_{i}.py"),
            relative_path=Path(f"file_{i}.py"),
            tags=frozenset({"python", "text"}),
            shebang=None,
            mime_type="text/x-python",
            is_executable=False,
            is_symlink=False,
            size_bytes=100 + i,
        )
        for i in range(count)
    ]


def test_cli_pager_options(sample_repo: Path) -> None:
    """Verify --pager, -P, and --no-pager CLI invocation flags."""
    runner = CliRunner()

    res_long = runner.invoke(app, ["--pager", str(sample_repo)])
    assert res_long.exit_code == 0

    res_short = runner.invoke(app, ["-P", str(sample_repo)])
    assert res_short.exit_code == 0

    res_none = runner.invoke(app, ["--no-pager", str(sample_repo)])
    assert res_none.exit_code == 0


def test_execute_findfmt_with_forced_pager() -> None:
    """Verify execute_findfmt invokes pager when pager=True on interactive stream."""
    stream = MockInteractiveStream()
    pager = MockCapturePager()
    controller = PagerController(pager=True, stream=stream, pager_impl=pager)

    execute_findfmt(
        paths=[Path()],
        tags=None,
        exclude_tags=None,
        all_tags=False,
        shebang=None,
        no_ignore=False,
        hidden=False,
        follow_symlinks=False,
        output_format=OutputFormat.TEXT,
        tree=False,
        table_style=None,
        absolute=False,
        print0=False,
        list_tags=False,
        summary=False,
        find_files_func=lambda _: _generate_test_files(3),
        pager_controller=controller,
    )

    assert len(pager.contents) == 1
    assert "file_0.py" in pager.contents[0]


def test_execute_findfmt_with_no_pager() -> None:
    """Verify execute_findfmt bypasses pager when pager=False."""
    stream = MockInteractiveStream()
    pager = MockCapturePager()
    controller = PagerController(pager=False, stream=stream, pager_impl=pager)

    execute_findfmt(
        paths=[Path()],
        tags=None,
        exclude_tags=None,
        all_tags=False,
        shebang=None,
        no_ignore=False,
        hidden=False,
        follow_symlinks=False,
        output_format=OutputFormat.TEXT,
        tree=False,
        table_style=None,
        absolute=False,
        print0=False,
        list_tags=False,
        summary=False,
        find_files_func=lambda _: _generate_test_files(50),
        pager_controller=controller,
    )

    assert len(pager.contents) == 0
    assert "file_0.py" in stream.getvalue()


def test_execute_findfmt_auto_paging_thresholds() -> None:
    """Verify auto-paging triggers only when file count exceeds terminal height."""
    stream_small = MockInteractiveStream()
    pager_small = MockCapturePager()
    controller_small = PagerController(
        pager=None,
        stream=stream_small,
        term_height=20,
        pager_impl=pager_small,
    )

    execute_findfmt(
        paths=[Path()],
        tags=None,
        exclude_tags=None,
        all_tags=False,
        shebang=None,
        no_ignore=False,
        hidden=False,
        follow_symlinks=False,
        output_format=OutputFormat.TEXT,
        tree=False,
        table_style=None,
        absolute=False,
        print0=False,
        list_tags=False,
        summary=False,
        find_files_func=lambda _: _generate_test_files(5),
        pager_controller=controller_small,
    )

    # 5 lines <= 20 height: direct output, no pager
    assert len(pager_small.contents) == 0
    assert "file_0.py" in stream_small.getvalue()

    stream_large = MockInteractiveStream()
    pager_large = MockCapturePager()
    controller_large = PagerController(
        pager=None,
        stream=stream_large,
        term_height=10,
        pager_impl=pager_large,
    )

    execute_findfmt(
        paths=[Path()],
        tags=None,
        exclude_tags=None,
        all_tags=False,
        shebang=None,
        no_ignore=False,
        hidden=False,
        follow_symlinks=False,
        output_format=OutputFormat.TEXT,
        tree=False,
        table_style=None,
        absolute=False,
        print0=False,
        list_tags=False,
        summary=False,
        find_files_func=lambda _: _generate_test_files(15),
        pager_controller=controller_large,
    )

    # 15 lines > 10 height: paged
    assert len(pager_large.contents) == 1
    assert "file_0.py" in pager_large.contents[0]


def test_execute_findfmt_non_interactive_pipe() -> None:
    """Verify non-interactive output streams bypass pager completely."""
    stream = io.StringIO()
    pager = MockCapturePager()
    controller = PagerController(pager=True, stream=stream, pager_impl=pager)

    execute_findfmt(
        paths=[Path()],
        tags=None,
        exclude_tags=None,
        all_tags=False,
        shebang=None,
        no_ignore=False,
        hidden=False,
        follow_symlinks=False,
        output_format=OutputFormat.TEXT,
        tree=False,
        table_style=None,
        absolute=False,
        print0=False,
        list_tags=False,
        summary=False,
        find_files_func=lambda _: _generate_test_files(30),
        stream=stream,
        pager_controller=controller,
    )

    assert len(pager.contents) == 0
    assert "file_0.py" in stream.getvalue()


def test_cli_no_color_strips_ansi(sample_repo: Path) -> None:
    """Verify NO_COLOR environment disables ANSI escape codes."""
    runner = CliRunner()
    res = runner.invoke(
        app,
        ["--format", "table", str(sample_repo)],
        env={"NO_COLOR": "1"},
    )
    assert res.exit_code == 0
    assert "findfmt Files" in res.stdout
    assert "\x1b[" not in res.stdout


def test_cli_clicolor_force_enables_ansi(sample_repo: Path) -> None:
    """Verify CLICOLOR_FORCE environment forces ANSI escape codes even on non-TTY."""
    runner = CliRunner()
    res = runner.invoke(
        app,
        ["--format", "table", str(sample_repo)],
        env={"CLICOLOR_FORCE": "1"},
    )
    assert res.exit_code == 0
    assert "findfmt Files" in res.stdout
    assert "\x1b[" in res.stdout
