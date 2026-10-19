"""
Non-blocking FFmpeg subprocess execution and progress tracking.

This module provides subprocess execution primitives with:
- Line-by-line machine-readable progress parsing (-progress pipe:1 -nostats)
- Non-blocking execution with responsive cancel_event coordination
- Clean process group lifecycle management (SIGTERM -> SIGKILL) to prevent orphaned processes
- Microsecond time conversion, percentage clamping, and ETA calculation
- Multi-pass pipeline execution support (aggregating or dispatching progress)
- Strongly typed exception taxonomy (RunnerError, RunnerCancelledError)

INVARIANT: Strict zero GUI imports (gi, Gtk, Adw, Nautilus, tkinter, PyQt, PySide).
"""

from __future__ import annotations

import collections
import errno
import math
import os
import signal
import subprocess
import threading
import time
from typing import Any, Callable, Iterable, Iterator, Optional, Union

from media_toolbox.core.models import MediaToolboxError, ProgressEvent


# ---------------------------------------------------------------------------
# Exception Taxonomy
# ---------------------------------------------------------------------------


class RunnerError(MediaToolboxError):
    """
    Raised when an external subprocess execution fails (non-zero exit code).

    Attributes:
        cmd: The argument list of the executed command.
        returncode: The process exit code.
        stderr: Captured standard error output.
        stdout: Captured standard output if available.
    """

    def __init__(
        self,
        message_or_cmd: Union[str, list[str]] = "",
        cmd: Optional[list[str]] = None,
        returncode: int = 1,
        stderr: str = "",
        stdout: str = "",
        **kwargs: Any,
    ) -> None:
        if isinstance(message_or_cmd, list):
            the_cmd = list(message_or_cmd)
            msg = f"FFmpeg command failed with exit code {returncode}: {' '.join(the_cmd)}\n{stderr}".strip()
        else:
            the_cmd = list(cmd) if cmd is not None else []
            if message_or_cmd:
                msg = str(message_or_cmd)
            else:
                msg = f"FFmpeg command failed with exit code {returncode}: {' '.join(the_cmd)}\n{stderr}".strip()

        self.cmd = the_cmd
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout
        super().__init__(msg)

    def __str__(self) -> str:
        cmd_str = " ".join(self.cmd) if self.cmd else "<unknown>"
        base_msg = super().__str__()
        parts = []

        if f"exit code {self.returncode}" not in base_msg:
            parts.append(f"{base_msg} (exit code {self.returncode})")
        else:
            parts.append(base_msg)

        if f"Command: {cmd_str}" not in base_msg and self.cmd:
            parts.append(f"Command: {cmd_str}")

        if self.stderr.strip() and self.stderr.strip() not in base_msg:
            snippet = self.stderr.strip()
            if len(snippet) > 1000:
                snippet = f"{snippet[:1000]}... [truncated {len(snippet) - 1000} chars]"
            parts.append(f"Stderr:\n{snippet}")

        return "\n".join(parts) if len(parts) > 1 else base_msg

    @property
    def last_error_line(self) -> str:
        """Return the last non-empty line of stderr, useful for UI status displays."""
        lines = [line.strip() for line in self.stderr.splitlines() if line.strip()]
        return lines[-1] if lines else f"Exit code {self.returncode}"


class RunnerCancelledError(RunnerError):
    """Raised when a subprocess execution is terminated via cancel_event."""

    def __init__(
        self,
        message_or_cmd: Union[str, list[str]] = "Execution was cancelled",
        cmd: Optional[list[str]] = None,
        returncode: int = -15,
        stderr: str = "",
        stdout: str = "",
        **kwargs: Any,
    ) -> None:
        if isinstance(message_or_cmd, list):
            the_cmd = list(message_or_cmd)
            msg = "Execution was cancelled"
        else:
            the_cmd = list(cmd) if cmd is not None else []
            msg = str(message_or_cmd) if message_or_cmd else "Execution was cancelled"

        super().__init__(
            message_or_cmd=msg,
            cmd=the_cmd,
            returncode=returncode,
            stderr=stderr,
            stdout=stdout,
        )


# Backward-compatible aliases for cross-module compatibility
ProcessExecutionError = RunnerError
ProcessCancelledError = RunnerCancelledError


# ---------------------------------------------------------------------------
# Parsing & Normalization Helpers
# ---------------------------------------------------------------------------


def parse_speed(speed_val: Any) -> Optional[float]:
    """
    Parse FFmpeg speed factor string into an optional positive float.

    Handles ' 1.2x', '60.6x', '2.50x', '0x', '0.00x', 'N/A', '', and non-numeric tokens.
    """
    if speed_val is None:
        return None
    s = str(speed_val).strip()
    if not s or s.upper() == "N/A":
        return None
    if s.lower().endswith("x"):
        s = s[:-1].strip()
    try:
        val = float(s)
        return val if math.isfinite(val) and val >= 0.0 else None
    except (ValueError, OverflowError):
        return None


def parse_time_to_seconds(
    out_time_us: Optional[str] = None,
    out_time_ms: Optional[str] = None,
    out_time_str: Optional[str] = None,
    out_time: Optional[str] = None,
) -> float:
    """
    Convert FFmpeg time fields to elapsed seconds.

    Priority:
    1. out_time_us / 1,000,000.0
    2. out_time_ms / 1,000,000.0 (FFmpeg emits microseconds for out_time_ms)
    3. out_time / out_time_str (HH:MM:SS.ffffff or MM:SS.ffffff)
    """
    for raw in (out_time_us, out_time_ms):
        if raw is not None:
            s = str(raw).strip()
            if s and s.upper() != "N/A":
                try:
                    val = int(s)
                    return max(0.0, val / 1_000_000.0)
                except (ValueError, OverflowError):
                    pass

    raw_str = out_time if out_time is not None else out_time_str
    if raw_str is not None:
        s = str(raw_str).strip()
        if s and s.upper() != "N/A":
            try:
                is_negative = s.startswith("-")
                clean = s.lstrip("-")
                parts = clean.split(":")
                if len(parts) == 3:
                    h, m, sec = float(parts[0]), float(parts[1]), float(parts[2])
                    total = h * 3600.0 + m * 60.0 + sec
                    return 0.0 if is_negative else max(0.0, total)
                elif len(parts) == 2:
                    m, sec = float(parts[0]), float(parts[1])
                    total = m * 60.0 + sec
                    return 0.0 if is_negative else max(0.0, total)
                elif len(parts) == 1:
                    total = float(parts[0])
                    return 0.0 if is_negative else max(0.0, total)
            except (ValueError, OverflowError):
                pass

    return 0.0


def calculate_percentage(
    out_time_seconds: float,
    total_duration: Optional[float],
    is_completed: bool = False,
) -> float:
    """Calculate completion percentage clamped to [0.0, 100.0]."""
    if is_completed:
        return 100.0
    if total_duration is None or not math.isfinite(total_duration) or total_duration <= 0.0:
        return 0.0
    if not math.isfinite(out_time_seconds) or out_time_seconds <= 0.0:
        return 0.0
    raw_pct = (out_time_seconds / total_duration) * 100.0
    return round(max(0.0, min(100.0, raw_pct)), 2)


def calculate_eta_seconds(
    out_time_seconds: float,
    total_duration: Optional[float],
    speed: Optional[float],
    is_completed: bool = False,
) -> Optional[float]:
    """Calculate estimated remaining time in seconds."""
    if is_completed:
        return 0.0
    if total_duration is None or not math.isfinite(total_duration) or total_duration <= 0.0:
        return None
    if speed is None or not math.isfinite(speed) or speed <= 0.0:
        return None
    remaining = total_duration - max(0.0, out_time_seconds)
    if remaining <= 0.0:
        return 0.0
    return round(remaining / speed, 2)


# ---------------------------------------------------------------------------
# Stream Parser Class & Generator
# ---------------------------------------------------------------------------


class ProgressParser:
    """
    Stateful parser for FFmpeg -progress pipe:1 key=value stream.

    Emits ProgressEvent on progress=continue and progress=end.
    """

    def __init__(self, total_duration: Optional[float] = None) -> None:
        self.total_duration = total_duration
        self._block: dict[str, str] = {}
        self._completed_emitted: bool = False

    def feed_line(self, line: str) -> Optional[ProgressEvent]:
        """Process one stream line. Returns ProgressEvent on block boundary, else None."""
        line = line.strip()
        if not line or "=" not in line:
            return None

        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        self._block[key] = val

        if key == "progress":
            is_end = val.lower() == "end"
            out_time = parse_time_to_seconds(
                out_time_us=self._block.get("out_time_us"),
                out_time_ms=self._block.get("out_time_ms"),
                out_time_str=self._block.get("out_time"),
            )
            speed = parse_speed(self._block.get("speed"))

            def _to_int(k: str) -> int:
                v = self._block.get(k, "")
                try:
                    return int(float(v))
                except (ValueError, TypeError):
                    return 0

            def _to_float(k: str) -> float:
                v = self._block.get(k, "")
                try:
                    f = float(v)
                    return f if math.isfinite(f) else 0.0
                except (ValueError, TypeError):
                    return 0.0

            pct = calculate_percentage(out_time, self.total_duration, is_completed=is_end)
            eta = calculate_eta_seconds(out_time, self.total_duration, speed, is_completed=is_end)

            event = ProgressEvent(
                frame=_to_int("frame"),
                fps=_to_float("fps"),
                out_time_seconds=out_time,
                total_size_bytes=_to_int("total_size"),
                speed=speed,
                percentage=pct,
                eta_seconds=eta,
                is_completed=is_end,
            )
            self._block.clear()
            if is_end:
                self._completed_emitted = True
            return event

        return None

    def finish(self) -> Optional[ProgressEvent]:
        """Emit completion event if process finished without emitting progress=end."""
        if not self._completed_emitted:
            self._completed_emitted = True
            return ProgressEvent(
                out_time_seconds=self.total_duration or 0.0,
                percentage=100.0,
                eta_seconds=0.0,
                is_completed=True,
            )
        return None


def parse_progress_stream(
    lines: Iterable[str],
    total_duration: Optional[float] = None,
) -> Iterator[ProgressEvent]:
    """Generator yielding ProgressEvents from an iterable of stream lines."""
    parser = ProgressParser(total_duration=total_duration)
    for line in lines:
        evt = parser.feed_line(line)
        if evt is not None:
            yield evt


# ---------------------------------------------------------------------------
# Process Group Management & Execution
# ---------------------------------------------------------------------------


def terminate_process_group(
    pgid: int,
    proc: subprocess.Popen[str],
    graceful_timeout: float = 2.0,
    kill_timeout: float = 1.0,
) -> None:
    """
    Terminate an isolated process group with SIGTERM, escalating to SIGKILL.

    Args:
        pgid: Process group ID to signal.
        proc: Subprocess Popen instance.
        graceful_timeout: Seconds to wait after SIGTERM before escalating to SIGKILL.
        kill_timeout: Seconds to wait after SIGKILL to reap process.
    """
    if proc.poll() is not None:
        return

    # Stage 1: Graceful SIGTERM to process group
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError as e:
        if e.errno == errno.ESRCH:
            return
        raise

    # Wait for graceful exit
    start = time.monotonic()
    while time.monotonic() - start < graceful_timeout:
        if proc.poll() is not None:
            return
        time.sleep(0.02)

    # Stage 2: Forced escalation to SIGKILL
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass

    start = time.monotonic()
    while time.monotonic() - start < kill_timeout:
        if proc.poll() is not None:
            return
        time.sleep(0.02)

    try:
        proc.wait(timeout=0.1)
    except (subprocess.TimeoutExpired, OSError):
        pass


def run_ffmpeg(
    cmd: list[str],
    total_duration_seconds: Optional[float] = None,
    progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    sigterm_timeout: float = 2.0,
    total_duration: Optional[float] = None,
) -> None:
    """
    Execute a single FFmpeg command, parsing progress output and handling cancellation.

    Args:
        cmd: Command line arguments list.
        total_duration_seconds: Duration in seconds for percentage/ETA calculation.
        progress_callback: Callback receiving ProgressEvent updates.
        cancel_event: Event to signal execution cancellation.
        sigterm_timeout: Grace period in seconds before SIGKILL escalation.
        total_duration: Compatibility parameter for total_duration_seconds.

    Raises:
        ValueError: If cmd is empty.
        FileNotFoundError: If binary is not found.
        RunnerCancelledError: If cancelled via cancel_event.
        RunnerError: If command exits with non-zero exit code.
    """
    if not cmd:
        raise ValueError("cmd argument list cannot be empty")

    dur = total_duration_seconds if total_duration_seconds is not None else total_duration

    if cancel_event is not None and cancel_event.is_set():
        raise RunnerCancelledError("Execution cancelled before start", cmd=cmd)

    effective_cmd = list(cmd)
    base_name = os.path.basename(effective_cmd[0]).lower()
    if "ffmpeg" in base_name and "-progress" not in effective_cmd:
        effective_cmd = [effective_cmd[0], "-nostats", "-progress", "pipe:1"] + effective_cmd[1:]

    proc = subprocess.Popen(
        effective_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        start_new_session=True,  # Process group leader (pgid == proc.pid)
    )

    pgid = proc.pid  # Cache process group ID immediately

    # Dedicated daemon thread draining proc.stderr to prevent 64KB kernel buffer deadlocks
    stderr_lines: list[str] = []

    def _drain_stderr() -> None:
        try:
            if proc.stderr is not None:
                for line in proc.stderr:
                    stderr_lines.append(line)
        except Exception:
            pass
        finally:
            if proc.stderr is not None:
                try:
                    proc.stderr.close()
                except Exception:
                    pass

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True, name="ffmpeg-stderr-drain")
    stderr_thread.start()

    done_event = threading.Event()

    # Asynchronous cancellation watcher thread
    if cancel_event is not None:
        def _cancel_watcher() -> None:
            cancel_event.wait()
            if not done_event.is_set() and proc.poll() is None:
                terminate_process_group(pgid, proc, graceful_timeout=sigterm_timeout)

        watcher_thread = threading.Thread(target=_cancel_watcher, daemon=True, name="ffmpeg-cancel-watch")
        watcher_thread.start()

    parser = ProgressParser(total_duration=dur)

    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                if cancel_event is not None and cancel_event.is_set():
                    terminate_process_group(pgid, proc, graceful_timeout=sigterm_timeout)
                    break

                event = parser.feed_line(line)
                if event is not None and progress_callback is not None:
                    progress_callback(event)
    finally:
        done_event.set()
        if proc.stdout is not None:
            try:
                proc.stdout.close()
            except Exception:
                pass

        if cancel_event is not None and cancel_event.is_set():
            terminate_process_group(pgid, proc, graceful_timeout=sigterm_timeout)
        else:
            if proc.poll() is None:
                terminate_process_group(pgid, proc, graceful_timeout=sigterm_timeout)
            else:
                proc.wait()

        stderr_thread.join(timeout=1.0)

    full_stderr = "".join(stderr_lines)

    if cancel_event is not None and cancel_event.is_set():
        raise RunnerCancelledError("Process was cancelled", cmd=effective_cmd, returncode=proc.returncode, stderr=full_stderr)

    if proc.returncode != 0:
        raise RunnerError(
            f"Command failed with exit code {proc.returncode}",
            cmd=effective_cmd,
            returncode=proc.returncode,
            stderr=full_stderr,
        )

    if progress_callback is not None:
        final_evt = parser.finish()
        if final_evt is not None:
            progress_callback(final_evt)


def run_command(
    cmd: list[str],
    total_duration: Optional[float] = None,
    progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    total_duration_seconds: Optional[float] = None,
    sigterm_timeout: float = 2.0,
) -> None:
    """Compatibility alias for run_ffmpeg supporting total_duration and total_duration_seconds."""
    dur = total_duration_seconds if total_duration_seconds is not None else total_duration
    run_ffmpeg(
        cmd=cmd,
        total_duration_seconds=dur,
        progress_callback=progress_callback,
        cancel_event=cancel_event,
        sigterm_timeout=sigterm_timeout,
    )


def run_ffmpeg_pipeline(
    cmds: list[list[str]],
    total_duration_seconds: Optional[float] = None,
    progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
    pipeline_progress_callback: Optional[Callable[[int, int, ProgressEvent], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    sigterm_timeout: float = 2.0,
    total_duration: Optional[float] = None,
) -> None:
    """
    Execute a sequential pipeline of FFmpeg commands (e.g. 2-pass bitrate targeting).

    Args:
        cmds: Non-empty list of command argument lists.
        total_duration_seconds: Duration of media for progress calculations.
        progress_callback: Callback receiving aggregated global ProgressEvents (0-100% across all passes).
        pipeline_progress_callback: Callback receiving (pass_num, total_passes, raw_event).
        cancel_event: Event to signal cancellation across passes.
        sigterm_timeout: Grace period before SIGKILL escalation.
        total_duration: Compatibility parameter for total_duration_seconds.

    Raises:
        ValueError: If cmds list is empty.
        RunnerCancelledError: If cancelled between or during passes.
        RunnerError: If any pass fails with non-zero exit code.
    """
    if not cmds:
        raise ValueError("cmds list cannot be empty")

    dur = total_duration_seconds if total_duration_seconds is not None else total_duration
    num_passes = len(cmds)

    for pass_idx, cmd in enumerate(cmds):
        pass_num = pass_idx + 1

        if cancel_event is not None and cancel_event.is_set():
            raise RunnerCancelledError(f"Pipeline cancelled before pass {pass_num}", cmd=cmd)

        def _pass_callback(raw_event: ProgressEvent, p_idx: int = pass_idx, p_num: int = pass_num) -> None:
            if pipeline_progress_callback is not None:
                pipeline_progress_callback(p_num, num_passes, raw_event)

            if progress_callback is not None:
                scaled_pct = (p_idx * 100.0 / num_passes) + (raw_event.percentage / num_passes)
                clamped_pct = round(max(0.0, min(100.0, scaled_pct)), 2)

                pipeline_eta: Optional[float] = None
                if dur and raw_event.speed and raw_event.speed > 0:
                    rem_in_pass = max(0.0, dur - raw_event.out_time_seconds)
                    rem_passes = num_passes - 1 - p_idx
                    total_rem_dur = rem_in_pass + (rem_passes * dur)
                    pipeline_eta = round(total_rem_dur / raw_event.speed, 2)
                elif raw_event.eta_seconds is not None:
                    pipeline_eta = raw_event.eta_seconds

                is_overall_completed = (p_idx == num_passes - 1) and raw_event.is_completed

                scaled_event = ProgressEvent(
                    frame=raw_event.frame,
                    fps=raw_event.fps,
                    out_time_seconds=raw_event.out_time_seconds,
                    total_size_bytes=raw_event.total_size_bytes,
                    speed=raw_event.speed,
                    percentage=clamped_pct,
                    eta_seconds=0.0 if is_overall_completed else pipeline_eta,
                    is_completed=is_overall_completed,
                )
                progress_callback(scaled_event)

        run_ffmpeg(
            cmd=cmd,
            total_duration_seconds=dur,
            progress_callback=_pass_callback,
            cancel_event=cancel_event,
            sigterm_timeout=sigterm_timeout,
        )
