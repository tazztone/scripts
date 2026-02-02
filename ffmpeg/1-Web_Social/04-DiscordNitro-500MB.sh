#!/bin/bash
# Discord Nitro Limit (500MB)

TARGET_MB=499

(
for f in "$@"; do
    echo "# Analyzing $f..."
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
    if [ -z "$DURATION" ]; then continue; fi

    TOTAL_BITRATE=$(echo "($TARGET_MB * 8192) / $DURATION" | bc)
    VIDEO_BITRATE=$(echo "$TOTAL_BITRATE - 192" | bc) 

    if (( $(echo "$VIDEO_BITRATE < 1000" | bc -l) )); then
        VIDEO_BITRATE=1000
    fi

    echo "# Target: ${VIDEO_BITRATE}k"

    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 1 -an -f null /dev/null
    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 2 -c:a aac -b:a 192k "${f%.*}_nitro.mp4"

    rm -f ffmpeg2pass-0.log ffmpeg2pass-0.log.mbtree
done
) | zenity --progress --title="Compressing for Nitro (500MB)..." --pulsate --auto-close

zenity --notification --text="Nitro Compression Finished!"
