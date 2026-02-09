#!/bin/bash
# Universal FFmpeg Toolbox
# Combine multiple operations (Speed, Scale, Crop, Audio, Format) in one pass.

# Source shared logic
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/common.sh"
source "$SCRIPT_DIR/../common/wizard.sh"

# --- GPU PROBE (Run once at startup) ---
probe_gpu </dev/null >/dev/null 2>&1 &

# --- CONFIG & PRESETS ---
CONFIG_DIR="$HOME/.config/scripts-sh/ffmpeg"
PRESET_FILE="$CONFIG_DIR/presets.conf"
HISTORY_FILE="$CONFIG_DIR/history.conf"
mkdir -p "$CONFIG_DIR"
touch "$HISTORY_FILE"

if [ ! -s "$PRESET_FILE" ]; then
    echo "Social Speed Edit|Speed 2x (Fast)|Scale 720p|Normalize (R128)|Output as H.264" > "$PRESET_FILE"
    echo "4K Archival (H.265)|Output as H.265|Clean Metadata" >> "$PRESET_FILE"
    echo "YouTube 1080p (Fast)|Scale 1080p|Normalize (R128)|Output as H.264" >> "$PRESET_FILE"
fi

# --- ARGUMENT PARSING (CLI PRESETS) ---
PRELOADED_CHOICES=""
if [ "$1" == "--preset" ] && [ -n "$2" ]; then
    PRESET_NAME="$2"
    # Read preset line: Name|Choice1|Choice2...
    LINE=$(grep "^$PRESET_NAME|" "$PRESET_FILE")
    if [ -n "$LINE" ]; then
        # Check if we have files passed after the preset args
        shift 2
        # Extract choices (everything after first pipe)
        PRELOADED_CHOICES="${LINE#*|}"
    else
        echo "Error: Preset '$PRESET_NAME' not found."
        exit 1
    fi
fi

# --- UNIFIED LAUNCHPAD ---
while true; do
    if [ -n "$PRELOADED_CHOICES" ]; then
        CHOICES="$PRELOADED_CHOICES"
        break
    fi

    INTENTS_STR="⏪|Speed Control|Change playback speed;📐|Scale / Resize|Change resolution;🖼️|Crop / Aspect Ratio|Vertical/Square/etc;🔄|Rotate & Flip|Fix orientation;⏱️|Trim (Cut Time)|Select segment;🔊|Audio Tools|Normalize/Boost/Mute"
    [ -f "${1%.*}.srt" ] && INTENTS_STR+=";📝|Subtitles|Burn-in or Mux .srt"

    PICKED_RAW=$(show_unified_wizard "Universal Toolbox Wizard" "$INTENTS_STR" "$PRESET_FILE" "$HISTORY_FILE")
    [ -z "$PICKED_RAW" ] && exit 0

    # Parse results. Result format: "Name|Name|..."
    IFS='|' read -ra PARTS <<< "$PICKED_RAW"
    
    INTENTS=""
    LOAD_PRESET=""
    LOAD_HISTORY=""

    for VALUE in "${PARTS[@]}"; do
        if [[ "$VALUE" == "---" ]]; then
            continue
        elif [[ "$VALUE" == "⭐ "* ]]; then
            # PRESET detected
            LOAD_PRESET="${VALUE#* }"
        elif [[ "$VALUE" == "🕒 "* ]]; then
            # HISTORY detected
            LOAD_HISTORY="${VALUE#* }"
        else
            # Assume INTENT
            # Strip icon if present
            if [[ "$VALUE" =~ ^[^[:alnum:]]+[[:space:]] ]]; then
                INTENTS+="${VALUE#* }|"
            else
                INTENTS+="$VALUE|"
            fi
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
        
        VAL_ior=" (Inactive)"
        [[ "$INTENTS" == *"Rotate"* ]] && VAL_ior="No Change"
        ZENITY_FORMS+=( "--add-combo=🔄 Orientation" "--combo-values=$VAL_ior|Rotate 90 CW|Rotate 90 CCW|Flip Horizontal|Flip Vertical" )
        
        ZENITY_FORMS+=( "--add-entry=⏱️ Trim Start" "--add-entry=⏱️ Trim End" )

        # 4. AUDIO & SUBS
        VAL_iaud=" (Inactive)"
        [[ "$INTENTS" == *"Audio"* ]] && VAL_iaud="No Change"
        ZENITY_FORMS+=( "--add-combo=🔊 Audio Action" "--combo-values=$VAL_iaud|Remove Audio Track|Normalize (R128)|Boost Volume (+6dB)|Downmix to Stereo|Recode to PCM (for Linux)|Extract MP3|Extract WAV" )
        
        VAL_isub=" (Inactive)"
        [[ "$INTENTS" == *"Subtitles"* ]] && VAL_isub="Burn-in"
        ZENITY_FORMS+=( "--add-combo=📝 Subtitles" "--combo-values=$VAL_isub|Burn-in|Mux (Softsub)" )

        # 5. EXPORT (Always active)
        ZENITY_FORMS+=( "--add-combo=💎 Quality Strategy" "--combo-values=Medium (CRF 23)|High (CRF 18)|Low (CRF 28)|Lossless (CRF 0)" )
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

        CONFIG_RESULT=$(zenity "${ZENITY_FORMS[@]}")
        [ -z "$CONFIG_RESULT" ] && continue 

        # --- EXTRACT CONFIG & MAP TO CHOICES ---
        CHOICES=""
        IFS='|' read -ra VALS <<< "$CONFIG_RESULT"

        # 0. Speed
        PICK_spd="${VALS[0]}"; CUST_spd="${VALS[1]}"
        if [[ "$PICK_spd" != *"Inactive"* ]]; then
            [ -n "$CUST_spd" ] && CHOICES+="Speed: ${CUST_spd}x|" || CHOICES+="Speed: ${PICK_spd}|"
        fi

        # 2. Scale
        PICK_res="${VALS[2]}"; CUST_W="${VALS[3]}"
        if [ -n "$CUST_W" ]; then
            CHOICES+="Custom Scale Width:$CUST_W|"
            USER_W="$CUST_W"
        elif [[ "$PICK_res" != *"Inactive"* ]]; then
            CHOICES+="Scale: ${PICK_res}|"
        fi

        # 4. Crop
        PICK_crp="${VALS[4]}"
        [[ "$PICK_crp" != *"Inactive"* ]] && CHOICES+="Crop: $PICK_crp|"

        # 5. Rotate
        PICK_rot="${VALS[5]}"
        [[ "$PICK_rot" != *"Inactive"* && "$PICK_rot" != "No Change" ]] && CHOICES+="$PICK_rot|"

        # 6. Trim
        T_S="${VALS[6]}"; T_E="${VALS[7]}"
        [ -n "$T_S" ] && { CHOICES+="Trim: Start|"; USER_TRIM_S="$T_S"; }
        [ -n "$T_E" ] && { CHOICES+="Trim: End|"; USER_TRIM_E="$T_E"; }

        # 8. Audio
        PICK_aud="${VALS[8]}"
        [[ "$PICK_aud" != *"Inactive"* && "$PICK_aud" != "No Change" ]] && CHOICES+="$PICK_aud|"

        # 9. Subs
        PICK_sub="${VALS[9]}"
        [[ "$PICK_sub" != *"Inactive"* ]] && CHOICES+="Subtitles: $PICK_sub|"

        # EXPORT
        Q_STRAT="${VALS[10]}"; T_MB="${VALS[11]}"; O_FMT="${VALS[12]}"; H_ACCEL="${VALS[13]}"

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
        
        [ -z "$CHOICES" ] && continue
        
        SLUG=$(echo "$CHOICES" | sed 's/[^[:alnum:]| ]//g' | sed 's/Speed //g; s/Scale //g; s/Rotate //g; s/Flip //g; s/Crop //g; s/Trim //g; s/Output //g; s/Subtitles //g; s/Use //g; s/Fast//g; s/Slow//g; s/pixels//g; s/Quality //g; s/TargetSizeMB //g; s/|/_/g; s/ //g' | tr '[:upper:]' '[:lower:]')
        
        prompt_save_preset "$PRESET_FILE" "$CHOICES" "$SLUG"
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
if [[ "$CHOICES" =~ Target\ Size:([0-9]+) ]]; then
    TARGET_MB="${BASH_REMATCH[1]}"
    USER_TARGET_MB="$TARGET_MB" # Sync for consistency
fi

if [[ "$CHOICES" == *"Target Size"* ]]; then
    if [ -z "$TARGET_MB" ]; then
        TARGET_MB=$(zenity --entry --title="Target Size" --text="Total file size (MB):" --entry-text="25")
    fi
    [ -z "$TARGET_MB" ] && exit 0
fi

# 2. Logic & Prompts
VF_CHAIN=""
AF_CHAIN=""
INPUT_OPTS=""
VCODEC_OPTS=""
ACODEC_OPTS="-c:a aac -b:a 192k"
GLOBAL_OPTS="-movflags +faststart"
EXT="mp4"
TAG=""
FILTER_COUNT=0
FPS_OVERRIDE=""
USE_GPU=false
GPU_TYPE=""

# Quality Presets Logic
CRF_CPU=23; CQ_NV=23; GQ_QSV=25; QP_VA=25
if [[ "$CHOICES" == *"Quality: High"* ]]; then CRF_CPU=18; CQ_NV=19; GQ_QSV=20; QP_VA=20; TAG="${TAG}_high"; fi
if [[ "$CHOICES" == *"Quality: Low"* ]]; then CRF_CPU=28; CQ_NV=28; GQ_QSV=30; QP_VA=30; TAG="${TAG}_low"; fi
if [[ "$CHOICES" == *"Quality: Lossless"* ]]; then CRF_CPU=0; CQ_NV=0; GQ_QSV=1; QP_VA=1; TAG="${TAG}_lossless"; fi

# Helper to add video filter safely
add_vf() {
    if [ -z "$VF_CHAIN" ]; then VF_CHAIN="$1"; else VF_CHAIN="$VF_CHAIN,$1"; fi
    ((FILTER_COUNT++))
}
# Helper to add audio filter safely
add_af() {
    if [ -z "$AF_CHAIN" ]; then AF_CHAIN="$1"; else AF_CHAIN="$AF_CHAIN,$1"; fi
    ((FILTER_COUNT++))
}

# --- CUSTOM INPUTS ---
if [[ "$CHOICES" == *"Trim: Start"* ]]; then
    START="${USER_TRIM_S}"
    if [ -z "$START" ]; then
        START=$(zenity --entry --title="Trim Start" --text="Start time (seconds or hh:mm:ss):" --entry-text="00:00:10")
    fi
    if [ -n "$START" ]; then INPUT_OPTS="$INPUT_OPTS -ss $START"; TAG="${TAG}_cut"; ((FILTER_COUNT++)); fi
fi
if [[ "$CHOICES" == *"Trim: End"* ]]; then
    DUR="${USER_TRIM_E}"
    if [ -z "$DUR" ]; then
        DUR=$(zenity --entry --title="Trim Duration" --text="Duration to keep (seconds or hh:mm:ss):" --entry-text="00:01:00")
    fi
    if [ -n "$DUR" ]; then INPUT_OPTS="$INPUT_OPTS -t $DUR"; TAG="${TAG}_len"; ((FILTER_COUNT++)); fi
fi

# --- SPEED ---
SPEED_VAL=""
if [[ "$CHOICES" =~ Speed:\ ([0-9.]+)x ]]; then
    SPEED_VAL="${BASH_REMATCH[1]}"
    TAG="${TAG}_${SPEED_VAL}x"
    PTS=$(echo "scale=4; 1/$SPEED_VAL" | bc)
    ATEMPO="$SPEED_VAL"
fi

if [ -n "$SPEED_VAL" ]; then
    add_vf "setpts=${PTS}*PTS"
    if [[ "$CHOICES" != *"Mute"* && "$CHOICES" != *"Extract"* ]]; then
        CUR_A="$ATEMPO"
        AF_TMP=""
        while (( $(echo "$CUR_A > 2.0" | bc -l) )); do
            AF_TMP="${AF_TMP}atempo=2.0,"
            CUR_A=$(echo "scale=4; $CUR_A/2.0" | bc)
        done
        while (( $(echo "$CUR_A < 0.5" | bc -l) )); do
            AF_TMP="${AF_TMP}atempo=0.5,"
            CUR_A=$(echo "scale=4; $CUR_A/0.5" | bc)
        done
        add_af "${AF_TMP}atempo=${CUR_A}"
    fi
fi

# --- CROP ---
if [[ "$CHOICES" == *"Crop: 9:16"* ]]; then add_vf "crop=ih*(9/16):ih:(iw-ow)/2:0"; TAG="${TAG}_9x16"; fi
if [[ "$CHOICES" == *"Crop: 16:9"* ]]; then add_vf "crop=iw:iw*9/16:0:(ih-ow)/2"; TAG="${TAG}_16x9"; fi
if [[ "$CHOICES" == *"Crop: Square"* ]]; then add_vf "crop=min(iw\,ih):min(iw\,ih):(iw-ow)/2:(ih-oh)/2"; TAG="${TAG}_sq"; fi
if [[ "$CHOICES" == *"Crop: 4:3"* ]]; then add_vf "crop=ih*(4/3):ih:(iw-ow)/2:0"; TAG="${TAG}_4x3"; fi
if [[ "$CHOICES" == *"Crop: 21:9"* ]]; then add_vf "crop=iw:iw*(9/21):0:(ih-oh)/2"; TAG="${TAG}_21x9"; fi

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
        W=$(zenity --entry --title="Scale Width" --text="Target Width (px):" --entry-text="1280")
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
AUDIO_OPTS=""
if [[ "$CHOICES" == *"Remove Audio Track"* ]]; then 
    AUDIO_OPTS="-an"
    REMOVE_AUDIO=true
    TAG="${TAG}_noaudio"
else
    if [[ "$CHOICES" == *"Downmix to Stereo"* ]]; then AUDIO_OPTS="-ac 2"; TAG="${TAG}_stereo"; fi
    if [[ "$CHOICES" == *"Normalize"* ]]; then add_af "loudnorm=I=-23:LRA=7:TP=-1.5"; TAG="${TAG}_norm"; fi
    if [[ "$CHOICES" == *"Boost Volume"* ]]; then add_af "volume=6dB"; TAG="${TAG}_boost"; fi
    if [[ "$CHOICES" == *"Recode to PCM"* ]]; then AUDIO_OPTS="-c:a pcm_s16le"; TAG="${TAG}_pcm"; fi
fi

# --- GPU LOGIC ---
if [[ "$CHOICES" == *"Use NVENC"* ]]; then USE_GPU=true; GPU_TYPE="nvenc"; TAG="${TAG}_nvenc"; fi
if [[ "$CHOICES" == *"Use QSV"* ]]; then USE_GPU=true; GPU_TYPE="qsv"; TAG="${TAG}_qsv"; fi
if [[ "$CHOICES" == *"Use VAAPI"* ]]; then USE_GPU=true; GPU_TYPE="vaapi"; TAG="${TAG}_vaapi"; fi

# --- TAG PARSING ---
SPEED_VAL=""
if [[ "$CHOICES" == *"Speed: "* ]]; then
    SPEED_VAL=$(echo "$CHOICES" | grep -o "Speed: [^|]*" | cut -d: -f2 | xargs | cut -dx -f1)
elif [[ "$CHOICES" == *"2x (Fast)"* ]]; then SPEED_VAL="2"
elif [[ "$CHOICES" == *"4x (Super Fast)"* ]]; then SPEED_VAL="4"
elif [[ "$CHOICES" == *"0.5x (Slow)"* ]]; then SPEED_VAL="0.5"
elif [[ "$CHOICES" == *"0.25x (Very Slow)"* ]]; then SPEED_VAL="0.25"
fi

SCALE_W=""
if [[ "$CHOICES" == *"Res: "* ]]; then
    SCALE_W=$(echo "$CHOICES" | grep -o "Res: [^|]*" | cut -d: -f2 | xargs | cut -dp -f1)
elif [[ "$CHOICES" == *"1.44k"* ]]; then SCALE_W="1440"
elif [[ "$CHOICES" == *"1080p"* ]]; then SCALE_W="1080"
elif [[ "$CHOICES" == *"720p"* ]]; then SCALE_W="720"
elif [[ "$CHOICES" == *"4k"* ]]; then SCALE_W="2160"
elif [[ "$CHOICES" == *"480p"* ]]; then SCALE_W="480"
elif [[ "$CHOICES" == *"360p"* ]]; then SCALE_W="360"
elif [[ "$CHOICES" == *"50%"* ]]; then SCALE_W="50%"
fi

CUSTOM_W=$(echo "$CHOICES" | grep -o "CustomW: [^|]*" | cut -d: -f2 | xargs 2>/dev/null || true)
[ -n "$CUSTOM_W" ] && SCALE_W="$CUSTOM_W"

# --- FORMAT OVERRIDES ---
IS_audio_only=false
IS_gif=false

if [[ "$CHOICES" == *"Output: H.265"* ]]; then 
    if [ "$USE_GPU" = true ]; then
        if [ "$GPU_TYPE" = "nvenc" ]; then VCODEC_OPTS="-c:v hevc_nvenc -preset slow -rc vbr -cq $CQ_NV -pix_fmt yuv420p"; fi
        if [ "$GPU_TYPE" = "qsv" ]; then VCODEC_OPTS="-c:v hevc_qsv -load_plugin hevc_hw -preset medium -global_quality $GQ_QSV -pix_fmt yuv420p"; fi
        if [ "$GPU_TYPE" = "vaapi" ]; then VCODEC_OPTS="-c:v hevc_vaapi -rc_mode CQP -qp $QP_VA"; GLOBAL_OPTS="$GLOBAL_OPTS -vaapi_device /dev/dri/renderD128 -vf format=nv12,hwupload"; fi
    else
        VCODEC_OPTS="-c:v libx265 -crf $CRF_CPU -preset medium"
    fi
    ACODEC_OPTS="-c:a aac -b:a 128k"
    TAG="${TAG}_h265"
elif [[ "$CHOICES" == *"Output: WebM"* ]]; then 
    VCODEC_OPTS="-c:v libvpx-vp9 -b:v 0 -crf $CRF_CPU"
    ACODEC_OPTS="-c:a libopus"
    EXT="webm"
    TAG="${TAG}_vp9"
elif [[ "$CHOICES" == *"Output: ProRes"* ]]; then 
    VCODEC_OPTS="-c:v prores_ks -profile:v 3 -vendor apl0 -bits_per_mb 8000 -pix_fmt yuv422p10le"
    ACODEC_OPTS="-c:a pcm_s16le"
    EXT="mov"
    TAG="${TAG}_prores"
elif [[ "$CHOICES" == *"Extract MP3"* ]]; then
    VCODEC_OPTS="-vn"
    AUDIO_OPTS="-c:a libmp3lame -q:a 2"
    EXT="mp3"
    TAG="${TAG}_audio"
    IS_audio_only=true
elif [[ "$CHOICES" == *"Extract Audio (WAV)"* ]]; then
    VCODEC_OPTS="-vn"
    ACODEC_OPTS="-c:a pcm_s16le"
    EXT="wav"
    TAG="${TAG}_audio"
    IS_audio_only=true
elif [[ "$CHOICES" == *"Output: GIF"* ]]; then
    IS_gif=true
    EXT="gif"
elif [[ "$CHOICES" == *"Output: AV1"* ]]; then
    VCODEC_OPTS="-c:v libaom-av1 -crf $CRF_CPU -cpu-used 4 -row-mt 1"
    ACODEC_OPTS="-c:a libopus"
    EXT="mkv"
    TAG="${TAG}_av1"
elif [[ "$CHOICES" == *"Output: MOV"* ]]; then
    VCODEC_OPTS="-c:v copy"
    ACODEC_OPTS="-c:a copy"
    EXT="mov"
    GLOBAL_OPTS="-movflags +faststart"
    TAG="${TAG}_mov"
elif [[ "$CHOICES" == *"Output: MKV"* ]]; then
    VCODEC_OPTS="-c:v copy"
    ACODEC_OPTS="-c:a copy"
    EXT="mkv"
    GLOBAL_OPTS=""
    TAG="${TAG}_mkv"
else
    # Default H.264
    if [ "$USE_GPU" = true ]; then
        if [ "$GPU_TYPE" = "nvenc" ]; then VCODEC_OPTS="-c:v h264_nvenc -preset slow -rc vbr -cq $CQ_NV -pix_fmt yuv420p"; fi
        if [ "$GPU_TYPE" = "qsv" ]; then VCODEC_OPTS="-c:v h264_qsv -preset medium -global_quality $GQ_QSV -pix_fmt yuv420p"; fi
        if [ "$GPU_TYPE" = "vaapi" ]; then VCODEC_OPTS="-c:v h264_vaapi -rc_mode CQP -qp $QP_VA"; GLOBAL_OPTS="$GLOBAL_OPTS -vaapi_device /dev/dri/renderD128 -vf format=nv12,hwupload"; fi
    else
        # DEFAULT CPU H264
        VCODEC_OPTS="-c:v libx264 -crf $CRF_CPU -preset medium"
    fi
fi

# --- SUBTITLES ---
HAS_SUBS=false
SUB_EXT=""
if [[ "$CHOICES" == *"Subtitles: Burn-in"* ]]; then HAS_SUBS=true; SUB_TYPE="burn"; TAG="${TAG}_sub"; fi
if [[ "$CHOICES" == *"Subtitles: Mux"* ]]; then HAS_SUBS=true; SUB_TYPE="mux"; TAG="${TAG}_sub"; fi

# --- METADATA ---
if [[ "$CHOICES" == *"Clean Metadata"* ]]; then
    GLOBAL_OPTS="$GLOBAL_OPTS -map_metadata -1"
fi

# --- SMART FILENAMING ---
# Handled inside the loop now

# --- EXECUTION ---
LOG_FILE="/tmp/ffmpeg_universal_last_run.log"
echo "--- Universal Toolbox Run $(date) ---" > "$LOG_FILE"
echo "Options: $CHOICES" >> "$LOG_FILE"

(
for f in "$@"; do
    FILE_TAG="$TAG"
    # Calculate FPS if speed adjustment is active
    FPS_ARG=""
    if [ -n "$SPEED_VAL" ]; then
        IN_FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$f")
        if [ -n "$IN_FPS" ]; then
            FPS_ARG="-r $IN_FPS"
            echo "Detecting FPS: $IN_FPS for $f" >> "$LOG_FILE"
        fi
    fi

    # Subtitle Logic
    SUB_FILTER=""
    SUB_MAPPING=""
    if [ "$HAS_SUBS" = true ]; then
        SRT_FILE="${f%.*}.srt"
        if [ -f "$SRT_FILE" ]; then
            if [ "$SUB_TYPE" = "burn" ]; then
                # Burn-in: Force style for readability
                # Escape the path for filter: colon must be escaped
                ESC_SRT=$(echo "$SRT_FILE" | sed 's/:/\\:/g')
                SUB_FILTER="subtitles='$ESC_SRT':force_style='Fontsize=24,BorderStyle=3,Outline=2'"
            elif [ "$SUB_TYPE" = "mux" ]; then
                # Mux: Add input and map it
                SUB_MAPPING="-i \"$SRT_FILE\" -c:s mov_text -metadata:s:s:0 language=eng"
                # If output is MKV, use srt codec, else mov_text for MP4
                if [ "$EXT" = "webm" ] || [ "$EXT" = "mkv" ]; then
                     SUB_MAPPING="-i \"$SRT_FILE\" -c:s srt -metadata:s:s:0 language=eng"
                fi
            fi
        fi
    fi

    CMD_FILTERS=""
    # Combine VF_CHAIN and SUB_FILTER
    # Subtitles must be last usually, esp if burning into video
    FULL_VF="$VF_CHAIN"
    if [ -n "$SUB_FILTER" ]; then
        if [ -z "$FULL_VF" ]; then FULL_VF="$SUB_FILTER"; else FULL_VF="$FULL_VF,$SUB_FILTER"; fi
    fi
    
    if [ -n "$FULL_VF" ]; then CMD_FILTERS="-vf \"$FULL_VF\""; fi
    
    # Handle Audio flags correctly
    CURRENT_ACORE=""
    if [ "$REMOVE_AUDIO" = true ]; then
        CURRENT_ACORE="-an"
    else
        if [ -n "$AF_CHAIN" ] && [ "$IS_audio_only" = false ]; then 
            CURRENT_ACORE="-af \"$AF_CHAIN\" $ACODEC_OPTS $AUDIO_OPTS"
        else
            CURRENT_ACORE="$ACODEC_OPTS $AUDIO_OPTS"
        fi
    fi
    
    # --- SMART FILENAMING ---
    # Construct tag from active filters
    FILE_TAG=""
    [ -n "$SPEED_VAL" ] && FILE_TAG="${FILE_TAG}_${SPEED_VAL}x"
    [ -n "$SCALE_W" ] && FILE_TAG="${FILE_TAG}_${SCALE_W}p"
    [ "$REMOVE_AUDIO" = true ] && FILE_TAG="${FILE_TAG}_noaudio"
    [ -n "$GPU_TYPE" ] && FILE_TAG="${FILE_TAG}_${GPU_TYPE}"
    
    # Fallback if empty or generic
    if [ -z "$FILE_TAG" ] || [ "$FILE_TAG" == "_" ]; then FILE_TAG="_edit"; fi
    
    BASE="${f%.*}"
    OUT_FILE=$(generate_safe_filename "$BASE" "$FILE_TAG" "$EXT")
    
    echo "# Processing $f..."
    
    # --- TARGET SIZE (2-PASS) EXECUTION ---
    if [ -n "$TARGET_MB" ]; then
        echo "# Calculating Bitrate for Target Size..." >> "$LOG_FILE"
        DUR=$(get_duration "$f" | cut -d. -f1)
        if [ -z "$DUR" ] || [ "$DUR" -le 0 ]; then DUR=1; fi
        
        ABR=192
        if [[ "$ACODEC_OPTS" == *"-b:a 128k"* ]]; then ABR=128; fi
        if [ "$REMOVE_AUDIO" = true ]; then ABR=0; fi
        
        TOTAL_BR=$(echo "($TARGET_MB * 8192) / $DUR" | bc)
        V_BR=$(echo "$TOTAL_BR - $ABR" | bc)
        
        if [ "$V_BR" -lt 50 ]; then
            zenity --warning --text="Target size ($TARGET_MB MB) is too small for this duration ($DUR sec).\n\nCalculated Video Bitrate: ${V_BR}k."
        fi
        
        PASS_LOG="/tmp/ffmpeg2pass-$$"
        
        # STRIP QUALITY FLAGS FOR 2-PASS (Bitrate Priority)
        # We remove -crf, -cq, -global_quality, -qp
        VCODEC_2PASS=$(echo "$VCODEC_OPTS" | sed -E 's/-crf [0-9]+//g; s/-cq [0-9]+//g; s/-global_quality [0-9]+//g; s/-qp [0-9]+//g')
        
        # PASS 1 (Fast & Silent)
        echo "# Pass 1: Analyzing..."
        CMD1="ffmpeg -y -nostdin $INPUT_OPTS -i \"$f\" $SUB_MAPPING $CMD_FILTERS $VCODEC_2PASS -b:v ${V_BR}k -pass 1 -passlogfile \"$PASS_LOG\" -preset fast -an -f null /dev/null"
        echo "Pass 1: $CMD1" >> "$LOG_FILE"
        eval $CMD1
        
        # PASS 2 (Actual Encode)
        echo "# Pass 2: Finalizing size..."
        CMD2="ffmpeg -y -nostdin $INPUT_OPTS -i \"$f\" $SUB_MAPPING $CMD_FILTERS $VCODEC_2PASS -b:v ${V_BR}k -pass 2 -passlogfile \"$PASS_LOG\" $CURRENT_ACORE $FPS_ARG $GLOBAL_OPTS \"$OUT_FILE\""
        echo "Pass 2: $CMD2" >> "$LOG_FILE"
        eval $CMD2
        
        STATUS=$?
        rm -f "${PASS_LOG}"*
    elif [ "$IS_gif" = true ]; then
        PALETTE="/tmp/palette_$(basename "$f").png"
        echo "Generating palette..." >> "$LOG_FILE"
        VF_GIF="palettegen"
        [ -n "$FULL_VF" ] && VF_GIF="$FULL_VF,palettegen"
        CMD1="ffmpeg -y -nostdin $INPUT_OPTS -i \"$f\" -vf \"$VF_GIF\" \"$PALETTE\""
        echo "$CMD1" >> "$LOG_FILE"
        eval $CMD1
        
        echo "Creating GIF..." >> "$LOG_FILE"
        LAVFI_GIF="[0:v][1:v] paletteuse"
        [ -n "$FULL_VF" ] && LAVFI_GIF="$FULL_VF [x]; [x][1:v] paletteuse"
        CMD2="ffmpeg -y -nostdin $INPUT_OPTS -i \"$f\" -i \"$PALETTE\" -lavfi \"$LAVFI_GIF\" $FPS_ARG \"$OUT_FILE\""
        echo "$CMD2" >> "$LOG_FILE"
        eval $CMD2
        rm "$PALETTE"
        STATUS=$?

    else
        # Standard Video/Audio (CRF/CQ Mode)
        # Note: SUB_MAPPING has -i inside it, so it essentially adds a second input if muxing
        CMD="ffmpeg -y -nostdin $INPUT_OPTS -i \"$f\" $SUB_MAPPING $CMD_FILTERS $VCODEC_OPTS $CURRENT_ACORE $FPS_ARG $GLOBAL_OPTS \"$OUT_FILE\""
        echo "$CMD" >> "$LOG_FILE"
        eval $CMD
        STATUS=$?
    fi
    
    # --- GRACEFUL RETRY (Fallback to CPU) ---
    if [ $STATUS -ne 0 ] && [ "$USE_GPU" = true ]; then
        echo "GPU Encoding failed. Retrying with CPU..." >> "$LOG_FILE"
        echo "# GPU failed. Retrying with CPU..." # Update progress bar
        
        # Reset VCODEC to safe CPU defaults
        if [[ "$VCODEC_OPTS" == *"hevc"* ]]; then
             VCODEC_OPTS="-c:v libx265 -crf 28 -preset medium"
        elif [[ "$VCODEC_OPTS" == *"h264"* ]]; then
             VCODEC_OPTS="-c:v libx264 -crf 23 -preset medium"
        fi
        # Clear VAAPI specific global opts if any
        if [ "$GPU_TYPE" = "vaapi" ]; then GLOBAL_OPTS="-movflags +faststart -map_metadata -1"; fi

        CMD_RETRY="ffmpeg -y $INPUT_OPTS -i \"$f\" $SUB_MAPPING $CMD_FILTERS $VCODEC_OPTS $CURRENT_ACORE $FPS_ARG $GLOBAL_OPTS \"$OUT_FILE\""
        echo "$CMD_RETRY" >> "$LOG_FILE"
        eval $CMD_RETRY
        STATUS=$?
    fi

    if [ $STATUS -ne 0 ]; then
        echo "ERROR: Failed on file $f" >> "$LOG_FILE"
        zenity --error --text="FFmpeg failed on $(basename "$f").\nCheck logs details." --ok-label="Close" --extra-button="Details" --title="Error" < "$LOG_FILE"
    fi
done
) | zenity --progress --title="Universal Toolbox" --pulsate --auto-close

zenity --notification --text="Universal Toolbox Finished!"
