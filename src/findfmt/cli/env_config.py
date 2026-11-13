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

__all__ = [
    "ENV_CONFIG_PREFIX",
    "RESERVED_ENV_VARS",
    "load_env_config",
    "merge_raw_config",
]

ENV_CONFIG_PREFIX = "FINDFMT_"
RESERVED_ENV_VARS: frozenset[str] = frozenset(
    {
        "FINDFMT_CONFIG",
        "FINDFMT_CONTAINER_TESTS",
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
