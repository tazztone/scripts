#!/bin/bash
# H.265 Archive (HEVC)
# Half the file size of H.264 at same quality, but harder to play on old devices.

(
for f in "$@"; do
    echo "# Archiving $f to H.265..."
    # CRF 26 for HEVC corresponds roughly to CRF 23 for H.264 visually but smaller size.
    ffmpeg -y -i "$f" -c:v libx265 -crf 26 -preset medium -c:a aac -b:a 128k -tag:v hvc1 "${f%.*}_archive.mp4"
done
) | zenity --progress --title="Archiving to H.265..." --pulsate --auto-close

zenity --notification --text="Archiving Finished!"
