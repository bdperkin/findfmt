"""System diagnostics and runtime environment inspection."""

from __future__ import annotations

import inspect
import platform
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version

import typer

__all__ = [
    "diagnostics_callback",
    "get_diagnostics",
    "get_git_version",
    "get_version",
    "version_callback",
]


def get_version() -> str:
    """Retrieve package version or fallback string.

    Returns:
        Version string.
    """
    try:
        return version("findfmt")
    except PackageNotFoundError:
        return "0.2.0.dev0"


def get_git_version() -> str | None:
    """Retrieve git executable version string if git is available.

    Returns:
        Git version string or None if git is not detected.
    """
    git_path = shutil.which("git")
    if not git_path:
        return None

    try:
        proc = subprocess.run(  # noqa: S603
            [git_path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    return None


def get_diagnostics() -> str:
    """Compile runtime environment diagnostics.

    Returns:
        Formatted multi-line diagnostics string ending in a newline.
    """
    lines: list[str] = [f"findfmt {get_version()}"]
    py_ver = sys.version.split()[0]
    plat = platform.platform()
    lines.append(f"Python: {py_ver} ({plat})")

    try:
        identify_ver = version("identify")
    except PackageNotFoundError:
        identify_ver = "not installed"

    lines.append(f"identify: {identify_ver}")

    git_ver = get_git_version()
    lines.append(f"Git: {git_ver or 'not found'}")

    return "\n".join(lines) + "\n"


def _is_in_context(ctx: object) -> bool:
    """Check if verbose output or diagnostics was requested in context.

    Args:
        ctx: Click/Typer context, if available.

    Returns:
        True if requested in context, False otherwise.
    """
    params = getattr(ctx, "params", {})
    if params.get("verbose") or params.get("diagnostics"):
        return True

    ctx_obj = getattr(ctx, "obj", None)
    if isinstance(ctx_obj, dict):
        raw_argv = ctx_obj.get("argv", [])
        return "--verbose" in raw_argv or "--diagnostics" in raw_argv

    return False


def _is_in_frames() -> bool:
    """Check if verbose output or diagnostics was requested in caller frames.

    Returns:
        True if requested in caller frames, False otherwise.
    """
    frame = inspect.currentframe()
    while frame:
        opts = frame.f_locals.get("opts")
        if isinstance(opts, dict) and (opts.get("verbose") or opts.get("diagnostics")):
            return True

        frame = frame.f_back

    return False


def _is_verbose_requested(ctx: object = None) -> bool:
    """Check if verbose output or diagnostics was requested.

    Args:
        ctx: Click/Typer context, if available.

    Returns:
        True if verbose or diagnostics is requested, False otherwise.
    """
    if ctx is not None and _is_in_context(ctx):
        return True

    if _is_in_frames():
        return True

    return "--verbose" in sys.argv or "--diagnostics" in sys.argv


def version_callback(
    ctx: typer.Context | bool | None = None,
    value: bool = False,
) -> None:
    """Display the version of findfmt and exit.

    Args:
        ctx: Typer context, if provided by Click callback.
        value: Boolean flag indicating if version flag was passed.

    Raises:
        typer.Exit: Upon printing version.
    """
    if isinstance(ctx, bool):
        value = ctx
        ctx = None

    if value:
        if _is_verbose_requested(ctx):
            sys.stdout.write(get_diagnostics())
        else:
            sys.stdout.write(f"findfmt {get_version()}\n")

        raise typer.Exit(code=0)


def diagnostics_callback(value: bool) -> None:
    """Display runtime environment diagnostics and exit.

    Args:
        value: Boolean flag indicating if diagnostics flag was passed.

    Raises:
        typer.Exit: Upon printing diagnostics.
    """
    if value:
        sys.stdout.write(get_diagnostics())
        raise typer.Exit(code=0)
