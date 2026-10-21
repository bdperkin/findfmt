"""Output sink management and atomic file delivery for findfmt."""

from __future__ import annotations

import atexit
import contextlib
import errno
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, TextIO, cast

if sys.version_info >= (3, 11):
    from typing import Self
else:  # pragma: no cover
    from typing_extensions import Self

import typer

from findfmt.i18n import _

if TYPE_CHECKING:
    from types import TracebackType

__all__ = ["OutputSink", "open_output_sink", "reconfigure_surrogateescape"]


def reconfigure_surrogateescape(stream: TextIO) -> None:
    """Ensure text stream uses surrogateescape to avoid UnicodeEncodeError on raw POSIX paths."""
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="surrogateescape")


class OutputSink:
    """Manages target output stream and provides atomic file commit upon clean completion."""

    def __init__(
        self,
        stream: TextIO,
        *,
        temp_path: Path | None = None,
        target_path: Path | None = None,
    ) -> None:
        """Initialize OutputSink with stream, optional temp staging path and target path."""
        self.stream = stream
        self.temp_path = temp_path
        self.target_path = target_path
        self._committed = False
        self._closed = False
        if self.temp_path is not None:
            atexit.register(self.cleanup_uncommitted)

    @property
    def is_committed(self) -> bool:
        """Return whether output was cleanly committed."""
        return self._committed

    @property
    def is_closed(self) -> bool:
        """Return whether sink stream and files have been closed."""
        return self._closed

    def _close_stream(self) -> None:
        """Flush and close active delivery stream if associated with temp staging."""
        if not self.stream.closed:
            with contextlib.suppress(OSError):
                self.stream.flush()

            if self.temp_path is not None:
                self.stream.close()

    def _cleanup_temp(self) -> None:
        """Unlink staging temporary file from destination directory."""
        if self.temp_path is not None:
            with contextlib.suppress(OSError):
                self.temp_path.unlink(missing_ok=True)

    def cleanup_uncommitted(self) -> None:
        """Clean up uncommitted temporary staging file on premature termination."""
        self._close_stream()
        if not self._committed:
            self._cleanup_temp()

    def _unregister_atexit(self) -> None:
        """Unregister atexit cleanup hook if temp file was registered."""
        if self.temp_path is not None:
            atexit.unregister(self.cleanup_uncommitted)

    def commit(self) -> None:
        """Atomically commit temporary output file to the final destination path."""
        if self._committed:
            return

        self._committed = True
        if self.temp_path is not None and self.target_path is not None:
            self._unregister_atexit()
            self._close_stream()
            try:
                self.temp_path.replace(self.target_path)
            except OSError as e:
                self._cleanup_temp()
                typer.echo(
                    _("Error opening output file '{path}': {error}").format(
                        path=self.target_path,
                        error=e,
                    ),
                    err=True,
                )
                raise typer.Exit(code=2) from e

    def close(self) -> None:
        """Close sink and remove uncommitted temporary staging file if needed."""
        if self._closed:
            return

        self._closed = True
        self._unregister_atexit()
        self._close_stream()
        if not self._committed:
            self._cleanup_temp()

    def __enter__(self) -> Self:
        """Enter context manager context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, committing on clean completion and closing."""
        if exc_type is None:
            self.commit()

        self.close()


def _create_staging_file(target_path: Path) -> tuple[TextIO, Path]:
    """Create a temporary staging file in the target directory with matching permissions."""
    if target_path.is_dir():
        raise IsADirectoryError(
            errno.EISDIR,
            os.strerror(errno.EISDIR),
            str(target_path),
        )

    target_dir = target_path.parent
    # Temporary staging file in the destination directory guarantees atomic replace
    raw_temp = tempfile.NamedTemporaryFile(  # noqa: SIM115
        mode="w",
        encoding="utf-8",
        errors="surrogateescape",
        dir=target_dir,
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_file = cast("TextIO", raw_temp)
    temp_path = Path(temp_file.name)

    try:
        if target_path.exists():
            with contextlib.suppress(OSError):
                temp_path.chmod(target_path.stat().st_mode)
        else:
            with contextlib.suppress(OSError, AttributeError):
                current_umask = os.umask(0)
                os.umask(current_umask)
                temp_path.chmod(0o666 & ~current_umask)
    except OSError:
        with contextlib.suppress(OSError):
            temp_file.close()

        with contextlib.suppress(OSError):
            temp_path.unlink(missing_ok=True)

        raise

    return temp_file, temp_path


def open_output_sink(
    output: Path | str | None,
    fallback: TextIO | None = None,
) -> OutputSink:
    """Open destination output file atomically or return fallback text stream.

    Args:
        output: Target destination file path, or None for standard output.
        fallback: Optional fallback stream when output is None.

    Returns:
        Configured OutputSink instance managing delivery stream.

    Raises:
        typer.Exit: With exit code 2 if the output file or directory cannot be opened.
    """
    if output is None:
        target = fallback if fallback is not None else cast("TextIO", sys.stdout)
        reconfigure_surrogateescape(target)
        return OutputSink(stream=target)

    target_path = Path(output) if isinstance(output, str) else output

    try:
        temp_file, temp_path = _create_staging_file(target_path)
    except OSError as e:
        typer.echo(
            _("Error opening output file '{path}': {error}").format(
                path=target_path,
                error=e,
            ),
            err=True,
        )
        raise typer.Exit(code=2) from e

    return OutputSink(
        stream=temp_file,
        temp_path=temp_path,
        target_path=target_path,
    )
