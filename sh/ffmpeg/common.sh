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

# --- GPU PROBE (Run once at startup) ---
GPU_CACHE="/tmp/scripts-sh-gpu-cache"
probe_gpu() {
    # Skip if fresh cache exists (<24h)
    if [ -f "$GPU_CACHE" ] && [ $(( $(date +%s) - $(stat -c %Y "$GPU_CACHE") )) -lt 86400 ]; then
        return 0
    fi
    echo "" > "$GPU_CACHE"
    
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
    
    # Check if it's hh:mm:ss format
    if [[ "$time_input" =~ ^([0-9]{1,2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?$ ]]; then
        local hours=${BASH_REMATCH[1]}
        local minutes=${BASH_REMATCH[2]}
        local seconds=${BASH_REMATCH[3]}
        local fraction=${BASH_REMATCH[4]:-}
        
        # Convert to seconds
        local total_seconds=$((hours * 3600 + minutes * 60 + seconds))
        echo "${total_seconds}${fraction}"
        return 0
    fi
    
    # Check if it's mm:ss format
    if [[ "$time_input" =~ ^([0-9]{1,2}):([0-9]{2})(\.[0-9]+)?$ ]]; then
        local minutes=${BASH_REMATCH[1]}
        local seconds=${BASH_REMATCH[2]}
        local fraction=${BASH_REMATCH[3]:-}
        
        # Convert to seconds
        local total_seconds=$((minutes * 60 + seconds))
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
    local out="${base}${tag}.${ext}"
    local ctr=1
    
    while [ -f "$out" ]; do
        out="${base}${tag}_v${ctr}.${ext}"
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
    mktemp -u "/tmp/${1:-tmp}_XXXXXX"
}
