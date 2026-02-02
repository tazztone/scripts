#!/bin/bash
# Stabilize Video
# Removes shakiness using the vid.stab library.

(
for f in "$@"; do
    echo "# Stabilizing $f (Pass 1)..."
    # Pass 1: Analyze
    ffmpeg -y -i "$f" -vf vidstabdetect=stepsize=32:shakiness=10:accuracy=10:result="transforms.trf" -f null -
    
    echo "# Stabilizing $f (Pass 2)..."
    # Pass 2: Stabilize
    ffmpeg -y -i "$f" -vf vidstabtransform=input="transforms.trf":zoom=0:smoothing=10,unsharp=5:5:0.8:3:3:0.4 -c:v libx264 -crf 23 -c:a copy "${f%.*}_stabilized.mp4"
    
    rm -f transforms.trf
done
) | zenity --progress --title="Stabilizing Video..." --pulsate --auto-close

zenity --notification --text="Stabilization Finished!"
