#!/bin/bash
# Vertical Crop (9:16)
# CENTER CROPS the video to vertical aspect ratio (for TikTok/Reels/Shorts).

(
for f in "$@"; do
    echo "# Cropping $f to 9:16..."
    
    # Crop logic: width = height * (9/16), height = height, x = (in_w - out_w)/2
    ffmpeg -y -i "$f" -vf "crop=ih*(9/16):ih:(iw-ow)/2:0" -c:v libx264 -crf 23 -c:a copy "${f%.*}_vertical.mp4"
done
) | zenity --progress --title="Cropping to Vertical..." --pulsate --auto-close

zenity --notification --text="Vertical Crop Finished!"
