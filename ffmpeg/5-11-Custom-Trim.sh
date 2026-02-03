#!/bin/bash
# Custom Trim
# Allows entering a start time and duration.

START=$(zenity --entry --title="Trim Video" --text="Start Time (HH:MM:SS or seconds):" --entry-text="00:00:00")
if [ -z "$START" ]; then exit; fi

DUR=$(zenity --entry --title="Trim Video" --text="Duration (HH:MM:SS or seconds):" --entry-text="00:00:10")
if [ -z "$DUR" ]; then exit; fi

(
for f in "$@"; do
    echo "# Trimming $f..."
    ffmpeg -y -ss "$START" -i "$f" -t "$DUR" -c:v libx264 -crf 20 -c:a copy "${f%.*}_trim.mp4"
done
) | zenity --progress --title="Trimming..." --pulsate --auto-close

zenity --notification --text="Trim Finished!"
