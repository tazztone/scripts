# Cross-Platform Flat Media Staging

A high-performance utility to recursively scan multi-year photo/video archives, discover event folders (or sync event dates directly from an Immich album), and stage media files as flat **NTFS hardlinks** for streamlined import into **DaVinci Resolve**, **DxO PhotoLab**, **Lightroom**, **LosslessCut**, and other editors on both **Linux** and **Windows 11**.

---

## 🎯 Purpose & Problem Solved

### 🏔️ End-to-End Pipeline & User Story
This tool is the bridge connecting your Immich library curation to professional desktop editing:

```mermaid
flowchart LR
    A["1. Immich GPS Search<br>(Find initial photos)"] --> B["2. album_date_expansion.py<br>(Harvest all unlocated shots on those days)"]
    B --> C["3. stage_media.py<br>(Flat NTFS hardlinks)"]
    C --> D["4. Editors & NLEs<br>(DaVinci Resolve, DxO, LosslessCut)"]
```

> **The Story**:
> When hired to deliver all historical photos and videos of an alpine mountain hut ("Stampf") across multi-year archives (`2018`–`2025`), the visit dates were initially isolated using GPS coordinates in Immich and expanded via [`album_date_expansion.py`](album_date_expansion.md) to gather all non-GPS DSLR, GoPro, and drone shots.
> Because footage was scattered across deeply nested multi-year folders (`2020/2020-12-31_stampf/`, `2021/2021-01-01 stampf/videos/GoPro/`), importing them into DaVinci Resolve or DxO PhotoLab would create dozens of fragmented bins.
> **This tool bridges that gap**: it queries the Immich album for event dates, extracts all master RAW photos and videos for those exact dates, and stages them into flat, chronologically-sorted hardlinks ready for 1-click import.

---

## ⚡ Why Hardlinks? (Universal Editor & Cross-Platform Compatibility)

Instead of proprietary API imports (which only work in one specific editor and fail for photo tools), this utility uses **NTFS Hardlinks (`os.link`)**:

* 🌐 **Universal Filesystem Interface**: Works with **every** editor (DaVinci Resolve, DxO PhotoLab, Lightroom, LosslessCut, Topaz AI, CapCut, Premiere, VLC).
* 🔗 **100% Cross-Platform Native**: Hardlinks are native NTFS MFT directory pointers. Windows 11 (File Explorer, DaVinci Resolve, media players) and Linux see them as standard, real files.
* 💾 **Zero Storage Overhead**: Uses 0 additional bytes of disk space regardless of how many gigabytes or terabytes of footage are staged.
* 🛡️ **Non-Destructive & Safe**: Deleting a staged hardlink (via `--clean` or manual deletion) only removes the directory reference; your original master media files in `_MY PHOTOS and VIDEOS` remain 100% intact.
* 🚀 **Instant Staging**: Thousands of clips stage in less than a second.

---

## 📂 Staging Directories

The tool creates and populates two flat staging folders inside `_RESOLVE_IMPORT_STAGING/`:

| Staging Folder | Filtered File Types | Primary Use Case |
| :--- | :--- | :--- |
| **`photos_raw/`** | `.dng`, `.arw`, `.rw2`, `.cr2`, `.cr3`, `.nef`, `.orf`, `.raf`, `.tif`, `.tiff` *(+ optional `.jpg`/`.heic`)* | Direct batch import into **DxO PhotoLab** or DaVinci Resolve **Photo Album** bin |
| **`videos/`** | `.mp4`, `.mov`, `.mxf`, `.m4v`, `.insv`, `.braw`, `.avi`, `.mkv` | Direct import into **LosslessCut** or DaVinci Resolve **Video Timeline** |

> [!NOTE]
> **Ignored Files:** Sidecars and project files (`.xmp`, `.dop`, `.pp3`, `.rrdata`, `.prproj`, `.aep`, `.psd`, etc.) are automatically excluded during staging.

---

## ✨ Key Features

1. **Direct Immich Album Sync (`--immich-album`)**
   * Automatically queries your Immich server API to fetch all event dates directly from a curated album (e.g. `--immich-album "Stampf"`), eliminating manual date entry.
   * Auto-detects `IMMICH_BASE_URL` and `IMMICH_API_KEY` from the local `.env` file or environment variables.

2. **Dual-OS Auto-Discovery**
   * **On Windows 11**: Automatically scans drive letters (`D:`, `E:`, `F:`, etc.) for `_MY PHOTOS and VIDEOS` and `_RESOLVE_IMPORT_STAGING`.
   * **On Linux**: Auto-detects `/mnt/wd14tb` and `/media/$USER/*`.

3. **Windows NTFS Filename Sanitization**
   * Automatically strips and sanitizes characters forbidden on Windows (`: * ? " < > |`) from event names and subpaths to guarantee valid Windows filenames.

4. **Multi-Tier Safety Guardrails**
   * Prevents accidental cleaning if staging and base directories overlap.
   * `--clean` checks inode link count (`st_nlink > 1`) and only unlinks files inside `photos_raw` and `videos`, refusing to touch single-copy files.

5. **Self-Healing & Idempotent**
   * Automatically detects and removes old broken symlinks or stale links when re-staging.

6. **Collision Avoidance & Chronological Sorting**
   * Generic camera filenames (`C0001.MP4`, `DSC05558.ARW`) are prefixed with their event folder:
     * `2019/2019-07-22/C0001.MP4` $\rightarrow$ `2019-07-22__C0001.MP4`
     * `2021/2021-01-01 stampf/videos/C0028.mov` $\rightarrow$ `2021-01-01 stampf__videos__C0028.mov`
   * Sorting alphabetically in Resolve/DxO automatically arranges clips in chronological order.

---

## 🚀 Quick Start Launchers

### 🐧 Linux / macOS / WSL
```bash
./stage_media.sh
```

### 🪟 Windows 11 (Command Prompt / Explorer)
Double-click `stage_media.bat` or run:
```cmd
stage_media.bat
```

### 💻 Windows 11 (PowerShell / Windows Terminal)
```powershell
.\stage_media.ps1
```

---

## ⚙️ Command-Line Options

```bash
usage: stage_media.py [-h] [--immich-album [NAME_OR_UUID]]
                      [--immich-url IMMICH_URL] [--immich-key IMMICH_KEY]
                      [--clean] [--force] [--open] [--include-jpg]
                      [--mode {all,photos,videos}]
                      [--link-type {hardlink,symlink,copy}]
                      [-n] [--dates DATES [DATES ...]]
                      [--staging-dir STAGING_DIR]
                      [--base-dir BASE_DIR]
```

| Flag | Description |
| :--- | :--- |
| `--immich-album`, `-i` | Fetch event dates automatically from Immich album name or UUID (e.g. `--immich-album "Stampf"`). |
| `--immich-url` | Immich server base URL (default: `http://localhost:2283` or from `.env`). |
| `--immich-key` | Immich API Key (defaults to `IMMICH_API_KEY` from environment or `.env`). |
| `--clean` | Safely removes existing staged links in `photos_raw` and `videos` before staging. |
| `--force` | Forces `--clean` to remove files even if single-link files are detected. |
| `--open` | Opens staging folders in the system file manager (`xdg-open` on Linux, `Explorer` on Windows). |
| `--link-type` | Link strategy: `hardlink` (default), `symlink`, or `copy`. |
| `-n`, `--dry-run` | Preview actions and count matching files without modifying disk. |
| `--include-jpg` | Also stages `.jpg`, `.jpeg`, `.png`, and `.heic` alongside RAW files. |
| `--mode` | Filter media: `all` (default), `photos`, or `videos`. |
| `--dates` | Custom list of event dates (`YYYY-MM-DD`). |
| `--staging-dir` | Custom target staging path (auto-detected by default). |
| `--base-dir` | Custom source archive path (auto-detected by default). |

---

## 💡 Usage Examples

### 1. Sync Directly from Immich Album & Open Folders
```bash
python3 stage_media.py --immich-album "Stampf" --clean --open
```

### 2. Standard Rebuild with Default Archive Dates
```bash
python3 stage_media.py --clean --open
```

### 3. Preview Staging (Dry-Run)
```bash
python3 stage_media.py --dry-run
```

### 4. Stage Videos Only
```bash
python3 stage_media.py --mode videos --clean
```

### 5. Stage Photos (Including JPEGs and HEIC)
```bash
python3 stage_media.py --mode photos --include-jpg --clean
```

---

## 🎬 DaVinci Resolve Import & Multi-Camera Smart Bins Workflow

### Step 1: Ingest into DaVinci Resolve
1. Open **DaVinci Resolve** $\rightarrow$ **Media** page.
2. In the **Media Storage** panel on the left, navigate to `_RESOLVE_IMPORT_STAGING/`.
3. Drag `videos/` and `photos_raw/` into your Master Bin.

---

### Step 2: Organize Mixed Media with Smart Bins
Because multi-year projects mix different cameras (Sony, Panasonic, DJI Drone, GoPro, Phone) and frame rates (24/25/30fps vs 50/60/120fps slow-motion), use **DaVinci Resolve Smart Bins** to automatically bucket footage without manual folder sorting:

In DaVinci Resolve's left panel, right-click **Smart Bins** $\rightarrow$ **Add Smart Bin...**:

#### 🚁 1. Drone & Aerial Footage
* **Rule**: `Clip Name` $\rightarrow$ `contains` $\rightarrow$ `DJI`
* **Timeline Creation**: Right-click the Smart Bin $\rightarrow$ `Create Timeline Using Selected Clips` (*"Drone Highlights"*).

#### ⏱️ 2. High FPS / Slow-Motion B-Roll
* **Rule**: `FPS` $\rightarrow$ `is greater than or equal to` $\rightarrow$ `50`
* **Timeline Creation**: Right-click $\rightarrow$ `Create Timeline Using Selected Clips` (*"Slow Motion Stash"*).

#### 🎬 3. Real-Time 4K / Main Camera
* **Rule**: `Resolution` $\rightarrow$ `is` $\rightarrow$ `3840x2160` **AND** `FPS` $\rightarrow$ `is less than` $\rightarrow$ `50`
* **Timeline Creation**: Main narrative timeline.

#### 📱 4. Vertical Video / Shorts
* **Rule**: `Video Resolution` / `Aspect Ratio` $\rightarrow$ `Portrait` (Height > Width).

#### 📸 5. RAW Photo Sequences & Timelapses
* **Rule**: `File Type` / `Format` $\rightarrow$ `contains` $\rightarrow$ `DNG` or `ARW`
* **Timeline Creation**: Photo slideshow / timelapse compilation.
