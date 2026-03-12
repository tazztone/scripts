# 🖼️ ImageMagick Toolbox

The **ImageMagick Toolbox** (`1-00 🖼️ Image-Magick-Toolbox.sh`) is a high-performance batch image processing utility designed for Nautilus. It leverages `imagemagick` and `zenity` to provide a user-friendly GUI for complex image manipulation tasks.

## 📋 Table of Contents

- [Philosophy](#-philosophy)
- [Features](#-features)
- [Usage Guide](#-usage-guide)
- [Configuration](#-configuration)
- [Technical Details](#-technical-details)
- [Output Formats](#-output-formats)
- [Testing & Validation](#-testing--validation)
- [Troubleshooting](#-troubleshooting)
- [Future Enhancements](#-future-enhancements)
- [Technical Specifications](#-technical-specifications)

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

## 🚀 Features

### Core Capabilities
- **⚡ Parallel Processing**: Uses background jobs to process image libraries at maximum CPU speed (configurable job count).
- **📱 Modern Format Support**: Automated handling of **HEIC/RAW** to sRGB JPG conversion.
- **🛡️ Non-Destructive**: Always creates new files with smart naming (e.g., `image_web_sq.jpg`), never overwriting originals.
- **📊 Progress Tracking**: Visual progress bar for batch operations with real-time feedback.
- **🚨 Error Reporting**: Detailed error logs shown if any files fail to process.

### Operation Categories

#### 1. 📏 Scale & Resize
- **Presets**: 4K (3840x), HD (1920x), 720p (1280x), 640p, 50%.
- **Custom**: Enter any geometry (e.g., `800x600`, `x500` for height-only).
- **Smart Logic**: Preserves aspect ratio by default using `-resize` with dimension constraints.

#### 2. ✂️ Crop & Geometry
- **Square Crop (1:1)**: Automatically crops the center square of the image. Perfect for Instagram/social media.
- **Vertical (9:16)**: Standard mobile aspect ratio for stories/reels.
- **Landscape (16:9)**: Standard widescreen format.
- **Custom Crop**: Manual crop geometry specification.

#### 3. 🖼️ Montage & Grid
- **2x / 3x Grid**: Creates a high-resolution grid montage of your images.
- **Single Row/Column**: Stitches images together horizontally or vertically at full resolution.
- **Contact Sheet**: Creates a sheet of thumbnails (200x200) for overview with 4-column layout.

#### 4. 📦 Format Converter
- **Outputs**: JPG, PNG, WEBP, TIFF, PDF.
- **PDF Merging**: Select multiple images → Output "PDF" → Creates a single multi-page PDF.
- **PDF Extraction**: Select a PDF → Output "JPG/PNG" → Extracts all pages as high-DPI images (300 DPI).
- **Smart Transparency**: Intelligent handling of alpha channels during format conversion.

#### 5. 🚀 Optimization
- **Web Ready**: Standard quality (85) + strips metadata (EXIF/GPS) for privacy and small size.
- **Max Compression**: Aggressive compression (Quality 60) for archival.
- **Archive**: Lossless compression, keeps all metadata.

#### 6. ✨ Effects & Branding
- **Watermark**: Auto-detects `watermark.png` in the folder (or script folder) and overlays it in the Southeast corner.
- **Text Annotation**: Add custom text overlays with configurable positioning.
- **Simple Effects**: Rotate 90° CW/CCW, Flip Horizontal, Black & White.
- **Colorspace Conversion**: CMYK to sRGB conversion for web compatibility.
- **Flatten**: Remove transparency by compositing onto white background.

#### 7. 🔇 Video Audio Removal
- **Remove Audio**: Strip audio tracks from video files using FFmpeg stream copy.

## 📖 Usage Guide

### Interactive Mode

1. **Select Images**: Highlight one or more images in Nautilus.
2. **Right-Click → Scripts → 1-00 🖼️ Image-Magick-Toolbox**.
3. **Choose Intent**: Select what you want to do (e.g., "Scale", "Canvas", "Format").
4. **Configure**: Fine-tune settings in the pop-up form.
   - *Example*: Select "Canvas/Montage" → Choose "Square Crop".
5. **Run**: The script processes files in background.

### Context-Aware UI

The toolbox automatically adapts its interface based on the selected files:

- **Image Files**: Shows scale, crop, format, effects, and montage options.
- **PDF Files**: Shows extract pages option.
- **Video Files**: Shows remove audio option.
- **Images with Alpha**: Shows flatten background option.
- **CMYK Images**: Shows convert to sRGB option.

### Command Line Interface

```bash
# Basic usage with files
./🖼️\ Image-Magick-Toolbox.sh image1.jpg image2.png

# Process entire directory
./🖼️\ Image-Magick-Toolbox.sh /path/to/images/*.jpg
```

## 🛠️ Configuration

### Configuration Files
```bash
Config Directory: ~/.config/scripts-sh/imagemagick/
Presets: presets.conf
History: history.conf (last 15 operations)
```

### Preset System
- **Save Presets**: After running a "New Custom Edit", choose to save your configuration.
- **Load Presets**: Access saved presets from the launchpad or via CLI.
- **Preset Format**: `Name|Scale:1920x|Format:JPG|Optimize:Web Ready`

### History Management
- **Automatic Logging**: All operations saved automatically.
- **Deduplication**: Prevents duplicate consecutive entries.
- **Quick Access**: Recent operations accessible from main menu.

## 🔧 Technical Details

### Processing Pipeline

The toolbox processes images in a specific order to ensure optimal results:

1. **Crop/Geometry** (Priority 1): Applied first to establish final dimensions.
2. **Scale/Resize** (Priority 2): Applied after crop for precise sizing.
3. **Effects** (Priority 3): Color corrections, rotations, etc.
4. **Format/Optimization** (Priority 4): Final output format and quality.

### Parallel Processing

```bash
# Default: 4 parallel jobs
MAX_JOBS=4

# Adjusts to CPU count if less than 4
[ $(nproc) -lt 4 ] && MAX_JOBS=$(nproc)
```

### Smart File Naming

Output files are automatically named based on applied operations:

```bash
image_1920p_web.jpg      # Scaled to 1920px, web optimized
photo_sq_90cw.jpg         # Square crop, rotated 90° CW
montage_grid2x.jpg        # 2-column grid montage
merged_images.pdf         # Multiple images merged to PDF
```

## 📦 Output Formats

### Image Formats
| Format | Extension | Use Case | Transparency |
|--------|-----------|----------|--------------|
| JPG | .jpg | Web, photos | ❌ No |
| PNG | .png | Graphics, screenshots | ✅ Yes |
| WEBP | .webp | Modern web | ✅ Yes |
| TIFF | .tiff | Print, archival | ✅ Yes |

### PDF Operations
| Operation | Input | Output | Description |
|-----------|-------|--------|-------------|
| Merge | Multiple images | Single PDF | Creates multi-page document |
| Extract | PDF | Multiple images | Extracts pages as images |

## 🧪 Testing & Validation

### Automated Testing
The ImageMagick Toolbox includes testing through the unified test runner:

```bash
# Run ImageMagick tests
bash testing/test_image_toolbox.sh
```

### Test Coverage
- **Format Conversion**: Validates output format correctness.
- **Geometry Operations**: Verifies crop and scale accuracy.
- **Montage Creation**: Tests grid and contact sheet generation.
- **PDF Operations**: Validates merge and extract functionality.

## 🔮 Troubleshooting

### Common Issues

**"Command not found: magick"**
- Ensure ImageMagick is installed: `sudo apt install imagemagick`
- Check version: `magick -version`

**"No images found"**
- Verify file paths and permissions.
- Ensure files are valid image formats.

**"Memory limit exceeded"**
- Reduce batch size or image dimensions.
- Increase ImageMagick memory limits in `policy.xml`.

**"PDF extraction failed"**
- Ensure Ghostscript is installed: `sudo apt install ghostscript`
- Check PDF is not password-protected.

### Performance Tips
- **Large Batches**: Process in groups of 50-100 images for optimal memory usage.
- **High Resolution**: Consider downscaling before applying complex effects.
- **Montage Creation**: Use thumbnail mode for large image sets.

## 🔮 Future Enhancements

### Planned Features
- **Advanced Watermarking**: Multi-position support with opacity control.
- **Batch Rename**: Integrated file renaming with pattern support.
- **EXIF Preservation**: Option to preserve metadata during conversion.
- **Collage Templates**: Pre-designed layouts for social media.

### Technical Improvements
- **Progressive Encoding**: Better web optimization for JPG/PNG.
- **Smart Compression**: Content-aware quality adjustment.
- **Format Detection**: Enhanced input format auto-detection.

## 📜 Technical Specifications

### Dependencies
- **ImageMagick**: Core image processing (v7+ recommended).
- **FFmpeg**: Video audio removal (optional).
- **Zenity**: GUI dialogs and progress bars.
- **Bash**: Shell scripting environment (4.0+).

### System Requirements
- **OS**: Linux (Ubuntu/Debian tested, other distributions compatible).
- **RAM**: 512MB minimum, 2GB recommended for large batches.
- **Storage**: Temporary space equal to 1.5x total input size.
- **CPU**: Multi-core recommended for parallel processing.

### Supported Formats
| Category | Formats |
|----------|---------|
| Input | JPG, PNG, GIF, TIFF, WEBP, BMP, HEIC, RAW, PDF |
| Output | JPG, PNG, WEBP, TIFF, PDF |
| Video | MP4, MKV, MOV, AVI, WEBM (audio removal only) |

---

*The ImageMagick Toolbox represents the intersection of power and simplicity - bringing professional-grade image processing to everyday users through intelligent automation and intuitive design.*
