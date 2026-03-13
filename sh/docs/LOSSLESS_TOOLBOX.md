# 🔒 Lossless Operations Toolbox

A specialized FFmpeg tool focused exclusively on quality-preserving video operations using stream copy functionality. No re-encoding, no quality loss, lightning-fast processing.

## 📋 Table of Contents

- [Philosophy](#-philosophy)
- [Architecture](#-architecture)
- [Features](#-features)
- [Usage Guide](#-usage-guide)
- [Operation Details](#-operation-details)
- [Preset System](#-preset-system)
- [Technical Details](#-technical-details)
- [Testing & Validation](#-testing--validation)
- [Troubleshooting](#-troubleshooting)
- [Gotchas & Warnings](#-gotchas--warnings)
- [Quick Reference](#-quick-reference)
- [Common Workflows](#-common-workflows)

## 🎯 Philosophy

The Lossless Operations Toolbox follows the principle that **not every video operation requires transcoding**. Many common tasks like trimming, format conversion, and metadata editing can be performed instantly without touching the actual video/audio streams.

### When to Use Lossless vs Universal Toolbox

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

---

## 🏗️ Architecture

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
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    FFmpeg Core                                  │
│              (Stream Copy -c copy)                              │
└─────────────────────────────────────────────────────────────────┘
```

> 💡 **Why This Architecture?** By isolating lossless operations into a dedicated tool, we avoid the overhead of complex filtergraph construction and ensure that bit-for-bit stream preservation is the default state, rather than an option.

---

## 🚀 Features

### Core Operations
- **✂️ Trimming**: Extract time segments with frame-accurate cutting
- **📦 Remuxing**: Change container formats (MP4, MKV, MOV, WebM)
- **🔗 Merging**: Concatenate files with identical codec parameters
- **🎚️ Stream Editing**: Remove or select specific audio/video tracks
- **📝 Metadata Editing**: Modify file information without touching streams
- **⚡ Batch Processing**: Apply operations to multiple files simultaneously

### Enhanced User Experience
- **⭐ Preset System**: Save and reuse common operations
- **📚 History Tracking**: Quick access to recent operations
- **🔧 Smart Validation**: Prevents incompatible operations with helpful suggestions
- **🛡️ Auto-Rename**: Intelligent file naming to prevent overwrites
- **⌨️ CLI Support**: Command-line automation with preset support

### Technical Excellence
- **🚀 Zero Quality Loss**: All operations use FFmpeg `-c copy` (stream copy)
- **⚡ Lightning Speed**: Operations complete in seconds, not minutes
- **🎯 Codec Validation**: Comprehensive compatibility checking
- **📦 Container Optimization**: Format-specific flags for better compatibility
- **🔍 Smart Detection**: Automatic subtitle and metadata detection

---

## 📖 Usage Guide

### Interactive Mode

1. **Right-click** on video files in Nautilus
2. Select **Scripts** → **🔒 Lossless-Operations-Toolbox**
3. Choose from the enhanced menu:
   - **New Operation**: Select from available lossless operations
   - **⭐ Presets**: Use saved favorites
   - **🕒 History**: Repeat recent operations

### Command Line Interface

```bash
# Basic usage
./🔒\ Lossless-Operations-Toolbox.sh video.mp4

# Use presets for automation
./🔒\ Lossless-Operations-Toolbox.sh --preset "Quick Trim" *.mp4

# List available presets
./🔒\ Lossless-Operations-Toolbox.sh --list-presets

# Show help
./🔒\ Lossless-Operations-Toolbox.sh --help
```

### Time Format Support

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

---

## 🔧 Operation Details

### Trimming (✂️)
Extract video segments without re-encoding. Perfect for creating clips, removing unwanted sections, or splitting long videos.

**Use Cases:**
- Create social media clips
- Remove intro/outro sections
- Extract highlights from recordings
- Split long videos into chapters

**Validation:**
- Checks file duration and time ranges
- Prevents invalid start/end times
- Warns about keyframe accuracy limitations

> 💡 **Why Lossless Trimming?** Unlike re-encoding, stream copy trimming reads only the needed bytes from the source file. A 1-hour video trimmed to 30 seconds takes the same 2-3 seconds regardless of source duration.

### Container Remuxing (📦)
Change video container format instantly while preserving all streams and quality.

**Supported Formats:**
- **MP4**: Universal compatibility, web streaming
- **MKV**: Open format, supports all codecs
- **MOV**: Apple ecosystem, editing workflows
- **WebM**: Web-optimized, browser-friendly

**Optimization Features:**
- MP4: `+faststart` for web streaming
- MKV: Index space reservation for better seeking
- MOV: QuickTime compatibility flags

### File Merging (🔗)
Concatenate multiple video files with identical codec parameters.

**Requirements:**
- All files must have matching video codecs
- All files must have matching audio codecs
- Container format can differ (will be unified)

**Smart Validation:**
- Automatic codec compatibility checking
- Clear error messages for incompatible files
- Suggestions for resolving compatibility issues

> 💡 **Why Smart Validation?** FFmpeg's `concat` demuxer is notoriously picky. Our validation engine pre-checks stream properties (profile, level, framerate) to guarantee a stable output before the process even starts.

---

## 🎛️ Preset System

### Default Presets
```bash
Quick Trim      # Extract 2-8 second segments
MP4 to MKV      # Convert container format
Remove Audio    # Strip audio tracks
Clean Metadata  # Remove privacy information
Merge Compatible # Concatenate matching files
```

### Creating Custom Presets
1. Perform an operation interactively
2. Choose "Save as Preset" when prompted
3. Enter a descriptive name
4. Use via CLI: `--preset "Your Preset Name"`

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

### Configuration

```bash
Config Directory: ~/.config/scripts-sh/lossless/
Presets: presets.conf
History: history.conf (last 15 operations)
Format: Pipe-separated values for easy parsing
```

---

## 🧪 Testing & Validation

The Lossless Operations Toolbox includes comprehensive property-based testing to ensure correctness and safety.

### Test Coverage
- **Stream Copy Preservation**: Verifies no re-encoding occurs
- **Codec Analysis Accuracy**: Validates codec detection
- **Operation Safety**: Prevents destructive operations
- **Compatibility Validation**: Ensures container-codec matching
- **Batch Processing Integrity**: Multi-file operation validation
- **Metadata Preservation**: Lossless metadata handling

### Running Tests
```bash
# Run property-based tests
bash testing/test_lossless_toolbox.sh

# Expected output: 12/12 tests passed
```

---

## 🔍 Troubleshooting

### Common Issues

**"Incompatible codecs" Error**
- Files have different video or audio codecs
- Solution: Use Universal Toolbox to standardize codecs first

**"Validation failed" Message**
- Operation cannot be performed losslessly
- Check suggested alternatives in error message

**"File not found" Error**
- Ensure FFmpeg and FFprobe are installed
- Check file permissions and paths

---

## ⚠️ Gotchas & Warnings

- **Keyframe Trimming**: Lossless cuts can only happen at keyframes — expect ±1 frame inaccuracy
- **Merge Limitations**: Files MUST have identical codecs, resolution, and framerate
- **Subtitle Handling**: Embedded subtitles are preserved but external .srt files are not auto-detected
- **Chapter Markers**: May be lost during remuxing depending on container format
- **HDR Content**: HDR metadata is preserved but tone mapping requires re-encoding (use Universal Toolbox)

---

## 📇 Quick Reference

### Common Commands

| Goal | Command |
|------|----------|
| Trim first 30 seconds | `./🔒\ Lossless-Operations-Toolbox.sh --preset "Quick Trim" video.mp4` |
| Convert to MKV | `./🔒\ Lossless-Operations-Toolbox.sh --preset "MP4 to MKV" *.mp4` |
| Remove audio track | `./🔒\ Lossless-Operations-Toolbox.sh --preset "Remove Audio" video.mp4` |
| Clean metadata | `./🔒\ Lossless-Operations-Toolbox.sh --preset "Clean Metadata" video.mp4` |

---

## 📚 Common Workflows

### Social Media Content Creator
1. **Record long video** → Lossless: Trim to highlight segment
2. **Remove metadata** → Lossless: Clean Metadata (privacy)
3. **Convert format** → Lossless: MP4 to MKV (if needed)

### Video Archival
1. **Collect recordings** → Lossless: Merge Compatible
2. **Clean up** → Lossless: Clean Metadata
3. **Repackage** → Lossless: Remux to MKV (preserves all streams)

---

*The Lossless Operations Toolbox represents a paradigm shift from "transcode everything" to "preserve when possible" - delivering professional results at consumer-friendly speeds.*
