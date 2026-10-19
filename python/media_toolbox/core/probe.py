"""
Media probing and JSON deserialization engine.

Invokes ffprobe with JSON output formatting and deserializes container
and stream metadata into immutable MediaInfo models.

INVARIANT: Must have ZERO imports from GUI toolkits (gi, Gtk, Adw, etc.).
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
import subprocess
from typing import Any, Optional

from media_toolbox.core.models import (
    AudioStream,
    FormatInfo,
    MediaInfo,
    ProbeError,
    VideoStream,
)

__all__ = [
    "probe_media",
    "parse_probe_json",
    "parse_frame_rate",
    "parse_stream_fps",
    "parse_optional_float",
    "parse_optional_int",
    "parse_rotation",
    "is_attached_pic",
    "ProbeError",
]


def parse_optional_float(val: Any) -> Optional[float]:
    """
    Safely parse float values from ffprobe metadata.

    Returns None for None, empty strings, 'N/A', negative values, or invalid floats.
    """
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str.upper() == "N/A":
        return None
    try:
        f = float(val_str)
        return f if f >= 0.0 else None
    except (ValueError, OverflowError):
        return None


def parse_optional_int(val: Any) -> Optional[int]:
    """
    Safely parse integer values from ffprobe metadata.

    Handles strings, floats, ints, 'N/A', and empty values.
    """
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str.upper() == "N/A":
        return None
    try:
        return int(float(val_str))
    except (ValueError, OverflowError):
        return None


def parse_frame_rate(val: Any) -> Optional[float]:
    """
    Safely evaluate fractional frame rates (e.g. '24000/1001', '30/1').

    Guards against '0/0', '0/1', 'N/A', non-numeric inputs, and division by zero.
    Returns None if frame rate is <= 0 or unparseable.
    """
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str.upper() == "N/A":
        return None
    try:
        frac = Fraction(val_str)
        if frac.numerator <= 0 or frac.denominator <= 0:
            return None
        return float(frac)
    except (ZeroDivisionError, ValueError, OverflowError):
        return None


def parse_stream_fps(stream: dict[str, Any]) -> Optional[float]:
    """
    Extract frame rate from a stream dictionary.

    Checks r_frame_rate first, falling back to avg_frame_rate for VFR streams.
    """
    fps = parse_frame_rate(stream.get("r_frame_rate"))
    if fps is None:
        fps = parse_frame_rate(stream.get("avg_frame_rate"))
    return fps


def parse_rotation(stream: dict[str, Any]) -> int:
    """
    Extract and normalize stream rotation angle in degrees [0, 360).

    Inspects side_data_list (Display Matrix in modern FFmpeg) and tags.rotate (legacy).
    """
    side_data = stream.get("side_data_list")
    if isinstance(side_data, list):
        for sd in side_data:
            if isinstance(sd, dict) and "rotation" in sd:
                try:
                    rot = int(float(sd["rotation"]))
                    return (rot % 360 + 360) % 360
                except (ValueError, TypeError):
                    pass

    tags = stream.get("tags")
    if isinstance(tags, dict) and "rotate" in tags:
        try:
            rot = int(float(tags["rotate"]))
            return (rot % 360 + 360) % 360
        except (ValueError, TypeError):
            pass

    return 0


def is_attached_pic(stream: dict[str, Any]) -> bool:
    """True if stream represents attached picture (e.g. ID3 album art)."""
    disposition = stream.get("disposition")
    if isinstance(disposition, dict):
        val = disposition.get("attached_pic")
        if val is not None:
            try:
                return int(val) == 1
            except (ValueError, TypeError):
                return False
    return False


def parse_probe_json(data: dict[str, Any]) -> MediaInfo:
    """
    Deserialize ffprobe JSON dictionary into strongly typed MediaInfo.

    Raises:
        ProbeError: If data is not a dict, missing 'format' or 'streams', or malformed.
    """
    if not isinstance(data, dict):
        raise ProbeError(f"Expected probe data dict, got {type(data).__name__}")

    if "format" not in data or not isinstance(data["format"], dict):
        raise ProbeError("Probe data missing required 'format' section")

    if "streams" not in data or not isinstance(data["streams"], list):
        raise ProbeError("Probe data missing required 'streams' section or streams is not a list")

    format_data = data["format"]
    raw_streams = data["streams"]

    format_info = FormatInfo(
        filename=str(format_data.get("filename", "")),
        format_name=str(format_data.get("format_name", "")),
        duration=parse_optional_float(format_data.get("duration")),
        size_bytes=parse_optional_int(format_data.get("size")),
        bit_rate=parse_optional_int(format_data.get("bit_rate")),
    )

    video_streams: list[VideoStream] = []
    audio_streams: list[AudioStream] = []

    for s in raw_streams:
        if not isinstance(s, dict):
            continue
        codec_type = s.get("codec_type")
        if codec_type == "video":
            video_streams.append(
                VideoStream(
                    index=int(s.get("index") or 0),
                    codec_name=str(s.get("codec_name", "")),
                    width=int(s.get("width") or 0),
                    height=int(s.get("height") or 0),
                    fps=parse_stream_fps(s),
                    bit_rate=parse_optional_int(s.get("bit_rate")),
                    duration=parse_optional_float(s.get("duration")),
                    pix_fmt=str(s["pix_fmt"]) if s.get("pix_fmt") else None,
                    rotation=parse_rotation(s),
                    is_attached_pic=is_attached_pic(s),
                )
            )
        elif codec_type == "audio":
            audio_streams.append(
                AudioStream(
                    index=int(s.get("index") or 0),
                    codec_name=str(s.get("codec_name", "")),
                    channels=int(s.get("channels") or 0),
                    sample_rate=int(s.get("sample_rate") or 0),
                    channel_layout=str(s["channel_layout"]) if s.get("channel_layout") else None,
                    bit_rate=parse_optional_int(s.get("bit_rate")),
                    duration=parse_optional_float(s.get("duration")),
                )
            )

    return MediaInfo(
        format=format_info,
        video_streams=tuple(video_streams),
        audio_streams=tuple(audio_streams),
    )


def probe_media(file_path: str | Path, ffprobe_bin: str = "ffprobe") -> MediaInfo:
    """
    Probe a media file using ffprobe and return strongly typed MediaInfo.

    Args:
        file_path: Path to target media file.
        ffprobe_bin: Path or binary name of ffprobe executable.

    Returns:
        Populated MediaInfo dataclass.

    Raises:
        FileNotFoundError: If input file_path does not exist.
        ProbeError: If ffprobe execution fails or emits malformed data.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Media file not found: {path}")

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        raise ProbeError(f"ffprobe binary not found at '{ffprobe_bin}'") from e
    except OSError as e:
        raise ProbeError(f"Failed to execute ffprobe: {e}") from e

    if proc.returncode != 0:
        err = proc.stderr.strip() or f"exit code {proc.returncode}"
        raise ProbeError(f"ffprobe failed with exit code {proc.returncode}: {err}")

    stdout = proc.stdout.strip()
    if not stdout:
        raise ProbeError("ffprobe returned empty output")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise ProbeError(f"Failed to parse ffprobe output as JSON: {e}") from e

    return parse_probe_json(data)
