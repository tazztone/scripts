#!/bin/bash
# Convert to AAC (M4A)
# Native Apple/MP4 audio format.

(
for f in "$@"; do
    echo "# Converting to AAC..."
    ffmpeg -y -i "$f" -vn -c:a aac -b:a 256k "${f%.*}.m4a"
done
) | zenity --progress --title="Converting to AAC..." --pulsate --auto-close

zenity --notification --text="AAC Conversion Finished!"
