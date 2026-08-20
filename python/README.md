# Python Scripts & Utilities

A collection of automation and utility scripts written in Python.

## Directory Index

| Utility | Description | Folder |
| :--- | :--- | :--- |
| **Bitwarden Vault Deduplicator** | Deduplicates entries from Bitwarden JSON exports with smart merging. | [`bitwarden/`](./bitwarden/) |
| **ComfyUI PNG to WebP Compressor** | Batch converts PNGs to WebP while embedding ComfyUI workflow metadata into EXIF. | [`compress_png_to_webp_and_keep_comfyui_workflow/`](./compress_png_to_webp_and_keep_comfyui_workflow/) |
| **Google Drive Duplicate Cleaner** | Scans Google Drive for duplicate files by MD5 checksum and moves duplicates to trash. | [`google_drive_remove_duplicates/`](./google_drive_remove_duplicates/) |
| **Immich API Tools** | Automate timelapse/burst stacking, unstacking, album date expansion, and DaVinci Resolve media staging. | [`immich-api/`](./immich-api/) |
| **Immich Desktop Launcher** | Desktop launcher and installer script for Immich web app on Linux. | [`immich-launcher/`](./immich-launcher/) |
| **LoRA TE Weight Remover** | Strips text encoder weights from SDXL/FLUX `.safetensors` LoRA files to reduce file size. | [`lora_remove_te_weights/`](./lora_remove_te_weights/) |
| **File Organizer by Extension** | Organizes loose files into folders named by extension and groups them into categories. | [`put_files_into_folder_by_extension/`](./put_files_into_folder_by_extension/) |
| **RAW/JPEG Cleaner** | Scans photo libraries and removes camera-generated JPEGs if matching RAW files exist. | [`remove_jpg_if_raw_exists/`](./remove_jpg_if_raw_exists/) |

## Running Tests

You can run the full Python test suite with the bundled runner:

```bash
python3 run_tests.py
```

Or using `pytest`:

```bash
pytest python/
```