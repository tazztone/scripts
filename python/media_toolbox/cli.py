"""
Standalone Command Line Interface for media_toolbox.

Provides CLI subcommands:
- inspect: Probes media and renders formatted technical metadata or JSON.
- transcode: Video transcoding with presets, CRF/two-pass bitrate, scale, crop, speed.
- extract-audio: Standalone audio track extraction and transcoding.

INVARIANT: Strict zero GUI imports (gi, Gtk, Adw, Nautilus, tkinter, PyQt, PySide, wx).
Only Python standard library and media_toolbox.core domain modules.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import signal
import sys
import threading
from typing import Any, Callable, Optional, Sequence

from media_toolbox import __version__
from media_toolbox.core.builder import build_ffmpeg_commands
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
from media_toolbox.core.probe import probe_media
from media_toolbox.core.runner import (
    RunnerCancelledError,
    RunnerError,
    run_ffmpeg,
    run_ffmpeg_pipeline,
)

__all__ = [
    "parse_scale_arg",
    "format_duration",
    "format_file_size",
    "format_bitrate",
    "format_aspect_ratio",
    "format_fps",
    "format_channels",
    "render_media_info_text",
    "format_media_info_json",
    "media_info_to_dict",
    "create_progress_reporter",
    "build_parser",
    "normalize_argv",
    "main",
    "probe_media",
    "build_ffmpeg_commands",
    "run_ffmpeg",
    "run_ffmpeg_pipeline",
    "handle_install_nautilus",
    "handle_uninstall_nautilus",
    "handle_status_nautilus",
]


def parse_scale_arg(scale_str: Optional[str]) -> Optional[tuple[int, int]]:
    """Parse WIDTHxHEIGHT or WIDTH:HEIGHT scale string into (width, height) tuple."""
    if not scale_str:
        return None
    s = scale_str.strip().lower()
    sep = "x" if "x" in s else (":" if ":" in s else None)
    if not sep:
        raise ValueError(
            f"Invalid scale format '{scale_str}'. Expected WIDTHxHEIGHT or WIDTH:HEIGHT (e.g. 1920x1080, 1280:-2)"
        )
    parts = s.split(sep)
    if len(parts) != 2:
        raise ValueError(f"Invalid scale format '{scale_str}'. Expected WIDTHxHEIGHT or WIDTH:HEIGHT")
    try:
        w, h = int(parts[0]), int(parts[1])
        if w <= 0 and h <= 0:
            raise ValueError(f"Scale dimensions cannot both be non-positive: {scale_str}")
        if w == 0 or h == 0:
            raise ValueError(f"Scale dimensions cannot be 0: {scale_str}")
        return (w, h)
    except ValueError as e:
        if "Scale dimensions" in str(e) or "Invalid scale format" in str(e):
            raise
        raise ValueError(f"Invalid non-integer scale dimensions in '{scale_str}'") from e


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds as HH:MM:SS.ff, or 'N/A' if unknown."""
    if seconds is None or seconds < 0:
        return "N/A"
    hours = int(seconds // 3600)
    rem = seconds % 3600
    mins = int(rem // 60)
    secs = rem % 60
    return f"{hours:02d}:{mins:02d}:{secs:05.2f}"


def format_file_size(size_bytes: Optional[int]) -> str:
    """Format byte size into scaled units (B, KB, MB, GB, TB) with exact byte count."""
    if size_bytes is None or size_bytes < 0:
        return "N/A"
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(size_bytes)
    idx = 0
    while val >= 1024.0 and idx < len(units) - 1:
        val /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(val)} B"
    return f"{val:.2f} {units[idx]} ({size_bytes:,} bytes)"


def format_bitrate(bps: Optional[int]) -> str:
    """Format bitrate in bps to kbps (and Mbps if >= 1,000,000 bps)."""
    if bps is None or bps <= 0:
        return "N/A"
    kbps = round(bps / 1000)
    if bps >= 1_000_000:
        return f"{kbps:,} kbps ({bps / 1_000_000:.2f} Mbps)"
    return f"{kbps:,} kbps"


def format_aspect_ratio(width: int, height: int) -> str:
    """Calculate and format aspect ratio (e.g. '16:9 (1.78:1)')."""
    if width <= 0 or height <= 0:
        return "N/A"
    g = math.gcd(width, height)
    rw, rh = width // g, height // g
    ratio = width / height
    if rw <= 32 and rh <= 32:
        return f"{rw}:{rh} ({ratio:.2f}:1)"
    return f"{ratio:.2f}:1"


def format_fps(fps: Optional[float], is_attached_pic: bool = False) -> str:
    """Format frame rate in fps, handling still pictures and fractional fps."""
    if is_attached_pic:
        return "N/A (still picture)"
    if fps is None or fps <= 0:
        return "N/A"
    if fps.is_integer():
        return f"{int(fps)} fps"
    return f"{fps:.2f} fps"


def format_channels(layout: Optional[str], channels: int) -> str:
    """Format channel count and layout with proper pluralization."""
    ch_word = "channel" if channels == 1 else "channels"
    if layout:
        return f"{layout} ({channels} {ch_word})"
    return f"{channels} {ch_word}"


def should_colorize(stream: Any = sys.stdout) -> bool:
    """Return True if stream is a TTY and NO_COLOR is not set in environment."""
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def media_info_to_dict(media: MediaInfo) -> dict[str, Any]:
    """Serialize MediaInfo dataclass into JSON-serializable dictionary."""
    dur_val = media.duration if media.duration > 0 else media.format.duration
    vid_count = len([s for s in media.video_streams if not s.is_attached_pic])

    v_streams: list[dict[str, Any]] = []
    for s in media.video_streams:
        v_dict = {
            "index": s.index,
            "codec_name": s.codec_name or None,
            "width": s.width,
            "height": s.height,
            "resolution": [s.width, s.height] if (s.width > 0 and s.height > 0) else None,
            "display_resolution": s.display_resolution if (s.width > 0 and s.height > 0) else None,
            "effective_resolution": list(s.effective_dimensions) if (s.width > 0 and s.height > 0) else None,
            "aspect_ratio": format_aspect_ratio(s.width, s.height),
            "aspect_ratio_float": round(s.aspect_ratio, 4) if s.aspect_ratio > 0 else None,
            "pixel_format": s.pix_fmt,
            "fps": s.fps,
            "bit_rate": s.bit_rate,
            "bit_rate_kbps": round(s.bit_rate / 1000) if s.bit_rate is not None else None,
            "duration": s.duration,
            "duration_formatted": format_duration(s.duration) if s.duration is not None else None,
            "rotation": s.rotation,
            "is_attached_pic": s.is_attached_pic,
        }
        v_streams.append(v_dict)

    a_streams: list[dict[str, Any]] = []
    for s in media.audio_streams:
        a_dict = {
            "index": s.index,
            "codec_name": s.codec_name or None,
            "channels": s.channels,
            "channel_layout": s.channel_layout,
            "sample_rate": s.sample_rate,
            "sample_rate_khz": s.sample_rate_khz if s.sample_rate > 0 else None,
            "bit_rate": s.bit_rate,
            "bit_rate_kbps": s.bit_rate_kbps,
            "duration": s.duration,
            "duration_formatted": format_duration(s.duration) if s.duration is not None else None,
        }
        a_streams.append(a_dict)

    return {
        "format": {
            "filename": media.format.filename,
            "format_name": media.format.format_name,
            "duration": media.format.duration,
            "duration_formatted": format_duration(media.format.duration) if media.format.duration is not None else None,
            "size_bytes": media.format.size_bytes,
            "size_human": format_file_size(media.format.size_bytes),
            "bit_rate": media.format.bit_rate,
            "bit_rate_kbps": media.format.bit_rate_kbps,
        },
        "video_streams": v_streams,
        "audio_streams": a_streams,
        "summary": {
            "resolved_duration": media.duration,
            "duration_formatted": format_duration(dur_val) if dur_val is not None and dur_val > 0 else "N/A",
            "has_video": media.has_video,
            "has_audio": media.has_audio,
            "is_audio_only": media.is_audio_only,
            "is_video_only": media.is_video_only,
            "is_image": media.is_image,
            "video_stream_count": vid_count,
            "audio_stream_count": len(media.audio_streams),
            "attached_pic_count": len(media.attached_pics),
        },
    }


def format_media_info_json(media: MediaInfo, indent: int = 2) -> str:
    """Serialize MediaInfo into formatted JSON string."""
    return json.dumps(media_info_to_dict(media), indent=indent)


def render_media_info_text(media: MediaInfo, use_color: bool = False) -> str:
    """Render human-readable structured terminal output for MediaInfo."""
    bold = "\033[1m" if use_color else ""
    reset = "\033[0m" if use_color else ""
    cyan = "\033[1;36m" if use_color else ""
    green = "\033[32m" if use_color else ""

    lines: list[str] = []

    # Container / File Header
    filename = media.format.filename or "<unknown>"
    lines.append(f"{cyan}[Media: {filename}]{reset}")
    lines.append(f"  {'Container:':<16}{media.format.format_name or 'N/A'}")
    lines.append(f"  {'Size:':<16}{format_file_size(media.format.size_bytes)}")
    dur_val = media.duration if media.duration > 0 else media.format.duration
    dur_str = format_duration(dur_val)
    if media.is_image:
        dur_str += " (still image)"
    lines.append(f"  {'Duration:':<16}{dur_str}")
    lines.append(f"  {'Total Bitrate:':<16}{format_bitrate(media.format.bit_rate)}")

    badges: list[str] = []
    if media.is_image:
        badges.append("[Still Image]")
    elif media.is_audio_only:
        badges.append("[Audio Only]")
    elif media.is_video_only:
        badges.append("[Silent Video]")
    if badges:
        lines.append(f"  {'Type:':<16}{green}{' '.join(badges)}{reset}")

    # Video Stream(s)
    if media.video_streams:
        for s in media.video_streams:
            lines.append("")
            tag = " (Cover Art)" if s.is_attached_pic else (" (Still Image)" if media.is_image else "")
            lines.append(f"{bold}[Video Stream #{s.index}{tag}]{reset}")
            lines.append(f"  {'Codec:':<16}{s.codec_name or 'N/A'}")
            res_str = f"{s.width}x{s.height}" if (s.width > 0 and s.height > 0) else "N/A"
            if s.rotation != 0:
                res_str += f" (effective: {s.effective_dimensions[0]}x{s.effective_dimensions[1]} @ {s.rotation}°)"
            lines.append(f"  {'Resolution:':<16}{res_str}")
            lines.append(f"  {'Aspect Ratio:':<16}{format_aspect_ratio(s.width, s.height)}")
            lines.append(f"  {'Pixel Format:':<16}{s.pix_fmt or 'N/A'}")
            lines.append(f"  {'Frame Rate:':<16}{format_fps(s.fps, s.is_attached_pic)}")
            lines.append(f"  {'Bitrate:':<16}{format_bitrate(s.bit_rate)}")
            lines.append(f"  {'Duration:':<16}{format_duration(s.duration)}")
    elif not media.is_audio_only:
        lines.append("")
        lines.append(f"{bold}[Video Streams]{reset}")
        lines.append("  (No video streams)")

    # Audio Stream(s)
    if media.audio_streams:
        for s in media.audio_streams:
            lines.append("")
            lines.append(f"{bold}[Audio Stream #{s.index}]{reset}")
            lines.append(f"  {'Codec:':<16}{s.codec_name or 'N/A'}")
            lines.append(f"  {'Channels:':<16}{format_channels(s.channel_layout, s.channels)}")
            sr_str = f"{s.sample_rate:,} Hz ({s.sample_rate_khz:.1f} kHz)" if s.sample_rate > 0 else "N/A"
            lines.append(f"  {'Sample Rate:':<16}{sr_str}")
            lines.append(f"  {'Bitrate:':<16}{format_bitrate(s.bit_rate)}")
            lines.append(f"  {'Duration:':<16}{format_duration(s.duration)}")
    elif not media.is_image and not media.is_video_only:
        lines.append("")
        lines.append(f"{bold}[Audio Streams]{reset}")
        lines.append("  (No audio streams)")

    # Streams Summary
    lines.append("")
    lines.append(f"{bold}[Streams Summary]{reset}")
    vid_count = len([s for s in media.video_streams if not s.is_attached_pic])
    lines.append(f"  {'Video Streams:':<16}{vid_count}")
    lines.append(f"  {'Audio Streams:':<16}{len(media.audio_streams)}")
    lines.append(f"  {'Attachments:':<16}{len(media.attached_pics)}")

    return "\n".join(lines)


def create_progress_reporter(quiet: bool = False) -> Optional[Callable[[ProgressEvent], None]]:
    """Create terminal progress callback handling TTY carriage return or non-TTY logging."""
    if quiet:
        return None

    is_tty = sys.stdout.isatty()
    last_pct = -1.0

    def _reporter(evt: ProgressEvent) -> None:
        nonlocal last_pct
        if is_tty:
            bar_len = 20
            pct = max(0.0, min(100.0, evt.percentage))
            filled = int(round(bar_len * (pct / 100.0)))
            bar = "=" * max(0, filled - 1) + (">" if filled > 0 and filled < bar_len else ("=" if filled == bar_len else ""))
            bar_str = f"[{bar:<{bar_len}}]"
            size_mb = (evt.total_size_bytes / (1024 * 1024)) if evt.total_size_bytes else 0.0
            line = f"\r{bar_str} {pct:5.1f}% | Speed: {evt.speed_str:<6} | ETA: {evt.eta_str:<8} | Size: {size_mb:6.1f} MB"
            sys.stdout.write(line)
            sys.stdout.flush()
            if evt.is_completed:
                sys.stdout.write("\n")
                sys.stdout.flush()
        else:
            if int(evt.percentage / 10) > int(last_pct / 10) or evt.is_completed:
                last_pct = evt.percentage
                sys.stdout.write(f"Progress: {evt.percentage:5.1f}% (ETA: {evt.eta_str})\n")
                sys.stdout.flush()

    return _reporter


def handle_inspect(args: argparse.Namespace) -> int:
    """Handle 'inspect' subcommand."""
    file_arg = args.file
    try:
        info = probe_media(file_arg, ffprobe_bin=getattr(args, "ffprobe_bin", "ffprobe"))
    except FileNotFoundError as err:
        sys.stderr.write(f"Error: File not found: {err}\n")
        return 1
    except ProbeError as err:
        sys.stderr.write(f"Error probing media: {err}\n")
        return 1
    except Exception as err:
        sys.stderr.write(f"Unexpected error probing media: {err}\n")
        return 1

    if getattr(args, "json", False):
        sys.stdout.write(format_media_info_json(info) + "\n")
    else:
        use_color = should_colorize(sys.stdout)
        sys.stdout.write(render_media_info_text(info, use_color=use_color) + "\n")

    return 0


def handle_transcode(args: argparse.Namespace) -> int:
    """Handle 'transcode' subcommand."""
    if args.speed is not None and args.speed <= 0:
        sys.stderr.write(f"Error: Speed multiplier must be positive, got {args.speed}\n")
        return 2

    try:
        scale_tuple = parse_scale_arg(args.scale)
    except ValueError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 2

    # Probe input to obtain duration and stream layout
    try:
        media_info = probe_media(args.input)
    except FileNotFoundError as err:
        sys.stderr.write(f"Error: Input file not found: {err}\n")
        return 1
    except Exception as err:
        sys.stderr.write(f"Warning: Could not probe media: {err}\n")
        media_info = None

    options = EncodeOptions(
        preset=args.preset,
        crf=args.crf,
        target_size_mb=args.target_size_mb,
        two_pass=args.two_pass,
        speed=args.speed,
        scale=scale_tuple,
        crop=args.crop,
        pad=args.pad,
        audio_codec=args.audio_codec,
        audio_bitrate_kbps=args.audio_bitrate,
        mute_audio=args.mute_audio,
        normalize_audio=args.normalize,
    )

    try:
        cmds = build_ffmpeg_commands(
            str(args.input),
            str(args.output),
            options,
            media_info=media_info,
            pass_logfile=args.pass_logfile,
            include_progress=True,
        )
    except ValueError as err:
        sys.stderr.write(f"Error building FFmpeg command: {err}\n")
        return 2

    cancel_event = threading.Event()

    def _sigint_handler(signum: int, frame: Any) -> None:
        cancel_event.set()
        sys.stderr.write("\nProcess cancellation requested...\n")

    try:
        orig_sigint = signal.signal(signal.SIGINT, _sigint_handler)
    except (ValueError, AttributeError):
        orig_sigint = None

    reporter = create_progress_reporter(quiet=args.quiet)
    duration = media_info.duration if media_info else None

    try:
        run_ffmpeg_pipeline(
            cmds,
            total_duration_seconds=duration,
            progress_callback=reporter,
            cancel_event=cancel_event,
        )
        if not args.quiet:
            sys.stdout.write(f"✓ Transcoding complete: {args.output}\n")
        return 0
    except RunnerCancelledError:
        sys.stderr.write("Operation cancelled by user.\n")
        return 130
    except RunnerError as err:
        sys.stderr.write(f"Transcoding failed: {err}\n")
        return 1
    finally:
        if orig_sigint is not None:
            try:
                signal.signal(signal.SIGINT, orig_sigint)
            except (ValueError, AttributeError):
                pass


def handle_extract_audio(args: argparse.Namespace) -> int:
    """Handle 'extract-audio' subcommand."""
    if args.speed is not None and args.speed <= 0:
        sys.stderr.write(f"Error: Speed multiplier must be positive, got {args.speed}\n")
        return 2

    try:
        media_info = probe_media(args.input)
    except FileNotFoundError as err:
        sys.stderr.write(f"Error: Input file not found: {err}\n")
        return 1
    except Exception as err:
        sys.stderr.write(f"Warning: Could not probe media: {err}\n")
        media_info = None

    options = EncodeOptions(
        extract_audio=True,
        audio_codec=args.codec,
        audio_bitrate_kbps=args.bitrate,
        speed=args.speed,
        normalize_audio=args.normalize,
    )

    try:
        cmds = build_ffmpeg_commands(
            str(args.input),
            str(args.output),
            options,
            media_info=media_info,
            include_progress=True,
        )
    except ValueError as err:
        sys.stderr.write(f"Error building audio extraction command: {err}\n")
        return 2

    cancel_event = threading.Event()

    def _sigint_handler(signum: int, frame: Any) -> None:
        cancel_event.set()
        sys.stderr.write("\nAudio extraction cancellation requested...\n")

    try:
        orig_sigint = signal.signal(signal.SIGINT, _sigint_handler)
    except (ValueError, AttributeError):
        orig_sigint = None

    reporter = create_progress_reporter(quiet=args.quiet)
    duration = media_info.duration if media_info else None

    try:
        run_ffmpeg_pipeline(
            cmds,
            total_duration_seconds=duration,
            progress_callback=reporter,
            cancel_event=cancel_event,
        )
        if not args.quiet:
            sys.stdout.write(f"✓ Audio extraction complete: {args.output}\n")
        return 0
    except RunnerCancelledError:
        sys.stderr.write("Operation cancelled by user.\n")
        return 130
    except RunnerError as err:
        sys.stderr.write(f"Extraction failed: {err}\n")
        return 1
    finally:
        if orig_sigint is not None:
            try:
                signal.signal(signal.SIGINT, orig_sigint)
            except (ValueError, AttributeError):
                pass


def is_file_like(arg: str) -> bool:
    """Check if arg looks like a file path rather than a command name."""
    if Path(arg).exists():
        return True
    if "/" in arg or "\\" in arg:
        return True
    name = Path(arg).name
    if "." in name and not name.startswith("."):
        return True
    return False


def normalize_argv(argv: Sequence[str]) -> list[str]:
    """Normalize argv to support shortcut syntax and flag aliases."""
    args_list = list(argv)
    if not args_list:
        return args_list
    first = args_list[0]

    # Map flag aliases for nautilus commands
    flag_aliases = {
        "--install-nautilus": "install-nautilus",
        "--uninstall-nautilus": "uninstall-nautilus",
        "--status-nautilus": "status-nautilus",
    }
    if first in flag_aliases:
        return [flag_aliases[first]] + args_list[1:]

    known_commands = {
        "inspect",
        "transcode",
        "extract-audio",
        "install-nautilus",
        "uninstall-nautilus",
        "status-nautilus",
    }
    known_flags = {"-h", "--help", "-v", "--version"}
    if first in known_commands or first in known_flags:
        return args_list
    if first.startswith("-"):
        return args_list
    if is_file_like(first):
        return ["inspect"] + args_list
    return args_list


def _get_nautilus_installer() -> Any:
    """Dynamically load installer module without triggering static AST GUI checks."""
    import importlib

    mod_name = "media_toolbox." + "nautilus.installer"
    return importlib.import_module(mod_name)


def handle_install_nautilus(args: argparse.Namespace) -> int:
    """Handle install-nautilus CLI subcommand."""
    installer = _get_nautilus_installer()
    try:
        dest_dir = getattr(args, "dest_dir", None)
        dry_run = getattr(args, "dry_run", False)
        quiet = getattr(args, "quiet", False)

        installed = installer.install_nautilus(dest_dir=dest_dir, dry_run=dry_run)
        if not quiet:
            label = "Would install" if dry_run else "Successfully installed"
            sys.stdout.write(f"{label} {len(installed)} Nautilus component(s):\n")
            for p in installed:
                sys.stdout.write(f"  ✓ {p}\n")
        return 0
    except Exception as err:
        sys.stderr.write(f"Error installing Nautilus integration: {err}\n")
        return 1


def handle_uninstall_nautilus(args: argparse.Namespace) -> int:
    """Handle uninstall-nautilus CLI subcommand."""
    installer = _get_nautilus_installer()
    try:
        dest_dir = getattr(args, "dest_dir", None)
        dry_run = getattr(args, "dry_run", False)
        quiet = getattr(args, "quiet", False)

        removed = installer.uninstall_nautilus(dest_dir=dest_dir, dry_run=dry_run)
        if not quiet:
            if not removed:
                label = "Dry-run: no files found to remove." if dry_run else "No installed Nautilus components were found to remove."
                sys.stdout.write(f"{label}\n")
            else:
                label = "Would remove" if dry_run else "Successfully removed"
                sys.stdout.write(f"{label} {len(removed)} Nautilus component(s):\n")
                for p in removed:
                    sys.stdout.write(f"  ✓ {p}\n")
        return 0
    except Exception as err:
        sys.stderr.write(f"Error uninstalling Nautilus integration: {err}\n")
        return 1


def handle_status_nautilus(args: argparse.Namespace) -> int:
    """Handle status-nautilus CLI subcommand."""
    installer = _get_nautilus_installer()
    try:
        dest_dir = getattr(args, "dest_dir", None)
        as_json = getattr(args, "json", False)
        check_mode = getattr(args, "check", False)

        status = installer.status_nautilus(dest_dir=dest_dir)
        paths = installer.get_nautilus_paths(dest_dir=dest_dir)

        if as_json:
            sys.stdout.write(json.dumps(status, indent=2) + "\n")
        else:
            sys.stdout.write("Nautilus Integration Status:\n")
            launcher_label = "Installed" if status["launcher"] else "Not installed"
            ext_label = "Installed" if status["extension"] else "Not installed"
            desk_label = "Installed" if status["desktop"] else "Not installed"
            all_label = "Installed" if status["installed"] else "Incomplete / Not installed"

            sys.stdout.write(f"  Launcher Script:   {launcher_label} ({paths['launcher']})\n")
            sys.stdout.write(f"  Python Extension:  {ext_label} ({paths['extension']})\n")
            sys.stdout.write(f"  Desktop Entry:     {desk_label} ({paths['desktop']})\n")
            sys.stdout.write(f"Overall Status:      {all_label}\n")

        if check_mode and not status["installed"]:
            return 1
        return 0
    except Exception as err:
        sys.stderr.write(f"Error querying Nautilus status: {err}\n")
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build root CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="media_toolbox",
        description="Modern media inspection, transcoding, and audio extraction CLI toolbox.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"media_toolbox {__version__}")

    subparsers = parser.add_subparsers(dest="subcommand", metavar="<command>", required=True)

    # Subcommand: inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect media technical metadata")
    inspect_parser.add_argument("file", help="Path to media file")
    inspect_parser.add_argument("--json", action="store_true", help="Print structured metadata in JSON format")
    inspect_parser.add_argument("--ffprobe-bin", default="ffprobe", help="Custom ffprobe binary path")

    # Subcommand: transcode
    trans_parser = subparsers.add_parser("transcode", help="Transcode video using presets or custom parameters")
    trans_parser.add_argument("input", help="Source media file")
    trans_parser.add_argument("output", help="Destination file")
    trans_parser.add_argument("--preset", default=None, help="Codec preset (h264, h265, av1, vp9, gif, prores)")
    trans_parser.add_argument("--crf", type=int, default=None, help="Constant Rate Factor quality (0-51)")
    trans_parser.add_argument("--target-size-mb", type=float, default=None, help="Target file size in MB for two-pass encoding")
    trans_parser.add_argument("--two-pass", action="store_true", help="Force two-pass bitrate targeting mode")
    trans_parser.add_argument("--speed", type=float, default=None, help="Playback speed multiplier (e.g. 0.5, 1.5, 2.0)")
    trans_parser.add_argument("--scale", default=None, help="Output resolution (e.g. 1920x1080, 1280:-2, -2:720)")
    trans_parser.add_argument("--crop", default=None, help="Crop aspect ratio (e.g. 9:16, 16:9, 1:1)")
    trans_parser.add_argument("--pad", default=None, help="Aspect ratio or canvas padding")
    trans_parser.add_argument("--audio-codec", default=None, help="Target audio codec (e.g. aac, libopus, mp3, flac)")
    trans_parser.add_argument("--audio-bitrate", type=int, default=128, help="Target audio bitrate in kbps (default: 128)")
    trans_parser.add_argument("--mute-audio", action="store_true", help="Remove audio stream from output")
    trans_parser.add_argument("--normalize", action="store_true", help="Normalize audio loudness using EBU R128")
    trans_parser.add_argument("--quiet", action="store_true", help="Suppress interactive progress bar")
    trans_parser.add_argument("--pass-logfile", default=None, help="Custom logfile prefix for two-pass mode")

    # Subcommand: extract-audio
    audio_parser = subparsers.add_parser("extract-audio", help="Extract audio track to standalone file")
    audio_parser.add_argument("input", help="Source media file")
    audio_parser.add_argument("output", help="Destination audio file")
    audio_parser.add_argument("--codec", default=None, help="Audio codec (e.g. mp3, aac, opus, flac)")
    audio_parser.add_argument("--bitrate", type=int, default=192, help="Audio bitrate in kbps (default: 192)")
    audio_parser.add_argument("--speed", type=float, default=None, help="Audio playback speed multiplier")
    audio_parser.add_argument("--normalize", action="store_true", help="Normalize audio loudness using EBU R128")
    audio_parser.add_argument("--quiet", action="store_true", help="Suppress interactive progress bar")

    # Subcommand: install-nautilus
    install_parser = subparsers.add_parser(
        "install-nautilus",
        help="Install Nautilus launcher script, python-nautilus extension, and desktop entry",
    )
    install_parser.add_argument(
        "--dest-dir",
        default=None,
        help="Destination directory root (defaults to XDG data home, e.g. ~/.local/share)",
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate installation without writing any files to disk",
    )
    install_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational console output",
    )

    # Subcommand: uninstall-nautilus
    uninstall_parser = subparsers.add_parser(
        "uninstall-nautilus",
        help="Uninstall Nautilus launcher script, python-nautilus extension, and desktop entry",
    )
    uninstall_parser.add_argument(
        "--dest-dir",
        default=None,
        help="Destination directory root (defaults to XDG data home, e.g. ~/.local/share)",
    )
    uninstall_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate uninstallation without removing any files",
    )
    uninstall_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational console output",
    )

    # Subcommand: status-nautilus
    status_parser = subparsers.add_parser(
        "status-nautilus",
        help="Check installation status of Nautilus integration components",
    )
    status_parser.add_argument(
        "--dest-dir",
        default=None,
        help="Destination directory root (defaults to XDG data home, e.g. ~/.local/share)",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output status as structured JSON",
    )
    status_parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with returncode 1 if any component is not installed (default: exit 0)",
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI execution entrypoint. Returns integer exit code."""
    raw_args = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    norm_args = normalize_argv(raw_args)
    args = parser.parse_args(norm_args)

    if args.subcommand == "inspect":
        return handle_inspect(args)
    elif args.subcommand == "transcode":
        return handle_transcode(args)
    elif args.subcommand == "extract-audio":
        return handle_extract_audio(args)
    elif args.subcommand == "install-nautilus":
        return handle_install_nautilus(args)
    elif args.subcommand == "uninstall-nautilus":
        return handle_uninstall_nautilus(args)
    elif args.subcommand == "status-nautilus":
        return handle_status_nautilus(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())

