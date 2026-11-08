"""AI-assisted gettext PO catalog translation engine with batching, validation, and resume."""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.i18n_prompts import (
    build_plural_prompt,
    build_system_prompt,
    get_plural_rule_spec,
    validate_cli_flags_preserved,
)
from tools.i18n_validation import (
    PoCatalogEntry,
    mask_placeholders,
    parse_po_catalog,
    unmask_placeholders,
    validate_message_pair,
)

__all__ = [
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_TEMPERATURE",
    "SUPPORTED_BACKENDS",
    "TranslationConfig",
    "TranslationResult",
    "translate_catalogs",
    "translate_po_file",
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOMAIN = "findfmt"
DEFAULT_LOCALE_DIR = PROJECT_ROOT / "src" / "findfmt" / "locale"
SUPPORTED_BACKENDS: tuple[str, ...] = ("openai", "anthropic", "ollama", "mock")
DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "ollama": "qwen2.5:14b",
    "mock": "mock-deterministic-v1",
}
DEFAULT_API_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "ollama": "http://localhost:11434/api/chat",
}
DEFAULT_BATCH_SIZE = 25
DEFAULT_TEMPERATURE = 0.0
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_INTERNAL_ERROR = 500
_MOCK_PLURAL_COUNT_RE = re.compile(r"JSON array of exactly (\d+) strings")
_SINGULAR_PREFIX = "Source singular (msgid): "


@dataclass(frozen=True)
class TranslationConfig:
    """Configuration parameters for AI PO catalog translation."""

    backend: str = "openai"
    model: str | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    temperature: float = DEFAULT_TEMPERATURE
    dry_run: bool = False
    api_url: str | None = None
    api_key: str | None = None
    max_retries: int = 3
    retry_delay: float = 0.5
    transport: TransportFn | None = None
    sanitize_fn: Callable[[Path], None] | None = None

    def resolved_model(self) -> str:
        """Return explicit model name or the default model for the configured backend."""
        if self.model is not None and self.model.strip():
            return self.model.strip()

        return DEFAULT_MODELS.get(self.backend, "gpt-4o-mini")


@dataclass(frozen=True)
class TranslationResult:
    """Execution summary for a single PO catalog translation run."""

    locale: str
    po_path: Path
    total_entries: int
    untranslated_entries: int
    translated_entries: int
    batches_processed: int
    dry_run: bool


TransportFn = Callable[[str, str, TranslationConfig], str]
_InvokeFn = Callable[[str], str]


def escape_po_string(value: str) -> str:
    """Escape backslashes, double quotes, and tabs for a PO string literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t")


def format_po_msgstr(key: str, value: str) -> list[str]:
    """Format a `msgstr` or `msgstr[i]` assignment as one or more PO lines."""
    if "\n" not in value:
        return [f'{key} "{escape_po_string(value)}"']

    parts = value.split("\n")
    lines = [f'{key} ""']
    for idx, part in enumerate(parts):
        if idx < len(parts) - 1:
            lines.append(f'"{escape_po_string(part)}\\n"')
        elif part:
            lines.append(f'"{escape_po_string(part)}"')

    return lines


def apply_header_attribution(block: str, backend: str, model: str) -> str:
    """Record `X-Generator` AI model attribution in the PO header block."""
    attr_line = f'"X-Generator: findfmt-i18n ({backend}/{model})\\n"'
    lines = block.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith('"X-Generator:'):
            lines[idx] = attr_line
            return "\n".join(lines)

    lines.append(attr_line)
    return "\n".join(lines)


def update_block_msgstrs(block: str, msgstrs: tuple[str, ...], *, is_plural: bool) -> str:
    """Replace the `msgstr` section of a PO entry block while preserving comments and `msgid`."""
    lines = block.splitlines()
    idx0 = next(
        (i for i, ln in enumerate(lines) if ln.startswith(("msgstr ", "msgstr["))),
        len(lines),
    )
    if not is_plural:
        tail = format_po_msgstr("msgstr", msgstrs[0] if msgstrs else "")
    else:
        tail = [ln for i, txt in enumerate(msgstrs) for ln in format_po_msgstr(f"msgstr[{i}]", txt)]

    return "\n".join([*lines[:idx0], *tail])


def is_untranslated_block(block: str) -> PoCatalogEntry | None:
    """Return the parsed `PoCatalogEntry` if `block` is an active untranslated PO entry."""
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if not lines or any(ln.startswith("#~") for ln in lines):
        return None

    if any(ln.startswith("#,") and "fuzzy" in ln for ln in lines):
        return None

    entries = parse_po_catalog(block)
    if len(entries) != 1:
        return None

    entry = entries[0]
    return entry if not entry.msgstrs or any(s == "" for s in entry.msgstrs) else None


def build_batch_user_prompt(items: list[tuple[int, str]], locale: str) -> str:
    """Build a JSON batch prompt for translating masked singular `msgid` strings."""
    payload = [{"id": idx, "source": text} for idx, text in items]
    return (
        f"Translate the following {len(items)} CLI message(s) into locale '{locale}'.\n"
        "Preserve every `__PH_N__` token and CLI flag (`--option`, `-x`) verbatim.\n"
        f"Input JSON array:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        f"Respond with a JSON array of exactly {len(items)} translated strings in the same order."
    )


def _extract_json_array(raw_text: str) -> list[str]:
    """Extract and parse a JSON array of strings from an LLM response."""
    start = raw_text.find("[")
    end = raw_text.rfind("]")
    candidate = raw_text[start : end + 1] if 0 <= start < end else raw_text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as err:
        msg = f"Model response is not valid JSON array: {err}"
        raise ValueError(msg) from err

    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        msg = "Model response JSON must be a list of strings"
        raise ValueError(msg)

    return [str(item) for item in parsed]


def _validate_and_unmask(
    msgid: str,
    raw_tr: str,
    token_map: dict[str, str],
    *,
    msgid_plural: str | None = None,
) -> str:
    """Unmask placeholders and validate format specifiers, Rich tags, and CLI flags."""
    unmasked = unmask_placeholders(raw_tr, token_map)
    errors = [
        *validate_message_pair(msgid, unmasked, msgid_plural=msgid_plural),
        *validate_cli_flags_preserved(msgid, unmasked),
    ]
    if errors:
        msg = f"Translation validation failed for {msgid!r}: {'; '.join(errors)}"
        raise ValueError(msg)

    return unmasked


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Send an HTTP POST request with a JSON body and return the decoded JSON dictionary."""
    if not url.startswith(("https://", "http://")):
        msg = f"Unsupported URL scheme in translation endpoint: {url}"
        raise ValueError(msg)

    req_headers = {"Content-Type": "application/json", **headers}
    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=60.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if not isinstance(data, dict):
        msg = "Expected JSON object response from translation provider"
        raise TypeError(msg)

    return data


def _mock_transport(system_prompt: str, user_prompt: str, _config: TranslationConfig) -> str:
    """Deterministic offline transport for unit tests and local dry verification."""
    loc_match = re.search(r"locale '([^']+)'", system_prompt)
    locale = loc_match.group(1) if loc_match is not None else "xx"
    plural_match = _MOCK_PLURAL_COUNT_RE.search(user_prompt)
    if plural_match is not None:
        count = int(plural_match.group(1))
        raw_src = next(
            (
                ln.removeprefix(_SINGULAR_PREFIX).strip()
                for ln in user_prompt.splitlines()
                if ln.startswith(_SINGULAR_PREFIX)
            ),
            "",
        )
        src = raw_src.strip("'\"").replace("\\n", "\n")
        return json.dumps([f"[{locale}:{i}] {src}" for i in range(count)], ensure_ascii=False)

    start = user_prompt.find("[")
    end = user_prompt.rfind("]")
    items = json.loads(user_prompt[start : end + 1]) if 0 <= start < end else []
    return json.dumps([f"[{locale}] {item['source']}" for item in items], ensure_ascii=False)


def _default_transport(system_prompt: str, user_prompt: str, config: TranslationConfig) -> str:
    """Execute a chat completion request against the configured LLM backend."""
    model = config.resolved_model()
    chat_msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    if config.backend == "mock":
        return _mock_transport(system_prompt, user_prompt, config)

    if config.backend == "openai":
        api_key = config.api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            msg = "OPENAI_API_KEY environment variable is required for 'openai' backend"
            raise RuntimeError(msg)

        url = config.api_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_API_URLS["openai"]
        body = {"model": model, "temperature": config.temperature, "messages": chat_msgs}
        resp = _post_json(url, body, {"Authorization": f"Bearer {api_key}"})
        return str(resp["choices"][0]["message"]["content"])

    if config.backend == "anthropic":
        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            msg = "ANTHROPIC_API_KEY environment variable is required for 'anthropic' backend"
            raise RuntimeError(msg)

        url = config.api_url or DEFAULT_API_URLS["anthropic"]
        user_msgs = [{"role": "user", "content": user_prompt}]
        body = {
            "model": model,
            "max_tokens": 4096,
            "temperature": config.temperature,
            "system": system_prompt,
            "messages": user_msgs,
        }
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        return str(_post_json(url, body, headers)["content"][0]["text"])

    if config.backend == "ollama":
        url = config.api_url or os.environ.get("OLLAMA_HOST") or DEFAULT_API_URLS["ollama"]
        opts = {"temperature": config.temperature}
        body = {"model": model, "stream": False, "options": opts, "messages": chat_msgs}
        return str(_post_json(url, body, {})["message"]["content"])

    msg = f"Unsupported translation backend: {config.backend!r}"
    raise ValueError(msg)


def _call_with_retry(
    transport: TransportFn,
    sys_prompt: str,
    user_prompt: str,
    cfg: TranslationConfig,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> str:
    """Invoke `transport` with exponential backoff on transient HTTP or network errors."""
    attempts = max(1, cfg.max_retries)
    attempt = 0
    while True:
        try:
            return transport(sys_prompt, user_prompt, cfg)
        except urllib.error.HTTPError as err:
            is_retryable = err.code == _HTTP_TOO_MANY_REQUESTS or err.code >= _HTTP_INTERNAL_ERROR
            if not is_retryable or attempt + 1 >= attempts:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 >= attempts:
                raise

        sleep_fn(cfg.retry_delay * (2**attempt))
        attempt += 1


def _translate_plural_entry(
    ent: PoCatalogEntry,
    locale: str,
    po_text: str,
    invoke: _InvokeFn,
) -> tuple[str, ...]:
    """Translate and validate a single `ngettext` plural entry across all target forms."""
    plural_src = ent.msgid_plural or ent.msgid
    spec = get_plural_rule_spec(locale, po_text=po_text)
    merged_map = {**mask_placeholders(ent.msgid)[1], **mask_placeholders(plural_src)[1]}
    prompt = build_plural_prompt(ent.msgid, plural_src, locale, po_text=po_text)
    forms = _extract_json_array(invoke(prompt))
    if len(forms) != spec.nplurals:
        msg = f"Expected {spec.nplurals} plural forms for {locale}, got {len(forms)}"
        raise ValueError(msg)

    return tuple(
        _validate_and_unmask(
            ent.msgid,
            form,
            {tok: val for tok, val in merged_map.items() if tok in form},
            msgid_plural=plural_src,
        )
        for form in forms
    )


def _translate_singular_batch(
    batch: list[tuple[int, PoCatalogEntry]],
    locale: str,
    invoke: _InvokeFn,
) -> list[tuple[int, tuple[str, ...]]]:
    """Translate and validate a batch of singular PO entries."""
    masked = [mask_placeholders(entry.msgid) for _, entry in batch]
    items = [(idx, m_text) for idx, (m_text, _) in enumerate(masked)]
    translations = _extract_json_array(invoke(build_batch_user_prompt(items, locale)))
    if len(translations) != len(batch):
        msg = f"Expected {len(batch)} batch translations, got {len(translations)}"
        raise ValueError(msg)

    return [
        (b_idx, (_validate_and_unmask(entry.msgid, raw_tr, tok_map),))
        for (b_idx, entry), raw_tr, (_, tok_map) in zip(batch, translations, masked, strict=True)
    ]


def translate_po_file(
    po_path: Path,
    locale: str,
    config: TranslationConfig | None = None,
    *,
    transport: TransportFn | None = None,
    sanitize_fn: Callable[[Path], None] | None = None,
) -> TranslationResult:
    """Translate untranslated entries in po_path with batching, checkpointing, and sanitization."""
    cfg = config or TranslationConfig()
    active_transport = transport or cfg.transport or _default_transport
    active_sanitize = sanitize_fn or cfg.sanitize_fn
    po_text = po_path.read_text(encoding="utf-8")
    total = len(parse_po_catalog(po_text))
    blocks = po_text.split("\n\n")
    pending = [
        (idx, entry)
        for idx, blk in enumerate(blocks)
        if (entry := is_untranslated_block(blk)) is not None
    ]
    untrans = len(pending)
    batch_size = max(1, cfg.batch_size)
    if cfg.dry_run or not pending:
        planned = math.ceil(untrans / batch_size) if pending and cfg.dry_run else 0
        return TranslationResult(locale, po_path, total, untrans, 0, planned, dry_run=cfg.dry_run)

    sys_prompt = build_system_prompt(locale)
    model_name = cfg.resolved_model()
    done = 0
    batches = 0

    def _invoke(user_prompt: str) -> str:
        return _call_with_retry(active_transport, sys_prompt, user_prompt, cfg)

    for start in range(0, untrans, batch_size):
        chunk = pending[start : start + batch_size]
        singular = [(b_idx, ent) for b_idx, ent in chunk if ent.msgid_plural is None]
        plural = [(b_idx, ent) for b_idx, ent in chunk if ent.msgid_plural is not None]
        if singular:
            for b_idx, msgstrs in _translate_singular_batch(singular, locale, _invoke):
                blocks[b_idx] = update_block_msgstrs(blocks[b_idx], msgstrs, is_plural=False)
                done += 1

        for b_idx, ent in plural:
            msgstrs = _translate_plural_entry(ent, locale, po_text, _invoke)
            blocks[b_idx] = update_block_msgstrs(blocks[b_idx], msgstrs, is_plural=True)
            done += 1

        if blocks and 'msgid ""' in blocks[0]:
            blocks[0] = apply_header_attribution(blocks[0], cfg.backend, model_name)

        po_path.write_text("\n\n".join(blocks), encoding="utf-8")
        if active_sanitize is not None:
            active_sanitize(po_path)

        batches += 1

    return TranslationResult(locale, po_path, total, untrans, done, batches, dry_run=False)


def translate_catalogs(
    locale: str | None = None,
    *,
    all_locales: bool = False,
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    domain: str = DEFAULT_DOMAIN,
    config: TranslationConfig | None = None,
) -> int:
    """Translate one or all locale PO catalogs under `locale_dir`."""
    if all_locales:
        targets = [
            (p.parent.parent.name, p) for p in sorted(locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"))
        ]
        if not targets:
            sys.stderr.write(f"Error: No PO catalogs found under {locale_dir}.\n")
            return 1
    elif locale is not None and locale.strip():
        loc = locale.strip()
        po_path = locale_dir / loc / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.is_file():
            sys.stderr.write(f"Error: Catalog {po_path} not found. Run 'init {loc}' first.\n")
            return 1

        targets = [(loc, po_path)]
    else:
        sys.stderr.write("Error: Specify a <locale> (or --locale <locale>) or --all.\n")
        return 1

    cfg = config or TranslationConfig()
    try:
        for loc, po_path in targets:
            res = translate_po_file(po_path, loc, cfg)
            mode = "Dry-run" if res.dry_run else "Translated"
            sys.stdout.write(
                f"{mode} {loc} ({po_path}): {res.translated_entries}/{res.untranslated_entries} "
                f"untranslated entries across {res.batches_processed} batch(es).\n",
            )
    except (OSError, RuntimeError, TypeError, ValueError) as err:
        sys.stderr.write(f"Error translating catalog: {err}\n")
        return 1

    return 0
