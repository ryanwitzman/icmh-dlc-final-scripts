# Pipeline Tests

This directory contains standalone test scripts written in Python (`pytest`) to quickly verify the structural integrity of the pipeline, its configuration files, and the conda environment.

## Running the Tests

To run the tests locally or on the HPC cluster, ensure you are in the correct Conda environment, then simply run:

```bash
# From the root directory of the project
pytest tests/ -v
```

## Available Tests

- **`test_environment.py`**: Verifies that Python 3.9+ is being used, required Python packages (like `deeplabcut` and `snakemake`) are importable, and `ffmpeg` is available on the path.
- **`test_configs.py`**: Ensures `configs/config.yaml` exists and has all the keys the pipeline expects.
- **`test_pipeline_dryrun.py`**: Runs a `snakemake -n` "dry run". If this passes, the DAG is completely parsable, meaning there are no syntax errors in the Snakefile or missing basic inputs required for resolution.
