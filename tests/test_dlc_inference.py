import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dlc import run_dlc_inference  # noqa: E402


def test_log_environment(mocker, caplog):
    caplog.set_level(logging.INFO)

    import sys
    import types

    module = types.ModuleType("deeplabcut")
    module.__version__ = "2.3.11"
    sys.modules["deeplabcut"] = module

    mock_run = mocker.patch("subprocess.run")
    mock_response = mocker.Mock()
    mock_response.returncode = 0
    mock_response.stdout = "0, NVIDIA RTX 4090, 24576, 12000, 45\n"
    mock_run.return_value = mock_response

    run_dlc_inference.log_environment()
    print("-------CAPLOG--------")
    print(caplog.text)
    print("---------------------")
    assert "NVIDIA RTX 4090" in caplog.text
    assert "12000/24576 MiB free" in caplog.text


def test_collect_and_move_outputs(tmp_path):
    video_dir = tmp_path / "videos"
    out_dir = tmp_path / "outputs"
    video_dir.mkdir()
    out_dir.mkdir()

    video_path = video_dir / "vid1.mp4"

    (video_dir / "vid1DLC_resnet50.h5").touch()
    (video_dir / "vid1_superanimal.pickle").touch()

    run_dlc_inference.collect_and_move_outputs(video_path, out_dir)

    assert (out_dir / "vid1DLC_resnet50.h5").exists()
    assert (out_dir / "vid1_superanimal.pickle").exists()
    assert not (video_dir / "vid1DLC_resnet50.h5").exists()
