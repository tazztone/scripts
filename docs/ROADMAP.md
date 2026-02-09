# 🗺️ Toolbox Comparison & Roadmap

## 📊 Script Comparison

| Feature | 🔒 Lossless Operations (FFmpeg) | 🖼️ Image Magick Toolbox |
| :--- | :--- | :--- |
| **UX Pattern** | **Menu-Driven** (Select Operation -> Config -> Run) | **Wizard-Driven** (Launchpad -> Checklist -> Giant Form -> Run) |
| **Task Focus** | **Singular** (Do one thing well) | **Composite** (Do multiple things at once) |
| **Input Validation** | ✅ **High** (Pre-flight codec checks, container compatibility) | ⚠️ **Medium** (Basic file checks) |
| **Error Handling** | ✅ **Robust** (Detailed checks per file) | ✅ **Improved** (Session logs, but still catching up) |
| **Presets** | ✅ **Granular** (Saved per operation) | ✅ **Snapshot** (Saves the entire "Giant Form" state) |
| **Modular Code** | ✅ **High** (Functions for every specific operation) | ⚠️ **Medium** (Monolithic processing loop) |

### 🧠 UX Analysis: Why Lossless Feels Better
The **Lossless Toolbox** feels "sensical" because it reduces cognitive load.
1.  **Decision Segmentation**: You first decide *what* to do (Trim), then *how* (Start/End). You aren't bombarded with unused options (Crop? Format? Effects?).
2.  **Context-Aware Config**: The "Trim" interface looks different from the "Remux" interface. Each is tailored to the task.
3.  **Linear Flow**: `Menu -> Config -> Action` is a predictable loop. The ImageMagick script's `Checklist -> Config` requires you to remember what you checked in the previous screen.

## 🛤️ Unified Roadmap (2026)

### 🎨 Phase 1: UX Standardization (Immediate)
**Goal:** Align Image Magick Toolbox with the superior Lossless Toolbox architecture.

- [ ] **Refactor ImageMagick to Menu-Driven UI**
    - Replace "Wizard Checklist" with a "Primary Operation" menu.
    - Top-Level Options: `Scale`, `Crop`, `Convert`, `Montage`, `Effects`.
    - **Crucial**: Bring "Square Crop" and "Montage" to the top level.
- [ ] **Standardize Visuals**
    - Use compatible icons and terminology across both scripts.
    - Ensure progress bars and success/fail dialogs look identical.

### 🏗️ Phase 2: Architectural Consistency
**Goal:** Create a shared library for core functions.

- [ ] **Create `lib/common.sh`**
    - Move `generate_safe_filename` (both have it!) to a shared library.
    - Move `check_dependencies` to shared.
    - Move `history_management` to shared.
- [ ] **Unified Error Logging**
    - Adopt the `mktemp` error log pattern from ImageMagick for Lossless (if missing).
    - Create a standard "Run Summary" reporter for batch jobs in both.

### 🚀 Phase 3: Major Feature Expansions

#### 🖼️ Image Magick Improvements
- [ ] **Smart Crop / Content-Aware**: Use ImageMagick's `entropy` or `attention` features to crop to the *interesting* part of the photo, not just center.
- [ ] **Text Overlay Wizard**: A dedicated interface for watermarking/text that allows positioning (North, South, Center) and styling (Font, Color).
- [ ] **PDF Manipulator**: Dedicated menu for PDF tools (Extract Pages vs Merge Images).

#### 🔒 Lossless Improvements
- [ ] **"Smart Cut" (Lossy/Lossless Hybrid)**: Allow frame-accurate trimming by re-encoding *only* the GOP boundaries and stream-copying the middle. (Advanced FFmpeg tech).
- [ ] **Audio/Subtitle Track Selector**: A GUI to list specific tracks (Stream 0:1 vs 0:2) and keep/discard them selectively.
- [ ] **Chapter Editor**: Simple GUI to add/edit chapter markers in MKV/MP4.

### 📦 Phase 4: Distribution & Polish
- [ ] **Installer Update**: Ensure `install.sh` handles the new `lib/` structure correctly.
- [ ] **Desktop Integration**: Add `.desktop` files so these can be launched from the App Grid, not just Nautilus.
