#!/bin/bash
# 🖼️ Image-Magick-Toolbox v2.1
# Smart Recipe Builder - Stack edits and Context-Aware UI

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/common.sh"
source "$SCRIPT_DIR/../common/wizard.sh"

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
        local info=$($IM_IDENTIFY -format "%m %A %[colorspace]" "$f" 2>/dev/null)
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

DO_MUTE=false
DO_TEXT_ANNOTATION=false

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
        --column="Operation" --column="Description" \
        "🔲 Square Crop (Center 1:1)" "Automatic 1:1 center crop" \
        "📱 Vertical (9:16)" "Standard mobile aspect ratio" \
        "🖥️ Landscape (16:9)" "Standard widescreen aspect ratio" \
        "✍️ Custom Crop" "Specify manual crop geometry"
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
        --column="Layout" --column="Description" \
        "🏁 2x Grid" "2-column grid layout" \
        "🎲 3x Grid" "3-column grid layout" \
        "📑 Contact Sheet" "Labeled thumbnail grid" \
        "➡ Single Row" "Stitch images side-by-side" \
        "⬇ Single Column" "Stitch images vertically"
}

show_effects_interface() {
    local branding_opts="(Inactive)|Watermark PNG|Text Annotation"
    zenity --forms --title="✨ Effects & Branding" --width=450 \
        --text="Apply effects or watermarks:" \
        --add-combo="Visual Effect" --combo-values="No Change|Rotate 90 CW|Rotate 90 CCW|Flip Horizontal|Black & White" \
        --add-combo="Branding" --combo-values="$branding_opts" \
        --add-entry="Watermark Path / Text Content"
}

# Remove obsolete intent functions

# --- UNIFIED MAIN MENU ---
show_main_menu() {
    # 0. System Check & Diagnostics
    _wizard_log "--- NEW DIAGNOSTIC RUN ---"
    _wizard_log "File Checked: $1"
    _wizard_log "IM EXE: $IM_EXE, Version: $($IM_EXE -version | head -n 1)"

    # Run analysis on the first file to set context
    analyze_media "$1"
    _wizard_log "MEDIA_FORMAT: [$MEDIA_FORMAT], HAS_ALPHA: [$HAS_ALPHA], IS_CMYK: [$IS_CMYK]"

    local INTENTS=""
    # 1. Standard Image Ops
    if [[ "$MEDIA_FORMAT" != "PDF" && "$MEDIA_FORMAT" != "VIDEO" ]]; then
        INTENTS+="📏|Scale & Resize|Advanced scaling options;"
        INTENTS+="📏|Scale: 50%|Quick half-size resize;"
        INTENTS+="📏|Scale: 1920x|Resize to HD width;"
        INTENTS+="📏|Scale: 3840x|Resize to 4K width;"
        INTENTS+="📏|Scale: Custom|Specify manual dimensions;"
        INTENTS+="✂️|Crop & Geometry|Square crop or aspect ratios;"
    fi

    # 2. Contextual Image Ops
    [[ "$HAS_ALPHA" -eq 1 ]] && INTENTS+="🎨|Flatten Background|Remove transparency;"
    [[ "$IS_CMYK" -eq 1 ]] && INTENTS+="🌈|Convert to sRGB|Fix colors for web;"
    [[ "$MEDIA_FORMAT" == "PDF" ]] && INTENTS+="📄|Extract Pages|Convert PDF to images;"

    # 3. Standard Global Ops
    INTENTS+="📦|Convert Format|JPG/PNG/WEBP/PDF;✨|Effects & Branding|Rotation, Watermarks, BW"
    [[ "$MEDIA_FORMAT" != "VIDEO" ]] && INTENTS+=";🖼️|Montage & Grid|Combine images into grids"
    [[ "$HAS_AUDIO" -eq 1 ]] && INTENTS+=";🔇|Remove Audio|Strip audio from video"

    local LOOP_COUNT=0
    while true; do
        LOOP_COUNT=$((LOOP_COUNT + 1))
        if [ $LOOP_COUNT -gt 5 ]; then
            _wizard_log "RECURSION GUARD TRIGGERED - Too many reloads"
            zenity --error --text="Recursive UI loop detected ($LOOP_COUNT attempts). Selection might not be matching. Please check $LOG_FILE"
            exit 1
        fi
        
        local PICKED_RAW=$(show_unified_wizard "Image-Magick-Toolbox v2.1" "$INTENTS" "$PRESET_FILE" "$HISTORY_FILE")
        [ -z "$PICKED_RAW" ] && exit 0

        # Result format: "Name|Name|..."
        IFS='|' read -ra PARTS <<< "$PICKED_RAW"
        
        local LOAD_PRESET=""
        local LOAD_HISTORY=""
        local SELECTED_INTENTS=()
        local DO_SAVE=false

        for VALUE_RAW in "${PARTS[@]}"; do
            # Strip whitespace/newlines
            VALUE=$(echo -n "$VALUE_RAW" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [[ -z "$VALUE" || "$VALUE" == "---" ]]; then
                continue
            elif [[ "$VALUE" == "PRESET:"* ]]; then
                LOAD_PRESET="${VALUE#PRESET:}"
            elif [[ "$VALUE" == "HISTORY:"* ]]; then
                LOAD_HISTORY="${VALUE#HISTORY:}"
            elif [[ "$VALUE" == "ACTION:SAVE" ]]; then
                DO_SAVE=true
            else
                SELECTED_INTENTS+=("$VALUE")
            fi
        done

        if [ -n "$LOAD_PRESET" ]; then
            echo $(grep "^$LOAD_PRESET|" "$PRESET_FILE" | cut -d'|' -f2-)
            return 0
        elif [ -n "$LOAD_HISTORY" ]; then
            echo "$LOAD_HISTORY"
            return 0
        elif [ ${#SELECTED_INTENTS[@]} -gt 0 ]; then
            # Build recipe from intents
            local recipe_list=()
            for CHOICE in "${SELECTED_INTENTS[@]}"; do
                case "$CHOICE" in
                    "Scale & Resize")
                        RES=$(show_scale_interface)
                        [ -z "$RES" ] && continue
                        IFS='|' read -ra VALS <<< "$RES"
                        local CLEAN_RES=$(echo "${VALS[0]}" | sed 's/ (.*)$//')
                        if [[ "$CLEAN_RES" == "50%" ]]; then recipe_list+=("Scale: 50%")
                        elif [[ "$CLEAN_RES" == "Custom" ]]; then recipe_list+=("CustomGeometry:${VALS[1]}")
                        else recipe_list+=("Scale: $CLEAN_RES")
                        fi
                        ;;
                    "Scale: 50%")   recipe_list+=("Scale: 50%") ;;
                    "Scale: 1920x")  recipe_list+=("Scale: 1920x") ;;
                    "Scale: 3840x")  recipe_list+=("Scale: 3840x") ;;
                    "Scale: 1280x")  recipe_list+=("Scale: 1280x") ;;
                    "Scale: 640x")   recipe_list+=("Scale: 640x") ;;
                    "Scale: Custom") 
                        RES=$(zenity --entry --title="Scale Width" --text="Enter target width (e.g. 1280) or geometry (800x600):" --entry-text="1920" --cancel-label="Cancel")
                        [ -n "$RES" ] && recipe_list+=("CustomGeometry:$RES")
                        ;;
                    "Crop & Geometry")
                        RES=$(show_crop_interface)
                        [ -z "$RES" ] && continue
                        recipe_list+=("Canvas: $RES")
                        ;;
                    "Convert Format")
                        RES=$(show_convert_interface)
                        [ -z "$RES" ] && continue
                        IFS='|' read -ra VALS <<< "$RES"
                        recipe_list+=("Format: ${VALS[0]}|Optimize: ${VALS[1]}")
                        ;;
                    "Effects & Branding")
                        RES=$(show_effects_interface)
                        [ -z "$RES" ] && continue
                        IFS='|' read -ra VALS <<< "$RES"
                        # Only add if not "No Change" or "(Inactive)"
                        if [[ "${VALS[0]}" != "No Change" || "${VALS[1]}" != "(Inactive)" ]]; then
                            recipe_list+=("Effect: ${VALS[0]}|Branding: ${VALS[1]}|BrandingPayload: ${VALS[2]}")
                        fi
                        ;;
                    "Montage & Grid")
                        RES=$(show_montage_interface)
                        [ -z "$RES" ] && continue
                        # Montage is terminal/special
                        echo "Canvas: $RES"
                        return 0
                        ;;
                    "Flatten Background") recipe_list+=("Effect: Flatten") ;;
                    "Convert to sRGB")    recipe_list+=("Effect: sRGB") ;;
                    "Remove Audio")       recipe_list+=("Effect: Mute") ;;
                    "Extract Pages")      recipe_list+=("Action: ExtractPDF") ;;
                esac
            done
            
            # --- DEDUPLICATE RECIPE ---
            local unique_recipe=()
            for r in "${recipe_list[@]}"; do
                local found=false
                for u in "${unique_recipe[@]}"; do [[ "$u" == "$r" ]] && found=true && break; done
                [[ "$found" == "false" ]] && unique_recipe+=("$r")
            done
            recipe_list=("${unique_recipe[@]}")
            
            # If the user cancelled all sub-dialogs, return to the main menu instead of exiting
            if [ ${#recipe_list[@]} -eq 0 ]; then
                continue
            fi
            
            # Combine recipe_list into final string
            local final_choices=""
            for item in "${recipe_list[@]}"; do
                # Ensure each item only has one pipe at most if it's already a compound
                final_choices+="$item|"
            done
            final_choices="${final_choices%|}"
            
            # Handle inline save if requested
            if [ "$DO_SAVE" = true ]; then
                 prompt_save_preset "$PRESET_FILE" "$final_choices" "My-Recipe" "true"
            fi
            
            echo "$final_choices"
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
save_to_history "$HISTORY_FILE" "$CHOICES"

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
            VAL=$(echo "$opt" | cut -d':' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
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
               *"Custom Crop"*)
                   GEOM=$(zenity --entry --title="Custom Crop" --text="Enter geometry (widthxheight+x+y):" --entry-text="800x600+10+10" --cancel-label="Cancel")
                   if [ -n "$GEOM" ]; then
                       CROP_ARGS+=("-crop" "$GEOM" "+repage")
                       TAG="${TAG}_crop"
                   fi
                   ;;
               *"2x Grid"*) IM_ARGS+=("-tile" "2x" "-geometry" "+0+0"); TAG="${TAG}_grid2x"; DO_MONTAGE=true ;;
               *"3x Grid"*) IM_ARGS+=("-tile" "3x" "-geometry" "+0+0"); TAG="${TAG}_grid3x"; DO_MONTAGE=true ;;
               *"Single Row"*) IM_ARGS+=("-tile" "x1" "-geometry" "+0+0" "-background" "none"); TAG="${TAG}_row"; DO_MONTAGE=true ;;
               *"Single Column"*) IM_ARGS+=("-tile" "1x" "-geometry" "+0+0" "-background" "none"); TAG="${TAG}_col"; DO_MONTAGE=true ;;
               *"Contact Sheet"*) IM_ARGS+=("-thumbnail" "200x200>" "-geometry" "+10+10" "-tile" "4x"); TAG="${TAG}_sheet"; DO_MONTAGE=true ;;
            esac
            ;;
        
        # --- SCALE (PRIORITY 2) ---
        "Scale: 1920x") SCALE_ARGS+=("-resize" "1920x"); TAG="${TAG}_1920p" ;;
        "Scale: 3840x") SCALE_ARGS+=("-resize" "3840x"); TAG="${TAG}_4k" ;;
        "Scale: 1280x") SCALE_ARGS+=("-resize" "1280x"); TAG="${TAG}_720p" ;;
        "Scale: 640x")  SCALE_ARGS+=("-resize" "640x"); TAG="${TAG}_640p" ;;
        "Scale: 50%")   SCALE_ARGS+=("-resize" "50%"); TAG="${TAG}_half" ;;
        
        CustomGeometry:*)
            VAL=$(echo "$opt" | cut -d':' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            [ -n "$VAL" ] && { SCALE_ARGS+=("-resize" "$VAL"); TAG="${TAG}_${VAL}"; }
            ;;

        # --- EFFECTS (PRIORITY 3) ---
        Effect:*)
            VAL=$(echo "$opt" | cut -d':' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
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
            VAL=$(echo "$opt" | cut -d':' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [[ "$VAL" == *"Text Annotation"* ]]; then DO_TEXT_ANNOTATION=true; fi
            ;;
        BrandingPayload:*)
            BRAND_PAYLOAD=$(echo "$opt" | cut -d':' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [ "$DO_TEXT_ANNOTATION" = true ]; then
                EFFECT_ARGS+=("-gravity" "South" "-pointsize" "24" "-annotate" "+0+20" "$BRAND_PAYLOAD")
                TAG="${TAG}_text"
            fi
            ;;
        
        # --- FORMAT/ACTION (PRIORITY 4) ---
        Format:*)
            # Extract just the extension
            OUT_EXT=$(echo "$opt" | cut -d':' -f2- | cut -d'|' -f1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr '[:upper:]' '[:lower:]')
            ;;
        Optimize:*)
            VAL=$(echo "$opt" | cut -d':' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
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

# Combine in priority order - safely to preserve element integrity
IM_ARGS=()
[ ${#CROP_ARGS[@]} -gt 0 ] && IM_ARGS+=("${CROP_ARGS[@]}")
[ ${#SCALE_ARGS[@]} -gt 0 ] && IM_ARGS+=("${SCALE_ARGS[@]}")
[ ${#EFFECT_ARGS[@]} -gt 0 ] && IM_ARGS+=("${EFFECT_ARGS[@]}")
[ ${#FORMAT_ARGS[@]} -gt 0 ] && IM_ARGS+=("${FORMAT_ARGS[@]}")

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
                RET=$?
                rm "/tmp/tmp_mute_${COUNT}.${IN_EXT}"
            else
                $IM_EXE "$f" "${IM_ARGS[@]}" "$OUT_FILE" 2>>"$ERR_LOG"
                RET=$?
            fi
            [ $RET -ne 0 ] && echo "Error processing file: $f" >> "$ERR_LOG"
        }
        
        # In sequential mode we don't need wait -n or jobs
    done
    # Final wait is redundant in sequential but safe
    wait
) | zenity --progress --title="Image-Magick-Toolbox" --auto-close --percentage=0

# --- FINALIZE ---
if [ -s "$ERR_LOG" ]; then
    zenity --text-info --title="Processing Issues" --filename="$ERR_LOG" --width=500 --height=300
fi
rm -f "$ERR_LOG"

# prompt_save_preset logic already handled inline in show_main_menu

zenity --notification --text="Image Processing Finished!"
