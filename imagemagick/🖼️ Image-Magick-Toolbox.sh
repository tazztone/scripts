#!/bin/bash
# 🖼️ Image-Magick-Toolbox v3.0
# Unified Wizard UX: Checklist -> Integrated Form

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source "$SCRIPT_DIR/common.sh"

# --- CONFIG ---
CONFIG_DIR="$HOME/.config/scripts-sh/imagemagick"
mkdir -p "$CONFIG_DIR"

# --- MEDIA ANALYSIS ---
HAS_ALPHA=0
IS_CMYK=0
HAS_AUDIO=0
MEDIA_FORMAT=""

analyze_media() {
    local f="$1"
    [ ! -f "$f" ] && return
    local ext=$(echo "${f##*.}" | tr '[:upper:]' '[:lower:]')
    
    if [[ "$ext" =~ ^(jpg|jpeg|png|gif|tiff|webp)$ ]]; then
        local info=$(magick identify -format "%m %A %[colorspace]" "$f" 2>/dev/null)
        if [ -n "$info" ]; then
            read -r MEDIA_FORMAT alpha colorspace <<< "$info"
            [[ "$alpha" == "True" || "$alpha" == "Blend" ]] && HAS_ALPHA=1 || HAS_ALPHA=0
            [[ "$colorspace" == "CMYK" ]] && IS_CMYK=1 || IS_CMYK=0
        fi
    elif [[ "$ext" =~ ^(mp4|mkv|mov|avi|webm)$ ]]; then
        MEDIA_FORMAT="VIDEO"
        command -v ffprobe &>/dev/null && [ -n "$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of csv=p=0 "$f" 2>/dev/null | head -1)" ] && HAS_AUDIO=1
    elif [[ "$ext" == "pdf" ]]; then
        MEDIA_FORMAT="PDF"
    fi
}

# --- WIZARD logic ---

show_wizard() {
    local f="$1"
    analyze_media "$f"

    # --- STEP 1: INTENT CHECKLIST ---
    INTENT_ARGS=(
        "--list" "--checklist" "--width=600" "--height=450"
        "--title=🖼️ Image-Magick-Toolbox v3.0"
        "--column=Select" "--column=Operation" "--column=Description"
    )

    # Context-aware intents
    if [[ "$MEDIA_FORMAT" != "PDF" && "$MEDIA_FORMAT" != "VIDEO" ]]; then
        INTENT_ARGS+=(TRUE "📏 Scale" "Change image dimensions")
        INTENT_ARGS+=(FALSE "✂️ Crop" "Square crop or aspect ratios")
    fi
    [[ "$HAS_ALPHA" -eq 1 ]] && INTENT_ARGS+=(FALSE "🎨 Flatten" "Remove transparency")
    [[ "$IS_CMYK" -eq 1 ]] && INTENT_ARGS+=(FALSE "🌈 sRGB" "Fix colors for web")
    
    if [[ "$MEDIA_FORMAT" == "PDF" ]]; then
        INTENT_ARGS+=(TRUE "📄 Extract" "PDF pages to images")
    fi

    INTENT_ARGS+=(FALSE "✨ Effects" "Rotation, BW, Branding")
    
    if [[ "$MEDIA_FORMAT" != "VIDEO" ]]; then
        INTENT_ARGS+=(FALSE "🖼️ Montage" "Combine into grids (Terminal op)")
    fi
    [[ "$HAS_AUDIO" -eq 1 ]] && INTENT_ARGS+=(FALSE "🔇 Mute" "Strip audio track")

    # Final "Always show"
    INTENT_ARGS+=(TRUE "📦 Output" "Format and Optimization")

    INTENTS=$(zenity "${INTENT_ARGS[@]}" --text="Step 1: Select all intended operations:")
    [ -z "$INTENTS" ] && exit 0

    # --- STEP 2: INTEGRATED CONFIG FORM ---
    FORM_ARGS=(
        "--forms" "--title=Configure Operations" "--width=500"
        "--text=Step 2: Configure your selected operations at once."
    )

    [[ "$INTENTS" == *"Scale"* ]] && FORM_ARGS+=(--add-combo="📏 Scale" --combo-values="1920x (HD)|3840x (4K)|1280x (720p)|640x|50%")
    [[ "$INTENTS" == *"Crop"* ]] && FORM_ARGS+=(--add-combo="✂️ Crop Ratio" --combo-values="Square (1:1)|Vertical (9:16)|Landscape (16:9)")
    [[ "$INTENTS" == *"Effects"* ]] && {
        FORM_ARGS+=(--add-combo="✨ Visual" --combo-values="No Change|Rotate 90 CW|Rotate 90 CCW|Flip Horizontal|Black & White")
        FORM_ARGS+=(--add-entry="🏷️ Text Annotation")
    }
    [[ "$INTENTS" == *"Montage"* ]] && FORM_ARGS+=(--add-combo="🖼️ Grid" --combo-values="2x Grid|3x Grid|Contact Sheet|Single Row")
    
    # Output Settings (Always at end of form)
    FORM_ARGS+=(--add-combo="📦 Format" --combo-values="JPG|PNG|WEBP|TIFF|PDF")
    FORM_ARGS+=(--add-combo="🚀 Quality" --combo-values="Web Ready (85)|High Compression (60)|Lossless")

    RESULT=$(zenity "${FORM_ARGS[@]}")
    [ -z "$RESULT" ] && exit 0
    echo "$INTENTS|$RESULT"
}

# --- EXECUTION ---

FILES=("$@")
[ ${#FILES[@]} -eq 0 ] && { zenity --error --text="No files selected."; exit 1; }

CONFIG=$(show_wizard "${FILES[0]}")
[ -z "$CONFIG" ] && exit 0

# Parse CONFIG
IFS='|' read -ra PARTS <<< "$CONFIG"
INTENTS="${PARTS[0]}"
# Remaining parts are form fields. Mapping follows addition order in show_wizard.
# We need to be careful with indexing since fields are dynamic.
f_idx=1
V_SCALE=""; V_CROP=""; V_EFFECT=""; V_BRAND=""; V_GRID=""; V_FORMAT=""; V_QUALITY=""

[[ "$INTENTS" == *"Scale"* ]] && { V_SCALE="${PARTS[$f_idx]}"; ((f_idx++)); }
[[ "$INTENTS" == *"Crop"* ]] && { V_CROP="${PARTS[$f_idx]}"; ((f_idx++)); }
[[ "$INTENTS" == *"Effects"* ]] && { V_EFFECT="${PARTS[$f_idx]}"; ((f_idx++)); V_BRAND="${PARTS[$f_idx]}"; ((f_idx++)); }
[[ "$INTENTS" == *"Montage"* ]] && { V_GRID="${PARTS[$f_idx]}"; ((f_idx++)); }
V_FORMAT="${PARTS[$f_idx]}"; ((f_idx++))
V_QUALITY="${PARTS[$f_idx]}"

# Build Arguments
IM_ARGS=()
C_ARGS=()
S_ARGS=()
E_ARGS=()
F_ARGS=()
TAG=""
OUT_EXT=$(echo "$V_FORMAT" | tr '[:upper:]' '[:lower:]')
DO_MONTAGE=false; DO_MUTE=false; DO_EXTRACT=false

# 1. Crop (Priority 1)
case "$V_CROP" in
    *"Square"*) C_ARGS+=("-set" "option:distort:viewport" "%[fx:min(w,h)]x%[fx:min(w,h)]" "-distort" "SRT" "0" "+repage"); TAG+="_sq" ;;
    *"Vertical"*) C_ARGS+=("-set" "option:distort:viewport" "%[fx:min(w,h*9/16)]x%[fx:min(w*16/9,h)]" "-distort" "SRT" "0" "+repage"); TAG+="_9x16" ;;
    *"Landscape"*) C_ARGS+=("-set" "option:distort:viewport" "%[fx:min(w,h*16/9)]x%[fx:min(w*9/16,h)]" "-distort" "SRT" "0" "+repage"); TAG+="_16x9" ;;
esac

# 2. Scale (Priority 2)
case "$V_SCALE" in
    "1920x"*) S_ARGS+=("-resize" "1920x"); TAG+="_1080p" ;;
    "3840x"*) S_ARGS+=("-resize" "3840x"); TAG+="_4k" ;;
    "1280x"*) S_ARGS+=("-resize" "1280x"); TAG+="_720p" ;;
    "640x"*)  S_ARGS+=("-resize" "640x"); TAG+="_640p" ;;
    "50%"*)   S_ARGS+=("-resize" "50%"); TAG+="_half" ;;
esac

# 3. Effects (Priority 3)
case "$V_EFFECT" in
    *"90 CW"*) E_ARGS+=("-rotate" "90"); TAG+="_90cw" ;;
    *"90 CCW"*) E_ARGS+=("-rotate" "-90"); TAG+="_90ccw" ;;
    *"Flip"*) E_ARGS+=("-flop"); TAG+="_flop" ;;
    *"Black & White"*) E_ARGS+=("-colorspace" "gray"); TAG+="_bw" ;;
esac
[ -n "$V_BRAND" ] && { E_ARGS+=("-gravity" "South" "-pointsize" "24" "-annotate" "+0+20" "$V_BRAND"); TAG+="_label"; }
[[ "$INTENTS" == *"Flatten"* ]] && { E_ARGS+=("-background" "white" "-flatten"); TAG+="_flat"; }
[[ "$INTENTS" == *"sRGB"* ]] && { E_ARGS+=("-colorspace" "sRGB"); TAG+="_srgb"; }
[[ "$INTENTS" == *"Mute"* ]] && DO_MUTE=true
[[ "$INTENTS" == *"Extract"* ]] && DO_EXTRACT=true

# 4. Global Params (Priority 4)
case "$V_QUALITY" in
    *"Web Ready"*) F_ARGS+=("-quality" "85" "-strip"); TAG+="_web" ;;
    *"High Compression"*) F_ARGS+=("-quality" "60" "-strip"); TAG+="_min" ;;
esac

# 5. Montage (Special)
case "$V_GRID" in
    "2x Grid") IM_ARGS=("-tile" "2x" "-geometry" "+0+0"); TAG+="_grid2x"; DO_MONTAGE=true ;;
    "3x Grid") IM_ARGS=("-tile" "3x" "-geometry" "+0+0"); TAG+="_grid3x"; DO_MONTAGE=true ;;
    "Contact Sheet") IM_ARGS=("-thumbnail" "200x200>" "-geometry" "+10+10" "-tile" "4x"); TAG+="_sheet"; DO_MONTAGE=true ;;
    "Single Row") IM_ARGS=("-tile" "x1" "-geometry" "+0+0" "-background" "none"); TAG+="_row"; DO_MONTAGE=true ;;
esac

# Final IM Assembly
[ "$DO_MONTAGE" = false ] && IM_ARGS=("${C_ARGS[@]}" "${S_ARGS[@]}" "${E_ARGS[@]}" "${F_ARGS[@]}")

# Process
ERR_LOG=$(mktemp /tmp/im_error_XXXX.log)
if [ "$DO_MONTAGE" = true ]; then
    OUT_FILE=$(generate_safe_filename "montage" "$TAG" "$OUT_EXT")
    $IM_MONTAGE "${FILES[@]}" "${IM_ARGS[@]}" "$OUT_FILE" 2>>"$ERR_LOG"
else
    (
        COUNT=0; TOTAL=${#FILES[@]}
        for f in "${FILES[@]}"; do
            ((COUNT++))
            PERCENT=$((COUNT * 100 / TOTAL))
            echo "$PERCENT"; echo "# Processing: $(basename "$f")..."
            
            BASE="${f%.*}"
            IN_EXT="${f##*.}"
            
            if [ "$DO_EXTRACT" = true ]; then
                $IM_EXE -density 300 "$f" "${IM_ARGS[@]}" "${BASE}${TAG}-%d.${OUT_EXT}" 2>>"$ERR_LOG"
            else
                OUT_FILE=$(generate_safe_filename "$BASE" "$TAG" "${OUT_EXT}")
                if [ "$DO_MUTE" = true ] && command -v ffmpeg &>/dev/null; then
                    ffmpeg -v error -i "$f" -an -c:v copy "/tmp/tmp_v3_${COUNT}.${IN_EXT}"
                    $IM_EXE "/tmp/tmp_v3_${COUNT}.${IN_EXT}" "${IM_ARGS[@]}" "$OUT_FILE" 2>>"$ERR_LOG"
                    rm "/tmp/tmp_v3_${COUNT}.${IN_EXT}"
                else
                    $IM_EXE "$f" "${IM_ARGS[@]}" "$OUT_FILE" 2>>"$ERR_LOG"
                fi
            fi
        done
    ) | zenity --progress --title="Image-Magick-Toolbox v3.0" --auto-close
fi

[ -s "$ERR_LOG" ] && zenity --text-info --title="Errors" --filename="$ERR_LOG"
rm -f "$ERR_LOG"
zenity --notification --text="Finished!"