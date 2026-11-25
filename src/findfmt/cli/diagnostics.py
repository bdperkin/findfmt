"""System diagnostics and runtime environment inspection."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

import typer

from findfmt import _FALLBACK_VERSION
from findfmt.core import get_active_backend
from findfmt.exceptions import _sanitize_diagnostic_text as sanitize_diagnostic_text
from findfmt.i18n import _

if TYPE_CHECKING:
    from typer.core import _click

__all__ = [
    "diagnostics_callback",
    "generate_config_callback",
    "get_diagnostics",
    "get_git_version",
    "get_version",
    "show_config_callback",
    "version_callback",
]


def _extract_os_error_reason(err: OSError) -> str:
    """Resolve a human-readable, localized reason string from an OSError."""
    if err.strerror is not None and err.strerror != "":
        return str(err.strerror)

    if err.errno is not None:
        try:
            return os.strerror(err.errno)
        except (OverflowError, ValueError):
            return _("I/O error")

    if err.args and err.args[0]:
        return str(err.args[0])

    return _("I/O error")


def format_traversal_error(err: OSError) -> str:
    """Format a localized, sanitized traversal I/O diagnostic line."""
    filename = err.filename
    raw_path = str(filename) if filename is not None and str(filename) != "" else _("<unknown>")
    safe_path = sanitize_diagnostic_text(raw_path)
    safe_reason = sanitize_diagnostic_text(_extract_os_error_reason(err))
    return _("findfmt: cannot open '{path}': {reason}").format(
        path=safe_path,
        reason=safe_reason,
    )


def emit_traversal_error(err: OSError) -> None:
    """Write a localized, sanitized traversal I/O diagnostic to stderr."""
    typer.echo(format_traversal_error(err), err=True)


def emit_cli_error(message: object) -> None:
    """Write a localized, sanitized CLI error diagnostic to stderr."""
    safe_msg = sanitize_diagnostic_text(str(message))
    typer.echo(_("Error: {message}").format(message=safe_msg), err=True)


def get_version() -> str:
    """Retrieve package version or fallback string.

    Returns:
        Version string.
    """
    try:
        return version("findfmt")
    except PackageNotFoundError:
        return _FALLBACK_VERSION


def get_git_version() -> str | None:
    """Retrieve git executable version string if git is available.

    Returns:
        Git version string or None if git is not detected.
    """
    git_path = shutil.which("git")
    if git_path is None:
        return None

    try:
        proc = subprocess.run(  # noqa: S603 - vetted executable args list
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


def get_diagnostics(ctx: typer.Context | None = None) -> str:
    """Compile runtime environment diagnostics.

    Args:
        ctx: Optional Click/Typer context.

    Returns:
        Formatted multi-line diagnostics string ending in a newline.
    """
    lines: list[str] = [f"findfmt {get_version()}"]
    py_ver = sys.version.split()[0]
    plat = platform.platform()
    lines.append(f"Python: {py_ver} ({plat})")
    lines.append(f"Backend: {get_active_backend()}")

    try:
        identify_ver = version("identify")
    except PackageNotFoundError:
        identify_ver = _("not installed")

    lines.append(f"identify: {identify_ver}")

    git_ver = get_git_version()
    lines.append(f"Git: {git_ver or _('not found')}")

    config_path = None
    if ctx is not None:
        config_path = ctx.meta.get("findfmt_config_path")

    if config_path is None:
        from findfmt.cli.file_config import get_active_config_path

        config_path = get_active_config_path()

    cfg_str = sanitize_diagnostic_text(str(config_path)) if config_path is not None else _("none")
    lines.append(f"Configuration: {cfg_str}")

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


def _is_verbose_requested(ctx: object = None) -> bool:
    """Check if verbose output or diagnostics was requested.

    Args:
        ctx: Click/Typer context, if available.

    Returns:
        True if verbose or diagnostics is requested, False otherwise.
    """
    if ctx is not None and _is_in_context(ctx):
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
        from findfmt.cli.pager import display_with_pager

        if _is_verbose_requested(ctx):
            display_with_pager(get_diagnostics(ctx=ctx), ctx=ctx)
        else:
            sys.stdout.write(f"findfmt {get_version()}\n")

        raise typer.Exit(code=0)


def diagnostics_callback(
    ctx: typer.Context | bool | None = None,
    value: bool = False,
) -> None:
    """Display runtime environment diagnostics and exit.

    Args:
        ctx: Typer context, if provided by Click callback.
        value: Boolean flag indicating if diagnostics flag was passed.

    Raises:
        typer.Exit: Upon printing diagnostics.
    """
    if isinstance(ctx, bool):
        value = ctx
        ctx = None

    if value:
        from findfmt.cli.pager import display_with_pager

        display_with_pager(get_diagnostics(ctx=ctx), ctx=ctx)
        raise typer.Exit(code=0)


def show_config_callback(
    ctx: typer.Context | _click.Context | bool | None = None,
    value: bool = False,
) -> None:
    """Display active configuration settings and exit.

    Args:
        ctx: Typer context, if provided by Click callback.
        value: Boolean flag indicating if show-config flag was passed.

    Raises:
        typer.Exit: Upon printing configuration settings.
    """
    if isinstance(ctx, bool):
        value = ctx
        ctx = None

    if value:
        from findfmt.cli.env_config import collect_context_config_overrides
        from findfmt.cli.file_config import (
            format_config_dump,
            get_active_config_data,
            get_active_config_path,
            get_active_config_sources,
        )
        from findfmt.cli.pager import display_with_pager

        path = get_active_config_path()
        data = get_active_config_data()
        sources = get_active_config_sources()
        if ctx is not None:
            path = ctx.meta.get("findfmt_config_path", path)
            data = ctx.meta.get("findfmt_config_data", data)
            sources = ctx.meta.get("findfmt_config_sources", sources)
            data, sources = collect_context_config_overrides(ctx, data, sources)

        content = format_config_dump(path, data, sources=sources)
        display_with_pager(content, ctx=ctx)
        raise typer.Exit(code=0)


def generate_config_callback(
    ctx: typer.Context | bool | None = None,
    value: bool = False,
) -> None:
    """Output the annotated reference TOML configuration and exit.

    Args:
        ctx: Typer context, if provided by Click callback.
        value: Boolean flag indicating if generate-config flag was passed.

    Raises:
        typer.Exit: Upon printing the reference configuration.
    """
    if isinstance(ctx, bool):
        value = ctx
        ctx = None

    if value:
        from findfmt.cli.config_template import generate_reference_config
        from findfmt.cli.pager import display_with_pager

        display_with_pager(generate_reference_config(), ctx=ctx)
        raise typer.Exit(code=0)
