"""Redirected output is written as UTF-8 on Windows before Python 3.15 (#496)."""

from __future__ import annotations

import io

import pytest

from findfmt.cli.pager import _ensure_utf8_output

TEXT = "╭─ 日本.txt → a.txt ─╮\n"


def _stream(encoding: str = "cp1252") -> io.TextIOWrapper:
    return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors="surrogateescape")


def test_windows_code_page_streams_switch_to_utf8() -> None:
    """A cp1252 stream on Windows is reconfigured to UTF-8 and keeps its error handler."""
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", errors="surrogateescape")
    with pytest.raises(UnicodeEncodeError):
        stream.write(TEXT)

    _ensure_utf8_output([stream], env={}, platform="win32")
    assert (stream.encoding, stream.errors) == ("utf-8", "surrogateescape")
    stream.write(TEXT)
    stream.flush()
    assert raw.getvalue() == TEXT.encode()


@pytest.mark.parametrize(
    ("env", "platform"),
    [
        ({"PYTHONIOENCODING": "cp1252"}, "win32"),
        ({"PYTHONUTF8": "0"}, "win32"),
        ({}, "linux"),
        ({}, "darwin"),
    ],
)
def test_explicit_choices_and_other_platforms_are_respected(
    env: dict[str, str],
    platform: str,
) -> None:
    """PYTHONIOENCODING, PYTHONUTF8=0, and non-Windows locale encodings are left unchanged."""
    stream = _stream()
    _ensure_utf8_output([stream], env=env, platform=platform)
    assert stream.encoding == "cp1252"


def test_utf8_aliases_and_plain_streams_are_left_alone() -> None:
    """Streams already in UTF-8 (any alias) or without reconfigure() are not touched."""
    utf8 = _stream("UTF8")
    plain = io.StringIO()
    _ensure_utf8_output([utf8, plain, object()], env={}, platform="win32")
    assert utf8.encoding == "UTF8"


def test_unknown_encodings_switch_to_utf8() -> None:
    """A stream reporting an encoding Python does not know is treated as not UTF-8."""
    calls: list[dict[str, str]] = []

    class Stream:
        encoding = "x-no-such-codec"
        errors = None

        def reconfigure(self, **kwargs: str) -> None:
            calls.append(kwargs)

    _ensure_utf8_output([Stream()], env={}, platform="win32")
    assert calls == [{"encoding": "utf-8", "errors": "strict"}]


def test_default_streams_are_the_standard_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without arguments, sys.stdout and sys.stderr are checked."""
    out, err = _stream(), _stream()
    monkeypatch.setattr("sys.stdout", out)
    monkeypatch.setattr("sys.stderr", err)
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    _ensure_utf8_output(platform="win32")
    assert (out.encoding, err.encoding) == ("utf-8", "utf-8")
