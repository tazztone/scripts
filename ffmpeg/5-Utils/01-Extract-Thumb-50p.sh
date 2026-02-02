#!/bin/bash
# Extract Thumbnail (50%)
# Grabs a single frame from the middle of the video.

(
for f in "$@"; do
    echo "# Analyzing $f..."
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
    if [ -z "$DURATION" ]; then continue; fi
    
    # Calculate middle point
    MID=$(echo "$DURATION / 2" | bc)
    
    echo "# Extracting thumbnail at $MID seconds..."
    ffmpeg -y -ss "$MID" -i "$f" -vframes 1 -q:v 2 "${f%.*}_thumb.jpg"
done
) | zenity --progress --title="Extracting Thumbnail..." --pulsate --auto-close

zenity --notification --text="Thumbnail Extracted!"
