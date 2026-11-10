"""Tests for tools/verify_release_version.py, the release tag and artifact version guard (#327)."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest
from tools.verify_release_version import (
    check,
    main,
    sync_fallback_versions,
    version_from_tag,
)


def _wheel(dist: Path, filename_version: str, metadata_version: str) -> Path:
    """Write a minimal wheel whose METADATA declares ``metadata_version``."""
    path = dist / f"findfmt-{filename_version}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            f"findfmt-{filename_version}.dist-info/METADATA",
            f"Metadata-Version: 2.4\nName: findfmt\nVersion: {metadata_version}\n\nBody\n",
        )

    return path


def _sdist(dist: Path, filename_version: str, metadata_version: str) -> Path:
    """Write a minimal sdist whose PKG-INFO declares ``metadata_version``."""
    path = dist / f"findfmt-{filename_version}.tar.gz"
    data = f"Metadata-Version: 2.4\nName: findfmt\nVersion: {metadata_version}\n".encode()
    with tarfile.open(path, "w:gz") as tf:
        info = tarfile.TarInfo(f"findfmt-{filename_version}/PKG-INFO")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))

    return path


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    """Return an empty dist/ directory."""
    path = tmp_path / "dist"
    path.mkdir()
    return path


@pytest.mark.parametrize(("tag", "version"), [("v1.1.0", "1.1.0"), ("v10.20.30", "10.20.30")])
def test_version_from_tag_accepts_release_tags(tag: str, version: str) -> None:
    """Release tags are vMAJOR.MINOR.PATCH."""
    assert version_from_tag(tag) == version


@pytest.mark.parametrize(
    "tag",
    ["1.1.0", "v1.1", "v1.1.0.dev3", "v1.1.0rc1", "main", "", "v1.1.0\n"],
)
def test_version_from_tag_rejects_other_refs(tag: str) -> None:
    """Branches, pre-releases, and malformed tags are refused."""
    with pytest.raises(ValueError, match=r"vMAJOR\.MINOR\.PATCH"):
        version_from_tag(tag)


def test_check_passes_when_artifacts_match_tag(dist: Path) -> None:
    """A wheel and sdist built from the tag pass."""
    _wheel(dist, "1.1.0", "1.1.0")
    _sdist(dist, "1.1.0", "1.1.0")
    assert check("v1.1.0", dist) == []


def test_check_rejects_dev_build_from_branch(dist: Path) -> None:
    """The #327 failure: a dispatch built main HEAD, so hatch-vcs produced a .devN version."""
    _wheel(dist, "1.1.1.dev3", "1.1.1.dev3")
    _sdist(dist, "1.1.1.dev3", "1.1.1.dev3")
    errors = check("v1.1.0", dist)
    assert len(errors) == 2
    assert all("1.1.1.dev3" in e and "1.1.0" in e for e in errors)


def test_check_reads_metadata_not_just_filenames(dist: Path) -> None:
    """A wheel whose METADATA disagrees with the tag fails even if its filename matches."""
    _wheel(dist, "1.1.0", "1.1.0.dev1")
    _sdist(dist, "1.1.0", "1.1.0")
    errors = check("v1.1.0", dist)
    assert len(errors) == 1
    assert ".whl" in errors[0]


@pytest.mark.parametrize("present", ["wheel", "sdist", "none"])
def test_check_requires_one_wheel_and_one_sdist(dist: Path, present: str) -> None:
    """Both artifact types must be present, so a partial build cannot be published."""
    if present == "wheel":
        _wheel(dist, "1.1.0", "1.1.0")

    if present == "sdist":
        _sdist(dist, "1.1.0", "1.1.0")

    errors = check("v1.1.0", dist)
    assert errors
    assert any("expected exactly one" in e for e in errors)


def test_check_reports_unreadable_metadata(dist: Path) -> None:
    """An artifact without a Version header is reported, not silently accepted."""
    path = dist / "findfmt-1.1.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("findfmt-1.1.0.dist-info/METADATA", "Name: findfmt\n")

    _sdist(dist, "1.1.0", "1.1.0")
    errors = check("v1.1.0", dist)
    assert len(errors) == 1
    assert "no Version" in errors[0]


def test_check_tag_only() -> None:
    """Without --dist, only the tag format is checked."""
    assert check("v1.1.0") == []
    assert check("main") != []


def test_main_exit_codes(dist: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI exits 0 on success and 1 on any error, explaining why."""
    _wheel(dist, "1.1.0", "1.1.0")
    _sdist(dist, "1.1.0", "1.1.0")
    assert main(["--tag", "v1.1.0", "--dist", str(dist)]) == 0
    assert "1.1.0" in capsys.readouterr().out
    assert main(["--tag", "v1.2.0", "--dist", str(dist)]) == 1
    assert "1.2.0" in capsys.readouterr().err
    assert main(["--tag", "main"]) == 1
    assert "vMAJOR.MINOR.PATCH" in capsys.readouterr().err


def _mock_repo(tmp_path: Path, pyproject_ver: str | None, init_ver: str | None) -> Path:
    """Create a minimal repository layout with pyproject.toml and src/findfmt/__init__.py."""
    repo = tmp_path / "repo"
    init_dir = repo / "src" / "findfmt"
    init_dir.mkdir(parents=True)
    pyproject_text = (
        f'[tool.hatch]\nversion.fallback-version = "{pyproject_ver}"\n'
        if pyproject_ver is not None
        else "[tool.hatch]\n"
    )
    init_text = (
        f'_FALLBACK_VERSION: str = "{init_ver}"\n' if init_ver is not None else "__all__ = []\n"
    )
    (repo / "pyproject.toml").write_text(pyproject_text, encoding="utf-8")
    (init_dir / "__init__.py").write_text(init_text, encoding="utf-8")
    return repo


def test_check_repo_fallbacks_detects_skew_and_missing(tmp_path: Path) -> None:
    """Verify repo fallback checks pass when aligned and report skew or missing declarations."""
    repo_ok = _mock_repo(tmp_path / "ok", "1.2.0.dev0", "1.2.0.dev0")
    assert check("v1.2.0", repo=repo_ok) == []

    repo_skew = _mock_repo(tmp_path / "skew", "1.2.0.dev0", "1.1.3.dev0")
    skew_errors = check("v1.2.0", repo=repo_skew)
    assert len(skew_errors) == 1
    assert (
        "src/findfmt/__init__.py: fallback version 1.1.3.dev0 != expected 1.2.0.dev0"
        in (skew_errors[0])
    )

    repo_missing = _mock_repo(tmp_path / "missing", None, None)
    missing_errors = check("v1.2.0", repo=repo_missing)
    assert len(missing_errors) == 2
    assert all("missing fallback version declaration" in e for e in missing_errors)


def test_sync_fallback_versions_and_cli_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify --write updates fallback versions in pyproject.toml and src/findfmt/__init__.py."""
    repo = _mock_repo(tmp_path, "1.1.5.dev0", "1.1.3.dev0")
    assert main(["--tag", "v1.2.0", "--repo", str(repo), "--write"]) == 0
    assert "OK: tag match version 1.2.0" in capsys.readouterr().out
    assert check("v1.2.0", repo=repo) == []
    assert 'version.fallback-version = "1.2.0.dev0"' in (repo / "pyproject.toml").read_text(
        encoding="utf-8",
    )
    assert '_FALLBACK_VERSION: str = "1.2.0.dev0"' in (
        repo / "src" / "findfmt" / "__init__.py"
    ).read_text(encoding="utf-8")

    sync_fallback_versions("v1.3.0", repo)
    assert check("v1.3.0", repo=repo) == []

    assert main(["--tag", "invalid-tag", "--repo", str(repo), "--write"]) == 1
    assert "vMAJOR.MINOR.PATCH" in capsys.readouterr().err
