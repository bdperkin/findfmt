"""Filesystem traversal, filtering, and ignore engine package for findfmt."""

from __future__ import annotations

from findfmt.traversal.boundaries import matches_filter, should_skip_dir
from findfmt.traversal.engine import find_files, traverse_directory
from findfmt.traversal.ignore import (
    is_path_ignored,
    load_custom_gitignore_spec,
    load_git_exclude_spec,
    load_gitignore_spec,
    load_global_gitignore_spec,
)
from findfmt.traversal.patterns import PatternMatcher, create_pattern_matcher

__all__ = [
    "PatternMatcher",
    "create_pattern_matcher",
    "find_files",
    "is_path_ignored",
    "load_custom_gitignore_spec",
    "load_git_exclude_spec",
    "load_gitignore_spec",
    "load_global_gitignore_spec",
    "matches_filter",
    "should_skip_dir",
    "traverse_directory",
]
