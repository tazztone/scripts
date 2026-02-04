#!/bin/bash
# Metadata & Web Optimize
# Clean file metadata and optimize for web streaming.

CHOICE=$(zenity --list --title="File Polish" --column="Type" --column="Description" \
    "Strip Metadata" "Remove all tags, GPS, and personal info" \
    "Web Optimize" "Move atom to start for instant streaming" \
    "Full Polish" "Strip metadata AND optimize for web")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "Strip Metadata") FLAGS="-map_metadata -1 -c copy"; SUF="clean" ;;
    "Web Optimize")   FLAGS="-c copy -movflags +faststart"; SUF="web" ;;
    "Full Polish")    FLAGS="-map_metadata -1 -c copy -movflags +faststart"; SUF="polished" ;;
esac

(
for f in "$@"; do
    echo "# Polishing $f..."
    ffmpeg -y -i "$f" $FLAGS "${f%.*}_$SUF.mp4"
done
) | zenity --progress --title="Polishing File..." --pulsate --auto-close

zenity --notification --text="File Polish Finished!"
