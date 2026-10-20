"""Tag evaluation and early skipping utilities for directory traversal."""

from __future__ import annotations

import mimetypes
from typing import TYPE_CHECKING

import identify.identify as identify_engine

if TYPE_CHECKING:
    from findfmt.models import TraversalConfig

__all__ = ["GENERIC_TAGS", "INTERPRETER_TAGS", "can_skip_file_by_tags"]

INTERPRETER_TAGS: frozenset[str] = frozenset(
    {
        "ash",
        "awk",
        "bash",
        "bats",
        "cbsd",
        "csh",
        "dash",
        "erlang",
        "expect",
        "javascript",
        "ksh",
        "nushell",
        "perl",
        "php",
        "php7",
        "php8",
        "python",
        "python2",
        "python3",
        "ruby",
        "sh",
        "shell",
        "tcsh",
        "zsh",
    },
)

GENERIC_TAGS: frozenset[str] = frozenset(
    {
        "binary",
        "directory",
        "executable",
        "file",
        "non-executable",
        "symlink",
        "text",
    },
)


def _collect_possible_tags(
    filename: str,
    name_tags: frozenset[str] | set[str],
    *,
    allow_interpreters: bool,
) -> set[str]:
    """Collect possible tags from filename, MIME type, and interpreters."""
    mime_type, _ = mimetypes.guess_type(filename)
    mime_tags: set[str] = set()
    if mime_type:
        mime_tags.add(f"mime:{mime_type}")
        mime_tags.add(mime_type.split("/", 1)[0])

    possible = set(name_tags) | mime_tags
    if allow_interpreters:
        possible.update(INTERPRETER_TAGS)

    return possible


def can_skip_file_by_tags(
    filename: str,
    config: TraversalConfig,
    *,
    is_executable: bool | None = None,
) -> bool:
    """Determine if a file can be rejected early based on tag criteria."""
    if not config.include_tags and not config.exclude_tags:
        return False

    name_tags = identify_engine.tags_from_filename(filename)

    if config.exclude_tags and bool(name_tags & config.exclude_tags):
        return True

    if not config.include_tags or (config.include_tags & GENERIC_TAGS):
        return False

    allow_interp = is_executable is not False and bool(config.include_tags & INTERPRETER_TAGS)
    possible_tags = _collect_possible_tags(filename, name_tags, allow_interpreters=allow_interp)

    if config.all_tags:
        return not config.include_tags.issubset(possible_tags)

    return not bool(config.include_tags & possible_tags)
