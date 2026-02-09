# 🗺️ Toolbox Ecosystem Roadmap (2026)

This roadmap outlines the strategic evolution of the three core toolboxes: **Universal** (Video Transcode), **Lossless** (Video Stream Copy), and **ImageMagick** (Image Raster).

## 🎯 North Star Vision
Create a **Unified Creative Suite** for Linux users that acts as a **Smart Assistant**, continuously analyzing your media to offer *only* the relevant tools.

---

## 🏗️ Phase 1: Foundation & Standardization (Complete)
*Goal: Ensure all tools share a common design language and core reliability.*
- [x] **UX Alignment**: Refactored ImageMagick to match Lossless Menu pattern.
- [x] **Safe Filenaming**: smart conflict resolution.
- [x] **Documentation**: Centralized docs.

---

## 🧩 Phase 2: The "Smart Builder" Architecture (Q2 2026)
*Goal: Enable complex workflows that adapt to the user.*

### 🔄 The "Context-Aware" Loop
Migrate all tools to a **Dynamic Recipe Builder** backed by **Deep Analysis**:

#### 1. Pre-Flight Deep Scan
Before showing the menu, run `ffprobe` or `identify` to build a **Media Profile**:
- **Tracks**: Does it have Audio? Subtitles? Chapters?
- **Visuals**: Is it HDR? CMYK? Transparent (Alpha)?
- **Metadata**: Does it have GPS info? Rotation flags?

#### 2. Dynamic Option Filtering (The "Grey Out" Logic)
- **Audio Logic**:
    - *No Audio Track found?* -> **Hide** "Remove Audio", "Normalize", "Extract MP3".
- **Subtitle Logic**:
    - *No Subtitles found?* -> **Hide** "Burn-in Subs", "Extract SRT".
- **Image Logic**:
    - *Has Alpha Channel?* -> **Show** "Flatten Background" or "Shadow Effect".
    - *Is CMYK?* -> **Show** "Fix Colors (to sRGB)".
    - *Has GPS Data?* -> **Show** "Privacy Scrub (Remove Location)".
- **Video Logic**:
    - *Is HDR10/Dolby?* -> **Show** "Tone Map to SDR".
    - *Is Vertical (9:16)?* -> **Show** "Blur-Pad to Landscape".

### 🛠️ Tasks
- [ ] **Analysis Engine**: Create `analyze_media_deep(file)` function returning a state object.
- [ ] **UI Engine**: Update Zenity generator to read this state and filter list items.

---

## ⚡ Phase 3: Performance & Intelligence (Q3 2026)
*Goal: Make the tools faster and smarter.*

### 🏎️ Performance
- [ ] **Smart Parallelism**: Auto-detect CPU cores.
- [ ] **GPU Auto-Switch**: Self-healing fallback to CPU on error.

### 🧠 Intelligence
- [ ] **Content-Aware Crop**: Auto-crop to subject (entropy/attention).
- [ ] **Scene Splitter**: Auto-cut at scene changes.
- [ ] **Silence Trimmer**: Remove silent segments.

---

## 📦 Phase 4: Distribution & Integration (Q4 2026)
*Goal: Move beyond "Scripts" to "Applications".*

- [ ] **Desktop Entry Generator**: Create `.desktop` files.
- [ ] **Auto-Updater**: Built-in `--update` flag.
- [ ] **Interactive Tour**: First-run explanation of features.

---

## 🧪 Experimental
- [ ] **AI Tagging**: Local LLM description/renaming.
