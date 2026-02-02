#!/bin/bash
# Boost Volume (+6dB)
# Quick fix for quiet audio.

(
for f in "$@"; do
    echo "# Boosting volume for $f..."
    # volume=6dB
    ffmpeg -y -i "$f" -c:v copy -af "volume=6dB" "${f%.*}_boost.mp4"
done
) | zenity --progress --title="Boosting Volume..." --pulsate --auto-close

zenity --notification --text="Volume Boosted!"
