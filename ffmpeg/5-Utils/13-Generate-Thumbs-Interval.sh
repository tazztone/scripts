#!/bin/bash
# Interval Thumbnails
# Extracts a frame every X seconds.

INTERVAL=$(zenity --scale --title="Thumbnail Interval" --text="Seconds between frames" --min-value=1 --max-value=60 --value=5 --step=1)
if [ -z "$INTERVAL" ]; then exit; fi

(
for f in "$@"; do
    echo "# Generating thumbnails for $f..."
    DIR="${f%.*}_thumbs"
    mkdir -p "$DIR"
    
    # fps=1/N means 1 frame every N seconds
    ffmpeg -y -i "$f" -vf "fps=1/$INTERVAL" -q:v 2 "$DIR/thumb_%04d.jpg"
done
) | zenity --progress --title="Generating Thumbs..." --pulsate --auto-close

zenity --notification --text="Thumbnails Generated in Folder!"
