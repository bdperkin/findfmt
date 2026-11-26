"""XML 1.0 character validation and text sanitization helpers for XmlFormatter."""

from __future__ import annotations

from findfmt.utils.strings import strip_ansi_escapes

__all__ = [
    "clean_xml_text",
    "is_valid_xml_char",
    "sanitize_xml_text",
]

_MIN_PRINTABLE_ASCII = 0x20
_DEL_ASCII = 0x7F
_VALID_UNICODE_MIN = 0xA0
_XML_CHAR_TAB = 0x9
_XML_CHAR_LF = 0xA
_XML_CHAR_CR = 0xD
_XML_PRE_SURROGATE_MAX = 0xD7FF
_XML_POST_SURROGATE_MIN = 0xE000
_XML_BMP_MAX = 0xFFFD
_XML_SUPP_MIN = 0x10000
_XML_UNICODE_MAX = 0x10FFFF
_SURROGATE_MIN = 0xD800
_SURROGATE_MAX = 0xDFFF
_NONCHAR_FFFE = "\ufffe"
_NONCHAR_FFFF = "\uffff"


def is_valid_xml_char(c: str) -> bool:
    """Check if character is legal in XML 1.0 (excluding surrogates and U+FFFE/FFFF)."""
    cp = ord(c)
    return (
        cp in (_XML_CHAR_TAB, _XML_CHAR_LF, _XML_CHAR_CR)
        or (_MIN_PRINTABLE_ASCII <= cp < _DEL_ASCII)
        or (_VALID_UNICODE_MIN <= cp <= _XML_PRE_SURROGATE_MAX)
        or (_XML_POST_SURROGATE_MIN <= cp <= _XML_BMP_MAX)
        or (_XML_SUPP_MIN <= cp <= _XML_UNICODE_MAX)
    )


def sanitize_xml_text(text: str) -> str:
    """Sanitize string for XML 1.0 validity.

    Strips ANSI escapes and masks invalid control characters, surrogates, and noncharacters.
    """
    clean = strip_ansi_escapes(text)
    return "".join(c if is_valid_xml_char(c) else "?" for c in clean)


def clean_xml_text(val: str | None, *, literal: bool) -> str | None:
    """Sanitize text for XML compatibility unless literal output is active."""
    if val is None:
        return None

    if literal:
        has_invalid = any(
            (_SURROGATE_MIN <= ord(c) <= _SURROGATE_MAX) or c in (_NONCHAR_FFFE, _NONCHAR_FFFF) for c in val
        )
        if has_invalid:
            return "".join(
                "?"
                if (_SURROGATE_MIN <= ord(c) <= _SURROGATE_MAX) or c in (_NONCHAR_FFFE, _NONCHAR_FFFF)
                else c
                for c in val
            )

        return val

    return sanitize_xml_text(val)
