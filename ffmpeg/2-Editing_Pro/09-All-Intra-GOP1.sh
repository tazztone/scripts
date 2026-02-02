#!/bin/bash
# GOP-1 (All-Intra)
# Huge file size, but every frame is a keyframe (instant seeking).

(
for f in "$@"; do
    echo "# Converting to All-Intra H.264..."
    # -g 1 sets GOP size to 1.
    ffmpeg -y -i "$f" -c:v libx264 -crf 20 -g 1 -c:a copy "${f%.*}_allintra.mp4"
done
) | zenity --progress --title="Creating All-Intra Media..." --pulsate --auto-close

zenity --notification --text="All-Intra Export Finished!"
