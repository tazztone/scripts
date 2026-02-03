#!/bin/bash
# Uncompress (Raw Video)
# Warning: Creates MASSIVE files.

(
for f in "$@"; do
    echo "# Uncompressing $f..."
    ffmpeg -y -i "$f" -c:v rawvideo -c:a pcm_s16le "${f%.*}_raw.avi"
done
) | zenity --progress --title="Uncompressing..." --pulsate --auto-close

zenity --notification --text="Uncompressed Finished!"
