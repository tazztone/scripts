#!/bin/bash

# 008-concat-videos.sh
# Usage: ./008-concat-videos.sh <output_file> <input1> <input2> ...

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <output_file> <input1> <input2> ..."
    echo "Note: Inputs should ideally have the same resolution and codecs."
    exit 1
fi

OUTPUT_FILE="$1"
shift

# Create a temporary list file for the concat demuxer
LIST_FILE=$(mktemp)

for input in "$@"; do
    echo "file '$(realpath "$input")'" >> "$LIST_FILE"
done

echo "Concatenating files into $OUTPUT_FILE..."
ffmpeg -f concat -safe 0 -i "$LIST_FILE" -c copy "$OUTPUT_FILE"

rm "$LIST_FILE"
echo "Done."
