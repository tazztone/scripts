#!/bin/bash
# DNxHR SQ
# Avid-friendly intermediate (Resolution Independent / 4K).

(
for f in "$@"; do
    echo "# Transcoding $f to DNxHR SQ..."
    # DNxHR requires "dnxhd" codec but with specific profiles like "dnxhr_sq"
    ffmpeg -y -i "$f" -c:v dnxhd -profile:v dnxhr_sq -c:a pcm_s16le "${f%.*}_dnxhr.mov"
done
) | zenity --progress --title="Transcoding to DNxHR SQ..." --pulsate --auto-close

zenity --notification --text="DNxHR Finished!"
