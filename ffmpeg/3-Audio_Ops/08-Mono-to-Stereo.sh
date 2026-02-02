#!/bin/bash
# Mono to Stereo
# Duplicates one channel to both L and R.

(
for f in "$@"; do
    echo "# Converting Mono to Stereo for $f..."
    # -ac 2 downmixes/upmixes to 2 channels. 
    # If mono, it duplicates.
    ffmpeg -y -i "$f" -c:v copy -c:a aac -b:a 192k -ac 2 "${f%.*}_stereo.mp4"
done
) | zenity --progress --title="Mono to Stereo..." --pulsate --auto-close

zenity --notification --text="Converted to Stereo!"
