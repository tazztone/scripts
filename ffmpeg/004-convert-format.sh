#!/bin/bash

# convert_format.sh
# Usage: ./convert_format.sh <input_file> <target_extension> [output_file]

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <input_file> <target_extension> [output_file]"
    echo "Example: $0 input.mkv mp4"
    exit 1
fi

INPUT_FILE="$1"
EXT="$2"
# Remove dot if present in extension
EXT="${EXT#.}"
OUTPUT_FILE="${3:-${INPUT_FILE%.*}.$EXT}"

echo "Converting $INPUT_FILE to $OUTPUT_FILE..."

# We let ffmpeg handle codec selection automatically for the target container
ffmpeg -i "$INPUT_FILE" "$OUTPUT_FILE"

echo "Conversion complete: $OUTPUT_FILE"
