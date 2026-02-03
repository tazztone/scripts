#!/bin/bash
# Rewrap to MKV
# Use this to fix some container issues or for archiving.

(
for f in "$@"; do
    echo "# Rewrapping $f to MKV..."
    ffmpeg -y -i "$f" -c copy "${f%.*}_rewrap.mkv"
done
) | zenity --progress --title="Rewrapping to MKV..." --pulsate --auto-close

zenity --notification --text="Rewrap Finished!"
