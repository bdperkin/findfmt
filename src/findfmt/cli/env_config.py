"""Environment-variable configuration layer (FINDFMT_*) for findfmt (#456)."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from findfmt.cli.config_schema import (
    _BOOL_KEYS,
    _INT_KEYS,
    _STR_LIST_KEYS,
    ACCEPTED_CONFIG_KEYS,
    validate_and_convert_config,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from typer.core import _click

__all__ = [
    "ENV_CONFIG_PREFIX",
    "RESERVED_ENV_VARS",
    "collect_context_config_overrides",
    "load_env_config",
    "merge_raw_config",
    "merge_raw_config_with_sources",
]

ENV_CONFIG_PREFIX = "FINDFMT_"
RESERVED_ENV_VARS: frozenset[str] = frozenset(
    {
        "FINDFMT_CONFIG",
        "FINDFMT_CONTAINER_TESTS",
        "FINDFMT_NO_EXTENSIONS",
    },
)
_ENV_SOURCE = Path("environment")
_TRUE_STRINGS: frozenset[str] = frozenset({"1", "true", "yes", "on"})
_FALSE_STRINGS: frozenset[str] = frozenset({"0", "false", "no", "off"})


def _parse_env_bool(raw_val: str) -> object:
    """Parse a boolean environment variable string or return raw string on mismatch."""
    lowered = raw_val.strip().lower()
    if lowered in _TRUE_STRINGS:
        return True

    if lowered in _FALSE_STRINGS:
        return False

    return raw_val


def _parse_env_int(raw_val: str) -> object:
    """Parse an integer environment variable string or return raw string on mismatch."""
    try:
        return int(raw_val.strip(), 10)
    except ValueError:
        return raw_val


def _parse_env_list(stripped: str) -> object:
    """Parse a comma-separated string or TOML/JSON array literal into a list."""
    if stripped.startswith("["):
        try:
            return tomllib.loads(f"v = {stripped}")["v"]
        except tomllib.TOMLDecodeError:
            return [None]

    return [item.strip() for item in stripped.split(",") if item.strip()]


def _coerce_env_value(key: str, raw_val: str) -> object:
    """Coerce a raw environment variable string into a schema-typed Python value."""
    if key in _BOOL_KEYS:
        return _parse_env_bool(raw_val)

    if key in _INT_KEYS:
        return _parse_env_int(raw_val)

    if key in _STR_LIST_KEYS:
        return _parse_env_list(raw_val.strip())

    if key in ("format", "output_format", "color", "pager"):
        return raw_val.strip()

    return raw_val


def _canonical_target_key(raw_key: str) -> str:
    """Return the canonical target parameter name for a configuration key."""
    key = raw_key.removeprefix(ENV_CONFIG_PREFIX).lower().replace("-", "_")
    if key in ("format", "output_format"):
        return "output_format"

    if key in _BOOL_KEYS:
        return _BOOL_KEYS[key][0]

    if key in _STR_LIST_KEYS:
        return _STR_LIST_KEYS[key]

    return key


def merge_raw_config(
    base_raw: Mapping[str, Any],
    override_raw: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge raw configuration dictionaries, replacing overridden alias keys.

    Args:
        base_raw: Lower-precedence raw configuration dictionary (e.g. from file).
        override_raw: Higher-precedence raw configuration dictionary (e.g. from env).

    Returns:
        Combined raw configuration dictionary with conflicting aliases removed.
    """
    if not override_raw:
        return dict(base_raw)

    override_targets = {_canonical_target_key(k) for k in override_raw}
    merged = {k: v for k, v in base_raw.items() if _canonical_target_key(k) not in override_targets}
    merged.update(override_raw)
    return merged


def load_env_config(
    env: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Discover, coerce, and validate ``FINDFMT_*`` environment variables.

    Args:
        env: Optional environment mapping override (defaults to ``os.environ``).

    Returns:
        Tuple of ``(raw_env_data, converted_defaults)``.

    Raises:
        typer.Exit: On unrecognized ``FINDFMT_*`` keys or invalid values (exit code 2).
    """
    mapping = os.environ if env is None else env
    env_for_validation: dict[str, Any] = {}
    raw_env_data: dict[str, Any] = {}

    for env_name, raw_val in sorted(mapping.items()):
        if not env_name.startswith(ENV_CONFIG_PREFIX) or env_name in RESERVED_ENV_VARS:
            continue

        key = env_name.removeprefix(ENV_CONFIG_PREFIX).lower().replace("-", "_")
        if key in ACCEPTED_CONFIG_KEYS and not raw_val.strip():
            continue

        coerced = _coerce_env_value(key, raw_val)
        env_for_validation[env_name] = coerced
        raw_env_data[key] = coerced

    if not env_for_validation:
        return {}, {}

    converted = validate_and_convert_config(env_for_validation, _ENV_SOURCE)
    return raw_env_data, converted


_NON_CONFIG_CLI_PARAMS: frozenset[str] = frozenset(
    {
        "paths",
        "known_tags",
        "verbose",
        "diagnostics",
        "version",
        "help_all",
        "config",
        "no_config",
        "show_config",
        "generate_config",
    },
)


def merge_raw_config_with_sources(
    base_raw: Mapping[str, Any],
    base_sources: Mapping[str, str],
    override_raw: Mapping[str, Any],
    override_source: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Merge raw config dictionaries and record the provenance label for each key.

    Args:
        base_raw: Lower-precedence raw configuration dictionary.
        base_sources: Provenance labels corresponding to ``base_raw`` keys.
        override_raw: Higher-precedence raw configuration dictionary.
        override_source: Provenance label to assign to keys from ``override_raw``.

    Returns:
        Tuple of ``(merged_raw, merged_sources)``.
    """
    merged_raw = merge_raw_config(base_raw, override_raw)
    merged_sources = {k: base_sources[k] for k in merged_raw if k in base_sources}
    for k in override_raw:
        merged_sources[k] = override_source

    return merged_raw, merged_sources


def _cli_param_to_config_item(param_name: str, param_val: object) -> tuple[str, Any]:
    """Convert a Click CLI parameter name and value into a TOML config key and value."""
    if param_name == "output_format":
        return "format", str(param_val)

    if param_name in ("tree", "json", "xml"):
        return "format", param_name

    if param_name == "no_ignore":
        return "ignore", not bool(param_val)

    if param_name in ("color", "pager") and isinstance(param_val, bool):
        return param_name, "always" if param_val else "never"

    if isinstance(param_val, (list, tuple)):
        return param_name, list(param_val)

    return param_name, param_val


def collect_context_config_overrides(
    ctx: _click.Context,
    base_raw: Mapping[str, Any],
    base_sources: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Layer wrapper defaults and CLI overrides from a Click Context onto raw config data.

    Args:
        ctx: Active Click/Typer Context instance.
        base_raw: Raw configuration dictionary from config files and environment variables.
        base_sources: Provenance labels for ``base_raw`` keys.

    Returns:
        Tuple of ``(data_with_overrides, sources_with_overrides)``.
    """
    data = dict(base_raw)
    sources = dict(base_sources)
    wrapper_defaults: Mapping[str, Any] = ctx.meta.get("findfmt_wrapper_defaults", {})

    for key, val in wrapper_defaults.items():
        src = ctx.get_parameter_source(key)
        if src is not None and src.name == "DEFAULT":
            raw_k, raw_v = _cli_param_to_config_item(key, val)
            data, sources = merge_raw_config_with_sources(
                data,
                sources,
                {raw_k: raw_v},
                "default",
            )

    for param_name, param_val in ctx.params.items():
        if param_name in _NON_CONFIG_CLI_PARAMS:
            continue

        param_source = ctx.get_parameter_source(param_name)
        if param_source is not None and param_source.name == "COMMANDLINE":
            raw_k, raw_v = _cli_param_to_config_item(param_name, param_val)
            data, sources = merge_raw_config_with_sources(
                data,
                sources,
                {raw_k: raw_v},
                "cli",
            )

    return data, sources
