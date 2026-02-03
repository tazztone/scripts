#!/bin/bash
# Export Image Sequence
# Dumps every frame as a JPG image.

(
for f in "$@"; do
    echo "# Exporting frames for $f..."
    # Create directory
    DIR="${f%.*}_frames"
    mkdir -p "$DIR"
    
    ffmpeg -y -i "$f" -q:v 2 "$DIR/%05d.jpg"
done
) | zenity --progress --title="Exporting Frames..." --pulsate --auto-close

zenity --notification --text="Frames Exported!"
