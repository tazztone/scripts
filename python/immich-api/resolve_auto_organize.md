# DaVinci Resolve Automated Media Organizer & Color Grading Prep

A standalone Python automation tool for **DaVinci Resolve Studio** to automatically probe staged video files using a 3-tier deep metadata engine (container EXIF tags, stream properties, hardware models, and codec signatures), organize clips into structured Media Pool Bins, assign distinct Clip Colors, add CST (Color Space Transform) starting grade markers, and auto-generate dedicated Timelines per camera/resolution bucket.

---

## 🎯 Purpose & Problem Solved

When editing multi-year documentary, archival, or event projects, footage comes from dozens of different devices:
* **DJI Drones** (4K 60fps / 10-bit D-Log M / D-Cinelike)
* **Sony Alpha / FX** (4K 25fps real-time vs 100fps slow-motion XAVC)
* **Panasonic Lumix** (10-bit V-Log)
* **Smartphones & Mobile** (240fps slow-mo bursts & vertical reels)
* **5.4K Timelapses & Hyperlapses**

Importing these mixed formats into a single timeline creates color management chaos (mismatched color spaces, gamma curves, and framerates).

**`resolve_auto_organize.py`** automates the entire ingestion and color prep pipeline:
1. **Deep Metadata Probe**: Analyzes hardware make/model, bit-depth, codec, and framerate.
2. **Media Pool Bins**: Automatically creates structured sub-bins (e.g. `📁 DJI_Drone_4K_SlowMo_59fps`, `📁 Sony_Alpha_1080p_SlowMo_100fps`).
3. **Color Page Ready**: Color-codes clips (Orange for DJI, Teal for Sony, Yellow for Panasonic, Purple for Mobile, Blue for Timelapses) and embeds CST starting grade markers on Frame 0.
4. **Dedicated Timelines**: Automatically generates a timeline for each camera & resolution bucket.

---

## 🔬 3-Tier Deep Metadata Engine

| Camera / Device | Hardware & Container Tags | Detected Profile / Bit-Depth | Clip Color | Target Media Pool Bin |
| :--- | :--- | :--- | :--- | :--- |
| **DJI Drone** | `Model: FC6310`, `Handler: .DJI.Meta` | D-Cinelike / D-Log M (8/10-bit) | `Orange` | `📁 DJI_Drone_4K_{FPS}` |
| **Sony Alpha (XAVC)** | `Brand: XAVC`, `Model: ILCE-*` | S-Cinetone / S-Log3 (8/10-bit) | `Teal` | `📁 Sony_Alpha_{Res}_{FPS}` |
| **Panasonic Lumix** | `Make: Panasonic`, `Handler: Static Metadata` | V-Log / Standard (10-bit) | `Yellow` | `📁 Panasonic_Lumix_{Res}` |
| **Smartphone / Mobile** | `AndroidVersion`, `Apple iPhone` | Rec.709 / sRGB (8-bit, 240fps) | `Purple` | `📁 Mobile_Smartphone_{Res}` |
| **Timelapses** | `*TL*`, `hyperlapse`, 5.4K/Vertical | Rec.709 / sRGB (10-bit) | `Blue` | `📁 Timelapse_{Res}` |
| **Renders / Exports** | `Software: Adobe/DaVinci` | Master Rec.709 | `Navy` | `📁 Render_Exported_Render` |

---

## 🚀 Usage

### 1. Preview Metadata Without Opening Resolve (`--scan-only`)
Inspect all video files in the staging directory and print a formatted hardware & starting grade table:

```bash
python3 resolve_auto_organize.py --scan-only
```

### 2. Auto-Organize Live Resolve Project
With **DaVinci Resolve Studio** open and a project loaded:

```bash
python3 resolve_auto_organize.py
```

This will:
* Connect to your active Resolve project.
* Import all staged clips into dedicated sub-bins under `Staged_Clips_By_Camera/`.
* Assign Clip Colors and add CST starting grade markers to every clip.
* Generate matching Timelines (e.g. `TL - DJI Drone 4K 50fps`, `TL - Sony Alpha 100fps SlowMo`).
* Automatically switch Resolve to the **Color Page**.

### 3. Custom Staging Directory
```bash
python3 resolve_auto_organize.py --staging-dir "D:/_RESOLVE_IMPORT_STAGING/videos"
```

### 4. Skip Timeline Creation (Bins & Colors Only)
```bash
python3 resolve_auto_organize.py --no-timelines
```

---

## 🎨 Color Grading Workflow in DaVinci Resolve

### Step 1: Filter by Clip Color in Color Page
In DaVinci Resolve's **Color** page:
1. Click the **Clips** filter dropdown in the top right $\rightarrow$ select **Clip Color**.
2. Click **Orange** (DJI Drone) or **Teal** (Sony Alpha) or **Yellow** (Panasonic Lumix).

### Step 2: Create a Color Group
1. Select all clips of that color $\rightarrow$ Right-click $\rightarrow$ **Add into Current Group** (e.g. *"DJI Group"*).
2. In the Node Graph dropdown, switch from **Clip** to **Group Pre-Clip**.
3. Add a **Color Space Transform (CST)** node:
   * **Input Color Space**: Set according to the clip marker note (e.g. `DJI D-Gamut` / `Panasonic V-Gamut` / `Sony S-Gamut3.Cine`).
   * **Input Gamma**: `DJI D-Log M` / `Panasonic V-Log` / `Sony S-Log3`.
   * **Output Color Space**: `Rec.709`.
   * **Output Gamma**: `Gamma 2.4` (or your timeline working color space).
4. **All clips from that camera are now instantly normalized and graded!**
