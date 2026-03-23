import sys
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from postprocess import h5_to_csv  # noqa: E402


@pytest.fixture
def mock_logger():
    return logging.getLogger("test_logger")


def create_mock_dlc_h5(num_frames=10, p_cutoff=0.6, nan_likelihood=False):
    scorer = "DLC_resnet50_mock"
    bodyparts = ["snout", "tailBase"]
    coords = ["x", "y", "likelihood"]

    columns = pd.MultiIndex.from_product(
        [[scorer], bodyparts, coords], names=["scorer", "bodyparts", "coords"]
    )

    data = []
    for _ in range(num_frames):
        row = []
        for bp in bodyparts:
            row.extend([np.random.rand() * 100, np.random.rand() * 100])
            if nan_likelihood and bp == "snout":
                row.append(0.1)
            else:
                row.append(0.9)
        data.append(row)

    return pd.DataFrame(data, columns=columns)


def test_validate_h5_success(mock_logger):
    df = create_mock_dlc_h5()
    h5_to_csv.validate_h5(
        df,
        logger=mock_logger,
        expected_bodyparts=["snout", "tailBase"],
        expected_frames=10,
    )


def test_validate_h5_missing_bodyparts(mock_logger):
    df = create_mock_dlc_h5()
    with pytest.raises(ValueError, match="H5 validation failed"):
        h5_to_csv.validate_h5(
            df, logger=mock_logger, expected_bodyparts=["snout", "earLeft"]
        )


def test_flatten_drops_low_likelihood(mock_logger):
    df = create_mock_dlc_h5(nan_likelihood=True)
    flat_df = h5_to_csv.flatten(df, pcutoff=0.6, logger=mock_logger)

    assert np.isnan(flat_df["snout_x"]).all()
    assert np.isnan(flat_df["snout_y"]).all()

    assert not np.isnan(flat_df["tailBase_x"]).any()
    assert not np.isnan(flat_df["tailBase_y"]).any()
