# Media Toolbox

Modern Python media inspection, transcoding, and audio extraction package replacing legacy Bash/Zenity scripts. Built with a decoupled headless core, a dynamic Libadwaita / GTK4 desktop interface, and dual GNOME Nautilus integrations.

## Features

- **Decoupled Headless Core (`core/`)**:
  - Strongly typed `ffprobe` JSON parsing (`probe.py`) into frozen dataclasses (`models.py`).
  - Container-aware bitrate calculator (`bitrate.py`) reserving muxing margins and clamping to min 64 kbps.
  - Deterministic FFmpeg CLI builder (`builder.py`) supporting 10 codec presets (H.264, H.265, AV1, VP9, GIF, ProRes, MP3, AAC, Opus, FLAC).
  - Video & audio filter chaining (`filtergraph.py`) with automatic `atempo` multiplier splitting (>2.0x, <0.5x).
  - Real-time `-progress pipe:1` subprocess runner (`runner.py`) with process group isolation and cancellation.
  - Zero GUI dependencies in `core/` for reliable headless CI/server execution.

- **Dynamic Libadwaita Desktop GUI (`ui/`)**:
  - Dynamic forms with revealers (conditionally showing CRF quality slider vs 2-pass target size, custom resolutions).
  - Non-blocking background worker thread streaming progress to `Gtk.ProgressBar` via `GLib.idle_add`.
  - Graceful cancellation support (`SIGTERM` / `SIGKILL`).

- **Dual Nautilus Integration (`nautilus/`)**:
  - Zero-privilege user script: `~/.local/share/nautilus/scripts/Media-Toolbox`.
  - Native python-nautilus extension: `~/.local/share/nautilus-python/extensions/media_toolbox.py` with MIME-type filtering.
  - One-click installer and status checker CLI.

## Quick Start

### CLI

```bash
# Inspect media metadata
python3 -m media_toolbox.cli inspect video.mp4

# Transcode using preset
python3 -m media_toolbox.cli transcode video.mp4 --preset discord-h264 -o output.mp4

# 2-Pass target size transcode
python3 -m media_toolbox.cli transcode video.mp4 --target-mb 25 -o output.mp4

# Extract audio
python3 -m media_toolbox.cli extract-audio video.mp4 -o audio.mp3
```

### Desktop GUI

```bash
python3 -m media_toolbox.ui video.mp4
```

### Nautilus Integration

```bash
# Install Nautilus script, python-nautilus extension, and desktop entry
python3 -m media_toolbox.cli install-nautilus

# Check installation status
python3 -m media_toolbox.cli status-nautilus

# Uninstall integration
python3 -m media_toolbox.cli uninstall-nautilus
```

## Running Tests

```bash
.venv/bin/pytest python/media_toolbox/tests/
```
