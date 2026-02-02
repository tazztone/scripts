#!/bin/bash
# Burn Subtitles
# Hardcodes a selected .srt file into the video.

SUB_FILE=$(zenity --file-selection --title="Select Subtitle File (.srt)" --file-filter="*.srt")
if [ -z "$SUB_FILE" ]; then exit; fi

(
for f in "$@"; do
    echo "# Burning subs into $f..."
    # Escaping filename for filter
    # simple approach: use simple filter syntax. 
    # subtitles='filename.srt'
    # we need to handle potential special chars in path?
    # safest is to assume no crazy chars or warn user. 
    # ffmpeg escaping is hellish in bash.
    # We will try standard way.
    
    ffmpeg -y -i "$f" -vf "subtitles='$SUB_FILE'" -c:a copy "${f%.*}_hardsub.mp4"
done
) | zenity --progress --title="Burning Subtitles..." --pulsate --auto-close

zenity --notification --text="Subtitles Burned!"
