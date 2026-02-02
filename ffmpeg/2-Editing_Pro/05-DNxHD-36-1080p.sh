#!/bin/bash
# DNxHD 36 (LB)
# Lightweight 1080p Proxy for Avid.

(
for f in "$@"; do
    echo "# Transcoding $f to DNxHD 36..."
    # Must be 1080p. We scale just in case.
    # bitrate 36M is strict.
    ffmpeg -y -i "$f" -vf "scale=1920:1080" -c:v dnxhd -b:v 36M -c:a pcm_s16le "${f%.*}_dnxhd36.mov"
done
) | zenity --progress --title="Transcoding to DNxHD 36..." --pulsate --auto-close

zenity --notification --text="DNxHD 36 Finished!"
