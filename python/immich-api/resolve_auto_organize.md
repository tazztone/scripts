# DaVinci Resolve Automated Media Organizer & Color Grading Prep

A standalone Python automation tool for **DaVinci Resolve Studio** to automatically probe staged video files using a 3-tier deep metadata engine (container EXIF tags, stream properties, hardware models, and codec signatures), organize clips into structured Media Pool Bins, assign distinct Clip Colors, add CST (Color Space Transform) starting grade markers, and auto-generate dedicated Timelines with **strict unmixed resolutions, native canvas geometry, and framerate segregation**.

---

## 🎯 Purpose & Problem Solved

When editing multi-year documentary, archival, or event projects, footage comes from dozens of different devices:
* **DJI Drones** (4K 60fps / 10-bit D-Log M / D-Cinelike)
* **Sony Alpha / FX** (4K 25fps real-time vs 100fps slow-motion XAVC)
* **Panasonic Lumix** (10-bit V-Log)
* **Smartphones & Mobile** (240fps slow-mo bursts & vertical reels)
* **5.4K Drone Timelapses & 4:3 Photo Sensor Hyperlapses**

Importing these mixed formats into a single timeline creates color management and framing chaos:
* **Pillarboxing/Letterboxing**: Mixing 4:3 sensor timelapses or vertical 9:16 reels on a standard 16:9 timeline leaves black borders.
* **Cadence Judder**: Mixing 100fps/240fps high-framerate bursts with 25fps real-time footage forces unwanted speed/interpolation conforming.
* **Color Space Mismatches**: Log, Rec.709, and D-Cinelike profiles require completely different input color space transforms.

**`resolve_auto_organize.py`** automates the entire ingestion and color prep pipeline:
1. **⚡ Fast Parallel Metadata Engine**: Probes 250+ video containers in under 2 seconds across CPU cores.
2. **📐 Strict Unmixed Resolution & Geometry**: Strictly separates 5.4K, 4K UHD, 1080p FHD, 720p HD, 4:3 photo-timelapses, and vertical reels into their own bins.
3. **⏱️ Framerate Segregation**: Isolates 24/25/30fps real-time clips from 50/60/100/240fps slow-motion bursts.
4. **🎨 Color Page Ready**: Color-codes clips (Orange for DJI, Teal for Sony, Yellow for Panasonic, Purple for Mobile, Blue for Timelapses) and embeds CST starting grade markers on Frame 0.
5. **🎬 Dedicated Timelines with Native Settings**: Automatically creates timelines with native pixel dimensions (`useCustomSettings=1`) so vertical reels open vertically and 5.4K clips play at full raster.
6. **🔄 Idempotent Re-runs**: Safely re-run anytime; skips already-imported assets and reuses existing timelines without creating duplicate `clip_1` files.

---

## 🔬 3-Tier Deep Metadata Engine

| Camera / Device | Hardware & Container Tags | Detected Profile / Bit-Depth | Clip Color | Target Media Pool Bin |
| :--- | :--- | :--- | :--- | :--- |
| **DJI Drone** | `Model: FC6310`, `Handler: .DJI.Meta` | D-Cinelike / D-Log M (8/10-bit) | `Orange` | `📁 DJI_DJI_Drone_{Res}_{FPS}` |
| **Sony Alpha (XAVC)** | `Brand: XAVC`, `Model: ILCE-*` | S-Cinetone / S-Log3 (8/10-bit) | `Teal` | `📁 Sony_Alpha__FX_XAVC_{Res}_{FPS}` |
| **Panasonic Lumix** | `Make: Panasonic`, `Handler: Static Metadata` | V-Log / Standard (10-bit) | `Yellow` | `📁 Panasonic_Lumix_{Res}_{FPS}` |
| **Smartphone / Mobile** | `AndroidVersion`, `Apple iPhone` | Rec.709 / sRGB (8-bit, 240fps) | `Purple` | `📁 Mobile_Smartphone_{Res}_{FPS}` |
| **Timelapses** | `*TL*`, `hyperlapse`, 5.4K, 4:3, Vertical | Rec.709 / sRGB (10-bit) | `Blue` | `📁 Timelapse_Timelapse_{Res}_{FPS}` |
| **Renders / Exports** | `Software: Adobe/DaVinci` | Master Rec.709 | `Navy` | `📁 Render_Exported_Render_{Res}_{FPS}` |

---

## 🚀 Usage

### 1. Preview Metadata in Standalone Mode (`--scan-only`)
Inspect all video files in parallel and print a formatted technical breakdown table without connecting to Resolve:

```bash
python3 resolve_auto_organize.py --scan-only
```

### 2. Auto-Organize Active DaVinci Resolve Project
With **DaVinci Resolve Studio** open and a project loaded:

```bash
python3 resolve_auto_organize.py
```

This will:
* Connect to your active Resolve project.
* Import all staged clips into structured sub-bins under `Staged_Clips_By_Camera/`.
* Assign Clip Colors and add CST starting grade markers to every clip.
* Generate matching Timelines (e.g. `TL - DJI DJI Drone (4K_UHD_3840x2160 30fps)`, `TL - Sony Alpha / FX (XAVC) (1080p_FHD 100fps_SlowMo)`).
* Configure native resolution settings on each timeline (`useCustomSettings=1`).
* Automatically switch Resolve to the **Color Page**.

### 3. Custom Staging Directory
```bash
python3 resolve_auto_organize.py --staging-dir "/path/to/custom/staging/videos"
```

### 4. Skip Timeline Creation (Bins & Colors Only)
```bash
python3 resolve_auto_organize.py --no-timelines
```

### 5. Adjust Parallel Workers
```bash
python3 resolve_auto_organize.py --workers 16
```

---

## 🎨 Color Grading Workflow in DaVinci Resolve

### Step 1: Filter by Clip Color in Color Page
In DaVinci Resolve's **Color** page:
1. Click the **Clips** filter dropdown in the top right $\rightarrow$ select **Clip Color**.
2. Click **Orange** (DJI Drone), **Teal** (Sony Alpha), or **Yellow** (Panasonic Lumix).

### Step 2: Create a Color Group
1. Select all clips of that color $\rightarrow$ Right-click $\rightarrow$ **Add into Current Group** (e.g. *"DJI Group"*).
2. In the Node Graph dropdown, switch from **Clip** to **Group Pre-Clip**.
3. Add a **Color Space Transform (CST)** node:
   * **Input Color Space**: Set according to the clip marker note (e.g. `DJI D-Gamut` / `Panasonic V-Gamut` / `Sony S-Gamut3.Cine`).
   * **Input Gamma**: `DJI D-Log M` / `Panasonic V-Log` / `Sony S-Log3`.
   * **Output Color Space**: `Rec.709`.
   * **Output Gamma**: `Gamma 2.4` (or your timeline working color space).
4. **All clips from that camera across all timelines are now instantly normalized and graded!**
