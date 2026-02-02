#!/bin/bash
# Extract WAV
# Lossless uncompressed CD quality audio.

(
for f in "$@"; do
    echo "# Extracting WAV from $f..."
    ffmpeg -y -i "$f" -vn -c:a pcm_s16le "${f%.*}.wav"
done
) | zenity --progress --title="Extracting WAV..." --pulsate --auto-close

zenity --notification --text="WAV Extracted!"
