#!/bin/bash
# 🖼️ Image-Magick-Toolbox v2.1
# Smart Recipe Builder - Stack edits and Context-Aware UI

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source "$SCRIPT_DIR/common.sh"

# --- CONFIG ---
CONFIG_DIR="$HOME/.config/scripts-sh/imagemagick"
PRESET_FILE="$CONFIG_DIR/presets.conf"
HISTORY_FILE="$CONFIG_DIR/history.conf"
mkdir -p "$CONFIG_DIR"
touch "$PRESET_FILE" "$HISTORY_FILE"

# --- MEDIA ANALYSIS (PRE-FLIGHT) ---
HAS_ALPHA=0
IS_CMYK=0
HAS_AUDIO=0
MEDIA_FORMAT=""

analyze_media() {
    local f="$1"
    [ ! -f "$f" ] && return
    
    local ext=$(echo "${f##*.}" | tr '[:upper:]' '[:lower:]')
    
    # Image Analysis
    if [[ "$ext" =~ ^(jpg|jpeg|png|gif|tiff|webp)$ ]]; then
        # Try to get format, alpha existence, and colorspace
        local info=$(magick identify -format "%m %A %[colorspace]" "$f" 2>/dev/null)
        if [ -n "$info" ]; then
            read -r MEDIA_FORMAT alpha colorspace <<< "$info"
            [[ "$alpha" == "True" || "$alpha" == "Blend" ]] && HAS_ALPHA=1 || HAS_ALPHA=0
            [[ "$colorspace" == "CMYK" ]] && IS_CMYK=1 || IS_CMYK=0
        fi
    # Video Analysis
    elif [[ "$ext" =~ ^(mp4|mkv|mov|avi|webm)$ ]]; then
        MEDIA_FORMAT="VIDEO"
        if command -v ffprobe &>/dev/null; then
            local audio_codec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$f" 2>/dev/null)
            [ -n "$audio_codec" ] && HAS_AUDIO=1 || HAS_AUDIO=0
        fi
    elif [[ "$ext" == "pdf" ]]; then
        MEDIA_FORMAT="PDF"
    fi
}

# --- UI INTERFACES ---

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
    local branding_opts="(Inactive)|Watermark PNG|Text Annotation"
    zenity --forms --title="✨ Effects & Branding" --width=450 \
        --text="Apply effects or watermarks:" \
        --add-combo="Visual Effect" --combo-values="No Change|Rotate 90 CW|Rotate 90 CCW|Flip Horizontal|Black & White" \
        --add-combo="Branding" --combo-values="$branding_opts" \
        --add-entry="Watermark Path / Text Content"
}

# --- DYNAMIC MENU GENERATION ---

get_valid_operations() {
    # Returns rows for zenity list: Icon | Operation | Description
    # We only show operations that make sense for the input type
    
    # 1. Standard Image Ops
    if [[ "$MEDIA_FORMAT" != "PDF" && "$MEDIA_FORMAT" != "VIDEO" ]]; then
        echo "📏|Scale & Resize|Change image dimensions"
        echo "✂️|Crop & Geometry|Square crop or aspect ratios"
    fi

    # 2. Contextual Image Ops
    if [[ "$HAS_ALPHA" -eq 1 ]]; then
        echo "🎨|Flatten Background|Remove transparency (replace with white)"
    fi
    if [[ "$IS_CMYK" -eq 1 ]]; then
        echo "🌈|Convert to sRGB|Fix colors for web viewing"
    fi

    # 3. PDF Ops
    if [[ "$MEDIA_FORMAT" == "PDF" ]]; then
        echo "📄|Extract Pages|Convert PDF pages to individual images"
    fi

    # 4. Standard Global Ops
    echo "📦|Convert Format|JPG, PNG, WEBP, PDF + Optimization"
    
    if [[ "$MEDIA_FORMAT" != "VIDEO" ]]; then
        echo "🖼️|Montage & Grid|Combine images into grids or rows"
    fi

    echo "✨|Effects & Branding|Rotation, Watermarks, BW"

    if [[ "$HAS_AUDIO" -eq 1 ]]; then
        echo "🔇|Remove Audio|Strip audio from video"
    fi
}

# --- MAIN MENU (BUILDER LOOP) ---

show_main_menu() {
    local recipe_list=()
    local display_recipe=""
    
    # Run analysis on the first file to set context
    analyze_media "$1"

    while true; do
        LAUNCH_ARGS=(
            "--list" "--width=700" "--height=550"
            "--title=🖼️ Image-Magick-Toolbox v2.1 (Smart Builder)" "--print-column=2"
            "--column=Status" "--column=Name" "--column=Description"
        )

        # Show Current Recipe if any
        if [ -n "$display_recipe" ]; then
            LAUNCH_ARGS+=("▶️" "RUN OPERATIONS" "Execute: ${display_recipe# → }")
            LAUNCH_ARGS+=("🗑️" "Clear Recipe" "Start over")
            LAUNCH_ARGS+=("---" "------------------" "------------------")
        fi

        # Add Operation Selector
        LAUNCH_ARGS+=("➕" "Add Operation" "Choose a step to add to your recipe")

        # Load Presets
        if [ -s "$PRESET_FILE" ]; then
            while IFS='|' read -r name options; do
                [ -z "$name" ] && continue
                LAUNCH_ARGS+=("⭐" "$name" "Saved Recipe")
            done < "$PRESET_FILE"
        fi

        # Load History
        if [ -s "$HISTORY_FILE" ]; then
            local h_count=0
            while read -r line; do
                [ -z "$line" ] && continue
                [ $h_count -ge 5 ] && break
                LAUNCH_ARGS+=("🕒" "$line" "Recent Recipe")
                ((h_count++))
            done < "$HISTORY_FILE"
        fi

        PICKED=$(zenity "${LAUNCH_ARGS[@]}" --text="Recipe Builder: Build your stacking edit below.")
        if [ -z "$PICKED" ]; then exit 0; fi

        if [ "$PICKED" == "Add Operation" ]; then
            local valid_ops=$(get_valid_operations)
            OP_PICK=(
                "--list" "--width=600" "--height=450"
                "--title=Select Operation" "--print-column=2"
                "--column=Icon" "--column=Operation" "--column=Description"
            )
            while IFS='|' read -r icon op desc; do
                OP_PICK+=("$icon" "$op" "$desc")
            done <<< "$valid_ops"

            CHOICE=$(zenity "${OP_PICK[@]}" --text="What do you want to add?")
            [ -z "$CHOICE" ] && continue

            case "$CHOICE" in
                "Scale & Resize")
                    RES=$(show_scale_interface)
                    [ -z "$RES" ] && continue
                    IFS='|' read -ra VALS <<< "$RES"
                    recipe_list+=("Scale: ${VALS[0]}|CustomGeometry: ${VALS[1]}")
                    display_recipe+=" → Scale"
                    ;;
                "Crop & Geometry")
                    RES=$(show_crop_interface)
                    [ -z "$RES" ] && continue
                    recipe_list+=("Canvas: $RES")
                    display_recipe+=" → Crop"
                    ;;
                "Convert Format")
                    RES=$(show_convert_interface)
                    [ -z "$RES" ] && continue
                    IFS='|' read -ra VALS <<< "$RES"
                    recipe_list+=("Format: ${VALS[0]}|Optimize: ${VALS[1]}")
                    display_recipe+=" → Convert"
                    ;;
                "Montage & Grid")
                    RES=$(show_montage_interface)
                    [ -z "$RES" ] && continue
                    # Montage is terminal/special
                    echo "Canvas: $RES"
                    return 0
                    ;;
                "Effects & Branding")
                    RES=$(show_effects_interface)
                    [ -z "$RES" ] && continue
                    IFS='|' read -ra VALS <<< "$RES"
                    recipe_list+=("Effect: ${VALS[0]}|Branding: ${VALS[1]}|BrandingPayload: ${VALS[2]}")
                    display_recipe+=" → Effects"
                    ;;
                "Flatten Background")
                    recipe_list+=("Effect: Flatten")
                    display_recipe+=" → Flatten"
                    ;;
                "Convert to sRGB")
                    recipe_list+=("Effect: sRGB")
                    display_recipe+=" → sRGB"
                    ;;
                "Remove Audio")
                    recipe_list+=("Effect: Mute")
                    display_recipe+=" → Mute"
                    ;;
                "Extract Pages")
                    recipe_list+=("Action: ExtractPDF")
                    display_recipe+=" → Extract"
                    ;;
            esac
            continue

        elif [ "$PICKED" == "RUN OPERATIONS" ]; then
            # Build the final choice string
            local final_choices=""
            for item in "${recipe_list[@]}"; do
                final_choices+="$item|"
            done
            echo "${final_choices%|}"
            return 0

        elif [ "$PICKED" == "Clear Recipe" ]; then
            recipe_list=()
            display_recipe=""
            continue

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

CHOICES=$(show_main_menu "$1")
[ -z "$CHOICES" ] && exit 0

# Save to History
RECENT=$(head -n 1 "$HISTORY_FILE")
if [ "$CHOICES" != "$RECENT" ]; then
    echo "$CHOICES" | cat - "$HISTORY_FILE" | head -n 15 > "${HISTORY_FILE}.tmp" && mv "${HISTORY_FILE}.tmp" "$HISTORY_FILE"
fi

# Build IM Arguments (Sorting by priority)
# 1. Crop, 2. Scale, 3. Effects, 4. Format
IM_ARGS=()
CROP_ARGS=()
SCALE_ARGS=()
EFFECT_ARGS=()
FORMAT_ARGS=()

ERR_LOG=$(mktemp /tmp/im_toolbox_errors_XXXXX.log)
OUT_EXT=""
TAG=""
DO_MONTAGE=false
DO_PDF_EXTRACT=false

IFS='|' read -ra CHOICE_ARR <<< "$CHOICES"
for opt in "${CHOICE_ARR[@]}"; do
    case "$opt" in
        # --- CROP (PRIORITY 1) ---
        Canvas:*)
            VAL=$(echo "$opt" | cut -d':' -f2 | sed 's/^ //')
            case "$VAL" in
               *"Square Crop"*) 
                   CROP_ARGS+=("-set" "option:distort:viewport" "%[fx:min(w,h)]x%[fx:min(w,h)]" "-distort" "SRT" "0" "+repage")
                   TAG="${TAG}_sq" 
                   ;;
               *"Vertical (9:16)"*)
                   CROP_ARGS+=("-set" "option:distort:viewport" "%[fx:min(w,h*9/16)]x%[fx:min(w*16/9,h)]" "-distort" "SRT" "0" "+repage")
                   TAG="${TAG}_9x16"
                   ;;
               *"Landscape (16:9)"*)
                   CROP_ARGS+=("-set" "option:distort:viewport" "%[fx:min(w,h*16/9)]x%[fx:min(w*9/16,h)]" "-distort" "SRT" "0" "+repage")
                   TAG="${TAG}_16x9"
                   ;;
               *"2x Grid"*) IM_ARGS+=("-tile" "2x" "-geometry" "+0+0"); TAG="${TAG}_grid2x"; DO_MONTAGE=true ;;
               *"3x Grid"*) IM_ARGS+=("-tile" "3x" "-geometry" "+0+0"); TAG="${TAG}_grid3x"; DO_MONTAGE=true ;;
               *"Single Row"*) IM_ARGS+=("-tile" "x1" "-geometry" "+0+0" "-background" "none"); TAG="${TAG}_row"; DO_MONTAGE=true ;;
               *"Single Column"*) IM_ARGS+=("-tile" "1x" "-geometry" "+0+0" "-background" "none"); TAG="${TAG}_col"; DO_MONTAGE=true ;;
               *"Contact Sheet"*) IM_ARGS+=("-thumbnail" "200x200>" "-geometry" "+10+10" "-tile" "4x"); TAG="${TAG}_sheet"; DO_MONTAGE=true ;;
            esac
            ;;
        
        # --- SCALE (PRIORITY 2) ---
        Scale:*)
            VAL=$(echo "$opt" | cut -d' ' -f2)
            case "$VAL" in
                "1920x") SCALE_ARGS+=("-resize" "1920x"); TAG="${TAG}_1920p" ;;
                "3840x") SCALE_ARGS+=("-resize" "3840x"); TAG="${TAG}_4k" ;;
                "1280x") SCALE_ARGS+=("-resize" "1280x"); TAG="${TAG}_720p" ;;
                "640x")  SCALE_ARGS+=("-resize" "640x"); TAG="${TAG}_640p" ;;
                "50%")   SCALE_ARGS+=("-resize" "50%"); TAG="${TAG}_half" ;;
            esac
            ;;
        CustomGeometry:*)
            VAL=$(echo "$opt" | cut -d' ' -f2)
            [ -n "$VAL" ] && { SCALE_ARGS+=("-resize" "$VAL"); TAG="${TAG}_${VAL}"; }
            ;;

        # --- EFFECTS (PRIORITY 3) ---
        Effect:*)
            VAL=$(echo "$opt" | cut -d':' -f2 | sed 's/^ //')
            case "$VAL" in
                *"Rotate 90 CW"*)  EFFECT_ARGS+=("-rotate" "90"); TAG="${TAG}_90cw" ;;
                *"Rotate 90 CCW"*) EFFECT_ARGS+=("-rotate" "-90"); TAG="${TAG}_90ccw" ;;
                *"Flip Horizontal"*) EFFECT_ARGS+=("-flop"); TAG="${TAG}_flop" ;;
                *"Black & White"*) EFFECT_ARGS+=("-colorspace" "gray"); TAG="${TAG}_bw" ;;
                "Flatten") EFFECT_ARGS+=("-background" "white" "-flatten"); TAG="${TAG}_flat" ;;
                "sRGB") EFFECT_ARGS+=("-colorspace" "sRGB"); TAG="${TAG}_srgb" ;;
                "Mute") DO_MUTE=true ;;
            esac
            ;;
        Branding:*)
            VAL=$(echo "$opt" | cut -d':' -f2)
            if [[ "$VAL" == *"Text Annotation"* ]]; then DO_TEXT_ANNOTATION=true; fi
            ;;
        BrandingPayload:*)
            BRAND_PAYLOAD=$(echo "$opt" | cut -d':' -f2 | sed 's/^ //')
            if [ "$DO_TEXT_ANNOTATION" = true ]; then
                EFFECT_ARGS+=("-gravity" "South" "-pointsize" "24" "-annotate" "+0+20" "$BRAND_PAYLOAD")
                TAG="${TAG}_text"
            fi
            ;;
        
        # --- FORMAT/ACTION (PRIORITY 4) ---
        Format:*)
            OUT_EXT=$(echo "$opt" | cut -d' ' -f2 | tr '[:upper:]' '[:lower:]')
            ;;
        Optimize:*)
            VAL=$(echo "$opt" | cut -d':' -f2)
            if [[ "$VAL" == *"Web Ready"* ]]; then
                FORMAT_ARGS+=("-quality" "85" "-strip"); TAG="${TAG}_web"
            elif [[ "$VAL" == *"Max Compression"* ]]; then
                FORMAT_ARGS+=("-quality" "60" "-strip"); TAG="${TAG}_min"
            elif [[ "$VAL" == *"Archive"* ]]; then
                TAG="${TAG}_arch"
            fi
            ;;
        Action:ExtractPDF)
            DO_PDF_EXTRACT=true
            ;;
    esac
done

# Combine in priority order
IM_ARGS=("${CROP_ARGS[@]}" "${SCALE_ARGS[@]}" "${EFFECT_ARGS[@]}" "${FORMAT_ARGS[@]}")

# --- SPECIAL MODE: MONTAGE ---
if [ "$DO_MONTAGE" = true ]; then
    OUT_FILE=$(generate_safe_filename "montage" "$TAG" "${OUT_EXT:-jpg}")
    ( echo "10"; echo "# Creating Montage..."; $IM_MONTAGE "$@" "${IM_ARGS[@]}" "$OUT_FILE" ) | zenity --progress --title="Creating Montage" --auto-close --pulsate
    zenity --notification --text="Montage Finished: $OUT_FILE"
    exit 0
fi

# --- SPECIAL MODE: PDF MERGE/EXTRACT ---
if [[ "$OUT_EXT" == "pdf" && $# -gt 1 && "$DO_PDF_EXTRACT" == false ]]; then
    OUT_FILE=$(generate_safe_filename "merged_images" "$TAG" "pdf")
    ( echo "10"; echo "# Merging into PDF..."; $IM_EXE "$@" "${IM_ARGS[@]}" "$OUT_FILE" ) | zenity --progress --title="Creating PDF" --auto-close --pulsate
    zenity --notification --text="PDF Created: $OUT_FILE"
    exit 0
fi

# --- EXECUTION LOOP (PARALLEL) ---
(
    TOTAL=$#
    COUNT=0
    MAX_JOBS=4
    [ $(nproc) -lt 4 ] && MAX_JOBS=$(nproc)

    for f in "$@"; do
        ((COUNT++))
        PERCENT=$((COUNT * 100 / TOTAL))
        echo "$PERCENT"
        echo "# Processing ($COUNT/$TOTAL): $(basename "$f")..."
        
        BASE="${f%.*}"
        IN_EXT="${f##*.}"
        [ -z "$OUT_EXT" ] && CURRENT_EXT="$IN_EXT" || CURRENT_EXT="$OUT_EXT"
        
        # Handle PDF Extract
        if [[ "$IN_EXT" == "pdf" && "$DO_PDF_EXTRACT" == true ]]; then
            $IM_EXE -density 300 "$f" "${IM_ARGS[@]}" "${BASE}${TAG}-%d.${OUT_EXT:-jpg}" 2>>"$ERR_LOG"
            continue
        fi

        OUT_FILE=$(generate_safe_filename "$BASE" "$TAG" "$CURRENT_EXT")
        
        # Execute chain
        {
            if [ "$DO_MUTE" = true ] && command -v ffmpeg &>/dev/null; then
                ffmpeg -v error -i "$f" -an -c:v copy "/tmp/tmp_mute_${COUNT}.${IN_EXT}"
                $IM_EXE "/tmp/tmp_mute_${COUNT}.${IN_EXT}" "${IM_ARGS[@]}" "$OUT_FILE" 2>>"$ERR_LOG"
                rm "/tmp/tmp_mute_${COUNT}.${IN_EXT}"
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

if [[ "$CHOICES" != *"Recent Recipe"* ]]; then
    if zenity --question --text="Processing complete. Save this recipe as a favorite?" --title="Save Favorite"; then
        FAV_NAME=$(zenity --entry --text="Enter name for Favorite:" --title="Save Favorite")
        [ -n "$FAV_NAME" ] && echo "$FAV_NAME|$CHOICES" >> "$PRESET_FILE"
    fi
fi
zenity --notification --text="Image Processing Finished!"