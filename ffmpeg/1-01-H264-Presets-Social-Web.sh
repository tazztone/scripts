#!/bin/bash
# H.264 Presets (Social & Web)
# Optimized encodes for various platforms using libx264.

CHOICE=$(zenity --list --title="H.264 Presets" --column="Target" --column="Description" \
    "Universal" "High compatibility (CRF 23, 1080p)" \
    "Twitter" "High Quality (1080p, 25M bitrate limit)" \
    "WhatsApp" "Mobile friendly (480p, optimized size)")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "Universal")
        FLAGS="-c:v libx264 -crf 23 -preset slow -c:a aac -b:a 192k -movflags +faststart"
        SUF="universal"
        ;;
    "Twitter")
        FLAGS="-vf scale=-2:1080 -c:v libx264 -crf 18 -maxrate 25M -bufsize 25M -c:a aac -b:a 192k"
        SUF="twitter"
        ;;
    "WhatsApp")
        FLAGS="-vf scale=-2:480 -c:v libx264 -crf 28 -preset slow -c:a aac -b:a 128k -movflags +faststart"
        SUF="whatsapp"
        ;;
esac

(
for f in "$@"; do
    echo "# Encoding $f for $CHOICE..."
    ffmpeg -y -i "$f" $FLAGS "${f%.*}_$SUF.mp4"
done
) | zenity --progress --title="H.264 Encoding..." --pulsate --auto-close

zenity --notification --text="Encoding Finished!"
