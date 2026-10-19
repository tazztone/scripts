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
    AudioPreset,
    VideoPreset,
    get_audio_preset,
    get_container_faststart_args,
    get_video_preset,
    is_audio_preset,
    is_speed_preset,
    is_video_preset,
)
from media_toolbox.core.probe import probe_media


def resolve_video_preset(options: EncodeOptions) -> Optional[VideoPreset]:
    """
    Resolve target VideoPreset from EncodeOptions.

    Prioritizes options.preset when it matches a known video preset over
    options.video_codec (which defaults to 'libx264').
    """
    preset_lower = options.preset.strip().lower() if options.preset else ""
    if is_video_preset(preset_lower):
        return get_video_preset(preset_lower)

    codec_lower = options.video_codec.strip().lower() if options.video_codec else ""
    if is_video_preset(codec_lower):
        return get_video_preset(codec_lower)

    return None


def resolve_audio_preset(options: EncodeOptions) -> Optional[AudioPreset]:
    """
    Resolve target AudioPreset from EncodeOptions.

    Prioritizes options.preset when it matches a known audio preset over
    options.video_codec and options.audio_codec.
    """
    preset_lower = options.preset.strip().lower() if options.preset else ""
    if is_audio_preset(preset_lower):
        return get_audio_preset(preset_lower)

    if not is_video_preset(preset_lower):
        codec_lower = options.video_codec.strip().lower() if options.video_codec else ""
        if is_audio_preset(codec_lower):
            return get_audio_preset(codec_lower)

    if options.audio_codec and is_audio_preset(options.audio_codec):
        return get_audio_preset(options.audio_codec)

    return None


def resolve_speed_preset(options: EncodeOptions) -> Optional[str]:
    """
    Resolve valid FFmpeg encoder speed preset from EncodeOptions.

    Distinguishes format preset names ('h264', 'h265', etc.) from encoder speed
    presets ('ultrafast', 'fast', 'medium', 'slow', etc.).
    Only returns recognized speed presets, or None.
    """
    speed_opt = getattr(options, "speed_preset", None)
    if speed_opt and is_speed_preset(speed_opt):
        return speed_opt.strip().lower()

    if options.preset and is_speed_preset(options.preset):
        return options.preset.strip().lower()

    return None


def resolve_audio_codec(
    options: EncodeOptions,
    v_preset: Optional[VideoPreset],
    output_path: str,
) -> str:
    """
    Dynamically resolve the appropriate FFmpeg audio encoder codec.

    Resolution rules:
    1. If the output container is .webm or the video preset is VP9/WebM:
       - Only Vorbis and Opus are valid in WebM.
       - If user explicitly requested Vorbis ('vorbis', 'libvorbis'), resolves to 'libvorbis'.
       - If user explicitly requested Opus ('opus', 'libopus'), resolves to 'libopus'.
       - Otherwise (including None, default, or incompatible codecs like 'aac'),
         resolves to 'libopus'.
    2. If options.audio_codec was explicitly provided by the caller:
       - Returns options.audio_codec as requested.
    3. If options.audio_codec is None:
       - Defers to v_preset.default_audio_codec if available
         ('pcm_s16le' for ProRes, 'libopus' for AV1, 'aac' for H.264/H.265).
    4. Ultimate fallback: 'aac'.
    """
    out_ext = Path(output_path).suffix.lower()
    is_webm_container = out_ext == ".webm" or (v_preset is not None and v_preset.name == "vp9")

    req_audio = options.audio_codec.strip().lower() if options.audio_codec else None

    if is_webm_container:
        if req_audio in ("vorbis", "libvorbis"):
            return "libvorbis"
        return "libopus"

    if req_audio is not None:
        return options.audio_codec

    if v_preset is not None and v_preset.default_audio_codec:
        return v_preset.default_audio_codec

    return "aac"


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
    audio_preset = resolve_audio_preset(options)
    if audio_preset is None:
        out_ext = Path(output_path).suffix.lstrip(".").lower()
        if is_audio_preset(out_ext):
            audio_preset = get_audio_preset(out_ext)

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

    v_preset = resolve_video_preset(options)
    speed_preset = resolve_speed_preset(options)

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
                speed_preset=speed_preset,
            )
        )
    else:
        pass1_cmd.extend([
            "-c:v", options.video_codec,
            "-b:v", f"{int(v_bitrate_kbps)}k",
            "-pass", "1",
            "-passlogfile", log_prefix,
        ])
        if speed_preset:
            pass1_cmd.extend(["-preset", speed_preset])

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
                speed_preset=speed_preset,
            )
        )
    else:
        pass2_cmd.extend([
            "-c:v", options.video_codec,
            "-b:v", f"{int(v_bitrate_kbps)}k",
            "-pass", "2",
            "-passlogfile", log_prefix,
        ])
        if speed_preset:
            pass2_cmd.extend(["-preset", speed_preset])

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
        a_codec = resolve_audio_codec(options, v_preset, output_path)
        pass2_cmd.extend(["-c:a", a_codec])
        if not a_codec.startswith("pcm_"):
            pass2_cmd.extend(["-b:a", f"{options.audio_bitrate_kbps}k"])

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
    v_preset = resolve_video_preset(options)
    speed_preset = resolve_speed_preset(options)

    if v_preset is not None:
        cmd.extend(v_preset.build_video_args(crf=options.crf, speed_preset=speed_preset))
    else:
        cmd.extend(["-c:v", options.video_codec])
        if options.crf is not None:
            cmd.extend(["-crf", str(options.crf)])
        if speed_preset:
            cmd.extend(["-preset", speed_preset])

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
        a_codec = resolve_audio_codec(options, v_preset, output_path)
        cmd.extend(["-c:a", a_codec])
        if not a_codec.startswith("pcm_"):
            cmd.extend(["-b:a", f"{options.audio_bitrate_kbps}k"])

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

    preset_lower = options.preset.strip().lower() if options.preset else ""
    codec_lower = options.video_codec.strip().lower() if options.video_codec else ""

    # Mode 1: Audio Extraction / Audio-Only Presets
    if (
        options.extract_audio
        or is_audio_preset(preset_lower)
        or (not is_video_preset(preset_lower) and is_audio_preset(codec_lower))
    ):
        return [build_audio_extract_command(input_str, output_str, options, include_progress=include_progress)]

    # Mode 2: Animated GIF
    if preset_lower == "gif" or (not is_video_preset(preset_lower) and codec_lower == "gif"):
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
