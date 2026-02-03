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

### 1. 🌐 Distribution & Web (`1-*`)
*Optimized for sharing, compatibility, and platform limits.*
- **H.264 Presets (Social & Web)**: Integrated presets for Twitter, WhatsApp, and Universal compatibility.
- **H.265 HEVC Archive**: Ultra-efficient compression for long-term storage.
- **H.264 Compress to Target Size**: Auto-calculates bitrate to hit exact MB limits (Discord/Email).
- **VP9 WebM Alpha**: Web-friendly video with support for transparency.
- **GIF Palette Optimized**: High-quality GIF generation using two-pass palette analysis.

### 2. 🎬 Production & Intermediates (`2-*`)
*High-fidelity formats and repair tools for video editing.*
- **ProRes Intermediate**: All profiles (Proxy, LT, Standard, HQ, 4444).
- **DNxHD/HR Intermediate**: Avid-friendly proxies and mastering files.
- **Fix VFR**: Enforces Constant Framerate to prevent audio drift in editors.
- **H264 All-Intra Production**: Every frame is a keyframe for instant seeking.
- **Uncompressed Raw Video**: Bit-for-bit pixel perfect output.
- **Audio Internal Fix**: Specialized fix for PCM/WAV synchronization.
- **Container Remux/Rewrap**: Instant container swaps (MOV/MKV/MP4) without re-encoding.

### 3. 🔊 Audio Operations (`3-*`)
*Extract, normalize, and manipulate audio tracks.*
- **Audio Format Converter**: One-click extraction to MP3, WAV, FLAC, or AAC.
- **Audio Fix (Normalize/Boost/Mute)**: EBU R128 normalization, +6dB boost, or total mute.
- **Audio Channel Remix**: Unified Mono-to-Stereo and Stereo-to-Mono tools.
- **Audio Stem Extraction (5.1)**: Splits surround sound into 6 individual mono WAV tracks.

### 4. 📐 Geometry & Time (`4-*`)
*Resize, rotate, and manipulate video flow.*
- **Resolution Smart Scaler**: Presets for 720p, 1080p, 4K, or custom width scaling.
- **Geometry Transform**: Rotate (90 CW/CCW, 180) and Mirror/Flip in one tool.
- **VidStab Stabilization**: Two-pass software analysis to remove camera shake.
- **Crop Aspect Ratios**: Center-crop for 9:16 (Vertical), 16:9, 4:3, or 2.39:1 (Cinema).
- **Video Speed (Fast/Slow)**: Variable playback speed with auto-pitch correction.

### 5. 🛠️ Utilities & Editing (`5-*`)
*Workflow helpers and specialized editing tools.*
- **Image Extract (Thumb/Sequence)**: Middle snapshots, full sequences, or interval thumbs.
- **Image Sequence to Video**: Stitches a folder of JPGs into an MP4 video.
- **Filters (Subtitles/Watermarks)**: Burn `.srt` files or overlay image watermarks.
- **Concat/Join Videos**: Stitches selected files together into one.
- **Metadata Privacy & Web Optimize**: Cleans personal info and prepares for web streaming.
- **Scene Detection Split**: Automatic cutting based on visual scene changes.
- **Editing Smart Trim**: Unified tool for trimming heads, tails, or specific ranges.

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
