#!/bin/bash
# Trim Start (10s)
# Cuts the first 10 seconds.

(
for f in "$@"; do
    echo "# Trimming start of $f..."
    # -ss 10 before input? slightly faster but -ss after input is more accurate for re-encode often.
    # We re-encode to be safe on keyframes? Or copy? 
    # Copy is fast but might have blank frame at start if keyframe missing.
    # Let's use re-encode for "Fix It" pack quality.
    ffmpeg -y -ss 10 -i "$f" -c:v libx264 -c:a aac "${f%.*}_trimmed_start.mp4"
done
) | zenity --progress --title="Trimming Start..." --pulsate --auto-close

zenity --notification --text="Trim Start Finished!"
