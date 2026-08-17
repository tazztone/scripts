# DaVinci Resolve Automated Media & Timelapse Ingestion Suite

A pair of high-performance Python automation tools for **DaVinci Resolve Studio** to automatically probe, mathematically sequence, organize, and color-prep both **video footage** and **RAW photo timelapses/hyperlapses**.

1. **`resolve_auto_organize.py`**: Automated video organizer, CST color-coder, and timeline generator with strict unmixed resolutions and framerate segregation.
2. **`resolve_timelapse_engine.py`**: Mathematical EXIF-driven timelapse/hyperlapse sequence detector, zero-copy CinemaDNG sequence stager, and native 4:3 canvas timeline generator.

---

## 🎯 1. Video Organization (`resolve_auto_organize.py`)

### 🔬 3-Tier Deep Metadata Engine

| Camera / Device | Hardware & Container Tags | Detected Profile / Bit-Depth | Clip Color | Target Media Pool Bin |
| :--- | :--- | :--- | :--- | :--- |
| **DJI Drone** | `Model: FC6310`, `Handler: .DJI.Meta` | D-Cinelike / D-Log M (8/10-bit) | `Orange` | `📁 DJI_DJI_Drone_{Res}_{FPS}` |
| **Sony Alpha (XAVC)** | `Brand: XAVC`, `Model: ILCE-*` | S-Cinetone / S-Log3 (8/10-bit) | `Teal` | `📁 Sony_Alpha__FX_XAVC_{Res}_{FPS}` |
| **Panasonic Lumix** | `Make: Panasonic`, `Handler: Static Metadata` | V-Log / Standard (10-bit) | `Yellow` | `📁 Panasonic_Lumix_{Res}_{FPS}` |
| **Smartphone / Mobile** | `AndroidVersion`, `Apple iPhone` | Rec.709 / sRGB (8-bit, 240fps) | `Purple` | `📁 Mobile_Smartphone_{Res}_{FPS}` |
| **Timelapses (Video)** | `*TL*`, `hyperlapse`, 5.4K, 4:3, Vertical | Rec.709 / sRGB (10-bit) | `Blue` | `📁 Timelapse_Timelapse_{Res}_{FPS}` |
| **Renders / Exports** | `Software: Adobe/DaVinci` | Master Rec.709 | `Navy` | `📁 Render_Exported_Render_{Res}_{FPS}` |

### 🚀 Video Usage

```bash
# 1. Preview metadata in standalone mode
python3 resolve_auto_organize.py --scan-only

# 2. Auto-organize active DaVinci Resolve Project
python3 resolve_auto_organize.py
```

---

## 📸 2. RAW Timelapse & Hyperlapse Engine (`resolve_timelapse_engine.py`)

### 🧠 The Math: Cadence Regularity & Delta-T Clustering

Filenames and folder names are often inconsistent across cameras and editing tools. `resolve_timelapse_engine.py` inspects EXIF capture timestamps (`DateTimeOriginal` + sub-seconds) and applies mathematical sequence clustering:

1. **Interval Clustering**: Groups consecutive shots within an interval window $\Delta t \in [0.5\text{s}, 60.0\text{s}]$.
2. **Cadence Regularity (Coefficient of Variation)**:
   $$\mu = \text{mean}(\Delta t_i), \quad \sigma = \text{std}(\Delta t_i), \quad CV = \frac{\sigma}{\mu}$$
   Requires $CV \le 0.25$ to filter out erratic manual snaps and sports bursts while capturing true intervalometer shots.
3. **Span Filtering**: Requires sequence length $\ge 5$ frames and total capture duration $\ge 5.0\text{s}$ (eliminating 0-second single-burst AEB brackets).
4. **Dual-Stream Partitioning**: Separates base captures (`.DNG`) from Lightroom AI Denoised (`-Enhanced-NR.dng`) versions so both can be graded side-by-side.

### ❓ Why CinemaDNG / DNG Only?

* **NLE Sequence Limitation**: DaVinci Resolve's Image Sequence engine natively supports **CinemaDNG (`.dng`)**, TIFF, EXR, DPX, and JPEG/PNG sequences.
* **Proprietary RAW Formats**: Proprietary raw files (Sony `.ARW`, Panasonic `.RW2`, Nikon `.NEF`, Canon `.CR3`) cannot be imported directly as NLE image sequences by Resolve and are treated as standalone still photos.
* **Full RAW Control**: Ingesting CinemaDNG image sequences unlocks Resolve's dedicated **Camera RAW** palette in the Color page (ISO, Exposure, Color Temp, Tint, and Highlight Recovery).

### 📐 Strict Aspect Ratio & Orientation Segregation

When cameras/drones shoot portrait or vertical timelapses (e.g. `Orientation: Rotate 270 CW`), Resolve displays them as **Vertical 3:4 (3024x4032)** while landscape shots display as **Landscape 4:3 (4032x3024)**.
The engine automatically detects orientation metadata and creates dedicated, unmixed bins and timelines:
* **Landscape Bin**: `Timelapse_CinemaDNG_Landscape_4032x3024_25fps` $\rightarrow$ Timeline: **`TL - All Timelapses (Landscape 4032x3024 25fps)`**
* **Vertical Bin**: `Timelapse_CinemaDNG_Vertical_3024x4032_25fps` $\rightarrow$ Timeline: **`TL - All Timelapses (Vertical 3024x4032 25fps)`**

### 🚀 Timelapse Usage

```bash
# 1. Preview detected timelapses without modifying disk or Resolve
python3 resolve_timelapse_engine.py --scan-only

# 2. Dry-run staging simulation
python3 resolve_timelapse_engine.py --dry-run

# 3. Stage zero-copy hardlinks and import into active DaVinci Resolve Project
python3 resolve_timelapse_engine.py

# 4. Optional individual timelines per sequence (in addition to master timelines)
python3 resolve_timelapse_engine.py --individual-timelines

# 5. Custom interval or cadence settings
python3 resolve_timelapse_engine.py --min-frames 10 --max-cv 0.20 --fps 25.0

# 6. Re-scan and rebuild EXIF cache
python3 resolve_timelapse_engine.py --clear-cache
```

---

## 🎨 Color Grading Workflow in DaVinci Resolve

### For Video Clips (CST Group Grading)
1. In the **Color** page, filter by **Clip Color** (Orange for DJI, Teal for Sony, Yellow for Panasonic).
2. Right-click selected clips $\rightarrow$ **Add into Current Group**.
3. In **Group Pre-Clip**, add a **Color Space Transform (CST)** node matching the Frame 0 marker note (e.g. `DJI D-Gamut / D-Log M` $\rightarrow$ `Rec.709 / Gamma 2.4`).

### For CinemaDNG Timelapses (Camera RAW Photographic Grading)
1. Select any **Blue** timelapse clip on the timeline.
2. In the **Color Page**, click the **Camera RAW** icon (bottom-left palette next to Color Wheels).
3. Set **Decode Using** $\rightarrow$ **Clip**.
4. Configure Photographic Decode settings:
   * **Color Space**: `sRGB` (or `Rec.709`)
   * **Gamma**: `sRGB` (or `Gamma 2.2`)
   * **White Balance**: `As Shot` (or adjust Color Temp / Tint to taste)
   * **Highlight Recovery**: **Checked** (restores blown sky and cloud details from 12-bit/14-bit RAW sensor data)
5. *(Optional CST Transformation)*: If working on a Rec.709 / Gamma 2.4 broadcast timeline, add a **Color Space Transform (CST)** node with:
   * **Input Color Space**: `sRGB`
   * **Input Gamma**: `sRGB` (or `Gamma 2.2`)
   * **Output Color Space**: `Rec.709`
   * **Output Gamma**: `Gamma 2.4` (or `Gamma 2.2` for web / YouTube / PC monitors).
6. **Result**: Your timelapse photos will immediately have rich, natural contrast, accurate skin tones, and vibrant skies matching Lightroom / PhotoLab!
