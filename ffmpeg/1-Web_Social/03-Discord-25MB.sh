#!/bin/bash
# Discord 25MB Limit
# Calculates bitrate to fit video exactly in 25MB (Standard User Limit).

TARGET_MB=25

(
for f in "$@"; do
    echo "# Analyzing $f..."
    
    # Get duration
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
    
    if [ -z "$DURATION" ]; then
        zenity --error --text="Could not determine duration for $f"
        continue
    fi

    # Calculate Bitrate: (TargetMB * 8192 bits) / Duration = Total Bitrate
    # Subtract 96k for audio (optimized for small size)
    TOTAL_BITRATE=$(echo "($TARGET_MB * 8192) / $DURATION" | bc)
    VIDEO_BITRATE=$(echo "$TOTAL_BITRATE - 96" | bc)

    # Floor at 50k
    if (( $(echo "$VIDEO_BITRATE < 50" | bc -l) )); then
        VIDEO_BITRATE=50
    fi

    echo "# Target: ${VIDEO_BITRATE}k video bitrate"

    # 2-Pass Encoding
    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 1 -an -f null /dev/null
    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 2 -c:a aac -b:a 96k "${f%.*}_discord.mp4"

    rm -f ffmpeg2pass-0.log ffmpeg2pass-0.log.mbtree
done
) | zenity --progress --title="Compressing for Discord (25MB)..." --pulsate --auto-close

zenity --notification --text="Discord Compression Finished!"
