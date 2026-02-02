#!/bin/bash
# Speed Up (2x)
# Doubles the speed of the video.

(
for f in "$@"; do
    echo "# Speeding up $f..."
    # setpts=0.5*PTS makes video 2x faster
    # atempo=2.0 makes audio 2x faster
    ffmpeg -y -i "$f" -vf "setpts=0.5*PTS" -filter:a "atempo=2.0" "${f%.*}_2x_speed.mp4"
done
) | zenity --progress --title="Speeding Up..." --pulsate --auto-close

zenity --notification --text="Speed Up Finished!"
