#!/bin/bash
# Twitter/X Max Quality
# 1080p, Max Bitrate caps.

(
for f in "$@"; do
    echo "# Converting $f for Twitter..."
    
    # Twitter specs: 1080p, max 40fps (usually), bitrate < 25Mbps.
    # We'll stick to 1080p 30fps (or source fps if lower) and decently high bitrate.
    ffmpeg -y -i "$f" -vf "scale=-2:1080" -c:v libx264 -crf 18 -maxrate 25M -bufsize 25M -c:a aac -b:a 192k "${f%.*}_twitter.mp4"
done
) | zenity --progress --title="Processing for Twitter..." --pulsate --auto-close

zenity --notification --text="Twitter Export Finished!"
