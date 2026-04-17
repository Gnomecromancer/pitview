import subprocess
import sys


def test_version():
    result = subprocess.run(
        [sys.executable, "-m", "pitview.cli", "--version"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_help():
    result = subprocess.run(
        [sys.executable, "-m", "pitview.cli", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
