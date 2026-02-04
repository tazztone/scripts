#!/bin/bash
# Image Extract (Thumbnails & Sequences)
# Extract still images from video files.

CHOICE=$(zenity --list --title="Image Extraction" --column="Type" --column="Description" \
    "Thumbnail" "Single high-quality frame from the middle" \
    "Sequence" "Every frame to a JPEG file" \
    "Interval" "One frame every N seconds")

if [ -z "$CHOICE" ]; then exit; fi

(
for f in "$@"; do
    case "$CHOICE" in
        "Thumbnail")
            echo "# Analyzing $f..."
            DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
            if [ -z "$DURATION" ]; then continue; fi
            MID=$(echo "$DURATION / 2" | bc)
            ffmpeg -y -ss "$MID" -i "$f" -vframes 1 -q:v 2 "${f%.*}_thumb.jpg"
            ;;
        "Sequence")
            DIR="${f%.*}_sequence"
            mkdir -p "$DIR"
            echo "# Exporting sequence for $f..."
            ffmpeg -y -i "$f" -q:v 2 "$DIR/%05d.jpg"
            ;;
        "Interval")
            VAL=$(zenity --entry --title="Interval" --text="Extract frame every N seconds:" --entry-text="5")
            if [ -z "$VAL" ]; then exit; fi
            DIR="${f%.*}_thumbs"
            mkdir -p "$DIR"
            echo "# Exporting frames at ${VAL}s intervals..."
            ffmpeg -y -i "$f" -vf "fps=1/$VAL" -q:v 2 "$DIR/thumb_%04d.jpg"
            ;;
    esac
done
) | zenity --progress --title="Extracting Images..." --pulsate --auto-close

zenity --notification --text="Image Extraction Finished!"
