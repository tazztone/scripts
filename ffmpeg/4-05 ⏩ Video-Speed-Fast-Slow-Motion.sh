#!/bin/bash
# Video Speed (Fast / Slow Motion)
# Adjust playback speed of video and audio.

CHOICE=$(zenity --list --title="Speed Control" --column="Speed" --column="Description" \
    "2x Fast" "Double speed (50% duration)" \
    "4x Fast" "Quadruple speed (25% duration)" \
    "0.5x Slow" "Half speed (2x duration)" \
    "0.25x Slow" "Quarter speed (4x duration)" \
    "Custom" "Enter custom speed multiplier")

if [ -z "$CHOICE" ]; then exit; fi

if [ "$CHOICE" == "Custom" ]; then
    SPEED=$(zenity --entry --title="Custom Speed" --text="Enter multiplier (e.g. 1.5 for fast, 0.7 for slow):" --entry-text="1.0")
    if [ -z "$SPEED" ]; then exit; fi
else
    SPEED=$(echo "$CHOICE" | grep -oE "[0-9.]+")
fi

# PTS = 1/Speed
PTS_VAL=$(echo "scale=4; 1/$SPEED" | bc)

# Calculate audio filter chain
# atempo is limited to [0.5, 2.0]. We chain them for larger/smaller values.
AFILTER=""
REMAINING_SPEED=$SPEED

# Handle Slow Motion (< 0.5)
while (( $(echo "$REMAINING_SPEED < 0.5" | bc -l) )); do
    AFILTER="${AFILTER}atempo=0.5,"
    REMAINING_SPEED=$(echo "$REMAINING_SPEED * 2" | bc -l)
done

# Handle Fast Motion (> 2.0)
while (( $(echo "$REMAINING_SPEED > 2.0" | bc -l) )); do
    AFILTER="${AFILTER}atempo=2.0,"
    REMAINING_SPEED=$(echo "$REMAINING_SPEED / 2" | bc -l)
done

# Add remaining factor
AFILTER="${AFILTER}atempo=${REMAINING_SPEED}"

(
for f in "$@"; do
    # Detect Framerate if Speed > 1 (Fast Motion) to optionally preserve it
    FPS_OPT=""
    if (( $(echo "$SPEED > 1" | bc -l) )); then
        if zenity --question --text="Preserve original framerate?\n(Drop frames to prevent high-FPS output)" --title="Framerate Option" --no-wrap; then
            # Get input FPS
            IN_FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$f")
            if [ -n "$IN_FPS" ]; then
                FPS_OPT="-r $IN_FPS"
                echo "# Preserving input FPS: $IN_FPS"
            fi
        fi
    fi

    echo "# Changing speed of $f to ${SPEED}x..."
    ffmpeg -y -i "$f" -vf "setpts=${PTS_VAL}*PTS" $FPS_OPT -filter:a "$AFILTER" "${f%.*}_${SPEED}x.mp4"
done
) | zenity --progress --title="Changing Speed..." --pulsate --auto-close

zenity --notification --text="Speed Change Finished!"
