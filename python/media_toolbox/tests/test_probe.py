"""
Unit tests for ffprobe parser and inspection runner (core/probe.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import pytest

from media_toolbox.core.models import MediaInfo, ProbeError
from media_toolbox.core.probe import (
    parse_frame_rate,
    parse_probe_json,
    parse_rotation,
    probe_media,
)


class TestParseProbeJson:
    """Test suite for parsing deserialized ffprobe JSON structures."""

    def test_parse_standard_mp4(self, probe_data_standard_mp4: dict[str, Any]) -> None:
        media = parse_probe_json(probe_data_standard_mp4)
        assert isinstance(media, MediaInfo)
        assert media.has_video is True
        assert media.has_audio is True
        assert media.primary_video is not None
        assert media.primary_video.codec_name == "h264"
        assert media.primary_video.width == 1920
        assert media.primary_video.height == 1080
        assert media.primary_video.fps == 30.0
        assert media.primary_video.pix_fmt == "yuv420p"
        assert media.primary_video.duration == 60.0
        assert media.primary_video.bit_rate == 2500000

        assert media.primary_audio is not None
        assert media.primary_audio.codec_name == "aac"
        assert media.primary_audio.channels == 2
        assert media.primary_audio.sample_rate == 48000
        assert media.primary_audio.channel_layout == "stereo"
        assert media.primary_audio.duration == 60.0
        assert media.primary_audio.bit_rate == 192000

        assert media.format.filename == "sample_video.mp4"
        assert media.format.format_name == "mov,mp4,m4a,3gp,3g2,mj2"
        assert media.format.duration == 60.0
        assert media.format.size_bytes == 20190000
        assert media.duration == 60.0

    def test_parse_audio_only_with_cover_art(self, probe_data_audio_only_mp3: dict[str, Any]) -> None:
        media = parse_probe_json(probe_data_audio_only_mp3)
        assert media.has_video is False
        assert media.primary_video is None
        assert media.has_audio is True
        assert media.primary_audio is not None
        assert media.primary_audio.codec_name == "mp3"
        assert len(media.video_streams) == 1
        assert media.video_streams[0].is_attached_pic is True
        assert media.is_audio_only is True
        assert media.duration == 180.5

    def test_parse_silent_mp4(self, probe_data_silent_mp4: dict[str, Any]) -> None:
        media = parse_probe_json(probe_data_silent_mp4)
        assert media.has_video is True
        assert media.has_audio is False
        assert media.primary_audio is None
        assert len(media.audio_streams) == 0
        assert media.primary_video is not None
        assert media.primary_video.codec_name == "h264"
        assert media.primary_video.width == 1280
        assert media.primary_video.height == 720
        # NTSC fractional frame rate 24000/1001 ~ 23.976
        assert media.primary_video.fps == pytest.approx(23.976, rel=1e-3)
        assert media.is_video_only is True

    def test_parse_png_image(self, probe_data_png_image: dict[str, Any]) -> None:
        media = parse_probe_json(probe_data_png_image)
        assert media.has_video is True
        assert media.has_audio is False
        assert media.duration == 0.0
        assert media.primary_video is not None
        assert media.primary_video.fps is None
        assert media.is_image is True

    @pytest.mark.parametrize(
        "fps_str, expected_float",
        [
            ("30/1", 30.0),
            ("60/1", 60.0),
            ("24000/1001", 23.9760239),
            ("30000/1001", 29.9700299),
            ("25/1", 25.0),
            ("0/0", None),
            ("N/A", None),
            ("", None),
            ("invalid", None),
        ],
    )
    def test_parse_frame_rate_variations(self, fps_str: str, expected_float: float | None) -> None:
        data = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 100,
                    "height": 100,
                    "r_frame_rate": fps_str,
                }
            ],
            "format": {"filename": "test.mp4", "format_name": "mp4"},
        }
        media = parse_probe_json(data)
        assert media.primary_video is not None
        if expected_float is None:
            assert media.primary_video.fps is None
        else:
            assert media.primary_video.fps == pytest.approx(expected_float, rel=1e-4)

    def test_parse_duration_fallback(self, probe_data_missing_format_duration: dict[str, Any]) -> None:
        media = parse_probe_json(probe_data_missing_format_duration)
        assert media.format.duration is None
        assert media.primary_video is not None
        assert media.primary_video.duration == 42.5
        assert media.duration == 42.5

    @pytest.mark.parametrize(
        "malformed_data",
        [
            {},
            {"streams": []},  # Missing format
            {"format": {}},  # Missing streams
            {"streams": "not a list", "format": {}},
            {"streams": [], "format": "not a dict"},
        ],
    )
    def test_parse_malformed_json_raises_probe_error(self, malformed_data: dict[str, Any]) -> None:
        with pytest.raises(ProbeError):
            parse_probe_json(malformed_data)

    def test_parse_rotation_variations(self) -> None:
        stream_matrix = {"side_data_list": [{"rotation": -90}]}
        assert parse_rotation(stream_matrix) == 270

        stream_tag = {"tags": {"rotate": "90"}}
        assert parse_rotation(stream_tag) == 90

        stream_none = {}
        assert parse_rotation(stream_none) == 0


class TestProbeMediaExecution:
    """Test suite for probe_media command invocation and error handling."""

    def test_probe_media_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            probe_media("/path/to/definitely_nonexistent_file_12345.mp4")

    @patch("subprocess.run")
    def test_probe_media_success(
        self, mock_run: MagicMock, tmp_path: Path, mock_ffprobe_standard_mp4_json: str
    ) -> None:
        dummy_file = tmp_path / "test.mp4"
        dummy_file.write_bytes(b"dummy content")

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = mock_ffprobe_standard_mp4_json
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        media = probe_media(dummy_file)
        assert media.has_video is True
        assert media.has_audio is True

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffprobe" in args[0]
        assert "-print_format" in args
        assert "json" in args
        assert "-show_format" in args
        assert "-show_streams" in args
        assert str(dummy_file) in args

    @patch("subprocess.run")
    def test_probe_media_subprocess_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        dummy_file = tmp_path / "corrupt.mp4"
        dummy_file.write_bytes(b"bad content")

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Invalid data found when processing input"
        mock_run.return_value = mock_process

        with pytest.raises(ProbeError, match="ffprobe failed with exit code 1"):
            probe_media(dummy_file)

    @patch("subprocess.run")
    def test_probe_media_corrupt_json_output(self, mock_run: MagicMock, tmp_path: Path) -> None:
        dummy_file = tmp_path / "corrupt.mp4"
        dummy_file.write_bytes(b"bad content")

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "{this is not valid json..."
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        with pytest.raises(ProbeError, match="Failed to parse ffprobe output as JSON"):
            probe_media(dummy_file)

    @patch("subprocess.run")
    def test_probe_media_empty_output(self, mock_run: MagicMock, tmp_path: Path) -> None:
        dummy_file = tmp_path / "empty.mp4"
        dummy_file.write_bytes(b"empty")

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        with pytest.raises(ProbeError, match="ffprobe returned empty output"):
            probe_media(dummy_file)

    @patch("subprocess.run", side_effect=FileNotFoundError("Executable not found"))
    def test_probe_media_missing_binary(self, mock_run: MagicMock, tmp_path: Path) -> None:
        dummy_file = tmp_path / "valid.mp4"
        dummy_file.write_bytes(b"content")

        with pytest.raises(ProbeError, match="ffprobe binary not found"):
            probe_media(dummy_file, ffprobe_bin="nonexistent_ffprobe_bin")
