import importlib
import subprocess
import pytest


def test_python_version():
    import sys

    assert sys.version_info >= (3, 9), "Python 3.9+ is recommended for this pipeline."


def test_required_packages():
    required_packages = [
        "deeplabcut",
        "pandas",
        "snakemake",
        "dotenv",
        "yaml",
        "matplotlib",
    ]

    missing_packages = []
    for pkg in required_packages:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing_packages.append(pkg)

    assert not missing_packages, f"Missing required python packages: {missing_packages}"


def test_ffmpeg_installed():
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "ffmpeg version" in result.stdout.lower()
    except FileNotFoundError:
        pytest.fail("FFmpeg is not installed or not in PATH.")
