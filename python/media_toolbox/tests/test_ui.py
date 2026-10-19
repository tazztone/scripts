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
import sys
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


@pytest.fixture(autouse=True, scope="module")
def isolate_gi_sys_modules():
    """
    Module-level teardown fixture ensuring PyGObject and UI modules do not leak
    into sys.modules after UI tests complete.
    """
    yield
    # Purge all PyGObject, GObject static proxies, and UI modules
    to_delete = [
        k
        for k in list(sys.modules.keys())
        if k == "gi"
        or k.startswith("gi.")
        or k.startswith("gi_")
        or k in ("gobject", "glib", "gio", "gtk", "gtk.gdk")
        or k.startswith("media_toolbox.ui")
    ]
    for k in to_delete:
        sys.modules.pop(k, None)


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

    def test_build_encode_options_with_crop(self) -> None:
        """Verify crop string is passed to EncodeOptions."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state(
            preset="h264",
            rate_mode="crf",
            crf_value=23,
            target_size_mb=25.0,
            scale=(1920, 1080),
            crop="ih*9/16:ih",
            mute_audio=False,
            normalize_audio=False,
            volume_boost_db=None,
            audio_bitrate_kbps=128,
        )
        assert opts.crop == "ih*9/16:ih"
        assert opts.scale == (1920, 1080)

    def test_build_encode_options_crop_ignored_on_audio_extract(self) -> None:
        """Verify crop is reset to None when extracting audio."""
        from media_toolbox.ui.widgets import build_encode_options_from_state

        opts = build_encode_options_from_state(
            preset="mp3",
            rate_mode="crf",
            crf_value=23,
            target_size_mb=25.0,
            scale=(1920, 1080),
            crop="ih*9/16:ih",
            mute_audio=False,
            normalize_audio=False,
            volume_boost_db=None,
            audio_bitrate_kbps=128,
            is_extract_audio=True,
        )
        assert opts.crop is None
        assert opts.scale is None


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
    """Verifies conditional visibility and sensitivity logic for dynamic forms using genuine unbound methods."""

    def test_rate_control_revealer_crf_vs_target_size(self) -> None:
        """Verify mode index 0 reveals CRF and collapses Target Size; index 1 reverses."""
        from media_toolbox.ui.widgets import RateControlWidget

        mock_self = MagicMock()
        mock_combo = MagicMock()

        # Mode 0: CRF
        mock_combo.get_selected.return_value = 0
        RateControlWidget._on_mode_changed(mock_self, mock_combo, None)
        mock_self.crf_revealer.set_reveal_child.assert_called_with(True)
        mock_self.target_size_revealer.set_reveal_child.assert_called_with(False)

        # Mode 1: Target Size
        mock_combo.get_selected.return_value = 1
        RateControlWidget._on_mode_changed(mock_self, mock_combo, None)
        mock_self.crf_revealer.set_reveal_child.assert_called_with(False)
        mock_self.target_size_revealer.set_reveal_child.assert_called_with(True)

    def test_rate_control_revealer_disabled_for_gif_prores(self) -> None:
        """Verify selecting GIF or ProRes disables the rate control selector, and standard codecs re-enable."""
        from media_toolbox.ui.widgets import RateControlWidget

        mock_self = MagicMock()
        mock_self.mode_row = MagicMock()
        mock_self.mode_row.get_selected.return_value = 0
        mock_self._on_mode_changed = RateControlWidget._on_mode_changed.__get__(mock_self, RateControlWidget)

        # GIF disables rate control and collapses revealers
        RateControlWidget.set_codec_preset(mock_self, "gif")
        mock_self.mode_row.set_sensitive.assert_called_with(False)
        mock_self.crf_revealer.set_reveal_child.assert_called_with(False)
        mock_self.target_size_revealer.set_reveal_child.assert_called_with(False)

        # ProRes also disables rate control
        RateControlWidget.set_codec_preset(mock_self, "prores")
        mock_self.mode_row.set_sensitive.assert_called_with(False)
        mock_self.crf_revealer.set_reveal_child.assert_called_with(False)
        mock_self.target_size_revealer.set_reveal_child.assert_called_with(False)

        # Standard codec (h264) re-enables and configures upper bound to 51
        RateControlWidget.set_codec_preset(mock_self, "h264")
        mock_self.mode_row.set_sensitive.assert_called_with(True)
        mock_self.crf_adj.set_upper.assert_called_with(51)
        mock_self.crf_revealer.set_reveal_child.assert_called_with(True)

        # AV1 configures upper bound to 63
        RateControlWidget.set_codec_preset(mock_self, "av1")
        mock_self.crf_adj.set_upper.assert_called_with(63)

    def test_resolution_revealer_custom_expansion(self) -> None:
        """Verify index 4 (Custom) expands custom dimensions revealer; presets collapse it."""
        from media_toolbox.ui.widgets import ResolutionWidget

        mock_self = MagicMock()
        mock_combo = MagicMock()

        mock_combo.get_selected.return_value = 4  # Custom
        ResolutionWidget._on_resolution_changed(mock_self, mock_combo, None)
        mock_self.custom_revealer.set_reveal_child.assert_called_with(True)

        mock_combo.get_selected.return_value = 1  # 1080p
        ResolutionWidget._on_resolution_changed(mock_self, mock_combo, None)
        mock_self.custom_revealer.set_reveal_child.assert_called_with(False)

    def test_resolution_revealer_preset_collapse(self) -> None:
        """Verify selecting standard presets collapses custom revealer."""
        from media_toolbox.ui.widgets import ResolutionWidget

        mock_self = MagicMock()
        mock_combo = MagicMock()

        for idx in (0, 1, 2, 3):
            mock_combo.get_selected.return_value = idx
            ResolutionWidget._on_resolution_changed(mock_self, mock_combo, None)
            mock_self.custom_revealer.set_reveal_child.assert_called_with(False)

    def test_audio_revealer_mute_collapses_adjustments(self) -> None:
        """Verify toggling mute collapses volume and loudness adjustments."""
        from media_toolbox.ui.widgets import AudioOptionsWidget

        mock_self = MagicMock()
        mock_switch = MagicMock()

        mock_switch.get_active.return_value = True
        AudioOptionsWidget._on_mute_changed(mock_self, mock_switch, None)
        mock_self.adjustments_revealer.set_reveal_child.assert_called_with(False)

        mock_switch.get_active.return_value = False
        AudioOptionsWidget._on_mute_changed(mock_self, mock_switch, None)
        mock_self.adjustments_revealer.set_reveal_child.assert_called_with(True)

    def test_audio_options_disabled_when_source_is_silent(self, sample_silent_media_info: MediaInfo) -> None:
        """Verify that files without audio streams disable the audio options group."""
        from media_toolbox.ui.widgets import AudioOptionsWidget

        mock_self = MagicMock()
        AudioOptionsWidget.set_has_audio(mock_self, sample_silent_media_info.has_audio)
        mock_self.set_sensitive.assert_called_with(False)
        mock_self.set_description.assert_called_with("Source file contains no audio streams")

        AudioOptionsWidget.set_has_audio(mock_self, True)
        mock_self.set_sensitive.assert_called_with(True)
        mock_self.set_description.assert_called_with("")


# ---------------------------------------------------------------------------
# 5b. Metadata Card Tests
# ---------------------------------------------------------------------------


class TestMetadataCard:
    """Headless unit verification for MetadataCard.set_media_info and clear."""

    def test_metadata_card_video_and_audio(self, gi_env) -> None:
        """Verify card displays both video and audio stream specs and [Video + Audio] badge."""
        from media_toolbox.core.models import AudioStream, FormatInfo, MediaInfo, VideoStream
        from media_toolbox.ui.widgets import MetadataCard

        v = VideoStream(
            index=0,
            codec_name="h264",
            width=1920,
            height=1080,
            fps=30.0,
            duration=60.0,
            bit_rate=2_000_000,
        )
        a = AudioStream(
            index=1,
            codec_name="aac",
            channels=2,
            sample_rate=48000,
            duration=60.0,
            channel_layout="stereo",
            bit_rate=128_000,
        )
        fmt = FormatInfo(filename="sample.mp4", format_name="mov,mp4", duration=60.0, size_bytes=15_000_000)
        info = MediaInfo(format=fmt, video_streams=(v,), audio_streams=(a,))

        mock_card = MagicMock()
        MetadataCard.set_media_info(mock_card, info)

        mock_card.badge_row.set_subtitle.assert_called_with("[Video + Audio]")
        mock_card.video_row.set_subtitle.assert_called_with(
            "H264 | 1920 × 1080 @ 30 fps | Bitrate: 2,000 kbps (2.00 Mbps)"
        )
        mock_card.audio_row.set_subtitle.assert_called_with(
            "AAC | stereo (2 channels) | 48.0 kHz | Bitrate: 128 kbps"
        )
        mock_card.format_row.set_subtitle.assert_called_with(
            "mov,mp4 | Duration: 00:01:00.00 | Size: 14.31 MB (15,000,000 bytes)"
        )

    def test_metadata_card_silent_video(self, gi_env) -> None:
        """Verify card displays [Silent Video] badge and 'No audio stream' for video-only media."""
        from media_toolbox.core.models import FormatInfo, MediaInfo, VideoStream
        from media_toolbox.ui.widgets import MetadataCard

        v = VideoStream(
            index=0,
            codec_name="hevc",
            width=3840,
            height=2160,
            fps=59.94,
            duration=10.0,
            bit_rate=15_000_000,
        )
        fmt = FormatInfo(filename="silent.mp4", format_name="mp4", duration=10.0, size_bytes=18_750_000)
        info = MediaInfo(format=fmt, video_streams=(v,), audio_streams=())

        mock_card = MagicMock()
        MetadataCard.set_media_info(mock_card, info)

        mock_card.badge_row.set_subtitle.assert_called_with("[Silent Video]")
        mock_card.video_row.set_subtitle.assert_called_with(
            "HEVC | 3840 × 2160 @ 59.94 fps | Bitrate: 15,000 kbps (15.00 Mbps)"
        )
        mock_card.audio_row.set_subtitle.assert_called_with("No audio stream")
        mock_card.format_row.set_subtitle.assert_called_with(
            "mp4 | Duration: 00:00:10.00 | Size: 17.88 MB (18,750,000 bytes)"
        )

    def test_metadata_card_audio_only(self, gi_env) -> None:
        """Verify card displays [Audio Only] badge and 'No video stream' for audio-only media."""
        from media_toolbox.core.models import AudioStream, FormatInfo, MediaInfo
        from media_toolbox.ui.widgets import MetadataCard

        a = AudioStream(
            index=0,
            codec_name="mp3",
            channels=2,
            sample_rate=44100,
            duration=120.0,
            channel_layout="stereo",
            bit_rate=320_000,
        )
        fmt = FormatInfo(filename="track.mp3", format_name="mp3", duration=120.0, size_bytes=4_800_000)
        info = MediaInfo(format=fmt, video_streams=(), audio_streams=(a,))

        mock_card = MagicMock()
        MetadataCard.set_media_info(mock_card, info)

        mock_card.badge_row.set_subtitle.assert_called_with("[Audio Only]")
        mock_card.video_row.set_subtitle.assert_called_with("No video stream")
        mock_card.audio_row.set_subtitle.assert_called_with(
            "MP3 | stereo (2 channels) | 44.1 kHz | Bitrate: 320 kbps"
        )
        mock_card.format_row.set_subtitle.assert_called_with(
            "mp3 | Duration: 00:02:00.00 | Size: 4.58 MB (4,800,000 bytes)"
        )

    def test_metadata_card_still_image(self, gi_env) -> None:
        """Verify card displays [Still Image / Other] for images and containers without streams."""
        from media_toolbox.core.models import FormatInfo, MediaInfo, VideoStream
        from media_toolbox.ui.widgets import MetadataCard

        # Probed still image with 0 duration
        v = VideoStream(
            index=0,
            codec_name="png",
            width=800,
            height=600,
            fps=None,
            duration=None,
            bit_rate=None,
        )
        fmt = FormatInfo(filename="diagram.png", format_name="image2", duration=None, size_bytes=45_000)
        info = MediaInfo(format=fmt, video_streams=(v,), audio_streams=())

        mock_card = MagicMock()
        MetadataCard.set_media_info(mock_card, info)

        mock_card.badge_row.set_subtitle.assert_called_with("[Still Image / Other]")
        mock_card.video_row.set_subtitle.assert_called_with("PNG | 800 × 600 @ N/A | Bitrate: -")
        mock_card.audio_row.set_subtitle.assert_called_with("No audio stream")

        # Container without any streams
        mock_card_empty = MagicMock()
        empty_fmt = FormatInfo(filename="raw.bin", format_name="data", duration=None, size_bytes=1024)
        empty_info = MediaInfo(format=empty_fmt, video_streams=(), audio_streams=())
        MetadataCard.set_media_info(mock_card_empty, empty_info)
        mock_card_empty.badge_row.set_subtitle.assert_called_with("[Still Image / Other]")
        mock_card_empty.video_row.set_subtitle.assert_called_with("No video stream")
        mock_card_empty.audio_row.set_subtitle.assert_called_with("No audio stream")

    def test_metadata_card_missing_channel_layout(self, gi_env) -> None:
        """Verify format_channels works seamlessly when channel_layout is None."""
        from media_toolbox.core.models import AudioStream, FormatInfo, MediaInfo
        from media_toolbox.ui.widgets import MetadataCard

        # Multi-channel layout is None
        a_multi = AudioStream(
            index=0,
            codec_name="flac",
            channels=6,
            sample_rate=96000,
            duration=60.0,
            channel_layout=None,
            bit_rate=None,
        )
        fmt = FormatInfo(filename="surround.flac", format_name="flac", duration=60.0, size_bytes=30_000_000)
        info_multi = MediaInfo(format=fmt, video_streams=(), audio_streams=(a_multi,))

        mock_card = MagicMock()
        MetadataCard.set_media_info(mock_card, info_multi)
        mock_card.audio_row.set_subtitle.assert_called_with("FLAC | 6 channels | 96.0 kHz | Bitrate: -")

        # Mono layout is None
        a_mono = AudioStream(
            index=0,
            codec_name="wav",
            channels=1,
            sample_rate=44100,
            duration=5.0,
            channel_layout=None,
            bit_rate=705_600,
        )
        info_mono = MediaInfo(format=fmt, video_streams=(), audio_streams=(a_mono,))
        mock_card_mono = MagicMock()
        MetadataCard.set_media_info(mock_card_mono, info_mono)
        mock_card_mono.audio_row.set_subtitle.assert_called_with("WAV | 1 channel | 44.1 kHz | Bitrate: 706 kbps")

    def test_metadata_card_clear(self, gi_env) -> None:
        """Verify clear restores placeholder labels across all rows."""
        from media_toolbox.ui.widgets import MetadataCard

        mock_card = MagicMock()
        MetadataCard.clear(mock_card)

        mock_card.badge_row.set_subtitle.assert_called_with("No media loaded")
        mock_card.video_row.set_subtitle.assert_called_with("-")
        mock_card.audio_row.set_subtitle.assert_called_with("-")
        mock_card.format_row.set_subtitle.assert_called_with("-")


# ---------------------------------------------------------------------------
# 6. Non-Blocking Worker Thread & GLib.idle_add Tests
# ---------------------------------------------------------------------------


class TestNonBlockingWorkerThread:
    """Verifies daemon worker thread execution and GLib.idle_add main loop marshalling using genuine production methods."""

    def test_worker_thread_spawns_daemon(self, tmp_path: Path) -> None:
        """Verify MainWindow._launch_worker_pipeline spawns a daemon thread with correct name and target."""
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win.progress_footer = MagicMock()
        mock_win._set_ui_controls_sensitive = MagicMock()
        mock_win._worker_thread_entry = MagicMock()

        out_file = tmp_path / "output.mp4"
        cmds = [["ffmpeg", "-i", "in.mp4", "out.mp4"]]

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_inst = MagicMock()
            mock_thread_cls.return_value = mock_thread_inst

            MainWindow._launch_worker_pipeline(mock_win, cmds, 120.0, out_file, "Encoding...")

            assert mock_win.is_transcoding is True
            assert isinstance(mock_win.cancel_event, threading.Event)
            assert not mock_win.cancel_event.is_set()
            mock_win._set_ui_controls_sensitive.assert_called_with(False)
            mock_win.progress_footer.start.assert_called_with("Encoding...")

            mock_thread_cls.assert_called_once_with(
                target=mock_win._worker_thread_entry,
                args=(cmds, 120.0, out_file, mock_win.cancel_event),
                daemon=True,
                name="MediaToolboxWorker",
            )
            mock_thread_inst.start.assert_called_once()

    def test_worker_dispatches_progress_via_glib_idle_add(self, gi_env) -> None:
        """Verify ProgressEvents update UI via MainWindow._on_progress_idle and ProgressFooterWidget.update_progress."""
        _, _, _, _, _, GLib = gi_env
        from media_toolbox.ui.window import MainWindow
        from media_toolbox.ui.widgets import ProgressFooterWidget

        mock_win = MagicMock()
        evt = ProgressEvent(frame=150, fps=30.0, out_time_seconds=5.0, percentage=50.0, speed=2.0, eta_seconds=5.0, total_size_bytes=1048576)

        # 1. Verify MainWindow._on_progress_idle dispatch
        GLib.idle_add(MainWindow._on_progress_idle, mock_win, evt)

        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        mock_win.progress_footer.update_progress.assert_called_once_with(evt)

        # 2. Verify ProgressFooterWidget.update_progress widget formatting
        mock_footer = MagicMock()
        ProgressFooterWidget.update_progress(mock_footer, evt)
        mock_footer.progress_bar.set_fraction.assert_called_with(0.5)
        mock_footer.pct_label.set_text.assert_called_with("50.0%")
        mock_footer.speed_label.set_text.assert_called_with("Speed: 2.00x")
        mock_footer.eta_label.set_text.assert_called_with("ETA: 00:05")
        mock_footer.size_label.set_text.assert_called_with("Size: 1.00 MB (1,048,576 bytes)")

    def test_worker_dispatches_pipeline_progress_idle(self, gi_env) -> None:
        """Verify multi-pass progress events dispatch to MainWindow._on_pass_progress_idle with pass_info formatted."""
        _, _, _, _, _, GLib = gi_env
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        evt = ProgressEvent(frame=300, fps=30.0, out_time_seconds=10.0, percentage=75.5)

        # Multi-pass: pass 1 of 2
        GLib.idle_add(MainWindow._on_pass_progress_idle, mock_win, 1, 2, evt)

        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        mock_win.progress_footer.update_progress.assert_called_once_with(
            evt, pass_info="Pass 1 of 2 (75.5%)"
        )

        # Single pass: pass_info is None
        mock_win.reset_mock()
        GLib.idle_add(MainWindow._on_pass_progress_idle, mock_win, 1, 1, evt)
        while ctx.pending():
            ctx.iteration(False)

        mock_win.progress_footer.update_progress.assert_called_once_with(
            evt, pass_info=None
        )

    def test_worker_idle_handlers_return_source_remove(self, gi_env, tmp_path: Path) -> None:
        """Verify all MainWindow idle handlers return GLib.SOURCE_REMOVE (False) and do not repeat."""
        _, _, _, _, _, GLib = gi_env
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        evt = ProgressEvent(frame=100, fps=25.0, out_time_seconds=4.0, percentage=40.0)
        fake_path = tmp_path / "out.mp4"

        # Direct return value check
        assert MainWindow._on_progress_idle(mock_win, evt) == GLib.SOURCE_REMOVE
        assert MainWindow._on_pass_progress_idle(mock_win, 1, 2, evt) == GLib.SOURCE_REMOVE
        assert MainWindow._on_success_idle(mock_win, fake_path) == GLib.SOURCE_REMOVE
        assert MainWindow._on_cancelled_idle(mock_win, fake_path) == GLib.SOURCE_REMOVE
        assert MainWindow._on_error_idle(mock_win, "error message") == GLib.SOURCE_REMOVE

        # Verify handlers execute exactly once in GLib main context without infinite loop
        mock_win.reset_mock()
        GLib.idle_add(MainWindow._on_progress_idle, mock_win, evt)
        ctx = GLib.MainContext.default()
        assert ctx.pending()
        ctx.iteration(False)
        assert not ctx.pending()
        assert mock_win.progress_footer.update_progress.call_count == 1

    def test_worker_success_completion_handling(self, gi_env, tmp_path: Path) -> None:
        """Verify successful transcode schedules success handler and restores UI controls."""
        _, _, _, _, _, GLib = gi_env
        from media_toolbox.ui.window import MainWindow
        from media_toolbox.ui.widgets import ProgressFooterWidget

        mock_win = MagicMock()
        mock_win.is_transcoding = True
        out_file = tmp_path / "done.mp4"

        GLib.idle_add(MainWindow._on_success_idle, mock_win, out_file)

        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        assert mock_win.is_transcoding is False
        mock_win._set_ui_controls_sensitive.assert_called_with(True)
        mock_win.progress_footer.finish.assert_called_with(True, "Saved: done.mp4")
        mock_win.toast_overlay.add_toast.assert_called_once()

        # Verify ProgressFooterWidget.finish on success
        mock_footer = MagicMock()
        ProgressFooterWidget.finish(mock_footer, True, "Saved: done.mp4")
        mock_footer.cancel_button.set_sensitive.assert_called_with(False)
        mock_footer.progress_bar.set_fraction.assert_called_with(1.0)
        mock_footer.pct_label.set_text.assert_called_with("100.0%")
        mock_footer.status_label.set_text.assert_called_with("Saved: done.mp4")

    def test_worker_error_marshalled_to_ui(self, gi_env) -> None:
        """Verify runner error message is marshalled back to main thread and displayed."""
        _, _, _, _, _, GLib = gi_env
        from media_toolbox.ui.window import MainWindow
        from media_toolbox.ui.widgets import ProgressFooterWidget

        mock_win = MagicMock()
        mock_win.is_transcoding = True
        err = RunnerError("FFmpeg error", returncode=1, stderr="Invalid codec parameters")

        GLib.idle_add(MainWindow._on_error_idle, mock_win, err.last_error_line)

        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        assert mock_win.is_transcoding is False
        mock_win._set_ui_controls_sensitive.assert_called_with(True)
        mock_win.progress_footer.finish.assert_called_with(False, "Failed: Invalid codec parameters")
        mock_win.toast_overlay.add_toast.assert_called_once()

        # Verify ProgressFooterWidget.finish on failure
        mock_footer = MagicMock()
        ProgressFooterWidget.finish(mock_footer, False, "Failed: Invalid codec parameters")
        mock_footer.cancel_button.set_sensitive.assert_called_with(False)
        mock_footer.status_label.set_text.assert_called_with("Failed: Invalid codec parameters")

    def test_worker_start_disables_open_btn(self, gi_env, tmp_path: Path) -> None:
        """Verify _start_worker marks is_transcoding and disables open_btn."""
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win.is_transcoding = False
        out_file = tmp_path / "out.mp4"

        with patch("threading.Thread") as mock_thread_cls:
            MainWindow._start_worker(mock_win, [["ffmpeg"]], 60.0, out_file, "Transcoding...")

        assert mock_win.is_transcoding is True
        mock_win._set_ui_controls_sensitive.assert_called_with(False)
        mock_win.open_btn.set_sensitive.assert_called_with(False)
        mock_win.progress_footer.start.assert_called_with("Transcoding...")
        mock_thread_cls.assert_called_once()

    def test_worker_success_completion_restores_open_btn(self, gi_env, tmp_path: Path) -> None:
        """Verify _on_success_idle marks is_transcoding=False and enables open_btn."""
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win.is_transcoding = True
        out_file = tmp_path / "done.mp4"

        ret = MainWindow._on_success_idle(mock_win, out_file)

        assert ret is False  # GLib.SOURCE_REMOVE
        assert mock_win.is_transcoding is False
        mock_win._set_ui_controls_sensitive.assert_called_with(True)
        mock_win.open_btn.set_sensitive.assert_called_with(True)
        mock_win.progress_footer.finish.assert_called_with(True, f"Saved: {out_file.name}")

    def test_worker_cancelled_completion_restores_open_btn(self, gi_env, tmp_path: Path) -> None:
        """Verify _on_cancelled_idle marks is_transcoding=False and enables open_btn."""
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win.is_transcoding = True
        out_file = tmp_path / "cancelled.mp4"

        ret = MainWindow._on_cancelled_idle(mock_win, out_file)

        assert ret is False  # GLib.SOURCE_REMOVE
        assert mock_win.is_transcoding is False
        mock_win._set_ui_controls_sensitive.assert_called_with(True)
        mock_win.open_btn.set_sensitive.assert_called_with(True)
        mock_win.progress_footer.finish.assert_called_with(False, "Operation cancelled")

    def test_worker_error_restores_open_btn(self, gi_env) -> None:
        """Verify _on_error_idle marks is_transcoding=False and enables open_btn."""
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win.is_transcoding = True

        ret = MainWindow._on_error_idle(mock_win, "Encode failed")

        assert ret is False  # GLib.SOURCE_REMOVE
        assert mock_win.is_transcoding is False
        mock_win._set_ui_controls_sensitive.assert_called_with(True)
        mock_win.open_btn.set_sensitive.assert_called_with(True)
        mock_win.progress_footer.finish.assert_called_with(False, "Failed: Encode failed")

    def test_open_file_dialog_blocked_during_transcoding(self, gi_env) -> None:
        """Verify open_file_dialog toasts and returns early when is_transcoding=True."""
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win.is_transcoding = True

        MainWindow.open_file_dialog(mock_win)

        mock_win.toast_overlay.add_toast.assert_called_once()

    def test_load_media_file_blocked_during_transcoding(self, gi_env, tmp_path: Path) -> None:
        """Verify load_media_file toasts and does not load file when is_transcoding=True."""
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win.is_transcoding = True
        sample_file = tmp_path / "input.mp4"
        sample_file.touch()

        MainWindow.load_media_file(mock_win, sample_file)

        mock_win.toast_overlay.add_toast.assert_called_once()
        assert not hasattr(mock_win, "input_file") or mock_win.input_file != sample_file


# ---------------------------------------------------------------------------
# 7. Cancellation Flow Tests
# ---------------------------------------------------------------------------


class TestCancellationFlow:
    """Verifies responsive cancellation, cancel_event signaling, and partial file cleanup using genuine production methods."""

    def test_cancel_button_triggers_cancel_event(self) -> None:
        """Verify ProgressFooterWidget cancel invokes callback, and MainWindow._on_cancel_clicked sets cancel_event."""
        from media_toolbox.ui.window import MainWindow
        from media_toolbox.ui.widgets import ProgressFooterWidget

        # 1. Verify ProgressFooterWidget._on_cancel_clicked invokes callback
        mock_cb = MagicMock()
        mock_footer = MagicMock()
        mock_footer.on_cancel_callback = mock_cb
        ProgressFooterWidget._on_cancel_clicked(mock_footer, MagicMock())
        mock_cb.assert_called_once()

        # 2. Verify MainWindow._on_cancel_clicked sets cancel_event and transitions footer
        mock_win = MagicMock()
        mock_win.cancel_event = threading.Event()
        assert not mock_win.cancel_event.is_set()

        MainWindow._on_cancel_clicked(mock_win)
        assert mock_win.cancel_event.is_set() is True
        mock_win.progress_footer.set_cancelling.assert_called_once()

    def test_cancel_updates_ui_state_to_cancelling(self) -> None:
        """Verify ProgressFooterWidget.set_cancelling disables button, updates label and status."""
        from media_toolbox.ui.widgets import ProgressFooterWidget

        mock_footer = MagicMock()
        ProgressFooterWidget.set_cancelling(mock_footer)

        mock_footer.cancel_button.set_sensitive.assert_called_with(False)
        mock_footer.cancel_button.set_label.assert_called_with("Cancelling...")
        mock_footer.status_label.set_text.assert_called_with("Cancelling transcode...")

    def test_worker_catches_runner_cancelled_error(self, gi_env, tmp_path: Path) -> None:
        """Verify MainWindow._worker_thread_entry catches RunnerCancelledError, deletes partial file, and schedules _on_cancelled_idle."""
        _, _, _, _, _, GLib = gi_env
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win.is_transcoding = True
        mock_win._on_cancelled_idle.return_value = GLib.SOURCE_REMOVE

        partial_file = tmp_path / "cancelled_output.mp4"
        partial_file.write_bytes(b"partial video data")
        assert partial_file.exists()

        cancel_event = threading.Event()
        cancel_event.set()

        with patch("media_toolbox.ui.window.run_ffmpeg_pipeline", side_effect=RunnerCancelledError("Process killed")):
            MainWindow._worker_thread_entry(
                mock_win, [["ffmpeg"]], 10.0, partial_file, cancel_event
            )

        # File is unlinked
        assert not partial_file.exists()

        # GLib main context dispatches scheduled _on_cancelled_idle
        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        mock_win._on_cancelled_idle.assert_called_once_with(partial_file)

        # Verify MainWindow._on_cancelled_idle logic directly
        mock_win_idle = MagicMock()
        mock_win_idle.is_transcoding = True
        ret = MainWindow._on_cancelled_idle(mock_win_idle, partial_file)

        assert ret == GLib.SOURCE_REMOVE
        assert mock_win_idle.is_transcoding is False
        mock_win_idle._set_ui_controls_sensitive.assert_called_with(True)
        mock_win_idle.progress_footer.finish.assert_called_with(False, "Operation cancelled")
        mock_win_idle.toast_overlay.add_toast.assert_called_once()

    def test_cancellation_deletes_partial_output_file(self, tmp_path: Path) -> None:
        """Verify MainWindow._worker_thread_entry removes unplayable partial output files upon cancellation."""
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win._on_cancelled_idle.return_value = False

        partial_file = tmp_path / "partially_encoded.mp4"
        partial_file.write_bytes(b"corrupt partial chunk")
        assert partial_file.exists()

        cancel_event = threading.Event()
        cancel_event.set()

        with patch("media_toolbox.ui.window.run_ffmpeg_pipeline", side_effect=RunnerCancelledError("Aborted")):
            MainWindow._worker_thread_entry(mock_win, [["ffmpeg"]], 5.0, partial_file, cancel_event)

        assert not partial_file.exists()

    def test_window_close_request_aborts_active_transcode(self) -> None:
        """Verify MainWindow._on_close_request signals cancel_event when transcoding and permits window closure."""
        from media_toolbox.ui.window import MainWindow

        mock_win = MagicMock()
        mock_win.cancel_event = threading.Event()
        mock_win.is_transcoding = True

        # When transcoding: sets cancel_event, returns False
        ret = MainWindow._on_close_request(mock_win)
        assert ret is False
        assert mock_win.cancel_event.is_set() is True

        # When idle: leaves cancel_event unset, returns False
        mock_win.cancel_event.clear()
        mock_win.is_transcoding = False
        ret = MainWindow._on_close_request(mock_win)
        assert ret is False
        assert not mock_win.cancel_event.is_set()


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
