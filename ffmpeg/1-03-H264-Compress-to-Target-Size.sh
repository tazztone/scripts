#!/bin/bash
# Compress to Target Size
# Calculates bitrate to fit video exactly in a target MB size.

CHOICE=$(zenity --list --title="Target Size" --column="Size" --column="Description" \
    "9.5" "Email Tiny (10MB Limit)" \
    "25" "Discord Standard (25MB Limit)" \
    "500" "Discord Nitro (500MB Limit)" \
    "Custom" "Enter manually...")

if [ -z "$CHOICE" ]; then exit; fi

if [ "$CHOICE" == "Custom" ]; then
    TARGET_MB=$(zenity --entry --title="Custom Size" --text="Enter Target File Size (MB):" --entry-text="100")
    if [ -z "$TARGET_MB" ]; then exit; fi
else
    TARGET_MB=$CHOICE
fi

(
for f in "$@"; do
    echo "# Analyzing $f..."
    
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
    
    if [ -z "$DURATION" ]; then
        zenity --error --text="Could not determine duration for $f"
        continue
    fi

    # Set audio bitrate based on target size
    if (( $(echo "$TARGET_MB < 20" | bc -l) )); then
        A_BR=64
        A_CHAN=1
    elif (( $(echo "$TARGET_MB < 100" | bc -l) )); then
        A_BR=96
        A_CHAN=2
    else
        A_BR=128
        A_CHAN=2
    fi

    # Calculate Bitrate: (TargetMB * 8192 bits) / Duration
    TOTAL_BITRATE=$(echo "($TARGET_MB * 8192) / $DURATION" | bc)
    VIDEO_BITRATE=$(echo "$TOTAL_BITRATE - $A_BR" | bc)

    if (( $(echo "$VIDEO_BITRATE < 50" | bc -l) )); then
        VIDEO_BITRATE=50
    fi

    echo "# Target: ${VIDEO_BITRATE}k for ${TARGET_MB}MB"

    # 2-Pass Encoding
    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 1 -an -f null /dev/null
    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 2 -c:a aac -b:a "${A_BR}k" -ac "$A_CHAN" "${f%.*}_${TARGET_MB}MB.mp4"

    rm -f ffmpeg2pass-0.log ffmpeg2pass-0.log.mbtree
done
) | zenity --progress --title="Compressing to ${TARGET_MB} MB..." --pulsate --auto-close

zenity --notification --text="Compression Finished!"
