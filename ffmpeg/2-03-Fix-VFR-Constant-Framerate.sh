#!/bin/bash
# Fix Variable Framerate (VFR -> CFR)
# Prevents audio drift in editing software.

(
for f in "$@"; do
    echo "# Fixing VFR for $f..."
    # We detect the input FPS or default to 30/60? 
    # Better: just tell ffmpeg to re-encode standard usually fixes VFR.
    # explicit -vsync cfr is good.
    ffmpeg -y -i "$f" -c:v libx264 -crf 20 -c:a aac -b:a 192k -vsync cfr "${f%.*}_cfr.mp4"
done
) | zenity --progress --title="Fixing VFR..." --pulsate --auto-close

zenity --notification --text="VFR Fix Finished!"
