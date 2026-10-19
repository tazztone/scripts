"""
Composable FFmpeg filtergraph generator for media_toolbox.

Provides deterministic video and audio filter chain construction:
- Video: crop, scale (even-dimension snapping), pad, setpts, fps
- Audio: multi-stage atempo splitting, EBU R128 loudness normalization, volume boost

INVARIANT: Must have ZERO imports from GUI toolkits (gi, Gtk, Adw, etc.).
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

ASPECT_RATIO_CROPS: dict[str, str] = {
    "9:16": "crop=ih*(9/16):ih:(iw-ow)/2:0",
    "16:9": "crop=iw:iw*(9/16):0:(ih-oh)/2",
    "1:1": "crop=min(iw\\,ih):min(iw\\,ih):(iw-ow)/2:(ih-oh)/2",
    "4:3": "crop=ih*(4/3):ih:(iw-ow)/2:0",
    "21:9": "crop=iw:iw*(9/21):0:(ih-oh)/2",
}

EBU_R128_LOUDNORM: str = "loudnorm=I=-23:LRA=7:TP=-1.5"


def build_scale_filter(scale: tuple[int, int]) -> str:
    """
    Generate scale filter with even dimension snapping.

    Accepts:
        (w, h) where w, h > 0: snaps odd dimensions down to even integers.
        (w, -1) or (w, -2): snaps w to even, uses -2 for height auto-even scaling.
        (-1, h) or (-2, h): snaps h to even, uses -2 for width auto-even scaling.

    Raises:
        ValueError: If scale dimensions are non-positive or invalid.
    """
    w, h = scale
    if w <= 0 and h <= 0:
        raise ValueError(f"Scale dimensions cannot both be non-positive: {scale}")
    if w == 0 or h == 0:
        raise ValueError(f"Scale dimensions cannot be 0: {scale}")

    if w > 0 and h > 0:
        w_even = max(2, w - (w % 2))
        h_even = max(2, h - (h % 2))
        return f"scale={w_even}:{h_even}"
    elif w > 0 and h in (-1, -2):
        w_even = max(2, w - (w % 2))
        return f"scale={w_even}:-2"
    elif w in (-1, -2) and h > 0:
        h_even = max(2, h - (h % 2))
        return f"scale=-2:{h_even}"
    else:
        raise ValueError(f"Invalid scale dimensions: {scale}")


def build_crop_filter(crop: str) -> str:
    """
    Generate center crop filter for aspect ratios or custom geometries.
    """
    crop_clean = crop.strip()
    if crop_clean in ASPECT_RATIO_CROPS:
        return ASPECT_RATIO_CROPS[crop_clean]
    if crop_clean.startswith("crop="):
        return crop_clean
    return f"crop={crop_clean}"


def build_pad_filter(pad: str | tuple[int, int]) -> str:
    """
    Generate aspect ratio or canvas pad filter.
    """
    if isinstance(pad, tuple):
        w, h = pad
        w_even = max(2, w - (w % 2))
        h_even = max(2, h - (h % 2))
        return f"pad={w_even}:{h_even}:(ow-iw)/2:(oh-ih)/2:black"

    pad_clean = pad.strip()
    if pad_clean.startswith("pad="):
        return pad_clean
    if ":" in pad_clean and pad_clean.count(":") == 1:
        w_s, h_s = pad_clean.split(":")
        return f"pad={w_s}:{h_s}:(ow-iw)/2:(oh-ih)/2:black"
    return f"pad={pad_clean}"


def build_setpts_filter(speed: float) -> str:
    """
    Generate setpts filter for speed adjustment: setpts=(1.0/speed)*PTS.
    """
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError(f"Speed must be positive and finite, got {speed}")
    s_str = f"{speed:.1f}" if speed == int(speed) else f"{speed:g}"
    return f"setpts=(1.0/{s_str})*PTS"


def build_fps_filter(fps: int | float) -> str:
    """
    Generate fps filter: fps=fps={rate}.
    """
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError(f"Frame rate must be positive and finite, got {fps}")
    fps_str = str(int(fps)) if isinstance(fps, int) or (isinstance(fps, float) and fps.is_integer()) else f"{fps:g}"
    return f"fps=fps={fps_str}"


def build_video_filter(
    scale: Optional[tuple[int, int]] = None,
    crop: Optional[str] = None,
    pad: Optional[str | tuple[int, int]] = None,
    speed: Optional[float] = None,
    fps: Optional[int | float] = None,
) -> list[str]:
    """
    Construct ordered video filter chain:
    Order: crop -> scale -> pad -> setpts -> fps
    """
    filters: list[str] = []
    if crop is not None:
        filters.append(build_crop_filter(crop))
    if scale is not None:
        filters.append(build_scale_filter(scale))
    if pad is not None:
        filters.append(build_pad_filter(pad))
    if speed is not None:
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError(f"Speed must be positive and finite, got {speed}")
        if abs(speed - 1.0) >= 1e-4:
            filters.append(build_setpts_filter(speed))
    if fps is not None:
        filters.append(build_fps_filter(fps))
    return filters


def build_atempo_chain(speed: float) -> list[str]:
    """
    Split speed multiplier into chained atempo filters within [0.5, 2.0].
    Multipliers >2.0x are split into atempo=2.0 chains and <0.5x into atempo=0.5 chains.
    """
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError(f"Speed must be positive and finite, got {speed}")
    if abs(speed - 1.0) < 1e-4:
        return []

    filters: list[str] = []
    current = speed
    while current > 2.0:
        filters.append("atempo=2.0")
        current /= 2.0
    while current < 0.5:
        filters.append("atempo=0.5")
        current /= 0.5

    if abs(current - 1.0) >= 1e-4 or not filters:
        s = f"{current:.4f}".rstrip("0").rstrip(".")
        if "." not in s:
            s += ".0"
        filters.append(f"atempo={s}")
    return filters


def build_audio_filter(
    speed: Optional[float] = None,
    normalize_loudness: bool = False,
    volume_boost_db: Optional[float] = None,
) -> list[str]:
    """
    Construct ordered audio filter chain:
    Order: atempo -> loudnorm -> volume
    """
    filters: list[str] = []
    if speed is not None:
        filters.extend(build_atempo_chain(speed))
    if normalize_loudness:
        filters.append(EBU_R128_LOUDNORM)
    if volume_boost_db is not None and abs(volume_boost_db) >= 1e-4:
        filters.append(f"volume={volume_boost_db:g}dB")
    return filters


def join_filter_chain(filters: Sequence[str]) -> str:
    """Join filter list into comma-delimited filterchain string."""
    return ",".join(filters)


def build_video_filter_args(
    scale: Optional[tuple[int, int]] = None,
    crop: Optional[str] = None,
    pad: Optional[str | tuple[int, int]] = None,
    speed: Optional[float] = None,
    fps: Optional[int | float] = None,
) -> list[str]:
    """Return ['-vf', chain] if filters present, else []."""
    filters = build_video_filter(scale=scale, crop=crop, pad=pad, speed=speed, fps=fps)
    return ["-vf", join_filter_chain(filters)] if filters else []


def build_audio_filter_args(
    speed: Optional[float] = None,
    normalize_loudness: bool = False,
    volume_boost_db: Optional[float] = None,
) -> list[str]:
    """Return ['-af', chain] if filters present, else []."""
    filters = build_audio_filter(
        speed=speed,
        normalize_loudness=normalize_loudness,
        volume_boost_db=volume_boost_db,
    )
    return ["-af", join_filter_chain(filters)] if filters else []
