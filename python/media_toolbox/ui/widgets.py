"""
Dynamic Libadwaita / GTK4 widgets and state conversion helpers for media_toolbox.

Features:
- Pure domain conversion: build_encode_options_from_state, resolve_default_output_path.
- RateControlWidget: dynamic revealer switching CRF vs Target Size (2-Pass), auto-adapting to codec.
- ResolutionWidget: presets dropdown and custom resolution revealer with even-dimension snapping.
- AudioOptionsWidget: mute toggle and dynamic adjustments revealer (loudness, boost, bitrate).
- MetadataCard: visual badges and technical stream metadata summaries.
- ProgressFooterWidget: progress bar, metric indicators (percentage, speed, ETA, size), and cancellation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from media_toolbox.core.models import EncodeOptions, MediaInfo, ProgressEvent
from media_toolbox.core.presets import (
    get_audio_preset,
    get_video_preset,
    is_audio_preset,
    is_video_preset,
)
from media_toolbox.cli import (
    format_bitrate,
    format_channels,
    format_duration,
    format_file_size,
    format_fps,
)


# ---------------------------------------------------------------------------
# Pure Domain Helpers
# ---------------------------------------------------------------------------


def build_encode_options_from_state(
    preset: str,
    rate_mode: str,  # "crf" | "target_size"
    crf_value: int,
    target_size_mb: float,
    scale: Optional[tuple[int, int]],
    mute_audio: bool,
    normalize_audio: bool,
    volume_boost_db: Optional[float],
    audio_bitrate_kbps: int,
    speed_factor: float = 1.0,
    fps: Optional[int] = None,
    crop: Optional[str] = None,
    speed_preset: Optional[str] = None,
    is_extract_audio: bool = False,
) -> EncodeOptions:
    """
    Pure conversion of form widget states into an immutable EncodeOptions dataclass.
    """
    # Rate control resolution
    crf: Optional[int] = None
    target_size: Optional[float] = None
    two_pass: bool = False

    if not is_extract_audio and preset not in ("gif", "prores"):
        if rate_mode == "crf":
            crf = crf_value
        elif rate_mode == "target_size":
            target_size = target_size_mb
            two_pass = True

    # Audio resolution
    if is_extract_audio:
        eff_mute = False
        eff_extract = True
        eff_norm = normalize_audio
        eff_boost = volume_boost_db if volume_boost_db and abs(volume_boost_db) > 0.01 else None
        eff_audio_br = audio_bitrate_kbps
    else:
        eff_extract = False
        eff_mute = mute_audio
        if eff_mute:
            eff_norm = False
            eff_boost = None
            eff_audio_br = 128
        else:
            eff_norm = normalize_audio
            eff_boost = volume_boost_db if volume_boost_db and abs(volume_boost_db) > 0.01 else None
            eff_audio_br = audio_bitrate_kbps

    # Speed resolution
    eff_speed = speed_factor if abs(speed_factor - 1.0) > 0.001 else None

    # Resolution resolution
    eff_scale = None if is_extract_audio else scale
    eff_crop = None if is_extract_audio else crop

    return EncodeOptions(
        target_size_mb=target_size,
        crf=crf,
        video_codec=preset if not is_extract_audio else "libx264",
        audio_codec=None,
        audio_bitrate_kbps=eff_audio_br,
        scale=eff_scale,
        crop=eff_crop,
        speed=eff_speed,
        fps=fps,
        mute_audio=eff_mute,
        extract_audio=eff_extract,
        normalize_audio=eff_norm,
        volume_boost_db=eff_boost,
        two_pass=two_pass,
        preset=preset,
        speed_preset=speed_preset,
    )


def resolve_default_output_path(
    input_path: str | Path,
    preset_name: str,
    is_extract_audio: bool = False,
    is_target_size: bool = False,
) -> Path:
    """
    Generate default output file path with collision avoidance and overwrite protection.
    """
    inp = Path(input_path).resolve()
    directory = inp.parent
    stem = inp.stem

    if is_extract_audio or is_audio_preset(preset_name):
        ext = get_audio_preset(preset_name).default_extension
        tag = "audio"
    elif is_video_preset(preset_name):
        ext = get_video_preset(preset_name).default_extension
        tag = "compressed" if is_target_size else "transcoded"
    else:
        ext = "mp4"
        tag = "converted"

    candidate = directory / f"{stem}_{tag}.{ext}"
    counter = 1
    # Ensure candidate never overwrites the input file itself or existing disk files
    while candidate == inp or candidate.exists():
        candidate = directory / f"{stem}_{tag}_{counter}.{ext}"
        counter += 1

    return candidate


# ---------------------------------------------------------------------------
# UI Widgets
# ---------------------------------------------------------------------------


class RateControlWidget(Adw.PreferencesGroup):
    """
    Preferences group providing mode selector (CRF vs Target Size)
    with dynamic revealers. Automatically adapts to GIF and ProRes codecs.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(title="Rate Control & Quality", **kwargs)

        self.mode_model = Gtk.StringList.new([
            "Constant Rate Factor (CRF)",
            "Target File Size (2-Pass)",
        ])
        self.mode_row = Adw.ComboRow(
            title="Quality Mode",
            model=self.mode_model,
            selected=0,
        )
        self.add(self.mode_row)

        # CRF Revealer
        self.crf_adj = Gtk.Adjustment(
            value=23,
            lower=0,
            upper=51,
            step_increment=1,
            page_increment=5,
        )
        self.crf_row = Adw.SpinRow(
            title="CRF Quality",
            subtitle="Lower CRF = higher quality & larger file. Recommended: 18–28.",
            adjustment=self.crf_adj,
            climb_rate=1.0,
            digits=0,
        )
        self.crf_revealer = Gtk.Revealer(
            child=self.crf_row,
            reveal_child=True,
            transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
        )
        self.add(self.crf_revealer)

        # Target Size Revealer
        self.target_size_adj = Gtk.Adjustment(
            value=25.0,
            lower=1.0,
            upper=10000.0,
            step_increment=5.0,
            page_increment=25.0,
        )
        self.target_size_row = Adw.SpinRow(
            title="Target File Size (MB)",
            subtitle="Target file size in Megabytes. Computes exact video bitrate across 2 passes.",
            adjustment=self.target_size_adj,
            climb_rate=1.0,
            digits=1,
        )
        self.target_size_revealer = Gtk.Revealer(
            child=self.target_size_row,
            reveal_child=False,
            transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
        )
        self.add(self.target_size_revealer)

        self.mode_row.connect("notify::selected", self._on_mode_changed)

    def _on_mode_changed(self, combo: Adw.ComboRow, _param: Any) -> None:
        idx = combo.get_selected()
        if idx == 0:
            self.crf_revealer.set_reveal_child(True)
            self.target_size_revealer.set_reveal_child(False)
        else:
            self.crf_revealer.set_reveal_child(False)
            self.target_size_revealer.set_reveal_child(True)

    def set_codec_preset(self, preset: str) -> None:
        """Update sensitivity and revealers based on codec capabilities."""
        if preset in ("gif", "prores"):
            self.mode_row.set_sensitive(False)
            self.mode_row.set_subtitle("Fixed quality profile (Rate control unavailable)")
            self.crf_revealer.set_reveal_child(False)
            self.target_size_revealer.set_reveal_child(False)
        else:
            self.mode_row.set_sensitive(True)
            self.mode_row.set_subtitle("")
            if preset in ("av1", "vp9"):
                self.crf_adj.set_upper(63)
            else:
                self.crf_adj.set_upper(51)
            self._on_mode_changed(self.mode_row, None)

    def get_mode(self) -> str:
        return "crf" if self.mode_row.get_selected() == 0 else "target_size"

    def get_crf(self) -> int:
        return int(self.crf_row.get_value())

    def get_target_size_mb(self) -> float:
        return float(self.target_size_row.get_value())


class ResolutionWidget(Adw.PreferencesGroup):
    """
    Preferences group providing resolution scaling with dynamic custom dimension revealers.
    Guarantees even dimension snapping.
    """

    PRESETS = [
        ("Original (Source Resolution)", None),
        ("1080p Full HD (1920 × 1080)", (1920, 1080)),
        ("720p HD (1280 × 720)", (1280, 720)),
        ("480p SD (854 × 480)", (854, 480)),
        ("Custom Resolution...", "custom"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(title="Video Resolution & Dimensions", **kwargs)

        self.res_model = Gtk.StringList.new([p[0] for p in self.PRESETS])
        self.res_row = Adw.ComboRow(
            title="Resolution",
            model=self.res_model,
            selected=0,
        )
        self.add(self.res_row)

        # Custom dimensions box inside revealer
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.width_adj = Gtk.Adjustment(
            value=1920,
            lower=16,
            upper=7680,
            step_increment=2,
            page_increment=16,
        )
        self.width_row = Adw.SpinRow(
            title="Custom Width (px)",
            adjustment=self.width_adj,
            climb_rate=2.0,
            digits=0,
        )
        box.append(self.width_row)

        self.height_adj = Gtk.Adjustment(
            value=1080,
            lower=16,
            upper=4320,
            step_increment=2,
            page_increment=16,
        )
        self.height_row = Adw.SpinRow(
            title="Custom Height (px)",
            adjustment=self.height_adj,
            climb_rate=2.0,
            digits=0,
        )
        box.append(self.height_row)

        self.custom_revealer = Gtk.Revealer(
            child=box,
            reveal_child=False,
            transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
        )
        self.add(self.custom_revealer)

        self.res_row.connect("notify::selected", self._on_resolution_changed)

    def _on_resolution_changed(self, combo: Adw.ComboRow, _param: Any) -> None:
        idx = combo.get_selected()
        self.custom_revealer.set_reveal_child(idx == 4)

    def set_source_resolution(self, width: int, height: int) -> None:
        if width > 0 and height > 0:
            self.res_row.set_subtitle(f"Source: {width} × {height}")
            self.width_row.set_value(width - (width % 2))
            self.height_row.set_value(height - (height % 2))

    def get_scale(self) -> Optional[tuple[int, int]]:
        idx = self.res_row.get_selected()
        if idx == 0:
            return None
        if 1 <= idx <= 3:
            return self.PRESETS[idx][1]  # type: ignore[return-value]
        if idx == 4:
            w = int(self.width_row.get_value())
            h = int(self.height_row.get_value())
            # Enforce even dimensions
            return (w - (w % 2), h - (h % 2))
        return None


class AudioOptionsWidget(Adw.PreferencesGroup):
    """
    Preferences group providing mute toggle and dynamic adjustments revealer
    (loudness normalization, volume boost, bitrate).
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(title="Audio Options", **kwargs)

        self.mute_switch = Adw.SwitchRow(
            title="Mute Audio",
            subtitle="Strip all audio tracks from output (-an)",
            active=False,
        )
        self.add(self.mute_switch)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.norm_switch = Adw.SwitchRow(
            title="Normalize Loudness",
            subtitle="EBU R128 two-pass loudness normalization (loudnorm)",
            active=False,
        )
        box.append(self.norm_switch)

        self.boost_adj = Gtk.Adjustment(
            value=0.0,
            lower=-20.0,
            upper=20.0,
            step_increment=0.5,
            page_increment=2.0,
        )
        self.boost_row = Adw.SpinRow(
            title="Volume Boost (dB)",
            adjustment=self.boost_adj,
            climb_rate=0.5,
            digits=1,
        )
        box.append(self.boost_row)

        self.bitrate_adj = Gtk.Adjustment(
            value=128,
            lower=32,
            upper=320,
            step_increment=32,
            page_increment=64,
        )
        self.bitrate_row = Adw.SpinRow(
            title="Audio Bitrate (kbps)",
            adjustment=self.bitrate_adj,
            climb_rate=32.0,
            digits=0,
        )
        box.append(self.bitrate_row)

        self.adjustments_revealer = Gtk.Revealer(
            child=box,
            reveal_child=True,
            transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
        )
        self.add(self.adjustments_revealer)

        self.mute_switch.connect("notify::active", self._on_mute_changed)

    def _on_mute_changed(self, switch: Adw.SwitchRow, _param: Any) -> None:
        is_muted = switch.get_active()
        self.adjustments_revealer.set_reveal_child(not is_muted)

    def set_has_audio(self, has_audio: bool) -> None:
        self.set_sensitive(has_audio)
        if not has_audio:
            self.set_description("Source file contains no audio streams")
        else:
            self.set_description("")

    def get_mute(self) -> bool:
        return bool(self.mute_switch.get_active())

    def get_normalize(self) -> bool:
        return bool(self.norm_switch.get_active())

    def get_volume_boost(self) -> Optional[float]:
        val = float(self.boost_row.get_value())
        return val if abs(val) > 0.01 else None

    def get_audio_bitrate(self) -> int:
        return int(self.bitrate_row.get_value())


class MetadataCard(Adw.PreferencesGroup):
    """
    Displays media technical specifications, container details, and stream badges.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(title="Source Media Specifications", **kwargs)

        self.badge_row = Adw.ActionRow(title="Classification", subtitle="No media loaded")
        self.add(self.badge_row)

        self.video_row = Adw.ActionRow(title="Video Stream", subtitle="-")
        self.add(self.video_row)

        self.audio_row = Adw.ActionRow(title="Audio Stream", subtitle="-")
        self.add(self.audio_row)

        self.format_row = Adw.ActionRow(title="Format & Duration", subtitle="-")
        self.add(self.format_row)

    def set_media_info(self, media_info: MediaInfo) -> None:
        # Determine classification badge
        if media_info.is_image:
            badge = "[Still Image / Other]"
        elif media_info.has_video and media_info.has_audio:
            badge = "[Video + Audio]"
        elif media_info.has_video:
            badge = "[Silent Video]"
        elif media_info.has_audio:
            badge = "[Audio Only]"
        else:
            badge = "[Still Image / Other]"

        self.badge_row.set_subtitle(badge)

        # Video stream
        pv = media_info.primary_video
        if pv:
            fps_str = format_fps(pv.fps)
            res_str = f"{pv.width} × {pv.height}"
            codec_str = pv.codec_name.upper()
            br_str = format_bitrate(pv.bit_rate) if pv.bit_rate else "-"
            self.video_row.set_subtitle(f"{codec_str} | {res_str} @ {fps_str} | Bitrate: {br_str}")
        else:
            self.video_row.set_subtitle("No video stream")

        # Audio stream
        pa = media_info.primary_audio
        if pa:
            ch_str = format_channels(pa.channel_layout, pa.channels)
            sr_str = f"{pa.sample_rate_khz:.1f} kHz"
            codec_str = pa.codec_name.upper()
            br_str = format_bitrate(pa.bit_rate) if pa.bit_rate else "-"
            self.audio_row.set_subtitle(f"{codec_str} | {ch_str} | {sr_str} | Bitrate: {br_str}")
        else:
            self.audio_row.set_subtitle("No audio stream")

        # Format info
        fmt = media_info.format
        dur_str = format_duration(media_info.duration)
        size_str = format_file_size(fmt.size_bytes)
        self.format_row.set_subtitle(f"{fmt.format_name} | Duration: {dur_str} | Size: {size_str}")

    def clear(self) -> None:
        self.badge_row.set_subtitle("No media loaded")
        self.video_row.set_subtitle("-")
        self.audio_row.set_subtitle("-")
        self.format_row.set_subtitle("-")


class ProgressFooterWidget(Gtk.Box):
    """
    Footer card containing status label, progress bar, speed/ETA/size metrics,
    and a prominent Cancel button. Anchored inside a Gtk.Revealer.
    """

    def __init__(self, on_cancel_callback: Optional[Callable[[], None]] = None, **kwargs: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self.on_cancel_callback = on_cancel_callback

        self.revealer = Gtk.Revealer(
            reveal_child=False,
            transition_type=Gtk.RevealerTransitionType.SLIDE_UP,
        )

        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_box.add_css_class("card")
        card_box.set_margin_start(16)
        card_box.set_margin_end(16)
        card_box.set_margin_bottom(12)
        card_box.set_margin_top(4)

        # Header: status label and cancel button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.status_label = Gtk.Label(label="Ready", xalign=0.0, hexpand=True)
        self.status_label.add_css_class("heading")
        header_box.append(self.status_label)

        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.add_css_class("destructive-action")
        self.cancel_button.connect("clicked", self._on_cancel_clicked)
        header_box.append(self.cancel_button)
        card_box.append(header_box)

        # Progress bar
        self.progress_bar = Gtk.ProgressBar(show_text=False)
        self.progress_bar.set_fraction(0.0)
        card_box.append(self.progress_bar)

        # Metrics row
        metrics_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.pct_label = Gtk.Label(label="0.0%", xalign=0.0)
        self.pct_label.add_css_class("numeric")
        metrics_box.append(self.pct_label)

        self.speed_label = Gtk.Label(label="Speed: -", xalign=0.0)
        metrics_box.append(self.speed_label)

        self.eta_label = Gtk.Label(label="ETA: -", xalign=0.0)
        metrics_box.append(self.eta_label)

        self.size_label = Gtk.Label(label="Size: -", xalign=0.0)
        metrics_box.append(self.size_label)

        card_box.append(metrics_box)

        self.revealer.set_child(card_box)
        self.append(self.revealer)

    def _on_cancel_clicked(self, _btn: Gtk.Button) -> None:
        if self.on_cancel_callback:
            self.on_cancel_callback()

    def start(self, title: str = "Transcoding...") -> None:
        self.status_label.set_text(title)
        self.progress_bar.set_fraction(0.0)
        self.pct_label.set_text("0.0%")
        self.speed_label.set_text("Speed: -")
        self.eta_label.set_text("ETA: -")
        self.size_label.set_text("Size: -")
        self.cancel_button.set_sensitive(True)
        self.cancel_button.set_label("Cancel")
        self.revealer.set_reveal_child(True)

    def update_progress(self, event: ProgressEvent, pass_info: Optional[str] = None) -> None:
        fraction = max(0.0, min(1.0, event.percentage / 100.0))
        self.progress_bar.set_fraction(fraction)
        self.pct_label.set_text(f"{event.percentage:.1f}%")
        if event.speed_str:
            self.speed_label.set_text(f"Speed: {event.speed_str}")
        if event.eta_str:
            self.eta_label.set_text(f"ETA: {event.eta_str}")
        if event.total_size_bytes > 0:
            self.size_label.set_text(f"Size: {format_file_size(event.total_size_bytes)}")
        if pass_info:
            self.status_label.set_text(pass_info)

    def set_cancelling(self) -> None:
        self.cancel_button.set_sensitive(False)
        self.cancel_button.set_label("Cancelling...")
        self.status_label.set_text("Cancelling transcode...")

    def finish(self, success: bool, message: Optional[str] = None) -> None:
        self.cancel_button.set_sensitive(False)
        if success:
            self.progress_bar.set_fraction(1.0)
            self.pct_label.set_text("100.0%")
            self.status_label.set_text(message or "Completed successfully")
        else:
            self.status_label.set_text(message or "Failed")

    def reset(self) -> None:
        self.revealer.set_reveal_child(False)
        self.progress_bar.set_fraction(0.0)
        self.status_label.set_text("Ready")
