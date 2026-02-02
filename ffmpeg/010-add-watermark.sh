#!/bin/bash

# 010-add-watermark.sh
# Usage: ./010-add-watermark.sh <video> <watermark_img> <position> [output]
# Positions: top-left, top-right, bottom-left, bottom-right, center

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <video> <watermark_img> <position> [output]"
    exit 1
fi

VIDEO="$1"
IMG="$2"
POS="$3"
OUTPUT="${4:-${VIDEO%.*}_watermarked.${VIDEO##*.}}"

case $POS in
    top-left)     OVERLAY="10:10" ;;
    top-right)    OVERLAY="main_w-overlay_w-10:10" ;;
    bottom-left)  OVERLAY="10:main_h-overlay_h-10" ;;
    bottom-right) OVERLAY="main_w-overlay_w-10:main_h-overlay_h-10" ;;
    center)       OVERLAY="(main_w-overlay_w)/2:(main_h-overlay_h)/2" ;;
    *)            OVERLAY="10:10" ;;
esac

echo "Adding watermark at $POS..."
ffmpeg -i "$VIDEO" -i "$IMG" -filter_complex "overlay=$OVERLAY" -codec:a copy "$OUTPUT"

echo "Watermarked video saved to $OUTPUT"
