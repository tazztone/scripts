#!/bin/bash

# 011-generate-thumbnails.sh
# Usage: ./011-generate-thumbnails.sh <input> <interval_sec> [output_pattern]

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <input> <interval_sec> [output_pattern]"
    echo "Example: $0 input.mp4 5 thumb_%03d.jpg"
    exit 1
fi

INPUT="$1"
INTERVAL="$2"
PATTERN="${3:-${INPUT%.*}_thumb_%03d.jpg}"

echo "Generating thumbnails every $INTERVAL seconds..."
ffmpeg -i "$INPUT" -vf "fps=1/$INTERVAL" "$PATTERN"

echo "Thumbnails saved using pattern $PATTERN"
