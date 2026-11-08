"""Unit tests for AI gettext translation engine and `tools/i18n.py translate` subcommand."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from typing import Self

import pytest
from tools.i18n import _sanitize_po_locations, main
from tools.i18n_translate import (
    TranslationConfig,
    _call_with_retry,
    _default_transport,
    _extract_json_array,
    _post_json,
    _validate_and_unmask,
    apply_header_attribution,
    build_batch_user_prompt,
    escape_po_string,
    format_po_msgstr,
    is_untranslated_block,
    translate_catalogs,
    translate_po_file,
    update_block_msgstrs,
)

SAMPLE_PO_CONTENT = (
    '# Spanish translations for findfmt.\nmsgid ""\nmsgstr ""\n'
    '"Project-Id-Version: findfmt 1.1.3\\n"\n'
    '"Language: es\\n"\n'
    '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n'
    '"Content-Type: text/plain; charset=utf-8\\n"\n\n'
    "#: /home/dev/findfmt/src/findfmt/diagnostics.py:10\n"
    'msgid "already done"\nmsgstr "ya hecho"\n\n'
    "#: /home/dev/findfmt/src/findfmt/cli/main.py:25\n"
    'msgid "Path \'{path}\' with --format"\nmsgstr ""\n\n'
    "#: /home/dev/findfmt/src/findfmt/cli/runner.py:40\n"
    'msgid "[bold]Matched:[/] {count}"\nmsgstr ""\n\n'
    '#: /home/dev/findfmt/src/findfmt/summary.py:15\nmsgid "{count} file"\n'
    'msgid_plural "{count} files"\nmsgstr[0] ""\nmsgstr[1] ""\n'
)


class _DummyResponse:
    """Context manager stub for `urllib.request.urlopen` responses."""

    def __init__(self, payload: object) -> None:
        self._bytes = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._bytes

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        pass


def test_config_and_po_string_formatting() -> None:
    """Verify TranslationConfig model resolution and PO string escaping/multiline formatting."""
    assert TranslationConfig(backend="openai").resolved_model() == "gpt-4o-mini"
    assert TranslationConfig(backend="anthropic").resolved_model() == "claude-3-5-haiku-latest"
    assert TranslationConfig(backend="ollama", model="llama3").resolved_model() == "llama3"

    assert escape_po_string('a\\b"c\td') == 'a\\\\b\\"c\\td'
    assert format_po_msgstr("msgstr", "simple") == ['msgstr "simple"']
    assert format_po_msgstr("msgstr", "line1\nline2\n") == [
        'msgstr ""',
        '"line1\\n"',
        '"line2\\n"',
    ]
    assert format_po_msgstr("msgstr[0]", "line1\nline2") == [
        'msgstr[0] ""',
        '"line1\\n"',
        '"line2"',
    ]


def test_header_attribution_and_block_helpers() -> None:
    """Verify header X-Generator attribution, block msgstr replacement, and block filtering."""
    header = 'msgid ""\nmsgstr ""\n"Language: es\\n"\n"Content-Type: text/plain; charset=utf-8\\n"'
    updated = apply_header_attribution(header, "openai", "gpt-4o-mini")
    assert '"X-Generator: findfmt-i18n (openai/gpt-4o-mini)\\n"' in updated
    assert '"Content-Type: text/plain; charset=utf-8\\n"' in updated

    replaced = apply_header_attribution(updated, "anthropic", "claude-3-5-haiku-latest")
    assert replaced.count("X-Generator:") == 1
    assert '"X-Generator: findfmt-i18n (anthropic/claude-3-5-haiku-latest)\\n"' in replaced

    singular_blk = '#: src/a.py:1\nmsgid "hello"\nmsgstr ""'
    assert update_block_msgstrs(singular_blk, ("hola",), is_plural=False) == (
        '#: src/a.py:1\nmsgid "hello"\nmsgstr "hola"'
    )
    plural_blk = '#: src/a.py:2\nmsgid "one"\nmsgid_plural "many"\nmsgstr[0] ""\nmsgstr[1] ""'
    assert update_block_msgstrs(plural_blk, ("uno", "muchos"), is_plural=True) == (
        '#: src/a.py:2\nmsgid "one"\nmsgid_plural "many"\nmsgstr[0] "uno"\nmsgstr[1] "muchos"'
    )

    assert is_untranslated_block("") is None
    assert is_untranslated_block(header) is None
    assert is_untranslated_block('#~ msgid "old"\n#~ msgstr ""') is None
    assert is_untranslated_block('#, fuzzy\nmsgid "f"\nmsgstr ""') is None
    assert is_untranslated_block('msgid "done"\nmsgstr "hecho"') is None
    entry = is_untranslated_block(singular_blk)
    assert entry is not None
    assert entry.msgid == "hello"


def test_prompt_json_extraction_and_validation() -> None:
    """Verify batch prompt construction, JSON array extraction, and placeholder/flag validation."""
    prompt = build_batch_user_prompt([(0, "Hello __PH_0__")], "es")
    assert "__PH_0__" in prompt
    assert _extract_json_array('```json\n["Hola", "Mundo"]\n```') == ["Hola", "Mundo"]

    with pytest.raises(ValueError, match="not valid JSON array"):
        _extract_json_array("not json at all")

    with pytest.raises(ValueError, match="list of strings"):
        _extract_json_array("[1, 2]")

    valid = _validate_and_unmask(
        "Use --format with {name}",
        "Usar --format con __PH_0__",
        {"__PH_0__": "{name}"},
    )
    assert valid == "Usar --format con {name}"

    with pytest.raises(ValueError, match="Translation validation failed"):
        _validate_and_unmask("Use --format", "Usar --formato", {})


def test_post_json_and_provider_transports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify stdlib HTTP transport for openai, anthropic, ollama, and error paths."""
    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        _post_json("ftp://example.com", {}, {})

    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: _DummyResponse(["not-dict"]))
    with pytest.raises(TypeError, match="Expected JSON object"):
        _post_json("https://api.openai.com/v1/chat/completions", {}, {})

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        _default_transport("sys", "usr", TranslationConfig(backend="openai"))

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        _default_transport("sys", "usr", TranslationConfig(backend="anthropic"))

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_a, **_k: _DummyResponse({"choices": [{"message": {"content": '["ok-oai"]'}}]}),
    )
    oai_cfg = TranslationConfig(backend="openai", api_key="sk-test")
    assert _default_transport("sys", "usr", oai_cfg) == '["ok-oai"]'

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_a, **_k: _DummyResponse({"content": [{"text": '["ok-ant"]'}]}),
    )
    ant_cfg = TranslationConfig(backend="anthropic", api_key="ant-test")
    assert _default_transport("sys", "usr", ant_cfg) == '["ok-ant"]'

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_a, **_k: _DummyResponse({"message": {"content": '["ok-oll"]'}}),
    )
    oll_cfg = TranslationConfig(backend="ollama")
    assert _default_transport("sys", "usr", oll_cfg) == '["ok-oll"]'

    with pytest.raises(ValueError, match="Unsupported translation backend"):
        _default_transport("sys", "usr", TranslationConfig(backend="unknown"))


def test_call_with_retry_backoff() -> None:
    """Verify exponential backoff retry on HTTP 429/5xx, URLError, and non-retryable 400."""
    sleeps: list[float] = []
    calls = 0
    url = "https://x"

    def _flaky_transport(_sys: str, _usr: str, _cfg: TranslationConfig) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise urllib.error.HTTPError(url, 429, "Rate limit", Message(), io.BytesIO())

        if calls == 2:
            raise urllib.error.URLError(TimeoutError())

        return '["recovered"]'

    cfg = TranslationConfig(backend="mock", max_retries=3, retry_delay=0.25)
    assert _call_with_retry(_flaky_transport, "s", "u", cfg, sleeps.append) == '["recovered"]'
    assert sleeps == [0.25, 0.5]

    def _bad_req(_sys: str, _usr: str, _cfg: TranslationConfig) -> str:
        raise urllib.error.HTTPError(url, 400, "Bad request", Message(), io.BytesIO())

    with pytest.raises(urllib.error.HTTPError):
        _call_with_retry(_bad_req, "s", "u", cfg, sleeps.append)

    def _always_timeout(_sys: str, _usr: str, _cfg: TranslationConfig) -> str:
        raise TimeoutError

    with pytest.raises(TimeoutError):
        _call_with_retry(_always_timeout, "s", "u", cfg, sleeps.append)


def test_translate_po_file_dry_run_and_full_execution(tmp_path: Path) -> None:
    """Verify dry-run preview, batching, plural translation, attribution, and sanitization."""
    po_path = tmp_path / "es" / "LC_MESSAGES" / "findfmt.po"
    po_path.parent.mkdir(parents=True)
    po_path.write_text(SAMPLE_PO_CONTENT, encoding="utf-8")

    dry_cfg = TranslationConfig(backend="mock", batch_size=2, dry_run=True)
    dry_res = translate_po_file(po_path, "es", dry_cfg)
    assert dry_res.total_entries == 4
    assert dry_res.untranslated_entries == 3
    assert dry_res.translated_entries == 0
    assert dry_res.batches_processed == 2
    assert dry_res.dry_run is True
    assert po_path.read_text(encoding="utf-8") == SAMPLE_PO_CONTENT

    run_cfg = TranslationConfig(backend="mock", batch_size=2)
    res = translate_po_file(
        po_path,
        "es",
        run_cfg,
        sanitize_fn=lambda p: _sanitize_po_locations(p, root=Path("/home/dev/findfmt")),
    )
    assert res.untranslated_entries == 3
    assert res.translated_entries == 3
    assert res.batches_processed == 2
    assert res.dry_run is False

    final_text = po_path.read_text(encoding="utf-8")
    assert '"X-Generator: findfmt-i18n (mock/mock-deterministic-v1)\\n"' in final_text
    assert '"Content-Type: text/plain; charset=utf-8\\n"' in final_text
    assert "/home/dev/findfmt" not in final_text
    assert "#: src/findfmt/cli/main.py:25" in final_text
    assert "msgstr \"[es] Path '{path}' with --format\"" in final_text
    assert 'msgstr[0] "[es:0] {count} file"' in final_text
    assert 'msgstr[1] "[es:1] {count} file"' in final_text

    # Re-running when all entries are translated is a no-op
    noop_res = translate_po_file(po_path, "es", run_cfg)
    assert noop_res.untranslated_entries == 0
    assert noop_res.translated_entries == 0
    assert noop_res.batches_processed == 0

    # Batch length mismatch & plural form count mismatch raise ValueError
    po_path.write_text(SAMPLE_PO_CONTENT, encoding="utf-8")
    with pytest.raises(ValueError, match="Expected 2 batch translations, got 1"):
        translate_po_file(po_path, "es", run_cfg, transport=lambda *_a: '["only one"]')

    plural_only_po = tmp_path / "plural_only.po"
    plural_only_po.write_text(
        'msgid "{count} file"\nmsgid_plural "{count} files"\nmsgstr[0] ""\nmsgstr[1] ""\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Expected 2 plural forms for es, got 1"):
        translate_po_file(
            plural_only_po,
            "es",
            run_cfg,
            transport=lambda *_a: '["{count} archivo"]',
        )
    # Translate headerless catalog cleanly
    translate_po_file(plural_only_po, "es", run_cfg)
    assert 'msgstr[0] "[es:0] {count} file"' in plural_only_po.read_text(encoding="utf-8")


def test_partial_resume_after_network_failure(tmp_path: Path) -> None:
    """Verify completed batches are checkpointed before a mid-run failure and resume cleanly."""
    po_path = tmp_path / "fr" / "LC_MESSAGES" / "findfmt.po"
    po_path.parent.mkdir(parents=True)
    po_path.write_text(SAMPLE_PO_CONTENT, encoding="utf-8")

    call_count = 0

    def _fail_on_second_batch(sys_p: str, usr_p: str, cfg: TranslationConfig) -> str:
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            msg = "Simulated mid-run network outage"
            raise RuntimeError(msg)

        return _default_transport(sys_p, usr_p, cfg)

    cfg = TranslationConfig(backend="mock", batch_size=2, max_retries=1)
    with pytest.raises(RuntimeError, match="Simulated mid-run network outage"):
        translate_po_file(
            po_path,
            "fr",
            cfg,
            transport=_fail_on_second_batch,
            sanitize_fn=lambda p: _sanitize_po_locations(p, root=Path("/home/dev/findfmt")),
        )

    # Batch 1 (2 singular entries) was checkpointed to disk; batch 2 (1 plural entry) remains
    partial_text = po_path.read_text(encoding="utf-8")
    assert "msgstr \"[fr] Path '{path}' with --format\"" in partial_text
    assert "/home/dev/findfmt" not in partial_text

    resumed = translate_po_file(po_path, "fr", cfg)
    assert resumed.untranslated_entries == 1
    assert resumed.translated_entries == 1
    assert resumed.batches_processed == 1


def test_translate_catalogs_and_cli_dispatch(tmp_path: Path) -> None:
    """Verify `translate_catalogs` and `tools/i18n.py translate` CLI options and error handling."""
    locale_dir = tmp_path / "locale"
    es_po = locale_dir / "es" / "LC_MESSAGES" / "findfmt.po"
    es_po.parent.mkdir(parents=True)
    es_po.write_text(SAMPLE_PO_CONTENT, encoding="utf-8")

    # Missing locale / --all error
    assert translate_catalogs(locale_dir=locale_dir) == 1
    # Non-existent locale catalog error
    assert translate_catalogs("de", locale_dir=locale_dir) == 1
    # Empty directory with --all error
    assert translate_catalogs(all_locales=True, locale_dir=tmp_path / "empty") == 1

    # CLI dry-run via --locale
    assert (
        main(
            [
                "translate",
                "--locale",
                "es",
                "--localedir",
                str(locale_dir),
                "--backend",
                "mock",
                "--dry-run",
            ],
        )
        == 0
    )

    # CLI full translation via --all
    assert (
        main(
            [
                "translate",
                "--all",
                "--localedir",
                str(locale_dir),
                "--backend",
                "mock",
                "--batch-size",
                "2",
            ],
        )
        == 0
    )
    assert "msgstr \"[es] Path '{path}' with --format\"" in es_po.read_text(encoding="utf-8")

    # Error return code when transport raises ValueError
    es_po.write_text(SAMPLE_PO_CONTENT, encoding="utf-8")
    bad_code = translate_catalogs(
        "es",
        locale_dir=locale_dir,
        config=TranslationConfig(backend="mock", transport=lambda *_a: "invalid json"),
    )
    assert bad_code == 1
