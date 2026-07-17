#!/bin/bash
# Shared Wizard Logic for scripts-sh

# --- Logging & Security ---
LOG_DIR="$HOME/.local/share/scripts-sh"
LOG_FILE="$LOG_DIR/debug.log"
DEBUG_MODE="${DEBUG_MODE:-0}"

# Sourcing Guard
[ "${_WIZARD_SH_LOADED:-0}" -eq 1 ] && return
readonly _WIZARD_SH_LOADED=1

# --- Requirements ---
(( BASH_VERSINFO[0] >= 4 )) || { echo "Error: scripts-sh requires bash 4.0 or higher."; exit 1; }

# Helper to check for Zenity 4.0+ dependency
_wizard_check_zenity() {
    if ! command -v zenity &> /dev/null; then
        printf "Error: zenity is not installed. Please install it (sudo apt install zenity).\n" >&2
        exit 1
    fi

    local z_ver
    z_ver=$(zenity --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -n 1)
    if [ "$(echo "${z_ver:-0} < 4.0" | bc -l)" -eq 1 ]; then
        printf "Error: scripts-sh requires Zenity 4.0 or higher (found %s).\n" "${z_ver:-unknown}" >&2
        zenity --error --text="Upgrade Required: Zenity 4.0+ is needed for the checklist UI.\nFound: ${z_ver:-unknown}"
        exit 1
    fi
}

# --- Constants ---
readonly WIZARD_ROW_SIZE=4
readonly WIZARD_COL_RAWID=3 # Offset from row start (including boolean)
readonly MAX_HISTORY=10
readonly MAX_PRESETS=20

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

# show_unified_wizard "Title" "Intents..." "PresetsFile" "HistoryFile"
# Intents format: "Icon|Name|Description"
# Returns choice string (e.g. "INTENT:Speed|INTENT:Scale" or "PRESET:My Custom")
show_unified_wizard() {
    local TITLE="$1"
    local INTENTS_RAW="$2"
    local PRESET_FILE="$3"
    local HISTORY_FILE="$4"
    
    local ARGS=()
    _wizard_build_args ARGS "$TITLE" "$INTENTS_RAW" "$PRESET_FILE" "$HISTORY_FILE"

    local RESULT
    local EXIT_CODE=0
    RESULT=$(zenity "${ARGS[@]}") || EXIT_CODE=$?
    
    # Exit code handles: 0=OK, 1=Cancel/Close, >1=Error
    if [ $EXIT_CODE -gt 1 ]; then
        _wizard_log "zenity error (exit $EXIT_CODE). Check command args."
        # Don't exit here, let the parser handle potential partial returns or empty
    fi
    # Strip any trailing newlines or junk
    RESULT=$(echo -n "$RESULT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    _wizard_log "wizard raw return: [$RESULT]"

    local CLEANED
    CLEANED=$(_wizard_parse_result "$RESULT")
    
    _wizard_log "wizard clean return: [$CLEANED]"
    echo "$CLEANED"
}

_wizard_build_args() {
    local -n _ARGS=$1
    local TITLE="$2"
    local INTENTS_RAW="$3"
    local PRESET_FILE="$4"
    local HISTORY_FILE="$5"
    local IFS

    _ARGS+=(
        "--list" "--checklist" "--width" "700" "--height" "550"
        "--title" "$TITLE" "--separator" "|" "--print-column" "4"
        "--text" "Select fixes/edits OR load a preset below:"
        "--column" "" "--column" "Action" "--column" "Description" "--column" "ID"
    )

    # 1. Add Intents
    IFS=';' read -ra INTENTS_ARR <<< "$INTENTS_RAW"
    for item in "${INTENTS_ARR[@]}"; do
        local icon="" name="" desc=""
        IFS='|' read -r icon name desc <<< "$item"
        _ARGS+=(FALSE "$icon $name" "$desc" "$name")
    done

    # 2. Add Special Actions
    if [ -n "$PRESET_FILE" ]; then
        _ARGS+=(FALSE "⭐ Save as Favorite" "Save current recipe to favorites" "ACTION:SAVE")
    fi

    # 3. Add Presets Divider if they exist
    if [ -s "$PRESET_FILE" ] || [ -s "$HISTORY_FILE" ]; then
        _ARGS+=(FALSE "═══" ".................................." "═══")
    fi

    # 4. Add Presets
    if [ -s "$PRESET_FILE" ]; then
        local p_count=0
        while IFS='|' read -r p_name p_options || [ -n "$p_name" ]; do
            local p_name="${p_name:-}" p_options="${p_options:-}"
            [ -z "$p_name" ] && continue
            [ "$p_count" -ge "$MAX_PRESETS" ] && break
            _ARGS+=(FALSE "⭐ $p_name" "Saved Favorite" "PRESET:$p_name")
            ((p_count++))
        done < "$PRESET_FILE"
    fi

    # 5. Add History
    if [ -s "$HISTORY_FILE" ]; then
        local h_count=0
        while read -r line; do
            [ -z "$line" ] && continue
            [ "$h_count" -ge "$MAX_HISTORY" ] && break
            _ARGS+=(FALSE "🕒 $line" "Recent Activity" "HISTORY:$line")
            ((h_count++))
        done < "$HISTORY_FILE"
    fi

    # 6. Hide ID column
    _ARGS+=("--hide-column" "4")
}

_wizard_parse_result() {
    local RESULT="$1"
    local CLEAN_RESULT=""
    
    # 1. Terminal Booleans
    if [[ "$RESULT" =~ ^(TRUE|FALSE|true|false)$ ]]; then
        return
    fi
    
    # Simple split and deduplicate
    # This works because we now use --print-column 4, so zenity only returns IDs.
    # It also handles legacy/mock returns which are often simple piped strings.
    local -a ALL_PARTS=()
    IFS='|' read -ra ALL_PARTS <<< "$RESULT"
    
    local deduplicated=""
    declare -A SEEN
    for part in "${ALL_PARTS[@]}"; do
        # Strip whitespace
        part=$(echo "$part" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        # Normalize to uppercase for comparison
        local part_up=$(echo "$part" | tr '[:lower:]' '[:upper:]')
        
        # Filter out noise: empty, dividers, and boolean artifacts
        if [[ -n "$part" && "$part_up" != "---" && "$part_up" != "═══" && "$part_up" != "TRUE" && "$part_up" != "FALSE" ]]; then
            if [[ -z "${SEEN[$part]:-}" ]]; then
                deduplicated+="$part|"
                SEEN[$part]=1
            fi
        fi
    done
    echo "${deduplicated%|}"
}

# Consolidated State Management
STATE_CONFIG_DIR=""
STATE_PRESET_FILE=""
STATE_HISTORY_FILE=""

state_init() {
    local name="$1"
    [ -z "$name" ] && return 1
    
    local normalized
    normalized=$(echo "$name" | tr '[:upper:]' '[:lower:]')
    
    # Handle mappings
    if [ "$normalized" = "universal-toolbox" ] || [ "$normalized" = "universal" ] || [ "$normalized" = "ffmpeg" ]; then
        normalized="ffmpeg"
    elif [ "$normalized" = "lossless-operations-toolbox" ] || [ "$normalized" = "lossless-toolbox" ]; then
        normalized="lossless"
    elif [ "$normalized" = "image-magick-toolbox" ] || [ "$normalized" = "imagemagick-toolbox" ]; then
        normalized="imagemagick"
    fi

    STATE_CONFIG_DIR="$HOME/.config/scripts-sh/$normalized"
    STATE_PRESET_FILE="$STATE_CONFIG_DIR/presets.conf"
    STATE_HISTORY_FILE="$STATE_CONFIG_DIR/history.conf"
    
    # Legacy migration
    if [ "$normalized" = "lossless" ]; then
        local legacy_dir="$HOME/.config/lossless-toolbox"
        if [ -d "$legacy_dir" ] && [ ! -d "$STATE_CONFIG_DIR" ]; then
            _wizard_log "Migrating legacy lossless config from $legacy_dir to $STATE_CONFIG_DIR"
            mkdir -p "$(dirname "$STATE_CONFIG_DIR")"
            cp -r "$legacy_dir" "$STATE_CONFIG_DIR"
            mv "$legacy_dir" "${legacy_dir}.migrated" 2>/dev/null || true
        fi
    fi
    
    mkdir -p "$STATE_CONFIG_DIR"
    touch "$STATE_HISTORY_FILE"
    
    if [ ! -s "$STATE_PRESET_FILE" ]; then
        if [ "$normalized" = "ffmpeg" ]; then
            echo "Social Speed Edit|Speed 2x (Fast)|Scale 720p|Normalize (R128)|Output as H.264" > "$STATE_PRESET_FILE"
            echo "4K Archival (H.265)|Output as H.265|Clean Metadata" >> "$STATE_PRESET_FILE"
            echo "YouTube 1080p (Fast)|Scale 1080p|Normalize (R128)|Output as H.264" >> "$STATE_PRESET_FILE"
        elif [ "$normalized" = "lossless" ]; then
            echo "Quick Trim|trim|2|8" > "$STATE_PRESET_FILE"
            echo "MP4 to MKV|remux|mkv" >> "$STATE_PRESET_FILE"
            echo "Remove Audio|stream_edit|remove_audio" >> "$STATE_PRESET_FILE"
            echo "Clean Metadata|metadata|clean_metadata" >> "$STATE_PRESET_FILE"
            echo "Merge Compatible|merge" >> "$STATE_PRESET_FILE"
        fi
    fi
}

state_save_preset() {
    prompt_save_preset "$STATE_PRESET_FILE" "$1" "$2" "${3:-false}"
}

state_add_history() {
    save_to_history "$STATE_HISTORY_FILE" "$1"
}

# save_to_history "HistoryFile" "ChoiceString"
save_to_history() {
    local HISTORY_FILE="$1"
    local CHOICES="$2"
    [ -z "$CHOICES" ] && return
    
    # 1. De-duplicate: If choices match the most recent entry, do nothing.
    # Use || true to avoid set -e if file is empty
    local RECENT=""
    RECENT=$(head -n 1 "$HISTORY_FILE" 2>/dev/null || true)
    if [ "$CHOICES" != "$RECENT" ]; then
        # 2. Add to top atomically
        local tmp_file
        tmp_file=$(mktemp "${HISTORY_FILE}.XXXXXX" 2>/dev/null)
        if [ $? -ne 0 ] || [ -z "$tmp_file" ]; then
            _wizard_log "Failed to create temp file for history at ${HISTORY_FILE}"
            return 1
        fi
        echo "$CHOICES" > "$tmp_file"
        if [ -s "$HISTORY_FILE" ]; then
            head -n "$((MAX_HISTORY - 1))" "$HISTORY_FILE" >> "$tmp_file"
        fi
        mv -f "$tmp_file" "$HISTORY_FILE"
    fi
}

# prompt_save_preset "PresetFile" "Choices" "SuggestedName" "Force"
prompt_save_preset() {
    local PRESET_FILE="$1"
    local CHOICES="$2"
    local SUGGESTED_NAME="$3"
    local FORCE="${4:-false}"
    
    local SAVE_CONFIRMED=false
    if [ "$FORCE" = "true" ]; then
        SAVE_CONFIRMED=true
    else
        if zenity --question --title="Save as Favorite?" --text="Would you like to save this configuration as a permanent favorite?" --ok-label="Save" --cancel-label="Just Run Once" 2>/dev/null; then
            SAVE_CONFIRMED=true
        fi
    fi

    if [ "$SAVE_CONFIRMED" = "true" ]; then
        local PNAME=""
        PNAME=$(zenity --entry --title="Save Favorite" --text="Enter a name for this recipe:" --entry-text="$SUGGESTED_NAME" --cancel-label="Cancel" 2>/dev/null || true)
        if [ -n "$PNAME" ]; then
            PNAME="${PNAME//|/}" # Sanitize: remove pipes
            # Safer existence check using literal match with anchors
            if [ -f "$PRESET_FILE" ] && grep -q "^$(printf '%s' "$PNAME" | sed 's/[.[\*^$/]/\\&/g')|" "$PRESET_FILE"; then
                if ! zenity --question --title="Overwrite?" --text="A favorite named '$PNAME' already exists.\nOverwrite it?" --ok-label="Overwrite" --cancel-label="Cancel" 2>/dev/null; then
                    return 0
                fi
                # Safer deletion without regex pitfalls (fixed-string match)
                local tmp_preset
                tmp_preset=$(mktemp "${PRESET_FILE}.XXXXXX" 2>/dev/null)
                if [ -n "$tmp_preset" ]; then
                    grep -vF "$PNAME|" "$PRESET_FILE" > "$tmp_preset" || true
                    mv -f "$tmp_preset" "$PRESET_FILE"
                fi
            fi
            echo "$PNAME|$CHOICES" >> "$PRESET_FILE"
            zenity --notification --text="Saved as '$PNAME'!" 2>/dev/null || true
        fi
    fi
}
# parse_forms_result "RawResult" "key1 key2 key3..."
# Maps pipe-delimited zenity results to the global associative array CONFIG
parse_forms_result() {
    local raw="$1"
    shift
    local keys=("$@")
    
    # Initialize global CONFIG array
    declare -gA CONFIG=()
    
    local -a fields=()
    IFS='|' read -ra fields <<< "$raw"
    
    for i in "${!keys[@]}"; do
        local key="${keys[i]}"
        local val="${fields[i]:-}"
        # Strip "(Inactive)" if present (common in combos)
        [[ "$val" == *" (Inactive)"* ]] && val=""
        CONFIG["$key"]="$val"
    done
}

# Generate safe output filename (avoids overwrite)
# Usage: generate_safe_filename "base" "tag" "ext"
generate_safe_filename() {
    local base="$1"
    local tag="$2"
    local ext="$3"
    
    # Strip existing known tags recursively from basename ONLY
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
        [ -z "$stripped" ] && break
        [ "$stripped" == "$clean_bname" ] && break
        clean_bname="$stripped"
    done
    
    local final_base="${dir}/${clean_bname}"
    # Clean up ./ if it was added unnecessarily (e.g. if original base didn't have it)
    if [[ "$base" == "./"* ]]; then
        final_base="./${clean_bname}"
    elif [ "$dir" == "." ]; then
        final_base="$clean_bname"
    elif [ "$dir" == "/" ]; then
        final_base="/${clean_bname}"
    fi

    local out="${final_base}${tag}.${ext}"
    local ctr=1
    
    while [ -f "$out" ]; do
        out="${final_base}${tag}_v${ctr}.${ext}"
        ((ctr++))
    done
    echo "$out"
}
