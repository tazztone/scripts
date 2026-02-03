#!/bin/bash
# Extract FLAC
# Lossless compressed audio.

(
for f in "$@"; do
    echo "# Extracting FLAC from $f..."
    ffmpeg -y -i "$f" -vn -c:a flac "${f%.*}.flac"
done
) | zenity --progress --title="Extracting FLAC..." --pulsate --auto-close

zenity --notification --text="FLAC Extracted!"
