"""Unit tests for findfmt_rs PyO3 crate, hatch-maturin-build config, and _rust_ext.pyi (#577)."""

from __future__ import annotations

import ast
import importlib
import shutil
import tomllib
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hatchling.builders.wheel import WheelBuilder
from tools import hatch_build

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_toml(rel_path: str) -> dict[str, Any]:
    path = ROOT / rel_path
    assert path.is_file(), f"Missing TOML file: {rel_path}"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_pyproject_and_cargo_maturin_configuration() -> None:
    """Verify pyproject.toml and Cargo.toml configure hatch-maturin-build and pyo3 abi3-py311 (#577)."""
    pyproject = _load_toml("pyproject.toml")
    build_sys = pyproject["build-system"]
    assert build_sys["build-backend"] == "hatchling.build"
    requires = [str(r) for r in build_sys["requires"]]
    assert any(r.startswith("hatchling>=") for r in requires)
    assert any(r.startswith("hatch-maturin-build>=") for r in requires)
    assert any(r.startswith("maturin>=") for r in requires)

    maturin_hook = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["hooks"]["maturin"]
    assert maturin_hook["manifest-path"] == "findfmt_rs/Cargo.toml"
    assert maturin_hook["locked"] is True

    maturin_cfg = pyproject["tool"]["maturin"]
    assert maturin_cfg["module-name"] == "findfmt._rust_ext"
    assert maturin_cfg["python-source"] == "src"
    assert "**/*.po" in maturin_cfg["exclude"]
    assert "**/*.pot" in maturin_cfg["exclude"]

    cargo = _load_toml("findfmt_rs/Cargo.toml")
    assert cargo["lib"]["name"] == "_rust_ext"
    assert cargo["lib"]["crate-type"] == ["cdylib", "rlib"]
    assert cargo["features"]["default"] == ["extension-module"]
    assert cargo["features"]["extension-module"] == ["pyo3/extension-module"]
    pyo3_dep = cargo["dependencies"]["pyo3"]
    assert "abi3-py311" in pyo3_dep["features"]


def test_maturin_disable_guard_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify HATCH_MATURIN_DISABLE truthy parsing, guard wrapping, and idempotency (#577)."""
    for truthy in ("1", "true", "TRUE", " yes ", "On"):
        monkeypatch.setenv("HATCH_MATURIN_DISABLE", truthy)
        assert hatch_build.is_maturin_disabled() is True

    for falsy in ("0", "false", "no", ""):
        monkeypatch.setenv("HATCH_MATURIN_DISABLE", falsy)
        assert hatch_build.is_maturin_disabled() is False

    monkeypatch.delenv("HATCH_MATURIN_DISABLE", raising=False)
    assert hatch_build.is_maturin_disabled() is False

    monkeypatch.setattr(hatch_build, "_maturin_hook_mod", None)
    assert hatch_build.install_maturin_disable_guard() is False

    calls: list[tuple[str, dict[str, Any]]] = []
    clean_calls: list[list[str]] = []

    class DummyMaturinHook:
        def initialize(self, version: str, build_data: dict[str, Any]) -> None:
            calls.append((version, build_data))

        def clean(self, versions: list[str]) -> None:
            clean_calls.append(versions)

    assert hatch_build.install_maturin_disable_guard(DummyMaturinHook) is True
    assert hatch_build.install_maturin_disable_guard(DummyMaturinHook) is True

    hook = DummyMaturinHook()
    monkeypatch.setenv("HATCH_MATURIN_DISABLE", "1")
    hook.clean(["standard"])
    hook.initialize("standard", {"pure_python": True})
    assert clean_calls == []
    assert calls == []

    monkeypatch.setenv("HATCH_MATURIN_DISABLE", "0")
    payload: dict[str, Any] = {"pure_python": True}
    hook.clean(["standard"])
    hook.initialize("standard", payload)
    assert clean_calls == [["standard"]]
    assert calls == [("standard", payload)]


def test_rust_ext_stub_and_compiled_module_parity() -> None:
    """Verify src/findfmt/_rust_ext.pyi signatures and compiled _rust_ext behavior when built (#577)."""
    stub_path = ROOT / "src" / "findfmt" / "_rust_ext.pyi"
    assert stub_path.is_file(), "Missing src/findfmt/_rust_ext.pyi type stub"
    tree = ast.parse(stub_path.read_text(encoding="utf-8"))
    stub_funcs = {
        node.name: ast.unparse(node.returns) if node.returns is not None else ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    assert stub_funcs == {
        "backend_name": "str",
        "rust_ext_version": "str",
        "classify_file_rs": "FileInfo",
        "classify_file": "FileInfo",
        "classify_batch_rs": "list[FileInfo]",
    }

    cargo_version = str(_load_toml("findfmt_rs/Cargo.toml")["package"]["version"])
    try:
        rust_ext = importlib.import_module("findfmt._rust_ext")
    except ModuleNotFoundError as exc:
        if exc.name == "findfmt._rust_ext":
            return

        raise

    assert rust_ext.backend_name() == "rust"
    assert rust_ext.rust_ext_version() == cargo_version
    assert callable(rust_ext.classify_file_rs)
    assert callable(rust_ext.classify_file)
    assert callable(rust_ext.classify_batch_rs)


def test_hatch_maturin_disable_builds_pure_python_wheel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify HATCH_MATURIN_DISABLE=1 produces a pure-Python py3-none-any wheel without extensions (#577)."""
    monkeypatch.setenv("HATCH_MATURIN_DISABLE", "1")
    proj_dir = tmp_path / "pkg"
    (proj_dir / "src" / "findfmt").mkdir(parents=True)
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_text = pyproject_text.replace('dynamic = [ "version" ]', 'version = "0.0.0"')
    (proj_dir / "pyproject.toml").write_text(pyproject_text, encoding="utf-8")
    for filename in ("README.md", "LICENSE", "THIRD_PARTY_LICENSES.md"):
        shutil.copy(ROOT / filename, proj_dir / filename)

    shutil.copytree(ROOT / "tools", proj_dir / "tools")
    (proj_dir / "src" / "findfmt" / "__init__.py").write_text('"""Stub."""\n', encoding="utf-8")
    shutil.copy(ROOT / "src" / "findfmt" / "py.typed", proj_dir / "src" / "findfmt" / "py.typed")
    shutil.copy(ROOT / "src" / "findfmt" / "_rust_ext.pyi", proj_dir / "src" / "findfmt" / "_rust_ext.pyi")

    out_dir = tmp_path / "dist"
    wheel_path = Path(next(WheelBuilder(str(proj_dir)).build(directory=str(out_dir), versions=["standard"])))
    assert wheel_path.name.endswith("-py3-none-any.whl")

    with zipfile.ZipFile(wheel_path) as zf:
        names = set(zf.namelist())
        assert "findfmt/py.typed" in names
        assert "findfmt/_rust_ext.pyi" in names
        assert not any(n.endswith((".so", ".pyd", ".dylib", ".dll")) for n in names)
