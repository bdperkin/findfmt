"""Command-line interface package for findfmt."""

from __future__ import annotations

from findfmt.cli.config import (
    build_traversal_config,
    find_config_file,
    format_config_dump,
    get_active_config_data,
    get_active_config_path,
    load_toml_config,
    resolve_and_load_config,
    validate_and_convert_config,
    validate_cli_options,
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
from findfmt.diagnostics import (
    diagnostics_callback,
    get_diagnostics,
    get_git_version,
    get_version,
    version_callback,
)
from findfmt.entrypoints import (
    main,
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
)
from findfmt.terminal import PagerController

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
