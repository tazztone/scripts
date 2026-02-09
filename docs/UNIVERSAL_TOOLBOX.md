# 🧰 Universal FFmpeg Toolbox

The Swiss Army Knife for video processing. A powerful, workstation-grade tool that combines multiple FFmpeg operations in a single, intelligent workflow with hardware acceleration, smart presets, and professional-grade features.

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
- **🏷️ Intelligent Naming**: Descriptive file tags based on applied operations
- **🔄 Operation Chaining**: Multiple operations in single pass for optimal quality
- **🎯 Context Awareness**: Dynamic UI based on available files and system capabilities

### Professional Features
- **🎬 Production Formats**: ProRes, DNxHD, uncompressed workflows
- **🌐 Distribution Optimization**: Platform-specific presets (Twitter, Discord, etc.)
- **🔧 Advanced Controls**: Custom bitrates, quality settings, hardware selection
- **📊 Progress Intelligence**: Real-time feedback with operation-specific progress

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

### Preset System

#### Default Presets
```bash
Social Speed Edit    # Speed 2x + Scale 720p + Normalize + H.264
4K Archival (H.265) # H.265 encoding + Clean Metadata
YouTube 1080p (Fast) # Scale 1080p + Normalize + H.264
```

#### Creating Custom Presets
1. Configure operations in the wizard
2. Choose "Save as Favorite" when prompted
3. Enter descriptive name
4. Access via Launchpad or CLI

## 🏎️ Hardware Acceleration

### Auto-Detection System
The Universal Toolbox performs intelligent hardware probing at startup:

1. **Silent Testing**: 1-frame dummy encode to test each acceleration method
2. **Capability Caching**: Results cached for 24 hours to avoid repeated testing
3. **Smart Fallback**: Automatic CPU fallback if hardware encoding fails
4. **Vendor Optimization**: Specific settings for each hardware type

### Supported Hardware
- **NVENC (NVIDIA)**: GeForce GTX 600+ series, professional cards
- **QSV (Intel)**: Intel HD Graphics 4000+, Arc graphics
- **VAAPI (AMD/Intel)**: AMD Radeon, Intel integrated graphics

### Performance Benefits
| Hardware | Speed Improvement | Quality | Power Usage |
|----------|------------------|---------|-------------|
| NVENC | 3-10x faster | Excellent | Low |
| QSV | 2-5x faster | Very Good | Very Low |
| VAAPI | 2-4x faster | Good | Low |
| CPU | Baseline | Best | High |

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

#### Quality Optimization
- **Smart Audio Allocation**: Reserves appropriate bitrate for audio quality
- **Complexity Awareness**: Adjusts encoding based on video content
- **Warning System**: Alerts when target size is too small for duration

## 🎨 Advanced Operations

### Speed Control with Pitch Correction
```bash
Supported Speeds: 0.25x, 0.5x, 1x, 2x, 4x, custom
Audio Handling: Automatic pitch correction using atempo filters
Frame Rate: Maintains original frame rate for compatibility
```

### Intelligent Cropping
```bash
9:16 (Vertical): Perfect for mobile/social media
16:9 (Landscape): Standard widescreen format
Square 1:1: Instagram/social media posts
4:3 (Classic): Traditional TV format
21:9 (Cinema): Ultra-wide cinematic format
```

### Audio Processing
```bash
Normalize (R128): EBU R128 loudness standard (-23 LUFS)
Boost Volume: +6dB increase with limiting
Downmix to Stereo: 5.1/7.1 to stereo conversion
Recode to PCM: Uncompressed audio for Linux compatibility
Extract Audio: MP3/WAV extraction with quality control
```

### Subtitle Integration
```bash
Auto-Detection: Finds matching .srt files automatically
Burn-in: Permanent subtitles with customizable styling
Mux (Softsub): Separate subtitle track (MP4/MKV)
Style Control: Font size, outline, positioning
```

## 📦 Output Formats

### Video Codecs
- **H.264**: Universal compatibility, streaming optimization
- **H.265 (HEVC)**: 50% better compression, 4K/HDR support
- **VP9**: Web-optimized, royalty-free
- **AV1**: Next-generation codec, excellent compression
- **ProRes**: Professional editing, multiple profiles
- **DNxHD/HR**: Avid workflows, broadcast quality

### Container Formats
- **MP4**: Universal compatibility, web streaming
- **MKV**: Open format, advanced features
- **MOV**: Apple ecosystem, editing workflows
- **WebM**: Web-optimized, browser-friendly
- **GIF**: Animated images with palette optimization

### Quality Presets
```bash
Lossless (CRF 0): Bit-for-bit preservation
High (CRF 18): Visually lossless quality
Medium (CRF 23): Balanced size/quality (default)
Low (CRF 28): Smaller files, visible compression
```

## 🛡️ Safety & Intelligence Features

### Auto-Rename Protection
```bash
Original: video.mp4
First Edit: video_2x_1080p.mp4
Collision: video_2x_1080p_v1.mp4
Next Edit: video_2x_1080p_v2.mp4
```

### Smart File Naming
Files are automatically named based on applied operations:
```bash
video_2x_720p_noaudio_nvenc.mp4
# 2x speed, 720p resolution, no audio, NVENC encoded

presentation_trimmed_h265_cleaned.mkv
# Trimmed, H.265 codec, metadata cleaned, MKV container
```

### Error Handling
- **Hardware Fallback**: Automatic CPU retry if GPU encoding fails
- **Validation Checks**: Pre-flight validation of operations and files
- **Progress Recovery**: Graceful handling of interrupted operations
- **Clear Messaging**: Detailed error descriptions with suggested solutions

## 🧪 Testing & Validation

### Automated Testing
The Universal Toolbox includes comprehensive testing through the unified test runner:

```bash
# Run all Universal Toolbox tests
bash testing/test_runner.sh
```

### Test Coverage
- **Zenity Mocking**: Headless testing without GUI dependencies
- **Operation Validation**: Codec, resolution, and format verification
- **Hardware Testing**: Validation across different acceleration methods
- **Edge Case Handling**: Boundary conditions and error scenarios

### Quality Assurance
- **FFprobe Validation**: Automated verification of output properties
- **Regression Testing**: Ensures new features don't break existing functionality
- **Performance Benchmarking**: Speed and quality metrics validation

## 🔧 Configuration & Customization

### Configuration Files
```bash
Config Directory: ~/.config/scripts-sh/
Presets: presets.conf
History: history.conf (last 15 operations)
GPU Cache: /tmp/scripts-sh-gpu-cache (24h TTL)
```

### Preset Format
```bash
# Format: Name|Choice1|Choice2|...
Social Speed Edit|Speed 2x (Fast)|Scale 720p|Normalize (R128)|Output as H.264
4K Archival (H.265)|Output as H.265|Clean Metadata
YouTube 1080p (Fast)|Scale 1080p|Normalize (R128)|Output as H.264
```

### History Management
- **Automatic Logging**: All operations saved automatically
- **Deduplication**: Prevents duplicate consecutive entries
- **Management Actions**: Run, save as preset, or delete entries
- **Capacity Limit**: Maintains last 15 operations for performance

## 🚀 Performance Optimization

### Single-Pass Efficiency
The Universal Toolbox combines multiple operations into a single FFmpeg command:

```bash
# Instead of multiple passes:
ffmpeg -i input.mp4 -vf scale=1280:720 temp1.mp4
ffmpeg -i temp1.mp4 -filter:a loudnorm temp2.mp4
ffmpeg -i temp2.mp4 -c:v libx264 -crf 23 output.mp4

# Single optimized pass:
ffmpeg -i input.mp4 -vf scale=1280:720 -af loudnorm -c:v libx264 -crf 23 output.mp4
```

### Memory Management
- **Streaming Processing**: Minimal memory footprint for large files
- **Temporary File Cleanup**: Automatic cleanup of intermediate files
- **Resource Monitoring**: Intelligent resource allocation based on system capabilities

### Processing Speed Comparison
| Operation | Traditional Approach | Universal Toolbox | Improvement |
|-----------|---------------------|-------------------|-------------|
| Scale + Audio | 2 passes | 1 pass | 2x faster |
| Multiple Filters | 3+ passes | 1 pass | 3-5x faster |
| Hardware Accel | Manual setup | Auto-detected | Seamless |
| Target Size | Trial/error | 2-pass precision | Guaranteed |

## 🔮 Advanced Use Cases

### Content Creation Workflows
```bash
# Social Media Optimization
Speed: 2x (Fast) + Scale: 720p + Crop: 9:16 + Normalize

# Archival Processing
Output: H.265 + Quality: High + Clean Metadata

# Web Distribution
Scale: 1080p + Target Size: 25MB + Format: MP4 + Faststart
```

### Professional Workflows
```bash
# Proxy Generation
Scale: 720p + Output: ProRes Proxy + Audio: PCM

# Broadcast Delivery
Output: DNxHD + Audio: PCM + Clean Metadata

# Streaming Preparation
Scale: 1080p + Output: H.264 + Faststart + Normalize
```

### Batch Processing
```bash
# Process entire directories
./🧰\ Universal-Toolbox.sh --preset "YouTube 1080p" /path/to/videos/*.mp4

# Automated workflows
for preset in "Social" "Archive" "Web"; do
    ./🧰\ Universal-Toolbox.sh --preset "$preset" *.mov
done
```

## 🛠️ Troubleshooting

### Common Issues

**Hardware Acceleration Not Working**
- Check GPU drivers and FFmpeg compilation
- Review `/tmp/scripts-sh-gpu-cache` for detection results
- Use CPU fallback if hardware fails

**Target Size Too Small**
- Increase target size or reduce duration
- Consider lower resolution or frame rate
- Check audio bitrate allocation

**Subtitle Files Not Detected**
- Ensure `.srt` file matches video filename
- Check file permissions and encoding
- Verify subtitle format compatibility

### Performance Issues
- **Large Files**: Use hardware acceleration when available
- **Complex Filters**: Consider reducing filter complexity
- **Memory Usage**: Close other applications during processing
- **Disk Space**: Ensure adequate free space for temporary files

### Getting Help
1. **Built-in Validation**: Pre-flight checks catch most issues
2. **Error Messages**: Detailed descriptions with suggested solutions
3. **Log Files**: `/tmp/ffmpeg_universal_last_run.log` for debugging
4. **Test Mode**: Use small clips to test configurations

## 🔮 Future Enhancements

### Planned Features
- **Visual Preview**: 5-second test renders before full processing
- **Watermarking**: Auto-detect and overlay watermark images
- **Advanced Cropping**: Manual crop selection with preview
- **Batch Presets**: Multi-step automated workflows

### Technical Improvements
- **GPU Memory Management**: Better handling of VRAM limitations
- **Parallel Processing**: Multi-file batch optimization
- **Quality Prediction**: AI-based quality/size estimation
- **Format Migration**: Automated codec upgrade workflows

## 📜 Technical Specifications

### Dependencies
- **FFmpeg**: Core media processing with hardware acceleration support
- **Zenity**: GUI dialogs and progress bars
- **bc**: Mathematical calculations for bitrate and sizing
- **Bash**: Shell scripting environment (4.0+)

### System Requirements
- **OS**: Linux (Ubuntu/Debian tested, other distributions compatible)
- **RAM**: 2GB minimum, 8GB recommended for 4K processing
- **Storage**: Temporary space equal to 2x largest input file
- **GPU**: Optional but recommended for hardware acceleration

### Compatibility Matrix
| Format | Input | Output | Hardware Accel | Notes |
|--------|-------|--------|----------------|-------|
| MP4 | ✅ | ✅ | ✅ | Universal compatibility |
| MKV | ✅ | ✅ | ✅ | Open format, all codecs |
| MOV | ✅ | ✅ | ✅ | Apple ecosystem |
| WebM | ✅ | ✅ | ❌ | Web-optimized |
| AVI | ✅ | ❌ | ❌ | Legacy format |

---

*The Universal Toolbox represents the pinnacle of FFmpeg workflow optimization - combining professional capabilities with consumer-friendly automation to deliver studio-quality results at unprecedented speed and convenience.*