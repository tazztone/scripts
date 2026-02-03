#!/bin/bash
# Scale to 720p
# Resizes so height is 720 px (preserves aspect ratio).

(
for f in "$@"; do
    echo "# Scaling $f to 720p..."
    ffmpeg -y -i "$f" -vf "scale=-2:720" "${f%.*}_720p.mp4"
done
) | zenity --progress --title="Scaling to 720p..." --pulsate --auto-close

zenity --notification --text="Scale 720p Finished!"
