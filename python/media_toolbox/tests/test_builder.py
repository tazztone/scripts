"""
Unit tests for media_toolbox.core.builder.

Verifies:
- Deterministic CLI command line assembly for single-pass CRF encoding
- Two-pass bitrate targeting (Pass 1 null sink with statistics log, Pass 2 output)
- Identical video filtergraphs between Pass 1 and Pass 2
- Standalone audio extraction and audio preset routing
- Two-stage animated GIF generation via palettegen / paletteuse
- Defensive parameter validation (contradictions, negative values, zero duration)
- AST headless invariant (zero GUI imports)
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import pytest

from media_toolbox.core.builder import (
    build_audio_extract_command,
    build_ffmpeg_commands,
    build_gif_command,
    build_single_pass_command,
    build_two_pass_commands,
)
from media_toolbox.core.models import (
    AudioStream,
    EncodeOptions,
    FormatInfo,
    MediaInfo,
    VideoStream,
)


def test_crf_default() -> None:
    """Default EncodeOptions produce standard H.264 CRF 23 MP4 command."""
    options = EncodeOptions()
    cmds = build_ffmpeg_commands("in.mp4", "out.mp4", options)

    assert len(cmds) == 1
    cmd = cmds[0]
    expected = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-i",
        "in.mp4",
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "out.mp4",
    ]
    assert cmd == expected


def test_crf_custom() -> None:
    """Custom CRF and audio bitrate propagate to CLI flags."""
    options = EncodeOptions(crf=18, audio_bitrate_kbps=192)
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    assert "-crf" in cmd
    crf_idx = cmd.index("-crf")
    assert cmd[crf_idx + 1] == "18"

    assert "-b:a" in cmd
    ba_idx = cmd.index("-b:a")
    assert cmd[ba_idx + 1] == "192k"


def test_scale_only() -> None:
    """Scale option adds -vf scale filter to command."""
    options = EncodeOptions(scale=(1280, 720))
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    assert "-vf" in cmd
    vf_idx = cmd.index("-vf")
    assert cmd[vf_idx + 1] == "scale=1280:720"


def test_speed_2x() -> None:
    """Speed multiplier 2.0x scales video PTS and audio tempo in sync."""
    options = EncodeOptions(speed=2.0)
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    assert "-vf" in cmd
    vf_idx = cmd.index("-vf")
    assert cmd[vf_idx + 1] == "setpts=(1.0/2.0)*PTS"

    assert "-af" in cmd
    af_idx = cmd.index("-af")
    assert cmd[af_idx + 1] == "atempo=2.0"


def test_speed_3x() -> None:
    """Speed multiplier 3.0x chains multi-stage atempo filters."""
    options = EncodeOptions(speed=3.0)
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    assert "-af" in cmd
    af_idx = cmd.index("-af")
    assert cmd[af_idx + 1] == "atempo=2.0,atempo=1.5"


def test_audio_mute() -> None:
    """Mute audio adds -an and omits all audio encoding flags."""
    options = EncodeOptions(mute_audio=True)
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    assert "-an" in cmd
    assert "-c:a" not in cmd
    assert "-b:a" not in cmd
    assert "-af" not in cmd


def test_audio_normalize() -> None:
    """Loudness normalization adds EBU R128 loudnorm filter."""
    options = EncodeOptions(normalize_audio=True)
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    assert "-af" in cmd
    af_idx = cmd.index("-af")
    assert cmd[af_idx + 1] == "loudnorm=I=-23:LRA=7:TP=-1.5"


def test_audio_volume_boost() -> None:
    """Volume boost adds volume filter."""
    options = EncodeOptions(volume_boost_db=6.0)
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    assert "-af" in cmd
    af_idx = cmd.index("-af")
    assert "volume=6" in cmd[af_idx + 1]


def test_audio_extract_mp3() -> None:
    """Audio extraction with MP3 preset disables video and applies LAME encoder."""
    options = EncodeOptions(extract_audio=True, video_codec="mp3", audio_bitrate_kbps=192)
    cmd = build_ffmpeg_commands("in.mp4", "out.mp3", options)[0]

    expected = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-i",
        "in.mp4",
        "-vn",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        "out.mp3",
    ]
    assert cmd == expected


def test_audio_extract_flac() -> None:
    """Audio extraction with FLAC preset applies lossless compression level."""
    options = EncodeOptions(extract_audio=True, video_codec="flac")
    cmd = build_ffmpeg_commands("in.mp4", "out.flac", options)[0]

    assert "-vn" in cmd
    assert "-c:a" in cmd
    assert cmd[cmd.index("-c:a") + 1] == "flac"
    assert "-compression_level" in cmd
    assert "-b:a" not in cmd


def test_extract_and_mute_error() -> None:
    """Contradictory options extract_audio and mute_audio raise ValueError."""
    options = EncodeOptions(extract_audio=True, mute_audio=True)
    with pytest.raises(ValueError, match="Cannot simultaneously extract and mute audio"):
        build_ffmpeg_commands("in.mp4", "out.mp3", options)


def test_gif_simple() -> None:
    """GIF export builds two-stage palettegen / paletteuse complex filtergraph."""
    options = EncodeOptions(video_codec="gif")
    cmd = build_ffmpeg_commands("in.mp4", "out.gif", options)[0]

    expected = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-i",
        "in.mp4",
        "-filter_complex",
        "[0:v]split[a][b];[a]palettegen[p];[b][p]paletteuse",
        "-an",
        "out.gif",
    ]
    assert cmd == expected


def test_gif_with_scale_fps() -> None:
    """GIF export chains video transforms before palette generation."""
    options = EncodeOptions(video_codec="gif", scale=(320, -2), fps=15)
    cmd = build_ffmpeg_commands("in.mp4", "out.gif", options)[0]

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_expr = cmd[fc_idx + 1]
    assert filter_expr.startswith("[0:v]")
    assert "scale=320:-2" in filter_expr
    assert "fps=fps=15" in filter_expr
    assert "split[a][b];[a]palettegen[p];[b][p]paletteuse" in filter_expr
    assert "-an" in cmd


def test_gif_two_pass_error() -> None:
    """GIF preset rejects two-pass rate control."""
    options = EncodeOptions(video_codec="gif", two_pass=True)
    with pytest.raises(ValueError, match="Two-pass encoding is not supported for GIF preset"):
        build_ffmpeg_commands("in.mp4", "out.gif", options)


def test_two_pass_commands_count(sample_mediainfo_standard_mp4: MediaInfo) -> None:
    """Two-pass encoding returns a list of exactly two commands."""
    options = EncodeOptions(two_pass=True, target_size_mb=25.0)
    cmds = build_ffmpeg_commands(
        "in.mp4",
        "out.mp4",
        options,
        media_info=sample_mediainfo_standard_mp4,
    )
    assert len(cmds) == 2


def test_two_pass_pass1_null(sample_mediainfo_standard_mp4: MediaInfo) -> None:
    """Pass 1 writes statistics to null sink with audio disabled."""
    options = EncodeOptions(two_pass=True, target_size_mb=25.0)
    log_file = "/tmp/test_pass_log"
    cmds = build_ffmpeg_commands(
        "in.mp4",
        "out.mp4",
        options,
        media_info=sample_mediainfo_standard_mp4,
        pass_logfile=log_file,
    )
    pass1 = cmds[0]

    assert "-pass" in pass1
    assert pass1[pass1.index("-pass") + 1] == "1"
    assert "-passlogfile" in pass1
    assert pass1[pass1.index("-passlogfile") + 1] == log_file
    assert "-an" in pass1
    assert "-f" in pass1
    assert pass1[pass1.index("-f") + 1] == "null"
    assert pass1[-1] == os.devnull


def test_two_pass_pass2_output(sample_mediainfo_standard_mp4: MediaInfo) -> None:
    """Pass 2 encodes audio and writes final MP4 output with faststart."""
    options = EncodeOptions(two_pass=True, target_size_mb=25.0)
    log_file = "/tmp/test_pass_log"
    cmds = build_ffmpeg_commands(
        "in.mp4",
        "out.mp4",
        options,
        media_info=sample_mediainfo_standard_mp4,
        pass_logfile=log_file,
    )
    pass2 = cmds[1]

    assert "-pass" in pass2
    assert pass2[pass2.index("-pass") + 1] == "2"
    assert "-passlogfile" in pass2
    assert pass2[pass2.index("-passlogfile") + 1] == log_file
    assert "-c:a" in pass2
    assert pass2[pass2.index("-c:a") + 1] == "aac"
    assert "-movflags" in pass2
    assert pass2[pass2.index("-movflags") + 1] == "+faststart"
    assert pass2[-1] == "out.mp4"


def test_two_pass_identical_vf(sample_mediainfo_standard_mp4: MediaInfo) -> None:
    """Video filters must be exactly identical between Pass 1 and Pass 2."""
    options = EncodeOptions(
        two_pass=True,
        target_size_mb=25.0,
        scale=(1280, 720),
        speed=1.5,
    )
    cmds = build_ffmpeg_commands(
        "in.mp4",
        "out.mp4",
        options,
        media_info=sample_mediainfo_standard_mp4,
    )
    pass1, pass2 = cmds[0], cmds[1]

    pass1_vf = [pass1[i + 1] for i, arg in enumerate(pass1) if arg == "-vf"]
    pass2_vf = [pass2[i + 1] for i, arg in enumerate(pass2) if arg == "-vf"]

    assert pass1_vf == pass2_vf
    assert len(pass1_vf) == 1
    assert "scale=1280:720" in pass1_vf[0]
    assert "setpts=(1.0/1.5)*PTS" in pass1_vf[0]


def test_two_pass_mute_audio(sample_mediainfo_standard_mp4: MediaInfo) -> None:
    """Muted two-pass encoding disables audio on both passes and gives 100% bitrate to video."""
    options_muted = EncodeOptions(two_pass=True, target_size_mb=25.0, mute_audio=True)
    options_unmuted = EncodeOptions(two_pass=True, target_size_mb=25.0, mute_audio=False)

    cmds_muted = build_ffmpeg_commands(
        "in.mp4", "out.mp4", options_muted, media_info=sample_mediainfo_standard_mp4
    )
    cmds_unmuted = build_ffmpeg_commands(
        "in.mp4", "out.mp4", options_unmuted, media_info=sample_mediainfo_standard_mp4
    )

    pass2_muted = cmds_muted[1]
    assert "-an" in pass2_muted
    assert "-c:a" not in pass2_muted

    # Muted video bitrate should be higher than unmuted
    vbr_muted = int(pass2_muted[pass2_muted.index("-b:v") + 1].rstrip("k"))
    pass2_unmuted = cmds_unmuted[1]
    vbr_unmuted = int(pass2_unmuted[pass2_unmuted.index("-b:v") + 1].rstrip("k"))
    assert vbr_muted > vbr_unmuted


def test_two_pass_silent_input() -> None:
    """Silent input video automatically omits audio encoding in Pass 2."""
    v = VideoStream(0, "h264", 1280, 720, duration=30.0)
    fmt = FormatInfo(filename="silent.mp4", format_name="mp4", duration=30.0)
    silent_info = MediaInfo(format=fmt, video_streams=(v,), audio_streams=())

    options = EncodeOptions(two_pass=True, target_size_mb=10.0)
    cmds = build_ffmpeg_commands("in.mp4", "out.mp4", options, media_info=silent_info)

    pass2 = cmds[1]
    assert "-an" in pass2
    assert "-c:a" not in pass2


def test_two_pass_zero_duration() -> None:
    """Zero media duration raises ValueError in two-pass bitrate mode."""
    fmt = FormatInfo(filename="zero.mp4", format_name="mp4", duration=0.0)
    zero_info = MediaInfo(format=fmt, video_streams=(), audio_streams=())

    options = EncodeOptions(two_pass=True, target_size_mb=10.0)
    with pytest.raises(ValueError, match="Cannot calculate target bitrate"):
        build_ffmpeg_commands("in.mp4", "out.mp4", options, media_info=zero_info)


def test_two_pass_missing_media_info_not_on_disk() -> None:
    """If media_info is None and input file does not exist on disk, ValueError is raised."""
    options = EncodeOptions(two_pass=True, target_size_mb=10.0)
    with pytest.raises(ValueError, match="media_info is required when input file is not on disk"):
        build_ffmpeg_commands("/nonexistent/fake_file.mp4", "out.mp4", options)


def test_extra_arguments_forwarding() -> None:
    """Extra arguments are forwarded before the output path."""
    options = EncodeOptions(extra_args=("-threads", "4", "-tune", "film"))
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    assert "-threads" in cmd
    assert cmd[cmd.index("-threads") + 1] == "4"
    assert "-tune" in cmd
    assert cmd[cmd.index("-tune") + 1] == "film"
    # Forwarded before output path
    assert cmd[-3] == "-tune"
    assert cmd[-2] == "film"
    assert cmd[-1] == "out.mp4"


def test_include_progress_flag() -> None:
    """include_progress=True injects -progress pipe:1 -nostats flags."""
    options = EncodeOptions()
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options, include_progress=True)[0]

    assert "-progress" in cmd
    prog_idx = cmd.index("-progress")
    assert cmd[prog_idx + 1] == "pipe:1"
    assert "-nostats" in cmd


@pytest.mark.parametrize("invalid_speed", [-1.0, 0.0])
def test_negative_speed_raises(invalid_speed: float) -> None:
    """Non-positive speed multiplier raises ValueError."""
    options = EncodeOptions(speed=invalid_speed)
    with pytest.raises(ValueError, match="Speed multiplier must be positive"):
        build_ffmpeg_commands("in.mp4", "out.mp4", options)


@pytest.mark.parametrize("invalid_size", [-5.0, 0.0])
def test_negative_target_size_raises(invalid_size: float) -> None:
    """Non-positive target size raises ValueError."""
    options = EncodeOptions(target_size_mb=invalid_size)
    with pytest.raises(ValueError, match="target_size_mb must be positive"):
        build_ffmpeg_commands("in.mp4", "out.mp4", options)


def test_builder_zero_gui() -> None:
    """Builder module must have zero imports from GUI toolkits."""
    target_path = Path(__file__).resolve().parent.parent / "core" / "builder.py"
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
                ), f"Forbidden GUI import found in builder.py: {full_name}"


# ---------------------------------------------------------------------------
# Bug A Unit Tests (Speed Preset Handling and Format Unshadowing)
# ---------------------------------------------------------------------------


def test_preset_format_h264_no_invalid_preset_cli() -> None:
    """options.preset='h264' selects H.264 and does not emit invalid '-preset h264'."""
    options = EncodeOptions(preset="h264")
    cmds = build_ffmpeg_commands("in.mp4", "out.mp4", options)
    assert len(cmds) == 1
    cmd = cmds[0]
    assert "-c:v" in cmd
    assert cmd[cmd.index("-c:v") + 1] == "libx264"
    assert "-preset" in cmd
    assert cmd[cmd.index("-preset") + 1] == "medium"
    assert "h264" not in [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-preset"]


def test_preset_format_h265_unshadowed() -> None:
    """options.preset='h265' overrides default video_codec='libx264' and selects libx265."""
    options = EncodeOptions(preset="h265")
    cmds = build_ffmpeg_commands("in.mp4", "out.mp4", options)
    assert len(cmds) == 1
    cmd = cmds[0]
    assert "-c:v" in cmd
    assert cmd[cmd.index("-c:v") + 1] == "libx265"
    assert "-crf" in cmd
    assert cmd[cmd.index("-crf") + 1] == "28"
    assert "-tag:v" in cmd
    assert cmd[cmd.index("-tag:v") + 1] == "hvc1"
    assert "-preset" in cmd
    assert cmd[cmd.index("-preset") + 1] == "medium"


def test_preset_speed_preset_slow() -> None:
    """options.preset='slow' is recognized as a speed preset and passed as -preset slow."""
    options = EncodeOptions(preset="slow")
    cmds = build_ffmpeg_commands("in.mp4", "out.mp4", options)
    assert len(cmds) == 1
    cmd = cmds[0]
    assert "-c:v" in cmd
    assert cmd[cmd.index("-c:v") + 1] == "libx264"
    assert "-preset" in cmd
    assert cmd[cmd.index("-preset") + 1] == "slow"


def test_format_preset_with_explicit_speed_preset() -> None:
    """options.preset='h265' with speed_preset='veryslow' emits both correctly."""
    options = EncodeOptions(preset="h265", speed_preset="veryslow")
    cmds = build_ffmpeg_commands("in.mp4", "out.mp4", options)
    assert len(cmds) == 1
    cmd = cmds[0]
    assert "-c:v" in cmd
    assert cmd[cmd.index("-c:v") + 1] == "libx265"
    assert "-preset" in cmd
    assert cmd[cmd.index("-preset") + 1] == "veryslow"


# ---------------------------------------------------------------------------
# Regression Tests for Bug A & Bug B (Presets & Container Compatibility)
# ---------------------------------------------------------------------------


def test_preset_h265_selects_libx265_and_valid_preset() -> None:
    """
    EncodeOptions(preset='h265') selects libx265 and does NOT emit '-preset h265'.
    (Bug A regression test).
    """
    options = EncodeOptions(preset="h265")
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    # Video codec must be libx265, not libx264
    assert "-c:v" in cmd
    assert cmd[cmd.index("-c:v") + 1] == "libx265"

    # Must NOT emit '-preset h265' (invalid encoder speed preset)
    if "-preset" in cmd:
        preset_val = cmd[cmd.index("-preset") + 1]
        assert preset_val != "h265"
        assert preset_val == "medium"

    # Default CRF for H.265 is 28
    assert "-crf" in cmd
    assert cmd[cmd.index("-crf") + 1] == "28"

    # Apple compatibility tag
    assert "-tag:v" in cmd
    assert cmd[cmd.index("-tag:v") + 1] == "hvc1"

    # Container faststart for MP4
    assert "-movflags" in cmd
    assert cmd[cmd.index("-movflags") + 1] == "+faststart"


def test_preset_h264_emits_default_speed_preset() -> None:
    """
    EncodeOptions(preset='h264') does NOT emit '-preset h264'; emits default 'medium'.
    (Bug A regression test).
    """
    options = EncodeOptions(preset="h264")
    cmd = build_ffmpeg_commands("in.mp4", "out.mp4", options)[0]

    assert "-c:v" in cmd
    assert cmd[cmd.index("-c:v") + 1] == "libx264"

    # Codec preset name must not be forwarded as speed preset
    assert "-preset" in cmd
    preset_idx = cmd.index("-preset")
    assert cmd[preset_idx + 1] == "medium"
    assert cmd[preset_idx + 1] != "h264"


def test_vp9_webm_selects_libopus_audio() -> None:
    """
    EncodeOptions(video_codec='vp9') with .webm output selects libopus, not aac.
    (Bug B regression test).
    """
    options = EncodeOptions(video_codec="vp9")
    cmd = build_ffmpeg_commands("in.mp4", "out.webm", options)[0]

    # Video codec and VP9 CRF parameters
    assert "-c:v" in cmd
    assert cmd[cmd.index("-c:v") + 1] == "libvpx-vp9"
    assert "-b:v" in cmd
    assert cmd[cmd.index("-b:v") + 1] == "0"
    assert "-crf" in cmd
    assert cmd[cmd.index("-crf") + 1] == "30"

    # Audio codec: WebM container requires Opus or Vorbis, never AAC
    assert "-c:a" in cmd
    assert cmd[cmd.index("-c:a") + 1] == "libopus"
    assert cmd[cmd.index("-c:a") + 1] != "aac"

    # WebM container does not use MP4-specific faststart flags
    assert "-movflags" not in cmd
    assert cmd[-1] == "out.webm"


def test_two_pass_vp9_webm_uses_libopus_in_pass2(sample_mediainfo_standard_mp4: MediaInfo) -> None:
    """
    Two-pass encoding with preset='vp9' and .webm output uses libopus in Pass 2.
    (Bug A & Bug B regression test for 2-pass).
    """
    options = EncodeOptions(preset="vp9", two_pass=True, target_size_mb=10.0)
    cmds = build_ffmpeg_commands(
        "in.mp4",
        "out.webm",
        options,
        media_info=sample_mediainfo_standard_mp4,
    )

    assert len(cmds) == 2
    pass1, pass2 = cmds[0], cmds[1]

    # Pass 1: video codec must be libvpx-vp9, no invalid preset flag, audio muted
    assert "-c:v" in pass1
    assert pass1[pass1.index("-c:v") + 1] == "libvpx-vp9"
    if "-preset" in pass1:
        assert pass1[pass1.index("-preset") + 1] != "vp9"
    assert "-pass" in pass1
    assert pass1[pass1.index("-pass") + 1] == "1"
    assert "-an" in pass1

    # Pass 2: video codec libvpx-vp9, audio codec libopus (not aac)
    assert "-c:v" in pass2
    assert pass2[pass2.index("-c:v") + 1] == "libvpx-vp9"
    if "-preset" in pass2:
        assert pass2[pass2.index("-preset") + 1] != "vp9"
    assert "-pass" in pass2
    assert pass2[pass2.index("-pass") + 1] == "2"

    assert "-c:a" in pass2
    assert pass2[pass2.index("-c:a") + 1] == "libopus"
    assert pass2[pass2.index("-c:a") + 1] != "aac"
    assert "-b:a" in pass2
    assert pass2[pass2.index("-b:a") + 1] == "128k"
    assert pass2[-1] == "out.webm"


def test_preset_prores_selects_pcm_audio() -> None:
    """
    EncodeOptions(preset='prores') selects prores_ks video and pcm_s16le audio.
    (Bug A & Bug B regression test for ProRes).
    """
    options = EncodeOptions(preset="prores")
    cmd = build_ffmpeg_commands("in.mp4", "out.mov", options)[0]

    # Video codec and ProRes specific flags
    assert "-c:v" in cmd
    assert cmd[cmd.index("-c:v") + 1] == "prores_ks"
    assert "-profile:v" in cmd
    assert cmd[cmd.index("-profile:v") + 1] == "3"
    assert "-vendor" in cmd
    assert cmd[cmd.index("-vendor") + 1] == "apl0"
    assert "-pix_fmt" in cmd
    assert cmd[cmd.index("-pix_fmt") + 1] == "yuv422p10le"

    # ProRes must not emit -preset
    assert "-preset" not in cmd

    # Audio codec must be pcm_s16le, not aac
    assert "-c:a" in cmd
    assert cmd[cmd.index("-c:a") + 1] == "pcm_s16le"
    assert cmd[cmd.index("-c:a") + 1] != "aac"

    # MOV faststart
    assert "-movflags" in cmd
    assert cmd[cmd.index("-movflags") + 1] == "+faststart"

