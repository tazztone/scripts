#!/bin/bash
# Rotate 90 CW
# Fixes sideways phone videos.

(
for f in "$@"; do
    echo "# Rotating $f 90 CW..."
    # transpose=1 is 90Clockwise
    ffmpeg -y -i "$f" -vf "transpose=1" -c:a copy "${f%.*}_rot90cw.mp4"
done
) | zenity --progress --title="Rotating 90 CW..." --pulsate --auto-close

zenity --notification --text="Rotation Finished!"
