"""Pin the public API surface and test the dump tool that produces it (#493)."""

from __future__ import annotations

import enum
import json
import types
import typing
from pathlib import Path
from typing import Any

import pytest
from tools import api_surface
from tools.api_surface import SNAPSHOT, _describe, main, surface

REGENERATE = "uv run python tools/api_surface.py --write"
_T = typing.TypeVar("_T")


def _summarize(expected: dict[str, Any], actual: dict[str, Any]) -> str:
    """Summarize added, removed, and changed exports between two surfaces."""
    lines: list[str] = []
    for module in sorted(set(expected) | set(actual)):
        before, after = expected.get(module, {}), actual.get(module, {})
        lines += [f"  + {module}.{n}" for n in sorted(set(after) - set(before))]
        lines += [f"  - {module}.{n}" for n in sorted(set(before) - set(after))]
        lines += [
            f"  ~ {module}.{n}" for n in sorted(set(before) & set(after)) if before[n] != after[n]
        ]

    return "\n".join(lines)


def test_public_api_matches_snapshot() -> None:
    """The public API equals the committed 1.1 snapshot; any change must be deliberate."""
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    actual = surface()
    assert actual == expected, (
        "The public API changed:\n"
        f"{_summarize(expected, actual)}\n"
        f"If this is intended, run `{REGENERATE}` and record the change in CHANGELOG.md."
    )


class _Color(enum.StrEnum):
    RED = "red"


class _FailureError(ValueError):
    pass


class _Own:
    """Class defined in this module (not findfmt) for kind detection."""

    def __init__(self, value: int = 1) -> None:
        self.value = value

    def method(self, *, flag: bool = False) -> bool:
        return flag


def test_describe_kinds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each kind of exported object is described with stable, address-free data."""
    monkeypatch.setattr(api_surface, "_is_own", lambda _obj: True)
    assert _describe(_Color) == {"kind": "enum", "bases": ["StrEnum"], "members": {"RED": "red"}}
    assert _describe(_FailureError) == {
        "kind": "exception",
        "bases": ["ValueError", "Exception", "BaseException"],
    }
    own = _describe(_Own)
    assert own["kind"] == "class"
    assert own["signature"] == "(value: 'int' = 1) -> 'None'"
    assert own["members"]["method"] == "(self, *, flag: 'bool' = False) -> 'bool'"
    assert _describe(_Own().method)["kind"] == "function"
    assert _describe(types) == {"kind": "module"}
    assert _describe(42) == {"kind": "data", "type": "int"}
    assert _describe(len) == {"kind": "function", "signature": "(obj, /)"}


def test_describe_type_aliases_and_reexports() -> None:
    """Type aliases are described without metadata reprs; foreign callables by origin only."""
    marker = object()  # its repr contains a memory address
    assert _describe(typing.Any) == {"kind": "type alias", "value": "typing.Any"}
    assert _describe(typing.Annotated[bool, marker]) == {
        "kind": "type alias",
        "value": "Annotated[bool, ...]",
    }
    assert _describe(Path) == {"kind": "re-export", "origin": "pathlib.Path"}


def test_describe_class_with_inherited_third_party_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A findfmt class inheriting a dependency's constructor records where it comes from."""

    class Child(Path):
        pass

    monkeypatch.setattr(api_surface, "_is_own", lambda obj: obj is Child)
    described = _describe(Child)
    assert described["signature"].startswith("inherited from pathlib.")


def test_describe_uninspectable_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Callables without an introspectable signature are recorded with an empty one."""
    monkeypatch.setattr(api_surface, "_is_own", lambda _obj: True)
    assert _describe(dict.fromkeys) == {
        "kind": "function",
        "signature": "(iterable, value=None, /)",
    }
    assert api_surface._signature(object()) == ""  # noqa: SLF001

    def broken() -> None:
        """Callable whose signature metadata cannot be read."""

    setattr(broken, "__signature__", 42)  # noqa: B010 - simulate unreadable metadata
    assert api_surface._signature(broken) == ""  # noqa: SLF001


def test_main_prints_and_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``main`` prints the surface, and ``--write`` writes the snapshot file."""
    monkeypatch.setattr(api_surface, "surface", lambda: {"findfmt": {"x": {"kind": "data"}}})
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out) == {"findfmt": {"x": {"kind": "data"}}}
    target = tmp_path / "api_surface.json"
    monkeypatch.setattr(api_surface, "SNAPSHOT", target)
    assert main(["--write"]) == 0
    assert json.loads(target.read_text(encoding="utf-8")) == {"findfmt": {"x": {"kind": "data"}}}
    assert str(target) in capsys.readouterr().out


def test_surface_skips_modules_without_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """Modules that do not declare ``__all__`` contribute no public names."""
    import findfmt  # noqa: PLC0415

    fake = types.ModuleType("findfmt.fake")
    infos = [
        types.SimpleNamespace(name="findfmt.fake"),
        types.SimpleNamespace(name="findfmt._private"),
    ]
    monkeypatch.setattr(api_surface.pkgutil, "walk_packages", lambda *_args, **_kwargs: infos)
    monkeypatch.setattr(
        api_surface.importlib,
        "import_module",
        lambda name: findfmt if name == "findfmt" else fake,
    )
    assert set(surface()) == {"findfmt"}


def test_stability_policy_is_in_the_api_docs() -> None:
    """The API stability policy is reachable from the API reference and names the snapshot."""
    api_docs = Path(__file__).resolve().parents[2] / "docs" / "source" / "api"
    toctree = (api_docs / "index.md").read_text(encoding="utf-8").split("```{toctree}", 1)[1]
    assert "stability" in toctree.split("```", 1)[0].split()
    policy = (api_docs / "stability.md").read_text(encoding="utf-8")
    assert REGENERATE.removeprefix("uv run ") in policy
    assert "tests/unit/api_surface.json" in policy


@pytest.mark.parametrize(
    ("module", "qualname", "expected"),
    [
        ("pathlib._local", "WindowsPath", "pathlib.Path"),  # Windows on Python 3.13
        ("pathlib", "PosixPath", "pathlib.Path"),  # Linux/macOS on 3.12 and 3.14+
        ("pathlib._local", "Path", "pathlib.Path"),  # Python 3.13 module layout
        ("rich.box", "Box", "rich.box.Box"),
        ("builtins", "str", "str"),
    ],
)
def test_type_names_are_platform_and_version_stable(
    module: str,
    qualname: str,
    expected: str,
) -> None:
    """Type names drop private modules and path flavours, so the snapshot matches everywhere."""
    cls = type(qualname, (), {"__module__": module, "__qualname__": qualname})
    assert api_surface._qualified_name(cls) == expected  # noqa: SLF001


def test_type_expressions_are_built_from_their_parts() -> None:
    """Unions, generics, and None render from canonical parts rather than version-specific reprs."""
    type_name = api_surface._type_name  # noqa: SLF001
    assert type_name(Path | None) == "pathlib.Path | None"
    assert type_name(typing.Optional[Path]) == "pathlib.Path | None"  # noqa: UP045
    assert type_name(list[Path]) == "list[pathlib.Path]"
    assert type_name(type(None)) == "None"
    assert type_name(_T) == "~_T"
    assert _describe(json.dumps) == {"kind": "re-export", "origin": "json.dumps"}
