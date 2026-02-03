#!/bin/bash
# Audio Converter
# Extracts or converts audio to common formats.

CHOICE=$(zenity --list --title="Target Format" --column="Format" --column="Quality/Description" \
    "MP3" "V0 (High Quality VBR)" \
    "WAV" "Uncompressed 16-bit" \
    "FLAC" "Lossless Compression" \
    "AAC" "256k M4A")

if [ -z "$CHOICE" ]; then exit; fi

case "$CHOICE" in
    MP3) CMD="-vn -c:a libmp3lame -q:a 0"; EXT="mp3" ;;
    WAV) CMD="-vn -c:a pcm_s16le"; EXT="wav" ;;
    FLAC) CMD="-vn -c:a flac"; EXT="flac" ;;
    AAC) CMD="-vn -c:a aac -b:a 256k"; EXT="m4a" ;;
esac

(
for f in "$@"; do
    echo "# Converting $f to $CHOICE..."
    ffmpeg -y -i "$f" $CMD "${f%.*}.$EXT"
done
) | zenity --progress --title="Converting Audio..." --pulsate --auto-close

zenity --notification --text="Audio Conversion Finished!"
