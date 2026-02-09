#!/bin/bash
# 🖼️ Image-Magick-Toolbox v2.0
# Improved UX: Menu-driven operations (aligned with Lossless Toolbox)

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source "$SCRIPT_DIR/common.sh"

# --- CONFIG ---
CONFIG_DIR="$HOME/.config/scripts-sh/imagemagick"
PRESET_FILE="$CONFIG_DIR/presets.conf"
HISTORY_FILE="$CONFIG_DIR/history.conf"
mkdir -p "$CONFIG_DIR"
touch "$PRESET_FILE" "$HISTORY_FILE"

# --- UI FUNCTIONS ---

show_scale_interface() {
    zenity --forms --title="📏 Scale & Resize" --width=450 \
        --text="Select scaling options:" \
        --add-combo="Resolution" --combo-values="1920x (HD)|3840x (4K)|1280x (720p)|640x|50%|Custom" \
        --add-entry="Custom Geometry (e.g. 800x600)"
}

show_crop_interface() {
    zenity --list --title="✂️ Crop & Geometry" --width=500 --height=400 \
        --text="Select a cropping operation:" \
        --column="Type" --column="Operation" --column="Description" \
        "🔲" "Square Crop (Center 1:1)" "Automatic 1:1 center crop" \
        "📱" "Vertical (9:16)" "Standard mobile aspect ratio" \
        "🖥️" "Landscape (16:9)" "Standard widescreen aspect ratio" \
        "✍️" "Custom Crop" "Specify manual crop geometry"
}

show_convert_interface() {
    zenity --forms --title="📦 Convert & Optimize" --width=450 \
        --text="Select format and quality:" \
        --add-combo="Output Format" --combo-values="JPG|PNG|WEBP|TIFF|PDF" \
        --add-combo="Optimize Strategy" --combo-values="Web Ready (Quality 85)|Max Compression|Archive (Lossless)"
}

show_montage_interface() {
    zenity --list --title="🖼️ Montage & Grid" --width=500 --height=400 \
        --text="Select a montage layout:" \
        --column="Type" --column="Layout" --column="Description" \
        "🏁" "2x Grid" "2-column grid layout" \
        "🎲" "3x Grid" "3-column grid layout" \
        "📑" "Contact Sheet" "Labeled thumbnail grid" \
        "➡" "Single Row" "Stitch images side-by-side" \
        "⬇" "Single Column" "Stitch images vertically"
}

show_effects_interface() {
    zenity --forms --title="✨ Effects & Branding" --width=450 \
        --text="Apply effects or watermarks:" \
        --add-combo="Visual Effect" --combo-values="No Change|Rotate 90 CW|Rotate 90 CCW|Flip Horizontal|Black & White" \
        --add-combo="Branding" --combo-values="(Inactive)|Watermark PNG|Text Annotation" \
        --add-entry="Watermark Path / Text Content"
}

# --- MAIN MENU (LAUNCHPAD) ---

show_main_menu() {
    while true; do
        LAUNCH_ARGS=(
            "--list" "--width=650" "--height=500"
            "--title=🖼️ Image-Magick-Toolbox" "--print-column=2"
            "--column=Type" "--column=Name" "--column=Description"
            "➕" "New Operation" "Select an operation from scratch"
        )

        # Load Presets
        if [ -s "$PRESET_FILE" ]; then
            while IFS='|' read -r name options; do
                [ -z "$name" ] && continue
                LAUNCH_ARGS+=("⭐" "$name" "Saved Preset")
            done < "$PRESET_FILE"
        fi

        # Load History
        if [ -s "$HISTORY_FILE" ]; then
            local h_count=0
            while read -r line; do
                [ -z "$line" ] && continue
                [ $h_count -ge 5 ] && break
                LAUNCH_ARGS+=("🕒" "$line" "Recent Operation")
                ((h_count++))
            done < "$HISTORY_FILE"
        fi

        PICKED=$(zenity "${LAUNCH_ARGS[@]}" --text="Select a starting point:")
        if [ -z "$PICKED" ]; then exit 0; fi

        if [ "$PICKED" == "New Operation" ]; then
            OP_PICK=(
                "--list" "--width=600" "--height=450"
                "--title=Select Operation" "--print-column=2"
                "--column=Icon" "--column=Operation" "--column=Description"
                "📏" "Scale & Resize" "Change image dimensions"
                "✂️" "Crop & Geometry" "Square crop or aspect ratios"
                "📦" "Convert Format" "JPG, PNG, WEBP, PDF + Optimization"
                "🖼️" "Montage & Grid" "Combine images into grids or rows"
                "✨" "Effects & Branding" "Rotation, Watermarks, BW"
            )
            CHOICE=$(zenity "${OP_PICK[@]}" --text="What do you want to do?")
            [ -z "$CHOICE" ] && continue

            case "$CHOICE" in
                "Scale & Resize")
                    RES=$(show_scale_interface)
                    [ -z "$RES" ] && continue
                    IFS='|' read -ra VALS <<< "$RES"
                    CHOICES="Scale: ${VALS[0]}|CustomGeometry: ${VALS[1]}"
                    ;;
                "Crop & Geometry")
                    RES=$(show_crop_interface)
                    [ -z "$RES" ] && continue
                    CHOICES="Canvas: $RES"
                    ;;
                "Convert Format")
                    RES=$(show_convert_interface)
                    [ -z "$RES" ] && continue
                    IFS='|' read -ra VALS <<< "$RES"
                    CHOICES="Format: ${VALS[0]}|Optimize: ${VALS[1]}"
                    ;;
                "Montage & Grid")
                    RES=$(show_montage_interface)
                    [ -z "$RES" ] && continue
                    CHOICES="Canvas: $RES"
                    ;;
                "Effects & Branding")
                    RES=$(show_effects_interface)
                    [ -z "$RES" ] && continue
                    IFS='|' read -ra VALS <<< "$RES"
                    CHOICES="Effect: ${VALS[0]}|Branding: ${VALS[1]}|BrandingPayload: ${VALS[2]}"
                    ;;
            esac
            echo "$CHOICES"
            return 0

        elif grep -q "^$PICKED|" "$PRESET_FILE"; then
            echo $(grep "^$PICKED|" "$PRESET_FILE" | cut -d'|' -f2-)
            return 0
        else
            # History item
            echo "$PICKED"
            return 0
        fi
    done
}

# --- MAIN EXECUTION ---

if [ $# -eq 0 ]; then
    zenity --error --text="No files selected."
    exit 1
fi

CHOICES=$(show_main_menu)
[ -z "$CHOICES" ] && exit 0

# Save to History
if [ -n "$CHOICES" ]; then
    RECENT=$(head -n 1 "$HISTORY_FILE")
    if [ "$CHOICES" != "$RECENT" ]; then
        echo "$CHOICES" | cat - "$HISTORY_FILE" | head -n 15 > "${HISTORY_FILE}.tmp" && mv "${HISTORY_FILE}.tmp" "$HISTORY_FILE"
    fi
fi

# Prepare ImageMagick Arguments
IM_ARGS=()
ERR_LOG=$(mktemp /tmp/im_toolbox_errors_XXXXX.log)
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
            [ -n "$VAL" ] && { IM_ARGS+=("-resize" "$VAL"); TAG="${TAG}_${VAL}"; }
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
            elif [[ "$VAL" == *"Archive"* ]]; then
                TAG="${TAG}_arch"
            fi
            ;;
        Effect:*)
            VAL=$(echo "$opt" | cut -d':' -f2 | sed 's/^ //')
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
            VAL=$(echo "$opt" | cut -d':' -f2 | sed 's/^ //')
            case "$VAL" in
               *"Square Crop"*) 
                   IM_ARGS+=("-set" "option:distort:viewport" "%[fx:min(w,h)]x%[fx:min(w,h)]" "-distort" "SRT" "0" "+repage")
                   TAG="${TAG}_sq" 
                   ;;
               *"Vertical (9:16)"*)
                   IM_ARGS+=("-set" "option:distort:viewport" "%[fx:min(w,h*9/16)]x%[fx:min(w*16/9,h)]" "-distort" "SRT" "0" "+repage")
                   TAG="${TAG}_9x16"
                   ;;
               *"Landscape (16:9)"*)
                   IM_ARGS+=("-set" "option:distort:viewport" "%[fx:min(w,h*16/9)]x%[fx:min(w*9/16,h)]" "-distort" "SRT" "0" "+repage")
                   TAG="${TAG}_16x9"
                   ;;
               *"2x Grid"*) IM_ARGS+=("-tile" "2x" "-geometry" "+0+0"); TAG="${TAG}_grid2x"; DO_MONTAGE=true ;;
               *"3x Grid"*) IM_ARGS+=("-tile" "3x" "-geometry" "+0+0"); TAG="${TAG}_grid3x"; DO_MONTAGE=true ;;
               *"Single Row"*) IM_ARGS+=("-tile" "x1" "-geometry" "+0+0" "-background" "none"); TAG="${TAG}_row"; DO_MONTAGE=true ;;
               *"Single Column"*) IM_ARGS+=("-tile" "1x" "-geometry" "+0+0" "-background" "none"); TAG="${TAG}_col"; DO_MONTAGE=true ;;
               *"Contact Sheet"*) IM_ARGS+=("-thumbnail" "200x200>" "-geometry" "+10+10" "-tile" "4x"); TAG="${TAG}_sheet"; DO_MONTAGE=true ;;
            esac
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
    [ "$MAX_JOBS" -gt 4 ] && MAX_JOBS=4 

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
            if [[ "$IN_EXT" == "pdf" && "$OUT_EXT" != "pdf" ]]; then
                $IM_EXE -density 300 "$f" "${IM_ARGS[@]}" "${BASE}${TAG}-%d.${OUT_EXT:-jpg}" 2>>"$ERR_LOG"
            elif [[ "$CHOICES" == *"Branding: Watermark PNG"* ]]; then
                WM_PATH="${BRAND_PAYLOAD:-watermark.png}"
                [ ! -f "$WM_PATH" ] && [ -f "$SCRIPT_DIR/$WM_PATH" ] && WM_PATH="$SCRIPT_DIR/$WM_PATH"
                if [ -f "$WM_PATH" ]; then
                    $IM_EXE "$f" "${IM_ARGS[@]}" miff:- | $IM_COMPOSITE -dissolve 30 -gravity Southeast "$WM_PATH" - "$OUT_FILE" 2>>"$ERR_LOG"
                else
                    $IM_EXE "$f" "${IM_ARGS[@]}" "$OUT_FILE" 2>>"$ERR_LOG"
                fi
            else
                $IM_EXE "$f" "${IM_ARGS[@]}" "$OUT_FILE" 2>>"$ERR_LOG"
            fi
            
            [ $? -ne 0 ] && echo "Error processing file: $f" >> "$ERR_LOG"
        } &
        
        [[ $(jobs -r | wc -l) -ge $MAX_JOBS ]] && wait -n
    done
    wait
) | zenity --progress --title="Image-Magick-Toolbox" --auto-close --percentage=0

# --- FINALIZE ---
if [ -s "$ERR_LOG" ]; then
    zenity --text-info --title="Processing Issues" --filename="$ERR_LOG" --width=500 --height=300
fi
rm -f "$ERR_LOG"

if [[ "$CHOICES" != *"Recent Operation"* ]]; then
    if zenity --question --text="Processing complete. Save this configuration to Favorites?" --title="Save Favorite"; then
        FAV_NAME=$(zenity --entry --text="Enter name for Favorite:" --title="Save Favorite")
        [ -n "$FAV_NAME" ] && echo "$FAV_NAME|$CHOICES" >> "$PRESET_FILE"
    fi
fi

zenity --notification --text="Image Processing Finished!"