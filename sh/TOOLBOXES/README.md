# scripts-sh

A collection of "Right-Click" productivity tools for Ubuntu users. These scripts integrate directly into the Nautilus file manager (Files), allowing you to convert, compress, and manipulate video/audio files without opening a heavy GUI application.

![alt text](image.png)

Powered by `ffmpeg`, `zenity`, and `bc`.

## 🚀 Features

- **Smart Compression:** Fit videos to exact sizes (e.g., 9MB for Email, 25MB for Discord) with auto-downscaling logic.
- **Lossless Operations:** Lightning-fast quality-preserving operations (trimming, remuxing, stream editing) with zero re-encoding.
- **Instant Conversions:** One-click presets for MP4, WebM, ProRes, and DNxHD.
- **Workflow Automation:** Trim, scale, and extract audio instantly with preset and history systems.
- **GUI Feedback:** Features a modern Zenity 4 checklist UI and **real-time** parsing progress bars for long FFmpeg encodes.
- **CLI Integration:** Command-line preset support for automation and batch processing.

## 🛠️ Prerequisites

You need a few standard tools installed on your system. Open a terminal and run:

```bash
sudo apt update
sudo apt install ffmpeg zenity bc
```
*   `ffmpeg`: The core media engine.
*   `zenity`: Creates the popup windows and progress bars. **(Requires version 4.0 or higher)**.
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
    - **Universal-Toolbox**: Full-featured video processing with transcoding
    - **Lossless-Operations-Toolbox**: Quality-preserving operations only

*A popup window will appear showing the progress, and the new file will be created in the same folder as the original.*

## 📂 Available Tools

The project has been streamlined into **three powerful master tools** that provide comprehensive media processing capabilities through intelligent, guided interfaces.

### 0. Universal Toolbox (`0-*`)
*The Swiss Army Knife for FFmpeg. A powerful, workstation-grade tool for all operations.*
- **0-00 Universal-Toolbox**: The ultimate one-stop shop for video editing.
    - **🧙‍♂️ Guided 2-Step Wizard**:
        1. **Unified Wizard (Fix 2)**: Robust multi-selection parsing that intelligently handles complex recipes (Starred, History, and custom categories) while ignoring UI metadata.
        2. **Dashboard**: Configure everything in a single, unified window with dynamic fields.
    - **🏎️ Smart Hardware Auto-Probe**: Performs a silent 1-frame dummy encode at startup to detect and **automatically enable** NVENC (Nvidia), QSV (Intel), or VAAPI (AMD), hiding broken options.
    - **⚖️ Integrated Target Size**: Accurate 2-pass encoding to hit exact MB limits (e.g., 25MB for Discord) directly in the tool.
    - **🛡️ Auto-Rename Safety**: Never overwrites files. Automatically increments names (`_v1`, `_v2`) if the output target already exists.
    - **🏷️ Descriptive Smart Tagging**: Files are named based on your edits (e.g. `video_2x_1080p_noaudio.mp4`) instead of generic tags.
    - **💾 Persistent Custom Presets**: Saved favorites now remember your manual entries (e.g. Custom Width, Target Size) and reload them instantly.
    - **📝 Smart Subtitles**: Auto-detects `.srt` files and offers styled **Burn-in** or **Mux** options.
    - **⚡ Dynamic Pre-Flight Scan**: Single-pass cached profiling automatically hides audio tools and options if the input video lacks audio tracks.
    - **💻 Headless CLI Execution**: Supports running recipe sequences headlessly using `--choices` parameter.

- **0-01 Lossless-Operations-Toolbox**: Specialized tool for quality-preserving operations only.
    - **🚀 Zero Quality Loss**: All operations use FFmpeg stream copy - no re-encoding, no quality degradation.
    - **⚡ Lightning Fast**: Operations complete in seconds, not minutes (no CPU/GPU encoding).
    - **🎯 Curated Operations**: Only truly lossless operations - trimming, remuxing, stream editing, metadata changes.
    - **🛡️ Smart Validation**: Prevents incompatible operations with clear error messages and alternatives.
    - **⭐ Preset System**: CLI support (`--preset "Quick Trim"`) and saved favorites for automation.
    - **📚 Operation History**: Recent operations accessible from main menu for quick re-use.
    - **🔧 Enhanced Input**: Flexible time formats (30, 1:30, 01:30:45) with real-time validation.
    - **📦 Container Optimization**: Format-specific flags for better compatibility (faststart, index space).
    - **🏷️ Smart Auto-Rename**: Prevents file overwrites with intelligent incremental naming.
    - **💻 Decoupled UI / Headless Runner**: Zenity UI dialogs are decoupled into helper scripts, enabling headless automation.

### 1. ImageMagick Toolbox (`1-*`)
*High-performance batch image processing directly from Nautilus.*
- **1-00 Image-Magick-Toolbox**: Comprehensive image manipulation with "Smart" logic.
    - **⚡ Parallel Batch Processing**: Uses background jobs to process image libraries at maximum CPU speed.
    - **📱 Modern Format Support**: Automated handling of **HEIC/RAW** to sRGB JPG conversion.
    - **📐 Smart Resizing**: Aspect ratio preservation with "Fit to Height/Width" and HD presets.
    - **💎 Dynamic Preset Naming**: Automatically suggests descriptive names for favorites based on operations (e.g., `scale128x128_jpg_q85`).
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

## 📖 Detailed Guides & Reference

---

### 📚 Domain Glossary

This section defines the domain language of the Nautilus Productivity Toolboxes ecosystem.

#### Core Concepts

##### Toolbox
An entrypoint Nautilus shell script integrated into the file manager context menu. It wraps media operations in a visual interface.
- **Universal-Toolbox**: Transcodes and applies visual filters.
- **Lossless-Toolbox**: Performs stream copy operations (zero re-encoding).
- **ImageMagick-Toolbox**: Performs batch image resizing, formatting, and effects.

##### Media Profile
The parsed track layout, metadata, codecs, and dimensions of a media file.
- **Audio Track**: Sound stream (AAC, MP3, PCM).
- **Video Track**: Visual stream (H.264, VP9, ProRes).
- **Subtitle Track**: Embedded or external timed text (.srt).

##### Recipe
A set of configuration parameters describing the stack of operations (e.g., speed, rotation, crop) to apply to a file.

##### Wizard
The Zenity-based user interface consisting of the **Checklist** (Intent selection) and the **Dashboard** (Forms configuration).

---

### 🧰 Universal FFmpeg Toolbox Detailed Guide

The Swiss Army Knife for video processing. A powerful, workstation-grade tool that combines multiple FFmpeg operations in a single, intelligent workflow with hardware acceleration, smart presets, and professional-grade features.

#### Philosophy
The Universal Toolbox follows the principle of **"Everything in One Pass"** - combining multiple video operations (speed, scale, crop, audio, format) into a single FFmpeg command for maximum efficiency and quality preservation. Instead of running separate tools for each operation, the Universal Toolbox intelligently chains operations to minimize quality loss and processing time.

##### When to Use Universal vs Lossless Toolbox
| Operation | Universal Toolbox | Lossless Toolbox |
|-----------|-------------------|------------------|
| Change resolution | ✅ Required | ❌ Not possible |
| Add filters/effects | ✅ Required | ❌ Not possible |
| Change codecs | ✅ Required | ❌ Not possible |
| Speed adjustment | ✅ With pitch correction | ❌ Not possible |
| Quality optimization | ✅ CRF/bitrate control | ❌ Not applicable |
| Trim video segments | ✅ With re-encoding | ✅ Instant (recommended) |
| Change container | ✅ With re-encoding | ✅ Instant (recommended) |
| Remove audio track | ✅ With re-encoding | ✅ Instant (recommended) |

#### Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIVERSAL_TOOLBOX                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Presets    │  │   History    │  │   Context-Aware UI   │   │
│  │              │  │              │  │                      │   │
│  │ • 2-Step Wiz │  │ • Session    │  │ • Hardware Probing   │   │
│  │ • Distribution│ │ • Smart      │  │ • Dynamic Options    │   │
│  │ • Production  │ │   Conflict   │  │ • Progress tracking  │   │
│  │ └──────────────┘  └──────────────┘  └──────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    FFmpeg Core                                  │
│              (Filter Chaining & HW Accel)                       │
└─────────────────────────────────────────────────────────────────┘
```
> 💡 **Why This Architecture?** By centering the design around a "Unified Filter Chain," we eliminate the need for intermediate temporary files. This reduces disk I/O bottlenecks and prevents the generation-loss that occurs when re-encoding multiple times.

#### Features
##### Core Capabilities
- **🧙‍♂️ 2-Step Guided Wizard**: Streamlined workflow from intent to execution
- **🏎️ Smart Hardware Acceleration**: Auto-detection and optimization for NVENC, QSV, VAAPI
- **⚖️ Precision Target Sizing**: 2-pass encoding to hit exact file size limits
- **🎨 Advanced Filtering**: Speed, scale, crop, rotate, flip, and audio processing
- **📝 Subtitle Integration**: Burn-in and soft-subtitle support with auto-detection
- **🛡️ Safety Features**: Auto-rename protection and graceful error handling

##### Workflow Innovation
- **⭐ Persistent Presets**: Save complex configurations with custom parameters
- **📚 Smart History**: Recent operations with management capabilities
- **🔄 Operation Chaining**: Multiple operations in single pass for optimal quality
- **🔄 Context Awareness**: Dynamic UI based on available files and system capabilities

##### Professional Features
- **🎬 Production Formats**: ProRes, DNxHD, uncompressed workflows
- **🌐 Distribution Optimization**: Platform-specific presets (Twitter, Discord, etc.)
- **🔧 Advanced Controls**: Custom bitrates, quality settings, hardware selection
- **📊 Progress Intelligence**: Real-time feedback with operation-specific progress

#### Usage Guide
##### The 2-Step Wizard

###### Step 1: Unified Wizard
The Unified Wizard combines starting point selection and operation intent in a single checklist interface:
1. **Pick a Starting Point**:
    - **➕ New Custom Edit**: Build a selection from scratch.
    - **⭐ Saved Favorites**: Use previously saved presets.
    - **🕒 Recent History**: Repeat recent operations.
2. **Select Operation Intents**:
    - **⏩ Speed Control**: Change playback speed (fast/slow motion).
    - **📐 Scale / Resize**: Change resolution (1080p, 720p, 4K, custom).
    - **🖼️ Crop / Aspect Ratio**: Vertical (9:16), Square (1:1), Cinema (21:9).
    - **🔄 Rotate & Flip**: Fix orientation issues.
    - **⏱️ Trim (Cut Time)**: Select specific start/end segments.
    - **🔊 Audio Tools**: Normalize, boost, mute, extract, remix.
    - **📝 Subtitles**: Burn-in or mux external subtitle files.

> 💡 **Why a 2-Step Wizard?** Traditional FFmpeg wrappers often bury options in tabs. Our wizard-first approach ensures you only see the configuration settings relevant to your current intent, reducing cognitive load.

###### Step 2: Configuration Dashboard
Unified configuration window with dynamic fields based on selected intents:
```
⏩ Speed: 2x (Fast) ✍️ Custom: [    ]
📐 Resolution: 1080p ✍️ Custom Width: [    ]
🖼️ Crop/Aspect: 16:9 (Landscape)
🔄 Orientation: Rotate 90 CW
⏱️ Trim Start: [00:00:10] ⏱️ Trim End: [00:01:30]
🔊 Audio Action: Normalize (R128)
📝 Subtitles: Burn-in
💎 Quality Strategy: High (CRF 18)
💾 Target Size MB: [25] (overrides quality)
📦 Output Format: Auto/MP4
🏎️ Hardware: Use NVENC (Nvidia)
```

##### Command Line Interface
```bash
# Basic usage with files
./Universal-Toolbox.sh video.mp4

# Use saved presets for automation
./Universal-Toolbox.sh --preset "Social Speed Edit" *.mp4
./Universal-Toolbox.sh --preset "4K Archival (H.265)" video.mov
```

#### Hardware Acceleration
##### Auto-Detection System
The Universal Toolbox performs intelligent hardware probing at startup:
1. **Silent Testing**: 1-frame dummy encode to test each acceleration method
2. **Capability Caching**: Results cached for 24 hours to avoid repeated testing
3. **Smart Fallback**: Automatic CPU fallback if hardware encoding fails
4. **Vendor Optimization**: Specific settings for each hardware type

> 💡 **Why Auto-Detection?** Hardware encoding is powerful but fragile. By probing each method at startup and caching the results, we ensure that you always get the fastest possible encoding without manually troubleshooting driver/codec compatibility.

##### Performance Benefits
| Hardware | Speed Improvement | Quality | Power Usage |
|----------|------------------|---------|-------------|
| NVENC | 3-10x faster | Excellent | Low |
| QSV | 2-5x faster | Very Good | Very Low |
| VAAPI | 2-4x faster | Good | Low |
| CPU | Baseline | Best | High |

#### Target Size System
##### Precision Sizing
The Universal Toolbox can encode videos to exact file sizes using intelligent 2-pass encoding:
1. **Duration Analysis**: Calculates video length and audio requirements
2. **Bitrate Calculation**: Determines optimal video bitrate for target size
3. **Pass 1**: Fast analysis pass to understand video complexity
4. **Pass 2**: Precision encoding to hit exact target size

##### Common Use Cases
```bash
Discord Limit: 25MB
Email Attachment: 9MB
WhatsApp: 16MB
Twitter: 512MB (8 minutes max)
```

#### Technical Details
##### Processing Pipeline
```
    ┌─────────────┐
    │   Input     │
    │   Files     │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Deep Scan  │ ← Analyze media profile
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │ Hardware    │ ← Probe for NVENC/QSV/VAAPI
    │ Detection   │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Filter     │ ← Speed + Scale + Crop + Audio
    │  Chaining   │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Encoding   │ ← Single-pass high-quality output
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Output     │ ← Descriptive-named result
    └─────────────┘
```
> 💡 **Why Single-Pass?** Running separate operations creates quality degradation with each pass. The Universal Toolbox chains all filters into one FFmpeg command, preserving maximum quality while being 3-5x faster.

##### Configuration
```bash
Config Directory: ~/.config/scripts-sh/universal/
Presets: presets.conf
History: history.conf (last 15 operations)
GPU Cache: /tmp/scripts-sh-gpu-cache (24h TTL)
```

#### Troubleshooting
##### Common Issues
- **Hardware Acceleration Not Working**: Check GPU drivers and FFmpeg compilation, review `/tmp/scripts-sh-gpu-cache` for detection results, or use CPU fallback if hardware fails.
- **Target Size Too Small**: Increase target size or reduce duration, consider lower resolution or frame rate, and check audio bitrate allocation.

#### Gotchas & Warnings
- **NVENC Quality**: NVIDIA encoding uses CQP/VBR — CRF not directly equivalent to x264.
- **Target Size Minimum**: Cannot reliably encode below ~0.5 Mbps for HD content.
- **Speed Limits**: Audio pitch correction fails above 4x or below 0.14x speed.
- **HDR Warning**: Tone mapping to SDR requires manual filter configuration.
- **Subtitle Burn-in**: Once burned, subtitles cannot be removed or toggled.
- **Hardware Fallback**: May silently fall back to CPU if GPU encoding fails.

#### Quick Reference
##### Common Commands
| Goal | Command/Action |
|------|----------|
| Fast social media clip | `./Universal-Toolbox.sh --preset "Social Speed Edit" video.mp4` |
| YouTube upload ready | `./Universal-Toolbox.sh --preset "YouTube 1080p (Fast)" *.mov` |
| Discord-friendly size | Set Target Size: 25MB in wizard |
| Archive quality | `./Universal-Toolbox.sh --preset "4K Archival (H.265)" video.mp4` |

#### Common Workflows
##### Social Media Content Creator
1. **Record long video** → Universal: Speed 2x + Scale 720p + Crop 9:16.
2. **Add subtitles** → Universal: Burn-in SRT.
3. **Optimize size** → Universal: Target Size 25MB (Discord).

##### YouTube Content Pipeline
1. **Edit in NLE** → Export as ProRes.
2. **Compress for upload** → Universal: Scale 1080p + H.264 + Normalize.
3. **Archive master** → Universal: H.265 + High Quality.

---

### 🔒 Lossless Operations Toolbox Detailed Guide

A specialized FFmpeg tool focused exclusively on quality-preserving video operations using stream copy functionality. No re-encoding, no quality loss, lightning-fast processing.

#### Philosophy
The Lossless Operations Toolbox follows the principle that **not every video operation requires transcoding**. Many common tasks like trimming, format conversion, and metadata editing can be performed instantly without touching the actual video/audio streams.

##### When to Use Lossless vs Universal Toolbox
| Operation | Lossless Toolbox | Universal Toolbox |
|-----------|------------------|-------------------|
| Trim video segments | ✅ Instant | ❌ Slow (re-encodes) |
| Change container (MP4→MKV) | ✅ Instant | ❌ Unnecessary re-encoding |
| Remove audio track | ✅ Instant | ❌ Re-encodes video |
| Clean metadata | ✅ Instant | ❌ Re-encodes everything |
| Merge compatible files | ✅ Instant | ❌ Re-encodes all files |
| Change resolution | ❌ Not possible | ✅ Required |
| Add filters/effects | ❌ Not possible | ✅ Required |
| Change codecs | ❌ Not possible | ✅ Required |

#### Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    LOSSLESS_TOOLBOX                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Presets    │  │   History    │  │   Context-Aware UI   │   │
│  │              │  │              │  │                      │   │
│  │ • Remuxing   │  │ • Session    │  │ • Stream Detection   │   │
│  │ • Trimming   │  │ • Smart      │  │ • Codec Validation  │   │
│  │ • Metadata   │  │   Conflict   │  │ • Progress bars     │   │
│  │ └──────────────┘  └──────────────┘  └──────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    FFmpeg Core                                  │
│              (Stream Copy -c copy)                              │
└─────────────────────────────────────────────────────────────────┘
```
> 💡 **Why This Architecture?** By isolating lossless operations into a dedicated tool, we avoid the overhead of complex filtergraph construction and ensure that bit-for-bit stream preservation is the default state, rather than an option.

#### Features
##### Core Operations
- **✂️ Trimming**: Extract time segments with frame-accurate cutting
- **📦 Remuxing**: Change container formats (MP4, MKV, MOV, WebM)
- **🔗 Merging**: Concatenate files with identical codec parameters
- **🎚️ Stream Editing**: Remove or select specific audio/video tracks
- **📝 Metadata Editing**: Modify file information without touching streams
- **⚡ Batch Processing**: Apply operations to multiple files simultaneously

##### Enhanced User Experience
- **⭐ Preset System**: Save and reuse common operations
- **📚 History Tracking**: Quick access to recent operations
- **🔧 Smart Validation**: Prevents incompatible operations with helpful suggestions
- **🛡️ Auto-Rename**: Intelligent file naming to prevent overwrites
- **⌨️ CLI Support**: Command-line automation with preset support

##### Technical Excellence
- **🚀 Zero Quality Loss**: All operations use FFmpeg `-c copy` (stream copy)
- **⚡ Lightning Speed**: Operations complete in seconds, not minutes
- **🎯 Codec Validation**: Comprehensive compatibility checking
- **📦 Container Optimization**: Format-specific flags for better compatibility
- **🔍 Smart Detection**: Automatic subtitle and metadata detection

#### Usage Guide
##### Interactive Mode
1. **Right-click** on video files in Nautilus.
2. Select **Scripts** → **Lossless-Operations-Toolbox**.
3. Choose from the enhanced menu:
   - **New Operation**: Select from available lossless operations.
   - **⭐ Presets**: Use saved favorites.
   - **🕒 History**: Repeat recent operations.

##### Command Line Interface
```bash
# Basic usage
./Lossless-Operations-Toolbox.sh video.mp4

# Use presets for automation
./Lossless-Operations-Toolbox.sh --preset "Quick Trim" *.mp4

# List available presets
./Lossless-Operations-Toolbox.sh --list-presets

# Show help
./Lossless-Operations-Toolbox.sh --help
```

##### Time Format Support
The toolbox accepts flexible time formats for trimming operations:
```bash
# Seconds
Start: 30
End: 120

# Minutes:Seconds
Start: 1:30
End: 2:00

# Hours:Minutes:Seconds
Start: 01:30:45
End: 02:15:30
```

#### Operation Details
##### Trimming (✂️)
Extract video segments without re-encoding. Perfect for creating clips, removing unwanted sections, or splitting long videos.
- **Use Cases**: Create social media clips, remove intro/outro sections, extract highlights, or split long videos.
- **Validation**: Checks file duration and time ranges, prevents invalid times, and warns about keyframe accuracy limits.

> 💡 **Why Lossless Trimming?** Unlike re-encoding, stream copy trimming reads only the needed bytes from the source file. A 1-hour video trimmed to 30 seconds takes the same 2-3 seconds regardless of source duration.

##### Container Remuxing (📦)
Change video container format instantly while preserving all streams and quality.
- **Supported Formats**: MP4 (universal compatibility), MKV (supports all codecs), MOV (Apple ecosystem), WebM (web-optimized).
- **Optimization Features**: MP4 (`+faststart` for web streaming), MKV (index space reservation for seeking), MOV (QuickTime compatibility flags).

##### File Merging (🔗)
Concatenate multiple video files with identical codec parameters.
- **Requirements**: Matching video/audio codecs. Container format can differ (will be unified).
- **Smart Validation**: Checks stream profiles, level, and framerates to ensure a stable output before concatenation.

#### Preset System
##### Default Presets
```bash
Quick Trim      # Extract 2-8 second segments
MP4 to MKV      # Convert container format
Remove Audio    # Strip audio tracks
Clean Metadata  # Remove privacy information
Merge Compatible # Concatenate matching files
```

##### Creating Custom Presets
1. Perform an operation interactively.
2. Choose "Save as Preset" when prompted.
3. Enter a descriptive name.
4. Use via CLI: `--preset "Your Preset Name"`.

#### Technical Details
##### Processing Pipeline
```
    ┌─────────────┐
    │   Input     │
    │   Files     │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Deep Scan  │ ← Analyze streams (Video/Audio/Sub)
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Validation │ ← Check codec compatibility for -c copy
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Remuxing   │ ← Stream copy to target container
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Output     │ ← Bit-perfect lossless result
    └─────────────┘
```
> 💡 **Why Stream Copy?** Unlike traditional transcoding that decodes and re-encodes every frame, the Lossless Toolbox simply "re-wraps" existing data into new containers. This preserves original quality and is limited only by disk I/O speed.

##### Configuration
```bash
Config Directory: ~/.config/scripts-sh/lossless/
Presets: presets.conf
History: history.conf (last 15 operations)
Format: Pipe-separated values for easy parsing
```

#### Gotchas & Warnings
- **Keyframe Trimming**: Lossless cuts can only happen at keyframes — expect ±1 frame inaccuracy.
- **Merge Limitations**: Files MUST have identical codecs, resolution, and framerate.
- **Subtitle Handling**: Embedded subtitles are preserved, but external `.srt` files are not auto-detected.
- **Chapter Markers**: May be lost during remuxing depending on container format.
- **HDR Content**: HDR metadata is preserved, but tone mapping requires re-encoding (use Universal Toolbox).

#### Quick Reference
##### Common Commands
| Goal | Command/Action |
|------|----------|
| Trim first 30 seconds | `./Lossless-Operations-Toolbox.sh --preset "Quick Trim" video.mp4` |
| Convert to MKV | `./Lossless-Operations-Toolbox.sh --preset "MP4 to MKV" *.mp4` |
| Remove audio track | `./Lossless-Operations-Toolbox.sh --preset "Remove Audio" video.mp4` |
| Clean metadata | `./Lossless-Operations-Toolbox.sh --preset "Clean Metadata" video.mp4` |

#### Common Workflows
##### Social Media Content Creator
1. **Record long video** → Lossless: Trim to highlight segment.
2. **Remove metadata** → Lossless: Clean Metadata (privacy).
3. **Convert format** → Lossless: MP4 to MKV (if needed).

##### Video Archival
1. **Collect recordings** → Lossless: Merge Compatible.
2. **Clean up** → Lossless: Clean Metadata.
3. **Repackage** → Lossless: Remux to MKV (preserves all streams).

---

### 🖼️ ImageMagick Toolbox Detailed Guide

The **ImageMagick Toolbox** (`Image-Magick-Toolbox.sh`) is a high-performance batch image processing utility designed for Nautilus. It leverages `imagemagick` and `zenity` to provide a user-friendly GUI for complex image manipulation tasks.

#### Philosophy
The ImageMagick Toolbox follows the principle of **"Parallel Processing + Smart Logic"** - using ImageMagick's powerful command-line tools with intelligent defaults and automated format handling to deliver professional results at maximum speed.

##### When to Use ImageMagick Toolbox
| Operation | ImageMagick Toolbox | Alternative Tools |
|-----------|---------------------|-------------------|
| Batch resize | ✅ Required | ❌ GIMP (manual) |
| Format conversion | ✅ Required | ❌ Online converters |
| Grid/Montage creation | ✅ Required | ❌ Photoshop |
| PDF merge/extract | ✅ Required | ❌ Dedicated PDF tools |
| Watermarking | ✅ Required | ❌ Manual editing |
| Single image edit | ⚠️ Overkill | ✅ GIMP/Photoshop |

#### Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    IMAGEMAGICK_TOOLBOX                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Presets    │  │   History    │  │   Context-Aware UI   │   │
│  │              │  │              │  │                      │   │
│  │ • Quick      │  │ • Undo/Redo  │  │ • Auto-detect type  │   │
│  │ • Custom     │  │ • Session    │  │ • Smart defaults    │   │
│  │ • Named      │  │ • Branching  │  │ • Progress bars     │   │
│  │ └──────────────┘  └──────────────┘  └──────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    ImageMagick Core                             │
│              (convert, mogrify, identify)                       │
└─────────────────────────────────────────────────────────────────┘
```
> 💡 **Why This Architecture?** By decoupling the UI (Zenity) from the processing logic (ImageMagick), we can provide a rich interactive experience while maintaining the raw performance of command-line tools. The middleware layer handles history, presets, and parallel job orchestration.

#### Features
##### Core Capabilities
- **⚡ Parallel Processing**: Uses background jobs to process image libraries at maximum CPU speed.
- **📱 Modern Format Support**: Automated handling of **HEIC/RAW** to sRGB JPG conversion.
- **🛡️ Non-Destructive**: Always creates new files with smart naming (e.g., `image_web_sq.jpg`), never overwriting originals.
- **📊 Progress Tracking**: Visual progress bar for batch operations with real-time feedback.
- **🚨 Error Reporting**: Detailed error logs shown if any files fail to process.
- **💎 Dynamic Preset Naming**: Automatically suggests descriptive names for favorites based on selected operations (e.g., `scale128x128_jpg_q85`).

##### Operation Categories
###### 1. 📏 Scale & Resize
- **Presets**: 4K, HD, 720p, 640p, 50%.
- **Custom**: Enter any geometry (e.g., `800x600`, `x500`).
- **Smart Logic**: Preserves aspect ratio by default.

###### 2. ✂️ Crop & Geometry
- **Square Crop (1:1)**: Automatically crops the center square.
- **Vertical (9:16)**: Standard mobile aspect ratio.
- **Landscape (16:9)**: Standard widescreen format.

###### 3. 🖼️ Montage & Grid
- **2x / 3x Grid**: Creates a high-resolution grid montage.
- **Single Row/Column**: Stitches images together at full resolution.
- **Contact Sheet**: Creates a sheet of thumbnails (200x200) for overview.

###### 4. 📦 Format Converter
- **Outputs**: JPG, PNG, WEBP, TIFF, PDF.
- **PDF Merging**: Multiple images → Single multi-page PDF.
- **PDF Extraction**: Extracts all PDF pages as high-DPI images (300 DPI).

#### Usage Guide
##### Interactive Mode
1. **Select Images**: Highlight one or more images in Nautilus.
2. **Right-Click → Scripts → Image-Magick-Toolbox**.
3. **Choose Intent**: Select what you want to do (e.g., "Scale", "Canvas", "Format").
4. **Configure**: Fine-tune settings in the pop-up form.
5. **Run**: The script processes files in the background.

##### Context-Aware UI
The toolbox automatically adapts its interface based on the selected files:
- **Image Files**: Shows scale, crop, format, effects, and montage options.
- **PDF Files**: Shows extract pages option.
- **CMYK Images**: Shows convert to sRGB option.

> 💡 **Why Context-Aware?** Most users don't know ImageMagick's internal formats. Auto-detection reduces cognitive load and prevents errors like trying to apply JPEG-specific operations to PNG files.

##### Command Line Interface
```bash
# Basic usage with files
./Image-Magick-Toolbox.sh image1.jpg image2.png

# Process entire directory
./Image-Magick-Toolbox.sh /path/to/images/*.jpg
```

#### Technical Details
##### Processing Pipeline
```
    ┌─────────────┐
    │   Input     │
    │   Files     │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Deep Scan  │ ← Analyze media properties (identify)
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Filter UI  │ ← Show only relevant options (Zenity)
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Process    │ ← Single-pass parallel execution
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Output     │ ← Smart-named files
    └─────────────┘
```
The toolbox processes images in a specific order to ensure optimal results:
1. **Crop/Geometry**: Applied first to establish final dimensions.
2. **Scale/Resize**: Applied after crop for precise sizing.
3. **Effects**: Color corrections, rotations, etc.
4. **Format/Optimization**: Final output format and quality.

##### Wizard & Parser Logic
The UI handles complex multi-selection parsing to ensure logical workflow execution:
- **Intents**: Operations are grouped as "Intents" which return distinct IDs.
- **Selective Parsing**: The parser (`common/wizard.sh`) uses column-aware logic to extract only relevant operation IDs from Zenity's multi-column output, ignoring UI metadata (icons, descriptions).
- **Sub-Dialog Stacking**: Triggers respective sub-dialogs sequentially before processing.
- **Recipe Builder**: Choices are aggregated into a pipe-separated "Recipe" string for presets/commands.

##### Parallel Processing
```bash
# Default: 4 parallel jobs (adjusts to CPU count)
MAX_JOBS=4
[ $(nproc) -lt 4 ] && MAX_JOBS=$(nproc)
```

##### Configuration
```bash
Config Directory: ~/.config/scripts-sh/imagemagick/
Presets: presets.conf
History: history.conf (last 15 operations)
Format: Pipe-separated values for easy parsing
```

#### Gotchas & Warnings
- **HEIC Support**: Requires `libheif` installed separately (`sudo apt install libheif-examples`).
- **Memory Usage**: Large images consume significant RAM. Processing 50+ at once can trigger OOM without parallel limits.
- **PDF Page Order**: Pages are merged in alphabetical order by filename.
- **CMYK Warning**: CMYK images may appear "neon" or washed out until converted to sRGB.
- **Lossy Operations**: Brightness/Contrast adjustments on JPEGs are lossy. Work on PNGs for multi-step editing.

#### Quick Reference
##### Common Commands
| Goal | Action |
|------|----------|
| Resize to web size | `./Image-Magick-Toolbox.sh --preset "Web Ready" *.jpg` |
| Create Instagram square | `./Image-Magick-Toolbox.sh --preset "Square Crop" photo.jpg` |
| Convert HEIC to JPG | Select files → Format → JPG |
| Merge images to PDF | Select files → Format → PDF |
| Extract PDF pages | Select PDF → Format → JPG/PNG |

#### Common Workflows
##### Social Media Content Creator
1. **Record photo** → ImageMagick: Square Crop + Web Ready.
2. **Create story** → ImageMagick: Vertical (9:16) + Watermark.

##### E-commerce Product Photos
1. **Batch resize** → Scale to 1920px max.
2. **Format convert** → WebP for modern browsers.
3. **Create thumbnails** → Contact Sheet for overview.

---

### 🗺️ Toolbox Ecosystem Roadmap (2026)

This roadmap outlines the strategic evolution of the three core toolboxes: **Universal** (Video Transcode), **Lossless** (Video Stream Copy), and **ImageMagick** (Image Raster).

#### 🎯 North Star Vision
Create a **Unified Creative Suite** for Linux users that acts as a **Smart Assistant**, continuously analyzing your media to offer *only* the relevant tools.

#### 🏗️ Phase 1: Foundation & Standardization (Complete)
*Goal: Ensure all tools share a common design language and core reliability.*
- [x] **UX Alignment**: Refactored ImageMagick to match Lossless Menu pattern.
- [x] **Safe Filenaming**: smart conflict resolution.
- [x] **Documentation**: Centralized docs.

#### 🧩 Phase 2: The "Smart Builder" Architecture (Completed)
*Goal: Enable complex workflows that adapt to the user.*

##### 🔄 The "Context-Aware" Loop
Migrate all tools to a **Dynamic Recipe Builder** backed by **Deep Analysis**:
1. **Pre-Flight Deep Scan**: Before showing the menu, run `ffprobe` or `identify` to build a **Media Profile**:
   - **Tracks**: Does it have Audio? Subtitles? Chapters?
   - **Visuals**: Is it HDR? CMYK? Transparent (Alpha)?
   - **Metadata**: Does it have GPS info? Rotation flags?
2. **Dynamic Option Filtering (The "Grey Out" Logic)**:
   - **Audio Logic**: *No Audio Track found?* -> **Hide** "Remove Audio", "Normalize", "Extract MP3".
   - **Subtitle Logic**: *No Subtitles found?* -> **Hide** "Burn-in Subs", "Extract SRT".
   - **Image Logic**:
     - *Has Alpha Channel?* -> **Show** "Flatten Background" or "Shadow Effect".
     - *Is CMYK?* -> **Show** "Fix Colors (to sRGB)".
     - *Has GPS Data?* -> **Show** "Privacy Scrub (Remove Location)".
   - **Video Logic**:
     - *Is HDR10/Dolby?* -> **Show** "Tone Map to SDR".
     - *Is Vertical (9:16)?* -> **Show** "Blur-Pad to Landscape".

##### 🛠️ Tasks
- [x] **Analysis Engine**: Create `analyze_media_deep(file)` function returning a state object.
- [x] **UI Engine**: Update Zenity generator to read this state and filter list items.

#### ⚡ Phase 3: Performance & Intelligence (Q3 2026)
*Goal: Make the tools faster and smarter.*

##### 🏎️ Performance
- [ ] **Smart Parallelism**: Auto-detect CPU cores.
- [ ] **GPU Auto-Switch**: Self-healing fallback to CPU on error.

##### 🧠 Intelligence
- [ ] **Content-Aware Crop**: Auto-crop to subject (entropy/attention).
- [ ] **Scene Splitter**: Auto-cut at scene changes.
- [ ] **Silence Trimmer**: Remove silent segments.

#### 📦 Phase 4: Distribution & Integration (Q4 2026)
*Goal: Move beyond "Scripts" to "Applications".*
- [ ] **Desktop Entry Generator**: Create `.desktop` files.
- [ ] **Auto-Updater**: Built-in `--update` flag.
- [ ] **Interactive Tour**: First-run explanation of features.

#### 🧪 Experimental
- [ ] **AI Tagging**: Local LLM description/renaming.

#### 🏗️ Phase 5: Quality & Test Maturity (Future)
*Goal: Address technical debt and close the remaining testing gaps.*
- [ ] **Unified Lossless Testing**: Migration of `test_lossless_toolbox.sh` to use end-to-end `validate_media` rules (Closing the validation gap).
- [ ] **Missing Operation Coverage**: 
  - [ ] Added tests for subtitle burn-in/embed tasks.
  - [ ] Hardware encoding (NVENC/QSV) verification suite.
  - [ ] Image watermark and custom-sizing validation.
- [ ] **Test Engine Hardening**: 
  - [ ] Refactor `run_test` output detection for better robustness.
  - [ ] Implement tighter duration tolerances (±0.1s) for lossless verification.
  - [ ] Fix FPS rounding issues in `validate_media`.

---

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

2. **Follow Code Style**: Maintain consistency with existing scripts:
   - Use bash 4.0+ features
   - Include `-nostdin` flag in all FFmpeg commands
   - Source shared utilities from [`common/`](common/) directory
   - Use the unified wizard system for UI dialogs

3. **Test Negative Paths**: Ensure your changes handle cancellations and errors gracefully.

### Reporting Issues

- Use GitHub Issues for bug reports and feature requests.
- Include steps to reproduce and expected vs. actual behavior.
- Attach relevant logs from `~/.local/share/scripts-sh/debug.log` when applicable.

## 📜 License

MIT License. Feel free to use and modify for your own workflow.
