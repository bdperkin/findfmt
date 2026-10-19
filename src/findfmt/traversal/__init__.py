"""Filesystem traversal, filtering, and ignore engine package for findfmt."""

from __future__ import annotations

from findfmt.exceptions import InvalidSortCriteriaError, TraversalError
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
from findfmt.traversal.sorting import (
    natural_sort_key,
    resolve_sort_key,
    sort_directory_entries,
)

__all__ = [
    "InvalidSortCriteriaError",
    "PatternMatcher",
    "TraversalError",
    "create_pattern_matcher",
    "find_files",
    "is_path_ignored",
    "load_custom_gitignore_spec",
    "load_git_exclude_spec",
    "load_gitignore_spec",
    "load_global_gitignore_spec",
    "matches_filter",
    "natural_sort_key",
    "resolve_sort_key",
    "should_skip_dir",
    "sort_directory_entries",
    "traverse_directory",
]
