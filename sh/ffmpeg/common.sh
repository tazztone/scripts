# Common utility functions for Nautilus FFmpeg Scripts

# Sourcing Guard
[ "${_FFMPEG_COMMON_SH_LOADED:-0}" -eq 1 ] && return
readonly _FFMPEG_COMMON_SH_LOADED=1

_wizard_log() {
    if [[ "${DEBUG_MODE:-0}" == "1" ]]; then
        local log_dir="${LOG_DIR:-$HOME/.local/share/scripts-sh}"
        local log_file="${LOG_FILE:-$log_dir/debug.log}"
        mkdir -p "$log_dir"
        chmod 700 "$log_dir" 2>/dev/null
        echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$log_file"
        echo "[DEBUG] $1" >&2
    fi
}

# Ensure dependencies
# Check zenity first to use it for errors
init_ffmpeg_script() {
    if ! command -v zenity &> /dev/null; then
        printf "Error: zenity is not installed. Please install it (sudo apt install zenity).\n" >&2
        exit 1
    fi

    # Zenity 4+ Requirement Check
    local z_ver
    z_ver=$(zenity --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -n 1)
    if [ "$(echo "${z_ver:-0} < 4.0" | bc -l)" -eq 1 ]; then
        printf "Error: scripts-sh requires Zenity 4.0 or higher (found %s).\n" "${z_ver:-unknown}" >&2
        zenity --error --text="Upgrade Required: Zenity 4.0+ is needed for the checklist UI.\nFound: ${z_ver:-unknown}"
        exit 1
    fi

    for cmd in ffmpeg ffprobe bc; do
        if ! command -v "$cmd" &> /dev/null; then
            zenity --error --text="Missing dependency: $cmd\nPlease install it."
            exit 1
        fi
    done
}

# Zenity Progress Command Standard
# Usage: ( ... ) | $Z_PROGRESS "Title"
Z_PROGRESS() {
    zenity --progress --title="$1" --pulsate --auto-close
}

# Show Error and Exit
# Usage: error_exit "Message"
error_exit() {
    echo "Error: $1" >&2
    zenity --error --text="$1" --no-markup
    exit 1
}

# Get Video Duration in Seconds (float)
# Usage: get_duration "filename"
get_duration() {
    local d
    d=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$1")
    _wizard_log "ffprobe duration for $1: [$d]"
    if [ -z "$d" ]; then 
        echo "0"
        echo "Warning: Could not detect duration for $1" >&2
    else 
        echo "$d"
    fi
}

# --- GPU PROBE (Run once at startup) ---
GPU_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/scripts-sh-gpu-cache"
probe_gpu() {
    # Ensure cache directory exists
    mkdir -p "$(dirname "$GPU_CACHE")"
    
    # Skip if fresh cache exists (<24h)
    # Check modification time portably (GNU or BSD/macOS)
    local mtime
    if stat -c %Y "$GPU_CACHE" &>/dev/null; then
        mtime=$(stat -c %Y "$GPU_CACHE") # GNU
    else
        mtime=$(stat -f %m "$GPU_CACHE" 2>/dev/null || echo "0") # BSD/macOS
    fi

    if [ -f "$GPU_CACHE" ] && [ $(( $(date +%s) - mtime )) -lt 86400 ]; then
        return 0
    fi
    # Use a fresh file to avoid accumulation
    : > "$GPU_CACHE"
    
    # 1. NVENC Probe
    if ffmpeg -v error -nostdin -f lavfi -i color=black:s=1280x720 -vframes 1 -an -c:v h264_nvenc -f null - 2>/dev/null; then
        echo "nvenc" >> "$GPU_CACHE"
    fi
    
    # 2. QSV Probe
    if ffmpeg -v error -nostdin -f lavfi -i color=black:s=1280x720 -vframes 1 -an -c:v h264_qsv -f null - 2>/dev/null; then
        echo "qsv" >> "$GPU_CACHE"
    fi
    
    # 3. VAAPI Probe (Needs valid device)
    if ffmpeg -v error -nostdin -f lavfi -i color=black:s=1280x720 -vframes 1 -an -c:v h264_vaapi -f null - 2>/dev/null; then
        echo "vaapi" >> "$GPU_CACHE"
    fi
}

# Validate time formats: seconds, mm:ss, hh:mm:ss
validate_time_format() {
    local time_input="$1"
    
    # Check if it's a number (seconds)
    if [[ "$time_input" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo "$time_input"
        return 0
    fi
    
    # Check if it's hh:mm:ss format (reject hours > 2 digits, minutes/seconds >= 60)
    if [[ "$time_input" =~ ^([0-9]{1,2}):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?$ ]]; then
        local hours=${BASH_REMATCH[1]}
        local minutes=${BASH_REMATCH[2]}
        local seconds=${BASH_REMATCH[3]}
        local fraction=${BASH_REMATCH[4]:-}
        
        # Convert to seconds (force base 10 to avoid octal errors)
        local total_seconds=$((10#$hours * 3600 + 10#$minutes * 60 + 10#$seconds))
        echo "${total_seconds}${fraction}"
        return 0
    fi
    
    # Check if it's mm:ss format (reject minutes >= 60)
    if [[ "$time_input" =~ ^([0-5]?[0-9]):([0-5][0-9])(\.[0-9]+)?$ ]]; then
        local minutes=${BASH_REMATCH[1]}
        local seconds=${BASH_REMATCH[2]}
        local fraction=${BASH_REMATCH[3]:-}
        
        # Convert to seconds (force base 10 to avoid octal errors)
        local total_seconds=$((10#$minutes * 60 + 10#$seconds))
        echo "${total_seconds}${fraction}"
        return 0
    fi
    
    return 1
}

# Generate safe output filename (avoids overwrite)
# Usage: generate_safe_filename "base" "tag" "ext"
generate_safe_filename() {
    local base="$1"
    local tag="$2"
    local ext="$3"
    
    # NEW: Strip existing known tags recursively from basename ONLY
    local KNOWN_TAGS=(
        "_half" "_1920p" "_4k" "_720p" "_640p" "_sq" "_9x16" "_16x9"
        "_grid2x" "_grid3x" "_row" "_col" "_sheet" "_90cw" "_90ccw" "_flop"
        "_bw" "_flat" "_srgb" "_text" "_web" "_min" "_arch" "_edit" "_high"
        "_low" "_lossless" "_nvenc" "_qsv" "_vaapi" "_cut" "_len" "_audio"
        "_av1" "_mov" "_mkv"
    )
    local tag_regex
    tag_regex=$(IFS='|'; echo "${KNOWN_TAGS[*]}")
    
    local dir=$(dirname "$base")
    local bname=$(basename "$base")
    local clean_bname="$bname"
    
    while true; do
        local stripped=$(echo "$clean_bname" | sed -E "s/(${tag_regex})(_v[0-9]+)?$//")
        [ "$stripped" == "$clean_bname" ] && break
        clean_bname="$stripped"
    done
    
    local final_base="${dir}/${clean_bname}"
    # Clean up ./ if it was added unnecessarily (e.g. if original base didn't have it)
    # but the current logic is actually simpler: just use dir/name unless dir is empty.
    # Wait, dirname returns "." if there's no slash.
    if [[ "$base" == "./"* ]]; then
        final_base="./${clean_bname}"
    elif [ "$dir" == "." ]; then
        final_base="$clean_bname"
    fi

    local out="${final_base}${tag}.${ext}"
    local ctr=1
    
    while [ -f "$out" ]; do
        out="${final_base}${tag}_v${ctr}.${ext}"
        ((ctr++))
    done
    echo "$out"
}

# Generate unique temp file in current directory (for concat lists etc)
# Usage: get_temp_file "prefix"
get_cwd_temp() {
    mktemp "./${1:-tmp}_XXXXXX"
}

# Generate unique temp file in /tmp (for large logs/transforms)
# Usage: get_sys_temp "prefix"
get_sys_temp() {
    mktemp "/tmp/${1:-tmp}_XXXXXX"
}
