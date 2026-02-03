#!/bin/bash
# Filters & Overlays (Subtitles / Watermarks)
# Apply visual overlays to the video stream.

CHOICE=$(zenity --list --title="Overlay Selection" --column="Type" --column="Description" \
    "Burn Subtitles" "Hardcode .srt file into video" \
    "Add Watermark" "Overlay an image (PNG/JPG)")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "Burn Subtitles")
        SUB_FILE=$(zenity --file-selection --title="Select Subtitle File (.srt)" --file-filter="*.srt")
        if [ -z "$SUB_FILE" ]; then exit; fi
        (
        for f in "$@"; do
            echo "# Burning subs into $f..."
            ffmpeg -y -i "$f" -vf "subtitles='$SUB_FILE'" -c:v libx264 -crf 20 -c:a copy "${f%.*}_hardsub.mp4"
        done
        ) | zenity --progress --title="Burning Subtitles..." --pulsate --auto-close
        ;;
    "Add Watermark")
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
        ;;
esac

zenity --notification --text="Filter Applied Successfully!"
