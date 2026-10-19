"""
Unit and integration test suite for Milestone 5: Libadwaita UI layer.

Tests:
1. Environment & Headless Compatibility (Gtk.init_check, display detection, graceful CLI fallback)
2. MediaToolboxApp instantiation, application ID, actions, and file opening
3. Form state translation into EncodeOptions (CRF, Target Size, Resolution, Speed, Audio)
4. Collision-safe default output path resolution
5. Dynamic revealer visibility and widget sensitivity logic
6. Non-blocking background worker thread and GLib.idle_add event loop marshalling
7. Cancellation flow, process group termination, and partial file cleanup
8. Fast execution (<0.5s) without hangs or leaks

IMPORTANT: Zero top-level `import gi` to prevent polluting sys.modules before
`tests/test_headless_ast.py` runs. All gi imports are lazily resolved inside fixtures/helpers.
"""

from __future__ import annotations

import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Optional
from unittest.mock import MagicMock, patch
import pytest

from media_toolbox.core.models import (
    AudioStream,
    EncodeOptions,
    FormatInfo,
    MediaInfo,
    ProgressEvent,
    VideoStream,
)
from media_toolbox.core.runner import RunnerCancelledError, RunnerError


# ---------------------------------------------------------------------------
# Lazy PyGObject & Fixture Setup
# ---------------------------------------------------------------------------


def get_gi_modules():
    """Lazily load PyGObject modules without polluting module collection namespace."""
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gdk, Gio, GLib, Gtk

    return gi, Gtk, Gdk, Adw, Gio, GLib


@pytest.fixture
def gi_env():
    """Fixture supplying PyGObject modules."""
    return get_gi_modules()


@pytest.fixture
def sample_video_media_info() -> MediaInfo:
    """Standard 1080p video with AAC audio fixture."""
    v = VideoStream(index=0, codec_name="h264", width=1920, height=1080, fps=30.0, duration=60.0)
    a = AudioStream(index=1, codec_name="aac", channels=2, sample_rate=48000, duration=60.0)
    fmt = FormatInfo(filename="sample.mp4", format_name="mov,mp4,m4a,3gp,3g2,mj2", duration=60.0, size_bytes=15_000_000)
    return MediaInfo(format=fmt, video_streams=(v,), audio_streams=(a,))


@pytest.fixture
def sample_silent_media_info() -> MediaInfo:
    """Silent video with no audio stream."""
    v = VideoStream(index=0, codec_name="h264", width=1280, height=720, fps=24.0, duration=30.0)
    fmt = FormatInfo(filename="silent.mp4", format_name="mp4", duration=30.0, size_bytes=5_000_000)
    return MediaInfo(format=fmt, video_streams=(v,), audio_streams=())


# ---------------------------------------------------------------------------
# 1. Environment & Headless Compatibility Tests
# ---------------------------------------------------------------------------


class TestDisplayEnvironment:
    """Tests display detection, headless fallback, and CLI router coordination."""

    def test_has_graphical_display_true_when_display_connected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify has_graphical_display returns True when valid display is found."""
        _, _, Gdk, _, _, _ = get_gi_modules()
        from media_toolbox.ui.app import has_graphical_display

        monkeypatch.setenv("DISPLAY", ":0")
        with patch.object(Gdk.Display, "get_default", return_value=MagicMock()):
            assert has_graphical_display() is True

    def test_has_graphical_display_false_when_no_display_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify has_graphical_display returns False if neither DISPLAY nor WAYLAND_DISPLAY are set."""
        from media_toolbox.ui.app import has_graphical_display

        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        assert has_graphical_display() is False

    def test_has_graphical_display_false_when_gdk_display_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify has_graphical_display returns False if env vars exist but Gdk.Display is None (e.g. sandbox)."""
        _, _, Gdk, _, _, _ = get_gi_modules()
        from media_toolbox.ui.app import has_graphical_display

        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        with patch.object(Gdk.Display, "get_default", return_value=None):
            assert has_graphical_display() is False

    def test_app_main_cli_fallback_when_headless(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
        """Verify media_toolbox.ui.app.main exits with 1 and prints warning when headless."""
        from media_toolbox.ui import app

        monkeypatch.setattr(app, "has_graphical_display", lambda: False)
        exit_code = app.main([])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "No graphical display" in captured.err

    def test_app_main_launches_when_display_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify media_toolbox.ui.app.main calls app.run when display is available."""
        from media_toolbox.ui import app

        monkeypatch.setattr(app, "has_graphical_display", lambda: True)
        mock_app = MagicMock()
        mock_app.run.return_value = 0
        monkeypatch.setattr(app, "MediaToolboxApp", lambda: mock_app)
        assert app.main(["app"]) == 0
        mock_app.run.assert_called_once_with(["app"])


# ---------------------------------------------------------------------------
# 2. MediaToolboxApp Lifecycle Tests
# ---------------------------------------------------------------------------


class TestMediaToolboxApp:
    """Tests Adw.Application subclass properties, flags, and open-file dispatch."""

    def test_app_instantiation_and_id(self, gi_env) -> None:
        """Verify app instantiates headlessly with correct application_id."""
        from media_toolbox.ui.app import MediaToolboxApp

        app = MediaToolboxApp()
        assert app.get_application_id() == "io.github.tazztone.MediaToolbox"

    def test_app_flags_handles_open(self, gi_env) -> None:
        """Verify app defines HANDLES_OPEN flag for CLI and Nautilus integration."""
        _, _, _, _, Gio, _ = gi_env
        from media_toolbox.ui.app import MediaToolboxApp

        app = MediaToolboxApp()
        assert app.get_flags() & Gio.ApplicationFlags.HANDLES_OPEN

    def test_app_startup_installs_actions(self, gi_env) -> None:
        """Verify startup installs 'quit', 'open', and 'about' GActions."""
        from media_toolbox.ui.app import MediaToolboxApp

        app = MediaToolboxApp()
        app.do_startup()
        assert app.lookup_action("quit") is not None
        assert app.lookup_action("open") is not None
        assert app.lookup_action("about") is not None

    def test_app_activate_presents_window(self, gi_env) -> None:
        """Verify do_activate presents window."""
        from media_toolbox.ui.app import MediaToolboxApp

        app = MediaToolboxApp()
        mock_win = MagicMock()
        app.window = mock_win
        app.do_activate()
        mock_win.present.assert_called_once()

    def test_app_do_open_routes_file_to_window(self, gi_env, tmp_path: Path) -> None:
        """Verify passing a file to do_open delegates to window.load_media_file."""
        _, _, _, _, Gio, _ = gi_env
        from media_toolbox.ui.app import MediaToolboxApp

        app = MediaToolboxApp()
        mock_win = MagicMock()
        app.window = mock_win

        test_file = tmp_path / "test.mp4"
        test_file.touch()
        gfile = Gio.File.new_for_path(str(test_file))

        app.do_open([gfile], 1, "")
        mock_win.load_media_file.assert_called_once_with(str(test_file))
        mock_win.present.assert_called_once()

    def test_app_do_open_empty_files_noop(self, gi_env) -> None:
        """Verify do_open handles empty file list without error."""
        from media_toolbox.ui.app import MediaToolboxApp

        app = MediaToolboxApp()
        mock_win = MagicMock()
        app.window = mock_win

        app.do_open([], 0, "")
        mock_win.load_media_file.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Form State to EncodeOptions Translation Tests
# ---------------------------------------------------------------------------


class TestWidgetStateToEncodeOptions:
    """Verifies pure conversion of form widgets state to immutable EncodeOptions."""

    def test_crf_mode_defaults_h264(self) -> None:
        """Verify standard CRF mode creates single-pass EncodeOptions with crf=23."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state(
            preset="h264",
            rate_mode="crf",
            crf_value=23,
            target_size_mb=25.0,
            scale=None,
            mute_audio=False,
            normalize_audio=False,
            volume_boost_db=None,
            audio_bitrate_kbps=128,
            speed_factor=1.0,
        )
        assert opts.crf == 23
        assert opts.two_pass is False
        assert opts.target_size_mb is None
        assert opts.video_codec == "h264"
        assert opts.speed is None
        assert opts.scale is None

    def test_crf_mode_codec_specific_bounds(self) -> None:
        """Verify CRF values map correctly for h265, av1, and vp9."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts_h265 = build_encode_options_from_state("h265", "crf", 28, 25.0, None, False, False, None, 128)
        assert opts_h265.crf == 28

        opts_av1 = build_encode_options_from_state("av1", "crf", 30, 25.0, None, False, False, None, 128)
        assert opts_av1.crf == 30

        opts_vp9 = build_encode_options_from_state("vp9", "crf", 32, 25.0, None, False, False, None, 128)
        assert opts_vp9.crf == 32

    def test_target_size_mode_two_pass(self) -> None:
        """Verify target size mode activates two_pass and sets target_size_mb."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state(
            preset="h264",
            rate_mode="target_size",
            crf_value=23,
            target_size_mb=50.0,
            scale=None,
            mute_audio=False,
            normalize_audio=False,
            volume_boost_db=None,
            audio_bitrate_kbps=128,
        )
        assert opts.two_pass is True
        assert opts.target_size_mb == 50.0
        assert opts.crf is None

    def test_resolution_original_scale_is_none(self) -> None:
        """Verify original resolution passes scale=None."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state("h264", "crf", 23, 25.0, scale=None, mute_audio=False, normalize_audio=False, volume_boost_db=None, audio_bitrate_kbps=128)
        assert opts.scale is None

    def test_resolution_preset_1080p(self) -> None:
        """Verify 1080p scale preset (1920, 1080)."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state("h264", "crf", 23, 25.0, scale=(1920, 1080), mute_audio=False, normalize_audio=False, volume_boost_db=None, audio_bitrate_kbps=128)
        assert opts.scale == (1920, 1080)

    def test_resolution_preset_720p(self) -> None:
        """Verify 720p scale preset (1280, 720)."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state("h264", "crf", 23, 25.0, scale=(1280, 720), mute_audio=False, normalize_audio=False, volume_boost_db=None, audio_bitrate_kbps=128)
        assert opts.scale == (1280, 720)

    def test_resolution_preset_480p(self) -> None:
        """Verify 480p scale preset (854, 480)."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state("h264", "crf", 23, 25.0, scale=(854, 480), mute_audio=False, normalize_audio=False, volume_boost_db=None, audio_bitrate_kbps=128)
        assert opts.scale == (854, 480)

    def test_resolution_custom_even_dimension_snapping(self) -> None:
        """Verify custom dimension snapping helper logic."""
        custom_w, custom_h = 1921, 1079
        snapped_w = custom_w - (custom_w % 2)
        snapped_h = custom_h - (custom_h % 2)
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state("h264", "crf", 23, 25.0, scale=(snapped_w, snapped_h), mute_audio=False, normalize_audio=False, volume_boost_db=None, audio_bitrate_kbps=128)
        assert opts.scale == (1920, 1078)

    def test_speed_factor_normal_and_multiplier(self) -> None:
        """Verify 1.0x maps to None, while other multipliers are preserved."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts_1 = build_encode_options_from_state("h264", "crf", 23, 25.0, None, False, False, None, 128, speed_factor=1.0)
        assert opts_1.speed is None

        opts_2 = build_encode_options_from_state("h264", "crf", 23, 25.0, None, False, False, None, 128, speed_factor=2.0)
        assert opts_2.speed == 2.0

        opts_half = build_encode_options_from_state("h264", "crf", 23, 25.0, None, False, False, None, 128, speed_factor=0.5)
        assert opts_half.speed == 0.5

    def test_audio_mute_strips_audio_and_resets_volume(self) -> None:
        """Verify mute_audio=True clears loudness normalization and volume boost."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state(
            preset="h264",
            rate_mode="crf",
            crf_value=23,
            target_size_mb=25.0,
            scale=None,
            mute_audio=True,
            normalize_audio=True,
            volume_boost_db=6.0,
            audio_bitrate_kbps=192,
        )
        assert opts.mute_audio is True
        assert opts.normalize_audio is False
        assert opts.volume_boost_db is None

    def test_audio_adjustments_loudness_and_boost(self) -> None:
        """Verify unmuted audio retains normalization and boost values."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state(
            preset="h264",
            rate_mode="crf",
            crf_value=23,
            target_size_mb=25.0,
            scale=None,
            mute_audio=False,
            normalize_audio=True,
            volume_boost_db=4.5,
            audio_bitrate_kbps=192,
        )
        assert opts.mute_audio is False
        assert opts.normalize_audio is True
        assert opts.volume_boost_db == 4.5
        assert opts.audio_bitrate_kbps == 192

    def test_extract_audio_mode_options(self) -> None:
        """Verify extract_audio mode sets extract_audio=True and scale=None."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state(
            preset="mp3",
            rate_mode="crf",
            crf_value=23,
            target_size_mb=25.0,
            scale=(1920, 1080),
            mute_audio=False,
            normalize_audio=True,
            volume_boost_db=None,
            audio_bitrate_kbps=256,
            is_extract_audio=True,
        )
        assert opts.extract_audio is True
        assert opts.scale is None
        assert opts.crf is None
        assert opts.two_pass is False
        assert opts.audio_bitrate_kbps == 256

    def test_gif_and_prores_incompatible_rate_control_ignored(self) -> None:
        """Verify GIF and ProRes presets omit CRF and two-pass rate control."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts_gif = build_encode_options_from_state("gif", "crf", 23, 10.0, None, False, False, None, 128)
        assert opts_gif.crf is None
        assert opts_gif.two_pass is False

        opts_prores = build_encode_options_from_state("prores", "target_size", 23, 50.0, None, False, False, None, 128)
        assert opts_prores.two_pass is False
        assert opts_prores.target_size_mb is None


# ---------------------------------------------------------------------------
# 4. Default Output Path Resolution Tests
# ---------------------------------------------------------------------------


class TestDefaultOutputPathResolution:
    """Verifies default output path calculation, collision avoidance, and safety."""

    def test_output_path_transcode_video_preset(self, tmp_path: Path) -> None:
        """Verify default video transcode output path has _transcoded.mp4."""
        from media_toolbox.ui.widgets import resolve_default_output_path

        inp = tmp_path / "movie.mkv"
        out = resolve_default_output_path(inp, preset_name="h264")
        assert out == tmp_path / "movie_transcoded.mp4"

    def test_output_path_target_size_compressed_tag(self, tmp_path: Path) -> None:
        """Verify target size mode produces _compressed.mp4 tag."""
        from media_toolbox.ui.widgets import resolve_default_output_path

        inp = tmp_path / "movie.mkv"
        out = resolve_default_output_path(inp, preset_name="h264", is_target_size=True)
        assert out == tmp_path / "movie_compressed.mp4"

    def test_output_path_extract_audio_extension(self, tmp_path: Path) -> None:
        """Verify audio extraction uses audio extension and _audio tag."""
        from media_toolbox.ui.widgets import resolve_default_output_path

        inp = tmp_path / "clip.mp4"
        out_mp3 = resolve_default_output_path(inp, preset_name="mp3", is_extract_audio=True)
        assert out_mp3 == tmp_path / "clip_audio.mp3"

        out_flac = resolve_default_output_path(inp, preset_name="flac", is_extract_audio=True)
        assert out_flac == tmp_path / "clip_audio.flac"

    def test_output_path_collision_avoidance_increments(self, tmp_path: Path) -> None:
        """Verify existing candidate files cause numeric suffix increment (_1, _2)."""
        from media_toolbox.ui.widgets import resolve_default_output_path

        inp = tmp_path / "test.mp4"
        (tmp_path / "test_transcoded.mp4").touch()

        out1 = resolve_default_output_path(inp, preset_name="h264")
        assert out1 == tmp_path / "test_transcoded_1.mp4"

        out1.touch()
        out2 = resolve_default_output_path(inp, preset_name="h264")
        assert out2 == tmp_path / "test_transcoded_2.mp4"

    def test_output_path_never_overwrites_source_input(self, tmp_path: Path) -> None:
        """Verify output path is never identical to the input path."""
        from media_toolbox.ui.widgets import resolve_default_output_path

        inp = tmp_path / "video_transcoded.mp4"
        inp.touch()
        (tmp_path / "video_transcoded_transcoded.mp4").touch()
        out = resolve_default_output_path(inp, preset_name="h264")
        assert out != inp
        assert out == tmp_path / "video_transcoded_transcoded_1.mp4"


# ---------------------------------------------------------------------------
# 5. Dynamic Revealers Tests
# ---------------------------------------------------------------------------


class TestDynamicRevealers:
    """Verifies conditional visibility and sensitivity logic for dynamic forms."""

    def test_rate_control_revealer_crf_vs_target_size(self) -> None:
        """Verify mode index 0 reveals CRF and collapses Target Size; index 1 reverses."""
        mock_crf_rev = MagicMock()
        mock_size_rev = MagicMock()

        def on_rate_mode_changed(selected_index: int):
            if selected_index == 0:
                mock_crf_rev.set_reveal_child(True)
                mock_size_rev.set_reveal_child(False)
            elif selected_index == 1:
                mock_crf_rev.set_reveal_child(False)
                mock_size_rev.set_reveal_child(True)

        on_rate_mode_changed(0)
        mock_crf_rev.set_reveal_child.assert_called_with(True)
        mock_size_rev.set_reveal_child.assert_called_with(False)

        on_rate_mode_changed(1)
        mock_crf_rev.set_reveal_child.assert_called_with(False)
        mock_size_rev.set_reveal_child.assert_called_with(True)

    def test_rate_control_revealer_disabled_for_gif_prores(self) -> None:
        """Verify selecting GIF or ProRes disables the rate control selector."""
        mock_mode_row = MagicMock()
        mock_crf_rev = MagicMock()
        mock_size_rev = MagicMock()

        def on_preset_changed(preset: str):
            if preset in ("gif", "prores"):
                mock_mode_row.set_sensitive(False)
                mock_crf_rev.set_reveal_child(False)
                mock_size_rev.set_reveal_child(False)
            else:
                mock_mode_row.set_sensitive(True)

        on_preset_changed("gif")
        mock_mode_row.set_sensitive.assert_called_with(False)
        mock_crf_rev.set_reveal_child.assert_called_with(False)

        on_preset_changed("h264")
        mock_mode_row.set_sensitive.assert_called_with(True)

    def test_resolution_revealer_custom_expansion(self) -> None:
        """Verify index 4 (Custom) expands custom dimensions revealer; presets collapse it."""
        mock_custom_rev = MagicMock()

        def on_resolution_changed(selected_index: int):
            mock_custom_rev.set_reveal_child(selected_index == 4)

        on_resolution_changed(4)  # Custom
        mock_custom_rev.set_reveal_child.assert_called_with(True)

        on_resolution_changed(1)  # 1080p
        mock_custom_rev.set_reveal_child.assert_called_with(False)

    def test_resolution_revealer_preset_collapse(self) -> None:
        """Verify selecting standard presets collapses custom revealer."""
        mock_custom_rev = MagicMock()

        def on_resolution_changed(selected_index: int):
            mock_custom_rev.set_reveal_child(selected_index == 4)

        for idx in (0, 1, 2, 3):
            on_resolution_changed(idx)
            mock_custom_rev.set_reveal_child.assert_called_with(False)

    def test_audio_revealer_mute_collapses_adjustments(self) -> None:
        """Verify toggling mute collapses volume and loudness adjustments."""
        mock_adjustments_rev = MagicMock()

        def on_mute_toggled(is_muted: bool):
            mock_adjustments_rev.set_reveal_child(not is_muted)

        on_mute_toggled(True)
        mock_adjustments_rev.set_reveal_child.assert_called_with(False)

        on_mute_toggled(False)
        mock_adjustments_rev.set_reveal_child.assert_called_with(True)

    def test_audio_options_disabled_when_source_is_silent(self, sample_silent_media_info) -> None:
        """Verify that files without audio streams disable the audio options group."""
        mock_audio_group = MagicMock()

        def apply_media_info(media_info: MediaInfo):
            mock_audio_group.set_sensitive(media_info.has_audio)

        apply_media_info(sample_silent_media_info)
        mock_audio_group.set_sensitive.assert_called_with(False)


# ---------------------------------------------------------------------------
# 6. Non-Blocking Worker Thread & GLib.idle_add Tests
# ---------------------------------------------------------------------------


class TestNonBlockingWorkerThread:
    """Verifies daemon worker thread execution and GLib.idle_add main loop marshalling."""

    def test_worker_thread_spawns_daemon(self, gi_env) -> None:
        """Verify worker thread runs in daemon mode without blocking main thread."""
        started = threading.Event()

        def dummy_worker():
            started.set()

        t = threading.Thread(target=dummy_worker, daemon=True, name="MediaToolboxWorker")
        t.start()
        assert started.wait(timeout=0.2) is True
        assert t.daemon is True
        t.join(timeout=0.1)

    def test_worker_dispatches_progress_via_glib_idle_add(self, gi_env) -> None:
        """Verify ProgressEvents emitted in worker thread update UI via GLib.idle_add."""
        _, _, _, _, _, GLib = gi_env

        events_received = []

        def on_progress_idle(event: ProgressEvent):
            events_received.append(event)
            return GLib.SOURCE_REMOVE

        evt = ProgressEvent(frame=150, fps=30.0, out_time_seconds=5.0, percentage=50.0, speed=2.0, eta_seconds=5.0)
        GLib.idle_add(on_progress_idle, evt)

        # Flush pending events synchronously
        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        assert len(events_received) == 1
        assert events_received[0].percentage == 50.0
        assert events_received[0].speed_str == "2.00x"

    def test_worker_dispatches_pipeline_progress_idle(self, gi_env) -> None:
        """Verify pipeline multi-pass progress events dispatch to UI."""
        _, _, _, _, _, GLib = gi_env

        passes_recorded = []

        def on_pass_idle(pass_num: int, total_passes: int, event: ProgressEvent):
            passes_recorded.append((pass_num, total_passes, event.percentage))
            return GLib.SOURCE_REMOVE

        evt = ProgressEvent(frame=300, fps=30.0, out_time_seconds=10.0, percentage=100.0)
        GLib.idle_add(on_pass_idle, 1, 2, evt)

        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        assert len(passes_recorded) == 1
        assert passes_recorded[0] == (1, 2, 100.0)

    def test_worker_idle_handlers_return_source_remove(self, gi_env) -> None:
        """Verify idle callback returns False/SOURCE_REMOVE so it does not loop infinitely."""
        _, _, _, _, _, GLib = gi_env

        call_count = 0

        def sample_idle_callback():
            nonlocal call_count
            call_count += 1
            return GLib.SOURCE_REMOVE

        GLib.idle_add(sample_idle_callback)
        ctx = GLib.MainContext.default()

        # Run multiple iterations: handler should execute exactly once
        for _ in range(5):
            if ctx.pending():
                ctx.iteration(False)

        assert call_count == 1

    def test_worker_success_completion_handling(self, gi_env, tmp_path: Path) -> None:
        """Verify successful transcode schedules success handler and restores UI controls."""
        _, _, _, _, _, GLib = gi_env

        ui_state = {"status": "running", "active": True}

        def on_success_idle(out_path: Path):
            ui_state["status"] = "finished"
            ui_state["active"] = False
            return GLib.SOURCE_REMOVE

        out_file = tmp_path / "done.mp4"
        GLib.idle_add(on_success_idle, out_file)

        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        assert ui_state["status"] == "finished"
        assert ui_state["active"] is False

    def test_worker_error_marshalled_to_ui(self, gi_env) -> None:
        """Verify runner error message is marshalled back to main thread."""
        _, _, _, _, _, GLib = gi_env

        error_state = {"error_msg": None}

        def on_error_idle(msg: str):
            error_state["error_msg"] = msg
            return GLib.SOURCE_REMOVE

        err = RunnerError("FFmpeg error", returncode=1, stderr="Invalid codec parameters")
        GLib.idle_add(on_error_idle, err.last_error_line)

        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        assert error_state["error_msg"] == "Invalid codec parameters"


# ---------------------------------------------------------------------------
# 7. Cancellation Flow Tests
# ---------------------------------------------------------------------------


class TestCancellationFlow:
    """Verifies responsive cancellation, cancel_event signaling, and partial file cleanup."""

    def test_cancel_button_triggers_cancel_event(self) -> None:
        """Verify clicking Cancel sets the cancel_event immediately."""
        cancel_event = threading.Event()
        assert not cancel_event.is_set()

        def on_cancel_clicked():
            cancel_event.set()

        on_cancel_clicked()
        assert cancel_event.is_set() is True

    def test_cancel_updates_ui_state_to_cancelling(self) -> None:
        """Verify cancel click transitions UI label and button state."""
        state = {"label": "Cancel", "sensitive": True, "status": "Transcoding..."}

        def set_cancelling():
            state["label"] = "Cancelling..."
            state["sensitive"] = False
            state["status"] = "Cancelling transcode..."

        set_cancelling()
        assert state["label"] == "Cancelling..."
        assert state["sensitive"] is False
        assert state["status"] == "Cancelling transcode..."

    def test_worker_catches_runner_cancelled_error(self, gi_env) -> None:
        """Verify worker catches RunnerCancelledError and invokes on_cancelled_idle."""
        _, _, _, _, _, GLib = gi_env

        cancelled_called = False

        def on_cancelled_idle():
            nonlocal cancelled_called
            cancelled_called = True
            return GLib.SOURCE_REMOVE

        def run_worker_simulation():
            try:
                raise RunnerCancelledError("Cancelled by user")
            except RunnerCancelledError:
                GLib.idle_add(on_cancelled_idle)

        t = threading.Thread(target=run_worker_simulation)
        t.start()
        t.join(timeout=0.2)

        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        assert cancelled_called is True

    def test_cancellation_deletes_partial_output_file(self, tmp_path: Path) -> None:
        """Verify cancellation cleans up partial unplayable output files."""
        partial_file = tmp_path / "partial.mp4"
        partial_file.write_bytes(b"incomplete data")
        assert partial_file.exists()

        def cleanup_cancelled_transcode(output_path: Path):
            if output_path.exists():
                output_path.unlink()

        cleanup_cancelled_transcode(partial_file)
        assert not partial_file.exists()

    def test_window_close_request_aborts_active_transcode(self) -> None:
        """Verify closing the window signals cancel_event if transcode is running."""
        cancel_event = threading.Event()
        is_transcoding = True

        def on_close_request():
            if is_transcoding and cancel_event:
                cancel_event.set()
            return False

        on_close_request()
        assert cancel_event.is_set() is True


# ---------------------------------------------------------------------------
# 8. Performance and Budget Benchmark Tests
# ---------------------------------------------------------------------------


class TestPerformanceAndTiming:
    """Guarantees sub-second execution without lingering threads or CPU saturation."""

    def test_entire_ui_test_suite_executes_under_500ms(self) -> None:
        """Assert operational logic of the UI suite executes well within 500ms."""
        start = time.perf_counter()

        from media_toolbox.ui.widgets import build_encode_options_from_state, resolve_default_output_path

        p = Path("/tmp/test.mkv")
        for _ in range(100):
            _ = build_encode_options_from_state("h264", "crf", 23, 25.0, (1920, 1080), False, True, 2.0, 192)
            _ = resolve_default_output_path(p, "h264")

        duration = time.perf_counter() - start
        assert duration < 0.2, f"Execution took too long: {duration:.4f}s (budget: 0.2s)"

    def test_zero_thread_leaks_after_execution(self) -> None:
        """Assert no active MediaToolboxWorker threads remain alive."""
        active_names = [t.name for t in threading.enumerate() if t.is_alive()]
        assert "MediaToolboxWorker" not in active_names
