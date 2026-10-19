"""
Pytest fixtures and test harness configuration for media_toolbox.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
import pytest

# Ensure repository python directory is in sys.path
python_root = Path(__file__).resolve().parent.parent.parent
if str(python_root) not in sys.path:
    sys.path.insert(0, str(python_root))

from media_toolbox.core.models import (
    AudioStream,
    FormatInfo,
    MediaInfo,
    VideoStream,
)


@pytest.fixture
def probe_data_standard_mp4() -> dict[str, Any]:
    """Synthetic ffprobe JSON structure for standard H.264 + AAC MP4 video."""
    return {
        "streams": [
            {
                "index": 0,
                "codec_name": "h264",
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "pix_fmt": "yuv420p",
                "r_frame_rate": "30/1",
                "avg_frame_rate": "30/1",
                "duration": "60.000000",
                "bit_rate": "2500000",
                "disposition": {"attached_pic": 0},
                "tags": {"rotate": "0"},
            },
            {
                "index": 1,
                "codec_name": "aac",
                "codec_type": "audio",
                "channels": 2,
                "sample_rate": "48000",
                "channel_layout": "stereo",
                "duration": "60.000000",
                "bit_rate": "192000",
                "disposition": {"attached_pic": 0},
            },
        ],
        "format": {
            "filename": "sample_video.mp4",
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "duration": "60.000000",
            "size": "20190000",
            "bit_rate": "2692000",
        },
    }


@pytest.fixture
def probe_data_audio_only_mp3() -> dict[str, Any]:
    """Synthetic ffprobe JSON structure for MP3 with ID3 embedded album art."""
    return {
        "streams": [
            {
                "index": 0,
                "codec_name": "mp3",
                "codec_type": "audio",
                "channels": 2,
                "sample_rate": "44100",
                "channel_layout": "stereo",
                "duration": "180.500000",
                "bit_rate": "320000",
                "disposition": {"attached_pic": 0},
            },
            {
                "index": 1,
                "codec_name": "png",
                "codec_type": "video",
                "width": 500,
                "height": 500,
                "pix_fmt": "rgb24",
                "r_frame_rate": "90000/1",
                "avg_frame_rate": "0/0",
                "duration": "180.500000",
                "disposition": {"attached_pic": 1},
                "tags": {"title": "Album cover"},
            },
        ],
        "format": {
            "filename": "song.mp3",
            "format_name": "mp3",
            "duration": "180.500000",
            "size": "7220000",
            "bit_rate": "320000",
        },
    }


@pytest.fixture
def probe_data_silent_mp4() -> dict[str, Any]:
    """Synthetic ffprobe JSON structure for silent video (no audio stream)."""
    return {
        "streams": [
            {
                "index": 0,
                "codec_name": "h264",
                "codec_type": "video",
                "width": 1280,
                "height": 720,
                "pix_fmt": "yuv420p",
                "r_frame_rate": "24000/1001",
                "avg_frame_rate": "24000/1001",
                "duration": "10.000000",
                "bit_rate": "1200000",
                "disposition": {"attached_pic": 0},
            }
        ],
        "format": {
            "filename": "silent.mp4",
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "duration": "10.000000",
            "size": "1500000",
            "bit_rate": "1200000",
        },
    }


@pytest.fixture
def probe_data_png_image() -> dict[str, Any]:
    """Synthetic ffprobe JSON structure for still image (0 duration, no audio)."""
    return {
        "streams": [
            {
                "index": 0,
                "codec_name": "png",
                "codec_type": "video",
                "width": 800,
                "height": 600,
                "pix_fmt": "rgb24",
                "r_frame_rate": "0/0",
                "avg_frame_rate": "0/0",
                "duration": "N/A",
                "disposition": {"attached_pic": 0},
            }
        ],
        "format": {
            "filename": "image.png",
            "format_name": "image2",
            "size": "45000",
        },
    }


@pytest.fixture
def probe_data_missing_format_duration() -> dict[str, Any]:
    """Probe JSON where format duration is 'N/A' and stream duration is present."""
    return {
        "streams": [
            {
                "index": 0,
                "codec_name": "h264",
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "duration": "42.500000",
            }
        ],
        "format": {
            "filename": "stream_dur_only.mp4",
            "format_name": "mov,mp4",
            "duration": "N/A",
        },
    }


@pytest.fixture
def mock_ffprobe_standard_mp4_json(probe_data_standard_mp4: dict[str, Any]) -> str:
    """JSON string of standard MP4 probe data."""
    return json.dumps(probe_data_standard_mp4)


@pytest.fixture
def mock_ffprobe_audio_only_mp3_json(probe_data_audio_only_mp3: dict[str, Any]) -> str:
    """JSON string of audio-only MP3 probe data."""
    return json.dumps(probe_data_audio_only_mp3)


@pytest.fixture
def mock_ffprobe_silent_mp4_json(probe_data_silent_mp4: dict[str, Any]) -> str:
    """JSON string of silent MP4 probe data."""
    return json.dumps(probe_data_silent_mp4)


@pytest.fixture
def mock_ffprobe_png_image_json(probe_data_png_image: dict[str, Any]) -> str:
    """JSON string of PNG still image probe data."""
    return json.dumps(probe_data_png_image)


@pytest.fixture
def sample_mediainfo_standard_mp4() -> MediaInfo:
    """Pre-built MediaInfo instance matching standard MP4."""
    v = VideoStream(
        index=0,
        codec_name="h264",
        width=1920,
        height=1080,
        pix_fmt="yuv420p",
        fps=30.0,
        duration=60.0,
        bit_rate=2500000,
    )
    a = AudioStream(
        index=1,
        codec_name="aac",
        channels=2,
        sample_rate=48000,
        channel_layout="stereo",
        duration=60.0,
        bit_rate=192000,
    )
    fmt = FormatInfo(
        filename="sample_video.mp4",
        format_name="mov,mp4",
        duration=60.0,
        size_bytes=20190000,
        bit_rate=2692000,
    )
    return MediaInfo(format=fmt, video_streams=(v,), audio_streams=(a,))
