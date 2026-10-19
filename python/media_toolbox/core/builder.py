"""
Deterministic FFmpeg CLI command builder for media_toolbox.

This module provides the central command line construction engine for media_toolbox,
assembling fully-qualified FFmpeg invocations for:
- Single-pass CRF video encoding
- Two-pass bitrate targeting (Pass 1 null sink and Pass 2 final output)
- Standalone audio extraction and transcoding
- Two-stage animated GIF generation via palettegen / paletteuse

INVARIANT: Must have ZERO imports from GUI toolkits (gi, Gtk, Adw, etc.).
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Optional

from media_toolbox.core.bitrate import calculate_target_video_bitrate
from media_toolbox.core.filtergraph import (
    build_audio_filter,
    build_video_filter,
)
from media_toolbox.core.models import EncodeOptions, MediaInfo
from media_toolbox.core.presets import (
    get_audio_preset,
    get_container_faststart_args,
    get_video_preset,
    is_audio_preset,
    is_video_preset,
)
from media_toolbox.core.probe import probe_media


def build_audio_extract_command(
    input_path: str,
    output_path: str,
    options: EncodeOptions,
    include_progress: bool = False,
) -> list[str]:
    """
    Construct FFmpeg command for audio extraction / transcoding.
    """
    cmd: list[str] = ["ffmpeg", "-y", "-nostdin"]
    if include_progress:
        cmd.extend(["-progress", "pipe:1", "-nostats"])

    cmd.extend(["-i", input_path, "-vn"])

    # Audio filters
    af = build_audio_filter(
        speed=options.speed,
        normalize_loudness=options.normalize_audio,
        volume_boost_db=options.volume_boost_db,
    )
    if af:
        cmd.extend(["-af", ",".join(af)])

    # Resolve audio preset / codec
    codec_lower = options.video_codec.lower() if options.video_codec else ""
    preset_lower = options.preset.lower() if options.preset else ""

    if is_audio_preset(codec_lower):
        audio_preset = get_audio_preset(codec_lower)
    elif is_audio_preset(preset_lower):
        audio_preset = get_audio_preset(preset_lower)
    elif options.audio_codec and is_audio_preset(options.audio_codec):
        audio_preset = get_audio_preset(options.audio_codec)
    else:
        audio_preset = None

    if audio_preset is not None:
        cmd.extend(audio_preset.build_audio_args(bitrate_kbps=options.audio_bitrate_kbps, extract_audio=False))
    else:
        codec = options.audio_codec or "aac"
        cmd.extend(["-c:a", codec, "-b:a", f"{options.audio_bitrate_kbps}k"])

    cmd.extend(options.extra_args)
    cmd.append(output_path)
    return cmd


def build_gif_command(
    input_path: str,
    output_path: str,
    options: EncodeOptions,
    include_progress: bool = False,
) -> list[str]:
    """
    Construct FFmpeg command for paletted animated GIF generation.
    """
    cmd: list[str] = ["ffmpeg", "-y", "-nostdin"]
    if include_progress:
        cmd.extend(["-progress", "pipe:1", "-nostats"])

    cmd.extend(["-i", input_path])

    vf = build_video_filter(
        scale=options.scale,
        crop=options.crop,
        pad=options.pad,
        speed=options.speed,
        fps=options.fps,
    )

    if vf:
        filter_spec = f"[0:v]{','.join(vf)},split[a][b];[a]palettegen[p];[b][p]paletteuse"
    else:
        filter_spec = "[0:v]split[a][b];[a]palettegen[p];[b][p]paletteuse"

    cmd.extend(["-filter_complex", filter_spec, "-an"])

    if not output_path.lower().endswith(".gif"):
        cmd.extend(["-f", "gif"])

    cmd.extend(options.extra_args)
    cmd.append(output_path)
    return cmd


def build_two_pass_commands(
    input_path: str,
    output_path: str,
    options: EncodeOptions,
    media_info: Optional[MediaInfo] = None,
    pass_logfile: Optional[str] = None,
    include_progress: bool = False,
) -> list[list[str]]:
    """
    Construct two FFmpeg commands for two-pass bitrate targeting.
    Pass 1 writes statistics to null sink with audio disabled.
    Pass 2 encodes final output file with identical video filters.
    """
    if media_info is None:
        if os.path.exists(input_path):
            media_info = probe_media(input_path)
        else:
            raise ValueError("media_info is required when input file is not on disk")

    duration = media_info.duration
    if duration <= 0:
        raise ValueError(f"Cannot calculate target bitrate: media duration is {duration}")

    # Audio bitrate for math formula
    if options.mute_audio or not media_info.has_audio:
        audio_br = 0
    else:
        audio_br = options.audio_bitrate_kbps

    target_mb = options.target_size_mb if options.target_size_mb is not None else 25.0
    v_bitrate_kbps = calculate_target_video_bitrate(
        target_size_mb=target_mb,
        duration_seconds=duration,
        audio_bitrate_kbps=audio_br,
    )

    log_prefix = pass_logfile or os.path.join(tempfile.gettempdir(), f"ffmpeg2pass_{os.getpid()}")

    vf = build_video_filter(
        scale=options.scale,
        crop=options.crop,
        pad=options.pad,
        speed=options.speed,
        fps=options.fps,
    )

    codec_lower = options.video_codec.lower() if options.video_codec else ""
    preset_lower = options.preset.lower() if options.preset else ""

    if is_video_preset(codec_lower):
        v_preset = get_video_preset(codec_lower)
    elif is_video_preset(preset_lower):
        v_preset = get_video_preset(preset_lower)
    else:
        v_preset = None

    # Pass 1 Command
    pass1_cmd: list[str] = ["ffmpeg", "-y", "-nostdin"]
    if include_progress:
        pass1_cmd.extend(["-progress", "pipe:1", "-nostats"])
    pass1_cmd.extend(["-i", input_path])

    if vf:
        pass1_cmd.extend(["-vf", ",".join(vf)])

    if v_preset is not None:
        pass1_cmd.extend(
            v_preset.build_video_args(
                bitrate_kbps=v_bitrate_kbps,
                pass_num=1,
                pass_logfile=log_prefix,
                speed_preset=options.preset,
            )
        )
    else:
        pass1_cmd.extend([
            "-c:v", options.video_codec,
            "-b:v", f"{int(v_bitrate_kbps)}k",
            "-pass", "1",
            "-passlogfile", log_prefix,
        ])
        if options.preset:
            pass1_cmd.extend(["-preset", options.preset])

    pass1_cmd.extend(["-an", "-f", "null", os.devnull])

    # Pass 2 Command
    pass2_cmd: list[str] = ["ffmpeg", "-y", "-nostdin"]
    if include_progress:
        pass2_cmd.extend(["-progress", "pipe:1", "-nostats"])
    pass2_cmd.extend(["-i", input_path])

    if vf:
        pass2_cmd.extend(["-vf", ",".join(vf)])

    if v_preset is not None:
        pass2_cmd.extend(
            v_preset.build_video_args(
                bitrate_kbps=v_bitrate_kbps,
                pass_num=2,
                pass_logfile=log_prefix,
                speed_preset=options.preset,
            )
        )
    else:
        pass2_cmd.extend([
            "-c:v", options.video_codec,
            "-b:v", f"{int(v_bitrate_kbps)}k",
            "-pass", "2",
            "-passlogfile", log_prefix,
        ])
        if options.preset:
            pass2_cmd.extend(["-preset", options.preset])

    # Pass 2 Audio
    if options.mute_audio or not media_info.has_audio:
        pass2_cmd.append("-an")
    else:
        af = build_audio_filter(
            speed=options.speed,
            normalize_loudness=options.normalize_audio,
            volume_boost_db=options.volume_boost_db,
        )
        if af:
            pass2_cmd.extend(["-af", ",".join(af)])
        a_codec = options.audio_codec or (v_preset.default_audio_codec if v_preset else "aac") or "aac"
        pass2_cmd.extend(["-c:a", a_codec, "-b:a", f"{options.audio_bitrate_kbps}k"])

    pass2_cmd.extend(get_container_faststart_args(output_path))
    pass2_cmd.extend(options.extra_args)
    pass2_cmd.append(output_path)

    return [pass1_cmd, pass2_cmd]


def build_single_pass_command(
    input_path: str,
    output_path: str,
    options: EncodeOptions,
    media_info: Optional[MediaInfo] = None,
    include_progress: bool = False,
) -> list[str]:
    """
    Construct FFmpeg command for single-pass CRF or fixed-bitrate video encoding.
    """
    cmd: list[str] = ["ffmpeg", "-y", "-nostdin"]
    if include_progress:
        cmd.extend(["-progress", "pipe:1", "-nostats"])

    cmd.extend(["-i", input_path])

    # Video filters
    vf = build_video_filter(
        scale=options.scale,
        crop=options.crop,
        pad=options.pad,
        speed=options.speed,
        fps=options.fps,
    )
    if vf:
        cmd.extend(["-vf", ",".join(vf)])

    # Video codec & quality
    codec_lower = options.video_codec.lower() if options.video_codec else ""
    preset_lower = options.preset.lower() if options.preset else ""

    if is_video_preset(codec_lower):
        v_preset = get_video_preset(codec_lower)
    elif is_video_preset(preset_lower):
        v_preset = get_video_preset(preset_lower)
    else:
        v_preset = None

    if v_preset is not None:
        cmd.extend(v_preset.build_video_args(crf=options.crf, speed_preset=options.preset))
    else:
        cmd.extend(["-c:v", options.video_codec])
        if options.crf is not None:
            cmd.extend(["-crf", str(options.crf)])
        if options.preset:
            cmd.extend(["-preset", options.preset])

    # Audio handling
    if options.mute_audio or (media_info is not None and not media_info.has_audio):
        cmd.append("-an")
    else:
        af = build_audio_filter(
            speed=options.speed,
            normalize_loudness=options.normalize_audio,
            volume_boost_db=options.volume_boost_db,
        )
        if af:
            cmd.extend(["-af", ",".join(af)])
        a_codec = options.audio_codec or (v_preset.default_audio_codec if v_preset else "aac") or "aac"
        cmd.extend(["-c:a", a_codec, "-b:a", f"{options.audio_bitrate_kbps}k"])

    cmd.extend(get_container_faststart_args(output_path))
    cmd.extend(options.extra_args)
    cmd.append(output_path)

    return cmd


def build_ffmpeg_commands(
    input_path: str | Path,
    output_path: str | Path,
    options: EncodeOptions,
    media_info: Optional[MediaInfo] = None,
    pass_logfile: Optional[str] = None,
    include_progress: bool = False,
) -> list[list[str]]:
    """
    Construct deterministic FFmpeg CLI argument list(s).

    Returns:
        list[list[str]]: 1 command for single-pass/CRF/audio/GIF; 2 commands for 2-pass.

    Raises:
        ValueError: On contradictory options (e.g. mute + extract audio, GIF + two-pass),
                    non-positive speeds/target sizes, or missing duration for bitrate targeting.
    """
    input_str = str(input_path)
    output_str = str(output_path)

    # Validation
    if options.extract_audio and options.mute_audio:
        raise ValueError("Cannot simultaneously extract and mute audio")
    if options.speed is not None and options.speed <= 0:
        raise ValueError(f"Speed multiplier must be positive, got {options.speed}")
    if options.target_size_mb is not None and options.target_size_mb <= 0:
        raise ValueError(f"target_size_mb must be positive, got {options.target_size_mb}")

    codec_lower = options.video_codec.lower() if options.video_codec else ""
    preset_lower = options.preset.lower() if options.preset else ""

    # Mode 1: Audio Extraction / Audio-Only Presets
    if options.extract_audio or is_audio_preset(codec_lower) or is_audio_preset(preset_lower):
        return [build_audio_extract_command(input_str, output_str, options, include_progress=include_progress)]

    # Mode 2: Animated GIF
    if codec_lower == "gif" or preset_lower == "gif":
        if options.two_pass:
            raise ValueError("Two-pass encoding is not supported for GIF preset")
        return [build_gif_command(input_str, output_str, options, include_progress=include_progress)]

    # Mode 3: Two-Pass Bitrate Targeting
    if options.two_pass or options.target_size_mb is not None:
        return build_two_pass_commands(
            input_path=input_str,
            output_path=output_str,
            options=options,
            media_info=media_info,
            pass_logfile=pass_logfile,
            include_progress=include_progress,
        )

    # Mode 4: Single-Pass Video (CRF)
    return [
        build_single_pass_command(
            input_path=input_str,
            output_path=output_str,
            options=options,
            media_info=media_info,
            include_progress=include_progress,
        )
    ]
