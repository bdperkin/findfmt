"""Unit tests for the hybrid Python-Rust runtime gateway in findfmt.core and _fallback (#578)."""

from __future__ import annotations

import types
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

import findfmt
from findfmt import _fallback, classifier, core
from findfmt.cli import app
from findfmt.models import FileInfo, TraversalConfig
from findfmt.traversal import engine as traversal_engine

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class _FakeRustExt(types.ModuleType):
    """Typed synthetic findfmt._rust_ext module for unit testing."""

    classify_file: Callable[..., FileInfo]
    find_files: Callable[..., Iterator[FileInfo]]


def _make_rust_panic_cls() -> type[BaseException]:
    """Create a synthetic PyO3 PanicException subclassing BaseException in pyo3_runtime."""
    return type("PanicException", (BaseException,), {"__module__": "pyo3_runtime"})


def test_fallback_module_reexports_pure_python_engines() -> None:
    """Verify findfmt._fallback exposes pure-Python classify_file and find_files (#578)."""
    assert _fallback.classify_file is classifier.classify_file
    assert _fallback.find_files is traversal_engine.find_files
    assert set(_fallback.__all__) == {"classify_file", "find_files"}


def test_extensions_disabled_env_parsing_and_import_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify FINDFMT_NO_EXTENSIONS parsing and _import_rust_ext load/fallback paths (#578)."""
    for truthy in ("1", "true", "TRUE", " yes ", "On"):
        monkeypatch.setenv("FINDFMT_NO_EXTENSIONS", truthy)
        assert core._are_extensions_disabled() is True  # noqa: SLF001 - white-box unit test

    for falsy in ("0", "false", "no", "off", ""):
        monkeypatch.setenv("FINDFMT_NO_EXTENSIONS", falsy)
        assert core._are_extensions_disabled() is False  # noqa: SLF001 - white-box unit test

    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    assert core._are_extensions_disabled() is False  # noqa: SLF001 - white-box unit test

    import_calls: list[str] = []
    fake_ext = types.ModuleType("findfmt._rust_ext")

    def _fake_import(name: str) -> types.ModuleType:
        import_calls.append(name)
        return fake_ext

    monkeypatch.setattr(core.importlib, "import_module", _fake_import)
    monkeypatch.setenv("FINDFMT_NO_EXTENSIONS", "1")
    assert core._import_rust_ext() is None  # noqa: SLF001 - white-box unit test
    assert import_calls == []

    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    assert core._import_rust_ext() is fake_ext  # noqa: SLF001 - white-box unit test
    assert import_calls == ["findfmt._rust_ext"]

    def _failing_import(name: str) -> types.ModuleType:
        msg = f"No module named {name!r}"
        raise ModuleNotFoundError(msg, name=name)

    monkeypatch.setattr(core.importlib, "import_module", _failing_import)
    assert core._import_rust_ext() is None  # noqa: SLF001 - white-box unit test


def test_backend_inspection_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify extension-loaded vs active execution-backend helpers across all states (#578)."""
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)

    # Metadata-only extension loaded -> extension is loaded, execution backend remains python
    bare_ext = types.ModuleType("findfmt._rust_ext")
    monkeypatch.setattr(core, "_RUST_EXT", bare_ext)
    assert findfmt.is_rust_extension_loaded() is True
    assert findfmt.is_rust_backend_active() is False
    assert findfmt.get_active_backend() == "python"

    # Extension exposing classify_file -> active rust backend
    classify_only_ext = _FakeRustExt("findfmt._rust_ext")
    classify_only_ext.classify_file = lambda *_args, **_kwargs: FileInfo(
        path=Path("a.py"),
        relative_path=Path("a.py"),
    )
    monkeypatch.setattr(core, "_RUST_EXT", classify_only_ext)
    assert findfmt.is_rust_extension_loaded() is True
    assert findfmt.is_rust_backend_active() is True
    assert findfmt.get_active_backend() == "rust"

    # Extension exposing find_files -> active rust backend
    find_only_ext = _FakeRustExt("findfmt._rust_ext")
    find_only_ext.find_files = lambda *_args, **_kwargs: iter(())
    monkeypatch.setattr(core, "_RUST_EXT", find_only_ext)
    assert findfmt.is_rust_extension_loaded() is True
    assert findfmt.is_rust_backend_active() is True
    assert findfmt.get_active_backend() == "rust"

    # Disabled via FINDFMT_NO_EXTENSIONS=1 -> neither loaded nor active
    monkeypatch.setenv("FINDFMT_NO_EXTENSIONS", "1")
    assert findfmt.is_rust_extension_loaded() is False
    assert findfmt.is_rust_backend_active() is False
    assert findfmt.get_active_backend() == "python"

    # Missing extension -> neither loaded nor active
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)
    monkeypatch.setattr(core, "_RUST_EXT", None)
    assert findfmt.is_rust_extension_loaded() is False
    assert findfmt.is_rust_backend_active() is False
    assert findfmt.get_active_backend() == "python"


def test_classify_file_dispatch_and_panic_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify classify_file dispatches to _rust_ext and falls back on missing symbol or PanicException."""
    target = tmp_path / "example.py"
    target.write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)

    # 1. Extension present without classify_file symbol -> pure-Python fallback
    bare_ext = types.ModuleType("findfmt._rust_ext")
    monkeypatch.setattr(core, "_RUST_EXT", bare_ext)
    baseline = core.classify_file(target)
    assert "python" in baseline.tags

    # 2. Extension present with working classify_file -> native result returned
    sentinel = FileInfo(path=target, relative_path=Path(target.name), tags=frozenset({"rust-native"}))
    native_ext = _FakeRustExt("findfmt._rust_ext")
    native_ext.classify_file = lambda *_args, **_kwargs: sentinel
    monkeypatch.setattr(core, "_RUST_EXT", native_ext)
    assert core.classify_file(target) is sentinel

    # 3. FINDFMT_NO_EXTENSIONS=1 bypasses loaded native_ext and uses pure-Python fallback
    monkeypatch.setenv("FINDFMT_NO_EXTENSIONS", "1")
    disabled_res = core.classify_file(target)
    assert disabled_res == baseline
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)

    # 4. Simulated pyo3_runtime.PanicException -> caught and routed to pure-Python fallback
    panic_cls = _make_rust_panic_cls()

    def _panicking_classify(*_args: object, **_kwargs: object) -> FileInfo:
        msg = "simulated Rust panic in classify_file"
        raise panic_cls(msg)

    native_ext.classify_file = _panicking_classify
    recovered = core.classify_file(target)
    assert recovered == baseline

    # 5. Non-panic exceptions and non-pyo3 PanicException classes propagate normally
    non_pyo3_panic = type("PanicException", (Exception,), {"__module__": "custom_mod"})

    def _foreign_panic(*_args: object, **_kwargs: object) -> FileInfo:
        raise non_pyo3_panic

    native_ext.classify_file = _foreign_panic
    with pytest.raises(non_pyo3_panic):
        core.classify_file(target)


def test_find_files_dispatch_and_panic_fallback(
    sample_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify find_files dispatches to _rust_ext and recovers cleanly including overlapping roots."""
    overlap_cfg = TraversalConfig(root_paths=(sample_repo, sample_repo / "src"))
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)

    # 1. Missing extension -> pure-Python fallback with overlapping roots
    monkeypatch.setattr(core, "_RUST_EXT", None)
    expected = list(core.find_files(overlap_cfg))
    app_occurrences = [f for f in expected if f.path.name == "app.py"]
    assert len(app_occurrences) == 2
    assert {f.relative_path for f in app_occurrences} == {Path("src/app.py"), Path("app.py")}

    # 2. Native find_files succeeds -> yields native items without invoking fallback
    native_ext = _FakeRustExt("findfmt._rust_ext")
    native_item = app_occurrences[0]
    native_ext.find_files = lambda *_args, **_kwargs: iter([native_item])
    monkeypatch.setattr(core, "_RUST_EXT", native_ext)
    assert list(core.find_files(overlap_cfg)) == [native_item]

    # 3. Mid-stream pyo3_runtime.PanicException after yielding through first overlapping-root item
    #    skips only already-delivered (path, relative_path) entries and preserves the second root's entry
    panic_cls = _make_rust_panic_cls()
    cutoff = expected.index(app_occurrences[0]) + 1

    def _midstream_panic_find(
        _cfg: TraversalConfig,
        *,
        on_error: Callable[[OSError], None] | None = None,
    ) -> Iterator[FileInfo]:
        _ = on_error
        yield from expected[:cutoff]
        msg = "simulated Rust panic mid-traversal"
        raise panic_cls(msg)

    native_ext.find_files = _midstream_panic_find
    recovered = list(core.find_files(overlap_cfg))
    assert [(f.path, f.relative_path) for f in recovered] == [(f.path, f.relative_path) for f in expected]

    # 4. Non-panic exception propagates normally
    def _broken_find(
        _cfg: TraversalConfig,
        *,
        on_error: Callable[[OSError], None] | None = None,
    ) -> Iterator[FileInfo]:
        _ = on_error
        msg = "ordinary runtime error"
        raise RuntimeError(msg)

    native_ext.find_files = _broken_find
    with pytest.raises(RuntimeError, match="ordinary runtime error"):
        list(core.find_files(overlap_cfg))


def test_cli_parity_across_backends_and_simulated_panic(
    sample_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify CLI output is identical across active, missing, disabled, and panicking _rust_ext (#578)."""
    runner = CliRunner()
    monkeypatch.delenv("FINDFMT_NO_EXTENSIONS", raising=False)

    # Missing extension baseline
    monkeypatch.setattr(core, "_RUST_EXT", None)
    res_missing = runner.invoke(app, [str(sample_repo)])
    assert res_missing.exit_code == 0

    # Active extension (delegating or disabled via FINDFMT_NO_EXTENSIONS=1)
    bare_ext = types.ModuleType("findfmt._rust_ext")
    monkeypatch.setattr(core, "_RUST_EXT", bare_ext)
    res_active = runner.invoke(app, [str(sample_repo)])
    assert res_active.exit_code == 0
    assert res_active.stdout == res_missing.stdout

    res_disabled = CliRunner(env={"FINDFMT_NO_EXTENSIONS": "1"}).invoke(app, [str(sample_repo)])
    assert res_disabled.exit_code == 0
    assert res_disabled.stdout == res_missing.stdout

    res_diag_disabled = CliRunner(env={"FINDFMT_NO_EXTENSIONS": "1"}).invoke(app, ["--diagnostics"])
    assert res_diag_disabled.exit_code == 0
    assert "Backend: python" in res_diag_disabled.stdout

    # Panicking native extension routed seamlessly to pure-Python fallback without CLI crash
    panic_cls = _make_rust_panic_cls()
    panicking_ext = _FakeRustExt("findfmt._rust_ext")

    def _panic_find(*_args: object, **_kwargs: object) -> Iterator[FileInfo]:
        msg = "simulated CLI Rust panic"
        raise panic_cls(msg)

    panicking_ext.find_files = _panic_find
    monkeypatch.setattr(core, "_RUST_EXT", panicking_ext)
    res_diag_rust = runner.invoke(app, ["--diagnostics"])
    assert res_diag_rust.exit_code == 0
    assert "Backend: rust" in res_diag_rust.stdout

    res_panic = runner.invoke(app, [str(sample_repo)])
    assert res_panic.exit_code == 0
    assert res_panic.stdout == res_missing.stdout
