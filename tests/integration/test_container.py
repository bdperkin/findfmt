"""Build the container image from a wheel and check what it runs (#328).

Slow, and needs a container engine and uv, so it runs only when ``FINDFMT_CONTAINER_TESTS=1`` is
set, as in CI's container smoke test. Once opted in, a missing engine is a failure, not a skip.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = shutil.which("docker") or shutil.which("podman")
UV = shutil.which("uv")

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("FINDFMT_CONTAINER_TESTS") != "1",
        reason="set FINDFMT_CONTAINER_TESTS=1 to build and run the container image",
    ),
]


def _run(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture(scope="module")
def image(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[str, str]]:
    """Build the image from a fresh wheel in a minimal context; return ``(tag, wheel version)``."""
    assert ENGINE is not None, "FINDFMT_CONTAINER_TESTS=1 needs docker or podman"
    assert UV is not None, "FINDFMT_CONTAINER_TESTS=1 needs uv"
    context = tmp_path_factory.mktemp("context")
    for name in ("Dockerfile", ".dockerignore", "pyproject.toml", "uv.lock"):
        shutil.copy(ROOT / name, context)

    _run(UV, "build", "--wheel", "--out-dir", str(context / "dist"), str(ROOT))
    (wheel,) = (context / "dist").glob("findfmt-*.whl")
    tag = f"findfmt-test:{uuid.uuid4().hex[:12]}"
    _run(ENGINE, "build", "--tag", tag, str(context))
    yield tag, wheel.name.split("-")[1]
    subprocess.run([ENGINE, "rmi", "--force", tag], check=False, capture_output=True)


def test_container_version_matches_wheel(image: tuple[str, str]) -> None:
    """The image reports the version of the wheel it was built from, not a fallback version."""
    tag, version = image
    assert _run(str(ENGINE), "run", "--rm", tag, "--version") == f"findfmt {version}"


def test_container_excludes_uv_and_runs_unprivileged(image: tuple[str, str]) -> None:
    """The runtime image has no uv, runs as appuser, and imports findfmt from its venv."""
    tag, _ = image
    script = (
        "command -v uv || command -v uvx || true; id -un; "
        "python3 -c 'import findfmt; print(findfmt.__file__)'"
    )
    out = _run(str(ENGINE), "run", "--rm", "--entrypoint", "sh", tag, "-c", script).splitlines()
    assert out[0] == "appuser", f"uv found or wrong user: {out}"
    assert out[1].startswith("/opt/findfmt/lib/")


def test_container_classifies_a_mounted_tree(image: tuple[str, str], tmp_path: Path) -> None:
    """A mounted workspace is classified like the CLI does on the host."""
    tag, _ = image
    (tmp_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("hi\n", encoding="utf-8")
    tmp_path.chmod(0o755)
    mount = f"{tmp_path}:/workspace:ro"
    if Path("/sys/fs/selinux/enforce").exists():
        mount += ",Z"

    out = _run(str(ENGINE), "run", "--rm", "-v", mount, tag, "-t", "python", "-l")
    assert out.splitlines() == ["app.py"]
