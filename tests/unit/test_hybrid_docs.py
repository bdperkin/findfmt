"""Unit tests verifying hybrid Python-Rust developer setup and architecture FAQ documentation (#580)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_contributing_and_agents_document_hybrid_rust_workflows() -> None:
    """Verify CONTRIBUTING.md and AGENTS.md document rustup, maturin, and fallback debugging (#580)."""
    for filename in ("CONTRIBUTING.md", "AGENTS.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        for required_term in (
            "rustup",
            "rustfmt",
            "clippy",
            "maturin develop",
            "findfmt_rs/Cargo.toml",
            "HATCH_MATURIN_DISABLE=1",
            "FINDFMT_NO_EXTENSIONS=1",
            "RUST_BACKTRACE=1",
        ):
            assert required_term in text, f"Missing {required_term!r} in {filename}"

    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for module_ref in (
        "src/findfmt/core.py",
        "src/findfmt/_fallback.py",
        "src/findfmt/_rust_ext.pyi",
    ):
        assert module_ref in agents_text, f"Missing {module_ref!r} in AGENTS.md"


def test_readme_and_sphinx_hybrid_architecture_faq() -> None:
    """Verify README.md and Sphinx docs include the Hybrid Python-Rust Architecture & Fallback FAQ (#580)."""
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## 5. Hybrid Python-Rust Architecture & Fallback FAQ" in readme_text
    for required_term in (
        "findfmt._rust_ext",
        "src/findfmt/core.py",
        "src/findfmt/_fallback.py",
        "FINDFMT_NO_EXTENSIONS=1",
        "HATCH_MATURIN_DISABLE=1",
        "PanicException",
    ):
        assert required_term in readme_text, f"Missing {required_term!r} in README.md"

    faq_page = ROOT / "docs" / "source" / "quality" / "hybrid_architecture.md"
    assert faq_page.is_file(), "Missing docs/source/quality/hybrid_architecture.md"
    faq_text = faq_page.read_text(encoding="utf-8")
    for required_term in (
        "# Hybrid Python-Rust Architecture & Fallback FAQ",
        "abi3-py311",
        "is_rust_extension_loaded()",
        "is_rust_backend_active()",
        "get_active_backend()",
        "pyo3_runtime.PanicException",
        "maturin develop",
        "find_files_rs",
        "classify_file_rs",
        "tests/test_parity.py",
        "--backend compare",
    ):
        assert required_term in faq_text, f"Missing {required_term!r} in {faq_page}"

    perf_text = (ROOT / "docs" / "performance.md").read_text(encoding="utf-8")
    assert "--backend compare" in perf_text
    assert "findfmt._rust_ext" in perf_text

    quality_index = (ROOT / "docs" / "source" / "quality" / "index.md").read_text(encoding="utf-8")
    assert "hybrid_architecture" in quality_index
