#!/bin/bash

# trim_video.sh
# Usage: ./trim_video.sh <input_file> <start_time> <duration> [output_file]

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <input_file> <start_time> <duration> [output_file]"
    echo "Example: $0 input.mp4 00:00:10 00:00:05 output.mp4"
    echo "Note: Uses stream copying for speed. Cuts may occur at nearest keyframe."
    exit 1
fi

INPUT_FILE="$1"
START="$2"
DURATION="$3"
OUTPUT_FILE="${4:-${INPUT_FILE%.*}_trim.${INPUT_FILE##*.}}"

echo "Trimming $INPUT_FILE from $START for $DURATION..."

# -ss before -i is fast seek
ffmpeg -ss "$START" -i "$INPUT_FILE" -t "$DURATION" -c copy "$OUTPUT_FILE"

echo "Trimmed video saved to $OUTPUT_FILE"
