# 🧰 Universal FFmpeg Toolbox

The Swiss Army Knife for video processing. A powerful, workstation-grade tool that combines multiple FFmpeg operations in a single, intelligent workflow with hardware acceleration, smart presets, and professional-grade features.

## 📋 Table of Contents

- [Philosophy](#-philosophy)
- [Architecture](#-architecture)
- [Features](#-features)
- [Usage Guide](#-usage-guide)
- [Hardware Acceleration](#-hardware-acceleration)
- [Target Size System](#-target-size-system)
- [Technical Details](#-technical-details)
- [Testing & Validation](#-testing--validation)
- [Troubleshooting](#-troubleshooting)
- [Gotchas & Warnings](#-gotchas--warnings)
- [Quick Reference](#-quick-reference)
- [Common Workflows](#-common-workflows)

## 🎯 Philosophy

The Universal Toolbox follows the principle of **"Everything in One Pass"** - combining multiple video operations (speed, scale, crop, audio, format) into a single FFmpeg command for maximum efficiency and quality preservation. Instead of running separate tools for each operation, the Universal Toolbox intelligently chains operations to minimize quality loss and processing time.

### When to Use Universal vs Lossless Toolbox

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

---

## 🏗️ Architecture

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
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    FFmpeg Core                                  │
│              (Filter Chaining & HW Accel)                       │
└─────────────────────────────────────────────────────────────────┘
```

> 💡 **Why This Architecture?** By centering the design around a "Unified Filter Chain," we eliminate the need for intermediate temporary files. This reduces disk I/O bottlenecks and prevents the generation-loss that occurs when re-encoding multiple times.

---

## 🚀 Features

### Core Capabilities
- **🧙‍♂️ 2-Step Guided Wizard**: Streamlined workflow from intent to execution
- **🏎️ Smart Hardware Acceleration**: Auto-detection and optimization for NVENC, QSV, VAAPI
- **⚖️ Precision Target Sizing**: 2-pass encoding to hit exact file size limits
- **🎨 Advanced Filtering**: Speed, scale, crop, rotate, flip, and audio processing
- **📝 Subtitle Integration**: Burn-in and soft-subtitle support with auto-detection
- **🛡️ Safety Features**: Auto-rename protection and graceful error handling

### Workflow Innovation
- **⭐ Persistent Presets**: Save complex configurations with custom parameters
- **📚 Smart History**: Recent operations with management capabilities
- **🔄 Operation Chaining**: Multiple operations in single pass for optimal quality
- **🎯 Context Awareness**: Dynamic UI based on available files and system capabilities

### Professional Features
- **🎬 Production Formats**: ProRes, DNxHD, uncompressed workflows
- **🌐 Distribution Optimization**: Platform-specific presets (Twitter, Discord, etc.)
- **🔧 Advanced Controls**: Custom bitrates, quality settings, hardware selection
- **📊 Progress Intelligence**: Real-time feedback with operation-specific progress

---

## 📖 Usage Guide

### The 2-Step Wizard

#### Step 1: Unified Wizard
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

#### Step 2: Configuration Dashboard
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

### Command Line Interface

```bash
# Basic usage with files
./🧰\ Universal-Toolbox.sh video.mp4

# Use saved presets for automation
./🧰\ Universal-Toolbox.sh --preset "Social Speed Edit" *.mp4
./🧰\ Universal-Toolbox.sh --preset "4K Archival (H.265)" video.mov
```

---

## 🏎️ Hardware Acceleration

### Auto-Detection System
The Universal Toolbox performs intelligent hardware probing at startup:

1. **Silent Testing**: 1-frame dummy encode to test each acceleration method
2. **Capability Caching**: Results cached for 24 hours to avoid repeated testing
3. **Smart Fallback**: Automatic CPU fallback if hardware encoding fails
4. **Vendor Optimization**: Specific settings for each hardware type

> 💡 **Why Auto-Detection?** Hardware encoding is powerful but fragile. By probing each method at startup and caching the results, we ensure that you always get the fastest possible encoding without manually troubleshooting driver/codec compatibility.

### Performance Benefits
| Hardware | Speed Improvement | Quality | Power Usage |
|----------|------------------|---------|-------------|
| NVENC | 3-10x faster | Excellent | Low |
| QSV | 2-5x faster | Very Good | Very Low |
| VAAPI | 2-4x faster | Good | Low |
| CPU | Baseline | Best | High |

---

## ⚖️ Target Size System

### Precision Sizing
The Universal Toolbox can encode videos to exact file sizes using intelligent 2-pass encoding:

#### How It Works
1. **Duration Analysis**: Calculates video length and audio requirements
2. **Bitrate Calculation**: Determines optimal video bitrate for target size
3. **Pass 1**: Fast analysis pass to understand video complexity
4. **Pass 2**: Precision encoding to hit exact target size

#### Common Use Cases
```bash
Discord Limit: 25MB
Email Attachment: 9MB
WhatsApp: 16MB
Twitter: 512MB (8 minutes max)
```

---

## 🔧 Technical Details

### Processing Pipeline

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

### Configuration

```bash
Config Directory: ~/.config/scripts-sh/universal/
Presets: presets.conf
History: history.conf (last 15 operations)
GPU Cache: /tmp/scripts-sh-gpu-cache (24h TTL)
```

---

## 🧪 Testing & Validation

### Automated Testing
The Universal Toolbox includes comprehensive testing through the unified test runner:

```bash
# Run all Universal Toolbox tests
bash testing/test_runner.sh
```

---

## 🔍 Troubleshooting

### Common Issues

**Hardware Acceleration Not Working**
- Check GPU drivers and FFmpeg compilation
- Review `/tmp/scripts-sh-gpu-cache` for detection results
- Use CPU fallback if hardware fails

**Target Size Too Small**
- Increase target size or reduce duration
- Consider lower resolution or frame rate
- Check audio bitrate allocation

---

## ⚠️ Gotchas & Warnings

- **NVENC Quality**: NVIDIA encoding uses CQP/VBR — CRF not directly equivalent to x264
- **Target Size Minimum**: Cannot reliably encode below ~0.5 Mbps for HD content
- **Speed Limits**: Audio pitch correction fails above 4x or below 0.14x speed
- **HDR Warning**: Tone mapping to SDR requires manual filter configuration
- **Subtitle Burn-in**: Once burned, subtitles cannot be removed or toggled
- **Hardware Fallback**: May silently fall back to CPU if GPU encoding fails

---

## 📇 Quick Reference

### Common Commands

| Goal | Command |
|------|----------|
| Fast social media clip | `./🧰\ Universal-Toolbox.sh --preset "Social Speed Edit" video.mp4` |
| YouTube upload ready | `./🧰\ Universal-Toolbox.sh --preset "YouTube 1080p (Fast)" *.mov` |
| Discord-friendly size | Set Target Size: 25MB in wizard |
| Archive quality | `./🧰\ Universal-Toolbox.sh --preset "4K Archival (H.265)" video.mp4` |

---

## 📚 Common Workflows

### Social Media Content Creator
1. **Record long video** → Universal: Speed 2x + Scale 720p + Crop 9:16
2. **Add subtitles** → Universal: Burn-in SRT
3. **Optimize size** → Universal: Target Size 25MB (Discord)

### YouTube Content Pipeline
1. **Edit in NLE** → Export as ProRes
2. **Compress for upload** → Universal: Scale 1080p + H.264 + Normalize
3. **Archive master** → Universal: H.265 + High Quality

---

*The Universal Toolbox represents the pinnacle of FFmpeg workflow optimization - combining professional capabilities with consumer-friendly automation to deliver studio-quality results at unprecedented speed and convenience.*
