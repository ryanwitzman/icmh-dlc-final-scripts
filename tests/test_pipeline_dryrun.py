import subprocess
import pytest
from pathlib import Path


def test_snakemake_dryrun():
    workflow_dir = Path("workflow")
    assert (
        workflow_dir.exists() and (workflow_dir / "Snakefile").exists()
    ), "Snakefile not found in workflow directory"

    # Run a dry-run of snakemake from the directory
    try:
        # We use -n for dry-run and -q for quiet (just evaluate the DAG)
        result = subprocess.run(
            ["snakemake", "-n", "-q"],
            cwd=str(workflow_dir),
            capture_output=True,
            text=True,
        )

        # Output should be either empty (if nothing to do) or contain job counts.
        # But crucially, it should exit with returncode 0
        if result.returncode != 0:
            # Provide Snakemake's error message if dry-run fails
            pytest.fail(f"Snakemake dry-run failed with error:\n{result.stderr}")

    except FileNotFoundError:
        pytest.fail("Snakemake executable not found in PATH.")
