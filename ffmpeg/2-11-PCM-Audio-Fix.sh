#!/bin/bash
# PCM Audio Fix
# Transcodes audio to high-quality PCM while copying video. Best for editing.

(
for f in "$@"; do
    echo "# Fixing audio for $f..."
    ffmpeg -y -i "$f" -c:v copy -c:a pcm_s16le "${f%.*}_pcm_fixed.mov"
done
) | zenity --progress --title="Fixing Audio..." --pulsate --auto-close

zenity --notification --text="Audio Fix Finished!"
