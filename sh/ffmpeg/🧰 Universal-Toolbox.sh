#!/bin/bash
set -euo pipefail
# Universal FFmpeg Toolbox
# Combine multiple operations (Speed, Scale, Crop, Audio, Format) in one pass.

# Source shared logic
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/common.sh"
source "$SCRIPT_DIR/../common/wizard.sh"

init_ffmpeg_script

# --- CONFIG & PRESETS ---
CONFIG_DIR="$HOME/.config/scripts-sh/ffmpeg"
PRESET_FILE="$CONFIG_DIR/presets.conf"
HISTORY_FILE="$CONFIG_DIR/history.conf"
LOG_FILE="${LOG_FILE:-$HOME/.local/share/scripts-sh/ffmpeg_last_run.log}"
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$CONFIG_DIR"
touch "$HISTORY_FILE"

if [[ ! -s "$PRESET_FILE" ]]; then
    echo "Social Speed Edit|Speed 2x (Fast)|Scale 720p|Normalize (R128)|Output as H.264" > "$PRESET_FILE"
    echo "4K Archival (H.265)|Output as H.265|Clean Metadata" >> "$PRESET_FILE"
    echo "YouTube 1080p (Fast)|Scale 1080p|Normalize (R128)|Output as H.264" >> "$PRESET_FILE"
fi

# --- ARGUMENT PARSING (CLI PRESETS) ---
PRELOADED_CHOICES=""
PRESET_NAME=""
USER_TARGET_MB=""
USER_TRIM_S=""
USER_TRIM_E=""
USER_W=""
USER_SPEED=""
USER_RATIO=""
USER_AUDIO_FILTER=""
USER_SUB_STYLE=""
USER_CRF=""
EXTRA_OPTS=""
DUR=""
START=""
PTS=""
ATEMPO=""
SPEED_VAL=""
VAL_ispd=" (Inactive)"
VAL_ires=" (Inactive)"
VAL_icrp=" (Inactive)"
VAL_ior=" (Inactive)"
VAL_iaud=" (Inactive)"
VAL_isub=" (Inactive)"
REMOVE_AUDIO=false
USE_GPU=false
CMD_HW=()
TAG=""
CHOICES=""

if [[ "${1:-}" == "--preset" ]] && [[ -n "${2:-}" ]]; then
    PRESET_NAME="$2"
    shift 2
elif [[ "${1:-}" == "preset="* ]]; then
    PRESET_NAME="${1#preset=}"
    shift 1
fi

if [[ -n "$PRESET_NAME" ]]; then
    # Read preset line: Name|Choice1|Choice2...
    # Use || true to prevent set -e trigger on no match
    LINE=$(grep "^$PRESET_NAME|" "$PRESET_FILE" 2>/dev/null || true)
    if [[ -n "$LINE" ]]; then
        # Extract choices (everything after first pipe)
        PRELOADED_CHOICES="${LINE#*|}"
    else
        echo "Error: Preset '$PRESET_NAME' not found."
        exit 1
    fi
fi

# Ensure at least one input file exists if no preset is loaded
if [[ -z "$PRELOADED_CHOICES" ]]; then
    if [[ -z "${1:-}" ]]; then
        echo "Usage: $0 [--preset NAME] input.mp4 [input2.mp4 ...]"
        exit 1
    fi
    if [[ ! -f "$1" ]]; then
        echo "Error: File not found: $1"
        exit 1
    fi
    if [[ ! -r "$1" ]]; then
        echo "Error: File not readable: $1"
        exit 1
    fi
fi

# --- GPU PROBE (Run once at startup) ---

# --- UNIFIED LAUNCHPAD ---
# 🧰 Universal-Toolbox v3.1
_wizard_log "Universal-Toolbox started with args: [$*]"

INTENTS_STR="⏪|Speed Control|Change playback speed;📐|Scale / Resize|Change resolution;🖼️|Crop / Aspect Ratio|Vertical/Square/etc;🔄|Rotate & Flip|Fix orientation;⏱️|Trim (Cut Time)|Select segment;🔊|Audio Tools|Normalize/Boost/Mute"
if [ -n "${1:-}" ] && [ -f "${1%.*}.srt" ]; then
    INTENTS_STR+=";📝|Subtitles|Burn-in or Mux .srt"
fi

LOOP_COUNT=0
while true; do
    LOOP_COUNT=$((LOOP_COUNT + 1))
    if [ $LOOP_COUNT -gt 10 ]; then
        _wizard_log "RECURSION GUARD TRIGGERED ($LOOP_COUNT attempts)"
        zenity --error --text="Recursive UI loop detected ($LOOP_COUNT attempts). If this is intentional, please restart the script."
        exit 1
    fi

    if [ -n "$PRELOADED_CHOICES" ]; then
        CHOICES="$PRELOADED_CHOICES"
        break
    fi

    PICKED_RAW=$(show_unified_wizard "Universal Toolbox Wizard" "$INTENTS_STR" "$PRESET_FILE" "$HISTORY_FILE")
    [ -z "$PICKED_RAW" ] && exit 0
    _wizard_log "wizard returned: [$PICKED_RAW]"

    # Parse results
    IFS='|' read -ra PARTS <<< "$PICKED_RAW"
    
    INTENTS=""
    LOAD_PRESET=""
    LOAD_HISTORY=""
    DO_SAVE=false

        for VALUE in "${PARTS[@]}"; do
            VALUE=$(echo -n "$VALUE" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [[ -z "$VALUE" || "$VALUE" == "---" ]]; then
                continue
            elif [[ "$VALUE" == "PRESET:"* ]]; then
                LOAD_PRESET="${VALUE#PRESET:}"
            elif [[ "$VALUE" == "HISTORY:"* ]]; then
                # For history, the ID is the same as the full string
                LOAD_HISTORY="${VALUE#HISTORY:}"
            elif [[ "$VALUE" == "ACTION:SAVE" ]]; then
                DO_SAVE=true
            else
                # Assume INTENT (Clean name from wizard.sh)
                INTENTS+="$VALUE|"
            fi
        done

    if [ -n "$LOAD_PRESET" ]; then
        CHOICES=$(grep "^$LOAD_PRESET|" "$PRESET_FILE" | head -n 1 | cut -d'|' -f2-)
        [ -n "$CHOICES" ] && break
    elif [ -n "$LOAD_HISTORY" ]; then
        CHOICES="$LOAD_HISTORY"
        break
    elif [ -n "$INTENTS" ]; then
        # --- CONFIG & SAVE (Step 2) ---
        # Build same single Form as before, but mapped to selected intents
        ZENITY_FORMS=(
            "--forms" "--title=Universal Toolbox: Configure"
            "--width=500" "--separator=|" 
            "--text=Finalize your recipe settings below:"
        )

        # 1. SPEED
        VAL_ispd=" (Inactive)"
        [[ "$INTENTS" == *"Speed"* ]] && VAL_ispd="1x (Normal)"
        ZENITY_FORMS+=( "--add-combo=⏩ Speed" "--combo-values=$VAL_ispd|2x (Fast)|4x (Super Fast)|0.5x (Slow)|0.25x (Very Slow)" )
        ZENITY_FORMS+=( "--add-entry=✍️ Custom Speed" )

        # 2. SCALE
        VAL_ires=" (Inactive)"
        [[ "$INTENTS" == *"Scale"* ]] && VAL_ires="1080p"
        ZENITY_FORMS+=( "--add-combo=📐 Resolution" "--combo-values=$VAL_ires|1440p|720p|4k|480p|360p|50%" )
        ZENITY_FORMS+=( "--add-entry=✍️ Custom Width (overrides)" )

        # 3. GEOMETRY & TIME
        VAL_icrp=" (Inactive)"
        [[ "$INTENTS" == *"Crop"* ]] && VAL_icrp="16:9 (Landscape)"
        ZENITY_FORMS+=( "--add-combo=🖼️ Crop/Aspect" "--combo-values=$VAL_icrp|9:16 (Vertical)|Square 1:1|4:3 (Classic)|21:9 (Cinema)" )
        ZENITY_FORMS+=( "--add-entry=✍️ Custom Aspect Ratio (e.g. 21:9)" )
        
        VAL_ior=" (Inactive)"
        [[ "$INTENTS" == *"Rotate"* ]] && VAL_ior="No Change"
        ZENITY_FORMS+=( "--add-combo=🔄 Orientation" "--combo-values=$VAL_ior|Rotate 90 CW|Rotate 90 CCW|Flip Horizontal|Flip Vertical" )
        
        ZENITY_FORMS+=( "--add-entry=⏱️ Trim Start" "--add-entry=⏱️ Trim End" )

        # 4. AUDIO & SUBS
        VAL_iaud=" (Inactive)"
        [[ "$INTENTS" == *"Audio"* ]] && VAL_iaud="No Change"
        ZENITY_FORMS+=( "--add-combo=🔊 Audio Action" "--combo-values=$VAL_iaud|Remove Audio Track|Normalize (R128)|Boost Volume (+6dB)|Downmix to Stereo|Recode to PCM (for Linux)|Extract MP3|Extract WAV" )
        ZENITY_FORMS+=( "--add-entry=✍️ Custom Audio Filter (e.g. volume=2.0)" )
        
        VAL_isub=" (Inactive)"
        [[ "$INTENTS" == *"Subtitles"* ]] && VAL_isub="Burn-in"
        ZENITY_FORMS+=( "--add-combo=📝 Subtitles" "--combo-values=$VAL_isub|Burn-in|Mux (Softsub)" )
        ZENITY_FORMS+=( "--add-entry=✍️ Custom Subtitle Style (e.g. Fontsize=30)" )

        # 5. EXPORT (Always active)
        ZENITY_FORMS+=( "--add-combo=💎 Quality Strategy" "--combo-values=Medium (CRF 23)|High (CRF 18)|Low (CRF 28)|Lossless (CRF 0)" )
        ZENITY_FORMS+=( "--add-entry=✍️ Custom CRF (0-51)" )
        ZENITY_FORMS+=( "--add-entry=💾 Target Size MB (overrides)" )
        ZENITY_FORMS+=( "--add-combo=📦 Output Format" "--combo-values=Auto/MP4|H.265|AV1|WebM|ProRes|MOV|MKV|GIF" )
        
        HW_OPTS=""
        if [ -s "$GPU_CACHE" ]; then
            grep -q "nvenc" "$GPU_CACHE" && HW_OPTS="${HW_OPTS}Use NVENC (Nvidia)|"
            grep -q "qsv" "$GPU_CACHE" && HW_OPTS="${HW_OPTS}Use QSV (Intel)|"
            grep -q "vaapi" "$GPU_CACHE" && HW_OPTS="${HW_OPTS}Use VAAPI (AMD/Intel)|"
        fi
        HW_OPTS="${HW_OPTS}None (CPU Only)"
        ZENITY_FORMS+=( "--add-combo=🏎️ Hardware" "--combo-values=$HW_OPTS" )
        ZENITY_FORMS+=( "--add-entry=🔧 Extra FFmpeg Flags" )

        # Use || true to prevent set -e on Cancel (exit 1)
        CONFIG_RESULT=$(zenity "${ZENITY_FORMS[@]}" || true)
        if [ -z "$CONFIG_RESULT" ]; then
            _wizard_log "User cancelled configuration form"
            continue 
        fi

        # --- EXTRACT CONFIG & MAP TO CHOICES ---
        CHOICES=""
        _wizard_log "CONFIG_RESULT: [$CONFIG_RESULT]"
        
        # Single source of truth for field mapping (19 fields)
        FORM_KEYS=(
            speed custom_speed resolution custom_width
            crop custom_ratio rotation trim_start trim_end
            audio custom_audio subtitles custom_subs
            quality custom_crf target_size format hw_accel extra_flags
        )
        # Declare associative array for CONFIG
        declare -A CONFIG
        parse_forms_result "$CONFIG_RESULT" "${FORM_KEYS[@]}"

        # Mapping for 19 fields (0-indexed):
        # 0:Speed 1:Custom_Spd 2:Res 3:CustomW 4:Crop 5:Custom_Ratio 6:Rot 7:TrimS 8:TrimE
        # 9:Audio 10:Custom_Audio 11:Subs 12:Custom_Subs 13:Qual 14:Custom_CRF 15:Target 16:Format 17:HW 18:Extra_Flags

        # 0. Speed
        PICK_spd="${CONFIG[speed]}"; CUST_SPD="${CONFIG[custom_speed]}"
        if [ -n "$CUST_SPD" ]; then
            CHOICES+="Speed: ${CUST_SPD}|"
            USER_SPEED="$CUST_SPD"
        elif [ -n "$PICK_spd" ]; then
            CHOICES+="Speed: ${PICK_spd}|"
        fi

        # 1. Scale
        PICK_res="${CONFIG[resolution]}"; CUST_W="${CONFIG[custom_width]}"
        if [ -n "$CUST_W" ]; then
            CHOICES+="Custom Scale Width:$CUST_W|"
            USER_W="$CUST_W"
        elif [ -n "$PICK_res" ]; then
            CHOICES+="Scale: ${PICK_res}|"
        fi

        # 3. Crop
        PICK_crp="${CONFIG[crop]}"; CUST_RATIO="${CONFIG[custom_ratio]}"
        if [ -n "$CUST_RATIO" ]; then
            CHOICES+="Custom Aspect Ratio:$CUST_RATIO|"
            USER_RATIO="$CUST_RATIO"
        elif [ -n "$PICK_crp" ]; then
            CHOICES+="Crop: $PICK_crp|"
        fi

        # 4. Rotate
        PICK_rot="${CONFIG[rotation]}"
        [[ -n "$PICK_rot" && "$PICK_rot" != "No Change" ]] && CHOICES+="$PICK_rot|"

        # 5. Trim
        T_S="${CONFIG[trim_start]}"; T_E="${CONFIG[trim_end]}"
        [ -n "$T_S" ] && { CHOICES+="Trim: Start|"; USER_TRIM_S="$T_S"; }
        [ -n "$T_E" ] && { CHOICES+="Trim: End|"; USER_TRIM_E="$T_E"; }

        # 7. Audio
        PICK_aud="${CONFIG[audio]}"; CUST_AUD="${CONFIG[custom_audio]}"
        if [ -n "$CUST_AUD" ]; then
            CHOICES+="Audio Filter: $CUST_AUD|"
            USER_AUDIO_FILTER="$CUST_AUD"
        elif [ -n "$PICK_aud" ]; then
            CHOICES+="$PICK_aud|"
        fi

        # 8. Subtitles
        PICK_sub="${CONFIG[subtitles]}"; CUST_SUB="${CONFIG[custom_subs]}"
        if [ -n "$CUST_SUB" ]; then
            CHOICES+="Subtitle Style: $CUST_SUB|"
            USER_SUB_STYLE="$CUST_SUB"
        elif [ -n "$PICK_sub" ]; then
            CHOICES+="Subtitles: $PICK_sub|"
        fi

        # EXPORT
        Q_STRAT="${CONFIG[quality]}"; CUST_CRF="${CONFIG[custom_crf]}"; T_MB="${CONFIG[target_size]}"; O_FMT="${CONFIG[format]}"; H_ACCEL="${CONFIG[hw_accel]}"; EXTRA_OPTS="${CONFIG[extra_flags]}"
        
        if [ -n "$CUST_CRF" ]; then
            CHOICES+="Custom CRF:$CUST_CRF|"
            USER_CRF="$CUST_CRF"
        fi

        if [ -n "$T_MB" ]; then
            CHOICES+="Target Size:$T_MB|"
            USER_TARGET_MB="$T_MB"
        else
            case "$Q_STRAT" in
                *"High"*) CHOICES+="Quality: High|" ;;
                *"Low"*) CHOICES+="Quality: Low|" ;;
                *"Lossless"*) CHOICES+="Quality: Lossless|" ;;
                *) CHOICES+="Quality: Medium|" ;;
            esac
        fi
        
        [[ "$O_FMT" != "Auto/MP4" ]] && CHOICES+="Output: $O_FMT|"

        if [[ "$H_ACCEL" == *"NVENC"* ]]; then CHOICES+="🏎️ Use NVENC (Nvidia)|"; fi
        if [[ "$H_ACCEL" == *"QSV"* ]]; then CHOICES+="🏎️ Use QSV (Intel)|"; fi
        if [[ "$H_ACCEL" == *"VAAPI"* ]]; then CHOICES+="🏎️ Use VAAPI (AMD/Intel)|"; fi

        CHOICES=$(echo "$CHOICES" | sed 's/|$//')
        _wizard_log "Final CHOICES: [$CHOICES]"
        
        [ -z "$CHOICES" ] && continue
        
        SLUG=$(echo "$CHOICES" | sed 's/[^[:alnum:]| ]//g' | sed 's/ (Inactive)//g; s/No Change//g; s/Speed //g; s/Scale //g; s/Rotate //g; s/Flip //g; s/Crop //g; s/Trim //g; s/Output //g; s/Subtitles //g; s/Use //g; s/Fast//g; s/Slow//g; s/pixels//g; s/Quality //g; s/TargetSizeMB //g; s/|/_/g; s/ //g' | tr '[:upper:]' '[:lower:]')
        
        # If user selected ⭐ Save as Favorite in the wizard, force the prompt
        FORCE_SAVE="false"
        [ "$DO_SAVE" = true ] && FORCE_SAVE="true"
        prompt_save_preset "$PRESET_FILE" "$CHOICES" "$SLUG" "$FORCE_SAVE"
        break
    else
        # No selection
        exit 0
    fi
done

# --- AUTOMATED HISTORY TRACKING ---
save_to_history "$HISTORY_FILE" "$CHOICES"

# --- TARGET SIZE PROMPT ---
TARGET_MB="${USER_TARGET_MB}"
# Extract embedded Target Size if present (format: "Target Size:25")
if [[ "$CHOICES" =~ Target\ Size:([0-9.]+) ]]; then
    TARGET_MB="${BASH_REMATCH[1]}"
    USER_TARGET_MB="$TARGET_MB" # Sync for consistency
fi

# Override CRF if custom entry is present
if [ -n "$USER_CRF" ]; then
    CRF_CPU="$USER_CRF"; CQ_NV="$USER_CRF"; GQ_QSV="$USER_CRF"; QP_VA="$USER_CRF"
fi

if [[ "$CHOICES" == *"Target Size"* ]]; then
    if [ -z "$TARGET_MB" ]; then
        TARGET_MB=$(zenity --entry --title="Target Size" --text="Total file size (MB):" --entry-text="25" --cancel-label="Cancel" || true)
    fi
    if [ -z "$TARGET_MB" ]; then
        _wizard_log "User cancelled target size prompt"
        exit 0
    fi
fi

# 2. Logic & Prompts
VF_CHAIN=""
AF_CHAIN=""
INPUT_OPTS=()
VCODEC_OPTS=()
ACODEC_OPTS=("-c:a" "aac" "-b:a" "192k")
GLOBAL_OPTS=("-movflags" "+faststart")
EXT="mp4"
TAG=""
FILTER_COUNT=0
FPS_OVERRIDE=""
USE_GPU=false
GPU_TYPE=""
CMD_HW=() # Initialize CMD_HW array

# Quality Presets Logic
CRF_CPU=23; CQ_NV=23; GQ_QSV=25; QP_VA=25
if [[ "$CHOICES" == *"Quality: High"* ]]; then CRF_CPU=18; CQ_NV=19; GQ_QSV=20; QP_VA=20; TAG="${TAG}_high"; fi
if [[ "$CHOICES" == *"Quality: Low"* ]]; then CRF_CPU=28; CQ_NV=28; GQ_QSV=30; QP_VA=30; TAG="${TAG}_low"; fi
if [[ "$CHOICES" == *"Quality: Lossless"* ]]; then CRF_CPU=0; CQ_NV=0; GQ_QSV=1; QP_VA=1; TAG="${TAG}_lossless"; fi

# Helper to add video filter safely
add_vf() {
    if [ -z "$VF_CHAIN" ]; then VF_CHAIN="$1"; else VF_CHAIN="$VF_CHAIN,$1"; fi
    ((FILTER_COUNT += 1))
}
# Helper to add audio filter safely
add_af() {
    if [ -z "$AF_CHAIN" ]; then AF_CHAIN="$1"; else AF_CHAIN="$AF_CHAIN,$1"; fi
    ((FILTER_COUNT += 1))
}

# --- CUSTOM AUDIO FILTER ---
if [ -n "$USER_AUDIO_FILTER" ]; then
    add_af "$USER_AUDIO_FILTER"
    TAG="${TAG}_af"
fi

# --- CUSTOM INPUTS ---
if [[ "$CHOICES" == *"Trim: Start"* ]]; then
    START="${USER_TRIM_S}"
    if [ -z "$START" ]; then
        START=$(zenity --entry --title="Trim Start" --text="Trim Start time (seconds or hh:mm:ss):" --entry-text="00:00:00" --cancel-label="Cancel" || true)
    fi
    if [ -n "$START" ]; then 
        if VALID_S=$(validate_time_format "$START"); then
            INPUT_OPTS+=( "-ss" "$VALID_S" )
            TAG="${TAG}_cut"
            ((FILTER_COUNT += 1))
        else
            zenity --error --text="Invalid Trim Start format: $START"
        fi
    fi
fi
if [[ "$CHOICES" == *"Trim: End"* ]]; then
    DUR="${USER_TRIM_E}"
    if [ -z "$DUR" ]; then
        DUR=$(zenity --entry --title="Trim End" --text="Trim End time / Duration to keep (seconds or hh:mm:ss):" --entry-text="00:01:00" --cancel-label="Cancel" || true)
    fi
    if [ -n "$DUR" ]; then 
        if VALID_E=$(validate_time_format "$DUR"); then
            INPUT_OPTS+=( "-t" "$VALID_E" )
            TAG="${TAG}_len"
            ((FILTER_COUNT += 1))
        else
            zenity --error --text="Invalid Trim End format: $DUR"
        fi
    fi
fi

# --- SPEED ---
SPEED_VAL=""
if [[ "$CHOICES" =~ Speed:\ ([0-9.]+)x ]]; then
    SPEED_VAL="${BASH_REMATCH[1]}"
    _wizard_log "SPEED_VAL: [$SPEED_VAL]"
    _wizard_log "BC CALL: echo \"$SPEED_VAL <= 0\" | bc -l"
    if (( $(echo "$SPEED_VAL <= 0" | bc -l) )); then
        zenity --error --text="Invalid Speed: $SPEED_VAL (Must be greater than 0)"
        SPEED_VAL="1.0"
    fi
    TAG="${TAG}_${SPEED_VAL}x"
    _wizard_log "BC CALL: echo \"scale=4; 1/$SPEED_VAL\" | bc -l"
    PTS=$(echo "scale=4; 1/$SPEED_VAL" | bc -l)
    ATEMPO="$SPEED_VAL"
fi

if [ -n "$SPEED_VAL" ]; then
    add_vf "setpts=${PTS}*PTS"
    if [[ "$CHOICES" != *"Mute"* && "$CHOICES" != *"Extract"* ]]; then
        CUR_A="$ATEMPO"
        AF_TMP=""
        while (( $(echo "$CUR_A > 2.0" | bc -l) )); do
            AF_TMP="${AF_TMP}atempo=2.0,"
            CUR_A=$(echo "scale=4; $CUR_A/2.0" | bc -l)
        done
        while (( $(echo "$CUR_A < 0.5" | bc -l) )); do
            AF_TMP="${AF_TMP}atempo=0.5,"
            CUR_A=$(echo "scale=4; $CUR_A/0.5" | bc -l)
        done
        add_af "${AF_TMP}atempo=${CUR_A}"
    fi
fi

# --- CROP ---
if [ -n "$USER_RATIO" ]; then
    # Custom Ratio (e.g. 2.35:1)
    # We calculate based on width/height. 
    # Logic: crop to the largest centered area matching the ratio.
    add_vf "crop=ih*($USER_RATIO):ih:(iw-ow)/2:0"
    TAG="${TAG}_ratio"
elif [[ "$CHOICES" == *"Crop: 9:16"* ]]; then add_vf "crop=ih*(9/16):ih:(iw-ow)/2:0"; TAG="${TAG}_9x16"
elif [[ "$CHOICES" == *"Crop: 16:9"* ]]; then add_vf "crop=iw:iw*9/16:0:(ih-ow)/2"; TAG="${TAG}_16x9"
elif [[ "$CHOICES" == *"Crop: Square"* ]]; then add_vf "crop=min(iw\,ih):min(iw\,ih):(iw-ow)/2:(ih-oh)/2"; TAG="${TAG}_sq"
elif [[ "$CHOICES" == *"Crop: 4:3"* ]]; then add_vf "crop=ih*(4/3):ih:(iw-ow)/2:0"; TAG="${TAG}_4x3"
elif [[ "$CHOICES" == *"Crop: 21:9"* ]]; then add_vf "crop=iw:iw*(9/21):0:(ih-oh)/2"; TAG="${TAG}_21x9"
fi

# --- SCALE ---
SCALE_W=""
if [[ "$CHOICES" == *"Scale: 4K"* ]] || [[ "$CHOICES" == *"Scale: 4k"* ]]; then SCALE_W="3840"; TAG="${TAG}_4k"; fi
if [[ "$CHOICES" == *"Scale: 1440p"* ]]; then SCALE_W="2560"; TAG="${TAG}_1440p"; fi
if [[ "$CHOICES" == *"Scale: 1080p"* ]]; then SCALE_W="1920"; TAG="${TAG}_1080p"; fi
if [[ "$CHOICES" == *"Scale: 720p"* ]]; then SCALE_W="1280"; TAG="${TAG}_720p"; fi
if [[ "$CHOICES" == *"Scale: 480p"* ]]; then SCALE_W="854"; TAG="${TAG}_480p"; fi
if [[ "$CHOICES" == *"Scale: 360p"* ]]; then SCALE_W="640"; TAG="${TAG}_360p"; fi
if [[ "$CHOICES" == *"Scale: 50%"* ]]; then SCALE_W="iw*0.5"; TAG="${TAG}_half"; fi
if [[ "$CHOICES" == *"Custom Scale Width"* ]]; then
    W="${USER_W}"
    if [ -z "$W" ]; then
        W=$(zenity --entry --title="Scale Width" --text="Target Width (px):" --entry-text="1280" --cancel-label="Cancel" || true)
    fi
    if [ -n "$W" ]; then SCALE_W="$W"; TAG="${TAG}_${W}w"; fi
fi
# Extract embedded width if present (format: "Custom Scale Width:1280")
if [[ "$CHOICES" =~ Custom\ Scale\ Width:([0-9]+) ]]; then
    SCALE_W="${BASH_REMATCH[1]}"
    TAG="${TAG}_${SCALE_W}w"
fi

if [ -n "$SCALE_W" ]; then
    add_vf "scale=${SCALE_W}:-2"
fi

# --- GEOMETRY ---
if [[ "$CHOICES" == *"Rotate: 90 CW"* ]]; then add_vf "transpose=1"; TAG="${TAG}_90cw"; fi
if [[ "$CHOICES" == *"Rotate: 90 CCW"* ]]; then add_vf "transpose=2"; TAG="${TAG}_90ccw"; fi
if [[ "$CHOICES" == *"Flip: Horizontal"* ]]; then add_vf "hflip"; TAG="${TAG}_flipH"; fi
if [[ "$CHOICES" == *"Flip: Vertical"* ]]; then add_vf "vflip"; TAG="${TAG}_flipV"; fi

# --- AUDIO ---
AUDIO_OPTS=()
if [[ "$CHOICES" == *"Remove Audio Track"* ]]; then 
    AUDIO_OPTS=("-an")
    REMOVE_AUDIO=true
    TAG="${TAG}_noaudio"
else
    if [[ "$CHOICES" == *"Downmix to Stereo"* ]]; then AUDIO_OPTS+=("-ac" "2"); TAG="${TAG}_stereo"; fi
    if [[ "$CHOICES" == *"Normalize"* ]]; then add_af "loudnorm=I=-23:LRA=7:TP=-1.5"; TAG="${TAG}_norm"; fi
    if [[ "$CHOICES" == *"Boost Volume"* ]]; then add_af "volume=6dB"; TAG="${TAG}_boost"; fi
    if [[ "$CHOICES" == *"Recode to PCM"* ]]; then AUDIO_OPTS+=("-c:a" "pcm_s16le"); TAG="${TAG}_pcm"; fi
fi

# --- GPU LOGIC ---
if [[ "$CHOICES" == *"Use NVENC"* ]]; then USE_GPU=true; GPU_TYPE="nvenc"; TAG="${TAG}_nvenc"; CMD_HW=("-hwaccel" "cuda"); fi
if [[ "$CHOICES" == *"Use QSV"* ]]; then USE_GPU=true; GPU_TYPE="qsv"; TAG="${TAG}_qsv"; CMD_HW=("-hwaccel" "qsv" "-init_hw_device" "qsv=hw" "-filter_hw_device" "hw"); fi
if [[ "$CHOICES" == *"Use VAAPI"* ]]; then USE_GPU=true; GPU_TYPE="vaapi"; TAG="${TAG}_vaapi"; CMD_HW=("-hwaccel" "vaapi" "-init_hw_device" "vaapi=hw:/dev/dri/renderD128" "-filter_hw_device" "hw"); fi

# --- FORMAT OVERRIDES ---
IS_audio_only=false
IS_gif=false

if [[ "$CHOICES" == *"Output: H.265"* ]]; then 
    if [ "$USE_GPU" = true ]; then
        if [ "$GPU_TYPE" = "nvenc" ]; then VCODEC_OPTS=("-c:v" "hevc_nvenc" "-preset" "slow" "-rc" "vbr" "-cq" "$CQ_NV" "-pix_fmt" "yuv420p"); fi
        if [ "$GPU_TYPE" = "qsv" ]; then VCODEC_OPTS=("-c:v" "hevc_qsv" "-load_plugin" "hevc_hw" "-preset" "medium" "-global_quality" "$GQ_QSV" "-pix_fmt" "yuv420p"); fi
        if [ "$GPU_TYPE" = "vaapi" ]; then VCODEC_OPTS=("-c:v" "hevc_vaapi" "-rc_mode" "CQP" "-qp" "$QP_VA"); GLOBAL_OPTS+=("-vf" "format=nv12,hwupload"); fi
    else
        VCODEC_OPTS=("-c:v" "libx265" "-crf" "$CRF_CPU" "-preset" "medium")
    fi
    ACODEC_OPTS=("-c:a" "aac" "-b:a" "128k")
    TAG="${TAG}_h265"
elif [[ "$CHOICES" == *"Output: WebM"* ]]; then 
    VCODEC_OPTS=("-c:v" "libvpx-vp9" "-b:v" "0" "-crf" "$CRF_CPU")
    ACODEC_OPTS=("-c:a" "libopus")
    EXT="webm"
    TAG="${TAG}_vp9"
elif [[ "$CHOICES" == *"Output: ProRes"* ]]; then 
    VCODEC_OPTS=("-c:v" "prores_ks" "-profile:v" "3" "-vendor" "apl0" "-bits_per_mb" "8000" "-pix_fmt" "yuv422p10le")
    ACODEC_OPTS=("-c:a" "pcm_s16le")
    EXT="mov"
    TAG="${TAG}_prores"
elif [[ "$CHOICES" == *"Extract MP3"* ]]; then
    VCODEC_OPTS=("-vn")
    AUDIO_OPTS=("-c:a" "libmp3lame" "-q:a" "2")
    EXT="mp3"
    TAG="${TAG}_audio"
    IS_audio_only=true
elif [[ "$CHOICES" == *"Extract WAV"* ]]; then
    VCODEC_OPTS=("-vn")
    ACODEC_OPTS=("-c:a" "pcm_s16le")
    EXT="wav"
    TAG="${TAG}_audio"
    IS_audio_only=true
elif [[ "$CHOICES" == *"Output: GIF"* ]]; then
    IS_gif=true
    EXT="gif"
elif [[ "$CHOICES" == *"Output: AV1"* ]]; then
    VCODEC_OPTS=("-c:v" "libaom-av1" "-crf" "$CRF_CPU" "-cpu-used" "4" "-row-mt" "1")
    ACODEC_OPTS=("-c:a" "libopus")
    EXT="mkv"
    TAG="${TAG}_av1"
elif [[ "$CHOICES" == *"Output: MOV"* ]]; then
    VCODEC_OPTS=("-c:v" "copy")
    ACODEC_OPTS=("-c:a" "copy")
    EXT="mov"
    GLOBAL_OPTS=("-movflags" "+faststart")
    TAG="${TAG}_mov"
elif [[ "$CHOICES" == *"Output: MKV"* ]]; then
    VCODEC_OPTS=("-c:v" "copy")
    ACODEC_OPTS=("-c:a" "copy")
    EXT="mkv"
    GLOBAL_OPTS=()
    TAG="${TAG}_mkv"
else
    # Default H.264
    if [ "$USE_GPU" = true ]; then
        if [ "$GPU_TYPE" = "nvenc" ]; then VCODEC_OPTS=("-c:v" "h264_nvenc" "-preset" "slow" "-rc" "vbr" "-cq" "$CQ_NV" "-pix_fmt" "yuv420p"); fi
        if [ "$GPU_TYPE" = "qsv" ]; then VCODEC_OPTS=("-c:v" "h264_qsv" "-preset" "medium" "-global_quality" "$GQ_QSV" "-pix_fmt" "yuv420p"); fi
        if [ "$GPU_TYPE" = "vaapi" ]; then VCODEC_OPTS=("-c:v" "h264_vaapi" "-rc_mode" "CQP" "-qp" "$QP_VA"); GLOBAL_OPTS+=("-vf" "format=nv12,hwupload"); fi
    else
        # DEFAULT CPU H264
        VCODEC_OPTS=("-c:v" "libx264" "-crf" "$CRF_CPU" "-preset" "medium")
    fi
fi

# --- SUBTITLES ---
HAS_SUBS=false
SUB_EXT=""
if [[ "$CHOICES" == *"Subtitles: Burn-in"* ]]; then HAS_SUBS=true; SUB_TYPE="burn"; TAG="${TAG}_sub"; fi
if [[ "$CHOICES" == *"Subtitles: Mux"* ]]; then HAS_SUBS=true; SUB_TYPE="mux"; TAG="${TAG}_sub"; fi

# --- METADATA ---
if [[ "$CHOICES" == *"Clean Metadata"* ]]; then
    GLOBAL_OPTS+=("-map_metadata" "-1")
fi

# --- SMART FILENAMING ---
# Handled inside the loop now

# --- EXECUTION ---
FAIL_SENTINEL=$(get_sys_temp "toolbox_fail")
rm -f "$FAIL_SENTINEL"

(
for f in "$@"; do
    FILE_TAG="$TAG"
    # Calculate FPS if speed adjustment is active
    FPS_ARG=()
    if [ -n "$SPEED_VAL" ]; then
        IN_FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$f" || true)
        if [ -n "$IN_FPS" ]; then
            FPS_ARG=("-r" "$IN_FPS")
            _wizard_log "Detecting FPS: $IN_FPS for $f"
        fi
    fi

    # Subtitle Logic
    SUB_FILTER=""
    SUB_MAPPING=()
    if [ "$HAS_SUBS" = true ]; then
        SRT_FILE="${f%.*}.srt"
        if [ -f "$SRT_FILE" ]; then
            if [ "$SUB_TYPE" = "burn" ]; then
                # Burn-in: Use relative path (best for ffmpeg)
                REL_SRT="./$(basename "$SRT_FILE")"
                STYLE="Fontsize=24,BorderStyle=3,Outline=2"
                [ -n "$USER_SUB_STYLE" ] && STYLE="$USER_SUB_STYLE"
                SUB_FILTER="subtitles=filename='$REL_SRT':force_style='$STYLE'"
            elif [ "$SUB_TYPE" = "mux" ]; then
                # Mux: Add input and map it
                SUB_MAPPING=("-i" "$SRT_FILE" "-c:s" "mov_text" "-metadata:s:s:0" "language=eng")
                # If output is MKV, use srt codec, else mov_text for MP4
                if [ "$EXT" = "webm" ] || [ "$EXT" = "mkv" ]; then
                     SUB_MAPPING=("-i" "$SRT_FILE" "-c:s" "srt" "-metadata:s:s:0" "language=eng")
                fi
            fi
        fi
    fi

    CMD_FILTERS=()
    # Combine VF_CHAIN and SUB_FILTER
    # Subtitles must be last usually, esp if burning into video
    FULL_VF="$VF_CHAIN"
    if [ -n "$SUB_FILTER" ]; then
        if [ -z "$FULL_VF" ]; then FULL_VF="$SUB_FILTER"; else FULL_VF="$FULL_VF,$SUB_FILTER"; fi
    fi
    
    if [ -n "$FULL_VF" ]; then CMD_FILTERS=("-vf" "$FULL_VF"); fi
    
    # Handle Audio flags correctly
    CURRENT_ACORE=()
    if [ "$REMOVE_AUDIO" = true ]; then
        CURRENT_ACORE=("-an")
    else
        if [ -n "$AF_CHAIN" ] && [ "$IS_audio_only" = false ]; then 
            CURRENT_ACORE=("-af" "$AF_CHAIN" "${ACODEC_OPTS[@]}" "${AUDIO_OPTS[@]}")
        else
            CURRENT_ACORE=("${ACODEC_OPTS[@]}" "${AUDIO_OPTS[@]}")
        fi
    fi
    
    # --- SMART FILENAMING ---
    # Construct tag from active filters
    # TAG is already built globally, FILE_TAG is initialized from it.
    
    # Fallback if empty or generic
    if [ -z "$FILE_TAG" ] || [ "$FILE_TAG" == "_" ]; then FILE_TAG="_edit"; fi
    
    BASE="${f%.*}"
    OUT_FILE=$(generate_safe_filename "$BASE" "$FILE_TAG" "$EXT")
    
    echo "# Processing $f..."
    
    DUR=$(get_duration "$f")
    if [ -z "$DUR" ] || (( $(echo "$DUR <= 0" | bc -l) )); then DUR=1; fi
    
    # --- TARGET SIZE (2-PASS) EXECUTION ---
    if [[ -n "$TARGET_MB" && "$TARGET_MB" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        _wizard_log "Calculating Bitrate for Target Size... MB=$TARGET_MB"
        _wizard_log "Duration for bitrate calc: [$DUR]"
        
        ABR=192
        if [[ "${ACODEC_OPTS[*]:-}" == *"-b:a 128k"* ]]; then ABR=128; fi
        if [ "$REMOVE_AUDIO" = true ]; then ABR=0; fi
        
        TOTAL_BR=$(echo "($TARGET_MB * 8192) / $DUR" | bc -l || echo "1000")
        V_BR=$(echo "$TOTAL_BR - $ABR" | bc -l || echo "800")
        
        # Round to integer for FFmpeg
        V_BR_INT=$(printf "%.0f" "$V_BR" 2>/dev/null || echo "800")
        if [ "$V_BR_INT" -lt 50 ]; then
            zenity --warning --text="Target size ($TARGET_MB MB) is too small for this duration ($DUR sec).\n\nCalculated Video Bitrate: ${V_BR_INT}k."
        fi
        
        # Use safer get_sys_temp which now returns a real file path
        PASS_LOG=$(get_sys_temp "ffmpeg2pass")
        # We use the file path as the logfile prefix (ffmpeg appends extensions like -0.log)
        
        # STRIP QUALITY FLAGS FOR 2-PASS (Bitrate Priority)
        # We remove -crf, -cq, -global_quality, -qp
        VCODEC_2PASS=()
        for opt in "${VCODEC_OPTS[@]}"; do
            [[ "$opt" =~ ^(-crf|-cq|-global_quality|-qp)$ ]] && skip_next=true && continue
            if [ "${skip_next:-false}" = "true" ]; then skip_next=false; continue; fi
            VCODEC_2PASS+=("$opt")
        done
        
        # PASS 1 (Fast & Silent)
        echo "# Pass 1: Analyzing $(basename "$f")..."
        _wizard_log "Pass 1 command: ffmpeg -y -nostdin ${INPUT_OPTS[@]} ${CMD_HW[@]} -i $f ${SUB_MAPPING[@]} ${CMD_FILTERS[@]} ${VCODEC_2PASS[@]} -b:v ${V_BR_INT}k -pass 1 -passlogfile $PASS_LOG -an -f null /dev/null"
        ffmpeg -y -nostdin "${INPUT_OPTS[@]}" "${CMD_HW[@]}" -i "$f" "${SUB_MAPPING[@]}" "${CMD_FILTERS[@]}" "${VCODEC_2PASS[@]}" -b:v "${V_BR_INT}k" -nostats -progress /dev/stdout -pass 1 -passlogfile "$PASS_LOG" -an -f null /dev/null 2>"$LOG_FILE" | awk -v dur="$DUR" -F'=' '/out_time_us=/ { if(dur>0){ pct=($2/1000000)/dur*50; if(pct>49)pct=49; printf "%.0f\n", pct; fflush(); } }'
        STATUS=${PIPESTATUS[0]}

        if [ $STATUS -ne 0 ]; then
            _wizard_log "Pass 1 failed for $f"
            echo "FAIL" > "$FAIL_SENTINEL"
            zenity --error --text="Encoding Pass 1 failed for: $(basename "$f")\n\nCheck $LOG_FILE for details."
            rm -f "${PASS_LOG}"*
            continue
        fi
        
        # PASS 2 (Actual Encode)
        echo "# Pass 2: Encoding $(basename "$f")..."
        _wizard_log "Pass 2 command: ffmpeg -y -nostdin ${INPUT_OPTS[@]} ${CMD_HW[@]} -i $f ${SUB_MAPPING[@]} ${CMD_FILTERS[@]} ${VCODEC_2PASS[@]} -b:v ${V_BR_INT}k -pass 2 -passlogfile $PASS_LOG ${CURRENT_ACORE[@]} ${FPS_ARG[@]} ${GLOBAL_OPTS[@]} ${EXTRA_OPTS} $OUT_FILE"
        ffmpeg -y -nostdin "${INPUT_OPTS[@]}" "${CMD_HW[@]}" -i "$f" "${SUB_MAPPING[@]}" "${CMD_FILTERS[@]}" "${VCODEC_2PASS[@]}" -b:v "${V_BR_INT}k" -nostats -progress /dev/stdout -pass 2 -passlogfile "$PASS_LOG" "${CURRENT_ACORE[@]}" "${FPS_ARG[@]}" "${GLOBAL_OPTS[@]}" ${EXTRA_OPTS} "$OUT_FILE" 2>>"$LOG_FILE" | awk -v dur="$DUR" -F'=' '/out_time_us=/ { if(dur>0){ pct=50+($2/1000000)/dur*50; if(pct>99)pct=99; printf "%.0f\n", pct; fflush(); } }'
        
        STATUS=${PIPESTATUS[0]}
        rm -f "${PASS_LOG}"*
    elif [ "$IS_gif" = true ]; then
        PALETTE=$(get_sys_temp "palette")
        PALETTE="${PALETTE}.png"
        _wizard_log "Generating palette..."
        VF_GIF="palettegen"
        [ -n "$FULL_VF" ] && VF_GIF="$FULL_VF,palettegen"
        
        ffmpeg -y -nostdin "${INPUT_OPTS[@]}" "${CMD_HW[@]}" -i "$f" -vf "$VF_GIF" "$PALETTE" 2>"$LOG_FILE"
        _wizard_log "Creating GIF..."
        LAVFI_GIF="[0:v][1:v] paletteuse"
        [ -n "$FULL_VF" ] && LAVFI_GIF="$FULL_VF [x]; [x][1:v] paletteuse"
        
        echo "# Generating GIF for $(basename "$f")..."
        ffmpeg -y -nostdin "${INPUT_OPTS[@]}" "${CMD_HW[@]}" -i "$f" -i "$PALETTE" -lavfi "$LAVFI_GIF" -nostats -progress /dev/stdout "${FPS_ARG[@]}" "$OUT_FILE" 2>>"$LOG_FILE" | awk -v dur="$DUR" -F'=' '/out_time_us=/ { if(dur>0){ pct=($2/1000000)/dur*100; if(pct>99)pct=99; printf "%.0f\n", pct; fflush(); } }'
        rm "$PALETTE"
        STATUS=${PIPESTATUS[0]}

    else
        # Standard Video/Audio (CRF/CQ Mode)
        echo "# Encoding $(basename "$f")..."
        _wizard_log "Executing: ffmpeg -y -nostdin ${INPUT_OPTS[@]} ${CMD_HW[@]} -i $f ${SUB_MAPPING[@]} ${CMD_FILTERS[@]} ${VCODEC_OPTS[@]} ${CURRENT_ACORE[@]} ${FPS_ARG[@]} ${GLOBAL_OPTS[@]} ${EXTRA_OPTS} $OUT_FILE"
        ffmpeg -y -nostdin "${INPUT_OPTS[@]}" "${CMD_HW[@]}" -i "$f" "${SUB_MAPPING[@]}" "${CMD_FILTERS[@]}" "${VCODEC_OPTS[@]}" -nostats -progress /dev/stdout "${CURRENT_ACORE[@]}" "${FPS_ARG[@]}" "${GLOBAL_OPTS[@]}" ${EXTRA_OPTS} "$OUT_FILE" 2>"$LOG_FILE" | awk -v dur="$DUR" -F'=' '/out_time_us=/ { if(dur>0){ pct=($2/1000000)/dur*100; if(pct>99)pct=99; printf "%.0f\n", pct; fflush(); } }'
        STATUS=${PIPESTATUS[0]}
    fi
    
    # --- GRACEFUL RETRY (Fallback to CPU) ---
    if [ $STATUS -ne 0 ] && [ "$USE_GPU" = true ]; then
        _wizard_log "GPU Encoding failed. Retrying with CPU..."
        echo "# GPU failed. Retrying with CPU..." # Update progress bar
        
        # Reset VCODEC to safe CPU defaults
        if [[ "${VCODEC_OPTS[*]}" == *"hevc"* ]]; then
             VCODEC_OPTS=("-c:v" "libx265" "-crf" "28" "-preset" "medium")
        elif [[ "${VCODEC_OPTS[*]}" == *"h264"* ]]; then
             VCODEC_OPTS=("-c:v" "libx264" "-crf" "23" "-preset" "medium")
        fi
        
        # Clear VAAPI specific global opts safely
        if [ "$GPU_TYPE" = "vaapi" ]; then
            NEW_GLOBAL=()
            skip_next=false
            for opt in "${GLOBAL_OPTS[@]}"; do
                if [ "$skip_next" = "true" ]; then skip_next=false; continue; fi
                if [[ "$opt" == "-vaapi_device" || "$opt" == "-vf" ]]; then
                    # Assuming -vf format=nv12,hwupload was what we added
                    skip_next=true
                    continue
                fi
                NEW_GLOBAL+=("$opt")
            done
            GLOBAL_OPTS=("${NEW_GLOBAL[@]}")
        fi

        _wizard_log "Retrying with: ffmpeg -y -nostdin ${INPUT_OPTS[@]} -i $f ${SUB_MAPPING[@]} ${CMD_FILTERS[@]} ${VCODEC_OPTS[@]} ${CURRENT_ACORE[@]} ${FPS_ARG[@]} ${GLOBAL_OPTS[@]} $OUT_FILE"
        ffmpeg -y -nostdin "${INPUT_OPTS[@]}" -i "$f" "${SUB_MAPPING[@]}" "${CMD_FILTERS[@]}" "${VCODEC_OPTS[@]}" ${EXTRA_OPTS} -nostats -progress /dev/stdout "${CURRENT_ACORE[@]}" "${FPS_ARG[@]}" "${GLOBAL_OPTS[@]}" "$OUT_FILE" 2>>"$LOG_FILE" | awk -v dur="$DUR" -F'=' '/out_time_us=/ { if(dur>0){ pct=($2/1000000)/dur*100; if(pct>99)pct=99; printf "%.0f\n", pct; fflush(); } }'
        STATUS=${PIPESTATUS[0]}
    fi

    if [ $STATUS -eq 0 ]; then
        _wizard_log "Successfully processed: $OUT_FILE"
    else
        _wizard_log "Failed to process: $f"
        echo "FAIL" > "$FAIL_SENTINEL"
        zenity --error --text="Encoding failed for: $(basename "$f")\n\nCheck $LOG_FILE for details."
    fi
    # Final progress jump for item
    echo "100"
done
) | zenity --progress --title="Universal Toolbox" --auto-close --auto-kill

if [ -f "$FAIL_SENTINEL" ] && grep -q "FAIL" "$FAIL_SENTINEL"; then
    rm -f "$FAIL_SENTINEL"
    exit 1
fi
rm -f "$FAIL_SENTINEL"
