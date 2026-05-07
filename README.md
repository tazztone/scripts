# Scripts

[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)](#)

A unified collection of automation scripts and utilities for Windows, Linux, and Python. Covers media processing, file organization, AI/ML tooling, and cloud utilities.

## Structure

```
scripts/
├── bat/                            # Windows Batch scripts
│   ├── file_organizer.bat          # File sorting by extension / date
│   └── media_tools.bat             # FFmpeg wrappers for batch media tasks
├── sh/                             # Bash scripts (Linux / macOS)
│   ├── universal_toolbox.sh        # Universal utility menu
│   ├── imagemagick_toolbox.sh      # ImageMagick batch operations
│   └── lossless_ops_toolbox.sh     # Lossless media conversion and processing
└── python/                         # Python utilities
    ├── google_drive_remove_duplicates/  # Google Drive duplicate file scanner + remover
    ├── lora_remove_te_weights/          # Strip TE (text encoder) weights from LoRA .safetensors
    └── put_files_into_folder_by_extension/  # Auto-organizer: sort files into folders by extension
```

## Highlights

### `sh/` — Bash Toolboxes
- **Universal Toolbox** — interactive menu-driven script for common sysadmin and media tasks
- **ImageMagick Toolbox** — batch resize, convert, strip metadata, watermark
- **Lossless Ops Toolbox** — lossless video/audio operations via FFmpeg (remux, trim, concat)

### `bat/` — Windows Batch
- File organization by extension and date
- FFmpeg-based batch media processing wrappers

### `python/` — Python Utilities
- **Google Drive Dedup** — authenticate via OAuth, scan for duplicate files by hash, prompt for removal
- **LoRA TE Weight Remover** — strip text encoder weights from `.safetensors` LoRA models (reduce file size for SDXL/FLUX)
- **Extension-based File Organizer** — auto-sorts a flat directory into sub-folders by file extension

## Usage

Each subdirectory contains its own `README.md` with specific requirements and usage instructions:

- Bash scripts: [`sh/README.md`](sh/README.md)
- Python utilities: [`python/README.md`](python/README.md)
- Windows Batch: [`bat/README.md`](bat/README.md)

### Quick examples

```bash
# Run the universal bash toolbox
bash sh/universal_toolbox.sh

# Organize files by extension (Python)
python python/put_files_into_folder_by_extension/organizer.py /path/to/folder

# Strip TE weights from a LoRA
python python/lora_remove_te_weights/remove_te.py model.safetensors
```

## License

MIT — see [LICENSE](LICENSE).
