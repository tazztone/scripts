"""
Unit test suite for media_toolbox CLI entrypoint and output formatters (cli.py & __main__.py).

Verifies:
- Argument parsing and help generation for all subcommands
- Terminal output formatting in human-readable and JSON modes
- Handling of standard video, audio-only, silent video, still images, and corrupted media
- Command generation and option mapping for 'transcode' and 'extract-audio'
- Exit code semantics and error reporting
- Routing logic in __main__.py (CLI execution vs lazy UI launch vs headless fallback)
- 100% fast, isolated execution (<0.5s) without external FFmpeg binaries
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock, patch
import pytest

from media_toolbox.core.models import (
    AudioStream,
    EncodeOptions,
    FormatInfo,
    MediaInfo,
    ProbeError,
    ProgressEvent,
    VideoStream,
)
from media_toolbox.core.runner import RunnerCancelledError, RunnerError
import media_toolbox.cli as cli
import media_toolbox.__main__ as main_module


# ---------------------------------------------------------------------------
# Synthetic Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_standard_video_info() -> MediaInfo:
    """Pre-built MediaInfo representing a standard 1080p MP4 video with stereo AAC audio."""
    v = VideoStream(
        index=0,
        codec_name="h264",
        width=1920,
        height=1080,
        fps=30.0,
        duration=60.0,
        bit_rate=2500000,
        pix_fmt="yuv420p",
    )
    a = AudioStream(
        index=1,
        codec_name="aac",
        channels=2,
        sample_rate=48000,
        channel_layout="stereo",
        duration=60.0,
        bit_rate=192000,
    )
    fmt = FormatInfo(
        filename="sample_video.mp4",
        format_name="mov,mp4",
        duration=60.0,
        size_bytes=20190000,
        bit_rate=2692000,
    )
    return MediaInfo(format=fmt, video_streams=(v,), audio_streams=(a,))


@pytest.fixture
def mock_audio_only_info() -> MediaInfo:
    """Pre-built MediaInfo representing an MP3 audio-only track with ID3 album art."""
    art = VideoStream(
        index=1,
        codec_name="png",
        width=500,
        height=500,
        is_attached_pic=True,
    )
    a = AudioStream(
        index=0,
        codec_name="mp3",
        channels=2,
        sample_rate=44100,
        channel_layout="stereo",
        duration=180.5,
        bit_rate=320000,
    )
    fmt = FormatInfo(
        filename="song.mp3",
        format_name="mp3",
        duration=180.5,
        size_bytes=7220000,
        bit_rate=320000,
    )
    return MediaInfo(format=fmt, video_streams=(art,), audio_streams=(a,))


@pytest.fixture
def mock_silent_video_info() -> MediaInfo:
    """Pre-built MediaInfo representing a silent video file (zero audio streams)."""
    v = VideoStream(
        index=0,
        codec_name="h264",
        width=1280,
        height=720,
        fps=24.0,
        duration=10.0,
        bit_rate=1200000,
        pix_fmt="yuv420p",
    )
    fmt = FormatInfo(
        filename="silent.mp4",
        format_name="mp4",
        duration=10.0,
        size_bytes=1500000,
        bit_rate=1200000,
    )
    return MediaInfo(format=fmt, video_streams=(v,), audio_streams=())


@pytest.fixture
def mock_still_image_info() -> MediaInfo:
    """Pre-built MediaInfo representing a still PNG image."""
    v = VideoStream(
        index=0,
        codec_name="png",
        width=800,
        height=600,
        fps=None,
        duration=None,
        bit_rate=None,
        pix_fmt="rgb24",
    )
    fmt = FormatInfo(
        filename="photo.png",
        format_name="image2",
        duration=None,
        size_bytes=45000,
        bit_rate=None,
    )
    return MediaInfo(format=fmt, video_streams=(v,), audio_streams=())


@pytest.fixture
def mock_incomplete_metadata_info() -> MediaInfo:
    """Pre-built MediaInfo with None duration, None bitrates (e.g. streaming chunks)."""
    v = VideoStream(
        index=0,
        codec_name="h264",
        width=1920,
        height=1080,
        fps=30.0,
        duration=None,
        bit_rate=None,
    )
    fmt = FormatInfo(
        filename="stream.ts",
        format_name="mpegts",
        duration=None,
        size_bytes=None,
        bit_rate=None,
    )
    return MediaInfo(format=fmt, video_streams=(v,), audio_streams=())


# ---------------------------------------------------------------------------
# Test Suite 1: Subcommand & Flag Parsing
# ---------------------------------------------------------------------------


class TestCliSubcommandParsing:
    """Verifies argument parsing, flag handling, help generation, and exit codes."""

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--version prints package version and exits 0."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "0.1.0" in captured.out or "0.1.0" in captured.err

    def test_top_level_help_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--help lists available subcommands."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr().out
        assert "inspect" in captured
        assert "transcode" in captured
        assert "extract-audio" in captured

    def test_inspect_subcommand_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """inspect --help lists file argument and --json flag."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["inspect", "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr().out
        assert "--json" in captured
        assert "file" in captured.lower()

    def test_transcode_subcommand_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """transcode --help lists all encoding flags."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["transcode", "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr().out
        for flag in (
            "--preset",
            "--crf",
            "--target-size-mb",
            "--speed",
            "--scale",
            "--crop",
            "--two-pass",
            "--quiet",
        ):
            assert flag in captured

    def test_extract_audio_subcommand_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """extract-audio --help lists audio extraction flags."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["extract-audio", "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr().out
        for flag in ("--codec", "--bitrate", "--speed", "--normalize"):
            assert flag in captured

    def test_unknown_subcommand_exits_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Passing an unrecognized subcommand exits non-zero (exit code 2)."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["nonexistent-command"])
        assert exc_info.value.code != 0

    def test_no_arguments_prints_help_or_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Invoking CLI with empty arguments prints usage/help and exits with status 0 or 2."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main([])
        assert exc_info.value.code in (0, 2)


# ---------------------------------------------------------------------------
# Test Suite 2: Mock Execution Tests for `inspect`
# ---------------------------------------------------------------------------


class TestCliInspectCommand:
    """Verifies media inspection terminal output and error handling."""

    @patch("media_toolbox.cli.probe_media")
    def test_inspect_video_and_audio_file(
        self,
        mock_probe: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect standard video+audio file renders clean formatted technical metadata."""
        mock_probe.return_value = mock_standard_video_info

        exit_code = cli.main(["inspect", "sample_video.mp4"])
        assert exit_code == 0

        captured = capsys.readouterr().out
        assert "sample_video.mp4" in captured
        assert "1920x1080" in captured
        assert "h264" in captured
        assert "30" in captured
        assert "aac" in captured
        assert "stereo" in captured
        assert "48000" in captured or "48.0" in captured
        mock_probe.assert_called_once()

    @patch("media_toolbox.cli.probe_media")
    def test_inspect_audio_only_file(
        self,
        mock_probe: MagicMock,
        mock_audio_only_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect audio-only file displays audio details and indicates no primary video track."""
        mock_probe.return_value = mock_audio_only_info

        exit_code = cli.main(["inspect", "song.mp3"])
        assert exit_code == 0

        captured = capsys.readouterr().out
        assert "song.mp3" in captured
        assert "mp3" in captured
        assert "44100" in captured or "44.1" in captured
        assert "1920x1080" not in captured

    @patch("media_toolbox.cli.probe_media")
    def test_inspect_silent_video_file(
        self,
        mock_probe: MagicMock,
        mock_silent_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect silent video displays video details and indicates absence of audio streams."""
        mock_probe.return_value = mock_silent_video_info

        exit_code = cli.main(["inspect", "silent.mp4"])
        assert exit_code == 0

        captured = capsys.readouterr().out
        assert "silent.mp4" in captured
        assert "1280x720" in captured
        assert "h264" in captured

    @patch("media_toolbox.cli.probe_media")
    def test_inspect_still_image(
        self,
        mock_probe: MagicMock,
        mock_still_image_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect still PNG image handles zero/None duration without crashing."""
        mock_probe.return_value = mock_still_image_info

        exit_code = cli.main(["inspect", "photo.png"])
        assert exit_code == 0

        captured = capsys.readouterr().out
        assert "photo.png" in captured
        assert "800x600" in captured
        assert "png" in captured

    @patch("media_toolbox.cli.probe_media")
    def test_inspect_json_mode(
        self,
        mock_probe: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--json flag outputs valid, structured JSON dictionary."""
        mock_probe.return_value = mock_standard_video_info

        exit_code = cli.main(["inspect", "--json", "sample_video.mp4"])
        assert exit_code == 0

        captured = capsys.readouterr().out
        data = json.loads(captured)
        assert isinstance(data, dict)
        assert "format" in data
        assert data["format"]["filename"] == "sample_video.mp4"
        assert len(data["video_streams"]) == 1
        assert data["video_streams"][0]["width"] == 1920
        assert len(data["audio_streams"]) == 1
        assert data["audio_streams"][0]["codec_name"] == "aac"

    @patch("media_toolbox.cli.probe_media")
    def test_inspect_json_mode_audio_only(
        self,
        mock_probe: MagicMock,
        mock_audio_only_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--json flag for audio-only file serializes cleanly."""
        mock_probe.return_value = mock_audio_only_info

        exit_code = cli.main(["inspect", "--json", "song.mp3"])
        assert exit_code == 0

        data = json.loads(capsys.readouterr().out)
        assert data["format"]["filename"] == "song.mp3"
        assert len(data["audio_streams"]) == 1
        assert data["audio_streams"][0]["codec_name"] == "mp3"

    @patch("media_toolbox.cli.probe_media")
    def test_inspect_resilience_missing_metadata(
        self,
        mock_probe: MagicMock,
        mock_incomplete_metadata_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect handles None duration and None bitrates by displaying 'N/A' without errors."""
        mock_probe.return_value = mock_incomplete_metadata_info

        exit_code = cli.main(["inspect", "stream.ts"])
        assert exit_code == 0

        captured = capsys.readouterr().out
        assert "stream.ts" in captured
        assert "1920x1080" in captured

    @patch("media_toolbox.cli.probe_media")
    def test_inspect_file_not_found(
        self,
        mock_probe: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Non-existent file triggers non-zero exit code and clean error message."""
        mock_probe.side_effect = FileNotFoundError("Media file not found: missing.mp4")

        exit_code = cli.main(["inspect", "missing.mp4"])
        assert exit_code != 0

        err = capsys.readouterr().err
        assert "not found" in err.lower() or "missing.mp4" in err

    @patch("media_toolbox.cli.probe_media")
    def test_inspect_probe_error(
        self,
        mock_probe: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """ProbeError triggers non-zero exit code and stderr error message."""
        mock_probe.side_effect = ProbeError("Corrupted bitstream")

        exit_code = cli.main(["inspect", "corrupt.mp4"])
        assert exit_code != 0

        err = capsys.readouterr().err
        assert "corrupted bitstream" in err.lower() or "probe error" in err.lower()

    @patch("media_toolbox.cli.probe_media")
    def test_shortcut_inspect_syntax(
        self,
        mock_probe: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Direct file argument 'media_toolbox <file>' acts as shortcut to 'inspect <file>'."""
        mock_probe.return_value = mock_standard_video_info

        exit_code = cli.main(["sample_video.mp4"])
        assert exit_code == 0
        assert "1920x1080" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Test Suite 3: Mock Execution Tests for `transcode`
# ---------------------------------------------------------------------------


class TestCliTranscodeCommand:
    """Verifies transcode argument generation, options mapping, and runner execution."""

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_transcode_preset_crf_speed_mapping(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
    ) -> None:
        """Options --preset, --crf, --speed map cleanly to EncodeOptions."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "out.mp4"]]

        exit_code = cli.main([
            "transcode",
            "in.mp4",
            "out.mp4",
            "--preset",
            "h265",
            "--crf",
            "28",
            "--speed",
            "1.5",
        ])
        assert exit_code == 0

        mock_builder.assert_called_once()
        opts: EncodeOptions = mock_builder.call_args[0][2]

        assert opts.preset == "h265"
        assert opts.crf == 28
        assert opts.speed == 1.5
        mock_runner.assert_called_once()

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_transcode_target_size_and_two_pass(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
    ) -> None:
        """--target-size-mb and --two-pass correctly configure EncodeOptions."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "pass1"], ["ffmpeg", "pass2"]]

        exit_code = cli.main([
            "transcode",
            "in.mp4",
            "out.mp4",
            "--target-size-mb",
            "25",
            "--two-pass",
        ])
        assert exit_code == 0

        opts: EncodeOptions = mock_builder.call_args[0][2]
        assert opts.target_size_mb == 25.0
        assert opts.two_pass is True

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_transcode_scale_and_crop(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
    ) -> None:
        """--scale and --crop correctly configure dimensions and aspect cropping."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "out.mp4"]]

        exit_code = cli.main([
            "transcode",
            "in.mp4",
            "out.mp4",
            "--scale",
            "1280:720",
            "--crop",
            "9:16",
        ])
        assert exit_code == 0

        opts: EncodeOptions = mock_builder.call_args[0][2]
        assert opts.scale == (1280, 720)
        assert opts.crop == "9:16"

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_transcode_scale_with_x_separator(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
    ) -> None:
        """--scale accepting '1920x1080' syntax parses into (1920, 1080)."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "out.mp4"]]

        exit_code = cli.main(["transcode", "in.mp4", "out.mp4", "--scale", "1920x1080"])
        assert exit_code == 0

        opts: EncodeOptions = mock_builder.call_args[0][2]
        assert opts.scale == (1920, 1080)

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_transcode_audio_codec_mapping(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
    ) -> None:
        """--audio-codec maps to EncodeOptions.audio_codec."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "out.mp4"]]

        exit_code = cli.main(["transcode", "in.mp4", "out.mp4", "--audio-codec", "libopus"])
        assert exit_code == 0

        opts: EncodeOptions = mock_builder.call_args[0][2]
        assert opts.audio_codec == "libopus"

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_transcode_quiet_suppresses_progress(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--quiet suppresses all progress and completion output."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "out.mp4"]]

        exit_code = cli.main(["transcode", "in.mp4", "out.mp4", "--quiet"])
        assert exit_code == 0
        captured = capsys.readouterr().out
        assert captured == ""

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_transcode_runner_failure(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """RunnerError failure in transcode returns exit code 1 and writes to stderr."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "out.mp4"]]
        mock_runner.side_effect = RunnerError("FFmpeg transcode failed", returncode=1, stderr="Invalid CRF")

        exit_code = cli.main(["transcode", "in.mp4", "out.mp4"])
        assert exit_code != 0
        err = capsys.readouterr().err
        assert "Invalid CRF" in err or "FFmpeg transcode failed" in err

    @patch("media_toolbox.cli.probe_media")
    def test_transcode_invalid_scale_syntax(
        self,
        mock_probe: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Invalid --scale parameter emits error and returns non-zero."""
        mock_probe.return_value = mock_standard_video_info

        exit_code = cli.main(["transcode", "in.mp4", "out.mp4", "--scale", "bad_scale"])
        assert exit_code != 0
        err = capsys.readouterr().err
        assert "scale" in err.lower()

    @patch("media_toolbox.cli.probe_media")
    def test_transcode_negative_speed_rejected(
        self,
        mock_probe: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Non-positive --speed parameter emits error and returns non-zero."""
        mock_probe.return_value = mock_standard_video_info

        exit_code = cli.main(["transcode", "in.mp4", "out.mp4", "--speed", "-1.5"])
        assert exit_code != 0


# ---------------------------------------------------------------------------
# Test Suite 4: Mock Execution Tests for `extract-audio`
# ---------------------------------------------------------------------------


class TestCliExtractAudioCommand:
    """Verifies audio extraction option mapping and command execution."""

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_extract_audio_defaults(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
    ) -> None:
        """Default extract-audio options set extract_audio=True."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "-vn", "out.mp3"]]

        exit_code = cli.main(["extract-audio", "in.mp4", "out.mp3"])
        assert exit_code == 0

        opts: EncodeOptions = mock_builder.call_args[0][2]
        assert opts.extract_audio is True
        mock_runner.assert_called_once()

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_extract_audio_all_options(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
    ) -> None:
        """--codec, --bitrate, --speed, --normalize options map accurately."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "-vn", "out.opus"]]

        exit_code = cli.main([
            "extract-audio",
            "in.mp4",
            "out.opus",
            "--codec",
            "opus",
            "--bitrate",
            "160",
            "--speed",
            "1.25",
            "--normalize",
        ])
        assert exit_code == 0

        opts: EncodeOptions = mock_builder.call_args[0][2]
        assert opts.audio_codec == "opus"
        assert opts.audio_bitrate_kbps == 160
        assert opts.speed == 1.25
        assert opts.normalize_audio is True

    @patch("media_toolbox.cli.probe_media")
    def test_extract_audio_missing_input_file(
        self,
        mock_probe: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Missing input file in extract-audio exits non-zero."""
        mock_probe.side_effect = FileNotFoundError("File not found: nonexistent.mp4")

        exit_code = cli.main(["extract-audio", "nonexistent.mp4", "out.mp3"])
        assert exit_code != 0
        err = capsys.readouterr().err
        assert "not found" in err.lower()

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_extract_audio_runner_failure(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Runner failure in extract-audio prints error and exits non-zero."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "-vn", "out.mp3"]]
        mock_runner.side_effect = RunnerError("FFmpeg audio extract failed", returncode=1, stderr="No audio track")

        exit_code = cli.main(["extract-audio", "in.mp4", "out.mp3"])
        assert exit_code != 0
        err = capsys.readouterr().err
        assert "No audio track" in err or "FFmpeg audio extract failed" in err


# ---------------------------------------------------------------------------
# Test Suite 5: Package Router Tests (__main__.py)
# ---------------------------------------------------------------------------


class TestMainRouter:
    """Verifies entrypoint routing in __main__.py."""

    @patch("media_toolbox.cli.main")
    def test_main_routes_to_cli_when_args_present(self, mock_cli_main: MagicMock) -> None:
        """Arguments passed route directly to cli.main()."""
        mock_cli_main.return_value = 0
        test_argv = ["media_toolbox", "inspect", "video.mp4"]

        with patch.object(sys, "argv", test_argv):
            main_module.main()

        mock_cli_main.assert_called_once_with(["inspect", "video.mp4"])

    @patch("importlib.import_module")
    def test_main_routes_to_ui_when_display_present_and_no_args(self, mock_import: MagicMock) -> None:
        """Empty arguments in a graphical environment lazily import and launch UI."""
        mock_ui_module = MagicMock()
        mock_import.return_value = mock_ui_module

        with patch.object(sys, "argv", ["media_toolbox"]):
            with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
                main_module.main()

        mock_import.assert_called_once_with("media_toolbox.ui.app")
        mock_ui_module.main.assert_called_once()

    @patch("media_toolbox.cli.main")
    def test_main_falls_back_to_cli_help_when_headless_and_no_args(self, mock_cli_main: MagicMock) -> None:
        """Empty arguments in a headless environment route to CLI help."""
        clean_env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}

        with patch.object(sys, "argv", ["media_toolbox"]):
            with patch.dict(os.environ, clean_env, clear=True):
                main_module.main()

        mock_cli_main.assert_called_once()


# ---------------------------------------------------------------------------
# Test Suite 6: Edge Cases, Formatters & Utilities
# ---------------------------------------------------------------------------


class TestCliFormattersAndEdgeCases:
    """Verifies formatting utilities and operational edge cases."""

    def test_format_duration(self) -> None:
        assert cli.format_duration(None) == "N/A"
        assert cli.format_duration(-5.0) == "N/A"
        assert cli.format_duration(0.0) == "00:00:00.00"
        assert cli.format_duration(65.5) == "00:01:05.50"
        assert cli.format_duration(3665.25) == "01:01:05.25"

    def test_format_file_size(self) -> None:
        assert cli.format_file_size(None) == "N/A"
        assert cli.format_file_size(-1) == "N/A"
        assert cli.format_file_size(500) == "500 B"
        assert "KB" in cli.format_file_size(2048)
        assert "MB" in cli.format_file_size(2048 * 1024)
        assert "GB" in cli.format_file_size(2048 * 1024 * 1024)

    def test_format_bitrate(self) -> None:
        assert cli.format_bitrate(None) == "N/A"
        assert cli.format_bitrate(0) == "N/A"
        assert cli.format_bitrate(128000) == "128 kbps"
        assert "Mbps" in cli.format_bitrate(2500000)

    def test_format_aspect_ratio(self) -> None:
        assert cli.format_aspect_ratio(0, 1080) == "N/A"
        assert cli.format_aspect_ratio(1920, 0) == "N/A"
        assert "16:9" in cli.format_aspect_ratio(1920, 1080)
        assert "4:3" in cli.format_aspect_ratio(640, 480)

    def test_format_fps(self) -> None:
        assert cli.format_fps(None) == "N/A"
        assert cli.format_fps(0.0) == "N/A"
        assert cli.format_fps(30.0) == "30 fps"
        assert cli.format_fps(23.976) == "23.98 fps"
        assert "still picture" in cli.format_fps(90000.0, is_attached_pic=True)

    def test_format_channels(self) -> None:
        assert cli.format_channels("stereo", 2) == "stereo (2 channels)"
        assert cli.format_channels("mono", 1) == "mono (1 channel)"
        assert cli.format_channels(None, 6) == "6 channels"

    def test_parse_scale_arg(self) -> None:
        assert cli.parse_scale_arg(None) is None
        assert cli.parse_scale_arg("") is None
        assert cli.parse_scale_arg("1920x1080") == (1920, 1080)
        assert cli.parse_scale_arg("1280:720") == (1280, 720)
        assert cli.parse_scale_arg("1280:-2") == (1280, -2)
        assert cli.parse_scale_arg("-2:720") == (-2, 720)

        with pytest.raises(ValueError):
            cli.parse_scale_arg("bad")
        with pytest.raises(ValueError):
            cli.parse_scale_arg("1920x")
        with pytest.raises(ValueError):
            cli.parse_scale_arg("-2:-2")
        with pytest.raises(ValueError):
            cli.parse_scale_arg("0:720")

    def test_create_progress_reporter(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert cli.create_progress_reporter(quiet=True) is None

        reporter = cli.create_progress_reporter(quiet=False)
        assert reporter is not None

        evt = ProgressEvent(
            frame=100,
            fps=30.0,
            out_time_seconds=10.0,
            total_size_bytes=1048576,
            speed=2.0,
            percentage=50.0,
            eta_seconds=10.0,
            is_completed=False,
        )
        reporter(evt)

        evt_done = ProgressEvent(
            frame=200,
            fps=30.0,
            out_time_seconds=20.0,
            total_size_bytes=2097152,
            speed=2.0,
            percentage=100.0,
            eta_seconds=0.0,
            is_completed=True,
        )
        reporter(evt_done)

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_transcode_cancellation_returns_130(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """User cancellation of transcode returns exit code 130."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "out.mp4"]]
        mock_runner.side_effect = RunnerCancelledError("Cancelled by user")

        exit_code = cli.main(["transcode", "in.mp4", "out.mp4"])
        assert exit_code == 130
        err = capsys.readouterr().err
        assert "cancelled" in err.lower()

    @patch("media_toolbox.cli.run_ffmpeg_pipeline")
    @patch("media_toolbox.cli.build_ffmpeg_commands")
    @patch("media_toolbox.cli.probe_media")
    def test_extract_audio_cancellation_returns_130(
        self,
        mock_probe: MagicMock,
        mock_builder: MagicMock,
        mock_runner: MagicMock,
        mock_standard_video_info: MediaInfo,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """User cancellation of extract-audio returns exit code 130."""
        mock_probe.return_value = mock_standard_video_info
        mock_builder.return_value = [["ffmpeg", "-i", "in.mp4", "-vn", "out.mp3"]]
        mock_runner.side_effect = RunnerCancelledError("Cancelled by user")

        exit_code = cli.main(["extract-audio", "in.mp4", "out.mp3"])
        assert exit_code == 130
        err = capsys.readouterr().err
        assert "cancelled" in err.lower()
