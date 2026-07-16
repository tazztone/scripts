# Common utility functions for Nautilus ImageMagick Scripts

# Sourcing Guard
[ "${_IMAGEMAGICK_COMMON_SH_LOADED:-0}" -eq 1 ] && return
readonly _IMAGEMAGICK_COMMON_SH_LOADED=1

# Check for dependencies and ImageMagick versions
init_imagemagick_script() {
    _wizard_check_zenity

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

    for cmd in "${DEPENDENCIES[@]:-}"; do
        [ -z "$cmd" ] && continue
        if ! command -v "$cmd" &> /dev/null; then
            zenity --error --text="Missing dependency: $cmd\nPlease install it."
            exit 1
        fi
    done
}


