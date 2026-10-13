"""Symbolic link syntax parsing and tokenization for external listings."""

from __future__ import annotations

__all__ = ["parse_symlink_target"]


def _strip_quotes(text: str) -> str:
    """Strip matching enclosing single or double quotes from string."""
    clean = text.strip()
    if clean.startswith(('"', "'")) and clean.endswith(clean[0]) and len(clean) > 1:
        return clean[1:-1].strip()

    return clean


def parse_symlink_target(token: str) -> tuple[str, bool, str | None]:
    """Parse a symlink token and its target destination if present.

    Detects standard Unix symlink notation ('link_name -> target_path') while
    handling surrounding quotes and extraneous whitespace.

    Args:
        token: Raw entry string or line segment to inspect.

    Returns:
        Tuple of (clean_path, is_symlink, symlink_target).
    """
    if " -> " in token:
        link_part, _, target_part = token.partition(" -> ")
        link_clean = _strip_quotes(link_part)
        target_clean = _strip_quotes(target_part)
        if link_clean and target_clean:
            return link_clean, True, target_clean

    return _strip_quotes(token), False, None
