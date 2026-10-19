"""
Unit tests for media_toolbox.core.filtergraph.

Verifies:
- Video transformations (crop, scale with even snapping, pad, setpts, fps)
- Strict pipeline execution ordering
- Audio transformations (multi-stage atempo splitting, loudnorm, volume boost)
- AST headless invariant (zero GUI imports)
"""

from __future__ import annotations

import ast
from pathlib import Path
import pytest

from media_toolbox.core.filtergraph import (
    ASPECT_RATIO_CROPS,
    EBU_R128_LOUDNORM,
    build_atempo_chain,
    build_audio_filter,
    build_audio_filter_args,
    build_crop_filter,
    build_fps_filter,
    build_pad_filter,
    build_scale_filter,
    build_setpts_filter,
    build_video_filter,
    build_video_filter_args,
    join_filter_chain,
)


def test_atempo_identity() -> None:
    """Exact 1.0x speed requires no atempo filter."""
    assert build_atempo_chain(1.0) == []


def test_atempo_identity_near() -> None:
    """Speed within floating point tolerance of 1.0 requires no atempo filter."""
    assert build_atempo_chain(1.00001) == []
    assert build_atempo_chain(0.99999) == []


def test_atempo_upper_bound() -> None:
    """Speed 2.0x generates a single atempo=2.0 filter."""
    assert build_atempo_chain(2.0) == ["atempo=2.0"]


def test_atempo_lower_bound() -> None:
    """Speed 0.5x generates a single atempo=0.5 filter."""
    assert build_atempo_chain(0.5) == ["atempo=0.5"]


def test_atempo_mid_speed() -> None:
    """Speed between 0.5 and 2.0 generates a single atempo filter."""
    assert build_atempo_chain(1.5) == ["atempo=1.5"]
    assert build_atempo_chain(0.75) == ["atempo=0.75"]


def test_atempo_3x() -> None:
    """Speed 3.0x splits into atempo=2.0 and atempo=1.5."""
    assert build_atempo_chain(3.0) == ["atempo=2.0", "atempo=1.5"]


def test_atempo_4x() -> None:
    """Speed 4.0x splits into atempo=2.0 and atempo=2.0."""
    assert build_atempo_chain(4.0) == ["atempo=2.0", "atempo=2.0"]


def test_atempo_5x() -> None:
    """Speed 5.0x splits into atempo=2.0, atempo=2.0, and atempo=1.25."""
    assert build_atempo_chain(5.0) == ["atempo=2.0", "atempo=2.0", "atempo=1.25"]


def test_atempo_0_25x() -> None:
    """Speed 0.25x splits into two atempo=0.5 filters."""
    assert build_atempo_chain(0.25) == ["atempo=0.5", "atempo=0.5"]


def test_atempo_0_125x() -> None:
    """Speed 0.125x splits into three atempo=0.5 filters."""
    assert build_atempo_chain(0.125) == ["atempo=0.5", "atempo=0.5", "atempo=0.5"]


@pytest.mark.parametrize("invalid_speed", [-2.0, -0.5, 0.0, float("nan"), float("inf"), float("-inf")])
def test_atempo_invalid_values(invalid_speed: float) -> None:
    """Non-positive or non-finite speed values raise ValueError."""
    with pytest.raises(ValueError):
        build_atempo_chain(invalid_speed)


def test_video_filter_empty() -> None:
    """Default video filter returns empty list."""
    assert build_video_filter() == []


def test_video_filter_scale_exact() -> None:
    """Explicit even dimensions format directly."""
    assert build_scale_filter((1920, 1080)) == "scale=1920:1080"
    assert build_scale_filter((1280, 720)) == "scale=1280:720"


def test_video_filter_scale_odd_snap() -> None:
    """Odd dimensions snap down to even numbers for yuv420p compliance."""
    assert build_scale_filter((853, 481)) == "scale=852:480"
    assert build_scale_filter((301, 199)) == "scale=300:198"


def test_video_filter_scale_auto_dimensions() -> None:
    """-1 or -2 auto dimensions snap correctly to -2."""
    assert build_scale_filter((1280, -1)) == "scale=1280:-2"
    assert build_scale_filter((1280, -2)) == "scale=1280:-2"
    assert build_scale_filter((853, -1)) == "scale=852:-2"
    assert build_scale_filter((-1, 720)) == "scale=-2:720"
    assert build_scale_filter((-2, 720)) == "scale=-2:720"
    assert build_scale_filter((-1, 481)) == "scale=-2:480"


@pytest.mark.parametrize("invalid_scale", [(0, 0), (1920, 0), (0, 1080), (-1, -1), (-2, -2), (-3, 720), (720, -3)])
def test_video_filter_scale_invalid(invalid_scale: tuple[int, int]) -> None:
    """Invalid scale dimensions raise ValueError."""
    with pytest.raises(ValueError):
        build_scale_filter(invalid_scale)


def test_video_filter_crop_aspect_ratios() -> None:
    """Standard aspect ratio crops use correct center-crop formulas with comma escaping."""
    assert build_crop_filter("9:16") == "crop=ih*(9/16):ih:(iw-ow)/2:0"
    assert build_crop_filter("16:9") == "crop=iw:iw*(9/16):0:(ih-oh)/2"
    assert build_crop_filter("1:1") == "crop=min(iw\\,ih):min(iw\\,ih):(iw-ow)/2:(ih-oh)/2"
    assert build_crop_filter("4:3") == "crop=ih*(4/3):ih:(iw-ow)/2:0"
    assert build_crop_filter("21:9") == "crop=iw:iw*(9/21):0:(ih-oh)/2"


def test_video_filter_crop_custom() -> None:
    """Custom crop specifications pass through properly."""
    assert build_crop_filter("crop=1280:720:0:0") == "crop=1280:720:0:0"
    assert build_crop_filter("1280:720:0:0") == "crop=1280:720:0:0"


def test_video_filter_pad() -> None:
    """Pad specifications generate center-padding filters with black background."""
    assert build_pad_filter("1920:1080") == "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
    assert build_pad_filter((1920, 1080)) == "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
    assert build_pad_filter((1921, 1081)) == "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
    assert build_pad_filter("pad=1920:1080:0:0:white") == "pad=1920:1080:0:0:white"


def test_video_filter_speed() -> None:
    """Speed adjustment creates reciprocal PTS multiplier."""
    assert build_setpts_filter(2.0) == "setpts=(1.0/2.0)*PTS"
    assert build_setpts_filter(0.5) == "setpts=(1.0/0.5)*PTS"
    assert build_setpts_filter(1.5) == "setpts=(1.0/1.5)*PTS"


@pytest.mark.parametrize("invalid_speed", [-1.0, 0.0, float("nan"), float("inf")])
def test_video_filter_speed_invalid(invalid_speed: float) -> None:
    """Invalid video speed raises ValueError."""
    with pytest.raises(ValueError):
        build_setpts_filter(invalid_speed)


def test_video_filter_fps() -> None:
    """FPS rate filter formats correctly."""
    assert build_fps_filter(30) == "fps=fps=30"
    assert build_fps_filter(24) == "fps=fps=24"
    assert build_fps_filter(29.97) == "fps=fps=29.97"


@pytest.mark.parametrize("invalid_fps", [-1, 0, float("nan")])
def test_video_filter_fps_invalid(invalid_fps: int | float) -> None:
    """Invalid FPS raises ValueError."""
    with pytest.raises(ValueError):
        build_fps_filter(invalid_fps)


def test_video_filter_pipeline_ordering() -> None:
    """Video filters are assembled in strict order: crop -> scale -> pad -> setpts -> fps."""
    filters = build_video_filter(
        crop="16:9",
        scale=(1280, 720),
        pad="1920:1080",
        speed=2.0,
        fps=30,
    )
    assert len(filters) == 5
    assert filters[0].startswith("crop=")
    assert filters[1].startswith("scale=")
    assert filters[2].startswith("pad=")
    assert filters[3].startswith("setpts=")
    assert filters[4].startswith("fps=")


def test_audio_filter_chain() -> None:
    """Audio filters are assembled in strict order: atempo -> loudnorm -> volume."""
    filters = build_audio_filter(
        speed=3.0,
        normalize_loudness=True,
        volume_boost_db=6.0,
    )
    assert filters == [
        "atempo=2.0",
        "atempo=1.5",
        EBU_R128_LOUDNORM,
        "volume=6dB",
    ]


def test_audio_filter_volume_negative() -> None:
    """Negative volume attenuation formats with dB suffix."""
    filters = build_audio_filter(volume_boost_db=-3.5)
    assert filters == ["volume=-3.5dB"]


def test_audio_filter_volume_zero() -> None:
    """Zero volume gain produces no filter."""
    assert build_audio_filter(volume_boost_db=0.0) == []


def test_filter_args_helpers() -> None:
    """Helper functions return correct CLI argument pairs."""
    vf_args = build_video_filter_args(scale=(1280, 720))
    assert vf_args == ["-vf", "scale=1280:720"]

    vf_empty = build_video_filter_args()
    assert vf_empty == []

    af_args = build_audio_filter_args(speed=2.0)
    assert af_args == ["-af", "atempo=2.0"]

    af_empty = build_audio_filter_args()
    assert af_empty == []


def test_filtergraph_zero_gui() -> None:
    """Filtergraph module must have zero imports from GUI toolkits."""
    target_path = Path(__file__).resolve().parent.parent / "core" / "filtergraph.py"
    with open(target_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(target_path))

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", "") or ""
            for alias in getattr(node, "names", []):
                full_name = f"{mod}.{alias.name}" if mod else alias.name
                assert not any(
                    gui_pkg in full_name
                    for gui_pkg in ("gi", "Gtk", "Adw", "Nautilus", "tkinter", "PyQt", "PySide")
                ), f"Forbidden GUI import found in filtergraph.py: {full_name}"
