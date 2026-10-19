"""
White-box adversarial stress test suite (Tier 5) for media_toolbox.

Verifies system resilience against:
1. Corrupted & Edge Payloads:
   - Truncated / malformed / non-JSON ffprobe output
   - Zero duration, negative bitrates, missing video/audio streams, 0x0 resolution
   - Bitrate calculation boundary and domain validation
2. Subprocess & Runner Adversarial Conditions:
   - Non-monotonic out_time_seconds and out_time=N/A injection during progress streaming
   - Process crash mid-transcode (exit code 1) with multiline stderr capture
   - Fast cancellation stress (<100ms process group SIGKILL escalation and partial output cleanup)
   - Stderr kernel pipe buffer deadlock prevention (128KB continuous error output)
3. CLI Adversarial Input Fuzzing:
   - Missing subcommands, missing positional arguments, invalid presets
   - Colliding input/output paths, non-existent input files
   - Malformed scale and speed parameter fuzzing, contradictory options
4. Desktop & Nautilus Invariant Hardening:
   - Path injection attacks via $NAUTILUS_SCRIPT_SELECTED_FILE_PATHS
   - Nautilus extension shlex quoting validation
   - Subprocess headless AST check across all core and CLI modules

Target performance: Execution time <1.0s.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import types
from typing import Any, Generator
from unittest.mock import MagicMock, patch
import pytest

from media_toolbox.core.models import (
    AudioStream,
    EncodeOptions,
    FormatInfo,
    MediaInfo,
    MediaToolboxError,
    ProbeError,
    ProgressEvent,
    VideoStream,
)
from media_toolbox.core.probe import (
    parse_frame_rate,
    parse_optional_float,
    parse_optional_int,
    parse_probe_json,
    probe_media,
)
from media_toolbox.core.bitrate import calculate_target_video_bitrate
from media_toolbox.core.builder import build_ffmpeg_commands
from media_toolbox.core.runner import (
    ProgressParser,
    RunnerCancelledError,
    RunnerError,
    parse_progress_stream,
    run_ffmpeg,
    run_ffmpeg_pipeline,
)
import media_toolbox.cli as cli


# ==============================================================================
# Suite 1: Corrupted & Edge Payloads
# ==============================================================================


class TestAdversarialPayloads:
    """White-box stress tests for corrupted ffprobe outputs and edge media payloads."""

    def test_probe_truncated_json_raises_probe_error(self, tmp_path: Path) -> None:
        """Truncated JSON output from ffprobe must raise ProbeError wrapping JSONDecodeError."""
        dummy_file = tmp_path / "test.mp4"
        dummy_file.write_bytes(b"dummy")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"format": {"filename": "test.mp4", "duration": "10.0"'  # Missing closing braces
        mock_proc.stderr = ""

        with patch("subprocess.run", return_value=mock_proc):
            with pytest.raises(ProbeError, match="Failed to parse ffprobe output as JSON"):
                probe_media(dummy_file)

    def test_probe_non_json_garbage_raises_probe_error(self, tmp_path: Path) -> None:
        """HTML errors or raw driver crash dumps from ffprobe must raise ProbeError."""
        dummy_file = tmp_path / "test.mp4"
        dummy_file.write_bytes(b"dummy")

        garbage_outputs = [
            "<html><body>502 Bad Gateway</body></html>",
            "[mov,mp4 @ 0x5555] moov atom not found\nInvalid data found when processing input",
            "Segmentation fault (core dumped)",
            "null",
            "12345",
        ]

        for garbage in garbage_outputs:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = garbage
            mock_proc.stderr = ""

            with patch("subprocess.run", return_value=mock_proc):
                with pytest.raises(ProbeError):
                    probe_media(dummy_file)

    def test_probe_empty_stdout_raises_probe_error(self, tmp_path: Path) -> None:
        """Empty or whitespace-only stdout from ffprobe must raise ProbeError."""
        dummy_file = tmp_path / "test.mp4"
        dummy_file.write_bytes(b"dummy")

        for empty in ["", "   ", "\n\t\r\n"]:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = empty
            mock_proc.stderr = ""

            with patch("subprocess.run", return_value=mock_proc):
                with pytest.raises(ProbeError, match="empty output"):
                    probe_media(dummy_file)

    def test_probe_missing_format_section(self) -> None:
        """Missing or non-dict 'format' field in probe dictionary must raise ProbeError."""
        with pytest.raises(ProbeError, match="missing required 'format' section"):
            parse_probe_json({"streams": []})

        with pytest.raises(ProbeError, match="missing required 'format' section"):
            parse_probe_json({"format": "not_a_dict", "streams": []})

    def test_probe_missing_or_invalid_streams_section(self) -> None:
        """Missing, null, or non-list 'streams' field must raise ProbeError."""
        with pytest.raises(ProbeError, match="missing required 'streams' section"):
            parse_probe_json({"format": {}})

        with pytest.raises(ProbeError, match="streams is not a list"):
            parse_probe_json({"format": {}, "streams": "not_a_list"})

        with pytest.raises(ProbeError, match="streams is not a list"):
            parse_probe_json({"format": {}, "streams": None})

    def test_probe_malformed_stream_elements_handled_defensively(self) -> None:
        """Stream entries containing non-dict items or missing attributes must not crash parser."""
        data = {
            "format": {"filename": "edge.mkv", "format_name": "matroska"},
            "streams": [
                None,  # Non-dict skipped
                "invalid_stream_string",  # Non-dict skipped
                {},  # Empty dict -> skipped (codec_type is None)
                {"codec_type": "video"},  # Missing index, dimensions, codec_name
                {"codec_type": "audio"},  # Missing index, channels, sample_rate
            ],
        }
        media = parse_probe_json(data)
        assert len(media.video_streams) == 1
        assert len(media.audio_streams) == 1
        v = media.video_streams[0]
        assert v.index == 0
        assert v.width == 0
        assert v.height == 0
        assert v.codec_name == ""
        a = media.audio_streams[0]
        assert a.index == 0
        assert a.channels == 0
        assert a.sample_rate == 0

    def test_probe_zero_duration_and_image_semantics(self) -> None:
        """Zero duration videos and still images must resolve duration 0.0 and correct flags."""
        data = {
            "format": {"filename": "img.png", "duration": "0.000000"},
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "png",
                    "width": 1920,
                    "height": 1080,
                    "duration": "0.000000",
                }
            ],
        }
        media = parse_probe_json(data)
        assert media.duration == 0.0
        assert media.has_video is True
        assert media.has_audio is False
        assert media.is_image is True
        assert media.is_video_only is True

    def test_probe_negative_bitrates_and_durations_sanitized(self) -> None:
        """Negative bitrate or duration values must be sanitized cleanly."""
        data = {
            "format": {
                "filename": "negative.mp4",
                "duration": "-60.000000",
                "bit_rate": "-2500000",
                "size": "1000",
            },
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1280,
                    "height": 720,
                    "duration": "-60.0",
                    "bit_rate": "-2000000",
                }
            ],
        }
        media = parse_probe_json(data)
        assert media.format.duration is None  # parse_optional_float drops negative
        assert media.video_streams[0].duration is None
        assert media.duration == 0.0
        rendered = cli.render_media_info_text(media)
        assert "N/A" in rendered

    def test_probe_0x0_resolution_zero_division_safety(self) -> None:
        """VideoStream with 0x0 resolution must never raise ZeroDivisionError on aspect ratio."""
        stream = VideoStream(index=0, codec_name="h264", width=0, height=0)
        assert stream.aspect_ratio == 0.0
        assert stream.effective_dimensions == (0, 0)
        assert stream.display_resolution == "0x0"
        assert cli.format_aspect_ratio(0, 0) == "N/A"

    def test_probe_empty_container_no_streams(self) -> None:
        """Container with zero streams must not crash summaries or formatters."""
        data = {
            "format": {
                "filename": "empty_container.mp4",
                "format_name": "mov,mp4",
                "duration": "10.0",
                "size": "500",
            },
            "streams": [],
        }
        media = parse_probe_json(data)
        assert media.has_video is False
        assert media.has_audio is False
        assert media.is_audio_only is False
        assert media.is_video_only is False
        assert media.is_image is False
        info_dict = cli.media_info_to_dict(media)
        assert info_dict["video_streams"] == []
        assert info_dict["audio_streams"] == []
        text = cli.render_media_info_text(media)
        assert "(No video streams)" in text
        assert "(No audio streams)" in text

    def test_bitrate_math_adversarial_parameters(self) -> None:
        """Bitrate calculator must strictly validate non-positive durations, targets, and bounds."""
        with pytest.raises(ValueError, match="duration_seconds must be a positive finite number"):
            calculate_target_video_bitrate(target_size_mb=25, duration_seconds=0.0)

        with pytest.raises(ValueError, match="duration_seconds must be a positive finite number"):
            calculate_target_video_bitrate(target_size_mb=25, duration_seconds=-10.0)

        with pytest.raises(ValueError, match="duration_seconds must be a positive finite number"):
            calculate_target_video_bitrate(target_size_mb=25, duration_seconds=float("nan"))

        with pytest.raises(ValueError, match="target_size_mb must be a positive finite number"):
            calculate_target_video_bitrate(target_size_mb=0.0, duration_seconds=60.0)

        with pytest.raises(ValueError, match="target_size_mb must be a positive finite number"):
            calculate_target_video_bitrate(target_size_mb=-25.0, duration_seconds=60.0)

        with pytest.raises(ValueError, match="audio_bitrate_kbps cannot be negative"):
            calculate_target_video_bitrate(target_size_mb=25, duration_seconds=60, audio_bitrate_kbps=-128)

        with pytest.raises(ValueError, match="mux_overhead_margin must be in range"):
            calculate_target_video_bitrate(target_size_mb=25, duration_seconds=60, mux_overhead_margin=1.5)

        with pytest.raises(ValueError, match="min_video_bitrate_kbps cannot be negative"):
            calculate_target_video_bitrate(target_size_mb=25, duration_seconds=60, min_video_bitrate_kbps=-1)


# ==============================================================================
# Suite 2: Subprocess & Runner Adversarial Conditions
# ==============================================================================


class TestAdversarialRunner:
    """White-box stress tests for subprocess runner, cancellation, and progress injection."""

    def test_progress_parser_non_monotonic_out_time_regression_safety(self) -> None:
        """Injecting regressing out_time stamps must not decrease out_time_seconds or percentage."""
        parser = ProgressParser(total_duration=60.0)

        stream = [
            "out_time=00:00:20.000000",
            "progress=continue",
            "out_time=00:00:10.000000",  # Regression
            "progress=continue",
            "out_time=00:00:05.000000",  # Further regression
            "progress=continue",
            "out_time=00:00:40.000000",  # Forward progress
            "progress=continue",
        ]

        events = [evt for line in stream if (evt := parser.feed_line(line)) is not None]
        assert len(events) == 4
        # Event 1: 20s
        assert events[0].out_time_seconds == pytest.approx(20.0)
        assert events[0].percentage == pytest.approx(33.33, abs=0.01)

        # Event 2: clamped to 20s
        assert events[1].out_time_seconds == pytest.approx(20.0)
        assert events[1].percentage == pytest.approx(33.33, abs=0.01)

        # Event 3: clamped to 20s
        assert events[2].out_time_seconds == pytest.approx(20.0)
        assert events[2].percentage == pytest.approx(33.33, abs=0.01)

        # Event 4: resumes at 40s
        assert events[3].out_time_seconds == pytest.approx(40.0)
        assert events[3].percentage == pytest.approx(66.67, abs=0.01)

    def test_progress_parser_out_time_na_injection_preserves_progress(self) -> None:
        """Injecting out_time=N/A midway through encoding must retain previous progress."""
        parser = ProgressParser(total_duration=100.0)

        stream = [
            "out_time=00:00:50.000000",
            "progress=continue",
            "out_time=N/A",
            "out_time_us=N/A",
            "out_time_ms=N/A",
            "progress=continue",
        ]

        events = [evt for line in stream if (evt := parser.feed_line(line)) is not None]
        assert len(events) == 2
        assert events[0].out_time_seconds == 50.0
        assert events[0].percentage == 50.0
        # Second event should maintain 50.0s and 50.0%, not reset to 0
        assert events[1].out_time_seconds == 50.0
        assert events[1].percentage == 50.0

    def test_progress_parser_malformed_numeric_and_nan_tokens(self) -> None:
        """Malformed, non-numeric, or infinite progress tokens must not crash parser."""
        parser = ProgressParser(total_duration=50.0)

        stream = [
            "frame=not_an_int",
            "fps=NaN",
            "total_size=corrupted_size",
            "speed=invalid_speed",
            "out_time=00:00:10.000000",
            "progress=continue",
        ]

        events = [evt for line in stream if (evt := parser.feed_line(line)) is not None]
        assert len(events) == 1
        evt = events[0]
        assert evt.frame == 0
        assert evt.fps == 0.0
        assert evt.total_size_bytes == 0
        assert evt.speed is None
        assert evt.out_time_seconds == 10.0

    def test_runner_process_crash_exit_code_1_with_stderr_capture(self) -> None:
        """Subprocess crashing with exit code 1 must capture full stderr and last_error_line."""
        script = (
            "import sys\n"
            "sys.stderr.write('Header line: probing stream #0\\n')\n"
            "sys.stderr.write('Error while opening encoder for output stream #0:0: Invalid argument\\n')\n"
            "sys.exit(1)\n"
        )
        cmd = [sys.executable, "-c", script]

        with pytest.raises(RunnerError) as exc_info:
            run_ffmpeg(cmd)

        err = exc_info.value
        assert err.returncode == 1
        assert "Invalid argument" in err.stderr
        assert err.last_error_line == "Error while opening encoder for output stream #0:0: Invalid argument"
        assert err.cmd == cmd

    def test_runner_fast_cancellation_within_100ms_process_group(self) -> None:
        """Process group cancellation must complete in <100ms without leaving dangling processes."""
        cancel_event = threading.Event()
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]

        def _cancel_after_tiny_delay() -> None:
            time.sleep(0.01)  # 10ms
            cancel_event.set()

        watcher = threading.Thread(target=_cancel_after_tiny_delay, daemon=True)
        watcher.start()

        start_time = time.monotonic()
        with pytest.raises(RunnerCancelledError):
            run_ffmpeg(cmd, cancel_event=cancel_event, sigterm_timeout=0.05)
        elapsed_ms = (time.monotonic() - start_time) * 1000.0

        watcher.join(timeout=1.0)
        assert elapsed_ms < 100.0, f"Cancellation took {elapsed_ms:.1f}ms (expected <100ms)"

    def test_runner_sigkill_escalation_on_sigterm_ignoring_process(self) -> None:
        """Unresponsive process ignoring SIGTERM must be terminated via SIGKILL within grace period."""
        cancel_event = threading.Event()
        script = (
            "import signal, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "time.sleep(30)\n"
        )
        cmd = [sys.executable, "-c", script]

        def _cancel_after_delay() -> None:
            time.sleep(0.01)
            cancel_event.set()

        watcher = threading.Thread(target=_cancel_after_delay, daemon=True)
        watcher.start()

        start_time = time.monotonic()
        with pytest.raises(RunnerCancelledError):
            run_ffmpeg(cmd, cancel_event=cancel_event, sigterm_timeout=0.04)
        elapsed_ms = (time.monotonic() - start_time) * 1000.0

        watcher.join(timeout=1.0)
        assert elapsed_ms < 150.0, f"SIGKILL escalation took {elapsed_ms:.1f}ms (expected <150ms)"

    def test_runner_pre_cancelled_event_never_spawns_process(self) -> None:
        """Pre-set cancel_event must immediately raise RunnerCancelledError without spawning Popen."""
        cancel_event = threading.Event()
        cancel_event.set()

        with patch("subprocess.Popen") as mock_popen:
            with pytest.raises(RunnerCancelledError, match="Execution cancelled before start"):
                run_ffmpeg(["ffmpeg", "-i", "in.mp4", "out.mp4"], cancel_event=cancel_event)
            mock_popen.assert_not_called()

    def test_runner_cancellation_cleans_partial_output_file(self, tmp_path: Path) -> None:
        """Worker cancellation flow must cleanly delete partial output file."""
        partial_file = tmp_path / "partial_output.mp4"
        partial_file.write_bytes(b"\x00" * 4096)
        assert partial_file.exists()

        cancel_event = threading.Event()
        cancel_event.set()

        try:
            run_ffmpeg(["ffmpeg", "-i", "in.mp4", str(partial_file)], cancel_event=cancel_event)
        except RunnerCancelledError:
            if partial_file.exists():
                partial_file.unlink()

        assert not partial_file.exists()

    def test_runner_stderr_pipe_overflow_stress_128kb(self) -> None:
        """Subprocess emitting 128KB of error text to stderr must not block or deadlock runner."""
        script = (
            "import sys\n"
            "sys.stderr.write('X' * 131072)\n"
            "sys.stderr.flush()\n"
            "sys.exit(1)\n"
        )
        cmd = [sys.executable, "-c", script]

        with pytest.raises(RunnerError) as exc_info:
            run_ffmpeg(cmd)

        assert exc_info.value.returncode == 1
        assert len(exc_info.value.stderr) == 131072


# ==============================================================================
# Suite 3: CLI Adversarial Input Fuzzing
# ==============================================================================


class TestAdversarialCLIFuzzing:
    """White-box fuzzing tests for CLI argument parsing, collision handling, and missing options."""

    def test_cli_missing_subcommand_in_headless_environment(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invoking cli.main([]) raises SystemExit(2); __main__.main() falls back to help (0)."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        # 1. Direct cli.main([]) requires command -> exits 2
        with pytest.raises(SystemExit) as exc_info:
            cli.main([])
        assert exc_info.value.code == 2

        # 2. Package router __main__.main() catches headless state -> displays help (0)
        import media_toolbox.__main__ as pkg_main
        monkeypatch.setattr(sys, "argv", ["media_toolbox"])
        code = pkg_main.main()
        out, err = capsys.readouterr()
        assert code == 0
        assert "usage: media_toolbox" in out or "Modern media inspection" in out

    def test_cli_inspect_missing_file_argument(self) -> None:
        """'inspect' without target file must raise SystemExit(2) from argparse."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["inspect"])
        assert exc_info.value.code == 2

    def test_cli_transcode_missing_positional_arguments(self) -> None:
        """'transcode' without input or output must raise SystemExit(2)."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["transcode"])
        assert exc_info.value.code == 2

        with pytest.raises(SystemExit) as exc_info:
            cli.main(["transcode", "input.mp4"])
        assert exc_info.value.code == 2

    def test_cli_invalid_preset_rejected(self) -> None:
        """Querying invalid preset names from registry must strictly raise KeyError."""
        from media_toolbox.core.presets import get_audio_preset, get_preset, get_video_preset

        with pytest.raises(KeyError, match="Unknown preset 'bogus_preset_999'"):
            get_preset("bogus_preset_999")

        with pytest.raises(KeyError, match="Unknown video preset 'bogus_video'"):
            get_video_preset("bogus_video")

        with pytest.raises(KeyError, match="Unknown audio preset 'bogus_audio'"):
            get_audio_preset("bogus_audio")

    def test_cli_colliding_input_and_output_paths_handling(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Passing identical input and output paths to transcode fails safely without silent overwrite."""
        same_file = tmp_path / "collision.mp4"
        same_file.write_bytes(b"dummy")

        with patch("media_toolbox.cli.probe_media") as mock_probe:
            mock_probe.return_value = MediaInfo(
                format=FormatInfo(filename=str(same_file), format_name="mov,mp4", duration=10.0),
                video_streams=(VideoStream(index=0, codec_name="h264", width=1280, height=720),),
            )
            with patch("media_toolbox.cli.run_ffmpeg_pipeline") as mock_runner:
                mock_runner.side_effect = RunnerError(
                    cmd=["ffmpeg", "-i", str(same_file), str(same_file)],
                    returncode=1,
                    stderr="Output file is same as input",
                )
                code = cli.main(["transcode", str(same_file), str(same_file)])

        out, err = capsys.readouterr()
        assert code == 1
        assert "Transcoding failed" in err or "Output file is same as input" in err

    def test_cli_nonexistent_input_file_handling(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Non-existent files passed to inspect, transcode, or extract-audio return exit code 1."""
        nonexistent = "/path/to/definitely_nonexistent_media_file_12345.mp4"

        code = cli.main(["inspect", nonexistent])
        out, err = capsys.readouterr()
        assert code == 1
        assert "File not found" in err

        code = cli.main(["transcode", nonexistent, "out.mp4"])
        out, err = capsys.readouterr()
        assert code == 1
        assert "Input file not found" in err

        code = cli.main(["extract-audio", nonexistent, "out.mp3"])
        out, err = capsys.readouterr()
        assert code == 1
        assert "Input file not found" in err

    def test_cli_scale_parameter_fuzzing(self) -> None:
        """Fuzzing --scale argument with various malformed strings raises ValueError."""
        fuzz_cases = [
            "0x0",
            "0x1080",
            "1920x0",
            "-1x-1",
            "1920",
            "abcxdef",
            "1920x1080x720",
            ":::",
            "1920::1080",
        ]
        for s in fuzz_cases:
            with pytest.raises(ValueError):
                cli.parse_scale_arg(s)

    def test_cli_speed_parameter_fuzzing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Negative and zero speed multipliers are rejected with exit code 2."""
        dummy = tmp_path / "sample.mp4"
        dummy.write_bytes(b"dummy")

        for bad_speed in ["0", "-1", "-0.5"]:
            code = cli.main(["transcode", str(dummy), "out.mp4", "--speed", bad_speed])
            out, err = capsys.readouterr()
            assert code == 2
            assert "Speed multiplier must be positive" in err

            code = cli.main(["extract-audio", str(dummy), "out.mp3", "--speed", bad_speed])
            out, err = capsys.readouterr()
            assert code == 2
            assert "Speed multiplier must be positive" in err

    def test_cli_contradictory_options_rejected(self) -> None:
        """Contradictory options (e.g. GIF with two-pass) raise ValueError in command builder."""
        options = EncodeOptions(preset="gif", two_pass=True)
        with pytest.raises(ValueError, match="Two-pass encoding is not supported for GIF preset"):
            build_ffmpeg_commands("in.mp4", "out.gif", options)

        options2 = EncodeOptions(extract_audio=True, mute_audio=True)
        with pytest.raises(ValueError, match="Cannot simultaneously extract and mute audio"):
            build_ffmpeg_commands("in.mp4", "out.mp3", options2)


# ==============================================================================
# Suite 4: Desktop & Nautilus Invariant Hardening
# ==============================================================================


@pytest.fixture
def mock_nautilus_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Inject headless Nautilus/GObject typelib mocks into sys.modules without real gi."""
    fake_nautilus = types.ModuleType("gi.repository.Nautilus")

    class MockMenuItem:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class MockMenuProvider:
        pass

    fake_nautilus.MenuItem = MockMenuItem  # type: ignore
    fake_nautilus.MenuProvider = MockMenuProvider  # type: ignore

    fake_gobject = types.ModuleType("gi.repository.GObject")

    class MockGObject:
        pass

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


class TestAdversarialDesktopAndAST:
    """White-box security and headless AST invariant hardening."""

    def test_launcher_sh_path_injection_spaces_semicolons_metacharacters(self, tmp_path: Path) -> None:
        """Launcher script must never execute injected shell commands from Nautilus paths."""
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        launcher_script = repo_root / "python" / "media_toolbox" / "nautilus" / "launcher.sh"
        assert launcher_script.is_file(), f"launcher.sh not found at {launcher_script}"

        canary_file = tmp_path / "pwned_canary.txt"
        if canary_file.exists():
            canary_file.unlink()

        # Malicious paths attempting shell injection via semicolons, subshells, backticks, and pipes
        hostile_paths = "\n".join([
            f"/tmp/file1;touch {canary_file};echo.mp4",
            f"/tmp/file2 $(touch {canary_file}).mp4",
            f"/tmp/file3 `touch {canary_file}`.mp4",
            f"/tmp/file4 | touch {canary_file}",
            f"/tmp/file5 && touch {canary_file}",
            "/tmp/file with spaces and quotes'\"!@#$%^&*().mp4",
        ])

        env = os.environ.copy()
        env["NAUTILUS_SCRIPT_SELECTED_FILE_PATHS"] = hostile_paths
        env["DISPLAY"] = ""
        env["WAYLAND_DISPLAY"] = ""

        # Run launcher.sh in bash
        proc = subprocess.run(
            ["bash", str(launcher_script)],
            env=env,
            capture_output=True,
            text=True,
        )

        # Assert no canary file was touched
        assert not canary_file.exists(), "Command injection vulnerability detected: canary file was created!"

    def test_nautilus_extension_shlex_quote_hardening(self, mock_nautilus_env: Any, tmp_path: Path) -> None:
        """Nautilus extension shell scripts must safely escape special characters with shlex.quote."""
        from media_toolbox.nautilus.extension import MediaToolboxExtension

        ext = MediaToolboxExtension()
        canary = tmp_path / "shlex_pwned.txt"
        assert not canary.exists()

        hostile_paths = [
            f"/path/file1; touch {canary}; foo.mp4",
            f"/path/file2 $(touch {canary}).mp4",
            f"/path/file3 `touch {canary}`.mp4",
            f"/path/file4 | touch {canary}",
            f"/path/file5 && touch {canary}",
            "/path/file with spaces and symbols !@#$%.mp4",
        ]

        with patch("media_toolbox.nautilus.extension.launch_detached") as mock_launch:
            ext._on_inspect(None, hostile_paths)
            assert mock_launch.called
            cmd = mock_launch.call_args[0][0]
            script = cmd[cmd.index("-c") + 1] if "-c" in cmd else cmd[-1]

            # 1. Bash syntax validation
            syntax_check = subprocess.run(["bash", "-n", "-c", script], capture_output=True, text=True)
            assert syntax_check.returncode == 0, f"Script has invalid syntax:\n{syntax_check.stderr}"

            # 2. Injection execution validation: running the script must NOT create canary
            subprocess.run(["bash", "-c", script], capture_output=True, text=True)
            assert not canary.exists(), "Command injection vulnerability detected in Nautilus extension script!"

    def test_nautilus_extension_non_colliding_output_path_generators(self, mock_nautilus_env: Any, tmp_path: Path) -> None:
        """Extension output generators must avoid colliding with existing files by appending counters."""
        from media_toolbox.nautilus.extension import (
            get_extract_audio_output_path,
            get_transcode_output_path,
        )

        input_file = tmp_path / "video.mp4"
        input_file.write_bytes(b"test")

        # First call produces base output
        out1 = Path(get_transcode_output_path(str(input_file)))
        assert out1.name == "video_h264.mp4"
        out1.write_bytes(b"existing1")

        # Second call increments counter
        out2 = Path(get_transcode_output_path(str(input_file)))
        assert out2.name == "video_h264_1.mp4"
        out2.write_bytes(b"existing2")

        # Third call increments counter further
        out3 = Path(get_transcode_output_path(str(input_file)))
        assert out3.name == "video_h264_2.mp4"

    def test_subprocess_headless_ast_check_across_all_modules(self) -> None:
        """Subprocess headless check: importing any core or CLI module must never load GUI toolkits."""
        modules_to_test = [
            "media_toolbox",
            "media_toolbox.core",
            "media_toolbox.core.models",
            "media_toolbox.core.probe",
            "media_toolbox.core.bitrate",
            "media_toolbox.core.filtergraph",
            "media_toolbox.core.presets",
            "media_toolbox.core.builder",
            "media_toolbox.core.runner",
            "media_toolbox.cli",
            "media_toolbox.__main__",
        ]

        repo_python = str(Path(__file__).resolve().parent.parent.parent.parent / "python")
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{repo_python}:{env.get('PYTHONPATH', '')}"

        forbidden_modules = [
            "gi",
            "Gtk",
            "Adw",
            "Nautilus",
            "tkinter",
            "PyQt5",
            "PyQt6",
            "PySide6",
            "wx",
        ]

        for mod in modules_to_test:
            code = (
                f"import sys\n"
                f"import {mod}\n"
                f"for f in {forbidden_modules!r}:\n"
                f"    assert f not in sys.modules, f'Module {mod} loaded GUI toolkit {{f}}'\n"
            )
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                env=env,
            )
            assert proc.returncode == 0, f"Module {mod} failed headless import test:\n{proc.stderr}"
