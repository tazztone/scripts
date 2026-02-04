#!/bin/bash
# Smart Scaler
# Resize video to standard or custom resolutions.

CHOICE=$(zenity --list --title="Target Resolution" --column="Target" --column="Description" \
    "50%" "Half Scale" \
    "720p" "1280x720 (HD)" \
    "1080p" "1920x1080 (Full HD)" \
    "4K" "3840x2160 (UHD)" \
    "Custom" "Enter custom width...")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "50%") SCALE="scale=iw*0.5:-2"; SUF="50p" ;;
    "720p") SCALE="scale=-2:720"; SUF="720p" ;;
    "1080p") SCALE="scale=-2:1080"; SUF="1080p" ;;
    "4K") SCALE="scale=-2:2160"; SUF="4k" ;;
    "Custom")
        WIDTH=$(zenity --entry --title="Custom Width" --text="Enter Target Width (height will scale proportionally):" --entry-text="1280")
        if [ -z "$WIDTH" ]; then exit; fi
        SCALE="scale=$WIDTH:-2"; SUF="${WIDTH}w"
        ;;
esac

(
for f in "$@"; do
    echo "# Scaling $f..."
    ffmpeg -y -i "$f" -vf "$SCALE" "${f%.*}_$SUF.mp4"
done
) | zenity --progress --title="Scaling..." --pulsate --auto-close

zenity --notification --text="Scaling Finished!"
