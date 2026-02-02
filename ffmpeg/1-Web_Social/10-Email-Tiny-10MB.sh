#!/bin/bash
# Email Tiny (<10MB)
# Aggressive compression to ensure file fits in standard email attachments.

TARGET_MB=9.5 # Safety margin for 10MB limit

(
for f in "$@"; do
    echo "# Analyzing $f..."
    
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
    
    if [ -z "$DURATION" ]; then continue; fi

    # Calculate Bitrate
    # Audio reduced to 64k mono for email size optimization
    TOTAL_BITRATE=$(echo "($TARGET_MB * 8192) / $DURATION" | bc)
    VIDEO_BITRATE=$(echo "$TOTAL_BITRATE - 64" | bc)

    if (( $(echo "$VIDEO_BITRATE < 30" | bc -l) )); then
        VIDEO_BITRATE=30
    fi

    echo "# Target: ${VIDEO_BITRATE}k"

    # 2-Pass Encoding
    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 1 -an -f null /dev/null
    ffmpeg -y -i "$f" -c:v libx264 -b:v "${VIDEO_BITRATE}k" -pass 2 -c:a aac -b:a 64k -ac 1 "${f%.*}_email.mp4"

    rm -f ffmpeg2pass-0.log ffmpeg2pass-0.log.mbtree
done
) | zenity --progress --title="Compressing for Email (10MB)..." --pulsate --auto-close

zenity --notification --text="Email Compression Finished!"
