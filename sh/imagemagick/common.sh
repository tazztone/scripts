#!/bin/bash
# Common utility functions for Nautilus ImageMagick Scripts

# Ensure dependencies
DEPENDENCIES=(zenity)

# Check for ImageMagick v7 (magick) or v6 (convert)
if command -v magick &> /dev/null; then
    IM_EXE="magick"
    IM_MONTAGE="magick montage"
elif command -v convert &> /dev/null; then
    IM_EXE="convert"
    IM_MONTAGE="montage"
else
    zenity --error --text="ImageMagick not found. Please install it (sudo apt install imagemagick)."
    exit 1
fi

for cmd in "${DEPENDENCIES[@]}"; do
    if ! command -v "$cmd" &> /dev/null; then
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
    
    # NEW: Strip existing known tags to prevent stacking (e.g. image_half_half)
    # This list should match common tags used across scripts
    local KNOWN_TAGS="_half|_1920p|_4k|_720p|_640p|_sq|_9x16|_16x9|_grid2x|_grid3x|_row|_col|_sheet|_90cw|_90ccw|_flop|_bw|_flat|_srgb|_text|_web|_min|_arch|_edit"
    
    # Remove tags from the end of the base filename
    local clean_base=$(echo "$base" | sed -E "s/(${KNOWN_TAGS})(_v[0-9]+)?$//")
    
    local out="${clean_base}${tag}.${ext}"
    local ctr=1
    
    while [ -f "$out" ]; do
        out="${clean_base}${tag}_v${ctr}.${ext}"
        ((ctr++))
    done
    echo "$out"
}
