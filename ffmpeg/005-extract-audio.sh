#!/bin/bash

# extract_audio.sh
# Usage: ./extract_audio.sh <input_file> [output_format]

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <input_file> [output_format]"
    echo "Example: $0 video.mp4 mp3"
    exit 1
fi

INPUT_FILE="$1"
FORMAT="${2:-mp3}"
OUTPUT_FILE="${INPUT_FILE%.*}.$FORMAT"

echo "Extracting audio from $INPUT_FILE to $OUTPUT_FILE..."

if [ "$FORMAT" == "mp3" ]; then
    # Ensure good quality mp3
    ffmpeg -i "$INPUT_FILE" -vn -acodec libmp3lame -q:a 2 "$OUTPUT_FILE"
elif [ "$FORMAT" == "aac" ]; then
    ffmpeg -i "$INPUT_FILE" -vn -acodec aac "$OUTPUT_FILE"
elif [ "$FORMAT" == "wav" ]; then
    ffmpeg -i "$INPUT_FILE" -vn -acodec pcm_s16le "$OUTPUT_FILE"
else
    # Let ffmpeg guess or copy if possible, but safe default usually implies re-encode for audio
    ffmpeg -i "$INPUT_FILE" -vn "$OUTPUT_FILE"
fi

echo "Audio extracted to $OUTPUT_FILE"
