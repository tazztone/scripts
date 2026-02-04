# 🗺️ Project Roadmap

## Phase 1: The Universal Basis ✅
- [x] **Universal Toolbox**: Single script for Speed, Scale, Crop, Audio, Format.
- [x] **Smart Logic**: Filter chaining, FPS correction, audio preservation.
- [x] **Test Suite**: Automated verification with `ffprobe`.

## Phase 2: Power User Features (Current Focus) 🚀
- [ ] **Hardware Acceleration**: Auto-detect specific GPU (NVIDIA/Intel/AMD) and offer `h264_nvenc`, `hevc_nvenc`, `h264_qsv`, etc.
- [ ] **Smart Subtitles**: Auto-detect `.srt` files and offer Burn/Mux options.
- [ ] **"My Recipes" Presets**: Save current checklist selection to a config file and load it later.

## Phase 3: Modern UI & Experience ✨
- [ ] **YAD Integration**: Migrate from Zenity to YAD for complex forms, tabs, and previews.
- [ ] **Batch Queue System**: Background worker for processing files without blocking the UI.

## Phase 4: Distribution
- [ ] **Debian Package**: Create a `.deb` for easy installation.
- [ ] **PPA**: Host on Launchpad.
