"""
Bitrate calculation engine for media_toolbox.

This module provides deterministic video bitrate calculation for two-pass
encoding targeting fixed file sizes, incorporating container multiplexing
overhead safety margins and minimum bitrate clamping.

INVARIANT: Zero GUI imports (gi, Gtk, Adw, etc.).
"""

from __future__ import annotations

import math

DEFAULT_AUDIO_BITRATE_KBPS: int = 128
DEFAULT_MUX_OVERHEAD_MARGIN: float = 0.03  # 3% container safety margin
DEFAULT_MIN_VIDEO_BITRATE_KBPS: int = 64  # Minimum video bitrate floor
KBITS_PER_MB: float = 8192.0  # 1 MiB = 1024 * 1024 * 8 / 1024 = 8192 kbits

__all__ = [
    "calculate_target_video_bitrate",
    "DEFAULT_AUDIO_BITRATE_KBPS",
    "DEFAULT_MUX_OVERHEAD_MARGIN",
    "DEFAULT_MIN_VIDEO_BITRATE_KBPS",
    "KBITS_PER_MB",
]


def calculate_target_video_bitrate(
    target_size_mb: float,
    duration_seconds: float,
    audio_bitrate_kbps: int = DEFAULT_AUDIO_BITRATE_KBPS,
    mux_overhead_margin: float = DEFAULT_MUX_OVERHEAD_MARGIN,
    min_video_bitrate_kbps: int = DEFAULT_MIN_VIDEO_BITRATE_KBPS,
) -> int:
    """
    Calculate target video bitrate in kbps for two-pass encoding.

    Formula:
        total_kbits = target_size_mb * 8192.0
        usable_kbits = total_kbits * (1.0 - mux_overhead_margin)
        total_bitrate_kbps = usable_kbits / duration_seconds
        net_video_bitrate_kbps = total_bitrate_kbps - audio_bitrate_kbps
        video_bitrate_kbps = max(min_video_bitrate_kbps, int(round(net_video_bitrate_kbps)))

    Parameters:
        target_size_mb: Desired total output file size in Megabytes (MiB).
        duration_seconds: Total duration of the media in seconds.
        audio_bitrate_kbps: Allocated audio bitrate in kbps. Use 0 for silent or muted video.
        mux_overhead_margin: Safety margin fraction reserved for container overhead (0.0 <= margin < 1.0).
        min_video_bitrate_kbps: Floor video bitrate to prevent invalid or unplayable output.

    Returns:
        Target video bitrate in kilobits per second (kbps) as an integer >= min_video_bitrate_kbps.

    Raises:
        ValueError: If duration_seconds <= 0 or not finite.
        ValueError: If target_size_mb <= 0 or not finite.
        ValueError: If audio_bitrate_kbps < 0.
        ValueError: If mux_overhead_margin is not in [0.0, 1.0).
        ValueError: If min_video_bitrate_kbps < 0.
    """
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError(f"duration_seconds must be a positive finite number, got {duration_seconds}")

    if not math.isfinite(target_size_mb) or target_size_mb <= 0:
        raise ValueError(f"target_size_mb must be a positive finite number, got {target_size_mb}")

    if audio_bitrate_kbps < 0:
        raise ValueError(f"audio_bitrate_kbps cannot be negative, got {audio_bitrate_kbps}")

    if not (0.0 <= mux_overhead_margin < 1.0):
        raise ValueError(
            f"mux_overhead_margin must be in range [0.0, 1.0), got {mux_overhead_margin}"
        )

    if min_video_bitrate_kbps < 0:
        raise ValueError(f"min_video_bitrate_kbps cannot be negative, got {min_video_bitrate_kbps}")

    total_kbits = float(target_size_mb) * KBITS_PER_MB
    usable_kbits = total_kbits * (1.0 - float(mux_overhead_margin))
    total_bitrate_kbps = usable_kbits / float(duration_seconds)

    net_video_bitrate_kbps = total_bitrate_kbps - float(audio_bitrate_kbps)
    clamped_video_bitrate = max(int(min_video_bitrate_kbps), int(round(net_video_bitrate_kbps)))
    return clamped_video_bitrate
