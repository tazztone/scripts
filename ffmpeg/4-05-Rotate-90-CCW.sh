#!/bin/bash
# Rotate 90 CCW
# Fixes sideways phone videos (other way).

(
for f in "$@"; do
    echo "# Rotating $f 90 CCW..."
    # transpose=2 is 90CounterClockwise
    ffmpeg -y -i "$f" -vf "transpose=2" -c:a copy "${f%.*}_rot90ccw.mp4"
done
) | zenity --progress --title="Rotating 90 CCW..." --pulsate --auto-close

zenity --notification --text="Rotation Finished!"
