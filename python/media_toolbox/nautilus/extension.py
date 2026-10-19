"""
Native GNOME Nautilus 4.1 extension for media_toolbox.
Installed to: ~/.local/share/nautilus-python/extensions/media_toolbox_nautilus.py

Provides contextual right-click menu items for video and audio files:
- Open in Media Toolbox (GUI)
- Inspect Metadata (Terminal)
- Quick Transcode (H.264)
- Extract Audio (MP3)

Non-blocking: all external commands spawn detached subprocesses (start_new_session=True).
Graceful fallback: imports without crashing when python-nautilus is not installed.
"""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Any, Optional, Sequence
from urllib.parse import unquote, urlparse

try:
    import gi
    try:
        gi.require_version("Nautilus", "4.1")
    except (ValueError, AttributeError):
        pass
    from gi.repository import GObject, Nautilus
    _NAUTILUS_AVAILABLE = True
except (ImportError, ValueError, AttributeError):
    _NAUTILUS_AVAILABLE = False

    class _MockGObject:
        class GObject:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

    class _MockNautilus:
        class MenuProvider:
            pass

        class MenuItem:
            def __init__(self, name: str = "", label: str = "", tip: str = "", icon: str = "") -> None:
                self.name = name
                self.label = label
                self.tip = tip
                self.icon = icon
                self.submenu: Any = None
                self._callbacks: list[tuple[str, Any, tuple[Any, ...]]] = []

            def set_submenu(self, menu: Any) -> None:
                self.submenu = menu

            def connect(self, signal: str, callback: Any, *args: Any) -> None:
                self._callbacks.append((signal, callback, args))

            def activate(self) -> None:
                for sig, cb, args in self._callbacks:
                    if sig == "activate":
                        cb(self, *args)

        class Menu:
            def __init__(self) -> None:
                self.items: list[Any] = []

            def append_item(self, item: Any) -> None:
                self.items.append(item)

            def get_items(self) -> list[Any]:
                return self.items

        class FileInfo:
            pass

    GObject = _MockGObject  # type: ignore
    Nautilus = _MockNautilus  # type: ignore

SUPPORTED_MIME_PREFIXES = ("video/", "audio/")

ADDITIONAL_MEDIA_MIMES = {
    "application/ogg",
    "application/x-ogg",
    "application/x-matroska",
    "application/x-shockwave-flash",
}

SUPPORTED_EXTENSIONS = {
    # Video containers
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".ts",
    # Audio containers
    ".mp3", ".wav", ".flac", ".opus", ".m4a", ".aac", ".ogg", ".oga", ".wma",
}

TERMINAL_CANDIDATES = (
    "ptyxis",
    "gnome-terminal",
    "kgx",
    "x-terminal-emulator",
    "kitty",
    "alacritty",
    "xterm",
)


def is_media_file(file_info: Any) -> bool:
    """Check if Nautilus.FileInfo represents a supported video or audio file."""
    if hasattr(file_info, "is_directory") and file_info.is_directory():
        return False

    if hasattr(file_info, "get_mime_type"):
        mime = (file_info.get_mime_type() or "").lower()
        if any(mime.startswith(prefix) for prefix in SUPPORTED_MIME_PREFIXES):
            return True
        if mime in ADDITIONAL_MEDIA_MIMES:
            return True

    name = ""
    if hasattr(file_info, "get_name"):
        name = file_info.get_name() or ""
    elif hasattr(file_info, "get_uri"):
        name = file_info.get_uri().split("/")[-1]

    ext = Path(name).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


def get_file_path(file_info: Any) -> Optional[str]:
    """Extract absolute filesystem path from Nautilus.FileInfo."""
    if hasattr(file_info, "get_location"):
        loc = file_info.get_location()
        if loc and hasattr(loc, "get_path"):
            path = loc.get_path()
            if path:
                return path

    if hasattr(file_info, "get_uri"):
        uri = file_info.get_uri()
        if uri and uri.startswith("file://"):
            return unquote(urlparse(uri).path)

    return None


def find_python_interpreter() -> str:
    """Locate virtualenv or system Python interpreter."""
    override = os.environ.get("MEDIA_TOOLBOX_PYTHON")
    if override and os.path.isfile(override) and os.access(override, os.X_OK):
        return override

    try:
        ext_path = Path(__file__).resolve()
        repo_root = ext_path.parent.parent.parent.parent
        venv_py = repo_root / ".venv" / "bin" / "python3"
        if venv_py.is_file() and os.access(venv_py, os.X_OK):
            return str(venv_py)
    except Exception:
        pass

    active_venv = os.environ.get("VIRTUAL_ENV")
    if active_venv:
        cand = Path(active_venv) / "bin" / "python3"
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)

    for known in (
        Path("/home/tazztone/_coding/scripts/.venv/bin/python3"),
        Path.home() / ".local/share/media_toolbox/venv/bin/python3",
        Path.home() / ".venv/bin/python3",
    ):
        if known.is_file() and os.access(known, os.X_OK):
            return str(known)

    return sys.executable or "/usr/bin/python3"


def get_toolbox_env() -> dict[str, str]:
    """Build environment dictionary guaranteeing media_toolbox is importable."""
    env = os.environ.copy()
    try:
        ext_path = Path(__file__).resolve()
        repo_py = ext_path.parent.parent.parent
        if (repo_py / "media_toolbox" / "__init__.py").is_file():
            pp = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{repo_py}:{pp}" if pp else str(repo_py)
            return env
    except Exception:
        pass

    known_py = Path("/home/tazztone/_coding/scripts/python")
    if (known_py / "media_toolbox" / "__init__.py").is_file():
        pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{known_py}:{pp}" if pp else str(known_py)

    return env


def launch_detached(cmd: Sequence[str], env: Optional[dict[str, str]] = None) -> subprocess.Popen[bytes]:
    """Launch detached subprocess to avoid blocking Nautilus or dying on window close."""
    full_env = get_toolbox_env()
    if env:
        full_env.update(env)

    return subprocess.Popen(
        list(cmd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
        env=full_env,
    )


def find_terminal_emulator() -> Optional[str]:
    """Find installed terminal emulator executable."""
    for term in TERMINAL_CANDIDATES:
        if shutil.which(term):
            return term
    return None


def build_terminal_command(terminal_bin: str, shell_script: str, extra_args: Sequence[str] = ()) -> list[str]:
    """Assemble terminal execution arguments across terminal types."""
    term_name = Path(terminal_bin).name
    if term_name in ("ptyxis", "gnome-terminal"):
        return [terminal_bin, "--", "bash", "-c", shell_script, "bash", *extra_args]
    elif term_name == "kgx":
        return [terminal_bin, "-e", f"bash -c {shlex.quote(shell_script)}", *extra_args]
    elif term_name == "kitty":
        return [terminal_bin, "--hold", "bash", "-c", shell_script, "bash", *extra_args]
    elif term_name in ("alacritty", "xterm", "x-terminal-emulator"):
        return [terminal_bin, "-e", "bash", "-c", shell_script, "bash", *extra_args]
    else:
        return [terminal_bin, "-e", f"bash -c {shlex.quote(shell_script)}", *extra_args]


def get_transcode_output_path(input_path: str) -> str:
    """Generate non-colliding default output path for H.264 transcode."""
    p = Path(input_path)
    base_out = p.parent / f"{p.stem}_h264.mp4"
    if not base_out.exists():
        return str(base_out)
    counter = 1
    while True:
        candidate = p.parent / f"{p.stem}_h264_{counter}.mp4"
        if not candidate.exists():
            return str(candidate)
        counter += 1


def get_extract_audio_output_path(input_path: str) -> str:
    """Generate non-colliding default output path for MP3 extraction."""
    p = Path(input_path)
    base_out = p.parent / (f"{p.stem}_audio.mp3" if p.suffix.lower() == ".mp3" else f"{p.stem}.mp3")
    if not base_out.exists():
        return str(base_out)
    counter = 1
    while True:
        candidate = p.parent / f"{p.stem}_audio_{counter}.mp3"
        if not candidate.exists():
            return str(candidate)
        counter += 1


class MediaToolboxExtension(GObject.GObject, Nautilus.MenuProvider):
    """Nautilus 4.1 MenuProvider extension providing Media Toolbox context actions."""

    def __init__(self) -> None:
        super().__init__()

    def get_file_items(self, files: list[Any]) -> list[Any]:
        """Generate contextual menu items when media files are selected."""
        valid_paths: list[str] = []
        for f in files:
            if is_media_file(f):
                p = get_file_path(f)
                if p:
                    valid_paths.append(p)

        if not valid_paths:
            return []

        root_item = Nautilus.MenuItem(
            name="MediaToolbox::Root",
            label="Media Toolbox",
            tip="Video & audio tools for selected media",
            icon="applications-multimedia",
        )
        submenu = Nautilus.Menu()
        root_item.set_submenu(submenu)

        item_open = Nautilus.MenuItem(
            name="MediaToolbox::Open",
            label="Open in Media Toolbox",
            tip="Open in Media Toolbox graphical interface",
            icon="media-playback-start",
        )
        item_open.connect("activate", self._on_open, valid_paths)
        submenu.append_item(item_open)

        item_inspect = Nautilus.MenuItem(
            name="MediaToolbox::Inspect",
            label="Inspect Metadata (Terminal)",
            tip="Inspect stream and codec metadata using ffprobe",
            icon="dialog-information",
        )
        item_inspect.connect("activate", self._on_inspect, valid_paths)
        submenu.append_item(item_inspect)

        item_transcode = Nautilus.MenuItem(
            name="MediaToolbox::QuickTranscode",
            label="Quick Transcode (H.264)",
            tip="Transcode video to standard H.264 MP4",
            icon="video-x-generic",
        )
        item_transcode.connect("activate", self._on_quick_transcode, valid_paths)
        submenu.append_item(item_transcode)

        item_extract = Nautilus.MenuItem(
            name="MediaToolbox::ExtractAudio",
            label="Extract Audio (MP3)",
            tip="Extract audio stream to MP3",
            icon="audio-x-generic",
        )
        item_extract.connect("activate", self._on_extract_audio, valid_paths)
        submenu.append_item(item_extract)

        return [root_item]

    def _on_open(self, _item: Any, paths: list[str]) -> None:
        """Launch GUI application detached."""
        py = find_python_interpreter()
        cmd = [py, "-m", "media_toolbox.ui.app", *paths]
        launch_detached(cmd)

    def _on_inspect(self, _item: Any, paths: list[str]) -> None:
        """Launch terminal to inspect media metadata."""
        py = find_python_interpreter()
        term = find_terminal_emulator()

        lines = ["set -e", "echo '=== Media Toolbox: Metadata Inspection ==='"]
        for p in paths:
            lines.append(f"echo {shlex.quote(f'--- Probing: {p} ---')}")
            lines.append(f"{shlex.quote(py)} -m media_toolbox.cli inspect {shlex.quote(p)}")
            lines.append("echo ''")
        lines.append("read -n 1 -s -r -p 'Press any key to close...'")
        script = "\n".join(lines)

        if term:
            launch_detached(build_terminal_command(term, script, paths))
        elif shutil.which("zenity"):
            first = paths[0]
            pipe_cmd = (
                f"{shlex.quote(py)} -m media_toolbox.cli inspect {shlex.quote(first)} "
                f"| zenity --text-info --title='Media Metadata' --width=700 --height=500"
            )
            launch_detached(["bash", "-c", pipe_cmd, "bash", *paths])
        elif shutil.which("notify-send"):
            shutil_notify = (
                f"OUT=$({shlex.quote(py)} -m media_toolbox.cli inspect {shlex.quote(paths[0])} | head -n 10); "
                f"notify-send 'Media Metadata' \"$OUT\""
            )
            launch_detached(["bash", "-c", shutil_notify, "bash", *paths])

    def _on_quick_transcode(self, _item: Any, paths: list[str]) -> None:
        """Launch batch H.264 video transcode."""
        py = find_python_interpreter()
        term = find_terminal_emulator()

        lines = ["set -e", "echo '=== Media Toolbox: Quick Transcode (H.264) ==='"]
        for idx, p in enumerate(paths, 1):
            out_p = get_transcode_output_path(p)
            lines.append(f"echo {shlex.quote(f'[{idx}/{len(paths)}] Transcoding {p} -> {out_p}')}")
            cmd = f"{shlex.quote(py)} -m media_toolbox.cli transcode {shlex.quote(p)} {shlex.quote(out_p)} --preset h264"
            lines.append(cmd)
        lines.append("echo ''")
        lines.append("echo '=== Transcoding Complete ==='")
        lines.append("if command -v notify-send >/dev/null 2>&1; then notify-send 'Media Toolbox' 'Transcoding complete'; fi")
        lines.append("read -n 1 -s -r -p 'Press any key to close...'")
        script = "\n".join(lines)

        if term:
            launch_detached(build_terminal_command(term, script, paths))
        else:
            launch_detached(["bash", "-c", script, "bash", *paths])

    def _on_extract_audio(self, _item: Any, paths: list[str]) -> None:
        """Launch batch MP3 audio extraction."""
        py = find_python_interpreter()
        term = find_terminal_emulator()

        lines = ["set -e", "echo '=== Media Toolbox: Extract Audio (MP3) ==='"]
        for idx, p in enumerate(paths, 1):
            out_p = get_extract_audio_output_path(p)
            lines.append(f"echo {shlex.quote(f'[{idx}/{len(paths)}] Extracting audio {p} -> {out_p}')}")
            cmd = f"{shlex.quote(py)} -m media_toolbox.cli extract-audio {shlex.quote(p)} {shlex.quote(out_p)} --codec mp3"
            lines.append(cmd)
        lines.append("echo ''")
        lines.append("echo '=== Audio Extraction Complete ==='")
        lines.append("if command -v notify-send >/dev/null 2>&1; then notify-send 'Media Toolbox' 'Audio extraction complete'; fi")
        lines.append("read -n 1 -s -r -p 'Press any key to close...'")
        script = "\n".join(lines)

        if term:
            launch_detached(build_terminal_command(term, script, paths))
        else:
            launch_detached(["bash", "-c", script, "bash", *paths])
