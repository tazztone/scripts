#!/bin/bash
# Images to Video
# Stitches JPGs in the selected folder (or current folder) into MP4.
# IMPORTANT: Select ONE image in the folder to target that folder.

FRAMERATE=$(zenity --scale --title="Framerate" --text="FPS" --value=24 --min-value=1 --max-value=60 --step=1)
if [ -z "$FRAMERATE" ]; then exit; fi

(
for f in "$@"; do
    DIR=$(dirname "$f")
    NAME=$(basename "$DIR")
    echo "# Stitching images in $DIR..."
    
    # Uses glob pattern for *.jpg in the directory
    ffmpeg -y -framerate "$FRAMERATE" -pattern_type glob -i "$DIR/*.jpg" -c:v libx264 -pix_fmt yuv420p "${DIR}_slideshow.mp4"
    
    # Break after first file since we process the whole folder
    break
done
) | zenity --progress --title="Creating Video from Images..." --pulsate --auto-close

zenity --notification --text="Video Created!"
