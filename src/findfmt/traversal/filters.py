"""File filter evaluation utilities based on tags, shebang, and pattern criteria."""

from __future__ import annotations

from typing import TYPE_CHECKING

from findfmt.traversal.patterns import matches_pattern_criteria

if TYPE_CHECKING:
    from findfmt.models import FileInfo, TraversalConfig
    from findfmt.traversal.patterns import PatternMatcher

__all__ = ["matches_filter"]


def _matches_shebang(shebang: str | None, filter_str: str | None) -> bool:
    """Check if file shebang satisfies the shebang filter criteria."""
    return not filter_str or bool(shebang and filter_str in shebang)


def _matches_tags(tags: frozenset[str], config: TraversalConfig) -> bool:
    """Check if file tags satisfy inclusion and exclusion criteria."""
    if config.exclude_tags and (tags & config.exclude_tags):
        return False

    if not config.include_tags:
        return True

    return (
        config.include_tags.issubset(tags) if config.all_tags else bool(tags & config.include_tags)
    )


def matches_filter(
    file_info: FileInfo,
    config: TraversalConfig,
    *,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
) -> bool:
    """Determine whether a classified file satisfies filter criteria."""
    if not file_info.path.is_dir() and (
        not _matches_tags(file_info.tags, config)
        or not _matches_shebang(file_info.shebang, config.shebang_filter)
    ):
        return False

    return matches_pattern_criteria(
        file_info,
        config,
        matcher=matcher,
        inherited_match=inherited_match,
    )
