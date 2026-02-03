#!/bin/bash
# ProRes Transcoder
# Standard intermediates for professional editing.

CHOICE=$(zenity --list --title="ProRes Profile" --column="Profile" --column="Description" \
    "Proxy" "Lowest bitrate (profile 0)" \
    "LT" "Lower bitrate (profile 1)" \
    "Standard" "Standard 422 (profile 2)" \
    "HQ" "High Quality (profile 3)" \
    "4444" "Lossless with Alpha (profile 4)")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    Proxy) PROF=0; PIX="yuv422p10le"; SUF="proxy" ;;
    LT) PROF=1; PIX="yuv422p10le"; SUF="lt" ;;
    Standard) PROF=2; PIX="yuv422p10le"; SUF="422" ;;
    HQ) PROF=3; PIX="yuv422p10le"; SUF="hq" ;;
    4444) PROF=4; PIX="yuv444p10le"; SUF="4444" ;;
esac

(
for f in "$@"; do
    echo "# Transcoding $f to ProRes $CHOICE..."
    ffmpeg -y -i "$f" -c:v prores_ks -profile:v "$PROF" -vendor apl0 -bits_per_mb 8000 -pix_fmt "$PIX" -c:a pcm_s16le "${f%.*}_$SUF.mov"
done
) | zenity --progress --title="Transcoding to ProRes $CHOICE..." --pulsate --auto-close

zenity --notification --text="ProRes Transcoding Finished!"
