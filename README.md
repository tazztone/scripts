# scripts-sh

A collection of "Right-Click" productivity tools for Ubuntu users. These scripts integrate directly into the Nautilus file manager (Files), allowing you to convert, compress, and manipulate video/audio files without opening a heavy GUI application.

![alt text](image.png)

Powered by `ffmpeg`, `zenity`, and `bc`.

## 🚀 Features

- **Smart Compression:** Fit videos to exact sizes (e.g., 9MB for Email, 25MB for Discord) with auto-downscaling logic.
- **Instant Conversions:** One-click presets for MP4, WebM, ProRes, and DNxHD.
- **Workflow Automation:** Trim, scale, and extract audio instantly.
- **GUI Feedback:** Uses Zenity to provide progress bars, confirmation dialogs, and user input fields.

## 🛠️ Prerequisites

You need a few standard tools installed on your system. Open a terminal and run:

```bash
sudo apt update
sudo apt install ffmpeg zenity bc
```
*   `ffmpeg`: The core media engine.
*   `zenity`: Creates the popup windows and progress bars.
*   `bc`: Performs math calculations for bitrate scripts.

## 📥 Installation

1.  **Clone this repository** (or download the scripts):
    ```bash
    git clone https://github.com/YOUR_USERNAME/nautilus-ffmpeg-scripts.git
    cd nautilus-ffmpeg-scripts
    ```

2.  **Run the Installer (Recommended):**
    ```bash
    ./install.sh
    ```

3.  **Manual Installation (Alternative):**
    If you prefer to copy files manually:

   1.  **Move scripts to the Nautilus folder:**
    Depending on your Ubuntu version, the folder is in one of two places:
    *   **Ubuntu 22.04 / 24.04+ (Modern):** `~/.local/share/nautilus/scripts/`
    *   *Older Ubuntu:* `~/.gnome2/nautilus-scripts/`

    ```bash
    # Create the directory if it doesn't exist
    mkdir -p ~/.local/share/nautilus/scripts/
    
    # Copy all categories into the Nautilus scripts folder
    # This preserves the subdirectories to create submenus in Nautilus
    cp -r ffmpeg/* ~/.local/share/nautilus/scripts/
    ```

   2.  **Make them executable:**
    Linux requires scripts to have permission to run.
    ```bash
    chmod +x ~/.local/share/nautilus/scripts/*/*.sh
    ```

## 🖱️ How to Use

1.  Open your file manager (**Files / Nautilus**).
2.  Select one or more video/audio files.
3.  **Right-Click** the selection.
4.  Navigate to **Scripts** in the context menu.
5.  Choose the tool you want to run (e.g., `1-11-Custom-Size-MB.sh`).

*A popup window will appear showing the progress, and the new file will be created in the same folder as the original.*

## 📂 Included Scripts

The scripts are now organized into **Master Scripts** to reduce menu clutter. Each script uses a Zenity menu to let you choose specific technical flavors or presets.

### 0. 🧰 Universal Toolbox (`0-*`)
*The Swiss Army Knife for FFmpeg. A powerful, workstation-grade tool for all operations.*
- **0-00 🧰 Universal-Toolbox v2.0**: The ultimate one-stop shop for video editing.
    - **🚀 Unified Launchpad**: Start from a **Custom Edit**, pick from your **⭐ Favorites**, or re-run a command from your **🕒 Recent History**.
    - **⭐ "Star" as Favorite**: Any custom or history edit can be starred and named to create a permanent one-click preset.
    - **🕒 Automated History**: Your last 15 unique edits are automatically saved—never repeat manual setup again.
    - **🏎️ Parallel GPU Probing**: Auto-detects Nvidia (NVENC), Intel (QSV), and AMD (VAAPI) in the background with zero-delay caching.
    - **📝 Smart Subtitles**: Auto-detects `.srt` files and offers **Burn-in** (styled) or **Mux** (selectable) options.
    - **🔊 Production Audio**: Integrated **Stereo Downmixing**, EBU R128 Normalization, and +6dB Boost.

### 1. 🌐 Distribution & Web (`1-*`)
*Optimized for sharing, compatibility, and platform limits.*
- **1-01 🌐 H264-Social-Web-Presets**: Integrated presets for Twitter, WhatsApp, and Universal compatibility.
- **1-02 📦 H265-HEVC-Archive**: Ultra-efficient compression for long-term storage.
- **1-03 ⚖️ H264-Compress-to-Target-Size**: Auto-calculates bitrate to hit exact MB limits (Discord/Email).
- **1-04 👻 VP9-WebM-Alpha-Transparency**: Web-friendly video with support for transparency.
- **1-05 🎞️ GIF-Palette-Optimized**: High-quality GIF generation using two-pass palette analysis.

### 2. 🎬 Production & Intermediates (`2-*`)
*High-fidelity formats and repair tools for video editing.*
- **2-01 🍎 ProRes-Intermediate-Transcoder**: All profiles (Proxy, LT, Standard, HQ, 4444).
- **2-02 🎬 DNxHD/HR-Intermediate-Transcoder**: Avid-friendly proxies and mastering files.
- **2-03 🔧 Fix-VFR-Constant-Framerate**: Enforces Constant Framerate to prevent audio drift in editors.
- **2-04 🎥 H264-All-Intra-Production**: Every frame is a keyframe for instant seeking.
- **2-05 💎 Uncompressed-Raw-Video**: Bit-for-bit pixel perfect output.
- **2-06 🎙️ Audio-Internal-Fix-PCM-WAV**: Specialized fix for PCM/WAV synchronization.
- **2-07 🎁 Container-Remux-Rewrap**: Instant container swaps (MOV/MKV/MP4) without re-encoding.

### 3. 🔊 Audio Operations (`3-*`)
*Extract, normalize, and manipulate audio tracks.*
- **3-01 🔊 Audio-Format-Converter**: One-click extraction to MP3, WAV, FLAC, or AAC.
- **3-02 🎚️ Audio-Normalize-Boost-Mute**: EBU R128 normalization, +6dB boost, or total mute.
- **3-03 🎧 Audio-Channel-Remix**: Unified Mono-to-Stereo and Stereo-to-Mono tools.
- **3-04 🔪 Audio-Stem-Extraction-5.1**: Splits surround sound into 6 individual mono WAV tracks.

### 4. 📐 Geometry & Time (`4-*`)
*Resize, rotate, and manipulate video flow.*
- **4-01 📐 Resolution-Smart-Scaler**: Presets for 720p, 1080p, 4K, or custom width scaling.
- **4-02 🔄 Geometry-Rotate-Flip**: Rotate (90 CW/CCW, 180) and Mirror/Flip in one tool.
- **4-03 🔭 VidStab-Video-Stabilization**: Two-pass software analysis to remove camera shake.
- **4-04 ✂️ Crop-Aspect-Ratios**: Center-crop for 9:16 (Vertical), 16:9, 4:3, or 2.39:1 (Cinema).
- **4-05 ⏩ Video-Speed-Fast-Slow-Motion**: Variable playback speed with auto-pitch correction.

### 5. 🛠️ Utilities & Editing (`5-*`)
*Workflow helpers and specialized editing tools.*
- **5-01 🖼️ Image-Extract-Thumb-Sequence**: Middle snapshots, full sequences, or interval thumbs.
- **5-02 🎞️ Image-Sequence-to-Video**: Stitches a folder of JPGs into an MP4 video.
- **5-03 ✒️ Filters-Subtitles-Watermarks**: Burn `.srt` files or overlay image watermarks.
- **5-04 🔗 Concat-Join-Videos**: Stitches selected files together into one.
- **5-05 🧹 Metadata-Privacy-Web-Optimize**: Cleans personal info and prepares for web streaming.
- **5-06 🎬 Scene-Detection-Split**: Automatic cutting based on visual scene changes.
- **5-07 🎥 Editing-Smart-Trim**: Unified tool for trimming heads, tails, or specific ranges.

## 🧪 Testing Setup

The project includes a unified, automated testing framework to verify all scripts without needing a full Nautilus environment.

### Automated Test Runner (`test_runner.sh`)
The `test_runner.sh` tool provides a robust way to verify script functionality. It automatically handles Zenity mocking for headless environments and uses `ffprobe` to validate the properties of the generated media.

```bash
# Run the unified test suite (Headless/Mocked)
bash testing/test_runner.sh
```

**What it does:**
- **Zenity Mocking**: Simulates user interaction so tests run without GUI popups.
- **Media Validation**: Verifies resolution, codecs, and stream properties using `ffprobe`.
- **Category Coverage**: Runs representative tests from all 5 categories.
- **Colorized Reports**: Provides a clear PASS/FAIL summary in the terminal.

### Syntax Verification
To check all 50+ scripts for shell syntax errors manually:
```bash
for f in ffmpeg/*/*.sh; do bash -n "$f" && echo "OK: $f"; done
```

---

## 🤝 Contributing

Feel free to submit Pull Requests with your own useful FFmpeg one-liners!

1.  Fork the Project
2.  Create your Feature Branch
3.  Commit your Changes
4.  Push to the Branch
5.  Open a Pull Request
