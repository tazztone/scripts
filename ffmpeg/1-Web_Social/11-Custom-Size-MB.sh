#!/bin/bash
# Custom Size Compression
# Calculates bitrate to fit video exactly in a user-defined MB size.

TARGET_MB=$(zenity --entry --title="Custom Compression" --text="Enter Target File Size (MB):" --entry-text="25")

if [ -z "$TARGET_MB" ]; then exit; fi

(
for f in "$@"; do
    echo "# Analyzing $f..."
    
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
    
    if [ -z "$DURATION" ]; then
        zenity --error --text="Could not determine duration for $f"
        continue
    fi

    # Calculate Bitrate: (TargetMB * 8192 bits) / Duration
    TOTAL_BITRATE=$(echo "($TARGET_MB * 8192) / $DURATION" | bc)
    VIDEO_BITRATE=$(echo "$TOTAL_BITRATE - 128" | bc)

    if (( $(echo "$VIDEO_BITRATE < 100" | bc -l) )); then
        VIDEO_BITRATE=100
    fi

    echo "# Target: ${VIDEO_BITRATE}k for ${TARGET_MB}MB"

    # 2-Pass Encoding
    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 1 -an -f null /dev/null
    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 2 -c:a aac -b:a 128k "${f%.*}_${TARGET_MB}MB.mp4"

    rm -f ffmpeg2pass-0.log ffmpeg2pass-0.log.mbtree
done
) | zenity --progress --title="Compressing to ${TARGET_MB} MB..." --pulsate --auto-close

zenity --notification --text="Compression Finished!"
