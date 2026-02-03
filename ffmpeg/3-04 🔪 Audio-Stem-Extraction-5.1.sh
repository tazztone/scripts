#!/bin/bash
# Extract Stems (5.1 to 6 mono WAVs)
# Splits surround sound into separate files.

(
for f in "$@"; do
    echo "# Splitting $f into stems..."
    
    # We use channelsplit filter
    ffmpeg -y -i "$f" -filter_complex "channelsplit=channel_layout=5.1[FL][FR][FC][LFE][BL][BR]" \
    -map "[FL]" "${f%.*}_FL.wav" \
    -map "[FR]" "${f%.*}_FR.wav" \
    -map "[FC]" "${f%.*}_FC.wav" \
    -map "[LFE]" "${f%.*}_LFE.wav" \
    -map "[BL]" "${f%.*}_BL.wav" \
    -map "[BR]" "${f%.*}_BR.wav"

done
) | zenity --progress --title="Extracting Stems..." --pulsate --auto-close

zenity --notification --text="Stems Extracted!"
