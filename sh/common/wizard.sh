# Shared Wizard Logic for scripts-sh

# --- Logging & Security ---
LOG_DIR="$HOME/.local/share/scripts-sh"
LOG_FILE="$LOG_DIR/debug.log"
DEBUG_MODE="${DEBUG_MODE:-0}"

# --- Constants ---
readonly WIZARD_ROW_SIZE=5
readonly WIZARD_COL_RAWID=4 # Offset from row start (including boolean)
readonly MAX_HISTORY=8
readonly MAX_PRESETS=20

_wizard_log() {
    if [[ "$DEBUG_MODE" == "1" ]]; then
        mkdir -p "$LOG_DIR"
        chmod 700 "$LOG_DIR" 2>/dev/null
        echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
    fi
}

# show_unified_wizard "Title" "Intents..." "PresetsFile" "HistoryFile"
# Intents format: "Icon|Name|Description"
# Returns choice string (e.g. "INTENT:Speed|INTENT:Scale" or "PRESET:My Custom")
# show_unified_wizard "Title" "Intents..." "PresetsFile" "HistoryFile"
show_unified_wizard() {
    local TITLE="$1"
    local INTENTS_RAW="$2"
    local PRESET_FILE="$3"
    local HISTORY_FILE="$4"
    
    local ARGS=()
    _wizard_build_args ARGS "$TITLE" "$INTENTS_RAW" "$PRESET_FILE" "$HISTORY_FILE"

    local RESULT
    RESULT=$(zenity "${ARGS[@]}")
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
        "--title" "$TITLE" "--separator" "|" "--print-column" "ALL"
        "--text" "Select fixes/edits OR load a preset below:"
        "--column" "" "--column" "Action" "--column" "Description" "--column" "ID" "--column" "RawID"
    )

    # 1. Add Intents
    IFS=';' read -ra INTENTS_ARR <<< "$INTENTS_RAW"
    for item in "${INTENTS_ARR[@]}"; do
        IFS='|' read -r icon name desc <<< "$item"
        _ARGS+=(FALSE "$icon $name" "$desc" "$name" "$name")
    done

    # 2. Add Special Actions
    if [ -n "$PRESET_FILE" ]; then
        _ARGS+=(FALSE "⭐ Save as Favorite" "Save current recipe to favorites" "ACTION:SAVE" "ACTION:SAVE")
    fi

    # 3. Add Presets Divider if they exist
    if [ -s "$PRESET_FILE" ] || [ -s "$HISTORY_FILE" ]; then
        _ARGS+=(FALSE "═══" ".................................." "═══" "═══")
    fi

    # 3. Add Presets
    if [ -s "$PRESET_FILE" ]; then
        local p_count=0
        while IFS='|' read -r name options; do
            [ -z "$name" ] && continue
            [ "$p_count" -ge "$MAX_PRESETS" ] && break
            _ARGS+=(FALSE "⭐ $name" "Saved Favorite" "PRESET:$name" "PRESET:$name")
            ((p_count++))
        done < "$PRESET_FILE"
    fi

    # 4. Add History
    if [ -s "$HISTORY_FILE" ]; then
        local h_count=0
        while read -r line; do
            [ -z "$line" ] && continue
            [ "$h_count" -ge "$MAX_HISTORY" ] && break
            _ARGS+=(FALSE "🕒 $line" "Recent Activity" "HISTORY:$line" "HISTORY:$line")
            ((h_count++))
        done < "$HISTORY_FILE"
    fi

    # 5. Hide columns (must come after headers, safer at the end)
    _ARGS+=("--hide-column" "4" "--hide-column" "5")
}

_wizard_parse_result() {
    local RESULT="$1"
    local CLEAN_RESULT=""

    if [[ "$RESULT" == *"|"* ]]; then
        local -a ALL_PARTS
        IFS='|' read -ra ALL_PARTS <<< "$RESULT"
        
        local FIRST_UP=$(echo "${ALL_PARTS[0]}" | tr '[:lower:]' '[:upper:]')
        if [[ "$FIRST_UP" == "TRUE" || "$FIRST_UP" == "FALSE" ]]; then
            for (( i=0; i<${#ALL_PARTS[@]}; i++ )); do
                local ITEM="${ALL_PARTS[i]}"
                local UP_ITEM=$(echo "$ITEM" | tr '[:lower:]' '[:upper:]')
                
                if [[ "$UP_ITEM" == "TRUE" ]]; then
                    local VAL="${ALL_PARTS[i+WIZARD_COL_RAWID]}"
                    if [[ -n "$VAL" && "$VAL" != "---" && "$VAL" != "═══" ]]; then
                        CLEAN_RESULT+="$VAL|"
                        ((i+=WIZARD_ROW_SIZE-1))
                    fi
                fi
            done
            
            if [[ -z "$CLEAN_RESULT" ]]; then
                for (( i=0; i<${#ALL_PARTS[@]}; i++ )); do
                    local UP_ITEM=$(echo "${ALL_PARTS[i]}" | tr '[:lower:]' '[:upper:]')
                    if [[ "$UP_ITEM" == "FALSE" ]]; then
                        local VAL="${ALL_PARTS[i+WIZARD_COL_RAWID]}"
                        if [[ -n "$VAL" && "$VAL" != "---" && "$VAL" != "═══" ]]; then
                            CLEAN_RESULT+="$VAL|"
                            break
                        fi
                    fi
                done
            fi
            RESULT="${CLEAN_RESULT%|}"
        fi
    elif [[ "$RESULT" =~ ^(TRUE|FALSE|true|false)$ ]]; then
        RESULT=""
    fi
    echo "$RESULT"
}

# save_to_history "HistoryFile" "ChoiceString"
save_to_history() {
    local HISTORY_FILE="$1"
    local CHOICES="$2"
    [ -z "$CHOICES" ] && return
    
    # 1. De-duplicate: If choices match the most recent entry, do nothing.
    local RECENT=$(head -n 1 "$HISTORY_FILE" 2>/dev/null)
    if [ "$CHOICES" != "$RECENT" ]; then
        # 2. Add to top
        echo "$CHOICES" | cat - "$HISTORY_FILE" > "${HISTORY_FILE}.tmp"
        # 3. Keep last 15
        head -n 15 "${HISTORY_FILE}.tmp" > "$HISTORY_FILE"
        rm "${HISTORY_FILE}.tmp"
    fi
}

# prompt_save_preset "PresetFile" "Choices" "SuggestedName" "Force"
prompt_save_preset() {
    local PRESET_FILE="$1"
    local CHOICES="$2"
    local SUGGESTED_NAME="$3"
    local FORCE="${4:-false}"
    
    if [ "$FORCE" = "true" ] || zenity --question --title="Save as Favorite?" --text="Would you like to save this configuration as a permanent favorite?" --ok-label="Save" --cancel-label="Just Run Once"; then
        local PNAME
        PNAME=$(zenity --entry --title="Save Favorite" --text="Enter a name for this recipe:" --entry-text="$SUGGESTED_NAME")
        if [ -n "$PNAME" ]; then
            PNAME="${PNAME//|/}" # Sanitize: remove pipes
            echo "$PNAME|$CHOICES" >> "$PRESET_FILE"
            zenity --notification --text="Saved as '$PNAME'!"
        fi
    fi
}
