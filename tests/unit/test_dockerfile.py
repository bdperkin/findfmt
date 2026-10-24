"""Container image build: locked dependencies, the release wheel, and no build tooling (#328)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _stages() -> dict[str, str]:
    """Return ``{stage name: instructions}`` for the Dockerfile's named stages."""
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    parts = re.split(r"^FROM \S+ AS (\w+)$", text, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def _containerize_steps() -> list[dict[str, Any]]:
    with (ROOT / ".github" / "workflows" / "release.yml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)["jobs"]["containerize"]["steps"]


def test_dockerfile_uses_locked_install() -> None:
    """Dependencies come from uv.lock, and findfmt from the built wheel without re-resolving."""
    builder = _stages()["builder"]
    assert "COPY pyproject.toml uv.lock ./" in builder
    assert "uv sync --locked --no-dev --no-install-project" in builder
    assert "uv pip install --python /opt/findfmt --no-deps" in builder
    assert "/tmp/dist/findfmt-*.whl" in builder
    assert not re.search(r"uv pip install[^\n]*\s\.(\s|$)", builder), "must not build from source"


def test_dockerfile_runtime_stage_excludes_uv() -> None:
    """The runtime stage copies only the virtual environment, not /usr/local with uv in it."""
    runtime = _stages()["runtime"]
    copies = re.findall(r"^COPY .*$", runtime, flags=re.MULTILINE)
    assert copies == ["COPY --from=builder /opt/findfmt /opt/findfmt"]
    assert 'ENV PATH="/opt/findfmt/bin:${PATH}"' in runtime
    assert "USER appuser" in runtime


def test_dockerignore_sends_only_wheels_from_dist() -> None:
    """The build context includes dist/*.whl (the image's source) but nothing else from dist/."""
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert "dist" not in lines
    assert lines.index("dist/*") < lines.index("!dist/*.whl")


def test_release_container_installs_and_verifies_the_release_wheel() -> None:
    """The release image is built from the dist artifact and verified before it is pushed."""
    steps = _containerize_steps()
    names = [step.get("name") for step in steps]
    download = steps[names.index("Download Distribution Artifacts")]
    assert download["with"] == {"name": "dist", "path": "dist"}
    verify = steps[names.index("Verify Image Version and Contents")]["run"]
    assert 'expected="findfmt ${RELEASE_TAG#v}"' in verify
    assert "command -v uv" in verify
    assert (
        names.index("Download Distribution Artifacts")
        < names.index("Build Image for Verification")
        < names.index("Verify Image Version and Contents")
        < names.index("Build and Push Docker Image")
    )


def test_release_container_publishes_sbom_and_provenance() -> None:
    """The pushed image carries an SBOM and provenance, and a signed attestation of its digest."""
    steps = _containerize_steps()
    push = next(step for step in steps if step.get("name") == "Build and Push Docker Image")
    assert push["with"]["provenance"] == "mode=max"
    assert push["with"]["sbom"] is True
    attest = next(s for s in steps if "actions/attest-build-provenance" in str(s.get("uses")))
    assert attest["with"]["subject-digest"] == "${{ steps.push.outputs.digest }}"
    assert attest["with"]["push-to-registry"] is True
