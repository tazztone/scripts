#!/bin/bash

# 009-make-gif.sh
# Usage: ./009-make-gif.sh <input> <start> <duration> <width> [output]

if [ "$#" -lt 4 ]; then
    echo "Usage: $0 <input> <start> <duration> <width> [output]"
    echo "Example: $0 input.mp4 00:00:05 3 480 output.gif"
    exit 1
fi

INPUT="$1"
START="$2"
DUR="$3"
WIDTH="$4"
OUTPUT="${5:-${INPUT%.*}_clip.gif}"

echo "Generating high-quality GIF..."

# Two-pass approach with palette generation for better quality
ffmpeg -ss "$START" -t "$DUR" -i "$INPUT" -vf "fps=15,scale=$WIDTH:-1:flags=lanczos,palettegen" -y /tmp/palette.png
ffmpeg -ss "$START" -t "$DUR" -i "$INPUT" -i /tmp/palette.png -lavfi "fps=15,scale=$WIDTH:-1:flags=lanczos [x]; [x][1:v] paletteuse" -y "$OUTPUT"

rm /tmp/palette.png
echo "GIF saved to $OUTPUT"
