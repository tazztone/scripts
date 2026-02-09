# 🖼️ Image Magick Toolbox

The **Image Magick Toolbox** (`1-00 🖼️ Image-Magick-Toolbox.sh`) is a high-performance batch image processing utility designed for Nautilus. It leverages `imagemagick` and `zenity` to provide a user-friendly GUI for complex image manipulation tasks.

## 🚀 Features

### Core Capabilities
- **⚡ Parallel Processing**: Uses your CPU's full power to process multiple images simultaneously.
- **📱 Format Support**: Handles modern formats like **HEIC** and **RAW**, converting them to sRGB JPG/PNG automatically.
- **🛡️ Non-Destructive**: Always creates new files with smart naming (e.g., `image_web_sq.jpg`), never overwriting originals.
- **📊 Progress Tracking**: Visual progress bar for batch operations.
- **🚨 Error Reporting**: Detailed error logs shown if any files fail to process.

### Operation Categories

#### 1. 📐 Scale & Resize
- **Presets**: 4K (3840x), HD (1920x), 720p (1280x), 640p, 50%.
- **Custom**: Enter any geometry (e.g., `800x600`, `x500` for height).
- **Smart Logic**: Preserves aspect ratio by default.

#### 2. 🖼️ Canvas & Crop
- **Square Crop (1:1)**: **NEW!** Automatically crops the center square of the image. Perfect for Instagram/social media.
- **2x / 3x Grid**: Creates a high-resolution grid montage of your images.
- **Single Row/Column**: **NEW!** Stitches images together horizontally or vertically at full resolution.
- **Contact Sheet**: **NEW!** Creates a sheet of thumbnails (200x200) for overview.

#### 3. 📦 Format Converter
- **Outputs**: JPG, PNG, WEBP, TIFF, PDF.
- **PDF Merging**: Select multiple images -> Output "PDF" -> Creates a single multi-page PDF.
- **PDF Extraction**: Select a PDF -> Output "JPG/PNG" -> Extracts all pages as images.

#### 4. 🚀 Optimization
- **Web Ready**: Standard quality (85) + strips metadata (EXIF/GPS) for privacy and small size.
- **Max Compression**: Aggressive compression (Quality 60) for archival.
- **Archive**: Lossless compression, keeps all metadata.

#### 5. 🏷️ Branding & Effects
- **Watermark**: Auto-detects `watermark.png` in the folder (or script folder) and overlays it in the Southeast corner.
- **Simple Effects**: Rotate 90° CW/CCW, Flip Horizontal, Black & White.

## 📖 Usage Guide

1.  **Select Images**: Highlight one or more images in Nautilus.
2.  **Right-Click -> Scripts -> 1-00 🖼️ Image-Magick-Toolbox**.
3.  **Choose Intent**: Select what you want to do (e.g., "Scale", "Canvas", "Format").
4.  **Configure**: Fine-tune settings in the pop-up form.
    - *Example*: Select "Canvas/Montage" -> Choose "Square Crop".
5.  **Run**: The script processes files in background.

## 🛠️ Configuration

- **Presets**: Save your favorite configurations after running a "New Custom Edit".
- **History**: Use "Recent History" in the launchpad to repeat the last action.

## 📋 Requirements
- `imagemagick`
- `zenity`
