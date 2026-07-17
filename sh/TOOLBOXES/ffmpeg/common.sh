# Common utility functions for Nautilus FFmpeg Scripts

# Sourcing Guard
[ "${_FFMPEG_COMMON_SH_LOADED:-0}" -eq 1 ] && return
readonly _FFMPEG_COMMON_SH_LOADED=1

_COMMON_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$_COMMON_DIR/media_profile.sh"

# Ensure dependencies
# Check zenity first to use it for errors
init_ffmpeg_script() {
    _wizard_check_zenity

    for cmd in ffmpeg ffprobe bc; do
        if ! command -v "$cmd" &> /dev/null; then
            zenity --error --text="Missing dependency: $cmd\nPlease install it."
            exit 1
        fi
    done
}


# Get Video Duration in Seconds (float)
# Usage: get_duration "filename"
get_duration() {
    if probe_media "$1"; then
        local d="${PROBED_INFO[duration]:-0}"
        _wizard_log "cached duration for $1: [$d]"
        echo "$d"
    else
        _wizard_log "Failed to probe duration for $1"
        echo "0"
        echo "Warning: Could not detect duration for $1" >&2
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

# Generate unique temp file in /tmp (for large logs/transforms)
# Usage: get_sys_temp "prefix"
get_sys_temp() {
    mktemp "/tmp/${1:-tmp}_XXXXXX"
}
