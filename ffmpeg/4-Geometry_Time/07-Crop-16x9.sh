#!/bin/bash
# Crop to 16:9
# Forces widescreen aspect ratio by cropping top/bottom or sides.

(
for f in "$@"; do
    echo "# Cropping $f to 16:9..."
    # Width = Height * (16/9) if image is too tall
    # Or Height = Width * (9/16) if image is too wide
    # This naive crop assumes we want to maximize size.
    # We'll assume input is usually 4:3 or similar and we want to crop height to fit 16:9 width? 
    # Or force 16:9. safely: crop=w=iw:h=iw*9/16:x=0:y=(ih-ow)/2
    ffmpeg -y -i "$f" -vf "crop=iw:iw*9/16:0:(ih-ow)/2" "${f%.*}_16x9.mp4"
done
) | zenity --progress --title="Cropping to 16:9..." --pulsate --auto-close

zenity --notification --text="Crop Finished!"
