import subprocess
import pytest
from pathlib import Path


def test_snakemake_dryrun():
    workflow_dir = Path("workflow")
    assert (
        workflow_dir.exists() and (workflow_dir / "Snakefile").exists()
    ), "Snakefile not found in workflow directory"


    try:

        result = subprocess.run(
            ["snakemake", "-n", "-q"],
            cwd=str(workflow_dir),
            capture_output=True,
            text=True,
        )


        if result.returncode != 0:

            pytest.fail(f"Snakemake dry-run failed with error:\n{result.stderr}")

    except FileNotFoundError:
        pytest.fail("Snakemake executable not found in PATH.")
