# Pipeline Tests

This directory contains standalone test scripts I wrote in Python (`pytest`) to quickly verify the structural integrity of the pipeline, its configuration files, and the internal codebase logic.

## Comprehensive Tool Coverage
I set up these tests to fully cover the codebase using mocked datasets. This prevents the need for large GPU utilization during testing and lets us target specific components across the pipeline:

- **`test_environment.py`**: Verifies Python 3.9+, DeepLabCut, Snakemake, and FFmpeg installations.
- **`test_configs.py`**: Ensures `configs/config.yaml` exists and has proper keys.
- **`test_pipeline_dryrun.py`**: Runs a Snakemake dry-run to identify syntax/DAG resolution errors.
- **`test_preprocess.py`**: Asserts the FFmpeg command builders accurately translate `configs/config.yaml` targets into execution strings.
- **`test_dlc_inference.py`**: Verifies GPU allocations are queried correctly and mock outputs are moved successfully post-inference.
- **`test_postprocess.py`**: Uses generated Pandas Dataframes to mock high/low confidence bounds and verifies filtering works (e.g., outputs flat CSVs containing `np.nan` on bad frames).
- **`test_qc_analytics.py`**: Ensures mock flattened outputs can be correctly computed into bounding boxes, heatmaps, and total distance vectors.


## Running the Tests

To run the tests locally or on the HPC cluster, make sure you're in the correct Conda environment (and have `pytest`, `pytest-mock`, `pandas`, `tables`, and `matplotlib` installed). 

You can run them all instantly like this:

```bash
# From the root directory of the project
pytest tests/ -v
```
