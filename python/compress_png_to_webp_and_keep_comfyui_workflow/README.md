# ComfyUI PNG to WebP Compressor (Workflow & Metadata Preserving)

A high-performance, parallelized Python script to batch compress ComfyUI-generated PNG images into WebP format while preserving prompt and workflow graph metadata for nodes like WAS Node Suite and ComfyUI.

---

## 🎯 Purpose & Problem Solved

Standard ComfyUI outputs are uncompressed or losslessly compressed PNG files that can quickly consume gigabytes of disk space. Converting PNGs directly to WebP with typical image tools strips the embedded generation metadata (prompt graph and workflow JSON), breaking the ability to drag-and-drop the resulting images back into ComfyUI or inspect workflow parameters.

This script:
1. **Compresses PNG images to WebP** with configurable lossy/near-lossless quality (saving ~80–90% disk space).
2. **Preserves ComfyUI Metadata** by mapping PNG tEXt chunks (`workflow` and `prompt`) into standard EXIF tags (`ImageDescription` and `Make`) in the WebP output (WAS Node Suite format).
3. **Processes batches in parallel** across all available CPU cores using `concurrent.futures.ProcessPoolExecutor`.

---

## ✨ Features

- ⚡ **Multi-Core Parallel Processing**: Automatically utilizes all available CPU cores to process large image datasets in parallel.
- 💾 **Massive Disk Space Savings**: Reduces file size by ~80% to 90% compared to raw PNG files with virtually no perceptual loss in quality at default quality (90).
- 🏷️ **Metadata Preservation**:
  - `workflow` metadata $\rightarrow$ EXIF `ImageDescription` (`0x010e`) with `"Workflow:<json>"` prefix.
  - `prompt` metadata $\rightarrow$ EXIF `Make` (`0x010f`) with `"Prompt:<json>"` prefix.
  - Fully compatible with WAS Node Suite and loaders expecting EXIF metadata in WebP images.
- 🔄 **Smart Resume & Idempotency**: Checks if `.webp` already exists before processing. Safe to interrupt and resume at any time.
- 🧹 **Auto-Cleanup Option**: Configurable automatic deletion of original PNG files upon successful conversion.

---

## 📋 Requirements

- Python 3.8+
- [Pillow](https://python-pillow.org/) (`Pillow>=10.0.0`)

### Installation

Install dependencies using `pip`:

```bash
pip install -r requirements.txt
```

or directly:

```bash
pip install Pillow
```

---

## ⚙️ Configuration

Open `compress_png_to_webp_and_keep_comfyui_workflow.py` and adjust the configuration variables at the top of the file:

```python
# CONFIGURATION
TARGET_FOLDERS = [
    r"C:\_stability_matrix\Data\Images\Img2Img",
    r"C:\_stability_matrix\Data\Images\Text2Img",
    r"C:\_stability_matrix\Data\Images\Text2ImgGrids"
]
QUALITY = 90             # WebP compression quality (1-100)
DELETE_ORIGINALS = True  # True to delete source PNG files after conversion
MAX_WORKERS = None       # None = use all CPU cores. Set to 4, 8, etc., to limit load
```

### Configuration Options

| Setting | Default | Description |
| :--- | :--- | :--- |
| `TARGET_FOLDERS` | List of paths | List of folder paths to recursively scan for `.png` images (supports Windows & Linux paths). |
| `QUALITY` | `90` | WebP compression quality factor (`1`–`100`). `90` provides high visual fidelity with ~85% reduction. |
| `DELETE_ORIGINALS` | `True` | If `True`, removes the source `.png` file once `.webp` is successfully created. |
| `MAX_WORKERS` | `None` | Number of worker processes. `None` uses all available CPU threads. |

---

## 🚀 Usage

Run the script directly with Python:

```bash
python compress_png_to_webp_and_keep_comfyui_workflow.py
```

### Output Example

```text
Scanning folders...
Found 1420 PNG images. Starting parallel compression...
Progress: 1420/1420...
Done! Processed 1420 images in 18.42 seconds.
Press Enter to exit.
```

---

## 🔍 Metadata Tag Specification

| ComfyUI PNG Property | Target WebP EXIF Tag | Tag ID | Format / Prefix |
| :--- | :--- | :--- | :--- |
| `img.info['workflow']` | `ImageDescription` | `0x010e` | `Workflow:<json_string>` |
| `img.info['prompt']` | `Make` | `0x010f` | `Prompt:<json_string>` |

---

## 📄 License

MIT License. See [LICENSE](../../LICENSE) in repository root for details.
