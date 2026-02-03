#!/bin/bash
# High Quality GIF
# Generates custom palette for best color accuracy.

WIDTH=$(zenity --scale --title="GIF Width" --text="Select Width (px)" --value=640 --min-value=320 --max-value=1280 --step=2)

if [ -z "$WIDTH" ]; then exit; fi

(
for f in "$@"; do
    echo "# Generating Palette for $f..."
    # 1. Generate Palette
    ffmpeg -y -i "$f" -vf "fps=15,scale=$WIDTH:-1:flags=lanczos,palettegen" "${f%.*}_palette.png"
    
    echo "# Creating GIF..."
    # 2. Use Palette
    ffmpeg -y -i "$f" -i "${f%.*}_palette.png" -filter_complex "fps=15,scale=$WIDTH:-1:flags=lanczos[x];[x][1:v]paletteuse" "${f%.*}.gif"

    rm -f "${f%.*}_palette.png"
done
) | zenity --progress --title="Making GIF ($WIDTH px)..." --pulsate --auto-close

zenity --notification --text="GIF Created!"
