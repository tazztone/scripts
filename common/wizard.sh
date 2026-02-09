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
        "--list" "--checklist" "--width=650" "--height=550"
        "--title=$TITLE" "--print-column=2,3" "--separator=|"
        "--column=Pick" "--column=Type" "--column=Name" "--column=Description"
    )

    # 1. Add Intents
    IFS=';' read -ra INTENTS <<< "$INTENTS_RAW"
    for item in "${INTENTS[@]}"; do
        IFS='|' read -r icon name desc <<< "$item"
        ARGS+=(FALSE "INTENT" "$icon $name" "$desc")
    done

    # 2. Add Presets Divider if they exist
    if [ -s "$PRESET_FILE" ] || [ -s "$HISTORY_FILE" ]; then
        ARGS+=(FALSE "SEP" "---" "----------------------------------")
    fi

    # 3. Add Presets
    if [ -s "$PRESET_FILE" ]; then
        while IFS='|' read -r name options; do
            [ -z "$name" ] && continue
            ARGS+=(FALSE "PRESET" "⭐ $name" "Saved Favorite")
        done < "$PRESET_FILE"
    fi

    # 4. Add History
    if [ -s "$HISTORY_FILE" ]; then
        local h_count=0
        while read -r line; do
            [ -z "$line" ] && continue
            [ $h_count -ge 8 ] && break
            # Raw options or Name
            ARGS+=(FALSE "HISTORY" "🕒 $line" "Recent Activity")
            ((h_count++))
        done < "$HISTORY_FILE"
    fi

    local RESULT
    RESULT=$(zenity "${ARGS[@]}" --text="Select fixes/edits OR load a preset below:")
    echo "$RESULT"
}
