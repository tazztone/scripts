# remove_jpg_if_raw_exists

A Python 3 script that deletes (or safely moves) JPEG files when a matching
RAW photo file exists in the same folder. Useful for cleaning up dual
RAW+JPEG shoots after you've confirmed the RAWs are intact.

---

## Features

- Recursive scan of any directory tree
- Dry-run mode — preview everything before touching a single file
- Trash mode — move matched JPEGs to a mirrored folder instead of hard-deleting
- Minimum RAW size guard — ignores zero-byte or stub RAW files
- Per-file error handling — one locked file won't abort the whole run
- Persistent log file support
- Clean CLI interface — no code editing required

---

## Requirements

- [uv](https://docs.astral.sh/uv/) (recommended for automatic dependency management)
- Python 3.10 or newer
- Dependencies: `exifread` (automatically handled by `uv`)

---

## Supported RAW Formats

`.dng` `.cr2` `.cr3` `.nef` `.arw` `.orf` `.raf` `.rw2` `.pef` `.srw`

Add or remove extensions by editing the `RAW_EXTENSIONS` set at the top of
the script.

---

## Usage

With `uv` installed, you can run the script directly:
```bash
uv run remove_jpg_if_raw_exists.py <directory> [options]
```

Or make it executable and run it directly:
```bash
chmod +x remove_jpg_if_raw_exists.py
./remove_jpg_if_raw_exists.py <directory> [options]
```

### Options

| Flag | Description |
|---|---|
| `--dry-run` | Preview which JPEGs would be removed — no files are touched |
| `--trash DIR` | Move matched JPEGs to `DIR` instead of deleting permanently |
| `--log FILE` | Write a full audit log to `FILE` |
| `--min-raw-size N` | Minimum RAW file size in bytes to be considered valid (default: `100000`) |
| `--verbose` | Log every file skipped due to missing RAW counterpart |

---

## Examples

**Always start with a dry run:**
```bash
uv run remove_jpg_if_raw_exists.py /Volumes/Photos/2024 --dry-run
```

**Safe mode — move to trash with a log:**
```bash
uv run remove_jpg_if_raw_exists.py /Volumes/Photos/2024 \
    --trash ~/Desktop/photo-trash \
    --log cleanup.log
```

**Hard delete (only after verifying the dry run):**
```bash
uv run remove_jpg_if_raw_exists.py /Volumes/Photos/2024 --log cleanup.log
```

---

## How It Works

For each subdirectory in the tree, the script:

1. Builds a map of `lowercase stem → Path` for every valid RAW file found
2. Iterates over JPEG files in the same directory
3. If a JPEG's stem matches a RAW stem (case-insensitive), it is removed or
   moved depending on the chosen mode
4. Files with no RAW counterpart are left untouched

A RAW file is considered **valid** only if its size is ≥ `--min-raw-size`
(default 100 KB). This prevents an empty or corrupted RAW stub from
accidentally triggering deletion of the JPEG.

---

## Safety Notes

- **Dry run first.** Always use `--dry-run` before any real deletion.
- **Trash mode is recommended** for the first real run. It mirrors the folder
  structure inside the trash directory, making recovery straightforward.
- The trash directory must be **outside** the scan directory to avoid
  recursive loops.
- The script matches files **by stem only** — `IMG_1234.jpg` is matched by
  `IMG_1234.cr3` regardless of case.
- **Metadata Protection**: Syncing ratings or simple metadata in Lightroom Classic (which preserves MakerNotes) will *not* trigger the editor-export detection. The script is designed to only protect files that have been re-encoded or stripped of camera-specific metadata.

---

## License

MIT