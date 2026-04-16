# remove_jpg_if_raw_exists

A professional-grade Python 3 script that deletes (or safely moves) JPEG files when a matching RAW photo file exists in the same folder. Unlike a simple filename matcher, this tool uses **EXIF-based safety logic** to distinguish between camera-original sidecars and your edited exports.

---

## Features

- **EXIF Safety Layer**: Only deletes JPEGs that look like direct camera outputs (Sony, Canon, Nikon, Fuji, Panasonic, etc.).
- **Editor Protection**: Automatically identifies and keeps files re-encoded by Lightroom, Photoshop, Capture One, RapidRAW, and others.
- **Recursive Scan**: Deep-scans your entire library tree.
- **Dry-run Mode**: Preview exactly what will happen without touching a single file.
- **Trash Mode**: Move matched JPEGs to a mirrored folder instead of hard-deleting.
- **Dual Logging**: Clean, scannable terminal output for humans; full timestamped audit logs for the record.
- **Broad Camera Support**: Detects camera originals from 100+ manufacturer families via MakerNote signatures.

---

## Requirements

- [uv](https://docs.astral.sh/uv/) (recommended for automatic dependency management)
- Python 3.10+
- Dependencies: `exifread` (managed automatically via `uv` PEP 723 inline metadata)

---

## Usage

With `uv` installed, run directly without environment setup:
```bash
uv run remove_jpg_if_raw_exists.py <directory> [options]
```

example command:
`uv run remove_jpg_if_raw_exists.py "/mnt/wd14tb/_MY PHOTOS and VIDEOS/2026" --log remove_2026.log`


### Options

| Flag | Description |
|---|---|
| `--dry-run` | Preview additions — no files are deleted. |
| `--trash DIR` | Move matched JPEGs to `DIR` instead of deleting. |
| `--log FILE` | Write a high-fidelity audit log with timestamps to `FILE`. |
| `--workers N` | Number of parallel threads (default: `4`). Use `2` for HDDs, `8+` for SSDs. |
| `--skip-exif` | ⚠ **Safety override**: Reverts to filename-only matching. Use with caution. |
| `--verbose` | Shows all skipped files and detailed EXIF reasoning. |
| `--min-raw-size N` | Minimum RAW file size in bytes (default: 100 KB). |

---

## Safety Architecture

To prevent accidental data loss, the script passes every JPEG through a three-stage verification:

1.  **Software Signature**: Checks for known "export" headers (Adobe, Capture One, etc.).
2.  **JFIF Header**: Detects if the file has been re-encoded by processing software.
3.  **MakerNotes Presence**: Verifies the presence of proprietary camera metadata (Sony, Panasonic, Nikon, etc.) which is typically stripped by editors.

---

## Examples

**Start with a dry run and verbose reasoning:**
```bash
uv run remove_jpg_if_raw_exists.py /Photos/2026 --dry-run --verbose
```

**Safe mode — move to trash with a persistent log:**
```bash
uv run remove_jpg_if_raw_exists.py /Photos/2024 \
    --trash ~/Desktop/photo-trash \
    --log cleanup.log
```

---

## Supported RAW Formats

`.dng` `.cr2` `.cr3` `.nef` `.arw` `.orf` `.raf` `.rw2` `.pef` `.srw`

Extensions can be customized by editing the `RAW_EXTENSIONS` set in the script.

---

## License

MIT