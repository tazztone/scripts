#!/bin/bash
# Scale to 1080p
# Resizes so height is 1080 px (preserves aspect ratio).

(
for f in "$@"; do
    echo "# Scaling $f to 1080p..."
    ffmpeg -y -i "$f" -vf "scale=-2:1080" "${f%.*}_1080p.mp4"
done
) | zenity --progress --title="Scaling to 1080p..." --pulsate --auto-close

zenity --notification --text="Scale 1080p Finished!"
