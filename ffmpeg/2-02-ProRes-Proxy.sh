#!/bin/bash
# ProRes Proxy
# Low bandwidth for smooth editing on slow machines.

(
for f in "$@"; do
    echo "# Transcoding $f to ProRes Proxy..."
    # profile 0 = Proxy
    ffmpeg -y -i "$f" -c:v prores_ks -profile:v 0 -vendor apl0 -bits_per_mb 8000 -pix_fmt yuv422p10le -c:a pcm_s16le "${f%.*}_proxy.mov"
done
) | zenity --progress --title="Transcoding to Proxy..." --pulsate --auto-close

zenity --notification --text="ProRes Proxy Finished!"
