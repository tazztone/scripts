"""
MainWindow Libadwaita application window for media_toolbox.

Features:
- HeaderBar with file opening, subtitle showing active file, and application menu.
- Dual-mode workflow: Transcode Video vs Extract Audio via Adw.ViewStack / Adw.ViewSwitcher.
- Dynamic preferences pages integrating RateControlWidget, ResolutionWidget, AudioOptionsWidget, and MetadataCard.
- Output destination file picker via Gtk.FileDialog.
- Non-blocking daemon background worker thread executing core.runner.run_ffmpeg_pipeline.
- Thread-safe UI updates dispatched via GLib.idle_add with GLib.SOURCE_REMOVE returns.
- Clean cancellation with process group termination and incomplete partial file cleanup.
- Window close-request handler ensuring no orphaned background FFmpeg processes.
"""

from __future__ import annotations

import os
from pathlib import Path
import threading
from typing import Any, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from media_toolbox.core.builder import build_ffmpeg_commands
from media_toolbox.core.models import EncodeOptions, MediaInfo, ProgressEvent
from media_toolbox.core.probe import probe_media
from media_toolbox.core.runner import (
    RunnerCancelledError,
    RunnerError,
    run_ffmpeg_pipeline,
)
from media_toolbox.ui.widgets import (
    AudioOptionsWidget,
    MetadataCard,
    ProgressFooterWidget,
    RateControlWidget,
    ResolutionWidget,
    build_encode_options_from_state,
    resolve_default_output_path,
)


class MainWindow(Adw.ApplicationWindow):
    """
    Main Libadwaita application window.
    """

    VIDEO_PRESETS = [
        ("H.264 (Universal / Web)", "h264"),
        ("H.265 (High Efficiency)", "h265"),
        ("AV1 (Next-Gen Open)", "av1"),
        ("VP9 (WebM)", "vp9"),
        ("Apple ProRes (Editing)", "prores"),
        ("Animated GIF", "gif"),
    ]

    AUDIO_PRESETS = [
        ("MP3 (Universal)", "mp3"),
        ("AAC (High Quality)", "aac"),
        ("Opus (Low Bitrate Speech/Music)", "opus"),
        ("FLAC (Lossless)", "flac"),
    ]

    CROP_PRESETS = [
        ("None (Original)", None),
        ("16:9 Landscape", "16:9"),
        ("9:16 Portrait / Shorts", "9:16"),
        ("1:1 Square", "1:1"),
        ("4:3 Classic", "4:3"),
        ("21:9 Ultrawide", "21:9"),
    ]

    SPEED_PRESETS = [
        ("1.0x (Normal)", 1.0),
        ("0.5x (Half Speed)", 0.5),
        ("0.75x", 0.75),
        ("1.25x", 1.25),
        ("1.5x", 1.5),
        ("2.0x (Double Speed)", 2.0),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.set_default_size(920, 740)
        self.set_size_request(640, 500)

        self.input_file: Optional[Path] = None
        self.media_info: Optional[MediaInfo] = None
        self.video_output_path: Optional[Path] = None
        self.audio_output_path: Optional[Path] = None
        self.cancel_event: Optional[threading.Event] = None
        self.is_transcoding: bool = False
        self.open_btn: Optional[Gtk.Button] = None

        self._build_ui()
        self.connect("close-request", self._on_close_request)

    def _build_ui(self) -> None:
        """Construct the complete Libadwaita window UI layout."""
        # Top Header Bar
        self.header_bar = Adw.HeaderBar()
        self.open_btn = Gtk.Button(
            icon_name="document-open-symbolic",
            tooltip_text="Open Media File (<Ctrl>O)",
        )
        self.open_btn.connect("clicked", lambda _b: self.open_file_dialog())
        self.header_bar.pack_start(self.open_btn)

        self.window_title = Adw.WindowTitle(
            title="Media Toolbox",
            subtitle="No media selected",
        )
        self.header_bar.set_title_widget(self.window_title)

        # Menu button
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu = Gio.Menu()
        menu.append("Open File...", "app.open")
        menu.append("About Media Toolbox", "app.about")
        menu.append("Quit", "app.quit")
        menu_btn.set_menu_model(menu)
        self.header_bar.pack_end(menu_btn)

        # Root box inside ToastOverlay
        self.toast_overlay = Adw.ToastOverlay()
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root_box.append(self.header_bar)

        # Main Stack: empty state vs loaded state
        self.main_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)

        # 1. Empty State Page
        empty_page = Adw.StatusPage(
            title="Media Toolbox",
            description="Open a video or audio file to inspect, transcode, or extract audio.",
            icon_name="video-x-generic-symbolic",
        )
        empty_btn = Gtk.Button(
            label="Open Media File...",
            halign=Gtk.Align.CENTER,
            css_classes=["suggested-action", "pill"],
        )
        empty_btn.connect("clicked", lambda _b: self.open_file_dialog())
        empty_page.set_child(empty_btn)
        self.main_stack.add_named(empty_page, "empty")

        # 2. Loaded State Page
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_start(18)
        content_box.set_margin_end(18)
        content_box.set_margin_top(14)
        content_box.set_margin_bottom(14)

        # Metadata summary card
        self.metadata_card = MetadataCard()
        content_box.append(self.metadata_card)

        # Tabs for Transcode Video vs Extract Audio
        self.view_stack = Adw.ViewStack()

        # Tab 1: Transcode Video
        transcode_page = self._build_transcode_page()
        self.view_stack.add_titled_with_icon(
            transcode_page,
            "transcode",
            "Transcode Video",
            "video-x-generic-symbolic",
        )

        # Tab 2: Extract Audio
        extract_page = self._build_extract_audio_page()
        self.view_stack.add_titled_with_icon(
            extract_page,
            "extract",
            "Extract Audio",
            "audio-x-generic-symbolic",
        )

        self.view_switcher = Adw.ViewSwitcher(
            stack=self.view_stack,
            policy=Adw.ViewSwitcherPolicy.WIDE,
            halign=Gtk.Align.CENTER,
        )
        content_box.append(self.view_switcher)
        content_box.append(self.view_stack)

        scrolled.set_child(content_box)
        self.main_stack.add_named(scrolled, "loaded")

        root_box.append(self.main_stack)

        # Progress Footer (anchored at bottom)
        self.progress_footer = ProgressFooterWidget(on_cancel_callback=self._on_cancel_clicked)
        root_box.append(self.progress_footer)

        self.toast_overlay.set_child(root_box)
        self.set_content(self.toast_overlay)

    def _build_transcode_page(self) -> Adw.PreferencesPage:
        """Construct the Transcode Video preferences page."""
        page = Adw.PreferencesPage()

        # Codec Preset Group
        preset_group = Adw.PreferencesGroup(title="Target Codec & Format")
        preset_strings = [p[0] for p in self.VIDEO_PRESETS]
        self.video_preset_row = Adw.ComboRow(
            title="Video Codec Preset",
            model=Gtk.StringList.new(preset_strings),
            selected=0,
        )
        self.video_preset_row.connect("notify::selected", self._on_video_preset_changed)
        preset_group.add(self.video_preset_row)
        page.add(preset_group)

        # Rate Control & Quality
        self.rate_widget = RateControlWidget()
        self.rate_widget.mode_row.connect("notify::selected", lambda *_: self._update_default_output_paths())
        page.add(self.rate_widget)

        # Resolution & Dimensions
        self.res_widget = ResolutionWidget()
        page.add(self.res_widget)

        # Video Adjustments Group (Crop & Speed)
        adjust_group = Adw.PreferencesGroup(title="Video Transformations")
        crop_strings = [c[0] for c in self.CROP_PRESETS]
        self.crop_row = Adw.ComboRow(
            title="Aspect Ratio Crop",
            model=Gtk.StringList.new(crop_strings),
            selected=0,
        )
        adjust_group.add(self.crop_row)

        speed_strings = [s[0] for s in self.SPEED_PRESETS]
        self.speed_row = Adw.ComboRow(
            title="Playback Speed",
            model=Gtk.StringList.new(speed_strings),
            selected=0,
        )
        adjust_group.add(self.speed_row)
        page.add(adjust_group)

        # Audio Adjustments
        self.audio_widget = AudioOptionsWidget()
        page.add(self.audio_widget)

        # Destination & Action Group
        action_group = Adw.PreferencesGroup(title="Destination & Action")
        self.video_dest_row = Adw.ActionRow(
            title="Output File",
            subtitle="Not configured",
        )
        browse_btn = Gtk.Button(label="Browse...")
        browse_btn.connect("clicked", lambda _b: self.choose_output_destination(is_audio=False))
        self.video_dest_row.add_suffix(browse_btn)
        action_group.add(self.video_dest_row)

        self.transcode_btn = Gtk.Button(
            label="Start Transcode",
            halign=Gtk.Align.END,
            css_classes=["suggested-action"],
            margin_top=8,
            margin_bottom=8,
        )
        self.transcode_btn.connect("clicked", lambda _b: self._start_transcode())
        action_group.add(self.transcode_btn)

        page.add(action_group)
        return page

    def _build_extract_audio_page(self) -> Adw.PreferencesPage:
        """Construct the standalone Extract Audio preferences page."""
        page = Adw.PreferencesPage()

        # Audio Format Group
        format_group = Adw.PreferencesGroup(title="Audio Format & Bitrate")
        audio_preset_strings = [p[0] for p in self.AUDIO_PRESETS]
        self.audio_preset_row = Adw.ComboRow(
            title="Audio Format",
            model=Gtk.StringList.new(audio_preset_strings),
            selected=0,
        )
        self.audio_preset_row.connect("notify::selected", self._on_audio_preset_changed)
        format_group.add(self.audio_preset_row)

        self.extract_bitrate_adj = Gtk.Adjustment(
            value=192,
            lower=32,
            upper=320,
            step_increment=32,
            page_increment=64,
        )
        self.extract_bitrate_row = Adw.SpinRow(
            title="Audio Bitrate (kbps)",
            adjustment=self.extract_bitrate_adj,
            climb_rate=32.0,
            digits=0,
        )
        format_group.add(self.extract_bitrate_row)
        page.add(format_group)

        # Audio Adjustments Group
        adjust_group = Adw.PreferencesGroup(title="Audio Processing")
        speed_strings = [s[0] for s in self.SPEED_PRESETS]
        self.extract_speed_row = Adw.ComboRow(
            title="Playback Speed",
            model=Gtk.StringList.new(speed_strings),
            selected=0,
        )
        adjust_group.add(self.extract_speed_row)

        self.extract_norm_switch = Adw.SwitchRow(
            title="Normalize Loudness",
            subtitle="EBU R128 two-pass loudness normalization (loudnorm)",
            active=False,
        )
        adjust_group.add(self.extract_norm_switch)

        self.extract_boost_adj = Gtk.Adjustment(
            value=0.0,
            lower=-20.0,
            upper=20.0,
            step_increment=0.5,
            page_increment=2.0,
        )
        self.extract_boost_row = Adw.SpinRow(
            title="Volume Boost (dB)",
            adjustment=self.extract_boost_adj,
            climb_rate=0.5,
            digits=1,
        )
        adjust_group.add(self.extract_boost_row)
        page.add(adjust_group)

        # Destination & Action Group
        action_group = Adw.PreferencesGroup(title="Destination & Action")
        self.audio_dest_row = Adw.ActionRow(
            title="Output File",
            subtitle="Not configured",
        )
        browse_btn = Gtk.Button(label="Browse...")
        browse_btn.connect("clicked", lambda _b: self.choose_output_destination(is_audio=True))
        self.audio_dest_row.add_suffix(browse_btn)
        action_group.add(self.audio_dest_row)

        self.extract_btn = Gtk.Button(
            label="Extract Audio",
            halign=Gtk.Align.END,
            css_classes=["suggested-action"],
            margin_top=8,
            margin_bottom=8,
        )
        self.extract_btn.connect("clicked", lambda _b: self._start_extract_audio())
        action_group.add(self.extract_btn)

        page.add(action_group)
        return page

    # -----------------------------------------------------------------------
    # File Dialogs & Loading
    # -----------------------------------------------------------------------

    def open_file_dialog(self) -> None:
        """Present modern async file chooser portal."""
        if self.is_transcoding:
            self.toast_overlay.add_toast(Adw.Toast(title="Cannot open file while transcoding is in progress."))
            return
        dialog = Gtk.FileDialog(title="Select Media File")
        dialog.open(self, None, self._on_file_dialog_finish)

    def _on_file_dialog_finish(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            gfile = dialog.open_finish(result)
            if gfile:
                path = gfile.get_path()
                if path:
                    self.load_media_file(path)
        except Exception:
            pass  # User cancelled dialog

    def choose_output_destination(self, is_audio: bool = False) -> None:
        """Present save file dialog for destination selection."""
        dialog = Gtk.FileDialog(title="Select Destination File")
        current = self.audio_output_path if is_audio else self.video_output_path
        if current:
            dialog.set_initial_name(current.name)
            dialog.set_initial_folder(Gio.File.new_for_path(str(current.parent)))

        dialog.save(self, None, lambda d, res: self._on_dest_dialog_finish(d, res, is_audio))

    def _on_dest_dialog_finish(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult, is_audio: bool) -> None:
        try:
            gfile = dialog.save_finish(result)
            if gfile:
                p = Path(gfile.get_path())
                if is_audio:
                    self.audio_output_path = p
                    self.audio_dest_row.set_subtitle(str(p))
                else:
                    self.video_output_path = p
                    self.video_dest_row.set_subtitle(str(p))
        except Exception:
            pass  # User cancelled

    def load_media_file(self, path: str | Path) -> None:
        """Inspect media file and configure widgets."""
        if self.is_transcoding:
            self.toast_overlay.add_toast(Adw.Toast(title="Cannot load file while transcoding is in progress."))
            return
        p = Path(path).resolve()
        if not p.exists():
            self.toast_overlay.add_toast(Adw.Toast(title=f"File not found: {p.name}"))
            return

        try:
            media_info = probe_media(p)
        except Exception as exc:
            self.toast_overlay.add_toast(Adw.Toast(title=f"Failed to probe media: {exc}"))
            return

        self.input_file = p
        self.media_info = media_info
        self.window_title.set_subtitle(p.name)
        self.metadata_card.set_media_info(media_info)

        if media_info.primary_video:
            pv = media_info.primary_video
            self.res_widget.set_source_resolution(pv.width, pv.height)

        self.audio_widget.set_has_audio(media_info.has_audio)
        self._update_default_output_paths()
        self.main_stack.set_visible_child_name("loaded")

    # -----------------------------------------------------------------------
    # Preset & Output Path Management
    # -----------------------------------------------------------------------

    def get_current_video_preset(self) -> str:
        idx = self.video_preset_row.get_selected()
        return self.VIDEO_PRESETS[idx][1]

    def get_current_audio_preset(self) -> str:
        idx = self.audio_preset_row.get_selected()
        return self.AUDIO_PRESETS[idx][1]

    def _on_video_preset_changed(self, combo: Adw.ComboRow, _param: Any) -> None:
        preset = self.get_current_video_preset()
        self.rate_widget.set_codec_preset(preset)
        self._update_default_output_paths()

    def _on_audio_preset_changed(self, combo: Adw.ComboRow, _param: Any) -> None:
        preset = self.get_current_audio_preset()
        self.extract_bitrate_row.set_sensitive(preset != "flac")
        self._update_default_output_paths()

    def _update_default_output_paths(self) -> None:
        if not self.input_file:
            return

        # Video path
        video_preset = self.get_current_video_preset()
        is_target_size = (self.rate_widget.get_mode() == "target_size") and video_preset not in ("gif", "prores")
        self.video_output_path = resolve_default_output_path(
            self.input_file,
            video_preset,
            is_extract_audio=False,
            is_target_size=is_target_size,
        )
        self.video_dest_row.set_subtitle(str(self.video_output_path))

        # Audio path
        audio_preset = self.get_current_audio_preset()
        self.audio_output_path = resolve_default_output_path(
            self.input_file,
            audio_preset,
            is_extract_audio=True,
        )
        self.audio_dest_row.set_subtitle(str(self.audio_output_path))

    # -----------------------------------------------------------------------
    # Form Extraction
    # -----------------------------------------------------------------------

    def get_transcode_options(self) -> EncodeOptions:
        preset = self.get_current_video_preset()
        rate_mode = self.rate_widget.get_mode()
        crf_val = self.rate_widget.get_crf()
        target_size_mb = self.rate_widget.get_target_size_mb()
        scale = self.res_widget.get_scale()

        crop_idx = self.crop_row.get_selected()
        crop = self.CROP_PRESETS[crop_idx][1]

        speed_idx = self.speed_row.get_selected()
        speed_factor = self.SPEED_PRESETS[speed_idx][1]

        mute = self.audio_widget.get_mute()
        norm = self.audio_widget.get_normalize()
        boost = self.audio_widget.get_volume_boost()
        audio_br = self.audio_widget.get_audio_bitrate()

        return build_encode_options_from_state(
            preset=preset,
            rate_mode=rate_mode,
            crf_value=crf_val,
            target_size_mb=target_size_mb,
            scale=scale,
            crop=crop,
            mute_audio=mute,
            normalize_audio=norm,
            volume_boost_db=boost,
            audio_bitrate_kbps=audio_br,
            speed_factor=speed_factor,
            is_extract_audio=False,
        )

    def get_extract_audio_options(self) -> EncodeOptions:
        preset = self.get_current_audio_preset()
        bitrate = int(self.extract_bitrate_row.get_value())
        speed_idx = self.extract_speed_row.get_selected()
        speed_factor = self.SPEED_PRESETS[speed_idx][1]
        norm = bool(self.extract_norm_switch.get_active())
        boost_val = float(self.extract_boost_row.get_value())
        boost = boost_val if abs(boost_val) > 0.01 else None

        return build_encode_options_from_state(
            preset=preset,
            rate_mode="crf",
            crf_value=23,
            target_size_mb=25.0,
            scale=None,
            mute_audio=False,
            normalize_audio=norm,
            volume_boost_db=boost,
            audio_bitrate_kbps=bitrate,
            speed_factor=speed_factor,
            is_extract_audio=True,
        )

    # -----------------------------------------------------------------------
    # Non-Blocking Thread Execution
    # -----------------------------------------------------------------------

    def _set_ui_controls_sensitive(self, sensitive: bool) -> None:
        self.view_stack.set_sensitive(sensitive)
        self.transcode_btn.set_sensitive(sensitive)
        self.extract_btn.set_sensitive(sensitive)
        if hasattr(self, "open_btn") and self.open_btn is not None:
            self.open_btn.set_sensitive(sensitive)

    def _start_transcode(self) -> None:
        if not self.input_file or not self.media_info:
            self.toast_overlay.add_toast(Adw.Toast(title="Please open a media file first."))
            return

        options = self.get_transcode_options()
        out_path = self.video_output_path
        if not out_path:
            out_path = resolve_default_output_path(self.input_file, options.preset or "h264")
            self.video_output_path = out_path

        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            cmds = build_ffmpeg_commands(
                input_path=str(self.input_file),
                output_path=str(out_path),
                options=options,
                media_info=self.media_info,
                include_progress=True,
            )
        except Exception as e:
            self.toast_overlay.add_toast(Adw.Toast(title=f"Configuration error: {e}"))
            return

        self._start_worker(cmds, self.media_info.duration or 0.0, out_path, "Transcoding video...")

    def _start_extract_audio(self) -> None:
        if not self.input_file or not self.media_info:
            self.toast_overlay.add_toast(Adw.Toast(title="Please open a media file first."))
            return

        options = self.get_extract_audio_options()
        out_path = self.audio_output_path
        if not out_path:
            out_path = resolve_default_output_path(self.input_file, options.preset or "mp3", is_extract_audio=True)
            self.audio_output_path = out_path

        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            cmds = build_ffmpeg_commands(
                input_path=str(self.input_file),
                output_path=str(out_path),
                options=options,
                media_info=self.media_info,
                include_progress=True,
            )
        except Exception as e:
            self.toast_overlay.add_toast(Adw.Toast(title=f"Configuration error: {e}"))
            return

        self._start_worker(cmds, self.media_info.duration or 0.0, out_path, "Extracting audio...")

    def _start_worker(
        self,
        cmds: list[list[str]],
        duration: float,
        output_path: Path,
        title: str,
    ) -> None:
        self.cancel_event = threading.Event()
        self.is_transcoding = True
        self._set_ui_controls_sensitive(False)
        if hasattr(self, "open_btn") and self.open_btn is not None:
            self.open_btn.set_sensitive(False)
        self.progress_footer.start(title)

        worker_thread = threading.Thread(
            target=self._worker_thread_entry,
            args=(cmds, duration, output_path, self.cancel_event),
            daemon=True,
            name="MediaToolboxWorker",
        )
        worker_thread.start()

    # Backwards compatibility alias
    _launch_worker_pipeline = _start_worker

    def _worker_thread_entry(
        self,
        cmds: list[list[str]],
        total_duration: float,
        output_path: Path,
        cancel_event: threading.Event,
    ) -> None:
        """Worker thread running FFmpeg pipeline in background without blocking UI thread."""
        try:
            run_ffmpeg_pipeline(
                cmds=cmds,
                total_duration_seconds=total_duration,
                progress_callback=lambda evt: GLib.idle_add(self._on_progress_idle, evt),
                pipeline_progress_callback=lambda p, t, evt: GLib.idle_add(self._on_pass_progress_idle, p, t, evt),
                cancel_event=cancel_event,
            )
            GLib.idle_add(self._on_success_idle, output_path)
        except RunnerCancelledError:
            # Clean up incomplete output file on cancellation
            if output_path.exists():
                try:
                    output_path.unlink()
                except OSError:
                    pass
            GLib.idle_add(self._on_cancelled_idle, output_path)
        except RunnerError as err:
            err_msg = err.last_error_line or str(err)
            GLib.idle_add(self._on_error_idle, err_msg)
        except Exception as exc:
            GLib.idle_add(self._on_error_idle, str(exc))

    def _on_progress_idle(self, event: ProgressEvent) -> bool:
        self.progress_footer.update_progress(event)
        return GLib.SOURCE_REMOVE

    def _on_pass_progress_idle(self, pass_num: int, total_passes: int, event: ProgressEvent) -> bool:
        pass_info = f"Pass {pass_num} of {total_passes} ({event.percentage:.1f}%)" if total_passes > 1 else None
        self.progress_footer.update_progress(event, pass_info=pass_info)
        return GLib.SOURCE_REMOVE

    def _on_success_idle(self, output_path: Path) -> bool:
        self.is_transcoding = False
        self._set_ui_controls_sensitive(True)
        if hasattr(self, "open_btn") and self.open_btn is not None:
            self.open_btn.set_sensitive(True)
        self.progress_footer.finish(True, f"Saved: {output_path.name}")
        self.toast_overlay.add_toast(Adw.Toast(title=f"Completed successfully: {output_path.name}"))
        return GLib.SOURCE_REMOVE

    def _on_cancelled_idle(self, output_path: Path) -> bool:
        self.is_transcoding = False
        self._set_ui_controls_sensitive(True)
        if hasattr(self, "open_btn") and self.open_btn is not None:
            self.open_btn.set_sensitive(True)
        self.progress_footer.finish(False, "Operation cancelled")
        self.toast_overlay.add_toast(Adw.Toast(title="Operation cancelled by user."))
        return GLib.SOURCE_REMOVE

    def _on_error_idle(self, error_message: str) -> bool:
        self.is_transcoding = False
        self._set_ui_controls_sensitive(True)
        if hasattr(self, "open_btn") and self.open_btn is not None:
            self.open_btn.set_sensitive(True)
        self.progress_footer.finish(False, f"Failed: {error_message}")
        self.toast_overlay.add_toast(Adw.Toast(title=f"Encoding failed: {error_message}"))
        return GLib.SOURCE_REMOVE

    def _on_cancel_clicked(self) -> None:
        if self.cancel_event:
            self.cancel_event.set()
        self.progress_footer.set_cancelling()

    def _on_close_request(self, *args: Any) -> bool:
        if self.is_transcoding and self.cancel_event:
            self.cancel_event.set()
        return False
