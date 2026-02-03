#!/bin/bash
# ProRes 422
# Standard intermediate for editing.

(
for f in "$@"; do
    echo "# Transcoding $f to ProRes 422..."
    # profile 3 = 422 (HQ is 3, standard is 2, LT is 1, Proxy is 0)
    # Actually: 0=Proxy, 1=LT, 2=Standard, 3=HQ.
    # The user asked for "ProRes 422". I'll use Standard (profile 2). 
    # Warning: apcn is standard. apch is HQ. 
    # ffmpeg 'prores_ks' profile 2 is Standard.
    ffmpeg -y -i "$f" -c:v prores_ks -profile:v 2 -vendor apl0 -bits_per_mb 8000 -pix_fmt yuv422p10le -c:a pcm_s16le "${f%.*}_prores422.mov"
done
) | zenity --progress --title="Transcoding to ProRes 422..." --pulsate --auto-close

zenity --notification --text="ProRes 422 Finished!"
