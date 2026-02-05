# 🔒 Lossless Operations Toolbox

A specialized FFmpeg tool focused exclusively on quality-preserving video operations using stream copy functionality. No re-encoding, no quality loss, lightning-fast processing.

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

### Stream Editing (🎚️)
Remove or select specific streams without affecting remaining content.

**Operations:**
- Remove audio track (video-only output)
- Remove video track (audio-only output)
- Select specific streams
- Preserve metadata and chapters

### Metadata Editing (📝)
Modify file information without touching video/audio streams.

**Privacy Levels:**
- **High**: Complete metadata removal
- **Medium**: Basic info changes (title, rotation)
- **Low**: Orientation fixes only

**Operations:**
- Clean all metadata (privacy)
- Set custom video title
- Set rotation metadata (0°, 90°, 180°, 270°)
- Preserve stream integrity

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

### Preset Format
Presets are stored in `~/.config/lossless-toolbox/presets.conf`:
```
Name|operation|param1|param2
Quick Trim|trim|2|8
MP4 to MKV|remux|mkv
```

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

### Getting Help

1. **Built-in Help**: `--help` flag shows usage and examples
2. **Preset List**: `--list-presets` shows available operations
3. **Error Messages**: Include specific suggestions and alternatives
4. **Validation**: Clear feedback on why operations fail

## 🚀 Performance Characteristics

### Speed Comparison
| Operation | Lossless Toolbox | Universal Toolbox | Speedup |
|-----------|------------------|-------------------|---------|
| 10min trim | 2-3 seconds | 5-15 minutes | 100-300x |
| Format change | 5-10 seconds | 10-30 minutes | 120-360x |
| Remove audio | 1-2 seconds | 5-15 minutes | 150-450x |
| Clean metadata | 1-2 seconds | 5-15 minutes | 150-450x |

### Resource Usage
- **CPU**: Minimal (no encoding)
- **Memory**: Low (stream copy only)
- **Disk I/O**: Optimized sequential read/write
- **Quality**: Perfect (bit-for-bit preservation)

## 🔮 Future Enhancements

### Planned Features
- **Subtitle Integration**: Mux external subtitle files
- **Chapter Editing**: Add/remove/modify chapters
- **Stream Mapping**: Advanced stream selection
- **Batch Presets**: Multi-operation workflows

### Technical Improvements
- **Progress Estimation**: Better progress reporting for large files
- **Parallel Processing**: Multi-file batch optimization
- **Format Detection**: Enhanced container-codec validation
- **Error Recovery**: Graceful handling of edge cases

## 📜 Technical Specifications

### Dependencies
- **FFmpeg**: Core media processing (stream copy operations)
- **FFprobe**: Media analysis and validation
- **Zenity**: GUI dialogs and progress bars
- **Bash**: Shell scripting environment

### Compatibility
- **Containers**: MP4, MKV, MOV, WebM, AVI
- **Video Codecs**: H.264, H.265, VP8, VP9, AV1, ProRes
- **Audio Codecs**: AAC, MP3, Opus, FLAC, Vorbis, PCM
- **Platforms**: Linux (Ubuntu/Debian tested)

### Configuration
- **Config Directory**: `~/.config/lossless-toolbox/`
- **Presets**: `presets.conf`
- **History**: `history.conf` (last 15 operations)
- **Format**: Pipe-separated values for easy parsing

---

*The Lossless Operations Toolbox represents a paradigm shift from "transcode everything" to "preserve when possible" - delivering professional results at consumer-friendly speeds.*