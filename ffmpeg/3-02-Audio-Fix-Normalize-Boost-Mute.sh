#!/bin/bash
# Audio Fix (Normalize / Boost / Mute)
# Adjust volume levels or remove audio entirely.

CHOICE=$(zenity --list --title="Audio Adjustment" --column="Type" --column="Description" \
    "Normalize" "EBU R128 Loudness Standard (-23 LUFS)" \
    "Boost +6dB" "Increase volume significantly" \
    "Mute" "Remove all audio tracks (Strip audio)")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    "Normalize")
        FLAGS="-c:v copy -af loudnorm=I=-23:LRA=7:TP=-1.5"
        SUF="norm"
        ;;
    "Boost +6dB")
        FLAGS="-c:v copy -af volume=6dB"
        SUF="boost"
        ;;
    "Mute")
        FLAGS="-c:v copy -an"
        SUF="noaudio"
        ;;
esac

(
for f in "$@"; do
    echo "# Processing audio for $f..."
    ffmpeg -y -i "$f" $FLAGS "${f%.*}_$SUF.mp4"
done
) | zenity --progress --title="Processing Audio..." --pulsate --auto-close

zenity --notification --text="Audio Adjustment Finished!"
