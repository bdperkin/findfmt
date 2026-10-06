import subprocess
import sys
from pathlib import Path


def test_integration_cli_subprocess(sample_repo: Path):
    cmd = [
        sys.executable,
        "-m",
        "findfmt",
        str(sample_repo),
        "-t",
        "python",
        "-l",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert proc.returncode == 0
    assert f"{Path('src/app.py')} [file," in proc.stdout
    assert "python" in proc.stdout


def test_integration_pipe_xargs_compatibility(sample_repo: Path):
    # Test -0 works cleanly with NUL delimiter
    cmd = [
        sys.executable,
        "-m",
        "findfmt",
        str(sample_repo),
        "-t",
        "python",
        "-0",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    items = [item for item in proc.stdout.split("\0") if item]
    assert len(items) >= 2
    for item in items:
        assert item.endswith(".py") or "mytool" in item
