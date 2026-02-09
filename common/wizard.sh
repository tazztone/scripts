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
    
    local ARGS=(
        "--list" "--checklist" "--width=700" "--height=550"
        "--title=$TITLE" "--separator=|"
        "--text=Select fixes/edits OR load a preset below:"
        "--column=Pick" "--column=Action" "--column=Description"
        "--"
    )

    # 1. Add Intents
    IFS=';' read -ra INTENTS <<< "$INTENTS_RAW"
    for item in "${INTENTS[@]}"; do
        IFS='|' read -r icon name desc <<< "$item"
        ARGS+=(FALSE "$icon $name" "$desc")
    done

    # 2. Add Presets Divider if they exist
    if [ -s "$PRESET_FILE" ] || [ -s "$HISTORY_FILE" ]; then
        ARGS+=(FALSE "---" "..................................")
    fi

    # 3. Add Presets
    if [ -s "$PRESET_FILE" ]; then
        while IFS='|' read -r name options; do
            [ -z "$name" ] && continue
            ARGS+=(FALSE "⭐ $name" "Saved Favorite")
        done < "$PRESET_FILE"
    fi

    # 4. Add History
    if [ -s "$HISTORY_FILE" ]; then
        local h_count=0
        while read -r line; do
            [ -z "$line" ] && continue
            [ $h_count -ge 8 ] && break
            # Raw options or Name
            ARGS+=(FALSE "🕒 $line" "Recent Activity")
            ((h_count++))
        done < "$HISTORY_FILE"
    fi

    local RESULT
    RESULT=$(zenity "${ARGS[@]}")
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
