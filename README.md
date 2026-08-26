# Scripts

[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)](#)

A unified collection of automation scripts and utilities for Windows, Linux, and Python. Covers media processing, file organization, AI/ML tooling, cloud utilities, and browser userscripts.

## Structure

```
scripts/
├── bat/                            # Windows Batch scripts
│   ├── exiftool_copy_and_organize_by_date.bat
│   ├── exiftool_rotate_mp4_270deg.bat
│   ├── windows_create_txt_for_each_png.bat
│   ├── windows_move_each_file_to_own_folder.bat
│   ├── windows_organize_files_by_extension.bat
│   └── windows_organize_images_by_date.bat
├── sh/                             # Bash scripts (Linux / macOS)
│   ├── TOOLBOXES/                  # Interactive FFmpeg & ImageMagick toolboxes
│   ├── antigravity2/               # Antigravity 2.0 environment and profile setup
│   ├── davinci-resolve-updater/    # DaVinci Resolve automated Linux updater
│   ├── immich/                     # Immich container and service updates
│   ├── opencode-desktop/           # OpenCode desktop application installer
│   ├── tarball-installer/          # Universal tarball archive installer
│   └── the-finals/                 # THE FINALS game & OBS Studio automation
├── python/                         # Python utilities
│   ├── bitwarden/                  # Bitwarden vault duplicate record cleaner
│   ├── compress_png_to_webp_and_keep_comfyui_workflow/  # ComfyUI PNG to WebP compressor with workflow preservation
│   ├── google_drive_remove_duplicates/  # Google Drive duplicate file scanner + remover
│   ├── immich-api/                 # Immich API utilities (timelapse stacking, unstacking, album expansion, staging)
│   ├── immich-launcher/            # Linux desktop launcher & installer for Immich
│   ├── lora_remove_te_weights/     # Strip text encoder weights from LoRA .safetensors
│   ├── put_files_into_folder_by_extension/  # Auto-organizer: sort files into folders by extension & category
│   └── remove_jpg_if_raw_exists/   # Remove camera JPEGs if matching RAW photo exists
└── userscripts/                    # Browser userscripts (Violentmonkey / Tampermonkey)
    ├── fastlog-watcher/            # Real-time event and log stream monitor
    ├── huggingface/                # Hugging Face inline liking, unliked highlighter, date & negative filter
    ├── perplexity/                 # Perplexity model lock, approvals, and GitHub enhancements
    └── toppreise/                  # Toppreise.ch Suite: best price highlight, negative & category filters, price alarm
```

## Highlights

### `sh/` — Linux & macOS Utilities
- **Toolboxes (`sh/TOOLBOXES/`)** — Interactive Zenity & CLI suites for FFmpeg media conversion, lossless cutting, remuxing, and ImageMagick batch image operations.
- **DaVinci Resolve Updater** — Download and update DaVinci Resolve on Linux distributions.
- **Immich Update & Installer** — Automated updater and launcher scripts for Immich self-hosted photo servers.
- **THE FINALS & OBS Automation** — Automated game launch and OBS Replay Buffer management with Wayland PipeWire window capture and cleanup.
- **Antigravity 2.0 Profile Setup** — Setup scripts for development environment profiles.

### `bat/` — Windows Batch
- File organization by file extension and EXIF creation date.
- ExifTool wrappers for lossless MP4 rotation and batch metadata date organization.
- Batch file restructuring and sidecar `.txt` metadata file creation.

### `python/` — Python Utilities
- **ComfyUI PNG to WebP Compressor** — Parallel batch conversion of PNGs to WebP while mapping workflow and prompt graphs into EXIF tags.
- **Google Drive Dedup** — Scan Google Drive for duplicate files by MD5 checksum and optionally move them to trash.
- **LoRA TE Weight Remover** — Strip text encoder weights from `.safetensors` LoRA models to reduce size for SDXL and FLUX.
- **Extension-based File Organizer** — Categorize and organize directory files into folder trees by file extension.
- **Immich API Tools** — Stacking and unstacking of timelapses/bursts, album date expansion, and DaVinci Resolve staging.
- **Bitwarden Deduplicator** — Deduplicate export JSON vaults while preserving custom fields, URIs, and passwords.
- **RAW/JPEG Cleaner** — Clean up camera-generated JPEG duplicates when higher quality RAW files exist.

### `userscripts/` — Browser Userscripts
- **Hugging Face Enhancements** — Inline model liking/unliking, unliked model card highlighter, date range slider filter, and keyword blocklist.
- **Perplexity Enhancements** — Locks preferred AI model, auto-accepts agent approvals, and enables GitHub integration across SPAs.
- **Toppreise.ch Suite** — Best price highlight, 1-click card category quick-block, hierarchical exclusions, and offer count sorting.

## Usage & Documentation

Each subdirectory contains its own documentation:

- Bash scripts: [`sh/TOOLBOXES/README.md`](sh/TOOLBOXES/README.md), [`sh/antigravity2/README.md`](sh/antigravity2/README.md), [`sh/davinci-resolve-updater/README.md`](sh/davinci-resolve-updater/README.md), [`sh/immich/README.md`](sh/immich/README.md), [`sh/tarball-installer/README.md`](sh/tarball-installer/README.md), [`sh/the-finals/README.md`](sh/the-finals/README.md)
- Python utilities: [`python/README.md`](python/README.md)
- Windows Batch: [`bat/README.md`](bat/README.md)
- Userscripts: [`userscripts/README.md`](userscripts/README.md)

### Running Tests

Run the test suite from the repository root using the workspace virtualenv:

```bash
# Run all tests (Python & Userscripts)
userscripts/venv/bin/pytest

# Run only Python tests
userscripts/venv/bin/pytest python

# Run only Userscript browser tests
userscripts/venv/bin/pytest userscripts
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
