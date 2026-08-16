# Stampf Media Staging for DaVinci Resolve (Cross-Platform)

A high-performance utility to recursively scan multi-year photo/video archives, discover event folders, and stage media files as flat **NTFS hardlinks** for streamlined import into **DaVinci Resolve** photo albums and video timelines on both **Linux** and **Windows 11**.

---

## 🎯 Purpose & Problem Solved

### 🏔️ End-to-End Pipeline & User Story
This tool is the second phase of a multi-stage archival workflow:

```mermaid
flowchart LR
    A["1. Immich GPS Search<br>(Find initial hut photos)"] --> B["2. Immich Date Expansion<br>(Harvest all unlocated shots on those days)"]
    B --> C["3. Stampf Media Staging<br>(Flat NTFS hardlinks)"]
    C --> D["4. DaVinci Resolve<br>(1-Click Timeline & Album Import)"]
```

> **The Story**:
> When hired to deliver all historical photos and videos of an alpine mountain hut ("Stampf") across multi-year archives (`2018`–`2025`), the visit dates were initially isolated using GPS coordinates in Immich and expanded via [`album_date_expansion.py`](../immich-api/album_date_expansion.md) to gather all non-GPS DSLR, GoPro, and drone shots.
> Because footage was scattered across deeply nested multi-year folders (`2020/2020-12-31_stampf/`, `2021/2021-01-01 stampf/videos/GoPro/`), importing them into DaVinci Resolve would create dozens of fragmented bins.
> **This tool bridges that gap**: it extracts all RAW photos and videos for those exact dates into flat, chronologically-sorted hardlinks ready for 1-click import into DaVinci Resolve.


---

## ⚡ Why Hardlinks? (Linux & Windows 11 Compatibility)

Older versions used Linux symlinks, which broke when opening the drive on Windows 11 due to POSIX path structures (`/mnt/...`) and Unix symlink reparse tags.

This utility uses **NTFS Hardlinks (`os.link`)**:
* 🔗 **100% Cross-Platform Native**: Hardlinks are native NTFS MFT directory pointers. Windows 11 (File Explorer, DaVinci Resolve, media players) and Linux see them as standard, real files.
* 💾 **Zero Storage Overhead**: Uses 0 additional bytes of disk space regardless of how many gigabytes or terabytes of footage are staged.
* 🛡️ **Non-Destructive & Safe**: Deleting a staged hardlink (via `--clean` or manual deletion) only removes the directory reference; your original media files in `_MY PHOTOS and VIDEOS` remain 100% intact.
* 🚀 **Instant Staging**: Thousands of clips stage in less than a second.

---

## 📂 Staging Directories

The tool creates and populates two flat staging folders inside `_RESOLVE_IMPORT_STAGING/`:

| Staging Folder | Filtered File Types | Primary Use Case |
| :--- | :--- | :--- |
| **`photos_raw/`** | `.dng`, `.arw`, `.rw2`, `.cr2`, `.cr3`, `.nef`, `.orf`, `.raf`, `.tif`, `.tiff` *(+ optional `.jpg`/`.heic`)* | Drag-and-drop directly into a single **Photo Album** bin / timeline |
| **`videos/`** | `.mp4`, `.mov`, `.mxf`, `.m4v`, `.insv`, `.braw`, `.avi`, `.mkv` | Drag-and-drop directly into your **Video Timeline** |

> [!NOTE]
> **Ignored Files:** Sidecars and project files (`.xmp`, `.dop`, `.pp3`, `.rrdata`, `.prproj`, `.aep`, `.psd`, etc.) are automatically excluded.

---

## ✨ Key Features

1. **Dual-OS Auto-Discovery**
   * **On Windows 11**: Automatically scans drive letters (`D:`, `E:`, `F:`, etc.) for `_MY PHOTOS and VIDEOS` and `_RESOLVE_IMPORT_STAGING`.
   * **On Linux**: Auto-detects `/mnt/wd14tb` and `/media/$USER/*`.
   * Also configurable via `STAMPF_BASE_DIR` and `STAMPF_STAGING_DIR` environment variables or CLI flags.

2. **Windows NTFS Filename Sanitization**
   * Automatically strips and sanitizes characters forbidden on Windows (`: * ? " < > |`) from event names and subpaths to guarantee valid Windows filenames.

3. **Multi-Tier Safety Guardrails**
   * Prevents accidental cleaning if staging and base directories overlap.
   * `--clean` checks inode link count (`st_nlink > 1`) and only unlinks files inside `photos_raw` and `videos`, refusing to touch single-copy files.

4. **Self-Healing & Idempotent**
   * Automatically detects and removes old broken symlinks or stale links when re-staging.

5. **Collision Avoidance & Chronological Sorting**
   * Generic camera filenames (`C0001.MP4`, `DSC05558.ARW`) are prefixed with their event folder:
     * `2019/2019-07-22/C0001.MP4` $\rightarrow$ `2019-07-22__C0001.MP4`
     * `2021/2021-01-01 stampf/videos/C0028.mov` $\rightarrow$ `2021-01-01 stampf__videos__C0028.mov`
   * Sorting alphabetically in Resolve automatically arranges clips in chronological order.

---

## 🚀 Quick Start Launchers

### 🐧 Linux / macOS / WSL
```bash
cd /home/tazztone/_coding/scripts/python/stage_stampf_media
./stage_stampf_media.sh
```

### 🪟 Windows 11 (Command Prompt / Explorer)
Double-click `stage_stampf_media.bat` or run:
```cmd
stage_stampf_media.bat
```

### 💻 Windows 11 (PowerShell / Windows Terminal)
```powershell
.\stage_stampf_media.ps1
```

---

## ⚙️ Command-Line Options

```bash
usage: stage_stampf_media.py [-h] [--clean] [--force] [--open] [--include-jpg]
                             [--mode {all,photos,videos}]
                             [--link-type {hardlink,symlink,copy}]
                             [-n] [--dates DATES [DATES ...]]
                             [--staging-dir STAGING_DIR]
                             [--base-dir BASE_DIR]
```

| Flag | Description |
| :--- | :--- |
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

### 1. Standard Rebuild & Open
```bash
python3 stage_stampf_media.py --clean --open
```

### 2. Preview Staging (Dry-Run)
```bash
python3 stage_stampf_media.py --dry-run
```

### 3. Stage Videos Only
```bash
python3 stage_stampf_media.py --mode videos --clean
```

### 4. Stage Photos (Including JPEGs and HEIC)
```bash
python3 stage_stampf_media.py --mode photos --include-jpg --clean
```

### 5. Stage Specific Event Dates
```bash
python3 stage_stampf_media.py --dates 2023-05-28 2024-03-28 2024-03-29 2024-03-30 --clean
```

---

## 🎬 DaVinci Resolve Import Workflow

1. Open **DaVinci Resolve** (on Linux or Windows 11).
2. Go to the **Media** page $\rightarrow$ in the **Media Storage** panel on the left, navigate to:
   * **Linux**: `/mnt/wd14tb/_RESOLVE_IMPORT_STAGING/`
   * **Windows 11**: `D:\_RESOLVE_IMPORT_STAGING\` (or your drive letter).
3. **Photos**: Open `photos_raw/` $\rightarrow$ Select all files $\rightarrow$ Drag into your **Photo Album Bin** or Timeline.
4. **Videos**: Open `videos/` $\rightarrow$ Select all files $\rightarrow$ Drag into your **Video Bin** or Timeline.
