#!/bin/bash

# compress_video.sh
# Usage: ./compress_video.sh <input_file> <crf> [preset] [output_file]

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <input_file> <crf> [preset] [output_file]"
    echo "  crf: 0-51 (lower is better quality, 18-28 is typical)"
    echo "  preset: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow"
    echo "Example: $0 input.mp4 23 fast"
    exit 1
fi

INPUT_FILE="$1"
CRF="$2"
PRESET="${3:-medium}"
OUTPUT_FILE="${4:-${INPUT_FILE%.*}_crf${CRF}.${INPUT_FILE##*.}}"

echo "Compressing $INPUT_FILE with CRF $CRF and preset $PRESET..."

# using libx264 for h264 compression
ffmpeg -i "$INPUT_FILE" -vcodec libx264 -crf "$CRF" -preset "$PRESET" -acodec copy "$OUTPUT_FILE"

echo "Compressed video saved to $OUTPUT_FILE"
