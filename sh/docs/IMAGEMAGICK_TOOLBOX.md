# 🖼️ ImageMagick Toolbox

The **ImageMagick Toolbox** (`🖼️ Image-Magick-Toolbox.sh`) is a high-performance batch image processing utility designed for Nautilus. It leverages `imagemagick` and `zenity` to provide a user-friendly GUI for complex image manipulation tasks.

## 📋 Table of Contents

- [Philosophy](#-philosophy)
- [Architecture](#-architecture)
- [Features](#-features)
- [Usage Guide](#-usage-guide)
- [Configuration](#-configuration)
- [Technical Details](#-technical-details)
- [Testing & Validation](#-technical-details)
- [Troubleshooting](#-troubleshooting)
- [Gotchas & Warnings](#-gotchas--warnings)
- [Quick Reference](#-quick-reference)
- [Common Workflows](#-common-workflows)

## 🎯 Philosophy

The ImageMagick Toolbox follows the principle of **"Parallel Processing + Smart Logic"** - using ImageMagick's powerful command-line tools with intelligent defaults and automated format handling to deliver professional results at maximum speed.

### When to Use ImageMagick Toolbox

| Operation | ImageMagick Toolbox | Alternative Tools |
|-----------|---------------------|-------------------|
| Batch resize | ✅ Required | ❌ GIMP (manual) |
| Format conversion | ✅ Required | ❌ Online converters |
| Grid/Montage creation | ✅ Required | ❌ Photoshop |
| PDF merge/extract | ✅ Required | ❌ Dedicated PDF tools |
| Watermarking | ✅ Required | ❌ Manual editing |
| Single image edit | ⚠️ Overkill | ✅ GIMP/Photoshop |

---

## 🏗️ Architecture

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
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    ImageMagick Core                             │
│              (convert, mogrify, identify)                       │
└─────────────────────────────────────────────────────────────────┘
```

> 💡 **Why This Architecture?** By decoupling the UI (Zenity) from the processing logic (ImageMagick), we can provide a rich interactive experience while maintaining the raw performance of command-line tools. The middleware layer handles history, presets, and parallel job orchestration.

---

## 🚀 Features

### Core Capabilities
- **⚡ Parallel Processing**: Uses background jobs to process image libraries at maximum CPU speed.
- **📱 Modern Format Support**: Automated handling of **HEIC/RAW** to sRGB JPG conversion.
- **🛡️ Non-Destructive**: Always creates new files with smart naming (e.g., `image_web_sq.jpg`), never overwriting originals.
- **📊 Progress Tracking**: Visual progress bar for batch operations with real-time feedback.
- **🚨 Error Reporting**: Detailed error logs shown if any files fail to process.
- **💎 Dynamic Preset Naming**: Automatically suggests descriptive names for favorites based on your selected operations (e.g., `scale128x128_jpg_q85`).

### Operation Categories

#### 1. 📏 Scale & Resize
- **Presets**: 4K, HD, 720p, 640p, 50%.
- **Custom**: Enter any geometry (e.g., `800x600`, `x500`).
- **Smart Logic**: Preserves aspect ratio by default.

#### 2. ✂️ Crop & Geometry
- **Square Crop (1:1)**: Automatically crops the center square.
- **Vertical (9:16)**: Standard mobile aspect ratio.
- **Landscape (16:9)**: Standard widescreen format.

#### 3. 🖼️ Montage & Grid
- **2x / 3x Grid**: Creates a high-resolution grid montage.
- **Single Row/Column**: Stitches images together at full resolution.
- **Contact Sheet**: Creates a sheet of thumbnails (200x200) for overview.

#### 4. 📦 Format Converter
- **Outputs**: JPG, PNG, WEBP, TIFF, PDF.
- **PDF Merging**: Multiple images → Single multi-page PDF.
- **PDF Extraction**: Extracts all PDF pages as high-DPI images (300 DPI).

---

## 📖 Usage Guide

### Interactive Mode

1. **Select Images**: Highlight one or more images in Nautilus.
2. **Right-Click → Scripts → 🖼️ Image-Magick-Toolbox**.
3. **Choose Intent**: Select what you want to do (e.g., "Scale", "Canvas", "Format").
4. **Configure**: Fine-tune settings in the pop-up form.
5. **Run**: The script processes files in background.

### Context-Aware UI

The toolbox automatically adapts its interface based on the selected files:

- **Image Files**: Shows scale, crop, format, effects, and montage options.
- **PDF Files**: Shows extract pages option.
- **Video Files**: Shows remove audio option.
- **CMYK Images**: Shows convert to sRGB option.

> 💡 **Why Context-Aware?** Most users don't know ImageMagick's internal formats. Auto-detection reduces cognitive load and prevents errors like trying to apply JPEG-specific operations to PNG files.

### Command Line Interface

```bash
# Basic usage with files
./🖼️\ Image-Magick-Toolbox.sh image1.jpg image2.png

# Process entire directory
./🖼️\ Image-Magick-Toolbox.sh /path/to/images/*.jpg
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

### Wizard & Parser Logic (Fix 2)

The UI handles complex multi-selection parsing to ensure logical workflow execution:
- **Intents**: Operations are grouped as "Intents" which return distinct IDs.
- **Selective Parsing**: The parser (`common/wizard.sh`) uses a column-aware logic to extract only relevant operation IDs from Zenity's multi-column output, ignoring UI metadata (icons, descriptions).
- **Sub-Dialog Stacking**: If multiple complex operations are selected (e.g., *Scale: Custom* and *Convert Format*), the script stacks them and triggers their respective sub-dialogs sequentially before the final processing begins.
- **Recipe Builder**: Choices are aggregated into a pipe-separated "Recipe" string, which is used for both command building and persistent preset storage.

### Parallel Processing

```bash
# Default: 4 parallel jobs (adjusts to CPU count)
MAX_JOBS=4
[ $(nproc) -lt 4 ] && MAX_JOBS=$(nproc)
```

### Configuration

```bash
Config Directory: ~/.config/scripts-sh/imagemagick/
Presets: presets.conf
History: history.conf (last 15 operations)
Format: Pipe-separated values for easy parsing
```

> 💡 **Why JSON-based presets?** JSON provides human-readable configuration that's easy to edit, version control, and share. Unlike binary formats, you can diff preset changes in git.

---

## 🧪 Testing & Validation

### Automated Testing
The ImageMagick Toolbox includes testing through the unified test runner:

```bash
# Run ImageMagick tests
bash testing/test_image_toolbox.sh
```

---

## 🔍 Troubleshooting

### Common Issues

**"Command not found: magick"**
- Ensure ImageMagick is installed: `sudo apt install imagemagick`
- Check version: `magick -version`

**"Memory limit exceeded"**
- Reduce batch size or image dimensions.
- Increase ImageMagick memory limits in `policy.xml`.

---

## ⚠️ Gotchas & Warnings

- **HEIC Support**: Requires `libheif` installed separately (`sudo apt install libheif-examples`).
- **Memory Usage**: Large images (e.g., 4K+) consume significant RAM (~36MB per 12MP image). Processing 50+ at once can trigger OOM without parallel limits.
- **PDF Page Order**: Pages are merged in alphabetical order by filename.
- **CMYK Warning**: CMYK images may appear "neon" or washed out until converted to sRGB for web use.
- **Lossy Operations**: Brightness/Contrast adjustments on JPEGs are lossy. Work on PNGs for multi-step editing.

---

## 📇 Quick Reference

| Goal | Command |
|------|----------|
| Resize to web size | `./🖼️\ Image-Magick-Toolbox.sh --preset "Web Ready" *.jpg` |
| Create Instagram square | `./🖼️\ Image-Magick-Toolbox.sh --preset "Square Crop" photo.jpg` |
| Convert HEIC to JPG | Select files → Format → JPG |
| Merge images to PDF | Select files → Format → PDF |
| Extract PDF pages | Select PDF → Format → JPG/PNG |

---

## 📚 Common Workflows

### Social Media Content Creator
1. **Record photo** → ImageMagick: Square Crop + Web Ready.
2. **Create story** → ImageMagick: Vertical (9:16) + Watermark.

### E-commerce Product Photos
1. **Batch resize** → Scale to 1920px max.
2. **Format convert** → WebP for modern browsers.
3. **Create thumbnails** → Contact Sheet for overview.

---

*The ImageMagick Toolbox represents the intersection of power and simplicity - bringing professional-grade image processing to everyday users through intelligent automation and intuitive design.*
