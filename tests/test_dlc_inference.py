import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dlc import run_dlc_inference


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