"""
Unit tests for bitrate calculation engine (core/bitrate.py).
"""

from __future__ import annotations

import pytest
from media_toolbox.core.bitrate import (
    calculate_target_video_bitrate,
    DEFAULT_AUDIO_BITRATE_KBPS,
    DEFAULT_MUX_OVERHEAD_MARGIN,
    DEFAULT_MIN_VIDEO_BITRATE_KBPS,
)


class TestBitrateCalculation:
    """Test suite for calculate_target_video_bitrate."""

    @pytest.mark.parametrize(
        "target_mb, duration_s, audio_kbps, margin, expected_kbps",
        [
            # 25MB, 60s, 128k audio, 3% margin -> 3183 kbps
            (25.0, 60.0, 128, 0.03, 3183),
            # 8MB (Discord limit), 120s, 128k audio, 3% margin -> 402 kbps
            (8.0, 120.0, 128, 0.03, 402),
            # 100MB, 1800s (30 min), 192k audio, 5% margin -> 240 kbps
            (100.0, 1800.0, 192, 0.05, 240),
            # Zero margin: 25MB, 60s, 128k audio, 0% margin -> 3285 kbps
            (25.0, 60.0, 128, 0.0, 3285),
            # Zero audio bitrate (muted/silent video): 10MB, 100s, 0k audio, 3% margin -> 795 kbps
            (10.0, 100.0, 0, 0.03, 795),
            # Integer inputs: 25, 60, 128 -> 3183 kbps
            (25, 60, 128, 0.03, 3183),
        ],
    )
    def test_bitrate_standard_scenarios(
        self, target_mb: float, duration_s: float, audio_kbps: int, margin: float, expected_kbps: int
    ) -> None:
        result = calculate_target_video_bitrate(
            target_size_mb=target_mb,
            duration_seconds=duration_s,
            audio_bitrate_kbps=audio_kbps,
            mux_overhead_margin=margin,
        )
        assert result == expected_kbps
        assert isinstance(result, int)

    def test_bitrate_default_parameters(self) -> None:
        # target_mb=25.0, duration_seconds=60.0 with all defaults
        result = calculate_target_video_bitrate(25.0, 60.0)
        assert result == 3183

    @pytest.mark.parametrize(
        "target_mb, duration_s, audio_kbps, expected_clamp",
        [
            # Extreme long duration (1 hour) with tiny size (1 MB) -> clamps to 64
            (1.0, 3600.0, 128, 64),
            # Duration where net bitrate is negative -> clamps to 64
            (0.5, 600.0, 128, 64),
            # Net bitrate slightly positive (e.g. 50 kbps) -> clamps to 64
            (1.6, 60.0, 160, 64),
        ],
    )
    def test_bitrate_clamps_to_minimum(
        self, target_mb: float, duration_s: float, audio_kbps: int, expected_clamp: int
    ) -> None:
        result = calculate_target_video_bitrate(
            target_size_mb=target_mb,
            duration_seconds=duration_s,
            audio_bitrate_kbps=audio_kbps,
        )
        assert result == expected_clamp

    def test_custom_min_video_bitrate(self) -> None:
        # Clamping to custom floor 100 kbps
        result = calculate_target_video_bitrate(
            target_size_mb=1.0,
            duration_seconds=3600.0,
            audio_bitrate_kbps=128,
            min_video_bitrate_kbps=100,
        )
        assert result == 100

        # Clamping to custom floor 0 kbps
        result_zero = calculate_target_video_bitrate(
            target_size_mb=1.0,
            duration_seconds=3600.0,
            audio_bitrate_kbps=128,
            min_video_bitrate_kbps=0,
        )
        assert result_zero == 0

    @pytest.mark.parametrize(
        "invalid_duration",
        [0, 0.0, -1, -60.0, float("nan"), float("inf"), float("-inf")],
    )
    def test_invalid_duration_raises_value_error(self, invalid_duration: float) -> None:
        with pytest.raises(ValueError, match="duration_seconds must be a positive finite number"):
            calculate_target_video_bitrate(25.0, invalid_duration)

    @pytest.mark.parametrize(
        "invalid_target_size",
        [0, 0.0, -1, -25.0, float("nan"), float("inf"), float("-inf")],
    )
    def test_invalid_target_size_raises_value_error(self, invalid_target_size: float) -> None:
        with pytest.raises(ValueError, match="target_size_mb must be a positive finite number"):
            calculate_target_video_bitrate(invalid_target_size, 60.0)

    def test_negative_audio_bitrate_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="audio_bitrate_kbps cannot be negative"):
            calculate_target_video_bitrate(25.0, 60.0, audio_bitrate_kbps=-1)

    @pytest.mark.parametrize("invalid_margin", [-0.01, -1.0, 1.0, 1.05, 2.0])
    def test_invalid_margin_raises_value_error(self, invalid_margin: float) -> None:
        with pytest.raises(ValueError, match="mux_overhead_margin must be in range"):
            calculate_target_video_bitrate(25.0, 60.0, mux_overhead_margin=invalid_margin)

    def test_negative_min_video_bitrate_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="min_video_bitrate_kbps cannot be negative"):
            calculate_target_video_bitrate(25.0, 60.0, min_video_bitrate_kbps=-1)
