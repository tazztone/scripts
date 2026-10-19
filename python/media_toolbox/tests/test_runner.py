"""
Unit tests for FFmpeg subprocess runner and progress streaming (core/runner.py).

Verifies:
- Stateful and streaming progress stream parsing (-progress pipe:1)
- Microsecond time conversion (out_time_us, out_time_ms, out_time)
- Speed factor parsing and 'N/A' handling
- Percentage clamping and unknown/zero duration fallbacks
- ETA estimation calculation
- Subprocess execution and typed ProgressEvent emission
- Non-blocking process group cancellation (SIGTERM and SIGKILL escalation)
- Error capturing and typed RunnerError with command, exit code, and stderr
- Multi-pass pipeline execution and scaled progress reporting
- Headless AST invariant (zero GUI imports in core/runner.py)
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import threading
import time
from typing import Any
from unittest.mock import MagicMock, patch
import pytest

from media_toolbox.core.models import MediaToolboxError, ProgressEvent
from media_toolbox.core.runner import (
    ProgressParser,
    RunnerCancelledError,
    RunnerError,
    calculate_eta_seconds,
    calculate_percentage,
    parse_progress_stream,
    parse_speed,
    parse_time_to_seconds,
    run_command,
    run_ffmpeg,
    run_ffmpeg_pipeline,
    terminate_process_group,
)


# ---------------------------------------------------------------------------
# Test Suite 1: Pure Parsing & Time Conversion Math
# ---------------------------------------------------------------------------


class TestProgressParserUnits:
    """Test suite verifying pure parsing helpers and math calculations."""

    def test_parse_speed_valid(self) -> None:
        assert parse_speed("1.0x") == 1.0
        assert parse_speed(" 2.50x ") == 2.50
        assert parse_speed("60.6x") == 60.6
        assert parse_speed("0x") == 0.0
        assert parse_speed("0.00x") == 0.0

    def test_parse_speed_na_and_malformed(self) -> None:
        assert parse_speed("N/A") is None
        assert parse_speed("  n/a  ") is None
        assert parse_speed("") is None
        assert parse_speed(None) is None
        assert parse_speed("invalid_speed") is None
        assert parse_speed("-1.5x") is None

    def test_parse_time_to_seconds_out_time_us(self) -> None:
        assert parse_time_to_seconds(out_time_us="4000000") == 4.0
        assert parse_time_to_seconds(out_time_us="60000000") == 60.0
        assert parse_time_to_seconds(out_time_us="500000") == 0.5

    def test_parse_time_to_seconds_out_time_ms_microsecond_quirk(self) -> None:
        # FFmpeg emits out_time_ms in microseconds
        assert parse_time_to_seconds(out_time_ms="2000000") == 2.0
        assert parse_time_to_seconds(out_time_ms="1234567") == pytest.approx(1.234567)

    def test_parse_time_to_seconds_formatted_out_time(self) -> None:
        assert parse_time_to_seconds(out_time_str="00:01:30.500000") == pytest.approx(90.5)
        assert parse_time_to_seconds(out_time_str="01:00:00.000000") == pytest.approx(3600.0)
        assert parse_time_to_seconds(out_time_str="02:15.000000") == pytest.approx(135.0)
        assert parse_time_to_seconds(out_time_str="45.5") == pytest.approx(45.5)

    def test_parse_time_to_seconds_negative_and_na(self) -> None:
        assert parse_time_to_seconds(out_time_us="-1000000") == 0.0
        assert parse_time_to_seconds(out_time_str="-00:00:01.000000") == 0.0
        assert parse_time_to_seconds(out_time_us="N/A", out_time_ms="N/A") == 0.0

    def test_calculate_percentage_normal(self) -> None:
        assert calculate_percentage(30.0, 60.0) == 50.0
        assert calculate_percentage(60.0, 60.0) == 100.0
        assert calculate_percentage(0.0, 60.0) == 0.0

    def test_calculate_percentage_clamping(self) -> None:
        # Clamped to 100.0 on slight overshoot
        assert calculate_percentage(61.5, 60.0) == 100.0
        # Clamped to 0.0 on negative values
        assert calculate_percentage(-5.0, 60.0) == 0.0

    def test_calculate_percentage_unknown_duration(self) -> None:
        assert calculate_percentage(30.0, None) == 0.0
        assert calculate_percentage(30.0, 0.0) == 0.0
        assert calculate_percentage(30.0, -10.0) == 0.0
        # When completed, percentage is 100.0 even without duration
        assert calculate_percentage(30.0, None, is_completed=True) == 100.0

    def test_calculate_eta_seconds_normal(self) -> None:
        # 30 seconds remaining at 2.0x speed = 15.0 seconds
        assert calculate_eta_seconds(30.0, 60.0, 2.0) == 15.0
        # 45 seconds remaining at 1.5x speed = 30.0 seconds
        assert calculate_eta_seconds(15.0, 60.0, 1.5) == 30.0

    def test_calculate_eta_seconds_edge_cases(self) -> None:
        # None when speed or duration unknown
        assert calculate_eta_seconds(30.0, 60.0, None) is None
        assert calculate_eta_seconds(30.0, 60.0, 0.0) is None
        assert calculate_eta_seconds(30.0, None, 2.0) is None
        assert calculate_eta_seconds(30.0, 0.0, 2.0) is None
        # 0.0 when completed or past duration
        assert calculate_eta_seconds(30.0, 60.0, 2.0, is_completed=True) == 0.0
        assert calculate_eta_seconds(65.0, 60.0, 2.0) == 0.0


# ---------------------------------------------------------------------------
# Test Suite 2: Stateful ProgressParser & Stream Chunks
# ---------------------------------------------------------------------------


class TestProgressParserStream:
    """Test suite verifying ProgressParser state transitions and synthetic chunks."""

    def test_parser_complete_stream(self) -> None:
        lines = [
            "frame=30\n",
            "fps=29.97\n",
            "stream_0_0_q=28.0\n",
            "bitrate= 1500.0kbits/s\n",
            "total_size=1048576\n",
            "out_time_us=10000000\n",
            "out_time_ms=10000000\n",
            "out_time=00:00:10.000000\n",
            "dup_frames=0\n",
            "drop_frames=0\n",
            "speed= 2.00x\n",
            "progress=continue\n",
            "frame=60\n",
            "fps=30.0\n",
            "stream_0_0_q=28.0\n",
            "bitrate= 1500.0kbits/s\n",
            "total_size=2097152\n",
            "out_time_us=20000000\n",
            "out_time_ms=20000000\n",
            "out_time=00:00:20.000000\n",
            "dup_frames=0\n",
            "drop_frames=0\n",
            "speed= 2.00x\n",
            "progress=end\n",
        ]
        events = list(parse_progress_stream(lines, total_duration=20.0))
        assert len(events) == 2

        # Block 1
        ev1 = events[0]
        assert ev1.frame == 30
        assert ev1.fps == 29.97
        assert ev1.out_time_seconds == 10.0
        assert ev1.total_size_bytes == 1048576
        assert ev1.speed == 2.0
        assert ev1.percentage == 50.0
        assert ev1.eta_seconds == 5.0
        assert ev1.is_completed is False
        assert ev1.speed_str == "2.00x"
        assert ev1.eta_str == "00:05"

        # Block 2 (End)
        ev2 = events[1]
        assert ev2.frame == 60
        assert ev2.fps == 30.0
        assert ev2.out_time_seconds == 20.0
        assert ev2.total_size_bytes == 2097152
        assert ev2.percentage == 100.0
        assert ev2.eta_seconds == 0.0
        assert ev2.is_completed is True

    def test_parser_resilient_to_malformed_lines(self) -> None:
        parser = ProgressParser(total_duration=10.0)
        assert parser.feed_line("") is None
        assert parser.feed_line("    ") is None
        assert parser.feed_line("corrupt line without equals") is None
        assert parser.feed_line("key_with_multiple=equals=values") is None
        assert parser.feed_line("unknown_custom_key=value") is None
        assert parser.feed_line("frame=not_an_int") is None
        assert parser.feed_line("fps=not_a_float") is None
        assert parser.feed_line("out_time_us=not_time") is None
        assert parser.feed_line("progress=continue") is not None

    def test_parser_finish_fallback(self) -> None:
        parser = ProgressParser(total_duration=15.0)
        parser.feed_line("frame=10")
        parser.feed_line("out_time_us=5000000")
        parser.feed_line("progress=continue")
        # Final block did not have progress=end before stream EOF
        fin = parser.finish()
        assert fin is not None
        assert fin.is_completed is True
        assert fin.percentage == 100.0
        # Subsequent finish() returns None
        assert parser.finish() is None

    def test_parse_progress_stream_generator(self) -> None:
        stream = [
            "frame=5\n",
            "progress=continue\n",
            "frame=10\n",
            "progress=end\n",
        ]
        evts = list(parse_progress_stream(stream, total_duration=10.0))
        assert len(evts) == 2
        assert evts[0].frame == 5
        assert evts[1].frame == 10

    def test_progress_parser_monotonic_on_na_out_time_and_midstream_drops(self) -> None:
        """
        Verify ProgressParser maintains non-decreasing out_time_seconds and percentage
        when encountering out_time_us='N/A', out_time_ms='N/A', or out-of-order time drops mid-stream.
        """
        stream_lines = [
            # Block 1: Valid initial progress at 2.0s
            "frame=20\n",
            "fps=30.0\n",
            "out_time_us=2000000\n",
            "progress=continue\n",
            # Block 2: Multiplexer buffer delay emits N/A out_time_us
            "frame=35\n",
            "fps=30.0\n",
            "out_time_us=N/A\n",
            "progress=continue\n",
            # Block 3: Jitter / out-of-order drop (1.5s < 2.0s)
            "frame=40\n",
            "fps=30.0\n",
            "out_time_us=1500000\n",
            "progress=continue\n",
            # Block 4: Advances to 5.0s
            "frame=60\n",
            "fps=30.0\n",
            "out_time_us=5000000\n",
            "progress=continue\n",
            # Block 5: out_time_ms is N/A and out_time is empty
            "frame=70\n",
            "fps=30.0\n",
            "out_time_ms=N/A\n",
            "out_time=N/A\n",
            "progress=continue\n",
            # Block 6: Mid-stream drop to 3.0s
            "frame=80\n",
            "fps=30.0\n",
            "out_time_us=3000000\n",
            "progress=continue\n",
            # Block 7: Completion at 10.0s
            "frame=100\n",
            "fps=30.0\n",
            "out_time_us=10000000\n",
            "progress=end\n",
        ]

        parser = ProgressParser(total_duration=10.0)
        events: list[ProgressEvent] = []
        for line in stream_lines:
            evt = parser.feed_line(line)
            if evt is not None:
                events.append(evt)

        assert len(events) == 7

        times = [e.out_time_seconds for e in events]
        pcts = [e.percentage for e in events]

        # Invariant 1: out_time_seconds must be monotonically non-decreasing
        assert all(times[i] <= times[i + 1] for i in range(len(times) - 1)), (
            f"out_time_seconds decreased: {times}"
        )

        # Invariant 2: percentage must be monotonically non-decreasing
        assert all(pcts[i] <= pcts[i + 1] for i in range(len(pcts) - 1)), (
            f"percentage decreased: {pcts}"
        )

        # Exact expected values: prior high-water marks held during drops
        assert times[0] == 2.0
        assert times[1] == 2.0  # Held monotonic on N/A
        assert times[2] == 2.0  # Held monotonic on 1.5s drop
        assert times[3] == 5.0  # Advanced to 5.0s
        assert times[4] == 5.0  # Held monotonic on N/A
        assert times[5] == 5.0  # Held monotonic on 3.0s drop
        assert times[6] == 10.0  # Advanced to 10.0s
        assert events[-1].is_completed is True
        assert events[-1].percentage == 100.0

    def test_progress_parser_monotonic_generator_with_na(self) -> None:
        """Verify parse_progress_stream generator yields monotonic events through N/A blocks."""
        stream = [
            "frame=10\n",
            "out_time_us=3000000\n",
            "progress=continue\n",
            "frame=20\n",
            "out_time_us=N/A\n",
            "progress=continue\n",
            "frame=30\n",
            "out_time_us=6000000\n",
            "progress=end\n",
        ]
        evts = list(parse_progress_stream(stream, total_duration=6.0))
        assert len(evts) == 3
        times = [e.out_time_seconds for e in evts]
        assert times == [3.0, 3.0, 6.0]
        assert evts[1].percentage == 50.0  # Kept at 50%, not reset to 0%
        assert evts[2].percentage == 100.0

    def test_progress_parser_finish_monotonic_with_shorter_total_duration(self) -> None:
        """
        Verify finish() does not regress out_time_seconds if total_duration was smaller
        than already emitted out_time_seconds, or if total_duration was None.
        """
        # Case A: Media transcode exceeded estimated total_duration
        parser_short = ProgressParser(total_duration=5.0)
        parser_short.feed_line("frame=100")
        parser_short.feed_line("out_time_us=6200000")  # 6.2s emitted
        evt_mid = parser_short.feed_line("progress=continue")
        assert evt_mid is not None
        assert evt_mid.out_time_seconds == 6.2

        fin_short = parser_short.finish()
        assert fin_short is not None
        assert fin_short.is_completed is True
        assert fin_short.percentage == 100.0
        assert fin_short.eta_seconds == 0.0
        # Invariant: finish out_time must not regress to 5.0
        assert fin_short.out_time_seconds == 6.2

        # Case B: total_duration is None (unknown duration / live stream)
        parser_none = ProgressParser(total_duration=None)
        parser_none.feed_line("frame=50")
        parser_none.feed_line("out_time_us=4500000")  # 4.5s emitted
        parser_none.feed_line("progress=continue")

        fin_none = parser_none.finish()
        assert fin_none is not None
        assert fin_none.is_completed is True
        assert fin_none.percentage == 100.0
        # Invariant: finish out_time must not regress to 0.0
        assert fin_none.out_time_seconds == 4.5

        # Case C: Media completed normally before total_duration
        parser_normal = ProgressParser(total_duration=10.0)
        parser_normal.feed_line("frame=70")
        parser_normal.feed_line("out_time_us=7000000")  # 7.0s emitted
        parser_normal.feed_line("progress=continue")

        fin_normal = parser_normal.finish()
        assert fin_normal is not None
        # Invariant: finish advances to total_duration on completion
        assert fin_normal.out_time_seconds == 10.0
        assert fin_normal.percentage == 100.0


# ---------------------------------------------------------------------------
# Test Suite 3: Subprocess Execution & Mock Streaming
# ---------------------------------------------------------------------------


class TestRunFFmpegExecution:
    """Test suite executing isolated Python child processes to verify runner."""

    def test_run_ffmpeg_mock_stream(self) -> None:
        """Run subprocess emitting progress stream and capture ProgressEvents."""
        script = (
            "import sys, time\n"
            "print('frame=10\\nout_time_us=5000000\\nspeed=1.0x\\nprogress=continue', flush=True)\n"
            "time.sleep(0.01)\n"
            "print('frame=20\\nout_time_us=10000000\\nspeed=1.0x\\nprogress=end', flush=True)\n"
        )
        cmd = [sys.executable, "-c", script]
        events: list[ProgressEvent] = []

        run_ffmpeg(cmd, total_duration_seconds=10.0, progress_callback=events.append)

        assert len(events) >= 2
        assert events[0].frame == 10
        assert events[0].percentage == 50.0
        assert events[-1].percentage == 100.0
        assert events[-1].is_completed is True

    def test_run_command_alias_compatibility(self) -> None:
        """run_command alias supports total_duration and runs successfully."""
        script = "print('frame=1\\nout_time_us=1000000\\nprogress=end', flush=True)"
        cmd = [sys.executable, "-c", script]
        events: list[ProgressEvent] = []

        run_command(cmd, total_duration=1.0, progress_callback=events.append)
        assert len(events) >= 1
        assert events[-1].is_completed is True

    def test_run_ffmpeg_empty_cmd_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            run_ffmpeg([])

    def test_run_ffmpeg_nonexistent_binary(self) -> None:
        with pytest.raises(FileNotFoundError):
            run_ffmpeg(["_nonexistent_binary_xyz_12345_"])

    def test_run_ffmpeg_without_callback(self) -> None:
        """Running a valid command without progress_callback completes cleanly."""
        cmd = [sys.executable, "-c", "import sys; sys.exit(0)"]
        run_ffmpeg(cmd)

    def test_ffmpeg_auto_injection_progress_flags(self) -> None:
        """Verify that ffmpeg commands automatically receive -nostats -progress pipe:1."""
        captured_cmd: list[str] = []

        def fake_popen(cmd: list[str], **kwargs: Any) -> Any:
            captured_cmd.extend(cmd)
            mock = MagicMock()
            mock.pid = 99999
            mock.poll.return_value = 0
            mock.returncode = 0
            mock.stdout = []
            mock.stderr = []
            return mock

        with patch("subprocess.Popen", side_effect=fake_popen):
            run_ffmpeg(["ffmpeg", "-i", "input.mp4", "output.mp4"], progress_callback=lambda e: None)

        assert "-progress" in captured_cmd
        assert "pipe:1" in captured_cmd
        assert "-nostats" in captured_cmd


# ---------------------------------------------------------------------------
# Test Suite 4: Error Capture & Stderr Handling
# ---------------------------------------------------------------------------


class TestRunnerErrorHandling:
    """Test suite verifying RunnerError taxonomy and pipe capacity handling."""

    def test_runner_error_on_nonzero_exit(self) -> None:
        script = "import sys\nsys.stderr.write('Invalid codec parameters\\n')\nsys.exit(42)\n"
        cmd = [sys.executable, "-c", script]

        with pytest.raises(RunnerError) as exc_info:
            run_ffmpeg(cmd)

        err = exc_info.value
        assert isinstance(err, MediaToolboxError)
        assert err.returncode == 42
        assert "Invalid codec parameters" in err.stderr
        assert err.cmd == cmd
        assert "exit code 42" in str(err)
        assert "Invalid codec parameters" in str(err)

    def test_runner_error_last_error_line_property(self) -> None:
        err = RunnerError(
            cmd=["ffmpeg", "-i", "broken.mp4"],
            returncode=1,
            stderr="Header line 1\nFatal: unsupported bit depth\n",
        )
        assert err.last_error_line == "Fatal: unsupported bit depth"

    def test_runner_large_stderr_drain_no_deadlock(self) -> None:
        """Subprocess emits 128KB to stderr without deadlocking the runner."""
        script = (
            "import sys\n"
            "sys.stderr.write('E' * 131072)\n"
            "sys.stderr.flush()\n"
            "sys.exit(1)\n"
        )
        cmd = [sys.executable, "-c", script]

        with pytest.raises(RunnerError) as exc_info:
            run_ffmpeg(cmd)

        assert exc_info.value.returncode == 1
        assert len(exc_info.value.stderr) == 131072


# ---------------------------------------------------------------------------
# Test Suite 5: Non-Blocking Process Group Cancellation
# ---------------------------------------------------------------------------


class TestRunnerCancellation:
    """Test suite verifying cancel_event handling, SIGTERM, and SIGKILL escalation."""

    def test_cancel_before_start(self) -> None:
        cancel_event = threading.Event()
        cancel_event.set()
        cmd = [sys.executable, "-c", "import time; time.sleep(10)"]

        with pytest.raises(RunnerCancelledError):
            run_ffmpeg(cmd, cancel_event=cancel_event)

    def test_cancel_during_execution(self) -> None:
        cancel_event = threading.Event()
        cmd = [sys.executable, "-c", "import time; time.sleep(10)"]

        def _cancel_after_delay() -> None:
            time.sleep(0.05)
            cancel_event.set()

        watcher = threading.Thread(target=_cancel_after_delay)
        watcher.start()

        start_time = time.monotonic()
        with pytest.raises(RunnerCancelledError):
            run_ffmpeg(cmd, cancel_event=cancel_event)
        elapsed = time.monotonic() - start_time

        watcher.join()
        # Must terminate in well under the 10-second sleep
        assert elapsed < 3.0

    def test_cancel_escalates_to_sigkill_on_unresponsive_child(self) -> None:
        """Process ignoring SIGTERM is forcefully killed via SIGKILL."""
        script = (
            "import signal, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "time.sleep(10)\n"
        )
        cmd = [sys.executable, "-c", script]
        cancel_event = threading.Event()

        def _cancel_after_delay() -> None:
            time.sleep(0.05)
            cancel_event.set()

        watcher = threading.Thread(target=_cancel_after_delay)
        watcher.start()

        start_time = time.monotonic()
        with pytest.raises(RunnerCancelledError):
            # Use small sigterm_timeout to keep test fast (~0.2s)
            run_ffmpeg(cmd, cancel_event=cancel_event, sigterm_timeout=0.2)
        elapsed = time.monotonic() - start_time

        watcher.join()
        assert elapsed < 2.0

    def test_terminate_process_group_already_dead(self) -> None:
        """Verifies terminate_process_group handles already-terminated process gracefully."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        # Should return immediately without exception
        terminate_process_group(999999, mock_proc)


# ---------------------------------------------------------------------------
# Test Suite 6: Multi-Pass Pipeline Execution
# ---------------------------------------------------------------------------


class TestMultiPassPipeline:
    """Test suite verifying sequential execution and scaled progress reporting."""

    def test_pipeline_empty_cmds_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            run_ffmpeg_pipeline([])

    def test_pipeline_two_pass_scaled_progress(self) -> None:
        # Pass 1 script
        script1 = (
            "print('frame=10\\nout_time_us=5000000\\nspeed=1.0x\\nprogress=continue', flush=True)\n"
            "print('frame=20\\nout_time_us=10000000\\nspeed=1.0x\\nprogress=end', flush=True)\n"
        )
        # Pass 2 script
        script2 = (
            "print('frame=15\\nout_time_us=5000000\\nspeed=1.0x\\nprogress=continue', flush=True)\n"
            "print('frame=30\\nout_time_us=10000000\\nspeed=1.0x\\nprogress=end', flush=True)\n"
        )
        cmds = [
            [sys.executable, "-c", script1],
            [sys.executable, "-c", script2],
        ]

        scaled_events: list[ProgressEvent] = []
        pass_records: list[tuple[int, int, ProgressEvent]] = []

        def _pipeline_cb(p_num: int, total_p: int, ev: ProgressEvent) -> None:
            pass_records.append((p_num, total_p, ev))

        run_ffmpeg_pipeline(
            cmds=cmds,
            total_duration_seconds=10.0,
            progress_callback=scaled_events.append,
            pipeline_progress_callback=_pipeline_cb,
        )

        # Verify pass records
        assert len(pass_records) >= 4
        assert pass_records[0][0] == 1
        assert pass_records[0][1] == 2
        assert pass_records[-1][0] == 2
        assert pass_records[-1][1] == 2

        # Verify scaled percentages:
        # Pass 1 at 50% raw -> 25% pipeline
        # Pass 1 at 100% raw -> 50% pipeline
        # Pass 2 at 50% raw -> 75% pipeline
        # Pass 2 at 100% raw -> 100% pipeline
        assert scaled_events[0].percentage == 25.0
        assert scaled_events[0].is_completed is False
        assert any(e.percentage == 50.0 and not e.is_completed for e in scaled_events)
        assert scaled_events[-1].percentage == 100.0
        assert scaled_events[-1].is_completed is True

    def test_pipeline_aborts_on_pass1_error(self) -> None:
        cmd1 = [sys.executable, "-c", "import sys; sys.stderr.write('pass 1 error'); sys.exit(2)"]
        cmd2 = [sys.executable, "-c", "import sys; sys.exit(0)"]

        with pytest.raises(RunnerError) as exc_info:
            run_ffmpeg_pipeline([cmd1, cmd2])

        assert exc_info.value.returncode == 2
        assert "pass 1 error" in exc_info.value.stderr

    def test_pipeline_cancellation_between_passes(self) -> None:
        cancel_event = threading.Event()

        def _cb(ev: ProgressEvent) -> None:
            cancel_event.set()

        cmd1 = [sys.executable, "-c", "print('out_time_us=1000000\\nprogress=end', flush=True)"]
        cmd2 = [sys.executable, "-c", "import time; time.sleep(5)"]

        with pytest.raises(RunnerCancelledError):
            run_ffmpeg_pipeline([cmd1, cmd2], progress_callback=_cb, cancel_event=cancel_event)

    def test_pipeline_monotonic_out_time_across_pass_transitions(self) -> None:
        """
        Verify run_ffmpeg_pipeline emits non-decreasing cumulative out_time_seconds
        across pass transitions (Pass 1 completes at duration -> Pass 2 starts).
        """
        # Pass 1 script: emits progress at 2.5s and finishes at 5.0s
        script1 = (
            "print('frame=10\\nout_time_us=2500000\\nspeed=2.0x\\nprogress=continue', flush=True)\n"
            "print('frame=20\\nout_time_us=5000000\\nspeed=2.0x\\nprogress=end', flush=True)\n"
        )
        # Pass 2 script: starts new process at 0.5s, 2.5s, and finishes at 5.0s
        script2 = (
            "print('frame=5\\nout_time_us=500000\\nspeed=2.0x\\nprogress=continue', flush=True)\n"
            "print('frame=15\\nout_time_us=2500000\\nspeed=2.0x\\nprogress=continue', flush=True)\n"
            "print('frame=30\\nout_time_us=5000000\\nspeed=2.0x\\nprogress=end', flush=True)\n"
        )
        cmds = [
            [sys.executable, "-c", script1],
            [sys.executable, "-c", script2],
        ]

        global_events: list[ProgressEvent] = []
        pass_records: list[tuple[int, int, ProgressEvent]] = []

        def _pass_cb(p_num: int, total_p: int, ev: ProgressEvent) -> None:
            pass_records.append((p_num, total_p, ev))

        run_ffmpeg_pipeline(
            cmds=cmds,
            total_duration_seconds=5.0,
            progress_callback=global_events.append,
            pipeline_progress_callback=_pass_cb,
        )

        assert len(global_events) == 5

        times = [e.out_time_seconds for e in global_events]
        pcts = [e.percentage for e in global_events]

        # Invariant 1: Pipeline global out_time_seconds must never decrease
        assert all(times[i] <= times[i + 1] for i in range(len(times) - 1)), (
            f"Pipeline out_time_seconds decreased: {times}"
        )

        # Invariant 2: Pass transition boundary must be strictly monotonic
        # Event 1 is end of Pass 1 (5.0s); Event 2 is start of Pass 2 (must be >= 5.0s, not 0.5s)
        assert global_events[1].out_time_seconds <= global_events[2].out_time_seconds, (
            f"Pass transition regression: {global_events[1].out_time_seconds} -> {global_events[2].out_time_seconds}"
        )

        # Invariant 3: Cumulative timeline calculation
        # Pass 1: 2.5s, 5.0s
        # Pass 2: (1 * 5.0) + 0.5 = 5.5s, (1 * 5.0) + 2.5 = 7.5s, (1 * 5.0) + 5.0 = 10.0s
        assert times == [2.5, 5.0, 5.5, 7.5, 10.0]

        # Invariant 4: Percentages must be monotonic and reach 100%
        assert all(pcts[i] <= pcts[i + 1] for i in range(len(pcts) - 1))
        assert pcts == [25.0, 50.0, 55.0, 75.0, 100.0]
        assert global_events[-1].is_completed is True

        # Invariant 5: Pass-level callback preserves unscaled pass out_times
        pass1_raw_times = [ev.out_time_seconds for p_num, _, ev in pass_records if p_num == 1]
        pass2_raw_times = [ev.out_time_seconds for p_num, _, ev in pass_records if p_num == 2]
        assert pass1_raw_times == [2.5, 5.0]
        assert pass2_raw_times == [0.5, 2.5, 5.0]

    def test_pipeline_monotonic_out_time_three_passes(self) -> None:
        """Verify pipeline monotonicity across three passes."""
        script_template = (
            "print('frame=10\\nout_time_us=2000000\\nprogress=continue', flush=True)\n"
            "print('frame=20\\nout_time_us=4000000\\nprogress=end', flush=True)\n"
        )
        cmds = [[sys.executable, "-c", script_template] for _ in range(3)]
        events: list[ProgressEvent] = []

        run_ffmpeg_pipeline(cmds, total_duration_seconds=4.0, progress_callback=events.append)
        assert len(events) == 6

        times = [e.out_time_seconds for e in events]
        assert all(times[i] <= times[i + 1] for i in range(len(times) - 1)), f"Times decreased: {times}"
        # Expected cumulative times:
        # Pass 1: 2.0s, 4.0s
        # Pass 2: 4.0 + 2.0 = 6.0s, 4.0 + 4.0 = 8.0s
        # Pass 3: 8.0 + 2.0 = 10.0s, 8.0 + 4.0 = 12.0s
        assert times == [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
        assert events[-1].percentage == 100.0
        assert events[-1].is_completed is True

    def test_pipeline_monotonic_out_time_without_duration(self) -> None:
        """Verify pipeline out_time does not regress across passes even when total_duration is None."""
        script1 = "print('out_time_us=3000000\\nprogress=end', flush=True)"
        script2 = "print('out_time_us=1000000\\nprogress=end', flush=True)"
        cmds = [
            [sys.executable, "-c", script1],
            [sys.executable, "-c", script2],
        ]
        events: list[ProgressEvent] = []
        run_ffmpeg_pipeline(cmds, total_duration_seconds=None, progress_callback=events.append)
        assert len(events) == 2
        times = [e.out_time_seconds for e in events]
        # Invariant: monotonic clamp prevents drop from 3.0s to 1.0s
        assert times[0] <= times[1]
        assert times[0] == 3.0
        assert times[1] == 3.0


# ---------------------------------------------------------------------------
# Test Suite 7: Headless AST Invariant
# ---------------------------------------------------------------------------


class TestRunnerHeadlessASTInvariant:
    """Verifies that core/runner.py maintains zero GUI imports invariant."""

    def test_runner_zero_gui_imports(self) -> None:
        runner_path = Path(__file__).resolve().parent.parent / "core" / "runner.py"
        with open(runner_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(runner_path))

        forbidden = ("gi", "Gtk", "Adw", "Nautilus", "tkinter", "PyQt", "PySide")

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                for alias in getattr(node, "names", []):
                    full_name = f"{mod}.{alias.name}" if mod else alias.name
                    assert not any(
                        pkg in full_name for pkg in forbidden
                    ), f"Forbidden GUI import found in core/runner.py: {full_name}"

    def test_test_runner_zero_gui_imports(self) -> None:
        """Verify test_runner.py contains zero GUI imports (headless execution invariant)."""
        test_path = Path(__file__).resolve()
        with open(test_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(test_path))

        forbidden_roots = {"gi", "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6"}
        forbidden_submodules = {"Gtk", "Adw", "Nautilus"}

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                root_pkg = mod.split(".")[0] if mod else ""
                assert root_pkg not in forbidden_roots, (
                    f"Forbidden root GUI package imported in test_runner.py: {root_pkg}"
                )
                if root_pkg == "gi":
                    for alias in getattr(node, "names", []):
                        assert alias.name not in forbidden_submodules, (
                            f"Forbidden GI submodule imported in test_runner.py: {alias.name}"
                        )
                for alias in getattr(node, "names", []):
                    if not mod:
                        assert alias.name.split(".")[0] not in forbidden_roots, (
                            f"Forbidden root import in test_runner.py: {alias.name}"
                        )
