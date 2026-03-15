# Common utility functions for Nautilus ImageMagick Scripts

# Ensuring Zenity for errors
if ! command -v zenity &> /dev/null; then
    printf "Error: zenity is not installed. Please install it (sudo apt install zenity).\n" >&2
    exit 1
fi

# Check for ImageMagick v7 (magick) or v6 (convert)
if command -v magick &> /dev/null; then
    IM_EXE="magick"
    IM_MONTAGE="magick montage"
    IM_IDENTIFY="magick identify"
elif command -v convert &> /dev/null; then
    IM_EXE="convert"
    IM_MONTAGE="montage"
    IM_IDENTIFY="identify"
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
    
    # NEW: Strip existing known tags recursively to prevent stacking (e.g. image_half_half)
    # This list should match common tags used across scripts
    local KNOWN_TAGS="_half|_1920p|_4k|_720p|_640p|_sq|_9x16|_16x9|_grid2x|_grid3x|_row|_col|_sheet|_90cw|_90ccw|_flop|_bw|_flat|_srgb|_text|_web|_min|_arch|_edit|_high|_low|_lossless|_nvenc|_qsv|_vaapi|_cut|_len|_audio|_av1|_mov|_mkv"
    
    local clean_base="$base"
    while true; do
        local stripped=$(echo "$clean_base" | sed -E "s/(${KNOWN_TAGS})(_v[0-9]+)?$//")
        [ "$stripped" == "$clean_base" ] && break
        clean_base="$stripped"
    done
    
    local out="${clean_base}${tag}.${ext}"
    local ctr=1
    
    while [ -f "$out" ]; do
        out="${clean_base}${tag}_v${ctr}.${ext}"
        ((ctr++))
    done
    echo "$out"
}
