# 🗺️ Project Roadmap

## Phase 1: The Universal Basis ✅
- [x] **Universal Toolbox**: Single script for Speed, Scale, Crop, Audio, Format.
- [x] **Smart Logic**: Filter chaining, FPS correction, audio preservation.
- [x] **Test Suite**: Automated verification with `ffprobe`.

## Phase 2: Power User Features (Completed) ✅
- [x] **Hardware Acceleration**: Auto-detect specific GPU (NVIDIA/Intel/AMD) and offer `h264_nvenc`, `hevc_nvenc`, `h264_qsv`, etc.
- [x] **Smart Subtitles**: Auto-detect `.srt` files and offer Burn/Mux options.
- [x] **"My Recipes" Presets**: Save current checklist selection to a config file and load it later.
- [x] **Launchpad UI**: Unified entry point for New Edits, Favorites, and History. (Bonus)
- [x] **History Tracking**: Auto-save last 15 unique commands. (Bonus)

## Phase 2.5: Deep Integration (Proposed) 🚧
- [ ] **Visual Preview**: "Test Run" button to generate a 5-second sample to verify filters before the long encode.
- [ ] **Target Size Mode**: Integrate "Fit to MB" (bitrate calc) directly into Universal Toolbox.
- [ ] **Watermarking**: Auto-detect `watermark.png` and offer overly options in the main tool.

## Phase 3: The Wizard Refactor (Current) 🚧
- [ ] **Multi-Step UI**: Break the monolithic checklist into a cleaner 3-step Wizard.
    - **Step 1**: "What do you want to fix?" (Scale, Speed, Audio, etc.)
    - **Step 2**: "Configure Details" (Select specific resolution, speed value, etc.)
    - **Step 3**: "Export Settings" (Quality, Size, Format).
- [ ] **Refined Sub-Menus**: Allow for more detailed options in specific categories (e.g., granular cropping).

## Phase 4: Distribution
- [ ] **Debian Package**: Create a `.deb` for easy installation.
- [ ] **PPA**: Host on Launchpad.
