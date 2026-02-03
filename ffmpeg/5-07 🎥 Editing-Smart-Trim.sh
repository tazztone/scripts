#!/bin/bash
# Smart Trim
# Trim start, end, or specific section.

CHOICE=$(zenity --list --title="Trim Operation" --column="Type" --column="Description" \
    "Start" "Cut first N seconds" \
    "End" "Cut last N seconds" \
    "Range" "Specify Start and Duration")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "Start")
        VAL=$(zenity --entry --title="Trim Start" --text="Seconds to cut from beginning:" --entry-text="10")
        if [ -z "$VAL" ]; then exit; fi
        (
        for f in "$@"; do
            echo "# Trimming start of $f..."
            ffmpeg -y -ss "$VAL" -i "$f" -c:v libx264 -c:a aac "${f%.*}_trimmed_start.mp4"
        done
        ) | zenity --progress --title="Trimming Start..." --pulsate --auto-close
        ;;
    "End")
        VAL=$(zenity --entry --title="Trim End" --text="Seconds to cut from end:" --entry-text="10")
        if [ -z "$VAL" ]; then exit; fi
        (
        for f in "$@"; do
            DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
            if [ -z "$DURATION" ]; then continue; fi
            NEW_DUR=$(echo "$DURATION - $VAL" | bc)
            if (( $(echo "$NEW_DUR <= 0" | bc -l) )); then continue; fi
            ffmpeg -y -i "$f" -t "$NEW_DUR" -c:v libx264 -c:a aac "${f%.*}_trimmed_end.mp4"
        done
        ) | zenity --progress --title="Trimming End..." --pulsate --auto-close
        ;;
    "Range")
        START=$(zenity --entry --title="Trim Range" --text="Start Time (HH:MM:SS or seconds):" --entry-text="00:00:00")
        DUR=$(zenity --entry --title="Trim Range" --text="Duration (HH:MM:SS or seconds):" --entry-text="00:00:10")
        if [ -z "$START" ] || [ -z "$DUR" ]; then exit; fi
        (
        for f in "$@"; do
            ffmpeg -y -ss "$START" -i "$f" -t "$DUR" -c:v libx264 -crf 20 -c:a copy "${f%.*}_trim.mp4"
        done
        ) | zenity --progress --title="Trimming Range..." --pulsate --auto-close
        ;;
esac

zenity --notification --text="Trimming Finished!"
