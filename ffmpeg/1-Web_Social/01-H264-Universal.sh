#!/bin/bash
# Universal MP4 (H.264/AAC)
# Best compatibility for sharing.

(
for f in "$@"; do
    echo "# Converting $f to Universal MP4..."
    # CRF 23 is a good balance for general use. Preset slow for better compression/quality ratio.
    ffmpeg -y -i "$f" -c:v libx264 -crf 23 -preset slow -c:a aac -b:a 192k -movflags +faststart "${f%.*}_universal.mp4"
done
) | zenity --progress --title="Converting to Universal H.264..." --pulsate --auto-close

zenity --notification --text="Conversion Finished!"
