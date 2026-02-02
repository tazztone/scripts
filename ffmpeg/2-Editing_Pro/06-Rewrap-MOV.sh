#!/bin/bash
# Rewrap to MOV
# Changes container without re-encoding (Instant).

(
for f in "$@"; do
    echo "# Rewrapping $f to MOV..."
    ffmpeg -y -i "$f" -c copy "${f%.*}_rewrap.mov"
done
) | zenity --progress --title="Rewrapping to MOV..." --pulsate --auto-close

zenity --notification --text="Rewrap Finished!"
