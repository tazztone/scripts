#!/bin/bash
# Shared Wizard Logic for scripts-sh

# show_unified_wizard "Title" "Intents..." "PresetsFile" "HistoryFile"
# Intents format: "Icon|Name|Description"
# Returns choice string (e.g. "INTENT:Speed|INTENT:Scale" or "PRESET:My Custom")
show_unified_wizard() {
    local TITLE="$1"
    local INTENTS_RAW="$2"
    local PRESET_FILE="$3"
    local HISTORY_FILE="$4"
    local IFS
    
    local ARGS=(
        "--list" "--checklist" "--width=700" "--height=550"
        "--title=$TITLE" "--separator=|" "--print-column=ALL" "--hide-column=2,5"
        "--text=Select fixes/edits OR load a preset below:"
        "--column=Pick" "--column=ID" "--column=Display" "--column=Description" "--column=RawID"
        "--"
    )

    # 1. Add Intents
    IFS=';' read -ra INTENTS_ARR <<< "$INTENTS_RAW"
    for item in "${INTENTS_ARR[@]}"; do
        IFS='|' read -r icon name desc <<< "$item"
        # 1:Pick, 2:ID(name), 3:Display(icon+name), 4:Description, 5:RawID(name)
        ARGS+=(FALSE "$name" "$icon $name" "$desc" "$name")
    done

    # 2. Add Presets Divider if they exist
    if [ -s "$PRESET_FILE" ] || [ -s "$HISTORY_FILE" ]; then
        ARGS+=(FALSE "---" "---" ".................................." "---")
    fi

    # 3. Add Presets
    if [ -s "$PRESET_FILE" ]; then
        while IFS='|' read -r name options; do
            [ -z "$name" ] && continue
            ARGS+=(FALSE "PRESET:$name" "⭐ $name" "Saved Favorite" "PRESET:$name")
        done < "$PRESET_FILE"
    fi

    # 4. Add History
    if [ -s "$HISTORY_FILE" ]; then
        local h_count=0
        while read -r line; do
            [ -z "$line" ] && continue
            [ $h_count -ge 8 ] && break
            ARGS+=(FALSE "HISTORY:$line" "🕒 $line" "Recent Activity" "HISTORY:$line")
            ((h_count++))
        done < "$HISTORY_FILE"
    fi

    local RESULT
    RESULT=$(zenity "${ARGS[@]}")
    # Strip any trailing newlines or junk
    RESULT=$(echo -n "$RESULT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    echo "[DEBUG] wizard raw return: [$RESULT]" >> /tmp/scripts_debug.log

    echo "[DEBUG] wizard raw return: [$RESULT]" >> /tmp/scripts_debug.log

    # --- Bulletproof Result Parser (Zenity 4.x compliant) ---
    local CLEAN_RESULT=""
    if [[ "$RESULT" == *"|"* ]]; then
        # Explicitly set IFS and read into array
        local -a ALL_PARTS
        IFS='|' read -ra ALL_PARTS <<< "$RESULT"
        
        # Check if the FIRST element is a known Zenity 4 marker (TRUE/FALSE)
        local FIRST_UP=$(echo "${ALL_PARTS[0]}" | tr '[:lower:]' '[:upper:]')
        if [[ "$FIRST_UP" == "TRUE" || "$FIRST_UP" == "FALSE" ]]; then
            # 1. First pass: Handle standard checkbox selections
            for (( i=0; i<${#ALL_PARTS[@]}; i++ )); do
                local ITEM="${ALL_PARTS[i]}"
                # Case-insensitive check for TRUE or FALSE
                local UP_ITEM=$(echo "$ITEM" | tr '[:lower:]' '[:upper:]')
                
                if [[ "$UP_ITEM" == "TRUE" ]]; then
                    local VAL="${ALL_PARTS[i+1]}"
                    if [[ -n "$VAL" && "$VAL" != "---" ]]; then
                        CLEAN_RESULT+="$VAL|"
                        # Skip the ID we just took to avoid false booleans if ID is "TRUE" (unlikely)
                        ((i++))
                    fi
                fi
            done
            
            # Fallback: If no explicit TRUE found, check for the "Last Interacted Row" (FALSE prefix)
            # This occurs on double-clicks or Enter key in Zenity 4.x
            if [[ -z "$CLEAN_RESULT" ]]; then
                for (( i=0; i<${#ALL_PARTS[@]}; i++ )); do
                    local ITEM="${ALL_PARTS[i]}"
                    local UP_ITEM=$(echo "$ITEM" | tr '[:lower:]' '[:upper:]')
                    if [[ "$UP_ITEM" == "FALSE" ]]; then
                        local VAL="${ALL_PARTS[i+1]}"
                        if [[ -n "$VAL" && "$VAL" != "---" ]]; then
                            CLEAN_RESULT+="$VAL|"
                            break # Only take the first one for implicit selection
                        fi
                    fi
                done
            fi
            RESULT="${CLEAN_RESULT%|}"
        else
            # Not a Zenity 4 marker? It's likely a Zenity 3 multi-select return (item1|item2)
            # We keep it as is.
            :
        fi
    elif [[ "$RESULT" =~ ^(TRUE|FALSE|true|false)$ ]]; then
        # Discard pure boolean returns with no data
        RESULT=""
    fi

    echo "[DEBUG] wizard clean return: [$RESULT]" >> /tmp/scripts_debug.log
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

# prompt_save_preset "PresetFile" "Choices" "SuggestedName"
prompt_save_preset() {
    local PRESET_FILE="$1"
    local CHOICES="$2"
    local SUGGESTED_NAME="$3"
    
    if zenity --question --title="Save as Favorite?" --text="Would you like to save this configuration as a permanent favorite?" --ok-label="Save" --cancel-label="Just Run Once"; then
        local PNAME
        PNAME=$(zenity --entry --title="Save Favorite" --text="Enter a name for this recipe:" --entry-text="$SUGGESTED_NAME")
        if [ -n "$PNAME" ]; then
            echo "$PNAME|$CHOICES" >> "$PRESET_FILE"
            zenity --notification --text="Saved as '$PNAME'!"
        fi
    fi
}
