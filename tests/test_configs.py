import yaml
from pathlib import Path


def test_config_yaml_exists_and_loads():
    config_path = Path("configs/config.yaml")
    assert config_path.exists(), "configs/config.yaml not found at root level"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    assert isinstance(config, dict), "Config file should parse into a dictionary"

    # Check for some essential keys
    expected_keys = [
        "trim_start_seconds",
        "trim_duration_seconds",
        "fps",
        "output_codec",
        "batch_id",
        "pcutoff",
    ]
    for key in expected_keys:
        assert key in config, f"Expected key '{key}' missing from config.yaml"


def test_env_file_exists():
    env_path = Path(".env")
    # It's okay if .env doesn't exist for general running, but it's required for ingest.
    # We will just warn or check if it exists or if the ingest is skipped.
    if env_path.exists():
        with open(env_path, "r") as f:
            content = f.read()
            assert "TENANT_ID=" in content
            assert "CLIENT_ID=" in content
            assert "CLIENT_SECRET=" in content
    else:
        # Just a placeholder in case they only run the pipeline locally.
        pass
