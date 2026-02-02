#!/bin/bash
# Split by Scene
# Detects cuts and saves separate files.
# Uses sc_threshold to force keyframes at scene changes and splits there.

(
for f in "$@"; do
    echo "# Splitting $f by scene..."
    # -segment_time 0.01 ensures we split at every forced keyframe
    # force_key_frames expr:gte(scene,0.3) detects 30% pixel change
    ffmpeg -y -i "$f" -c:v libx264 -c:a aac -force_key_frames "expr:gte(scene,0.3)" -f segment -segment_time 0.01 -reset_timestamps 1 "${f%.*}_scene%03d.mp4"
done
) | zenity --progress --title="Splitting by Scene..." --pulsate --auto-close

zenity --notification --text="Scene Split Finished!"
