#!/bin/bash
# Remove Audio
# Creates a video track with no audio.

(
for f in "$@"; do
    echo "# Removing Audio from $f..."
    # -an disables audio
    ffmpeg -y -i "$f" -c:v copy -an "${f%.*}_noaudio.mp4"
done
) | zenity --progress --title="Removing Audio..." --pulsate --auto-close

zenity --notification --text="Audio Removed!"
