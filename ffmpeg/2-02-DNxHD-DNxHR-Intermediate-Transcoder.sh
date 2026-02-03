#!/bin/bash
# DNxHD / DNxHR Transcoder
# Avid-friendly intermediate codecs for high-performance editing.

CHOICE=$(zenity --list --title="Avid DNx Profile" --column="Profile" --column="Description" \
    "DNxHD 36" "1080p Proxy (36 Mbps, LB)" \
    "DNxHR LB" "Low Bandwidth (Resolution independent)" \
    "DNxHR SQ" "Standard Quality (Resolution independent)" \
    "DNxHR HQ" "High Quality (8-bit)")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "DNxHD 36") FLAGS="-vf scale=1920:1080 -c:v dnxhd -b:v 36M"; SUF="dnxhd36" ;;
    "DNxHR LB") FLAGS="-c:v dnxhd -profile:v dnxhr_lb"; SUF="dnxhr_lb" ;;
    "DNxHR SQ") FLAGS="-c:v dnxhd -profile:v dnxhr_sq"; SUF="dnxhr_sq" ;;
    "DNxHR HQ") FLAGS="-c:v dnxhd -profile:v dnxhr_hq"; SUF="dnxhr_hq" ;;
esac

(
for f in "$@"; do
    echo "# Transcoding $f to $CHOICE..."
    ffmpeg -y -i "$f" $FLAGS -c:a pcm_s16le "${f%.*}_$SUF.mov"
done
) | zenity --progress --title="Transcoding to $CHOICE..." --pulsate --auto-close

zenity --notification --text="DNx Transcoding Finished!"
