#!/bin/bash
# Custom Scale
# Asks for a specific width in pixels.

TARGET_WIDTH=$(zenity --scale --title="Scale Video" --text="Select Target Width (px)" --min-value=320 --max-value=3840 --value=1280 --step=2)

if [ -z "$TARGET_WIDTH" ]; then exit; fi

(
for f in "$@"; do
    echo "# Scaling $f to $TARGET_WIDTH..."
    ffmpeg -y -i "$f" -vf scale="$TARGET_WIDTH":-2 "${f%.*}_${TARGET_WIDTH}w.${f##*.}"
done
) | zenity --progress --title="Scaling Videos..." --pulsate --auto-close

zenity --notification --text="Scaling Finished!"
