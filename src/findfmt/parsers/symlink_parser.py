"""Symbolic link syntax parsing and tokenization for external listings."""

from __future__ import annotations

__all__ = ["parse_symlink_target"]

_SYMLINK_ARROW = " -> "
_QUOTE_CHARS = ('"', "'")


def _find_closing_quote(text: str, start: int) -> int:
    """Return the index of the matching unescaped closing quote, or -1 if unmatched."""
    quote_char = text[start]
    idx = start + 1
    length = len(text)
    while idx < length:
        ch = text[idx]
        if ch == "\\" and idx + 1 < length and text[idx + 1] == quote_char:
            idx += 2
            continue

        if ch == quote_char:
            return idx

        idx += 1

    return -1


def _is_quoted_segment(clean: str, start: int, close_idx: int) -> bool:
    """Return True if clean[start:close_idx + 1] sits on symlink token boundaries."""
    if close_idx == -1:
        return False

    left_ok = start == 0 or clean[:start].rstrip().endswith(" ->")
    right_ok = close_idx == len(clean) - 1 or clean[close_idx + 1 :].lstrip().startswith("-> ")
    return left_ok and right_ok


def _strip_quotes(text: str) -> str:
    """Strip a single matching enclosing quote pair while preserving interior quotes and spaces."""
    clean = text.strip()
    if (
        len(clean) > 1
        and clean[0] in _QUOTE_CHARS
        and clean[-1] == clean[0]
        and _find_closing_quote(clean, 0) == len(clean) - 1
    ):
        quote_char = clean[0]
        return clean[1:-1].replace(f"\\{quote_char}", quote_char)

    return clean


def _find_last_unquoted_arrow(clean_token: str) -> int:
    """Return the start index of the last unquoted ' -> ' delimiter, or -1 if none exists."""
    last_arrow = -1
    idx = 0
    length = len(clean_token)
    while idx < length:
        ch = clean_token[idx]
        if ch in _QUOTE_CHARS:
            close_idx = _find_closing_quote(clean_token, idx)
            if _is_quoted_segment(clean_token, idx, close_idx):
                idx = close_idx + 1
                continue
        elif clean_token.startswith(_SYMLINK_ARROW, idx):
            last_arrow = idx

        idx += 1

    return last_arrow


def parse_symlink_target(token: str) -> tuple[str, bool, str | None]:
    """Parse a symlink token and its target destination if present.

    Detects standard Unix symlink notation ('link_name -> target_path') using
    quote-aware scanning that ignores arrows inside quoted segments and splits
    on the last unquoted ' -> ' delimiter while preserving interior quotes.

    Args:
        token: Raw entry string or line segment to inspect.

    Returns:
        Tuple of (clean_path, is_symlink, symlink_target).
    """
    clean_token = token.strip()
    arrow_idx = _find_last_unquoted_arrow(clean_token)
    if arrow_idx != -1:
        link_part = clean_token[:arrow_idx]
        target_part = clean_token[arrow_idx + len(_SYMLINK_ARROW) :]
        link_clean = _strip_quotes(link_part)
        target_clean = _strip_quotes(target_part)
        if link_clean and target_clean:
            return link_clean, True, target_clean

    return _strip_quotes(clean_token), False, None
