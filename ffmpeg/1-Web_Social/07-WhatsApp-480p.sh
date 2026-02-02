#!/bin/bash
# WhatsApp Optimized
# 480p limit to ensure quick sending and compatibility.

(
for f in "$@"; do
    echo "# Optimizing $f for WhatsApp..."
    # WhatsApp likes 480p H.264 AAC
    ffmpeg -y -i "$f" -vf "scale=-2:480" -c:v libx264 -crf 28 -preset slow -c:a aac -b:a 128k -movflags +faststart "${f%.*}_whatsapp.mp4"
done
) | zenity --progress --title="Optimizing for WhatsApp..." --pulsate --auto-close

zenity --notification --text="WhatsApp Optimize Finished!"
