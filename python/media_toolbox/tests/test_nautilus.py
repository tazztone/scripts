"""
Unit and integration test suite for Milestone 6: Nautilus Desktop Integration.

Tests:
1. Launcher Script Testing (bash -n syntax, selected file paths, CLI args, zero-arg exit).
2. Headless Extension Testing (mocked Nautilus 4.1 MenuProvider, MIME/ext filtering, subprocess dispatch).
3. Installer Testing (install_nautilus, permissions 0o755/0o644, desktop ini, idempotence, uninstall, status).
4. CLI Subcommand Testing (media_toolbox install-nautilus --dry-run, uninstall-nautilus --dry-run, --dest-dir).
5. AST & Module Invariants (zero module-scope gi imports, zero GUI imports in installer.py, fast execution).

INVARIANT: Strict zero module-scope `import gi` or `import Nautilus`.
All PyGObject / Nautilus mocking is scoped inside fixtures or local helpers.
"""

from __future__ import annotations

import ast
import configparser
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import types
from typing import Any, Callable, Generator, Optional
from unittest.mock import MagicMock, call, patch
import pytest

from media_toolbox import cli
from media_toolbox.nautilus import installer


# ---------------------------------------------------------------------------
# Module-Level Teardown & Invariant Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="module")
def isolate_gi_sys_modules() -> Generator[None, None, None]:
    """
    Module-level teardown fixture ensuring PyGObject and Nautilus mock modules
    do not leak into sys.modules after Nautilus tests complete.
    """
    yield
    to_delete = [
        k
        for k in list(sys.modules.keys())
        if k == "gi"
        or k.startswith("gi.")
        or k.startswith("gi_")
        or k in ("gobject", "glib", "gio", "gtk", "nautilus")
        or k.startswith("media_toolbox.nautilus.extension")
    ]
    for k in to_delete:
        sys.modules.pop(k, None)


# ---------------------------------------------------------------------------
# Headless Nautilus Mock Hierarchy
# ---------------------------------------------------------------------------


class MockLocation:
    """Mock for Gio.File returned by FileInfo.get_location()."""

    def __init__(self, path: str):
        self._path = path

    def get_path(self) -> str:
        return self._path


class MockFileInfo:
    """Mock for Nautilus.FileInfo."""

    def __init__(
        self,
        path: str | Path,
        mime_type: str = "application/octet-stream",
        is_directory: bool = False,
    ):
        self.path = str(path)
        self.mime_type = mime_type
        self._is_dir = is_directory

    def get_uri(self) -> str:
        return f"file://{self.path}"

    def get_name(self) -> str:
        return Path(self.path).name

    def get_mime_type(self) -> str:
        return self.mime_type

    def is_directory(self) -> bool:
        return self._is_dir

    def get_location(self) -> MockLocation:
        return MockLocation(self.path)


class MockMenuItem:
    """Mock for Nautilus.MenuItem with signal callback triggering."""

    def __init__(self, name: str = "", label: str = "", tip: str = "", icon: str = ""):
        self.name = name
        self.label = label
        self.tip = tip
        self.icon = icon
        self.submenu: Optional[MockMenu] = None
        self._signals: dict[str, list[tuple[Callable[..., Any], tuple[Any, ...]]]] = {}

    def set_submenu(self, menu: MockMenu) -> None:
        self.submenu = menu

    def connect(self, signal_name: str, handler: Callable[..., Any], *args: Any) -> None:
        if signal_name not in self._signals:
            self._signals[signal_name] = []
        self._signals[signal_name].append((handler, args))

    def emit_activate(self) -> None:
        """Simulate user activating this menu item in Nautilus."""
        for handler, args in self._signals.get("activate", []):
            handler(self, *args)


class MockMenu:
    """Mock for Nautilus.Menu container."""

    def __init__(self) -> None:
        self.items: list[MockMenuItem] = []

    def append_item(self, item: MockMenuItem) -> None:
        self.items.append(item)

    def get_items(self) -> list[MockMenuItem]:
        return list(self.items)


class MockMenuProvider:
    """Base dummy for Nautilus.MenuProvider interface."""
    pass


class MockGObject:
    """Base dummy for GObject.GObject."""
    pass


@pytest.fixture
def mock_nautilus_env(monkeypatch: pytest.MonkeyPatch) -> Generator[dict[str, Any], None, None]:
    """
    Headless environment fixture injecting mock Nautilus and GObject modules into sys.modules.
    Loads and provides media_toolbox.nautilus.extension without requiring system typelibs.
    """
    fake_nautilus = types.ModuleType("gi.repository.Nautilus")
    fake_nautilus.FileInfo = MockFileInfo  # type: ignore
    fake_nautilus.MenuItem = MockMenuItem  # type: ignore
    fake_nautilus.Menu = MockMenu  # type: ignore
    fake_nautilus.MenuProvider = MockMenuProvider  # type: ignore

    fake_gobject = types.ModuleType("gi.repository.GObject")
    fake_gobject.GObject = MockGObject  # type: ignore

    fake_gi_repo = types.ModuleType("gi.repository")
    fake_gi_repo.Nautilus = fake_nautilus  # type: ignore
    fake_gi_repo.GObject = fake_gobject  # type: ignore

    fake_gi = types.ModuleType("gi")
    fake_gi.repository = fake_gi_repo  # type: ignore
    fake_gi.require_version = lambda *args, **kwargs: None  # type: ignore

    with monkeypatch.context() as m:
        m.setitem(sys.modules, "gi", fake_gi)
        m.setitem(sys.modules, "gi.repository", fake_gi_repo)
        m.setitem(sys.modules, "gi.repository.Nautilus", fake_nautilus)
        m.setitem(sys.modules, "gi.repository.GObject", fake_gobject)

        if "media_toolbox.nautilus.extension" in sys.modules:
            del sys.modules["media_toolbox.nautilus.extension"]

        import media_toolbox.nautilus.extension as ext

        yield {
            "ext": ext,
            "Nautilus": fake_nautilus,
            "GObject": fake_gobject,
            "FileInfo": MockFileInfo,
            "MenuItem": MockMenuItem,
            "Menu": MockMenu,
        }


# ---------------------------------------------------------------------------
# 1. Launcher Script Testing
# ---------------------------------------------------------------------------


class TestLauncherScript:
    """Validates python/media_toolbox/nautilus/launcher.sh syntax and runtime conventions."""

    @pytest.fixture
    def launcher_path(self) -> Path:
        p = Path(__file__).resolve().parent.parent / "nautilus" / "launcher.sh"
        assert p.is_file(), f"launcher.sh not found at expected path: {p}"
        return p

    def test_launcher_bash_syntax_validity(self, launcher_path: Path) -> None:
        """Verify launcher.sh passes strict bash syntax checking (bash -n)."""
        proc = subprocess.run(
            ["bash", "-n", str(launcher_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"bash -n failed for launcher.sh:\n{proc.stderr}"
        assert proc.stderr == ""

    def test_launcher_shebang_and_strict_mode(self, launcher_path: Path) -> None:
        """Assert launcher.sh has valid shebang and strict shell flags."""
        lines = launcher_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) > 0
        assert lines[0].startswith("#!/") and "bash" in lines[0]
        header = "\n".join(lines[:10])
        assert "set -e" in header or "set -euo pipefail" in header

    def test_launcher_exits_nonzero_when_no_files_provided(self, launcher_path: Path) -> None:
        """Assert launcher exits with non-zero code and error message when no files given."""
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
        }
        proc = subprocess.run(
            ["bash", str(launcher_path)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert proc.returncode != 0
        combined = proc.stdout + proc.stderr
        assert any(k in combined.lower() for k in ("no files", "error", "usage", "selected"))

    def test_launcher_execution_with_cli_arguments(
        self, launcher_path: Path, tmp_path: Path
    ) -> None:
        """Assert launcher forwards command line arguments $@ to the Python execution router."""
        log_file = tmp_path / "invoked_args.log"
        mock_bin_dir = tmp_path / "bin"
        mock_bin_dir.mkdir()
        fake_python = mock_bin_dir / "python3"
        fake_python.write_text(
            f"#!/usr/bin/env bash\necho \"$@\" > '{log_file}'\nexit 0\n",
            encoding="utf-8",
        )
        fake_python.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{mock_bin_dir}:{env.get('PATH', '')}"
        env["MEDIA_TOOLBOX_PYTHON"] = str(fake_python)
        env.pop("NAUTILUS_SCRIPT_SELECTED_FILE_PATHS", None)

        test_files = ["/tmp/sample1.mp4", "/tmp/sample2.mkv"]
        proc = subprocess.run(
            ["bash", str(launcher_path), *test_files],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert proc.returncode == 0, f"Launcher failed with stderr:\n{proc.stderr}"

        # Wait briefly for detached background process if launched via nohup
        for _ in range(50):
            if log_file.is_file():
                break
            time.sleep(0.01)

        assert log_file.is_file(), "Fake python was not invoked"
        recorded = log_file.read_text(encoding="utf-8")
        assert "/tmp/sample1.mp4" in recorded
        assert "/tmp/sample2.mkv" in recorded

    def test_launcher_execution_with_nautilus_env_variable(
        self, launcher_path: Path, tmp_path: Path
    ) -> None:
        """Assert launcher reads newline-delimited $NAUTILUS_SCRIPT_SELECTED_FILE_PATHS."""
        log_file = tmp_path / "nautilus_env_args.log"
        mock_bin_dir = tmp_path / "bin"
        mock_bin_dir.mkdir()
        fake_python = mock_bin_dir / "python3"
        fake_python.write_text(
            f"#!/usr/bin/env bash\necho \"$@\" > '{log_file}'\nexit 0\n",
            encoding="utf-8",
        )
        fake_python.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{mock_bin_dir}:{env.get('PATH', '')}"
        env["MEDIA_TOOLBOX_PYTHON"] = str(fake_python)
        env["NAUTILUS_SCRIPT_SELECTED_FILE_PATHS"] = "/media/video_a.mp4\n/media/video_b.mkv\n"

        proc = subprocess.run(
            ["bash", str(launcher_path)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert proc.returncode == 0, f"Launcher failed:\n{proc.stderr}"

        for _ in range(50):
            if log_file.is_file():
                break
            time.sleep(0.01)

        assert log_file.is_file()
        recorded = log_file.read_text(encoding="utf-8")
        assert "/media/video_a.mp4" in recorded
        assert "/media/video_b.mkv" in recorded

    def test_launcher_preserves_spaces_and_special_chars_in_paths(
        self, launcher_path: Path, tmp_path: Path
    ) -> None:
        """Assert launcher preserves spaces, brackets, and quotes in filenames."""
        log_file = tmp_path / "special_args.log"
        mock_bin_dir = tmp_path / "bin"
        mock_bin_dir.mkdir()
        fake_python = mock_bin_dir / "python3"
        # Script writes each argument on its own line
        fake_python.write_text(
            f"#!/usr/bin/env bash\nfor arg in \"$@\"; do echo \"$arg\" >> '{log_file}'; done\nexit 0\n",
            encoding="utf-8",
        )
        fake_python.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{mock_bin_dir}:{env.get('PATH', '')}"
        env["MEDIA_TOOLBOX_PYTHON"] = str(fake_python)
        special_path = "/tmp/my video [1080p] (2024) 'test' #1.mp4"
        env["NAUTILUS_SCRIPT_SELECTED_FILE_PATHS"] = f"{special_path}\n"

        proc = subprocess.run(
            ["bash", str(launcher_path)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert proc.returncode == 0

        for _ in range(50):
            if log_file.is_file():
                break
            time.sleep(0.01)

        assert log_file.is_file()
        lines = log_file.read_text(encoding="utf-8").splitlines()
        assert special_path in lines, f"Filename was split incorrectly. Recorded: {lines}"


# ---------------------------------------------------------------------------
# 2. Extension Testing (Headless Python-Nautilus Mock)
# ---------------------------------------------------------------------------


class TestNautilusExtensionHeadless:
    """Validates python/media_toolbox/nautilus/extension.py menu logic and callbacks."""

    def test_get_file_items_returns_menu_for_video(self, mock_nautilus_env: dict[str, Any]) -> None:
        """Assert get_file_items returns root Menu item with submenus for video file."""
        ext = mock_nautilus_env["ext"]
        provider = ext.MediaToolboxExtension()
        f = MockFileInfo("/tmp/clip.mp4", mime_type="video/mp4")

        items = provider.get_file_items([f])
        assert len(items) == 1
        root = items[0]
        assert "Media Toolbox" in root.label
        assert root.submenu is not None

        sub_items = root.submenu.get_items()
        assert len(sub_items) >= 4
        labels = [item.label for item in sub_items]
        assert any("Open" in lbl for lbl in labels)
        assert any("Inspect" in lbl for lbl in labels)
        assert any("Transcode" in lbl for lbl in labels)
        assert any("Extract Audio" in lbl for lbl in labels)

    def test_get_file_items_returns_menu_for_audio(self, mock_nautilus_env: dict[str, Any]) -> None:
        """Assert get_file_items returns root Menu item for audio file."""
        ext = mock_nautilus_env["ext"]
        provider = ext.MediaToolboxExtension()
        f = MockFileInfo("/tmp/track.flac", mime_type="audio/flac")

        items = provider.get_file_items([f])
        assert len(items) == 1
        assert items[0].submenu is not None

    @pytest.mark.parametrize(
        "ext_name",
        [".mp4", ".mkv", ".mov", ".avi", ".webm", ".mp3", ".wav", ".flac", ".opus", ".m4a", ".aac"],
    )
    def test_get_file_items_matches_container_extensions_with_generic_mime(
        self, mock_nautilus_env: dict[str, Any], ext_name: str
    ) -> None:
        """Assert extension fallback recognizes media extensions even when MIME is octet-stream."""
        ext = mock_nautilus_env["ext"]
        provider = ext.MediaToolboxExtension()
        f = MockFileInfo(f"/tmp/file{ext_name}", mime_type="application/octet-stream")

        items = provider.get_file_items([f])
        assert len(items) == 1, f"Failed to match extension {ext_name} with generic MIME"

    def test_get_file_items_ignores_non_media_files(self, mock_nautilus_env: dict[str, Any]) -> None:
        """Assert get_file_items returns empty list for text, pdf, and non-media archives."""
        ext = mock_nautilus_env["ext"]
        provider = ext.MediaToolboxExtension()
        files = [
            MockFileInfo("/tmp/notes.txt", mime_type="text/plain"),
            MockFileInfo("/tmp/doc.pdf", mime_type="application/pdf"),
            MockFileInfo("/tmp/data.zip", mime_type="application/zip"),
            MockFileInfo("/tmp/code.py", mime_type="text/x-python"),
        ]
        items = provider.get_file_items(files)
        assert items == []

    def test_get_file_items_ignores_directories(self, mock_nautilus_env: dict[str, Any]) -> None:
        """Assert directories are excluded even if named like media files."""
        ext = mock_nautilus_env["ext"]
        provider = ext.MediaToolboxExtension()
        f = MockFileInfo("/tmp/movies.mp4", mime_type="inode/directory", is_directory=True)

        items = provider.get_file_items([f])
        assert items == []

    def test_get_file_items_mixed_batch_filters_to_media(
        self, mock_nautilus_env: dict[str, Any]
    ) -> None:
        """Assert mixed batch of media and non-media shows menu targeting media only."""
        ext = mock_nautilus_env["ext"]
        provider = ext.MediaToolboxExtension()
        video = MockFileInfo("/tmp/holiday.mp4", mime_type="video/mp4")
        doc = MockFileInfo("/tmp/summary.pdf", mime_type="application/pdf")

        items = provider.get_file_items([video, doc])
        assert len(items) == 1

    def test_menu_callbacks_dispatch_non_blocking_subprocess(
        self, mock_nautilus_env: dict[str, Any]
    ) -> None:
        """Assert activating menu items dispatches non-blocking detached subprocesses."""
        ext = mock_nautilus_env["ext"]
        provider = ext.MediaToolboxExtension()
        f = MockFileInfo("/tmp/render.mov", mime_type="video/quicktime")
        items = provider.get_file_items([f])
        assert len(items) == 1
        sub_items = items[0].submenu.get_items()

        with patch("subprocess.Popen") as mock_popen, patch("subprocess.run") as mock_run:
            for item in sub_items:
                mock_popen.reset_mock()
                mock_run.reset_mock()

                # Trigger activation signal
                item.emit_activate()

                # Assert non-blocking Popen was called
                assert mock_popen.call_count == 1, f"Popen not called for {item.label}"
                # Assert blocking subprocess.run was NEVER called
                assert mock_run.call_count == 0, f"Blocking subprocess.run was called for {item.label}"

                # Verify command line includes target file
                cmd = mock_popen.call_args[0][0]
                cmd_str = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
                assert "/tmp/render.mov" in cmd or "/tmp/render.mov" in cmd_str

                # Verify detached process flags (start_new_session=True or close_fds=True)
                kwargs = mock_popen.call_args[1]
                assert kwargs.get("start_new_session") is True or kwargs.get("close_fds") is True


# ---------------------------------------------------------------------------
# 3. Installer Testing
# ---------------------------------------------------------------------------


class TestNautilusInstaller:
    """Validates python/media_toolbox/nautilus/installer.py installation and lifecycle logic."""

    def test_install_nautilus_into_isolated_tmp_path(self, tmp_path: Path) -> None:
        """Assert install_nautilus creates files with exact required paths and permissions."""
        installed = installer.install_nautilus(dest_dir=tmp_path)
        assert len(installed) == 3

        launcher = tmp_path / "nautilus" / "scripts" / "Media-Toolbox"
        extension = tmp_path / "nautilus-python" / "extensions" / "media_toolbox_nautilus.py"
        desktop = tmp_path / "applications" / "io.github.tazztone.MediaToolbox.desktop"

        assert launcher.is_file()
        assert extension.is_file()
        assert desktop.is_file()

        # Permissions checks
        launcher_mode = launcher.stat().st_mode & 0o777
        assert launcher_mode == 0o755, f"Expected 0o755 mode, got {oct(launcher_mode)}"

        ext_mode = extension.stat().st_mode & 0o644
        assert ext_mode == 0o644, f"Expected 0o644 mode, got {oct(ext_mode)}"

        desktop_mode = desktop.stat().st_mode & 0o644
        assert desktop_mode == 0o644, f"Expected 0o644 mode, got {oct(desktop_mode)}"

    def test_desktop_file_valid_ini_syntax_and_fields(self, tmp_path: Path) -> None:
        """Assert installed desktop entry is valid INI conforming to XDG Desktop Entry Spec."""
        installer.install_nautilus(dest_dir=tmp_path)
        desktop = tmp_path / "applications" / "io.github.tazztone.MediaToolbox.desktop"

        config = configparser.ConfigParser(interpolation=None)
        config.read_string(desktop.read_text(encoding="utf-8"))

        assert "Desktop Entry" in config.sections()
        entry = config["Desktop Entry"]
        assert entry.get("Type") == "Application"
        assert entry.get("Name") == "Media Toolbox"
        assert entry.get("Terminal") in ("false", "False")
        assert "Exec" in entry
        assert "Categories" in entry
        assert "AudioVideo;" in entry.get("Categories")
        assert "MimeType" in entry
        assert "video/mp4;" in entry.get("MimeType")

        # System XDG validator check (if tool present on Linux)
        validator = shutil.which("desktop-file-validate")
        if validator:
            proc = subprocess.run(
                [validator, str(desktop)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert proc.returncode == 0, f"desktop-file-validate failed:\n{proc.stderr}"

    def test_install_nautilus_idempotent_reinstall(self, tmp_path: Path) -> None:
        """Assert calling install_nautilus multiple times overwrites cleanly without error."""
        first_run = installer.install_nautilus(dest_dir=tmp_path)
        second_run = installer.install_nautilus(dest_dir=tmp_path)

        assert first_run == second_run
        launcher = tmp_path / "nautilus" / "scripts" / "Media-Toolbox"
        assert (launcher.stat().st_mode & 0o777) == 0o755

    def test_install_nautilus_dry_run(self, tmp_path: Path) -> None:
        """Assert dry_run=True returns planned paths without creating them on disk."""
        dry_targets = installer.install_nautilus(dest_dir=tmp_path, dry_run=True)
        assert len(dry_targets) == 3

        launcher = tmp_path / "nautilus" / "scripts" / "Media-Toolbox"
        assert not launcher.exists()
        assert not (tmp_path / "applications").exists()

    def test_status_nautilus_reflects_accurate_state(self, tmp_path: Path) -> None:
        """Assert status_nautilus tracks uninstalled, partial, and fully installed states."""
        # 1. Initially uninstalled
        status = installer.status_nautilus(dest_dir=tmp_path)
        assert status["launcher"] is False
        assert status["extension"] is False
        assert status["desktop"] is False
        assert status["installed"] is False

        # 2. Partially installed (only launcher script)
        script_dir = tmp_path / "nautilus" / "scripts"
        script_dir.mkdir(parents=True)
        launcher = script_dir / "Media-Toolbox"
        launcher.write_text("#!/bin/bash\n", encoding="utf-8")
        launcher.chmod(0o755)

        status = installer.status_nautilus(dest_dir=tmp_path)
        assert status["launcher"] is True
        assert status["extension"] is False
        assert status["installed"] is False

        # 3. Fully installed
        installer.install_nautilus(dest_dir=tmp_path)
        status = installer.status_nautilus(dest_dir=tmp_path)
        assert status["launcher"] is True
        assert status["extension"] is True
        assert status["desktop"] is True
        assert status["installed"] is True

    def test_uninstall_nautilus_removes_toolbox_files_and_preserves_directories(
        self, tmp_path: Path
    ) -> None:
        """Assert uninstall_nautilus removes toolbox files and preserves third-party files/directories."""
        installer.install_nautilus(dest_dir=tmp_path)

        # Create unrelated user files in the same directories
        other_script = tmp_path / "nautilus" / "scripts" / "OtherUserScript.sh"
        other_script.write_text("#!/bin/bash\necho other\n", encoding="utf-8")

        other_ext = tmp_path / "nautilus-python" / "extensions" / "other_extension.py"
        other_ext.write_text("# other ext\n", encoding="utf-8")

        other_desktop = tmp_path / "applications" / "other.desktop"
        other_desktop.write_text("[Desktop Entry]\n", encoding="utf-8")

        # Perform uninstallation
        removed = installer.uninstall_nautilus(dest_dir=tmp_path)
        assert len(removed) == 3

        # Media toolbox files must be gone
        paths = installer.get_nautilus_paths(dest_dir=tmp_path)
        assert not paths["launcher"].exists()
        assert not paths["extension"].exists()
        assert not paths["desktop"].exists()

        # Third-party files must STILL exist
        assert other_script.is_file()
        assert other_ext.is_file()
        assert other_desktop.is_file()

        # Directories must STILL exist
        assert (tmp_path / "nautilus" / "scripts").is_dir()
        assert (tmp_path / "nautilus-python" / "extensions").is_dir()
        assert (tmp_path / "applications").is_dir()

    def test_uninstall_nautilus_dry_run(self, tmp_path: Path) -> None:
        """Assert uninstall with dry_run=True returns removed targets without deleting files."""
        installer.install_nautilus(dest_dir=tmp_path)
        removed = installer.uninstall_nautilus(dest_dir=tmp_path, dry_run=True)
        assert len(removed) == 3

        paths = installer.get_nautilus_paths(dest_dir=tmp_path)
        assert paths["launcher"].is_file()
        assert paths["extension"].is_file()
        assert paths["desktop"].is_file()

    def test_uninstall_nautilus_idempotent_when_already_absent(self, tmp_path: Path) -> None:
        """Assert uninstall on an empty/uninstalled directory succeeds returning empty list."""
        removed = installer.uninstall_nautilus(dest_dir=tmp_path)
        assert removed == []


# ---------------------------------------------------------------------------
# 4. CLI Subcommand Testing
# ---------------------------------------------------------------------------


class TestNautilusCLISubcommands:
    """Validates CLI integration for install-nautilus, uninstall-nautilus, and status-nautilus."""

    def test_cli_install_nautilus_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Assert 'media_toolbox install-nautilus --dry-run' succeeds without modifying system."""
        exit_code = cli.main(["install-nautilus", "--dry-run"])
        assert exit_code == 0
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "dry-run" in combined.lower() or "would install" in combined.lower()

    def test_cli_uninstall_nautilus_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Assert 'media_toolbox uninstall-nautilus --dry-run' succeeds without deleting files."""
        exit_code = cli.main(["uninstall-nautilus", "--dry-run"])
        assert exit_code == 0
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "dry-run" in combined.lower() or "would remove" in combined.lower() or "no files" in combined.lower()

    def test_cli_install_and_uninstall_with_dest_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Assert CLI subcommands correctly pass --dest-dir to installer module."""
        # 1. Install via CLI
        code = cli.main(["install-nautilus", "--dest-dir", str(tmp_path)])
        assert code == 0
        paths = installer.get_nautilus_paths(dest_dir=tmp_path)
        assert paths["launcher"].is_file()
        assert paths["extension"].is_file()
        assert paths["desktop"].is_file()

        # 2. Check status via CLI
        code = cli.main(["status-nautilus", "--dest-dir", str(tmp_path)])
        assert code == 0

        # 3. Uninstall via CLI
        code = cli.main(["uninstall-nautilus", "--dest-dir", str(tmp_path)])
        assert code == 0
        assert not paths["launcher"].exists()
        assert not paths["extension"].exists()
        assert not paths["desktop"].exists()

    def test_cli_status_nautilus_json_mode(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Assert 'status-nautilus --json' emits valid JSON structure."""
        import json

        code = cli.main(["status-nautilus", "--dest-dir", str(tmp_path), "--json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "launcher" in data
        assert "extension" in data
        assert "desktop" in data
        assert "installed" in data

    def test_cli_subcommands_headless_execution_does_not_load_gi(self) -> None:
        """Assert executing install-nautilus --dry-run in standalone subprocess loads zero gi modules."""
        toolbox_root = Path(__file__).resolve().parent.parent
        python_dir = str(toolbox_root.parent)
        env = os.environ.copy()
        env["PYTHONPATH"] = python_dir

        code = (
            "import sys\n"
            "from media_toolbox import cli\n"
            "exit_code = cli.main(['install-nautilus', '--dry-run'])\n"
            "assert exit_code == 0\n"
            "assert 'gi' not in sys.modules, f'Forbidden gi loaded: {list(sys.modules.keys())}'\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert proc.returncode == 0, f"Headless check failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}"


# ---------------------------------------------------------------------------
# 5. Headless AST & Module Invariants
# ---------------------------------------------------------------------------


class TestNautilusModuleInvariants:
    """Verifies architectural invariants: zero module-scope GUI imports in tests and installer."""

    def test_test_nautilus_has_zero_module_scope_gi_imports(self) -> None:
        """Assert test_nautilus.py has zero top-level imports from gi or Nautilus."""
        test_file = Path(__file__).resolve()
        source = test_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(test_file))

        forbidden = ("gi", "nautilus", "gtk", "adw", "gobject")
        violations: list[str] = []

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0].lower()
                    if root in forbidden:
                        violations.append(f"Line {node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0].lower()
                    if root in forbidden:
                        violations.append(f"Line {node.lineno}: from {node.module} import ...")

        assert not violations, (
            "Forbidden module-scope GUI imports found in test_nautilus.py:\n"
            + "\n".join(violations)
        )

    def test_installer_has_zero_gui_imports(self) -> None:
        """Assert media_toolbox/nautilus/installer.py has zero GUI imports using AST scanner."""
        from media_toolbox.tests.test_headless_ast import scan_ast_for_gui_violations

        installer_file = Path(__file__).resolve().parent.parent / "nautilus" / "installer.py"
        if not installer_file.is_file():
            pytest.skip("installer.py not implemented yet")

        source = installer_file.read_text(encoding="utf-8")
        violations = scan_ast_for_gui_violations(source, str(installer_file))
        assert not violations, (
            f"GUI import violations detected in {installer_file.name}:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
