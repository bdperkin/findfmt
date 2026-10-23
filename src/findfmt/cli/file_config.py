"""Configuration file discovery, loading, and resolution engine for findfmt."""

from __future__ import annotations

import os
import platform
import tomllib
from pathlib import Path
from typing import Any

import typer

from findfmt.cli.config_schema import (
    _extract_tool_section,
    validate_and_convert_config,
)
from findfmt.i18n import _

__all__ = [
    "extract_config_args",
    "find_config_file",
    "format_config_dump",
    "get_active_config_data",
    "get_active_config_path",
    "load_toml_config",
    "reset_active_config",
    "resolve_and_load_config",
    "validate_and_convert_config",
]


class _ActiveConfigState:
    """Internal container for the active configuration file path and settings."""

    def __init__(self) -> None:
        self.path: Path | None = None
        self.data: dict[str, object] = {}


_state = _ActiveConfigState()


def get_active_config_path() -> Path | None:
    """Retrieve the filesystem path of the currently active configuration file.

    Returns:
        Resolved Path instance or None if defaults are active.
    """
    return _state.path


def get_active_config_data() -> dict[str, object]:
    """Retrieve the parsed raw dictionary of the currently active configuration.

    Returns:
        Dictionary of active configuration settings.
    """
    return dict(_state.data)


def reset_active_config() -> None:
    """Reset active configuration state back to uninitialized defaults."""
    _state.path = None
    _state.data = {}


def extract_config_args(
    args: list[str],
) -> tuple[str | None, bool, bool]:
    """Pre-scan command-line arguments for configuration-related flags.

    Respects POSIX '--' terminator: arguments after '--' are not interpreted
    as configuration flags.

    Args:
        args: Raw command line argument list.

    Returns:
        Tuple of (config_path, no_config, show_config).
    """
    config_path: str | None = None
    no_config: bool = False
    show_config: bool = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            break

        if arg == "--no-config":
            no_config = True
        elif arg == "--show-config":
            show_config = True
        elif arg == "--config":
            if i + 1 < len(args):
                config_path = args[i + 1]
                i += 1
        elif arg.startswith("--config="):
            config_path = arg.split("=", 1)[1]

        i += 1

    return config_path, no_config, show_config


def _get_standard_user_config_path() -> Path:
    """Determine the platform-standard path for the user configuration file."""
    if platform.system() == "Windows":
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / "findfmt" / "config.toml"

        return Path.home() / "AppData" / "Roaming" / "findfmt" / "config.toml"

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "findfmt" / "config.toml"

    return Path.home() / ".config" / "findfmt" / "config.toml"


def find_config_file(
    explicit_path: Path | str | None = None,
    *,
    no_config: bool = False,
    cwd: Path | None = None,
) -> tuple[Path | None, bool]:
    """Resolve the configuration file path following findfmt precedence rules.

    Precedence order:

    1. ``--no-config`` suppresses all configuration files.
    2. Explicit path passed via ``--config``.
    3. ``FINDFMT_CONFIG`` environment variable (empty string suppresses loading).
    4. User config file (``$XDG_CONFIG_HOME`` or ``%APPDATA%``).
    5. Project ``pyproject.toml`` containing a ``[tool.findfmt]`` table.
    6. Built-in defaults.

    Args:
        explicit_path: Explicit config path supplied via CLI argument.
        no_config: Flag suppressing all configuration file loading.
        cwd: Optional current working directory override for project discovery.

    Returns:
        Tuple of (resolved_file_path, is_explicit).
        is_explicit is True when path originates from --config or FINDFMT_CONFIG.
    """
    if no_config:
        return None, False

    if explicit_path is not None:
        path_str = str(explicit_path).strip()
        return (Path(path_str), True) if path_str else (None, False)

    env_config = os.environ.get("FINDFMT_CONFIG")
    if env_config is not None:
        trimmed = env_config.strip()
        return (Path(trimmed), True) if trimmed else (None, False)

    user_config = _get_standard_user_config_path()
    if user_config.is_file():
        return user_config, False

    pyproject = (cwd if cwd is not None else Path.cwd()) / "pyproject.toml"
    return (pyproject, False) if pyproject.is_file() else (None, False)


def load_toml_config(path: Path, *, is_explicit: bool) -> dict[str, Any]:
    """Parse a TOML configuration file into a raw settings dictionary.

    Args:
        path: Path to target TOML configuration file.
        is_explicit: Whether this path was explicitly specified by the user.

    Returns:
        Dictionary of extracted configuration settings.

    Raises:
        typer.Exit: If an explicit file is missing or any file contains invalid syntax.
    """
    if not path.is_file():
        if is_explicit:
            typer.echo(
                _("Error: Configuration file '{path}' not found.").format(path=path),
                err=True,
            )
            raise typer.Exit(code=2)

        return {}

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        typer.echo(
            _("Error: Invalid TOML in configuration file '{path}': {error}").format(
                path=path,
                error=exc,
            ),
            err=True,
        )
        raise typer.Exit(code=2) from exc
    except OSError as exc:
        typer.echo(
            _("Error reading configuration file '{path}': {error}").format(
                path=path,
                error=exc,
            ),
            err=True,
        )
        raise typer.Exit(code=2) from exc

    return _extract_tool_section(data, path)


def resolve_and_load_config(
    explicit_path: Path | str | None = None,
    *,
    no_config: bool = False,
    cwd: Path | None = None,
) -> tuple[Path | None, dict[str, Any]]:
    """Discover, load, validate, and activate configuration settings.

    Args:
        explicit_path: Explicit config path supplied via CLI argument.
        no_config: Flag suppressing all configuration file loading.
        cwd: Optional current working directory override.

    Returns:
        Tuple of (active_config_path, defaults_dict).
    """
    path, is_explicit = find_config_file(
        explicit_path=explicit_path,
        no_config=no_config,
        cwd=cwd,
    )

    if path is None:
        reset_active_config()
        return None, {}

    raw_data = load_toml_config(path, is_explicit=is_explicit)
    if not raw_data:
        if path.name == "pyproject.toml":
            reset_active_config()
            return None, {}

        _state.path = path
        _state.data = {}
        return path, {}

    converted = validate_and_convert_config(raw_data, path)
    _state.path = path
    _state.data = dict(raw_data)
    return path, converted


def _format_toml_value(val: object) -> str:
    """Format a Python value as a TOML scalar or list string."""
    if isinstance(val, bool):
        return "true" if val else "false"

    if isinstance(val, (int, float)):
        return str(val)

    if isinstance(val, list):
        items = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in val)
        return f"[{items}]"

    return f'"{val}"'


def format_config_dump(path: Path | None, config_dict: dict[str, Any]) -> str:
    """Format active configuration settings for diagnostic display.

    Args:
        path: Path of the active configuration file or None.
        config_dict: Dictionary of active configuration key-value pairs.

    Returns:
        Formatted multi-line diagnostic string ending in a newline.
    """
    if path is None or not config_dict:
        active_label = str(path) if path is not None else _("(none)")
        return _("Active configuration: {path} (using built-in defaults)\n").format(
            path=active_label,
        )

    lines = [_("Active configuration: {path}").format(path=path), "", "[tool.findfmt]"]
    for key in sorted(config_dict):
        val_str = _format_toml_value(config_dict[key])
        lines.append(f"{key} = {val_str}")

    return "\n".join(lines) + "\n"
