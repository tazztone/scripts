# scripts-sh

A collection of "Right-Click" productivity tools for Ubuntu users. These scripts integrate directly into the Nautilus file manager (Files), allowing you to convert, compress, and manipulate video/audio files without opening a heavy GUI application.

![alt text](image.png)

Powered by `ffmpeg`, `zenity`, and `bc`.

## 🚀 Features

- **Smart Compression:** Fit videos to exact sizes (e.g., 9MB for Email, 25MB for Discord) with auto-downscaling logic.
- **Lossless Operations:** Lightning-fast quality-preserving operations (trimming, remuxing, stream editing) with zero re-encoding.
- **Instant Conversions:** One-click presets for MP4, WebM, ProRes, and DNxHD.
- **Workflow Automation:** Trim, scale, and extract audio instantly with preset and history systems.
- **GUI Feedback:** Uses Zenity to provide progress bars, confirmation dialogs, and user input fields.
- **CLI Integration:** Command-line preset support for automation and batch processing.

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
    git clone https://github.com/YOUR_USERNAME/scripts-sh.git
    cd scripts-sh
    ```
    
    > **Note:** Replace `YOUR_USERNAME` with your GitHub username, or use the actual repository URL if hosted elsewhere.

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
    
    # Copy the toolbox scripts to the Nautilus scripts folder
    cp ffmpeg/*.sh ~/.local/share/nautilus/scripts/
    ```

   2.  **Make them executable:**
    Linux requires scripts to have permission to run.
    ```bash
    chmod +x ~/.local/share/nautilus/scripts/*.sh
    ```

## 🖱️ How to Use

1.  Open your file manager (**Files / Nautilus**).
2.  Select one or more video/audio files.
3.  **Right-Click** the selection.
4.  Navigate to **Scripts** in the context menu.
5.  Choose the tool you want to run:
    - **🧰 Universal-Toolbox**: Full-featured video processing with transcoding
    - **🔒 Lossless-Operations-Toolbox**: Quality-preserving operations only

*A popup window will appear showing the progress, and the new file will be created in the same folder as the original.*

## 📂 Available Tools

The project has been streamlined into **two powerful master tools** that provide comprehensive video processing capabilities through intelligent, guided interfaces.

### 0. 🧰 Universal Toolbox (`0-*`)
*The Swiss Army Knife for FFmpeg. A powerful, workstation-grade tool for all operations.*
- **0-00 🧰 Universal-Toolbox**: The ultimate one-stop shop for video editing. **[📖 Full Documentation](docs/UNIVERSAL_TOOLBOX.md)**
    - **🧙‍♂️ Guided 2-Step Wizard**:
        1. **Unified Wizard**: Pick a starting point (Custom, Starred, or History) AND select categories (Speed, Scale, Crop, etc.) in a single, streamlined interface.
        2. **Dashboard**: Configure everything in a single, unified window with dynamic fields.
    - **🏎️ Smart Hardware Auto-Probe**: Performs a silent 1-frame dummy encode at startup to detect and **automatically enable** NVENC (Nvidia), QSV (Intel), or VAAPI (AMD), hiding broken options.
    - **⚖️ Integrated Target Size**: Accurate 2-pass encoding to hit exact MB limits (e.g., 25MB for Discord) directly in the tool.
    - **🛡️ Auto-Rename Safety**: Never overwrites files. Automatically increments names (`_v1`, `_v2`) if the output target already exists.
    - **🏷️ Descriptive Smart Tagging**: Files are named based on your edits (e.g. `video_2x_1080p_noaudio.mp4`) instead of generic tags.
    - **💾 Persistent Custom Presets**: Saved favorites now remember your manual entries (e.g. Custom Width, Target Size) and reload them instantly.
    - **📝 Smart Subtitles**: Auto-detects `.srt` files and offers styled **Burn-in** or **Mux** options.

- **0-01 🔒 Lossless-Operations-Toolbox**: Specialized tool for quality-preserving operations only. **[📖 Full Documentation](docs/LOSSLESS_TOOLBOX.md)**
    - **🚀 Zero Quality Loss**: All operations use FFmpeg stream copy - no re-encoding, no quality degradation.
    - **⚡ Lightning Fast**: Operations complete in seconds, not minutes (no CPU/GPU encoding).
    - **🎯 Curated Operations**: Only truly lossless operations - trimming, remuxing, stream editing, metadata changes.
    - **🛡️ Smart Validation**: Prevents incompatible operations with clear error messages and alternatives.
    - **⭐ Preset System**: CLI support (`--preset "Quick Trim"`) and saved favorites for automation.
    - **📚 Operation History**: Recent operations accessible from main menu for quick re-use.
    - **🔧 Enhanced Input**: Flexible time formats (30, 1:30, 01:30:45) with real-time validation.
    - **📦 Container Optimization**: Format-specific flags for better compatibility (faststart, index space).
    - **🏷️ Smart Auto-Rename**: Prevents file overwrites with intelligent incremental naming.

### 1. 🖼️ ImageMagick Toolbox (`1-*`)
*High-performance batch image processing directly from Nautilus.*
- **1-00 🖼️ Image-Magick-Toolbox**: Comprehensive image manipulation with "Smart" logic. **[📖 Full Documentation](docs/IMAGEMAGICK_TOOLBOX.md)**
    - **⚡ Parallel Batch Processing**: Uses background jobs to process image libraries at maximum CPU speed.
    - **📱 Modern Format Support**: Automated handling of **HEIC/RAW** to sRGB JPG conversion.
    - **📐 Smart Resizing**: Aspect ratio preservation with "Fit to Height/Width" and HD presets.
    - **📦 Format Conversion**: Instant conversion between JPG, PNG, WEBP, and TIFF with intelligent transparency handling.
    - **🚀 One-Click Optimization**: "Make Web Ready" preset (quality 85 + metadata stripping).
    - **🖼️ Canvas & Grid**: Create **2x2 / 3x3 grids** or contact sheets from selected images instantly.
    - **📄 PDF Utilities**: Combine multiple images into a single PDF or extract pages as high-DPI images.
    - **🏷️ Branded Output**: Auto-watermarking with `watermark.png` detection and Southeast orientation.

### Operation Categories Covered

Both tools provide comprehensive coverage of video processing needs:

#### 🌐 **Distribution & Web**
*Universal Toolbox: Optimized encoding for sharing, compatibility, and platform limits*
- Social media optimization (Twitter, WhatsApp, Discord)
- H.264/H.265 compression with target sizing
- WebM with transparency support
- High-quality GIF generation

#### 🎬 **Production & Intermediates** 
*Universal Toolbox: High-fidelity formats and repair tools for video editing*
- ProRes and DNxHD intermediate formats
- Constant framerate fixing for editors
- Uncompressed and PCM workflows
- Professional broadcast standards

#### 🔊 **Audio Operations**
*Both Tools: Extract, normalize, and manipulate audio tracks*
- Format conversion (MP3, WAV, FLAC, AAC)
- EBU R128 normalization and volume control
- Channel remixing and surround sound processing
- Lossless audio track removal/selection

#### 📐 **Geometry & Time**
*Universal Toolbox: Resize, rotate, and manipulate video flow*
- Smart scaling with aspect ratio preservation
- Rotation, flipping, and stabilization
- Aspect ratio cropping (9:16, 16:9, square, cinema)
- Variable speed with pitch correction

#### 🛠️ **Utilities & Editing**
*Both Tools: Workflow helpers and specialized editing tools*
- **Universal**: Advanced trimming with re-encoding
- **Lossless**: Instant trimming with stream copy
- **Universal**: Subtitle burning and watermarking
- **Lossless**: Metadata cleaning and container remuxing
- **Both**: File concatenation and batch processing

## 🧪 Testing Setup

The project includes comprehensive automated testing frameworks to verify all scripts without needing a full Nautilus environment. For detailed documentation, see the [Testing Framework Guide](testing/TESTING.md#-how-to-run-tests).

### Universal Scripts Test Runner (`test_runner.sh`)
The `test_runner.sh` tool provides a robust way to verify script functionality. It automatically handles Zenity mocking for headless environments and uses `ffprobe` to validate the properties of the generated media.

```bash
# Run the unified test suite (Headless/Mocked)
bash testing/test_runner.sh
```

The runner will:
1. Generate dummy media (H.264/AAC) in `/tmp/scripts_test_data`
2. Execute scripts against this data
3. Analyze output files using `ffprobe` to verify codecs, resolution, and metadata

### Lossless Operations Toolbox Tests (`test_lossless_toolbox.sh`)
Specialized property-based testing for the Lossless Operations Toolbox to ensure stream copy preservation and operation safety.

```bash
# Run property-based tests for lossless operations
bash testing/test_lossless_toolbox.sh
```

This test suite validates 12 comprehensive properties including:
- **Stream Copy Preservation**: Ensures no re-encoding occurs
- **Codec Compatibility**: Validates container-codec combinations
- **Operation Safety**: Prevents destructive operations
- **Batch Processing**: Multi-file operation integrity
- **Metadata Handling**: Lossless metadata operations

### Additional Test Suites
The project includes several specialized test runners:

```bash
# Syntax validation for all scripts
bash testing/test_lint.sh

# UI resilience and negative path testing
bash testing/test_ui_resilience.sh

# Wizard unit tests
bash testing/test_wizard_unit.sh

# Cross-version compatibility tests
bash testing/test_cross_version.sh
```

**What the tests do:**
- **Zenity Mocking**: Simulates user interaction so tests run without GUI popups.
- **Media Validation**: Verifies resolution, codecs, and stream properties using `ffprobe`.
- **Property Testing**: Validates universal correctness properties (stream preservation, codec compatibility).
- **Category Coverage**: Runs representative tests from all operation categories.
- **Colorized Reports**: Provides clear PASS/FAIL summaries in the terminal.

### Syntax Verification
To check all scripts for shell syntax errors manually:
```bash
for f in ffmpeg/*.sh; do bash -n "$f" && echo "OK: $f"; done
```

---

## 🛠️ Development & Testing

This project includes a robust, headless testing suite to ensure all FFmpeg scripts work across different environments. 

### 📖 Detailed Documentation
For comprehensive guides on specific tools:
- **🧰 Universal Toolbox**: See [UNIVERSAL_TOOLBOX.md](docs/UNIVERSAL_TOOLBOX.md) for complete feature guide
- **🔒 Lossless Operations Toolbox**: See [LOSSLESS_TOOLBOX.md](docs/LOSSLESS_TOOLBOX.md) for lossless operations guide
- **🖼️ Image Magick Toolbox**: See [IMAGEMAGICK_TOOLBOX.md](docs/IMAGEMAGICK_TOOLBOX.md) for image processing guide

Developers and AI agents should refer to the [Testing Guide](testing/TESTING.md) for details on:

- Running the automated test runner.
- Mocking the Zenity GUI.
- Guidelines for adding new features without breaking existing tests.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

### Before Submitting a Pull Request

1. **Run the Test Suite**: Ensure all tests pass by running:
   ```bash
   # Main test suites
   bash testing/test_runner.sh
   bash testing/test_lossless_toolbox.sh
   
   # Additional validation
   bash testing/test_lint.sh
   bash testing/test_ui_resilience.sh
   ```

2. **Update Documentation**: If you add new features, update the relevant documentation:
   - [`README.md`](README.md) - Main overview
   - [`docs/UNIVERSAL_TOOLBOX.md`](docs/UNIVERSAL_TOOLBOX.md) - Universal Toolbox details
   - [`docs/LOSSLESS_TOOLBOX.md`](docs/LOSSLESS_TOOLBOX.md) - Lossless Toolbox details
   - [`docs/IMAGEMAGICK_TOOLBOX.md`](docs/IMAGEMAGICK_TOOLBOX.md) - ImageMagick Toolbox details
   - [`testing/TESTING.md`](testing/TESTING.md) - Testing framework guide

3. **Follow Code Style**: Maintain consistency with existing scripts:
   - Use bash 4.0+ features
   - Include `-nostdin` flag in all FFmpeg commands
   - Source shared utilities from [`common/`](common/) directory
   - Use the unified wizard system for UI dialogs

4. **Test Negative Paths**: Ensure your changes handle cancellations and errors gracefully.

### Reporting Issues

- Use GitHub Issues for bug reports and feature requests.
- Include steps to reproduce and expected vs. actual behavior.
- Attach relevant logs from `/tmp/scripts_debug.log` when applicable.

## 📜 License

MIT License. Feel free to use and modify for your own workflow.

---

## 🗺️ Project Roadmap

### 🏁 Phase 1-3: Foundation & Wizard (Completed) ✅
- [x] **Universal Basis**: Single script for all major FFmpeg operations.
- [x] **Hardware Acceleration**: Smart auto-probe and vendor-specific optimizations.
- [x] **The Wizard**: 2-step guided flow for cleaner UX (Unified Wizard + Configuration Dashboard).
- [x] **Safety & Persistence**: Auto-rename protection and persistent custom presets.

### 🚧 Phase 4: Extended Capabilities (In Progress)
- [ ] **Visual Preview**: "Test Run" button to generate a 5-second sample to verify filters.
- [ ] **Watermarking**: Auto-detect `watermark.png` and offer easy overlay options.
- [ ] **Quality of Life**: Add support for more granular cropping and manual bitrate entries.

### 📦 Phase 5: Distribution
- [ ] **Debian Package**: Create a `.deb` for easy installation.
- [ ] **PPA**: Host on Launchpad for automated updates.
