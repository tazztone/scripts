#!/bin/bash
# Flip Horizontal
# Mirrors the image.

(
for f in "$@"; do
    echo "# Flipping $f..."
    ffmpeg -y -i "$f" -vf "hflip" -c:a copy "${f%.*}_flip.mp4"
done
) | zenity --progress --title="Flipping..." --pulsate --auto-close

zenity --notification --text="Flip Finished!"
