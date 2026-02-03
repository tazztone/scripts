#!/bin/bash
# Common utility functions for Nautilus FFmpeg Scripts

# Ensure dependencies
for cmd in ffmpeg ffprobe zenity bc; do
    if ! command -v $cmd &> /dev/null; then
        zenity --error --text="Missing dependency: $cmd\nPlease install it."
        exit 1
    fi
done

# Zenity Progress Command Standard
# Usage: ( ... ) | $Z_PROGRESS "Title"
Z_PROGRESS() {
    zenity --progress --title="$1" --pulsate --auto-close
}

# Show Error and Exit
# Usage: error_exit "Message"
error_exit() {
    zenity --error --text="$1"
    exit 1
}

# Get Video Duration in Seconds
# Usage: get_duration "filename"
get_duration() {
    local d
    d=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$1")
    if [ -z "$d" ]; then echo "0"; else echo "$d"; fi
}

# Generate unique temp file in current directory (for concat lists etc)
# Usage: get_temp_file "prefix"
get_cwd_temp() {
    mktemp "./${1:-tmp}_XXXXXX"
}

# Generate unique temp file in /tmp (for large logs/transforms)
# Usage: get_sys_temp "prefix"
get_sys_temp() {
    mktemp -u "/tmp/${1:-tmp}_XXXXXX"
}
