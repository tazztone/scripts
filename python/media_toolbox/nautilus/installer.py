"""
Installer and lifecycle manager for media_toolbox desktop & Nautilus integrations.

Manages automated deployment and removal of:
1. Nautilus user launcher script:
   ~/.local/share/nautilus/scripts/Media-Toolbox (mode 0o755)
2. Python-Nautilus context menu extension:
   ~/.local/share/nautilus-python/extensions/media_toolbox_nautilus.py (mode 0o644)
3. XDG desktop application entry:
   ~/.local/share/applications/io.github.tazztone.MediaToolbox.desktop (mode 0o644)

INVARIANT: Strict zero GUI imports (gi, Gtk, Adw, Nautilus).
Uses standard library exclusively (os, pathlib, shutil, subprocess, sys).
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Optional

__all__ = [
    "DEFAULT_DESKTOP_ENTRY",
    "get_data_home",
    "get_nautilus_paths",
    "run_update_desktop_database",
    "install_nautilus",
    "uninstall_nautilus",
    "status_nautilus",
]

DEFAULT_DESKTOP_ENTRY = """[Desktop Entry]
Version=1.0
Type=Application
Name=Media Toolbox
Comment=Modern Python Media Inspection & Transcoding Toolbox
Exec=media_toolbox %F
Icon=video-x-generic
Terminal=false
Categories=AudioVideo;AudioVideoEditing;Audio;Video;
MimeType=video/mp4;video/x-matroska;video/quicktime;video/webm;audio/mpeg;audio/x-wav;audio/flac;audio/ogg;
Keywords=video;audio;media;transcode;ffmpeg;probe;inspect;adwaita;nautilus;
StartupNotify=true
StartupWMClass=io.github.tazztone.MediaToolbox
Actions=Inspect;

[Desktop Action Inspect]
Name=Inspect Media Metadata
Exec=media_toolbox inspect %f
"""


def get_data_home(dest_dir: Optional[str | Path] = None) -> Path:
    """
    Resolve base XDG data directory.

    Priority:
    1. Explicit dest_dir argument (enables pytest tmp_path isolation)
    2. $XDG_DATA_HOME environment variable
    3. Fallback: ~/.local/share
    """
    if dest_dir is not None:
        return Path(dest_dir).expanduser().resolve()
    xdg_env = os.environ.get("XDG_DATA_HOME")
    if xdg_env and xdg_env.strip():
        return Path(xdg_env).expanduser().resolve()
    return (Path.home() / ".local" / "share").resolve()


def get_nautilus_paths(dest_dir: Optional[str | Path] = None) -> dict[str, Path]:
    """Return dictionary of target component paths under resolved data home."""
    data_home = get_data_home(dest_dir)
    return {
        "launcher": data_home / "nautilus" / "scripts" / "Media-Toolbox",
        "extension": data_home / "nautilus-python" / "extensions" / "media_toolbox_nautilus.py",
        "desktop": data_home / "applications" / "io.github.tazztone.MediaToolbox.desktop",
    }


def run_update_desktop_database(applications_dir: Path) -> bool:
    """
    Execute update-desktop-database if the binary is present on the host.
    Returns True if update executed successfully, False otherwise.
    Never raises exceptions.
    """
    bin_path = shutil.which("update-desktop-database")
    if not bin_path or not applications_dir.is_dir():
        return False
    try:
        proc = subprocess.run(
            [bin_path, str(applications_dir)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def install_nautilus(
    dest_dir: Optional[str | Path] = None,
    dry_run: bool = False,
) -> list[Path]:
    """
    Install Nautilus launcher script, python-nautilus extension, and desktop entry.

    Args:
        dest_dir: Optional target root path (overriding XDG_DATA_HOME).
        dry_run: If True, simulate actions without modifying filesystem.

    Returns:
        List of Path objects representing installed files.
    """
    paths = get_nautilus_paths(dest_dir)
    targets = [paths["launcher"], paths["extension"], paths["desktop"]]

    if dry_run:
        return targets

    pkg_nautilus_dir = Path(__file__).resolve().parent

    # 1. Source files resolution
    src_launcher = pkg_nautilus_dir / "launcher.sh"
    src_ext = pkg_nautilus_dir / "extension.py"
    src_desktop = pkg_nautilus_dir / "io.github.tazztone.MediaToolbox.desktop"

    # Read launcher content
    if src_launcher.is_file():
        launcher_content = src_launcher.read_text(encoding="utf-8")
    else:
        launcher_content = (
            "#!/usr/bin/env bash\n"
            "# Media-Toolbox launcher fallback\n"
            "exec python3 -m media_toolbox.ui.app \"$@\"\n"
        )

    # Read extension content
    if src_ext.is_file():
        ext_content = src_ext.read_text(encoding="utf-8")
    else:
        ext_content = "# python-nautilus extension placeholder\n"

    # Read desktop entry content
    if src_desktop.is_file():
        desktop_content = src_desktop.read_text(encoding="utf-8")
    else:
        desktop_content = DEFAULT_DESKTOP_ENTRY

    # 2. Write and set permissions
    # Launcher script: 0o755 (executable)
    paths["launcher"].parent.mkdir(parents=True, exist_ok=True)
    paths["launcher"].write_text(launcher_content, encoding="utf-8")
    paths["launcher"].chmod(0o755)

    # Extension file: 0o644
    paths["extension"].parent.mkdir(parents=True, exist_ok=True)
    paths["extension"].write_text(ext_content, encoding="utf-8")
    paths["extension"].chmod(0o644)

    # Desktop entry file: 0o644
    paths["desktop"].parent.mkdir(parents=True, exist_ok=True)
    paths["desktop"].write_text(desktop_content, encoding="utf-8")
    paths["desktop"].chmod(0o644)

    # 3. Update desktop database
    run_update_desktop_database(paths["desktop"].parent)

    return targets


def uninstall_nautilus(
    dest_dir: Optional[str | Path] = None,
    dry_run: bool = False,
) -> list[Path]:
    """
    Safely remove installed Nautilus launcher script, extension, and desktop entry.
    Preserves parent directories.

    Args:
        dest_dir: Optional target root path (overriding XDG_DATA_HOME).
        dry_run: If True, simulate removal without modifying filesystem.

    Returns:
        List of Path objects representing removed files.
    """
    paths = get_nautilus_paths(dest_dir)
    existing_targets = [p for p in paths.values() if p.is_file()]

    if dry_run:
        return existing_targets

    removed: list[Path] = []
    for p in existing_targets:
        try:
            p.unlink()
            removed.append(p)
        except OSError:
            pass

    # Update desktop database if desktop file was removed
    if paths["desktop"] in removed:
        run_update_desktop_database(paths["desktop"].parent)

    return removed


def status_nautilus(dest_dir: Optional[str | Path] = None) -> dict[str, bool]:
    """
    Query installation status of each Nautilus integration component.

    Returns:
        dict with boolean status for "launcher", "extension", "desktop", and "installed".
    """
    paths = get_nautilus_paths(dest_dir)

    launcher_ok = paths["launcher"].is_file() and os.access(paths["launcher"], os.X_OK)
    extension_ok = paths["extension"].is_file()
    desktop_ok = paths["desktop"].is_file()
    all_ok = launcher_ok and extension_ok and desktop_ok

    return {
        "launcher": launcher_ok,
        "extension": extension_ok,
        "desktop": desktop_ok,
        "installed": all_ok,
        "all_installed": all_ok,
    }
