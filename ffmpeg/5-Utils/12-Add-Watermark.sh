#!/bin/bash
# Add Watermark
# Overlays an image on the video.

IMG_FILE=$(zenity --file-selection --title="Select Watermark Image" --file-filter="*.png *.jpg *.jpeg")
if [ -z "$IMG_FILE" ]; then exit; fi

POSITION=$(zenity --list --title="Position" --column="Position" "top-left" "top-right" "bottom-left" "bottom-right" "center")
if [ -z "$POSITION" ]; then exit; fi

case $POSITION in
    "top-left") POS="W*0.05:H*0.05" ;;
    "top-right") POS="W-w-W*0.05:H*0.05" ;;
    "bottom-left") POS="W*0.05:H-h-H*0.05" ;;
    "bottom-right") POS="W-w-W*0.05:H-h-H*0.05" ;;
    "center") POS="(W-w)/2:(H-h)/2" ;;
esac

(
for f in "$@"; do
    echo "# Watermarking $f..."
    ffmpeg -y -i "$f" -i "$IMG_FILE" -filter_complex "overlay=$POS" -c:v libx264 -crf 23 -c:a copy "${f%.*}_watermarked.mp4"
done
) | zenity --progress --title="Adding Watermark..." --pulsate --auto-close

zenity --notification --text="Watermark Added!"
