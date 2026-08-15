# Stampf Media Staging for DaVinci Resolve

A high-performance utility to recursively scan multi-year photo/video archives, discover event folders, and stage media files as flat symlinks for streamlined import into **DaVinci Resolve** photo albums and video timelines.

---

## 🎯 Purpose & Problem Solved

When managing event media across many years (`2018`–`2026`), folders are often deeply nested (e.g. `2020/2020-12-31_stampf/`, `2021/2021-01-01 stampf/videos/`).

* **In DaVinci Resolve**, importing nested folders creates fragmented bins that cannot easily be dragged into a continuous photo album or video timeline.
* **This tool** recursively extracts all RAW/DNG photos and video files from target event dates and symlinks them into **two flat staging directories**, preserving chronological order and preventing filename collisions.

---

## 📂 Staging Directories

The tool creates and populates two flat staging folders inside `/mnt/wd14tb/_RESOLVE_IMPORT_STAGING/`:

| Staging Folder | Filtered File Types | Primary Use Case |
| :--- | :--- | :--- |
| **`photos_raw/`** | `.dng`, `.arw`, `.rw2`, `.cr2`, `.cr3`, `.nef`, `.orf`, `.raf`, `.tif`, `.tiff` *(+ optional `.jpg`/`.heic`)* | Drag-and-drop directly into a single **Photo Album** bin / timeline |
| **`videos/`** | `.mp4`, `.mov`, `.mxf`, `.m4v`, `.insv`, `.braw`, `.avi`, `.mkv` | Drag-and-drop directly into your **Video Timeline** |

> [!NOTE]
> **Ignored Files:** Sidecars and project files (`.xmp`, `.dop`, `.pp3`, `.rrdata`, `.prproj`, `.aep`, `.psd`, etc.) are automatically excluded.

---

## ✨ Key Features

1. **Zero Duplication (Symlink-Based)**
   * Operations are instant and consume negligible disk space.
   * Modifying metadata or exporting to source in Resolve resolves directly to the actual files on disk.

2. **Collision Avoidance & Chronological Sorting**
   * Generic camera filenames like `C0001.MP4` or `DSC05558.ARW` are prefixed with their source folder:
     * `2019/2019-07-22/C0001.MP4` $\rightarrow$ `2019-07-22__C0001.MP4`
     * `2021/2021-01-01 stampf/videos/C0028 Render 1.mov` $\rightarrow$ `2021-01-01 stampf__videos__C0028 Render 1.mov`
   * Sorting alphabetically in Resolve automatically sorts everything in perfect chronological order.

3. **Year-Aware Discovery**
   * Automatically resolves dates within year-partitioned directories (`/mnt/wd14tb/_MY PHOTOS and VIDEOS/<YYYY>/<date>*`) and handles naming suffixes (e.g. `_stampf`).

4. **100% Non-Destructive**
   * The source archive is strictly **read-only**.
   * The `--clean` flag checks `item.is_symlink()` and only unlinks symlinks inside the staging directory.

---

## 🚀 Quick Start

### Option 1: Using the Bash Launcher (Recommended)
Runs the Python script with `--clean` (removes old symlinks) and `--open` (opens staging folders in your file manager):
```bash
cd /home/tazztone/_coding/scripts/python/stage_stampf_media
./stage_stampf_media.sh
```

### Option 2: Running via Python
```bash
python3 stage_stampf_media.py [OPTIONS]
```

---

## ⚙️ Command-Line Options

```bash
usage: stage_stampf_media.py [-h] [--clean] [--open] [--include-jpg]
                            [--mode {all,photos,videos}]
                            [--dates DATES [DATES ...]]
                            [--staging-dir STAGING_DIR]
                            [--base-dir BASE_DIR]
```

| Flag | Description |
| :--- | :--- |
| `--clean` | Removes existing symlinks in staging folders before rebuilding. |
| `--open` | Opens staging folders in the system file manager (`xdg-open` / `nautilus`). |
| `--include-jpg` | Also stages `.jpg`, `.jpeg`, `.png`, and `.heic` alongside RAW files. |
| `--mode {all,photos,videos}` | Select whether to stage both media types, photos only, or videos only (default: `all`). |
| `--dates D1 D2 ...` | Provide a custom list of date strings (e.g. `--dates 2023-05-28 2024-03-29`). |
| `--staging-dir PATH` | Custom target staging path (default: `/mnt/wd14tb/_RESOLVE_IMPORT_STAGING`). |
| `--base-dir PATH` | Custom source archive path (default: `/mnt/wd14tb/_MY PHOTOS and VIDEOS`). |

---

## 💡 Usage Examples

### 1. Standard Rebuild & Open
```bash
python3 stage_stampf_media.py --clean --open
```

### 2. Stage Only Video Files
```bash
python3 stage_stampf_media.py --mode videos --clean
```

### 3. Stage Photos (Including JPEGs and HEIC)
```bash
python3 stage_stampf_media.py --mode photos --include-jpg --clean
```

### 4. Stage Specific Event Dates
```bash
python3 stage_stampf_media.py --dates 2023-05-28 2024-03-28 2024-03-29 2024-03-30 --clean
```

---

## 🎬 DaVinci Resolve Import Workflow

1. Open **DaVinci Resolve** $\rightarrow$ Navigate to the **Media** page.
2. In the **Media Storage** panel on the left, locate:
   ```
   /mnt/wd14tb/_RESOLVE_IMPORT_STAGING
   ```
3. **For Photos**:
   * Open `photos_raw/` $\rightarrow$ Select all files $\rightarrow$ Drag into your **Photo Album Bin** or Timeline.
4. **For Videos**:
   * Open `videos/` $\rightarrow$ Select all files $\rightarrow$ Drag into your **Video Bin** or Timeline.
