"""Unix signal handling, broken pipe mitigation, and pipeline resilience."""

from __future__ import annotations

import contextlib
import io
import os
import signal
import sys
import threading
from typing import TYPE_CHECKING, TextIO

import typer

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "handle_broken_pipe",
    "handle_keyboard_interrupt",
    "install_signal_handlers",
    "is_broken_pipe_wrapper",
    "trap_cli_signals",
]


def is_broken_pipe_wrapper(stream: object | None) -> bool:
    """Check if stream is wrapped by Click or Typer broken pipe pacifier.

    Args:
        stream: Stream instance to inspect.

    Returns:
        True if stream is wrapped by a broken pipe pacifier, False otherwise.
    """
    return stream is not None and "PacifyFlushWrapper" in type(stream).__name__


def _sigint_handler(_signum: int, _frame: object) -> None:
    """Signal handler for SIGINT (Ctrl+C) exiting cleanly with Unix code 130."""
    sys.exit(130)


def install_signal_handlers() -> None:
    """Install process-level Unix signal handlers if on the main thread."""
    if threading.current_thread() is threading.main_thread():
        with contextlib.suppress(ValueError, AttributeError):
            signal.signal(signal.SIGINT, _sigint_handler)


def handle_broken_pipe(stream: TextIO | None = None) -> None:
    """Safely handle SIGPIPE / BrokenPipeError for POSIX pipeline resilience.

    Flushes the destination stream if feasible, safely redirects stdout to
    /dev/null if connected to an OS file descriptor to avoid secondary
    BrokenPipeError during Python interpreter exit flushes, and raises
    typer.Exit(code=0) for clean termination.

    Args:
        stream: Target output text stream to flush, if provided.
    """
    target = stream if stream is not None else sys.stdout
    with contextlib.suppress(BrokenPipeError, OSError):
        target.flush()

    try:
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull_fd, sys.stdout.fileno())
        finally:
            os.close(devnull_fd)
    except (OSError, io.UnsupportedOperation, AttributeError):
        pass

    raise typer.Exit(code=0) from None


def handle_keyboard_interrupt() -> None:
    """Safely handle SIGINT / KeyboardInterrupt for interactive scans.

    Terminates execution immediately and exits cleanly with standard Unix
    status 130 (128 + SIGINT) without dumping Python traceback text.
    """
    raise typer.Exit(code=130) from None


@contextlib.contextmanager
def trap_cli_signals(
    stream: TextIO | None = None,
    *,
    standalone_mode: bool = False,
) -> Iterator[None]:
    """Context manager to trap BrokenPipeError and KeyboardInterrupt cleanly.

    Args:
        stream: Target output text stream to flush on broken pipe.
        standalone_mode: Whether running in standalone mode (sys.exit on error).

    Yields:
        None while managing execution within guarded context.
    """
    try:
        yield
    except BrokenPipeError:
        try:
            handle_broken_pipe(stream)
        except typer.Exit as exc:
            if standalone_mode:
                sys.exit(exc.exit_code)

            raise
    except KeyboardInterrupt:
        try:
            handle_keyboard_interrupt()
        except typer.Exit as exc:
            if standalone_mode:
                sys.exit(exc.exit_code)

            raise
