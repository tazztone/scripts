# Media Profiler Module for Nautilus scripts-sh
# Parses video and audio stream information in a single ffprobe pass and caches the results.

# Sourcing Guard
[ "${_MEDIA_PROFILE_SH_LOADED:-0}" -eq 1 ] && return
readonly _MEDIA_PROFILE_SH_LOADED=1

# Global cache variables
_PROBED_FILE=""
declare -gA PROBED_INFO=()

# Probe media file and populate PROBED_INFO cache
# Usage: probe_media "filepath"
probe_media() {
    local file="$1"
    [ -z "$file" ] && return 1
    
    # Check if cache is already loaded for this file
    if [ "$_PROBED_FILE" = "$file" ]; then
        return 0
    fi
    
    # Reset cache state
    _PROBED_FILE="$file"
    PROBED_INFO=()
    PROBED_INFO[has_audio]="false"
    PROBED_INFO[has_video]="false"
    PROBED_INFO[video_codec]=""
    PROBED_INFO[video_profile]=""
    PROBED_INFO[video_level]=""
    PROBED_INFO[video_pix_fmt]=""
    PROBED_INFO[width]=""
    PROBED_INFO[height]=""
    PROBED_INFO[video_fps]=""
    PROBED_INFO[video_rotation]=""
    PROBED_INFO[audio_codec]=""
    PROBED_INFO[audio_sample_rate]=""
    PROBED_INFO[audio_channels]=""
    PROBED_INFO[audio_channel_layout]=""
    PROBED_INFO[duration]="0"
    
    # Run ffprobe once to get all stream properties
    local raw_data
    raw_data=$(ffprobe -v error -show_format -show_streams -of flat "$file" 2>/dev/null) || {
        _PROBED_FILE=""
        return 1
    }
    
    # Stream-specific variables to compile index values
    local -a stream_types=()
    local -a stream_codecs=()
    local -a stream_profiles=()
    local -a stream_levels=()
    local -a stream_pix_fmts=()
    local -a stream_widths=()
    local -a stream_heights=()
    local -a stream_fps=()
    local -a stream_rotations=()
    local -a stream_sample_rates=()
    local -a stream_channels=()
    local -a stream_layouts=()

    # Parse ffprobe flat output
    while IFS= read -r line; do
        if [[ "$line" =~ ^streams\.stream\.([0-9]+)\.codec_type=\"([a-z]+)\" ]]; then
            local idx="${BASH_REMATCH[1]}"
            local type="${BASH_REMATCH[2]}"
            stream_types[idx]="$type"
            if [ "$type" = "audio" ]; then
                PROBED_INFO[has_audio]="true"
            elif [ "$type" = "video" ]; then
                PROBED_INFO[has_video]="true"
            fi
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.codec_name=\"([^\"]+)\" ]]; then
            stream_codecs[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.profile=\"([^\"]+)\" ]]; then
            stream_profiles[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.level=([0-9\-]+) ]]; then
            stream_levels[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.pix_fmt=\"([^\"]+)\" ]]; then
            stream_pix_fmts[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.width=([0-9]+) ]]; then
            stream_widths[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.height=([0-9]+) ]]; then
            stream_heights[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.r_frame_rate=\"([^\"]+)\" ]]; then
            stream_fps[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.sample_rate=\"([^\"]+)\" ]]; then
            stream_sample_rates[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.channels=([0-9]+) ]]; then
            stream_channels[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.channel_layout=\"([^\"]+)\" ]]; then
            stream_layouts[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^format\.duration=\"([0-9\.]+)\" ]]; then
            PROBED_INFO[duration]="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^streams\.stream\.([0-9]+)\.tags\.rotate=\"([0-9\-]+)\" ]]; then
            stream_rotations[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
        fi
    done <<< "$raw_data"

    # Map the first video and audio stream properties into cached keys
    local v_idx="" a_idx=""
    for idx in "${!stream_types[@]}"; do
        if [ "${stream_types[idx]}" = "video" ] && [ -z "$v_idx" ]; then
            v_idx="$idx"
        elif [ "${stream_types[idx]}" = "audio" ] && [ -z "$a_idx" ]; then
            a_idx="$idx"
        fi
    done

    if [ -n "$v_idx" ]; then
        PROBED_INFO[video_codec]="${stream_codecs[v_idx]:-}"
        PROBED_INFO[video_profile]="${stream_profiles[v_idx]:-}"
        PROBED_INFO[video_level]="${stream_levels[v_idx]:-}"
        PROBED_INFO[video_pix_fmt]="${stream_pix_fmts[v_idx]:-}"
        PROBED_INFO[width]="${stream_widths[v_idx]:-}"
        PROBED_INFO[height]="${stream_heights[v_idx]:-}"
        PROBED_INFO[video_fps]="${stream_fps[v_idx]:-}"
        PROBED_INFO[video_rotation]="${stream_rotations[v_idx]:-}"
    fi

    if [ -n "$a_idx" ]; then
        PROBED_INFO[audio_codec]="${stream_codecs[a_idx]:-}"
        PROBED_INFO[audio_sample_rate]="${stream_sample_rates[a_idx]:-}"
        PROBED_INFO[audio_channels]="${stream_channels[a_idx]:-}"
        PROBED_INFO[audio_channel_layout]="${stream_layouts[a_idx]:-}"
    fi

    return 0
}

# --- Profiler Query Helpers ---
has_audio() { [ "${PROBED_INFO[has_audio]:-false}" = "true" ]; }
has_video() { [ "${PROBED_INFO[has_video]:-false}" = "true" ]; }
get_video_codec() { echo "${PROBED_INFO[video_codec]:-}"; }
get_video_profile() { echo "${PROBED_INFO[video_profile]:-}"; }
get_video_level() { echo "${PROBED_INFO[video_level]:-}"; }
get_video_pix_fmt() { echo "${PROBED_INFO[video_pix_fmt]:-}"; }
get_width() { echo "${PROBED_INFO[width]:-}"; }
get_height() { echo "${PROBED_INFO[height]:-}"; }
get_video_fps() { echo "${PROBED_INFO[video_fps]:-}"; }
get_video_rotation() { echo "${PROBED_INFO[video_rotation]:-}"; }
get_audio_codec() { echo "${PROBED_INFO[audio_codec]:-}"; }
get_audio_sample_rate() { echo "${PROBED_INFO[audio_sample_rate]:-}"; }
get_audio_channels() { echo "${PROBED_INFO[audio_channels]:-}"; }
get_audio_channel_layout() { echo "${PROBED_INFO[audio_channel_layout]:-}"; }
