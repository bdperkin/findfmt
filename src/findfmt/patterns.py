"""Wildcard and glob pattern matching engine for directory traversal."""

from __future__ import annotations

import contextlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pathspec

if TYPE_CHECKING:
    from collections.abc import Sequence

    from findfmt.models import FileInfo, TraversalConfig

__all__ = [
    "PatternMatcher",
    "compile_pattern_spec",
    "create_pattern_matcher",
    "matches_pattern_criteria",
    "split_pattern_alternations",
]


def split_pattern_alternations(pattern: str) -> list[str]:
    """Split a glob pattern by '|' alternation outside of bracket character classes."""
    parts: list[str] = []
    current: list[str] = []
    in_bracket = False

    for ch in pattern:
        if ch == "[" and not in_bracket:
            in_bracket = True
            current.append(ch)
        elif ch == "]" and in_bracket:
            in_bracket = False
            current.append(ch)
        elif ch == "|" and not in_bracket:
            part = "".join(current).strip()
            if part:
                parts.append(part)

            current = []
        else:
            current.append(ch)

    part = "".join(current).strip()
    if part:
        parts.append(part)

    return parts


def _apply_ignore_case(spec: pathspec.PathSpec[Any]) -> None:
    """Apply case-insensitivity flag to all compiled pattern regular expressions."""
    for pat in spec.patterns:
        reg = getattr(pat, "regex", None)
        if reg is not None and hasattr(reg, "pattern"):
            pat.regex = re.compile(reg.pattern, reg.flags | re.IGNORECASE)


def compile_pattern_spec(
    patterns: Sequence[str] | tuple[str, ...],
    *,
    ignore_case: bool = False,
) -> pathspec.PathSpec[Any] | None:
    """Compile wildcard/glob patterns into a PathSpec matcher with alternations."""
    if not patterns:
        return None

    lines: list[str] = []
    for pat in patterns:
        lines.extend(split_pattern_alternations(pat))

    if not lines:
        return None

    spec = pathspec.PathSpec.from_lines("gitignore", lines)
    if ignore_case:
        _apply_ignore_case(spec)

    return spec


class PatternMatcher:
    """Compiled pattern matcher for include (-P) and exclude (-I) glob rules."""

    def __init__(
        self,
        include_patterns: tuple[str, ...] = (),
        exclude_patterns: tuple[str, ...] = (),
        *,
        ignore_case: bool = False,
        match_dirs: bool = False,
    ) -> None:
        """Initialize PatternMatcher with compiled inclusion/exclusion specifications."""
        self.include_spec = compile_pattern_spec(include_patterns, ignore_case=ignore_case)
        self.exclude_spec = compile_pattern_spec(exclude_patterns, ignore_case=ignore_case)
        self.has_includes: bool = self.include_spec is not None
        self.has_excludes: bool = self.exclude_spec is not None
        self.ignore_case: bool = ignore_case
        self.match_dirs: bool = match_dirs

    @classmethod
    def from_config(cls, config: TraversalConfig) -> PatternMatcher:
        """Construct PatternMatcher from TraversalConfig options."""
        return cls(
            include_patterns=config.include_patterns,
            exclude_patterns=config.exclude_patterns,
            ignore_case=config.ignore_case,
            match_dirs=config.match_dirs,
        )

    def to_posix(self, path: Path | str, base_root: Path | None) -> tuple[str, str]:
        """Convert path to POSIX relative path and basename string pair."""
        p = Path(path)
        if base_root is not None:
            with contextlib.suppress(ValueError):
                p = p.relative_to(base_root)

        return p.as_posix(), p.name

    def should_exclude(
        self,
        path: Path | str,
        *,
        is_dir: bool,
        base_root: Path | None = None,
    ) -> bool:
        """Determine whether a file or directory path matches exclude patterns (-I)."""
        if not self.has_excludes or self.exclude_spec is None:
            return False

        rel_str, name = self.to_posix(path, base_root)
        if is_dir:
            dir_str = rel_str.rstrip("/") + "/"
            name_dir = name.rstrip("/") + "/"
            return bool(
                self.exclude_spec.match_file(dir_str)
                or self.exclude_spec.match_file(name_dir)
                or self.exclude_spec.match_file(rel_str)
                or self.exclude_spec.match_file(name),
            )

        return bool(self.exclude_spec.match_file(rel_str) or self.exclude_spec.match_file(name))

    def matches_file(
        self,
        path: Path | str,
        *,
        base_root: Path | None = None,
        inherited_match: bool = False,
    ) -> bool:
        """Determine whether a file path satisfies active pattern criteria."""
        if self.should_exclude(path, is_dir=False, base_root=base_root):
            return False

        if not self.has_includes or inherited_match or self.include_spec is None:
            return True

        rel_str, name = self.to_posix(path, base_root)
        return bool(self.include_spec.match_file(rel_str) or self.include_spec.match_file(name))

    def matches_dir(
        self,
        path: Path | str,
        *,
        base_root: Path | None = None,
    ) -> bool:
        """Determine whether a directory name/path matches include patterns (-P)."""
        if not self.has_includes or self.include_spec is None:
            return True

        rel_str, name = self.to_posix(path, base_root)
        dir_str = rel_str.rstrip("/") + "/"
        name_dir = name.rstrip("/") + "/"
        return bool(
            self.include_spec.match_file(dir_str)
            or self.include_spec.match_file(name_dir)
            or self.include_spec.match_file(rel_str)
            or self.include_spec.match_file(name),
        )

    def should_inherit_match(
        self,
        dir_path: Path | str,
        *,
        base_root: Path | None = None,
        parent_inherited: bool = False,
    ) -> bool:
        """Determine whether children of a directory inherit pattern inclusion."""
        if not self.match_dirs:
            return False

        if parent_inherited:
            return True

        return self.matches_dir(dir_path, base_root=base_root)


def create_pattern_matcher(config: TraversalConfig) -> PatternMatcher:
    """Create a PatternMatcher instance from TraversalConfig."""
    return PatternMatcher.from_config(config)


def matches_pattern_criteria(
    file_info: FileInfo,
    config: TraversalConfig,
    *,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
) -> bool:
    """Check whether a FileInfo satisfies pattern inclusion and exclusion rules."""
    if not config.include_patterns and not config.exclude_patterns:
        return True

    active_matcher = matcher if matcher is not None else create_pattern_matcher(config)
    target_path = file_info.relative_path or file_info.path

    if file_info.path.is_dir():
        if active_matcher.should_exclude(target_path, is_dir=True):
            return False

        if not active_matcher.has_includes or inherited_match or not config.match_dirs:
            return True

        return active_matcher.matches_dir(target_path)

    return active_matcher.matches_file(
        target_path,
        inherited_match=inherited_match,
    )
