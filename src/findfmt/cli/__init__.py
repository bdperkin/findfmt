"""Command-line interface package for findfmt."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from findfmt.cli.config import (
        build_traversal_config,
        find_config_file,
        format_config_dump,
        get_active_config_data,
        get_active_config_path,
        load_env_config,
        load_toml_config,
        resolve_and_load_config,
        validate_and_convert_config,
        validate_cli_options,
    )
    from findfmt.cli.diagnostics import (
        diagnostics_callback,
        get_diagnostics,
        get_git_version,
        get_version,
        version_callback,
    )
    from findfmt.cli.entrypoints import (
        main,
        main_findfilefmt,
        main_findfilemime,
        main_findfiles,
        main_findfmt0,
        main_findshebang,
        main_findsummary,
    )
    from findfmt.cli.help import (
        get_help_all,
        help_all_callback,
        known_tags_callback,
    )
    from findfmt.cli.main import app, findfmt, show_config_callback
    from findfmt.cli.output_sink import OutputSink, open_output_sink
    from findfmt.cli.pager import FindfmtCommand, display_with_pager
    from findfmt.cli.runner import execute_findfmt
    from findfmt.cli.signals import (
        handle_broken_pipe,
        handle_keyboard_interrupt,
        install_signal_handlers,
        is_broken_pipe_wrapper,
        trap_cli_signals,
    )
    from findfmt.cli.terminal import PagerController

_LAZY_ATTRS: dict[str, str] = {
    "FindfmtCommand": "findfmt.cli.pager",
    "OutputSink": "findfmt.cli.output_sink",
    "PagerController": "findfmt.cli.terminal",
    "app": "findfmt.cli.main",
    "build_traversal_config": "findfmt.cli.config",
    "diagnostics_callback": "findfmt.cli.diagnostics",
    "display_with_pager": "findfmt.cli.pager",
    "execute_findfmt": "findfmt.cli.runner",
    "find_config_file": "findfmt.cli.config",
    "findfmt": "findfmt.cli.main",
    "format_config_dump": "findfmt.cli.config",
    "get_active_config_data": "findfmt.cli.config",
    "get_active_config_path": "findfmt.cli.config",
    "get_diagnostics": "findfmt.cli.diagnostics",
    "get_git_version": "findfmt.cli.diagnostics",
    "get_help_all": "findfmt.cli.help",
    "get_version": "findfmt.cli.diagnostics",
    "handle_broken_pipe": "findfmt.cli.signals",
    "handle_keyboard_interrupt": "findfmt.cli.signals",
    "help_all_callback": "findfmt.cli.help",
    "install_signal_handlers": "findfmt.cli.signals",
    "is_broken_pipe_wrapper": "findfmt.cli.signals",
    "known_tags_callback": "findfmt.cli.help",
    "load_env_config": "findfmt.cli.config",
    "load_toml_config": "findfmt.cli.config",
    "main": "findfmt.cli.entrypoints",
    "main_findfilefmt": "findfmt.cli.entrypoints",
    "main_findfilemime": "findfmt.cli.entrypoints",
    "main_findfiles": "findfmt.cli.entrypoints",
    "main_findfmt0": "findfmt.cli.entrypoints",
    "main_findshebang": "findfmt.cli.entrypoints",
    "main_findsummary": "findfmt.cli.entrypoints",
    "open_output_sink": "findfmt.cli.output_sink",
    "resolve_and_load_config": "findfmt.cli.config",
    "show_config_callback": "findfmt.cli.main",
    "trap_cli_signals": "findfmt.cli.signals",
    "validate_and_convert_config": "findfmt.cli.config",
    "validate_cli_options": "findfmt.cli.config",
    "version_callback": "findfmt.cli.diagnostics",
}

__all__ = [
    "FindfmtCommand",
    "OutputSink",
    "PagerController",
    "app",
    "build_traversal_config",
    "diagnostics_callback",
    "display_with_pager",
    "execute_findfmt",
    "find_config_file",
    "findfmt",
    "format_config_dump",
    "get_active_config_data",
    "get_active_config_path",
    "get_diagnostics",
    "get_git_version",
    "get_help_all",
    "get_version",
    "handle_broken_pipe",
    "handle_keyboard_interrupt",
    "help_all_callback",
    "install_signal_handlers",
    "is_broken_pipe_wrapper",
    "known_tags_callback",
    "load_env_config",
    "load_toml_config",
    "main",
    "main_findfilefmt",
    "main_findfilemime",
    "main_findfiles",
    "main_findfmt0",
    "main_findshebang",
    "main_findsummary",
    "open_output_sink",
    "resolve_and_load_config",
    "show_config_callback",
    "trap_cli_signals",
    "validate_and_convert_config",
    "validate_cli_options",
    "version_callback",
]


def __getattr__(name: str) -> object:
    """Lazily import public CLI attributes on demand (#453)."""
    mod_name = _LAZY_ATTRS.get(name)
    if mod_name is not None:
        mod = importlib.import_module(mod_name)
        globals().pop("main", None)
        return getattr(mod, name)

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
