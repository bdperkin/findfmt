"""Unit tests for MIT license parity, cargo-deny/cargo-about configs, and wheel attribution (#579)."""

from __future__ import annotations

import re
import shutil
import tomllib
import zipfile
from email.parser import HeaderParser
from pathlib import Path
from typing import Any

import pytest
from hatchling.builders.wheel import WheelBuilder
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version
from tools.dep_matrix import load_supported_pythons

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ALLOWED_LICENSES = [
    "MIT",
    "Apache-2.0",
    "Apache-2.0 WITH LLVM-exception",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Unicode-3.0",
    "Zlib",
]
CRATES_IO_SOURCE = "registry+https://github.com/rust-lang/crates.io-index"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _load_toml(rel_path: str) -> dict[str, Any]:
    path = ROOT / rel_path
    assert path.is_file(), f"Missing TOML file: {rel_path}"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _specifier_probes(req: Requirement) -> list[Version]:
    probes: list[Version] = [Version("99999999.0.0")]
    for spec in req.specifier:
        base_str = spec.version.removesuffix(".*")
        ver = Version(base_str)
        next_rel = (*ver.release[:-1], ver.release[-1] + 1)
        next_str = ".".join(str(part) for part in next_rel)
        probes.extend(
            (
                ver,
                Version(f"{base_str}.post0"),
                Version(f"{base_str}.1"),
                Version(next_str),
            ),
        )

    return probes


def _establishes_floor(spec_op: str, spec_ver: str, min_floor: Version) -> bool:
    if spec_op == "==" and spec_ver.endswith(".*"):
        return Version(spec_ver.removesuffix(".*")) >= min_floor

    if spec_op in {">=", "~=", "==", ">"}:
        return Version(spec_ver) >= min_floor

    return False


def _has_valid_trove_classifiers_floor(raw_specs: list[str], supported_pythons: tuple[str, ...]) -> bool:
    min_floor = Version("2025.5.8.13")
    for raw in raw_specs:
        req = Requirement(raw)
        if canonicalize_name(req.name) != "trove-classifiers":
            continue

        if req.marker is not None and not all(
            req.marker.evaluate({"python_version": py_ver}) for py_ver in supported_pythons
        ):
            continue

        has_floor = any(_establishes_floor(spec.operator, spec.version, min_floor) for spec in req.specifier)
        if has_floor and any(
            probe >= min_floor and probe in req.specifier for probe in _specifier_probes(req)
        ):
            return True

    return False


def test_mit_license_parity_across_python_and_rust_manifests() -> None:
    """Verify pyproject.toml, LICENSE, and findfmt_rs/Cargo.toml declare consistent MIT metadata (#579)."""
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("MIT License\n")
    assert "Copyright (c) 2026 Brandon Perkins" in license_text

    pyproject = _load_toml("pyproject.toml")
    project = pyproject["project"]
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE", "THIRD_PARTY_LICENSES.md"]
    assert all(not str(c).startswith("License ::") for c in project.get("classifiers", []))
    supported_pythons = load_supported_pythons(ROOT / "pyproject.toml")
    assert supported_pythons
    build_requires = [str(r) for r in pyproject["build-system"]["requires"]]
    uv_constraints = [str(r) for r in pyproject["tool"]["uv"]["constraint-dependencies"]]
    assert _has_valid_trove_classifiers_floor(build_requires, supported_pythons)
    assert _has_valid_trove_classifiers_floor(uv_constraints, supported_pythons)
    assert _has_valid_trove_classifiers_floor(["trove-classifiers>=2026.9.21.13"], supported_pythons)
    assert _has_valid_trove_classifiers_floor(
        ["trove-classifiers>=2025.5.8.13,!=2025.5.8.13"],
        supported_pythons,
    )
    assert _has_valid_trove_classifiers_floor(["trove-classifiers>2025.5.8.13"], supported_pythons)
    assert _has_valid_trove_classifiers_floor(["trove-classifiers==2025.5.8.13.*"], supported_pythons)
    assert not _has_valid_trove_classifiers_floor(["trove-classifiers==2025.5.8.*"], supported_pythons)
    assert not _has_valid_trove_classifiers_floor(["trove-classifiers>2025.5.8.12"], supported_pythons)
    assert not _has_valid_trove_classifiers_floor(
        ["trove-classifiers>=2025.5.8.13,<=2025.5.8.12"],
        supported_pythons,
    )
    assert not _has_valid_trove_classifiers_floor(["trove-classifiers>=2025.5.8.12"], supported_pythons)
    assert not _has_valid_trove_classifiers_floor(
        ["trove-classifiers>=2025.5.8.13; python_version<'3.11'"],
        supported_pythons,
    )

    cargo_path = ROOT / "findfmt_rs" / "Cargo.toml"
    cargo_raw = cargo_path.read_text(encoding="utf-8")
    assert "../LICENSE" in cargo_raw
    cargo_pkg = _load_toml("findfmt_rs/Cargo.toml")["package"]
    assert cargo_pkg["name"] == "findfmt_rs"
    assert cargo_pkg["license"] == "MIT"
    assert tuple(int(p) for p in str(cargo_pkg["rust-version"]).split(".")) >= (1, 85)
    assert "license-file" not in cargo_pkg, "Avoid setting both license and license-file in Cargo.toml"
    assert cargo_pkg["publish"] is False
    assert (ROOT / "findfmt_rs" / cargo_pkg["readme"]).resolve() == (ROOT / "README.md").resolve()


def test_cargo_deny_and_cargo_about_permissive_policy_parity() -> None:
    """Verify findfmt_rs/deny.toml and about.toml enforce OSI-permissive licenses and crates.io sources."""
    deny = _load_toml("findfmt_rs/deny.toml")
    about = _load_toml("findfmt_rs/about.toml")

    assert deny["graph"]["all-features"] is True
    assert deny["advisories"]["version"] == 2
    assert deny["advisories"]["yanked"] == "deny"

    licenses = deny["licenses"]
    assert licenses["version"] == 2
    assert licenses["allow"] == EXPECTED_ALLOWED_LICENSES
    assert licenses["private"]["ignore"] is False
    assert about["accepted"] == EXPECTED_ALLOWED_LICENSES
    assert about["ignore-build-dependencies"] is False
    assert about["ignore-transitive-dependencies"] is False
    assert about["findfmt_rs"]["clarify"]["license"] == "MIT"
    assert about["findfmt_rs"]["clarify"]["files"][0]["path"] == "../LICENSE"

    bans = deny["bans"]
    assert bans["multiple-versions"] == "deny"
    assert bans["wildcards"] == "deny"

    sources = deny["sources"]
    assert sources["unknown-registry"] == "deny"
    assert sources["unknown-git"] == "deny"
    assert sources["allow-registry"] == ["https://github.com/rust-lang/crates.io-index"]
    assert sources["allow-git"] == []


def test_cargo_lock_and_third_party_licenses_completeness() -> None:
    """Verify every external crate in findfmt_rs/Cargo.lock comes from crates.io and is attributed."""
    lock = _load_toml("findfmt_rs/Cargo.lock")
    packages = lock.get("package", [])
    assert isinstance(packages, list)
    assert packages

    names = [str(pkg["name"]) for pkg in packages]
    assert len(names) == len(set(names)), "Duplicate crate versions detected in findfmt_rs/Cargo.lock"

    third_party_text = (ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")
    assert "<year>" not in third_party_text
    assert "<copyright holders>" not in third_party_text
    assert "Copyright (c) 2026 Brandon Perkins" in third_party_text
    external_crates = [pkg for pkg in packages if pkg["name"] != "findfmt_rs"]
    assert external_crates, "Expected transitive PyO3 crates in findfmt_rs/Cargo.lock"

    for pkg in external_crates:
        name = str(pkg["name"])
        version = str(pkg["version"])
        assert pkg.get("source") == CRATES_IO_SOURCE, f"{name} uses non-crates.io source"
        assert SHA256_RE.fullmatch(str(pkg.get("checksum", ""))), f"{name} missing valid SHA-256 checksum"
        assert f"[`{name}` `{version}`]" in third_party_text, (
            f"THIRD_PARTY_LICENSES.md is missing attribution for {name} {version}; "
            "re-run cargo-about generate"
        )


def test_wheel_metadata_bundles_project_and_third_party_licenses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify built wheels emit PEP 639 License-Expression/License-File headers and bundle both files."""
    monkeypatch.setenv("HATCH_MATURIN_DISABLE", "1")
    proj_dir = tmp_path / "pkg"
    (proj_dir / "src" / "findfmt").mkdir(parents=True)
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_text = pyproject_text.replace('dynamic = [ "version" ]', 'version = "0.0.0"')
    (proj_dir / "pyproject.toml").write_text(pyproject_text, encoding="utf-8")
    shutil.copy(ROOT / "README.md", proj_dir / "README.md")
    shutil.copy(ROOT / "LICENSE", proj_dir / "LICENSE")
    shutil.copy(ROOT / "THIRD_PARTY_LICENSES.md", proj_dir / "THIRD_PARTY_LICENSES.md")
    shutil.copytree(ROOT / "tools", proj_dir / "tools")
    (proj_dir / "src" / "findfmt" / "__init__.py").write_text('"""Stub."""\n', encoding="utf-8")
    (proj_dir / "src" / "findfmt" / "py.typed").write_text("", encoding="utf-8")

    out_dir = tmp_path / "dist"
    built = next(WheelBuilder(str(proj_dir)).build(directory=str(out_dir), versions=["standard"]))
    wheel_path = Path(built)

    with zipfile.ZipFile(wheel_path) as zf:
        names = set(zf.namelist())
        metadata_entry = next(n for n in names if n.endswith(".dist-info/METADATA"))
        headers = HeaderParser().parsestr(zf.read(metadata_entry).decode("utf-8"))
        assert headers.get("License-Expression") == "MIT"
        assert sorted(headers.get_all("License-File") or []) == ["LICENSE", "THIRD_PARTY_LICENSES.md"]

        dist_info_prefix = metadata_entry.removesuffix("METADATA")
        bundled_mit = zf.read(f"{dist_info_prefix}licenses/LICENSE")
        bundled_third_party = zf.read(f"{dist_info_prefix}licenses/THIRD_PARTY_LICENSES.md")
        assert bundled_mit == (ROOT / "LICENSE").read_bytes()
        assert bundled_third_party == (ROOT / "THIRD_PARTY_LICENSES.md").read_bytes()


def test_security_and_contributing_docs_cover_rust_license_auditing() -> None:
    """Verify SECURITY.md and CONTRIBUTING.md document cargo-deny and cargo-about auditing (#579)."""
    security_md = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    contributing_md = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for doc_name, content in (("SECURITY.md", security_md), ("CONTRIBUTING.md", contributing_md)):
        assert "findfmt_rs/deny.toml" in content, f"{doc_name} must reference findfmt_rs/deny.toml"
        assert "cargo deny" in content, f"{doc_name} must document cargo deny command"
        assert "THIRD_PARTY_LICENSES.md" in content, f"{doc_name} must reference THIRD_PARTY_LICENSES.md"
