#!/bin/bash
# Geometry Transformer
# Rotate, flip, or transpose video.

CHOICE=$(zenity --list --title="Geometric Transform" --column="Operation" --column="Description" \
    "90 CW" "Rotate 90 degrees Clockwise" \
    "90 CCW" "Rotate 90 degrees Counter-Clockwise" \
    "180" "Rotate 180 degrees" \
    "Flip H" "Horizontal Flip (Mirror)" \
    "Flip V" "Vertical Flip")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "90 CW") VF="transpose=1"; SUF="90cw" ;;
    "90 CCW") VF="transpose=2"; SUF="90ccw" ;;
    "180") VF="transpose=1,transpose=1"; SUF="180" ;;
    "Flip H") VF="hflip"; SUF="hflip" ;;
    "Flip V") VF="vflip"; SUF="vflip" ;;
esac

(
for f in "$@"; do
    echo "# Transforming $f..."
    ffmpeg -y -i "$f" -vf "$VF" -c:a copy "${f%.*}_$SUF.mp4"
done
) | zenity --progress --title="Transforming..." --pulsate --auto-close

zenity --notification --text="Transformation Finished!"
