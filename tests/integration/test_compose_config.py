# Author: DrPlaga

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not available")
def test_compose_security_structure() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate-compose.py")],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=45,
    )
    assert completed.returncode == 0, completed.stdout
