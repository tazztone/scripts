#!/bin/bash
for f in "$@"; do
    ffmpeg -i "$f" -c:v copy -c:a pcm_s16le "${f%.*}_fixed.mov"
done

