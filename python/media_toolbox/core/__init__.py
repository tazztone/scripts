"""
Core engine for media_toolbox.

Provides domain models, probing, bitrate math, filtergraphs, presets, builder, and runner.
INVARIANT: ZERO GUI imports.
"""

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
    parse_rotation,
    parse_stream_fps,
    probe_media,
)
from media_toolbox.core.bitrate import (
    calculate_target_video_bitrate,
    DEFAULT_AUDIO_BITRATE_KBPS,
    DEFAULT_MUX_OVERHEAD_MARGIN,
    DEFAULT_MIN_VIDEO_BITRATE_KBPS,
)

__all__ = [
    "AudioStream",
    "EncodeOptions",
    "FormatInfo",
    "MediaInfo",
    "MediaToolboxError",
    "ProbeError",
    "ProgressEvent",
    "VideoStream",
    "parse_frame_rate",
    "parse_optional_float",
    "parse_optional_int",
    "parse_probe_json",
    "parse_rotation",
    "parse_stream_fps",
    "probe_media",
    "calculate_target_video_bitrate",
    "DEFAULT_AUDIO_BITRATE_KBPS",
    "DEFAULT_MUX_OVERHEAD_MARGIN",
    "DEFAULT_MIN_VIDEO_BITRATE_KBPS",
]
