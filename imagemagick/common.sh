#!/bin/bash
# Common utility functions for Nautilus ImageMagick Scripts

# Ensure dependencies
DEPENDENCIES=(zenity bc)

# Check for ImageMagick v7 (magick) or v6 (convert)
if command -v magick &> /dev/null; then
    IM_EXE="magick"
    IM_COMPOSITE="magick composite"
    IM_MONTAGE="magick montage"
elif command -v convert &> /dev/null; then
    IM_EXE="convert"
    IM_COMPOSITE="composite"
    IM_MONTAGE="montage"
else
    zenity --error --text="ImageMagick not found. Please install it (sudo apt install imagemagick)."
    exit 1
fi

for cmd in "${DEPENDENCIES[@]}"; do
    if ! command -v $cmd &> /dev/null; then
        zenity --error --text="Missing dependency: $cmd\nPlease install it."
        exit 1
    fi
done

# Zenity Progress Command Standard
Z_PROGRESS() {
    zenity --progress --title="$1" --pulsate --auto-close
}

# Show Error and Exit
error_exit() {
    zenity --error --text="$1"
    exit 1
}

# Generate unique temp file in current directory
get_cwd_temp() {
    mktemp "./${1:-tmp}_XXXXXX"
}

# Generate safe output filename (avoids overwrite)
# Usage: generate_safe_filename "base" "tag" "ext"
generate_safe_filename() {
    local base="$1"
    local tag="$2"
    local ext="$3"
    local out="${base}${tag}.${ext}"
    local ctr=1
    
    while [ -f "$out" ]; do
        out="${base}${tag}_v${ctr}.${ext}"
        ((ctr++))
    done
    echo "$out"
}
