"""
Unit tests for domain models (core/models.py).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import sys
import pytest

from media_toolbox.core.models import (
    AudioStream,
    EncodeOptions,
    FormatInfo,
    MediaInfo,
    ProgressEvent,
    VideoStream,
)


class TestModelsImmutability:
    """Test suite verifying frozen dataclass immutability invariants."""

    def test_video_stream_frozen(self) -> None:
        stream = VideoStream(index=0, codec_name="h264", width=1920, height=1080)
        with pytest.raises(FrozenInstanceError):
            stream.width = 1280  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            stream.codec_name = "hevc"  # type: ignore[misc]

    def test_audio_stream_frozen(self) -> None:
        stream = AudioStream(index=1, codec_name="aac", channels=2, sample_rate=48000)
        with pytest.raises(FrozenInstanceError):
            stream.channels = 6  # type: ignore[misc]

    def test_format_info_frozen(self) -> None:
        fmt = FormatInfo(filename="test.mp4", format_name="mp4", duration=10.0)
        with pytest.raises(FrozenInstanceError):
            fmt.duration = 20.0  # type: ignore[misc]

    def test_media_info_frozen(self) -> None:
        fmt = FormatInfo(filename="test.mp4", format_name="mp4")
        media = MediaInfo(format=fmt)
        with pytest.raises(FrozenInstanceError):
            media.format = FormatInfo(filename="other.mp4", format_name="mp4")  # type: ignore[misc]

    def test_progress_event_frozen(self) -> None:
        event = ProgressEvent(frame=100, percentage=50.0)
        with pytest.raises(FrozenInstanceError):
            event.percentage = 60.0  # type: ignore[misc]

    def test_encode_options_frozen(self) -> None:
        opts = EncodeOptions(crf=23)
        with pytest.raises(FrozenInstanceError):
            opts.crf = 28  # type: ignore[misc]

    def test_hashability(self) -> None:
        v = VideoStream(index=0, codec_name="h264", width=1920, height=1080)
        a = AudioStream(index=1, codec_name="aac", channels=2, sample_rate=48000)
        fmt = FormatInfo(filename="test.mp4", format_name="mp4")
        media = MediaInfo(format=fmt, video_streams=(v,), audio_streams=(a,))
        prog = ProgressEvent(frame=10)
        opts = EncodeOptions()

        assert hash(v) is not None
        assert hash(a) is not None
        assert hash(fmt) is not None
        assert hash(media) is not None
        assert hash(prog) is not None
        assert hash(opts) is not None


class TestModelsDefaultsAndHelpers:
    """Test defaults, dimension calculations, and derived properties."""

    def test_video_stream_defaults_and_properties(self) -> None:
        stream = VideoStream(index=0, codec_name="h264", width=1920, height=1080)
        assert stream.fps is None
        assert stream.bit_rate is None
        assert stream.duration is None
        assert stream.pix_fmt is None
        assert stream.rotation == 0
        assert stream.is_attached_pic is False
        assert stream.resolution == (1920, 1080)
        assert stream.display_resolution == "1920x1080"
        assert stream.aspect_ratio == pytest.approx(16 / 9, rel=1e-3)
        assert stream.effective_dimensions == (1920, 1080)

    def test_video_stream_rotation_effective_dimensions(self) -> None:
        stream90 = VideoStream(index=0, codec_name="h264", width=1920, height=1080, rotation=90)
        assert stream90.effective_dimensions == (1080, 1920)

        stream270 = VideoStream(index=0, codec_name="h264", width=1920, height=1080, rotation=-90)
        assert stream270.effective_dimensions == (1080, 1920)

        stream180 = VideoStream(index=0, codec_name="h264", width=1920, height=1080, rotation=180)
        assert stream180.effective_dimensions == (1920, 1080)

    def test_video_stream_zero_height_aspect_ratio(self) -> None:
        stream = VideoStream(index=0, codec_name="h264", width=1920, height=0)
        assert stream.aspect_ratio == 0.0

    def test_audio_stream_defaults_and_properties(self) -> None:
        stream = AudioStream(
            index=1, codec_name="aac", channels=2, sample_rate=48000, bit_rate=192000
        )
        assert stream.channel_layout is None
        assert stream.duration is None
        assert stream.bit_rate_kbps == 192
        assert stream.sample_rate_khz == 48.0

        stream_no_br = AudioStream(index=1, codec_name="flac", channels=2, sample_rate=44100)
        assert stream_no_br.bit_rate_kbps is None

    def test_format_info_defaults_and_properties(self) -> None:
        fmt = FormatInfo(
            filename="video.mp4",
            format_name="mov,mp4",
            size_bytes=10 * 1024 * 1024,
            bit_rate=2500000,
        )
        assert fmt.duration is None
        assert fmt.size_mb == 10.0
        assert fmt.bit_rate_kbps == 2500

        fmt_empty = FormatInfo(filename="stream", format_name="pipe")
        assert fmt_empty.size_mb is None
        assert fmt_empty.bit_rate_kbps is None

    def test_encode_options_defaults(self) -> None:
        opts = EncodeOptions()
        assert opts.video_codec == "libx264"
        assert opts.audio_codec is None
        assert opts.audio_bitrate_kbps == 128
        assert opts.preset is None
        assert opts.speed_preset is None
        assert opts.two_pass is False


class TestMediaInfoProperties:
    """Test MediaInfo composite properties and fallback hierarchy."""

    def test_media_info_standard_video_audio(self) -> None:
        v = VideoStream(index=0, codec_name="h264", width=1920, height=1080, duration=60.0)
        a = AudioStream(index=1, codec_name="aac", channels=2, sample_rate=48000, duration=60.0)
        fmt = FormatInfo(filename="test.mp4", format_name="mp4", duration=60.0)
        media = MediaInfo(format=fmt, video_streams=(v,), audio_streams=(a,))

        assert media.has_video is True
        assert media.has_audio is True
        assert media.primary_video == v
        assert media.primary_audio == a
        assert media.duration == 60.0
        assert media.is_audio_only is False
        assert media.is_video_only is False
        assert media.is_image is False

    def test_media_info_silent_video(self) -> None:
        v = VideoStream(index=0, codec_name="h264", width=1280, height=720, duration=15.0)
        fmt = FormatInfo(filename="silent.mp4", format_name="mp4", duration=15.0)
        media = MediaInfo(format=fmt, video_streams=(v,))

        assert media.has_video is True
        assert media.has_audio is False
        assert media.primary_video == v
        assert media.primary_audio is None
        assert media.is_video_only is True

    def test_media_info_audio_only_with_album_art(self) -> None:
        a = AudioStream(index=0, codec_name="mp3", channels=2, sample_rate=44100, duration=180.0)
        cover = VideoStream(
            index=1, codec_name="png", width=500, height=500, is_attached_pic=True
        )
        fmt = FormatInfo(filename="song.mp3", format_name="mp3", duration=180.0)
        media = MediaInfo(format=fmt, video_streams=(cover,), audio_streams=(a,))

        assert media.has_video is False
        assert media.has_audio is True
        assert media.primary_video is None
        assert media.primary_audio == a
        assert len(media.attached_pics) == 1
        assert media.is_audio_only is True
        assert media.duration == 180.0

    def test_media_info_still_image(self) -> None:
        img = VideoStream(
            index=0, codec_name="png", width=800, height=600, duration=None, is_attached_pic=False
        )
        fmt = FormatInfo(filename="photo.png", format_name="image2", duration=None)
        media = MediaInfo(format=fmt, video_streams=(img,))

        assert media.has_video is True
        assert media.has_audio is False
        assert media.primary_video == img
        assert media.duration == 0.0
        assert media.is_image is True

    def test_media_info_duration_fallback_order(self) -> None:
        # Format duration takes precedence when present and > 0
        fmt = FormatInfo(filename="f.mp4", format_name="mp4", duration=100.0)
        v = VideoStream(index=0, codec_name="h264", width=10, height=10, duration=99.0)
        media = MediaInfo(format=fmt, video_streams=(v,))
        assert media.duration == 100.0

        # Primary video duration used when format duration is None
        fmt_no_dur = FormatInfo(filename="f.mp4", format_name="mp4", duration=None)
        media_v_dur = MediaInfo(format=fmt_no_dur, video_streams=(v,))
        assert media_v_dur.duration == 99.0

        # Primary audio duration used when format and video durations are None
        v_no_dur = VideoStream(index=0, codec_name="h264", width=10, height=10, duration=None)
        a = AudioStream(index=1, codec_name="aac", channels=2, sample_rate=48000, duration=50.0)
        media_a_dur = MediaInfo(format=fmt_no_dur, video_streams=(v_no_dur,), audio_streams=(a,))
        assert media_a_dur.duration == 50.0

        # Default 0.0 when all are None
        a_no_dur = AudioStream(index=1, codec_name="aac", channels=2, sample_rate=48000, duration=None)
        media_zero = MediaInfo(format=fmt_no_dur, video_streams=(v_no_dur,), audio_streams=(a_no_dur,))
        assert media_zero.duration == 0.0

    def test_media_info_list_coercion_to_tuple(self) -> None:
        fmt = FormatInfo(filename="test.mp4", format_name="mp4")
        v = VideoStream(index=0, codec_name="h264", width=1920, height=1080)
        # Passing mutable list instead of tuple
        media = MediaInfo(format=fmt, video_streams=[v], audio_streams=[])  # type: ignore[arg-type]
        assert isinstance(media.video_streams, tuple)
        assert isinstance(media.audio_streams, tuple)


class TestProgressEvent:
    """Test ProgressEvent metrics and string representations."""

    def test_progress_event_defaults(self) -> None:
        event = ProgressEvent()
        assert event.frame == 0
        assert event.fps == 0.0
        assert event.out_time_seconds == 0.0
        assert event.total_size_bytes == 0
        assert event.speed is None
        assert event.percentage == 0.0
        assert event.eta_seconds is None
        assert event.is_completed is False
        assert event.speed_str == "N/A"
        assert event.eta_str == "N/A"

    def test_progress_event_speed_and_eta_strings(self) -> None:
        event = ProgressEvent(speed=2.5, eta_seconds=125)
        assert event.speed_str == "2.50x"
        assert event.eta_str == "02:05"

        event_hours = ProgressEvent(eta_seconds=3665)
        assert event_hours.eta_str == "01:01:05"

        event_neg = ProgressEvent(eta_seconds=-10)
        assert event_neg.eta_str == "N/A"


class TestHeadlessInvariant:
    """Verify core models do not trigger imports of GUI libraries."""

    def test_zero_gui_imports_in_models(self) -> None:
        for mod in ("gi", "gi.repository", "gi.repository.Gtk", "gi.repository.Adw"):
            assert mod not in sys.modules, f"Forbidden GUI module {mod} loaded in core models test!"
