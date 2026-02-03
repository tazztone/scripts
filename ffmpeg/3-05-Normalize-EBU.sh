#!/bin/bash
# Normalize Audio (EBU R128)
# Professional loudness normalization.

(
for f in "$@"; do
    echo "# Normalizing $f..."
    # loudnorm filter does single pass normalization
    # For strict compliance, double pass is needed, but single pass is usually "good enough" for quick tools.
    ffmpeg -y -i "$f" -c:v copy -af loudnorm=I=-23:LRA=7:TP=-1.5 "${f%.*}_norm.mp4"
done
) | zenity --progress --title="Normalizing Audio..." --pulsate --auto-close

zenity --notification --text="Normalization Finished!"
