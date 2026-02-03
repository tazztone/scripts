#!/bin/bash
# ProRes 4444
# Supports Alpha Channel (Transparency).

(
for f in "$@"; do
    echo "# Transcoding $f to ProRes 4444..."
    # profile 4 = 4444. profile 5 = 4444 XQ.
    ffmpeg -y -i "$f" -c:v prores_ks -profile:v 4 -vendor apl0 -bits_per_mb 8000 -pix_fmt yuv444p10le -c:a pcm_s16le "${f%.*}_prores4444.mov"
done
) | zenity --progress --title="Transcoding to ProRes 4444..." --pulsate --auto-close

zenity --notification --text="ProRes 4444 Finished!"
