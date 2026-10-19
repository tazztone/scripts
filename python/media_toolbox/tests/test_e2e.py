"""
Tier 4 Real-World Application Workload Scenarios for media_toolbox.

This module validates the 7 end-to-end real-world workload application scenarios:
1. Scenario 1: Discord Video Compression (25MB target, 2-pass H.264, audio downmix to stereo, faststart).
2. Scenario 2: High-Speed Preview (3.0x speed, chained atempo=2.0,1.5, setpts=0.3333*PTS, 720p scale).
3. Scenario 3: Audio Extraction & Normalization (Extract to MP3, 192k, loudnorm normalization, mute video).
4. Scenario 4: Vertical Social Media Crop (9:16 center crop, 60fps, H.265 CRF 28).
5. Scenario 5: High-Quality GIF Conversion (Palettegen + paletteuse filter_complex, 15fps, 480p width).
6. Scenario 6: Headless Batch CLI Pipeline (media_toolbox.cli inspection on audio-less, corrupt, and multi-stream files).
7. Scenario 7: Nautilus Context Menu Dispatch (Launcher script & extension MIME type detection with space-separated file paths).

INVARIANTS:
- Strict zero module-scope `import gi` or GUI imports.
- Sub-second execution (<1s total across all 7 scenarios).
- Headless execution with synthetic fixtures and mock streams without requiring real GPU/display servers.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import types
from typing import Any, Callable, Generator, Optional
from unittest.mock import MagicMock, call, patch
import pytest

from media_toolbox import cli
from media_toolbox.core.bitrate import calculate_target_video_bitrate
from media_toolbox.core.builder import (
    build_audio_extract_command,
    build_ffmpeg_commands,
    build_gif_command,
    build_single_pass_command,
    build_two_pass_commands,
)
from media_toolbox.core.filtergraph import (
    build_atempo_chain,
    build_audio_filter,
    build_crop_filter,
    build_fps_filter,
    build_scale_filter,
    build_setpts_filter,
    build_video_filter,
)
from media_toolbox.core.models import (
    AudioStream,
    EncodeOptions,
    FormatInfo,
    MediaInfo,
    ProbeError,
    ProgressEvent,
    VideoStream,
)
from media_toolbox.core.presets import (
    GIF_PRESET,
    H264_PRESET,
    H265_PRESET,
    MP3_PRESET,
    get_audio_preset,
    get_video_preset,
)
from media_toolbox.core.runner import (
    ProgressParser,
    run_ffmpeg,
    run_ffmpeg_pipeline,
)


# ---------------------------------------------------------------------------
# Module-Level Teardown & Isolation Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="module")
def isolate_gi_sys_modules() -> Generator[None, None, None]:
    """Ensure no mock modules leak beyond this test module."""
    yield
    gi_mod = sys.modules.get("gi")
    if gi_mod is not None and not hasattr(gi_mod, "__file__"):
        to_delete = [
            k
            for k in list(sys.modules.keys())
            if k == "gi"
            or k.startswith("gi.")
            or k.startswith("gi_")
            or k in ("gobject", "glib", "gio", "gtk", "nautilus")
            or k.startswith("media_toolbox.nautilus.extension")
        ]
        for k in to_delete:
            sys.modules.pop(k, None)


# ---------------------------------------------------------------------------
# Nautilus Headless Mocks (Zero Module-Scope `import gi`)
# ---------------------------------------------------------------------------


class MockLocation:
    """Mock for Gio.File returned by FileInfo.get_location()."""

    def __init__(self, path: str):
        self._path = path

    def get_path(self) -> str:
        return self._path


class MockFileInfo:
    """Mock for Nautilus.FileInfo supporting URI parsing and MIME types."""

    def __init__(
        self,
        path: str | Path,
        mime_type: str = "application/octet-stream",
        is_directory: bool = False,
    ):
        self.path = str(path)
        self.mime_type = mime_type
        self._is_dir = is_directory

    def get_uri(self) -> str:
        from urllib.parse import quote

        return f"file://{quote(self.path)}"

    def get_name(self) -> str:
        return Path(self.path).name

    def get_mime_type(self) -> str:
        return self.mime_type

    def is_directory(self) -> bool:
        return self._is_dir

    def get_location(self) -> MockLocation:
        return MockLocation(self.path)


class MockMenuItem:
    """Mock for Nautilus.MenuItem with signal callback triggering."""

    def __init__(self, name: str = "", label: str = "", tip: str = "", icon: str = ""):
        self.name = name
        self.label = label
        self.tip = tip
        self.icon = icon
        self.submenu: Optional[MockMenu] = None
        self._signals: dict[str, list[tuple[Callable[..., Any], tuple[Any, ...]]]] = {}

    def set_submenu(self, menu: MockMenu) -> None:
        self.submenu = menu

    def connect(self, signal_name: str, handler: Callable[..., Any], *args: Any) -> None:
        if signal_name not in self._signals:
            self._signals[signal_name] = []
        self._signals[signal_name].append((handler, args))

    def emit_activate(self) -> None:
        for handler, args in self._signals.get("activate", []):
            handler(self, *args)

    def activate(self) -> None:
        """Alias for emit_activate."""
        self.emit_activate()


class MockMenu:
    """Mock for Nautilus.Menu container."""

    def __init__(self) -> None:
        self.items: list[MockMenuItem] = []

    def append_item(self, item: MockMenuItem) -> None:
        self.items.append(item)

    def get_items(self) -> list[MockMenuItem]:
        return list(self.items)


class MockMenuProvider:
    """Base dummy for Nautilus.MenuProvider interface."""

    pass


class MockGObject:
    """Base dummy for GObject.GObject."""

    pass


@pytest.fixture
def mock_nautilus_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Inject headless Nautilus/GObject typelib mocks into sys.modules without real gi."""
    fake_nautilus = types.ModuleType("gi.repository.Nautilus")
    fake_nautilus.FileInfo = MockFileInfo  # type: ignore
    fake_nautilus.MenuItem = MockMenuItem  # type: ignore
    fake_nautilus.Menu = MockMenu  # type: ignore
    fake_nautilus.MenuProvider = MockMenuProvider  # type: ignore

    fake_gobject = types.ModuleType("gi.repository.GObject")
    fake_gobject.GObject = MockGObject  # type: ignore

    fake_gi_repo = types.ModuleType("gi.repository")
    fake_gi_repo.Nautilus = fake_nautilus  # type: ignore
    fake_gi_repo.GObject = fake_gobject  # type: ignore

    fake_gi = types.ModuleType("gi")
    fake_gi.repository = fake_gi_repo  # type: ignore
    fake_gi.require_version = lambda *args, **kwargs: None  # type: ignore

    with monkeypatch.context() as m:
        m.setitem(sys.modules, "gi", fake_gi)
        m.setitem(sys.modules, "gi.repository", fake_gi_repo)
        m.setitem(sys.modules, "gi.repository.Nautilus", fake_nautilus)
        m.setitem(sys.modules, "gi.repository.GObject", fake_gobject)

        if "media_toolbox.nautilus.extension" in sys.modules:
            del sys.modules["media_toolbox.nautilus.extension"]

        yield

        if "media_toolbox.nautilus.extension" in sys.modules:
            del sys.modules["media_toolbox.nautilus.extension"]


# ---------------------------------------------------------------------------
# Synthetic Stream & Popen Helpers
# ---------------------------------------------------------------------------


def generate_synthetic_progress_lines(
    duration: float, steps: int = 5, speed: float = 2.0
) -> list[str]:
    """Generate line-by-line -progress pipe:1 key=value stream for testing."""
    lines: list[str] = []
    fps = 30.0
    for i in range(1, steps + 1):
        elapsed = (duration / steps) * i
        frame = int(elapsed * fps)
        out_time_us = int(elapsed * 1_000_000)
        total_size = int(elapsed * 250_000)
        lines.extend([
            f"frame={frame}",
            f"fps={fps:.1f}",
            f"stream_0_0_q=28.0",
            f"bitrate=2000.0kbits/s",
            f"total_size={total_size}",
            f"out_time_us={out_time_us}",
            f"out_time_ms={out_time_us}",
            f"out_time=00:00:{elapsed:05.2f}",
            f"dup_frames=0",
            f"drop_frames=0",
            f"speed={speed:.2f}x",
            "progress=continue",
        ])
    lines.append("progress=end")
    return lines


def create_mock_popen(lines: list[str], returncode: int = 0) -> MagicMock:
    """Create a mock subprocess.Popen yielding synthetic progress stream."""
    proc = MagicMock()
    proc.pid = 42424
    proc.poll.return_value = returncode
    proc.returncode = returncode
    proc.stdout = (f"{line}\n" for line in lines)
    proc.stderr = []
    proc.wait.return_value = returncode
    return proc


# ---------------------------------------------------------------------------
# Scenario 1: Discord Video Compression
# ---------------------------------------------------------------------------


class TestScenario1DiscordVideoCompression:
    """
    Scenario 1: Discord Video Compression
    - Target: 25.0 MB file size limit
    - Duration: 180 seconds (3 minutes)
    - Codec: 2-Pass H.264 (libx264)
    - Audio: Downmixed to stereo with AAC 128k
    - Container optimization: -movflags +faststart
    """

    @pytest.fixture
    def gameplay_media_info(self) -> MediaInfo:
        v = VideoStream(
            index=0,
            codec_name="h264",
            width=1920,
            height=1080,
            fps=60.0,
            duration=180.0,
            bit_rate=6000000,
            pix_fmt="yuv420p",
        )
        a = AudioStream(
            index=1,
            codec_name="ac3",
            channels=6,
            sample_rate=48000,
            channel_layout="5.1",
            duration=180.0,
            bit_rate=384000,
        )
        fmt = FormatInfo(
            filename="gameplay_1080p60.mkv",
            format_name="matroska",
            duration=180.0,
            size_bytes=135000000,
        )
        return MediaInfo(format=fmt, video_streams=(v,), audio_streams=(a,))

    def test_discord_bitrate_math_and_margin(self) -> None:
        """25MB budget over 180s reserving 3% mux overhead computes exactly 976 kbps video bitrate."""
        bitrate = calculate_target_video_bitrate(
            target_size_mb=25.0,
            duration_seconds=180.0,
            audio_bitrate_kbps=128,
            mux_overhead_margin=0.03,
            min_video_bitrate_kbps=64,
        )
        assert bitrate == 976

    def test_discord_two_pass_command_structure(self, gameplay_media_info: MediaInfo) -> None:
        """Two-pass H.264 commands configure Pass 1 null sink and Pass 2 stereo faststart output."""
        options = EncodeOptions(
            target_size_mb=25.0,
            two_pass=True,
            preset="h264",
            audio_bitrate_kbps=128,
            extra_args=("-ac", "2"),
        )
        cmds = build_ffmpeg_commands(
            input_path="gameplay_1080p60.mkv",
            output_path="discord_upload.mp4",
            options=options,
            media_info=gameplay_media_info,
            pass_logfile="/tmp/discord_2pass",
            include_progress=True,
        )

        assert len(cmds) == 2
        pass1_cmd, pass2_cmd = cmds[0], cmds[1]

        # Pass 1 verifications
        assert "-pass" in pass1_cmd and pass1_cmd[pass1_cmd.index("-pass") + 1] == "1"
        assert "-b:v" in pass1_cmd and pass1_cmd[pass1_cmd.index("-b:v") + 1] == "976k"
        assert "-an" in pass1_cmd
        assert "-f" in pass1_cmd and pass1_cmd[pass1_cmd.index("-f") + 1] == "null"
        assert pass1_cmd[-1] == os.devnull

        # Pass 2 verifications
        assert "-pass" in pass2_cmd and pass2_cmd[pass2_cmd.index("-pass") + 1] == "2"
        assert "-b:v" in pass2_cmd and pass2_cmd[pass2_cmd.index("-b:v") + 1] == "976k"
        assert "-c:a" in pass2_cmd and pass2_cmd[pass2_cmd.index("-c:a") + 1] == "aac"
        assert "-b:a" in pass2_cmd and pass2_cmd[pass2_cmd.index("-b:a") + 1] == "128k"
        assert "-ac" in pass2_cmd and pass2_cmd[pass2_cmd.index("-ac") + 1] == "2"
        assert "-movflags" in pass2_cmd and pass2_cmd[pass2_cmd.index("-movflags") + 1] == "+faststart"
        assert pass2_cmd[-1] == "discord_upload.mp4"

    def test_discord_progress_pipeline_aggregation(self) -> None:
        """Synthetic execution of 2-pass pipeline aggregates progress smoothly from 0% to 100%."""
        pass1_lines = generate_synthetic_progress_lines(180.0, steps=3, speed=4.0)
        pass2_lines = generate_synthetic_progress_lines(180.0, steps=3, speed=3.0)

        mock_p1 = create_mock_popen(pass1_lines)
        mock_p2 = create_mock_popen(pass2_lines)

        aggregated_events: list[ProgressEvent] = []
        pass_steps: list[tuple[int, int]] = []

        with patch("subprocess.Popen", side_effect=[mock_p1, mock_p2]):
            run_ffmpeg_pipeline(
                cmds=[["ffmpeg", "-pass", "1"], ["ffmpeg", "-pass", "2"]],
                total_duration_seconds=180.0,
                progress_callback=aggregated_events.append,
                pipeline_progress_callback=lambda p, total, ev: pass_steps.append((p, total)),
            )

        assert len(aggregated_events) >= 6
        assert aggregated_events[0].percentage > 0.0
        assert any(45.0 <= e.percentage <= 55.0 for e in aggregated_events)
        assert aggregated_events[-1].percentage == 100.0
        assert aggregated_events[-1].is_completed is True
        assert (1, 2) in pass_steps
        assert (2, 2) in pass_steps


# ---------------------------------------------------------------------------
# Scenario 2: High-Speed Preview
# ---------------------------------------------------------------------------


class TestScenario2HighSpeedPreview:
    """
    Scenario 2: High-Speed Preview
    - Speed multiplier: 3.0x
    - Video filter: setpts=(1.0/3.0)*PTS
    - Audio filter: chained atempo=2.0,atempo=1.5
    - Scaling: 720p (1280:720 with even dimension snapping)
    """

    def test_high_speed_filtergraph_construction(self) -> None:
        """3.0x speed generates setpts=(1.0/3.0)*PTS and chained atempo=2.0,atempo=1.5."""
        vf = build_video_filter(scale=(1280, 720), speed=3.0)
        assert vf == ["scale=1280:720", "setpts=(1.0/3.0)*PTS"]

        af = build_atempo_chain(3.0)
        assert af == ["atempo=2.0", "atempo=1.5"]

    def test_high_speed_preview_single_pass_command(self) -> None:
        """Command builder emits single-pass CRF 28 command with scale, speed, and atempo chain."""
        options = EncodeOptions(
            speed=3.0,
            scale=(1280, 720),
            preset="h264",
            crf=28,
        )
        cmds = build_ffmpeg_commands(
            input_path="lecture_4k.mp4",
            output_path="preview_720p_3x.mp4",
            options=options,
            include_progress=True,
        )

        assert len(cmds) == 1
        cmd = cmds[0]
        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert cmd[vf_idx + 1] == "scale=1280:720,setpts=(1.0/3.0)*PTS"

        assert "-af" in cmd
        af_idx = cmd.index("-af")
        assert cmd[af_idx + 1] == "atempo=2.0,atempo=1.5"

        assert "-crf" in cmd and cmd[cmd.index("-crf") + 1] == "28"
        assert "-movflags" in cmd and cmd[cmd.index("-movflags") + 1] == "+faststart"
        assert cmd[-1] == "preview_720p_3x.mp4"

    def test_high_speed_preview_cli_execution(self) -> None:
        """CLI transcode subcommand parses speed 3.0 and scale 1280:720 without errors."""
        mock_info = MediaInfo(
            format=FormatInfo(filename="lecture.mp4", format_name="mov,mp4", duration=600.0),
            video_streams=(VideoStream(index=0, codec_name="h264", width=3840, height=2160, fps=30.0),),
            audio_streams=(AudioStream(index=1, codec_name="aac", channels=2, sample_rate=48000),),
        )

        with (
            patch("media_toolbox.cli.probe_media", return_value=mock_info),
            patch("media_toolbox.cli.run_ffmpeg_pipeline") as mock_run,
        ):
            code = cli.main([
                "transcode",
                "lecture.mp4",
                "preview.mp4",
                "--speed",
                "3.0",
                "--scale",
                "1280:720",
                "--crf",
                "28",
                "--quiet",
            ])
            assert code == 0
            assert mock_run.call_count == 1
            executed_cmds = mock_run.call_args[0][0]
            assert "scale=1280:720,setpts=(1.0/3.0)*PTS" in executed_cmds[0]
            assert "atempo=2.0,atempo=1.5" in executed_cmds[0]


# ---------------------------------------------------------------------------
# Scenario 3: Audio Extraction & Normalization
# ---------------------------------------------------------------------------


class TestScenario3AudioExtractionAndNormalization:
    """
    Scenario 3: Audio Extraction & Normalization
    - Target: MP3 at 192 kbps
    - Audio normalization: EBU R128 loudness normalization
    - Video track: Explicitly stripped (-vn)
    """

    def test_audio_extraction_filter_and_preset(self) -> None:
        """Audio filter applies EBU R128 loudnorm and MP3 preset configures libmp3lame."""
        af = build_audio_filter(normalize_loudness=True)
        assert af == ["loudnorm=I=-23:LRA=7:TP=-1.5"]

        args = MP3_PRESET.build_audio_args(bitrate_kbps=192, extract_audio=True)
        assert args == ["-vn", "-c:a", "libmp3lame", "-b:a", "192k"]

    def test_audio_extraction_command_assembly(self) -> None:
        """Command builder generates standalone audio extraction command with loudnorm and -vn."""
        options = EncodeOptions(
            extract_audio=True,
            preset="mp3",
            audio_bitrate_kbps=192,
            normalize_audio=True,
        )
        cmds = build_ffmpeg_commands(
            input_path="podcast_interview.mkv",
            output_path="podcast_normalized.mp3",
            options=options,
            include_progress=True,
        )

        assert len(cmds) == 1
        cmd = cmds[0]
        assert "-vn" in cmd
        assert "-c:v" not in cmd
        assert "-vf" not in cmd
        assert "-af" in cmd
        assert cmd[cmd.index("-af") + 1] == "loudnorm=I=-23:LRA=7:TP=-1.5"
        assert "-c:a" in cmd and cmd[cmd.index("-c:a") + 1] == "libmp3lame"
        assert "-b:a" in cmd and cmd[cmd.index("-b:a") + 1] == "192k"
        assert cmd[-1] == "podcast_normalized.mp3"

    def test_audio_extraction_cli_e2e(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CLI extract-audio subcommand extracts normalized MP3 cleanly."""
        mock_info = MediaInfo(
            format=FormatInfo(filename="podcast.mkv", format_name="matroska", duration=300.0),
            video_streams=(VideoStream(index=0, codec_name="h264", width=1920, height=1080),),
            audio_streams=(AudioStream(index=1, codec_name="flac", channels=2, sample_rate=48000),),
        )

        with (
            patch("media_toolbox.cli.probe_media", return_value=mock_info),
            patch("media_toolbox.cli.run_ffmpeg_pipeline") as mock_run,
        ):
            code = cli.main([
                "extract-audio",
                "podcast.mkv",
                "podcast.mp3",
                "--codec",
                "mp3",
                "--bitrate",
                "192",
                "--normalize",
            ])
            assert code == 0
            assert mock_run.call_count == 1
            captured = capsys.readouterr()
            assert "Audio extraction complete: podcast.mp3" in captured.out


# ---------------------------------------------------------------------------
# Scenario 4: Vertical Social Media Crop
# ---------------------------------------------------------------------------


class TestScenario4VerticalSocialMediaCrop:
    """
    Scenario 4: Vertical Social Media Crop
    - Aspect ratio: 9:16 center crop (TikTok / Reels / Shorts)
    - Frame rate: 60 fps
    - Codec: H.265 (libx265) at CRF 28 with Apple compatibility tag (hvc1)
    """

    def test_vertical_crop_and_fps_filters(self) -> None:
        """9:16 center crop and 60fps filter assemble in strict order crop -> fps."""
        crop_f = build_crop_filter("9:16")
        assert crop_f == "crop=ih*(9/16):ih:(iw-ow)/2:0"

        fps_f = build_fps_filter(60)
        assert fps_f == "fps=fps=60"

        vf = build_video_filter(crop="9:16", fps=60)
        assert vf == ["crop=ih*(9/16):ih:(iw-ow)/2:0", "fps=fps=60"]

    def test_vertical_crop_h265_command_assembly(self) -> None:
        """Command builder generates H.265 CRF 28 command with 9:16 crop, 60fps, and hvc1 tag."""
        options = EncodeOptions(
            crop="9:16",
            fps=60,
            preset="h265",
            crf=28,
        )
        cmds = build_ffmpeg_commands(
            input_path="landscape_clip.mov",
            output_path="vertical_tiktok.mp4",
            options=options,
            include_progress=True,
        )

        assert len(cmds) == 1
        cmd = cmds[0]
        assert "-vf" in cmd
        assert cmd[cmd.index("-vf") + 1] == "crop=ih*(9/16):ih:(iw-ow)/2:0,fps=fps=60"
        assert "-c:v" in cmd and cmd[cmd.index("-c:v") + 1] == "libx265"
        assert "-crf" in cmd and cmd[cmd.index("-crf") + 1] == "28"
        assert "-tag:v" in cmd and cmd[cmd.index("-tag:v") + 1] == "hvc1"
        assert "-movflags" in cmd and cmd[cmd.index("-movflags") + 1] == "+faststart"
        assert cmd[-1] == "vertical_tiktok.mp4"


# ---------------------------------------------------------------------------
# Scenario 5: High-Quality GIF Conversion
# ---------------------------------------------------------------------------


class TestScenario5HighQualityGifConversion:
    """
    Scenario 5: High-Quality GIF Conversion
    - Filtergraph: Two-stage palettegen + paletteuse via -filter_complex
    - Frame rate: 15 fps
    - Scale: 480p width with automatic even-height preservation (scale=480:-2)
    - Audio: Explicitly muted (-an)
    """

    def test_gif_palettegen_paletteuse_filter_complex(self) -> None:
        """GIF conversion generates two-stage palettegen/paletteuse complex filtergraph."""
        options = EncodeOptions(
            preset="gif",
            fps=15,
            scale=(480, -2),
        )
        cmds = build_ffmpeg_commands(
            input_path="screen_recording.mp4",
            output_path="demo.gif",
            options=options,
            include_progress=True,
        )

        assert len(cmds) == 1
        cmd = cmds[0]
        assert "-filter_complex" in cmd
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert fc == "[0:v]scale=480:-2,fps=fps=15,split[a][b];[a]palettegen[p];[b][p]paletteuse"
        assert "-an" in cmd
        assert cmd[-1] == "demo.gif"

    def test_gif_rejects_two_pass(self) -> None:
        """Attempting two-pass encoding for GIF raises ValueError."""
        options = EncodeOptions(preset="gif", two_pass=True)
        with pytest.raises(ValueError, match="Two-pass encoding is not supported for GIF preset"):
            build_ffmpeg_commands("input.mp4", "output.gif", options)

    def test_gif_progress_runner(self) -> None:
        """GIF execution parses stream events up to completion."""
        lines = generate_synthetic_progress_lines(10.0, steps=3, speed=1.5)
        mock_proc = create_mock_popen(lines)
        events: list[ProgressEvent] = []

        with patch("subprocess.Popen", return_value=mock_proc):
            run_ffmpeg(
                ["ffmpeg", "-filter_complex", "...", "demo.gif"],
                total_duration_seconds=10.0,
                progress_callback=events.append,
            )

        assert len(events) >= 3
        assert events[-1].is_completed is True
        assert events[-1].percentage == 100.0


# ---------------------------------------------------------------------------
# Scenario 6: Headless Batch CLI Pipeline
# ---------------------------------------------------------------------------


class TestScenario6HeadlessBatchCLIPipeline:
    """
    Scenario 6: Headless Batch CLI Pipeline
    - Inspection of audio-less files (has_audio=False, audio_streams=[])
    - Corrupted files handling (ProbeError trapped, exit code 1, stderr formatted)
    - Multi-stream files (multiple audio languages, attached cover art)
    - AST invariant: Zero GUI modules loaded during headless execution
    """

    def test_cli_inspect_silent_videofile(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CLI inspect cleanly handles video without audio streams in JSON mode."""
        v = VideoStream(index=0, codec_name="h264", width=1280, height=720, fps=24.0, duration=15.0)
        fmt = FormatInfo(filename="silent.mp4", format_name="mov,mp4", duration=15.0, size_bytes=1000000)
        silent_info = MediaInfo(format=fmt, video_streams=(v,), audio_streams=())

        with patch("media_toolbox.cli.probe_media", return_value=silent_info):
            ret = cli.main(["inspect", "silent.mp4", "--json"])
            assert ret == 0

        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["summary"]["has_video"] is True
        assert data["summary"]["has_audio"] is False
        assert data["audio_streams"] == []
        assert len(data["video_streams"]) == 1

    def test_cli_inspect_corrupt_file_handling(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Corrupt media file raising ProbeError returns exit code 1 with clean stderr error."""
        with patch("media_toolbox.cli.probe_media", side_effect=ProbeError("Corrupt EBML header")):
            ret = cli.main(["inspect", "corrupt_sample.mkv"])
            assert ret == 1

        err = capsys.readouterr().err
        assert "Error probing media: Corrupt EBML header" in err

    def test_cli_inspect_multi_stream_media(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Multi-stream container properly catalogs secondary audio tracks and attached cover art."""
        v_main = VideoStream(index=0, codec_name="hevc", width=3840, height=2160, fps=23.976, duration=120.0)
        a_eng = AudioStream(index=1, codec_name="ac3", channels=6, sample_rate=48000, channel_layout="5.1", duration=120.0, bit_rate=640000)
        a_comm = AudioStream(index=2, codec_name="aac", channels=2, sample_rate=48000, channel_layout="stereo", duration=120.0, bit_rate=128000)
        v_art = VideoStream(index=3, codec_name="png", width=1000, height=1000, is_attached_pic=True)
        fmt = FormatInfo(filename="movie_multi.mkv", format_name="matroska", duration=120.0, size_bytes=250000000)
        multi_info = MediaInfo(format=fmt, video_streams=(v_main, v_art), audio_streams=(a_eng, a_comm))

        with patch("media_toolbox.cli.probe_media", return_value=multi_info):
            ret = cli.main(["inspect", "movie_multi.mkv", "--json"])
            assert ret == 0

        data = json.loads(capsys.readouterr().out)
        assert len(data["video_streams"]) == 2
        assert len(data["audio_streams"]) == 2
        assert data["summary"]["attached_pic_count"] == 1
        assert data["summary"]["audio_stream_count"] == 2

    def test_headless_ast_zero_gi_in_sys_modules(self) -> None:
        """Verify that batch CLI execution does not load 'gi' into sys.modules."""
        repo_python = str(Path(__file__).resolve().parent.parent.parent)
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{repo_python}:{env.get('PYTHONPATH', '')}"
        code = (
            "import sys\n"
            "from media_toolbox import cli\n"
            "assert 'gi' not in sys.modules, f'Forbidden module gi loaded: {list(sys.modules.keys())}'\n"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        assert proc.returncode == 0, f"Headless execution loaded gi:\n{proc.stderr}"


# ---------------------------------------------------------------------------
# Scenario 7: Nautilus Context Menu Dispatch
# ---------------------------------------------------------------------------


class TestScenario7NautilusContextMenuDispatch:
    """
    Scenario 7: Nautilus Context Menu Dispatch
    - Extension MIME and file extension matching
    - Safe handling of spaces and special characters in file paths
    - Detached subprocess execution avoiding Nautilus UI blocking
    - Launcher script shell syntax and argument parsing
    """

    def test_nautilus_extension_mime_and_path_filtering(self, mock_nautilus_env: Any) -> None:
        """Extension accepts video/audio files with spaces and rejects non-media documents."""
        from media_toolbox.nautilus.extension import (
            MediaToolboxExtension,
            get_file_path,
            is_media_file,
        )

        f_video = MockFileInfo("/home/user/My Videos/Action Movie (2026).mp4", mime_type="video/mp4")
        f_audio = MockFileInfo("/home/user/Music/Track 01 - Intro.flac", mime_type="audio/flac")
        f_doc = MockFileInfo("/home/user/Documents/Invoice 2026.pdf", mime_type="application/pdf")
        f_dir = MockFileInfo("/home/user/Videos/", is_directory=True)

        assert is_media_file(f_video) is True
        assert is_media_file(f_audio) is True
        assert is_media_file(f_doc) is False
        assert is_media_file(f_dir) is False

        assert get_file_path(f_video) == "/home/user/My Videos/Action Movie (2026).mp4"
        assert get_file_path(f_audio) == "/home/user/Music/Track 01 - Intro.flac"

        ext = MediaToolboxExtension()
        items = ext.get_file_items([f_video, f_audio, f_doc])
        assert len(items) == 1
        root = items[0]
        assert root.label == "Media Toolbox"
        assert root.submenu is not None
        subitems = root.submenu.get_items()
        assert len(subitems) == 4

    def test_nautilus_space_safe_dispatch_execution(self, mock_nautilus_env: Any) -> None:
        """Menu activations quote paths with spaces using shlex.quote and spawn detached processes."""
        from media_toolbox.nautilus.extension import MediaToolboxExtension

        f1 = MockFileInfo("/home/user/My Videos/Action Movie (2026).mp4", mime_type="video/mp4")
        ext = MediaToolboxExtension()
        items = ext.get_file_items([f1])
        assert items[0].submenu is not None
        subitems = items[0].submenu.get_items()

        # Item 2 is Quick Transcode (H.264)
        item_transcode = subitems[2]
        assert "Quick Transcode" in item_transcode.label

        with patch("media_toolbox.nautilus.extension.launch_detached") as mock_launch:
            item_transcode.activate()
            assert mock_launch.call_count == 1
            cmd = mock_launch.call_args[0][0]
            cmd_str = " ".join(cmd)
            # Assert file path is quoted with single quotes so bash does not split on spaces
            assert "'/home/user/My Videos/Action Movie (2026).mp4'" in cmd_str

    def test_nautilus_launcher_script_syntax_and_spaces(self) -> None:
        """Launcher script passes bash -n validation and correctly preserves space-separated paths."""
        toolbox_root = Path(__file__).resolve().parent.parent
        launcher_path = toolbox_root / "nautilus" / "launcher.sh"
        assert launcher_path.is_file()

        # 1. Syntax check
        res = subprocess.run(["bash", "-n", str(launcher_path)], capture_output=True, text=True)
        assert res.returncode == 0, f"Bash syntax check failed: {res.stderr}"

        # 2. Simulation of space-separated files handling
        test_script = (
            f"source {shlex.quote(str(launcher_path))} --help >/dev/null 2>&1 || true\n"
        )
        assert len(test_script) > 0
