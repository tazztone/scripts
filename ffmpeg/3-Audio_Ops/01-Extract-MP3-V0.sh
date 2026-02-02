#!/bin/bash
# Extract MP3 (V0)
# Best balance of quality and size (Variable Bitrate).

(
for f in "$@"; do
    echo "# Extracting MP3 from $f..."
    # -q:a 0 is V0 (Best VBR quality, ~245 kbps)
    ffmpeg -y -i "$f" -vn -c:a libmp3lame -q:a 0 "${f%.*}.mp3"
done
) | zenity --progress --title="Extracting MP3..." --pulsate --auto-close

zenity --notification --text="MP3 Extracted!"
