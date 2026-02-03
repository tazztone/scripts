#!/bin/bash
# Container Rewrapper
# Change file format without re-encoding (Zero quality loss).

CHOICE=$(zenity --list --title="Target Container" --column="Format" --column="Notes" \
    "MP4" "MPEG-4 Base Media" \
    "MOV" "QuickTime / Apple" \
    "MKV" "Matroska (Highly Flexible)" \
    "TS" "MPEG Transport Stream")

if [ -z "$CHOICE" ]; then exit; fi

EXT=$(echo "$CHOICE" | tr '[:upper:]' '[:lower:]')

(
for f in "$@"; do
    echo "# Rewrapping $f to $CHOICE..."
    ffmpeg -y -i "$f" -c copy "${f%.*}.$EXT"
done
) | zenity --progress --title="Rewrapping..." --pulsate --auto-close

zenity --notification --text="Rewrapping Finished!"
