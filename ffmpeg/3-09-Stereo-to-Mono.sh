#!/bin/bash
# Stereo to Mono
# Mixes down to a single center channel.

(
for f in "$@"; do
    echo "# Converting Stereo to Mono for $f..."
    # -ac 1 mixes to mono
    ffmpeg -y -i "$f" -c:v copy -c:a aac -b:a 96k -ac 1 "${f%.*}_mono.mp4"
done
) | zenity --progress --title="Stereo to Mono..." --pulsate --auto-close

zenity --notification --text="Converted to Mono!"
