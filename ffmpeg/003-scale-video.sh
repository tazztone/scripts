#!/bin/bash

# scale_video.sh
# Usage: ./scale_video.sh <input_file> <target_width> [output_file]

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <input_file> <target_width> [output_file]"
    exit 1
fi

INPUT_FILE="$1"
WIDTH="$2"
OUTPUT_FILE="${3:-${INPUT_FILE%.*}_${WIDTH}w.${INPUT_FILE##*.}}"

# -2 ensures the height is calculated to preserve aspect ratio and is even (required by some codecs)
ffmpeg -i "$INPUT_FILE" -vf scale="$WIDTH":-2 "$OUTPUT_FILE"

echo "Scaled video saved to $OUTPUT_FILE"
