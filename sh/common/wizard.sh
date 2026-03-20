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

# --- Constants ---
readonly WIZARD_ROW_SIZE=4
readonly WIZARD_COL_RAWID=3 # Offset from row start (including boolean)
readonly MAX_HISTORY=10
readonly MAX_PRESETS=20

_wizard_log() {
    if [[ "${DEBUG_MODE:-0}" == "1" ]]; then
        mkdir -p "$LOG_DIR"
        chmod 700 "$LOG_DIR" 2>/dev/null
        echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
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
    RESULT=$(zenity "${ARGS[@]}" || true)
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

    # 3. Add Presets
    if [ -s "$PRESET_FILE" ]; then
        local p_count=0
        while IFS='|' read -r name options || [ -n "$name" ]; do
            local name="${name:-}" options="${options:-}"
            [ -z "$name" ] && continue
            [ "$p_count" -ge "$MAX_PRESETS" ] && break
            _ARGS+=(FALSE "⭐ $name" "Saved Favorite" "PRESET:$name")
            ((p_count++))
        done < "$PRESET_FILE"
    fi

    # 4. Add History
    if [ -s "$HISTORY_FILE" ]; then
        local h_count=0
        while read -r line; do
            [ -z "$line" ] && continue
            [ "$h_count" -ge "$MAX_HISTORY" ] && break
            _ARGS+=(FALSE "🕒 $line" "Recent Activity" "HISTORY:$line")
            ((h_count++))
        done < "$HISTORY_FILE"
    fi

    # 4. Hide ID column
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
        tmp_file=$(mktemp "${HISTORY_FILE}.XXXXXX")
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
            if [ -f "$PRESET_FILE" ] && grep -q "^$PNAME|" "$PRESET_FILE"; then
                if ! zenity --question --title="Overwrite?" --text="A favorite named '$PNAME' already exists.\nOverwrite it?" --ok-label="Overwrite" --cancel-label="Cancel" 2>/dev/null; then
                    return 0
                fi
                # Safer deletion without regex pitfalls
                local tmp_preset=$(mktemp "${PRESET_FILE}.XXXXXX")
                grep -v "^$PNAME|" "$PRESET_FILE" > "$tmp_preset" || true
                mv -f "$tmp_preset" "$PRESET_FILE"
            fi
            echo "$PNAME|$CHOICES" >> "$PRESET_FILE"
            zenity --notification --text="Saved as '$PNAME'!" 2>/dev/null || true
        fi
    fi
}
