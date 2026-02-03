#!/bin/bash
# Crop Aspect Ratios
# Center-crop video to specific standard aspect ratios.

CHOICE=$(zenity --list --title="Target Aspect Ratio" --column="Ratio" --column="Usage" \
    "9:16" "Vertical (Shorts / Reels / TikTok)" \
    "16:9" "Widescreen (Standard TV/Web)" \
    "4:3" "Legacy TV / Square-ish" \
    "2.39:1" "Cinematic Ultrawide")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "9:16")   VF="crop=ih*(9/16):ih:(iw-ow)/2:0"; SUF="9x16" ;;
    "16:9")   VF="crop=iw:iw*9/16:0:(ih-ow)/2"; SUF="16x9" ;;
    "4:3")    VF="crop=ih*(4/3):ih:(iw-ow)/2:0"; SUF="4x3" ;;
    "2.39:1") VF="crop=iw:iw/2.39:0:(ih-ow)/2"; SUF="239" ;;
esac

(
for f in "$@"; do
    echo "# Cropping $f to $CHOICE..."
    ffmpeg -y -i "$f" -vf "$VF" -c:v libx264 -crf 20 -c:a copy "${f%.*}_$SUF.mp4"
done
) | zenity --progress --title="Cropping..." --pulsate --auto-close

zenity --notification --text="Aspect Ratio Crop Finished!"
