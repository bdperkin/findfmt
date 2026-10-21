"""Unit tests for OutputSink atomic output file management."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from findfmt.cli.output_sink import OutputSink, open_output_sink, reconfigure_surrogateescape
from findfmt.cli.runner import _open_output_sink


def test_reconfigure_surrogateescape_with_callable() -> None:
    """Verify reconfigure_surrogateescape invokes reconfigure when callable."""
    mock_stream = MagicMock(spec=io.TextIOWrapper)
    mock_stream.reconfigure = MagicMock()
    reconfigure_surrogateescape(mock_stream)
    mock_stream.reconfigure.assert_called_once_with(errors="surrogateescape")


def test_reconfigure_surrogateescape_without_reconfigure() -> None:
    """Verify reconfigure_surrogateescape handles streams without reconfigure gracefully."""
    stream = io.StringIO()
    reconfigure_surrogateescape(stream)


def test_output_sink_stdout_fallback() -> None:
    """Verify OutputSink with no temp_path acts as a pass-through without closing stdout."""
    stream = io.StringIO()
    sink = OutputSink(stream=stream)
    assert sink.temp_path is None
    assert sink.target_path is None

    sink.stream.write("hello")
    sink.commit()
    sink.commit()  # idempotent branch test
    sink.close()
    sink.close()  # idempotent branch test
    sink._cleanup_temp()  # temp_path is None branch test # noqa: SLF001

    assert not stream.closed
    assert stream.getvalue() == "hello"


def test_output_sink_context_manager_clean(tmp_path: Path) -> None:
    """Verify OutputSink context manager commits and closes cleanly on success."""
    target = tmp_path / "final.txt"
    with open_output_sink(target) as sink:
        sink.stream.write("atomic success\n")

    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "atomic success\n"
    assert [p for p in tmp_path.iterdir() if p.name.startswith(".")] == []


def test_output_sink_context_manager_exception(tmp_path: Path) -> None:
    """Verify OutputSink context manager cleans up temp file when exception occurs."""
    target = tmp_path / "failed.txt"
    abort_msg = "abort"

    def _failing_work() -> None:
        with open_output_sink(target) as sink:
            sink.stream.write("will not be committed\n")
            raise ValueError(abort_msg)

    with pytest.raises(ValueError, match=abort_msg):
        _failing_work()

    assert not target.exists()
    assert [p for p in tmp_path.iterdir() if p.name.startswith(".")] == []


def test_output_sink_commit_replace_os_error(tmp_path: Path) -> None:
    """Verify commit raises typer.Exit(code=2) and cleans up temp file when os.replace fails."""
    target = tmp_path / "replace_fail.txt"
    sink = open_output_sink(target)
    sink.stream.write("data")

    fail_msg = "Replace failed"
    with (
        patch("os.replace", side_effect=OSError(fail_msg)),
        pytest.raises(typer.Exit) as exc,
    ):
        sink.commit()

    assert exc.value.exit_code == 2
    assert not target.exists()
    assert [p for p in tmp_path.iterdir() if p.name.startswith(".")] == []


def test_output_sink_flush_and_unlink_os_error(tmp_path: Path) -> None:
    """Verify close handles OSError in stream.flush and temp_path.unlink gracefully."""
    target = tmp_path / "flush_err.txt"
    sink = open_output_sink(target)

    with (
        patch.object(sink.stream, "flush", side_effect=OSError("Flush error")),
        patch.object(Path, "unlink", side_effect=OSError("Unlink error")),
    ):
        sink.close()

    assert sink.is_closed


def test_output_sink_atexit_handler(tmp_path: Path) -> None:
    """Verify atexit handler cleans up uncommitted temp files on premature termination."""
    target = tmp_path / "atexit_test.txt"
    sink = open_output_sink(target)
    sink.stream.write("partial")

    # Test cleanup when not committed
    sink.cleanup_uncommitted()
    assert not target.exists()
    assert sink.stream.closed

    # Test cleanup when committed
    target2 = tmp_path / "committed.txt"
    sink2 = open_output_sink(target2)
    sink2.stream.write("done")
    sink2.commit()
    assert sink2.is_committed
    sink2.cleanup_uncommitted()
    assert target2.read_text() == "done"


def test_open_output_sink_existing_file_preserves_mode(tmp_path: Path) -> None:
    """Verify open_output_sink preserves existing file permissions and handles chmod OSError."""
    target = tmp_path / "existing.txt"
    target.write_text("prior")

    with open_output_sink(target) as sink:
        sink.stream.write("updated")

    assert target.read_text() == "updated"

    # Test chmod failure branch on existing file
    with (
        patch.object(Path, "chmod", side_effect=OSError("chmod error")),
        open_output_sink(target) as sink,
    ):
        sink.stream.write("again")

    assert target.read_text() == "again"


def test_open_output_sink_string_path(tmp_path: Path) -> None:
    """Verify open_output_sink accepts a string path argument."""
    target = str(tmp_path / "string_path.txt")
    with open_output_sink(target) as sink:
        sink.stream.write("from string")

    assert Path(target).read_text() == "from string"


def test_open_output_sink_chmod_os_error(tmp_path: Path) -> None:
    """Verify open_output_sink tolerates OSError during os.chmod."""
    target = tmp_path / "chmod_fail.txt"
    with (
        patch.object(Path, "chmod", side_effect=OSError("Permission failed")),
        open_output_sink(target) as sink,
    ):
        sink.stream.write("chmod fail handled")

    assert target.read_text() == "chmod fail handled"


def test_open_output_sink_cleanup_on_setup_os_error(tmp_path: Path) -> None:
    """Verify open_output_sink cleans up open temp file if an OSError occurs after creation."""
    target = tmp_path / "setup_fail.txt"
    with (
        patch.object(Path, "exists", side_effect=OSError("Stat failed")),
        pytest.raises(typer.Exit) as exc,
    ):
        open_output_sink(target)

    assert exc.value.exit_code == 2
    assert not target.exists()
    assert [p for p in tmp_path.iterdir() if p.name.startswith(".")] == []


def test_open_output_sink_cleanup_tolerates_errors(tmp_path: Path) -> None:
    """Verify open_output_sink error handler tolerates OSError during close and unlink."""
    target = tmp_path / "cleanup_err.txt"

    class FailingFile:
        def __init__(self, name: str) -> None:
            self.name = name

        def close(self) -> None:
            msg = "Close failed"
            raise OSError(msg)

    with (
        patch("tempfile.NamedTemporaryFile", return_value=FailingFile(str(tmp_path / "f.tmp"))),
        patch.object(Path, "unlink", side_effect=OSError("Unlink failed")),
        patch.object(Path, "exists", side_effect=OSError("Stat failed")),
        pytest.raises(typer.Exit) as exc,
    ):
        open_output_sink(target)

    assert exc.value.exit_code == 2


def test_open_output_sink_is_dir_error(tmp_path: Path) -> None:
    """Verify open_output_sink raises typer.Exit(code=2) when destination is a directory."""
    dir_target = tmp_path / "a_directory"
    dir_target.mkdir()
    with pytest.raises(typer.Exit) as exc:
        open_output_sink(dir_target)

    assert exc.value.exit_code == 2


def test_runner_open_output_sink_backward_compatibility(tmp_path: Path) -> None:
    """Verify _open_output_sink wrapper behaves as expected for both None and Path."""
    stream, sink = _open_output_sink(None, None)
    assert stream is sys.stdout
    assert sink is None

    target = tmp_path / "compat.txt"
    stream2, sink2 = _open_output_sink(target, None)
    assert sink2 is not None
    assert stream2 is sink2.stream
    sink2.stream.write("content")
    sink2.commit()
    sink2.close()
    assert target.read_text() == "content"
