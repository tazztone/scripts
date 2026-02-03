#!/bin/bash
# Remove Metadata
# Cleans GPS, Camera, and other tag info.

(
for f in "$@"; do
    echo "# Cleaning $f..."
    ffmpeg -y -i "$f" -map_metadata -1 -c copy "${f%.*}_clean.mp4"
done
) | zenity --progress --title="Removing Metadata..." --pulsate --auto-close

zenity --notification --text="Metadata Removed!"
