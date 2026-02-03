#!/bin/bash
# WebM (VP9 + Alpha)
# Preserves transparency for web usage.

(
for f in "$@"; do
    echo "# Converting $f to WebM with Alpha..."
    
    # VP9 auto-detects alpha if present in input (like ProRes 4444)
    # -b:v 0 -crf 30 is recommended for VP9
    ffmpeg -y -i "$f" -c:v libvpx-vp9 -b:v 0 -crf 30 -pass 1 -an -f null /dev/null
    ffmpeg -y -i "$f" -c:v libvpx-vp9 -b:v 0 -crf 30 -pass 2 -c:a libvorbis "${f%.*}_alpha.webm"

    rm -f ffmpeg2pass-0.log
done
) | zenity --progress --title="Creating Transparent WebM..." --pulsate --auto-close

zenity --notification --text="WebM Export Finished!"
