#!/bin/bash
# Trim End (10s)
# Cuts the last 10 seconds.

(
for f in "$@"; do
    echo "# Calculating duration for $f..."
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
    if [ -z "$DURATION" ]; then continue; fi
    
    NEW_DUR=$(echo "$DURATION - 10" | bc)
    
    if (( $(echo "$NEW_DUR <= 0" | bc -l) )); then
        echo "# Video too short to trim 10s!"
        continue
    fi
    
    echo "# Trimming to $NEW_DUR seconds..."
    ffmpeg -y -i "$f" -t "$NEW_DUR" -c:v libx264 -c:a aac "${f%.*}_trimmed_end.mp4"
done
) | zenity --progress --title="Trimming End..." --pulsate --auto-close

zenity --notification --text="Trim End Finished!"
