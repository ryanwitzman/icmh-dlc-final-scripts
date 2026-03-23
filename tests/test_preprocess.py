import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocess import trim_video


def test_has_nvenc_success(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.stdout = "h264_nvenc"
    assert trim_video.has_nvenc() is True


def test_has_nvenc_missing(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.stdout = "libx264"
    assert trim_video.has_nvenc() is False


def test_build_ffmpeg_cmd(mocker):
    mocker.patch.object(trim_video, "trim_start", 60)
    mocker.patch.object(trim_video, "duration", 300)
    mocker.patch.object(trim_video, "fps", 30)
    mocker.patch.object(trim_video, "policy", "CFR")
    mocker.patch.object(trim_video, "ffmpeg_exe", "mock_ffmpeg")

    cmd_cpu = trim_video.build_ffmpeg_cmd("input.mp4", "output.mp4", gpu=False)
    assert "mock_ffmpeg" in cmd_cpu[0]
    assert "-ss" in cmd_cpu and cmd_cpu[cmd_cpu.index("-ss") + 1] == "60"
    assert "-t" in cmd_cpu and cmd_cpu[cmd_cpu.index("-t") + 1] == "300"
    assert "-c:v" in cmd_cpu and cmd_cpu[cmd_cpu.index("-c:v") + 1] == "libx264"
    assert "-vsync" in cmd_cpu and cmd_cpu[cmd_cpu.index("-vsync") + 1] == "cfr"

    cmd_gpu = trim_video.build_ffmpeg_cmd("input.mp4", "output.mp4", gpu=True)
    assert "-hwaccel" in cmd_gpu
    assert "-c:v" in cmd_gpu and cmd_gpu[cmd_gpu.index("-c:v") + 1] == "h264_nvenc"


def test_process_video_error_handling(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_response = mocker.Mock()
    mock_response.returncode = 1
    mock_response.stderr = "FFMPEG FAILED"
    mock_run.return_value = mock_response

    mocker.patch.object(trim_video, "build_ffmpeg_cmd", return_value=["mock_ffmpeg"])
    mocker.patch.object(trim_video, "has_nvenc", return_value=False)

    with pytest.raises(RuntimeError, match="FFmpeg failed with code 1"):
        trim_video.process_video()
