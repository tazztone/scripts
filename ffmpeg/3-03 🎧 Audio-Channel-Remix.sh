#!/bin/bash
# Channel Remixer
# Convert between Mono and Stereo.

CHOICE=$(zenity --list --title="Channel Remix" --column="Operation" --column="Description" \
    "Mono to Stereo" "Expand mono track to two channels" \
    "Stereo to Mono" "Downmix two channels to one")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "Mono to Stereo") CH=2; BR=192; SUF="stereo" ;;
    "Stereo to Mono") CH=1; BR=96; SUF="mono" ;;
esac

(
for f in "$@"; do
    echo "# Remixing $f..."
    ffmpeg -y -i "$f" -c:v copy -c:a aac -b:a "${BR}k" -ac "$CH" "${f%.*}_$SUF.mp4"
done
) | zenity --progress --title="Remixing Channels..." --pulsate --auto-close

zenity --notification --text="Channel Remix Finished!"
