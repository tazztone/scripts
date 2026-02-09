#!/bin/bash
# 🖼️ Image-Magick-Toolbox v1.0
# Comprehensive image manipulation via Zenity and ImageMagick

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source "$SCRIPT_DIR/common.sh"

# --- CONFIG ---
CONFIG_DIR="$HOME/.config/scripts-sh/imagemagick"
PRESET_FILE="$CONFIG_DIR/presets.conf"
HISTORY_FILE="$CONFIG_DIR/history.conf"
mkdir -p "$CONFIG_DIR"
touch "$PRESET_FILE" "$HISTORY_FILE"

# --- LAUNCHPAD (MAIN MENU) ---
while true; do
    LAUNCH_ARGS=(
        "--list" "--width=600" "--height=500"
        "--title=🖼️ Image-Magick-Toolbox Launchpad" "--print-column=2"
        "--column=Type" "--column=Name" "--column=Description"
        "➕" "New Custom Edit" "Build a selection from scratch"
    )

    # Load Presets
    if [ -s "$PRESET_FILE" ]; then
        while IFS='|' read -r name options; do
            [ -z "$name" ] && continue
            LAUNCH_ARGS+=("⭐" "$name" "Saved Favorite")
        done < "$PRESET_FILE"
    fi

    # Load History
    if [ -s "$HISTORY_FILE" ]; then
        while read -r line; do
            [ -z "$line" ] && continue
            LAUNCH_ARGS+=("🕒" "$line" "Recent History")
        done < "$HISTORY_FILE"
    fi

    PICKED=$(zenity "${LAUNCH_ARGS[@]}" --text="Select a starting point:")
    if [ -z "$PICKED" ]; then exit 0; fi

    if [ "$PICKED" == "New Custom Edit" ]; then
        # --- STEP 2: INTENT CHECKLIST ---
        ZENITY_INTENTS=(
            "--list" "--checklist" "--width=600" "--height=500"
            "--title=Wizard Step 2: What do you want to fix?" "--print-column=2"
            "--column=Pick" "--column=Action" "--column=Description"
            FALSE "📐 Scale / Resize" "Change dimensions (1080p, 50%, etc)"
            FALSE "📦 Format Converter" "Convert to JPG, PNG, WEBP, PDF"
            FALSE "🚀 Optimization" "Web Ready, Strip Metadata, Compress"
            FALSE "🖼️ Canvas & Crop" "Montage Grid, Square Crop, Border"
            FALSE "🏷️ Branding" "Add Watermark or Text"
            FALSE "🔄 Effects" "Rotate, Flip, Greyscale"
        )
        
        INTENTS=$(zenity "${ZENITY_INTENTS[@]}" --separator="|")
        [ -z "$INTENTS" ] && continue

        # --- STEP 3: CONFIGURATION FORM ---
        ZENITY_FORMS=(
            "--forms" "--title=Wizard Step 3: Configure & Run"
            "--width=500" "--separator=|" 
            "--text=Finalize your image recipe:"
        )

        # 1. SCALE
        VAL_ires=" (Inactive)"
        [[ "$INTENTS" == *"Scale"* ]] && VAL_ires="1920x (HD)"
        ZENITY_FORMS+=( "--add-combo=📐 Resolution" "--combo-values=$VAL_ires|3840x (4K)|1280x (720p)|640x|50%|Custom" )
        ZENITY_FORMS+=( "--add-entry=✍️ Custom Geometry (e.g. 800x600)" )

        # 2. FORMAT
        VAL_ifmt=" (Inactive)"
        [[ "$INTENTS" == *"Format"* ]] && VAL_ifmt="JPG"
        ZENITY_FORMS+=( "--add-combo=📦 Output Format" "--combo-values=$VAL_ifmt|PNG|WEBP|TIFF|PDF" )

        # 3. OPTIMIZATION
        VAL_iopt=" (Inactive)"
        [[ "$INTENTS" == *"Optimization"* ]] && VAL_iopt="Web Ready (Quality 85 + Strip)"
        ZENITY_FORMS+=( "--add-combo=🚀 Optimize Strategy" "--combo-values=$VAL_iopt|Max Compression|Archive (Lossless+Keep Metadata)" )

        # 4. EFFECTS & BRANDING
        VAL_ieff=" (Inactive)"
        [[ "$INTENTS" == *"Effects"* ]] && VAL_ieff="No Change"
        ZENITY_FORMS+=( "--add-combo=🔄 Effects" "--combo-values=$VAL_ieff|Rotate 90 CW|Rotate 90 CCW|Flip Horizontal|Black & White" )

        # 5. ADVANCED TOOLS (Montage / PDF / Watermark)
        VAL_imnt=" (Inactive)"
        [[ "$INTENTS" == *"Canvas"* ]] && VAL_imnt="2x Grid"
        ZENITY_FORMS+=( "--add-combo=🖼️ Canvas/Montage" "--combo-values=$VAL_imnt|3x Grid|Contact Sheet|Single Row|Single Column" )
        
        VAL_iwm=" (Inactive)"
        [[ "$INTENTS" == *"Branding"* ]] && VAL_iwm="Watermark PNG"
        ZENITY_FORMS+=( "--add-combo=🏷️ Branding" "--combo-values=$VAL_iwm|Text Annotation" )
        ZENITY_FORMS+=( "--add-entry=✍️ Text/Watermark Path (or 'watermark.png')" )

        CONFIG_RESULT=$(zenity "${ZENITY_FORMS[@]}")
        [ -z "$CONFIG_RESULT" ] && continue 

        # --- EXTRACT CONFIG ---
        IFS='|' read -ra VALS <<< "$CONFIG_RESULT"
        CHOICES=""
        
        [[ "${VALS[0]}" != *"Inactive"* ]] && CHOICES+="Scale: ${VALS[0]}|"
        [ -n "${VALS[1]}" ] && CHOICES+="CustomGeometry: ${VALS[1]}|"
        [[ "${VALS[2]}" != *"Inactive"* ]] && CHOICES+="Format: ${VALS[2]}|"
        [[ "${VALS[3]}" != *"Inactive"* ]] && CHOICES+="Optimize: ${VALS[3]}|"
        [[ "${VALS[4]}" != *"Inactive"* && "${VALS[4]}" != "No Change" ]] && CHOICES+="Effect: ${VALS[4]}|"
        [[ "${VALS[5]}" != *"Inactive"* ]] && CHOICES+="Canvas: ${VALS[5]}|"
        [[ "${VALS[6]}" != *"Inactive"* ]] && CHOICES+="Branding: ${VALS[6]}|"
        [ -n "${VALS[7]}" ] && CHOICES+="BrandingPayload: ${VALS[7]}|"

        CHOICES=$(echo "$CHOICES" | sed 's/|$//')
        break

    else
        # Handle Favs/History
        PRESET_MATCH=$(grep "^$PICKED|" "$PRESET_FILE" | cut -d'|' -f2-)
        if [ -n "$PRESET_MATCH" ]; then
            CHOICES="$PRESET_MATCH"
        else
            CHOICES="$PICKED"
        fi
        break
    fi
done

# --- PROCESSING LOGIC (PHASE 2) ---

# Save to History
if [ -n "$CHOICES" ]; then
    RECENT=$(head -n 1 "$HISTORY_FILE")
    if [ "$CHOICES" != "$RECENT" ]; then
        echo "$CHOICES" | cat - "$HISTORY_FILE" | head -n 15 > "${HISTORY_FILE}.tmp" && mv "${HISTORY_FILE}.tmp" "$HISTORY_FILE"
    fi
fi

# Prepare ImageMagick Arguments
IM_ARGS=()
OUT_EXT=""
TAG=""
DO_MONTAGE=false
DO_TEXT_ANNOTATION=false

IFS='|' read -ra CHOICE_ARR <<< "$CHOICES"
for opt in "${CHOICE_ARR[@]}"; do
    case "$opt" in
        Scale:*)
            VAL=$(echo "$opt" | cut -d' ' -f2)
            case "$VAL" in
                "1920x") IM_ARGS+=("-resize" "1920x"); TAG="${TAG}_1920p" ;;
                "3840x") IM_ARGS+=("-resize" "3840x"); TAG="${TAG}_4k" ;;
                "1280x") IM_ARGS+=("-resize" "1280x"); TAG="${TAG}_720p" ;;
                "640x")  IM_ARGS+=("-resize" "640x"); TAG="${TAG}_640p" ;;
                "50%")   IM_ARGS+=("-resize" "50%"); TAG="${TAG}_half" ;;
            esac
            ;;
        CustomGeometry:*)
            VAL=$(echo "$opt" | cut -d' ' -f2)
            IM_ARGS+=("-resize" "$VAL"); TAG="${TAG}_${VAL}"
            ;;
        Format:*)
            OUT_EXT=$(echo "$opt" | cut -d' ' -f2 | tr '[:upper:]' '[:lower:]')
            ;;
        Optimize:*)
            VAL=$(echo "$opt" | cut -d':' -f2)
            if [[ "$VAL" == *"Web Ready"* ]]; then
                IM_ARGS+=("-quality" "85" "-strip"); TAG="${TAG}_web"
            elif [[ "$VAL" == *"Max Compression"* ]]; then
                IM_ARGS+=("-quality" "60" "-strip"); TAG="${TAG}_min"
            fi
            ;;
        Effect:*)
            VAL=$(echo "$opt" | cut -d':' -f2)
            case "$VAL" in
                *"Rotate 90 CW"*)  IM_ARGS+=("-rotate" "90"); TAG="${TAG}_90cw" ;;
                *"Rotate 90 CCW"*) IM_ARGS+=("-rotate" "-90"); TAG="${TAG}_90ccw" ;;
                *"Flip Horizontal"*) IM_ARGS+=("-flop"); TAG="${TAG}_flop" ;;
                *"Black & White"*) IM_ARGS+=("-colorspace" "gray"); TAG="${TAG}_bw" ;;
            esac
            ;;
        Branding:*)
            VAL=$(echo "$opt" | cut -d':' -f2)
            if [[ "$VAL" == *"Text Annotation"* ]]; then
                DO_TEXT_ANNOTATION=true
            fi
            ;;
        BrandingPayload:*)
            BRAND_PAYLOAD=$(echo "$opt" | cut -d':' -f2 | sed 's/^ //')
            if [ "$DO_TEXT_ANNOTATION" = true ]; then
                IM_ARGS+=("-gravity" "South" "-pointsize" "24" "-annotate" "+0+20" "$BRAND_PAYLOAD")
                TAG="${TAG}_text"
            fi
            ;;
        Canvas:*)
            VAL=$(echo "$opt" | cut -d':' -f2)
            case "$VAL" in
               *"2x Grid"*) IM_ARGS+=("-tile" "2x"); TAG="${TAG}_grid2x" ;;
               *"3x Grid"*) IM_ARGS+=("-tile" "3x"); TAG="${TAG}_grid3x" ;;
            esac
            DO_MONTAGE=true
            ;;
    esac
done

# --- SPECIAL MODE: MONTAGE ---
if [ "$DO_MONTAGE" = true ]; then
    OUT_FILE=$(generate_safe_filename "montage" "$TAG" "${OUT_EXT:-jpg}")
    (
    echo "10"
    echo "# Creating Montage..."
    $IM_MONTAGE "$@" "${IM_ARGS[@]}" "$OUT_FILE"
    ) | zenity --progress --title="Creating Montage" --auto-close --pulsate
    zenity --notification --text="Montage Finished: $OUT_FILE"
    exit 0
fi

# --- SPECIAL MODE: PDF MERGE ---
if [[ "$OUT_EXT" == "pdf" && $# -gt 1 ]]; then
    OUT_FILE=$(generate_safe_filename "merged_images" "$TAG" "pdf")
    (
    echo "10"
    echo "# Merging into PDF..."
    $IM_EXE "$@" "${IM_ARGS[@]}" "$OUT_FILE"
    ) | zenity --progress --title="Creating PDF" --auto-close --pulsate
    zenity --notification --text="PDF Created: $OUT_FILE"
    exit 0
fi

# --- EXECUTION LOOP (PARALLEL) ---
(
TOTAL=$#
COUNT=0
MAX_JOBS=$(nproc)
[ "$MAX_JOBS" -gt 4 ] && MAX_JOBS=4 # Cap at 4 for UI responsiveness

for f in "$@"; do
    ((COUNT++))
    PERCENT=$((COUNT * 100 / TOTAL))
    echo "$PERCENT"
    echo "# Processing ($COUNT/$TOTAL): $(basename "$f")..."
    
    BASE="${f%.*}"
    IN_EXT="${f##*.}"
    [ -z "$OUT_EXT" ] && CURRENT_EXT="$IN_EXT" || CURRENT_EXT="$OUT_EXT"
    
    OUT_FILE=$(generate_safe_filename "$BASE" "$TAG" "$CURRENT_EXT")
    
    {
        # 0. PDF Extraction Special handling
        if [[ "$IN_EXT" == "pdf" && "$OUT_EXT" != "pdf" ]]; then
            $IM_EXE -density 300 "$f" "${IM_ARGS[@]}" "${BASE}${TAG}-%d.${OUT_EXT:-jpg}"
        # 1. Watermark logic
        elif [[ "$CHOICES" == *"Branding: Watermark PNG"* ]]; then
            WM_PATH="${BRAND_PAYLOAD:-watermark.png}"
            [ ! -f "$WM_PATH" ] && [ -f "$SCRIPT_DIR/$WM_PATH" ] && WM_PATH="$SCRIPT_DIR/$WM_PATH"
            if [ -f "$WM_PATH" ]; then
                $IM_EXE "$f" "${IM_ARGS[@]}" miff:- | $IM_COMPOSITE -dissolve 30 -gravity Southeast "$WM_PATH" - "$OUT_FILE"
            else
                $IM_EXE "$f" "${IM_ARGS[@]}" "$OUT_FILE"
            fi
        else
            $IM_EXE "$f" "${IM_ARGS[@]}" "$OUT_FILE" 2>/tmp/im_error.log
        fi
    } &
    
    # Manage job queue
    if [[ $(jobs -r | wc -l) -ge $MAX_JOBS ]]; then
        wait -n
    fi
done
wait
) | zenity --progress --title="Image-Magick-Toolbox" --auto-close --percentage=0

# --- FINALIZE ---
if [ "$PICKED" == "New Custom Edit" ] && [ -n "$CHOICES" ]; then
    if zenity --question --text="Processing complete. Save this configuration to Favorites?" --title="Save Favorite"; then
        FAV_NAME=$(zenity --entry --text="Enter name for Favorite:" --title="Save Favorite")
        if [ -n "$FAV_NAME" ]; then
            echo "$FAV_NAME|$CHOICES" >> "$PRESET_FILE"
        fi
    fi
fi

zenity --notification --text="Image Processing Finished!"