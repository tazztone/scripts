#!/bin/bash
# Slow Motion (0.5x)
# Slows video to half speed.

(
for f in "$@"; do
    echo "# Slowing down $f..."
    # setpts=2.0*PTS makes video 2x slower
    # atempo=0.5 makes audio 2x slower
    ffmpeg -y -i "$f" -vf "setpts=2.0*PTS" -filter:a "atempo=0.5" "${f%.*}_slowmo.mp4"
done
) | zenity --progress --title="Slowing Down..." --pulsate --auto-close

zenity --notification --text="Slow Motion Finished!"
