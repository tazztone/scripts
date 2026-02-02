#!/bin/bash
# Scale 50%
# Quick resize to half resolution.

(
for f in "$@"; do
    echo "# Scaling $f to 50%..."
    ffmpeg -y -i "$f" -vf "scale=iw*0.5:-2" "${f%.*}_50p.mp4"
done
) | zenity --progress --title="Scaling to 50%..." --pulsate --auto-close

zenity --notification --text="Scale 50% Finished!"
