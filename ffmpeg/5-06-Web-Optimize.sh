#!/bin/bash
# Web Optimize
# Moves metadata to front for instant streaming (Fast Start).

(
for f in "$@"; do
    echo "# Optimizing $f..."
    ffmpeg -y -i "$f" -c copy -movflags +faststart "${f%.*}_web.mp4"
done
) | zenity --progress --title="Optimizing for Web..." --pulsate --auto-close

zenity --notification --text="Web Optimization Finished!"
