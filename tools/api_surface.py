"""Dump the public API surface of ``findfmt`` as deterministic JSON (#493).

The public API is every name a module lists in ``__all__``. For each name the dump records what it
is and, where meaningful, its call signature, its public members (classes), or its values (enums).
The committed snapshot ``tests/unit/api_surface.json`` pins the surface, so any change to it shows
up in review and must be acknowledged in the changelog.

Usage:
    python tools/api_surface.py              # print the surface
    python tools/api_surface.py --write      # regenerate the committed snapshot
"""

from __future__ import annotations

import argparse
import enum
import importlib
import inspect
import json
import pkgutil
import re
import sys
import types
import typing
from pathlib import Path
from typing import Any

SNAPSHOT = Path(__file__).resolve().parents[1] / "tests" / "unit" / "api_surface.json"


def _signature(obj: object) -> str:
    """Return a stable signature string, or an empty string if there is none."""
    if not callable(obj):
        return ""

    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return ""


def _is_own(obj: object) -> bool:
    """Return True if ``obj`` is defined in findfmt (not re-exported from a dependency)."""
    return str(getattr(obj, "__module__", "")).split(".")[0] == "findfmt"


def _class_signature(cls: type) -> str:
    """Return the constructor signature, or where it is inherited from if a dependency owns it.

    Signatures inherited from third-party classes are not findfmt's API, and Python 3.11 renders
    their annotations differently from 3.12+, so they are recorded by origin only.
    """
    owner = next(c for c in cls.__mro__ if "__init__" in vars(c) or "__new__" in vars(c))
    if owner is object or _is_own(owner):
        return _signature(cls)

    return f"inherited from {owner.__module__}.{owner.__qualname__}"


# Concrete platform flavours of pathlib.Path (PosixPath on Linux/macOS, WindowsPath on Windows).
_PATH_FLAVOURS = {"PosixPath": "Path", "WindowsPath": "Path"}


def _public_module(module: str) -> str:
    """Drop private components from a module path (``pathlib._local`` -> ``pathlib``)."""
    return ".".join(part for part in module.split(".") if not part.startswith("_"))


def _qualified_name(cls: type) -> str:
    """Return ``module.Qualname`` without private module components or platform path flavours.

    ``pathlib.Path`` lives in ``pathlib._local`` on Python 3.13 only, and paths are ``PosixPath``
    or ``WindowsPath`` depending on the platform, so both are canonicalized.
    """
    module = _public_module(cls.__module__)
    name = (
        _PATH_FLAVOURS.get(cls.__qualname__, cls.__qualname__)
        if module == "pathlib"
        else cls.__qualname__
    )
    return name if module == "builtins" else f"{module}.{name}"


def _type_name(tp: object) -> str:
    """Return a version- and platform-stable, address-free name for a type or type expression."""
    if tp is type(None):
        return "None"

    if isinstance(tp, type):
        return _qualified_name(tp)

    origin, args = typing.get_origin(tp), typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        return " | ".join(_type_name(arg) for arg in args)

    if origin is not None and args:
        return f"{_type_name(origin)}[{', '.join(_type_name(arg) for arg in args)}]"

    return re.sub(r" at 0x[0-9a-f]+", "", repr(tp))


def _alias(obj: object) -> str:
    """Describe a type alias; ``Annotated`` metadata objects are omitted (their reprs vary)."""
    if typing.get_origin(obj) is typing.Annotated:
        return f"Annotated[{_type_name(typing.get_args(obj)[0])}, ...]"

    return _type_name(obj)


def _describe_type(cls: type) -> dict[str, Any]:
    """Describe an exported enum, exception, or class."""
    if issubclass(cls, enum.Enum):
        return {
            "kind": "enum",
            "bases": [b.__name__ for b in cls.__bases__],
            "members": {m.name: m.value for m in cls},
        }

    if issubclass(cls, BaseException):
        return {"kind": "exception", "bases": [b.__name__ for b in cls.__mro__[1:-1]]}

    members = {
        name: _signature(value) if callable(value) else "attribute"
        for name, value in sorted(vars(cls).items())
        if not name.startswith("_") or name == "__init__"
    }
    return {"kind": "class", "signature": _class_signature(cls), "members": members}


def _describe(obj: object) -> dict[str, Any]:
    """Describe one exported object."""
    if type(obj).__module__ == "typing":
        # Type aliases (``PathSpecType``, ``Annotated`` CLI option types) are typing objects.
        return {"kind": "type alias", "value": _alias(obj)}

    if (inspect.isroutine(obj) or isinstance(obj, type)) and not _is_own(obj):
        origin = (
            _qualified_name(obj)
            if isinstance(obj, type)
            else f"{_public_module(obj.__module__)}.{obj.__qualname__}"
        )
        return {"kind": "re-export", "origin": origin}

    if isinstance(obj, type):
        return _describe_type(obj)

    if inspect.isroutine(obj):
        return {"kind": "function", "signature": _signature(obj)}

    if inspect.ismodule(obj):
        return {"kind": "module"}

    return {"kind": "data", "type": _qualified_name(type(obj))}


def surface() -> dict[str, dict[str, Any]]:
    """Return ``{module: {exported name: description}}`` for every public findfmt module."""
    import findfmt  # noqa: PLC0415

    modules = [
        "findfmt",
        *sorted(
            info.name
            for info in pkgutil.walk_packages(findfmt.__path__, prefix="findfmt.")
            if not any(part.startswith("_") for part in info.name.split("."))
        ),
    ]
    result: dict[str, dict[str, Any]] = {}
    for name in modules:
        module = importlib.import_module(name)
        exported = getattr(module, "__all__", None)
        if exported is None:
            continue

        result[name] = {item: _describe(getattr(module, item)) for item in sorted(exported)}

    return result


def main(argv: list[str] | None = None) -> int:
    """Print the surface, or write it to the committed snapshot with ``--write``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help=f"write {SNAPSHOT.name}")
    args = parser.parse_args(argv)
    text = json.dumps(surface(), indent=1, sort_keys=True) + "\n"
    if args.write:
        SNAPSHOT.write_text(text, encoding="utf-8")
        sys.stdout.write(f"Wrote {SNAPSHOT}\n")
    else:
        sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
