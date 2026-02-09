#!/bin/bash
# Lossless Operations Toolbox v2.0
# Unified Wizard UX: Checklist -> Integrated Form

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source "$SCRIPT_DIR/common.sh"

# --- CONFIG ---
CONFIG_DIR="$HOME/.config/scripts-sh/lossless"
mkdir -p "$CONFIG_DIR"

# --- MEDIA ANALYSIS ---
get_duration() {
    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$1" | cut -d. -f1
}

# --- WIZARD logic ---

show_wizard() {
    local f="$1"
    local duration=$(get_duration "$f")

    # --- STEP 1: INTENT CHECKLIST ---
    INTENT_ARGS=(
        "--list" "--checklist" "--width=600" "--height=450"
        "--title=🔒 Lossless-Operations-Toolbox v2.0"
        "--column=Select" "--column=Operation" "--column=Description"
        TRUE "✂️ Trim" "Extract a segment without re-encoding"
        FALSE "🔄 Rotate" "Metadata rotation (0, 90, 180, 270)"
        FALSE "🔇 Audio/Video" "Remove audio or video streams"
        TRUE "📦 Container" "Change file extensions (MP4, MKV, etc)"
    )

    INTENTS=$(zenity "${INTENT_ARGS[@]}" --text="Step 1: Select all intended operations:")
    [ -z "$INTENTS" ] && exit 0

    # --- STEP 2: INTEGRATED CONFIG FORM ---
    FORM_ARGS=(
        "--forms" "--title=Configure Lossless Operations" "--width=500"
        "--text=Step 2: Configure your selected operations (Duration: ${duration}s)"
    )

    [[ "$INTENTS" == *"Trim"* ]] && {
        FORM_ARGS+=(--add-entry="Start Time (sec or HH:MM:SS)")
        FORM_ARGS+=(--add-entry="End Time (sec or HH:MM:SS)")
    }
    [[ "$INTENTS" == *"Rotate"* ]] && FORM_ARGS+=(--add-combo="Rotation Angle" --combo-values="No Change|90|180|270|0")
    [[ "$INTENTS" == *"Audio/Video"* ]] && FORM_ARGS+=(--add-combo="Stream Action" --combo-values="Keep All|Remove Audio|Remove Video")
    
    # Output Settings
    FORM_ARGS+=(--add-combo="📦 Format" --combo-values="MP4|MKV|MOV|TS")

    RESULT=$(zenity "${FORM_ARGS[@]}")
    [ -z "$RESULT" ] && exit 0
    echo "$INTENTS|$RESULT"
}

# --- HELPERS ---
execute_ffmpeg_copy() {
    local input="$1"
    local output="$2"
    local args=("$@")
    # Shift to get only the ffmpeg-specific args
    shift 2

    ffmpeg -nostdin -v error -i "$input" -c copy "$@" "$output"
}

# --- MAIN EXECUTION ---

main() {
    FILES=("$@")
    [ ${#FILES[@]} -eq 0 ] && { zenity --error --text="No files selected."; exit 1; }

    # Top-level Choice: Wizard vs Merge vs Batch
    local mode=$(zenity --list --title="Lossless Operations" --width=400 --height=350 \
        --column="Mode" --column="Description" \
        "🌟 Wizard Edit" "Stack Trim, Rotate, and Map in one pass" \
        "🔗 Merge/Join" "Concatenate compatible video files" \
        "📂 Batch Convert" "Remux many files to a different container")
    
    [ -z "$mode" ] && exit 0

    case "$mode" in
        "🌟 Wizard Edit")
            CONFIG=$(show_wizard "${FILES[0]}")
            [ -z "$CONFIG" ] && exit 0

            # Parse CONFIG
            IFS='|' read -ra PARTS <<< "$CONFIG"
            INTENTS="${PARTS[0]}"
            f_idx=1
            V_START=""; V_END=""; V_ROTATE=""; V_STREAMS=""; V_FORMAT=""

            [[ "$INTENTS" == *"Trim"* ]] && { V_START="${PARTS[$f_idx]}"; ((f_idx++)); V_END="${PARTS[$f_idx]}"; ((f_idx++)); }
            [[ "$INTENTS" == *"Rotate"* ]] && { V_ROTATE="${PARTS[$f_idx]}"; ((f_idx++)); }
            [[ "$INTENTS" == *"Audio/Video"* ]] && { V_STREAMS="${PARTS[$f_idx]}"; ((f_idx++)); }
            V_FORMAT="${PARTS[$f_idx]}"

            # Build FFmpeg Arguments
            FF_ARGS=()
            TAG=""
            OUT_EXT=$(echo "$V_FORMAT" | tr '[:upper:]' '[:lower:]')

            [ -n "$V_START" ] && { FF_ARGS+=("-ss" "$V_START"); TAG+="_trimmed"; }
            [ -n "$V_END" ] && FF_ARGS+=("-to" "$V_END")
            
            case "$V_ROTATE" in
                "90"|"180"|"270"|"0") 
                    FF_ARGS+=("-metadata:s:v:0" "rotate=$V_ROTATE")
                    TAG+="_rotated${V_ROTATE}"
                    ;;
            esac

            case "$V_STREAMS" in
                "Remove Audio") FF_ARGS+=("-an"); TAG+="_muted" ;;
                "Remove Video") FF_ARGS+=("-vn") ;;
            esac

            # Process
            (
                COUNT=0; TOTAL=${#FILES[@]}
                for f in "${FILES[@]}"; do
                    ((COUNT++))
                    PERCENT=$((COUNT * 100 / TOTAL))
                    echo "$PERCENT"; echo "# Processing: $(basename "$f")..."
                    
                    BASE="${f%.*}"
                    OUT_FILE=$(generate_safe_filename "$BASE" "$TAG" "$OUT_EXT")
                    
                    ffmpeg -nostdin -v error -i "$f" -c copy "${FF_ARGS[@]}" "$OUT_FILE" 2>/tmp/lossless_err.log
                    [ $? -ne 0 ] && echo "Error processing $(basename "$f")" >> /tmp/lossless_batch_errors.log
                done
            ) | zenity --progress --title="Lossless Wizard Processing" --auto-close
            ;;

        "🔗 Merge/Join")
            # Reuse existing merge logic (simplified here for brevity or as placeholder)
            if [ ${#FILES[@]} -lt 2 ]; then
                zenity --error --text="Select at least 2 files to merge."
                exit 1
            fi
            OUT_FILE=$(generate_safe_filename "merged" "" "${FILES[0]##*.}")
            # Create concat list
            LIST_FILE=$(mktemp)
            for f in "${FILES[@]}"; do echo "file '$f'" >> "$LIST_FILE"; done
            ffmpeg -f concat -safe 0 -i "$LIST_FILE" -c copy "$OUT_FILE"
            rm "$LIST_FILE"
            zenity --notification --text="Merged into $OUT_FILE"
            ;;

        "📂 Batch Convert")
            CONTAINER=$(zenity --list --title="Batch Remux" --column="Format" "MP4" "MKV" "MOV")
            [ -z "$CONTAINER" ] && exit 0
            OUT_EXT=$(echo "$CONTAINER" | tr '[:upper:]' '[:lower:]')
            (
                COUNT=0
                for f in "${FILES[@]}"; do
                    ((COUNT++))
                    echo $(( COUNT * 100 / ${#FILES[@]} ))
                    BASE="${f%.*}"
                    ffmpeg -i "$f" -c copy "${BASE}.${OUT_EXT}"
                done
            ) | zenity --progress --auto-close
            ;;
    esac

    [ -s /tmp/lossless_batch_errors.log ] && zenity --text-info --title="Errors" --filename=/tmp/lossless_batch_errors.log
    rm -f /tmp/lossless_batch_errors.log /tmp/lossless_err.log
}

main "$@"