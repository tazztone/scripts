#!/bin/bash
# Universal FFmpeg Toolbox
# Combine multiple operations (Speed, Scale, Crop, Audio, Format) in one pass.

# Function to get video duration
get_duration() {
    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$1" | cut -d. -f1
}

# --- CONFIG & PRESETS ---
CONFIG_DIR="$HOME/.config/scripts-sh"
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

# --- LAUNCHPAD (MAIN MENU) ---
while true; do
    if [ -n "$PRELOADED_CHOICES" ]; then
        CHOICES="$PRELOADED_CHOICES"
        break
    fi

    LAUNCH_ARGS=(
        "--list" "--width=600" "--height=500"
        "--title=Universal Toolbox Launchpad" "--print-column=2"
        "--column=Type" "--column=Name" "--column=Description"
        "✨" "New Custom Edit" "Build a selection from scratch"
    )

    # 1. Load Favorites (Presets)
    if [ -s "$PRESET_FILE" ]; then
        while IFS='|' read -r name options; do
            [ -z "$name" ] && continue
            # Display name, and a preview of the options (readable)
            PREVIEW=$(echo "$options" | sed 's/|/, /g')
            LAUNCH_ARGS+=("⭐" "$name" "$PREVIEW")
        done < "$PRESET_FILE"
    fi

    # 2. Load History
    if [ -s "$HISTORY_FILE" ]; then
        while read -r line; do
            [ -z "$line" ] && continue
            PREVIEW=$(echo "$line" | sed 's/|/, /g')
            LAUNCH_ARGS+=("🕒" "$line" "$PREVIEW")
        done < "$HISTORY_FILE"
    fi

    PICKED=$(zenity "${LAUNCH_ARGS[@]}" --text="Select a starting point:")
    if [ -z "$PICKED" ]; then exit 0; fi

    if [ "$PICKED" == "New Custom Edit" ]; then
        # --- CHECKLIST BUILDER ---
        # ARRAY-BASED CONSTRUCTION (SAFE)
        ZENITY_ARGS=(
            "--list" "--checklist" "--width=600" "--height=750"
            "--title=Universal Edit Builder" "--print-column=3"
            "--column=Pick" "--column=Category" "--column=Option" "--column=Description"
            FALSE "Speed" "Speed 2x (Fast)" "Double speed (50% duration)"
            FALSE "Speed" "Speed 4x (Super Fast)" "Quadruple speed (25% duration)"
            FALSE "Speed" "Speed 0.5x (Slow)" "Half speed (2x duration)" 
            FALSE "Resolution" "Scale 4K" "3840x2160" 
            FALSE "Resolution" "Scale 1080p" "1920x1080" 
            FALSE "Resolution" "Scale 720p" "1280x720" 
            FALSE "Resolution" "Scale 480p" "854x480" 
            FALSE "Resolution" "Scale 50%" "Half current dimensions" 
            FALSE "Resolution" "Custom Scale Width" "Enter specific width" 
            FALSE "Geometry" "Rotate 90 CW" "Clockwise" 
            FALSE "Geometry" "Rotate 90 CCW" "Counter-Clockwise" 
            FALSE "Geometry" "Flip Horizontal" "Mirror" 
            FALSE "Geometry" "Flip Vertical" "Upside down" 
            FALSE "Crop" "Crop 9:16 (Vertical)" "For Shorts/TikTok" 
            FALSE "Crop" "Crop 16:9 (Landscape)" "Standard Widescreen" 
            FALSE "Crop" "Crop Square 1:1" "Instagram/perfect square" 
            FALSE "Video" "Trim Start" "Skip first 10 seconds (or custom)" 
            FALSE "Video" "Trim End" "Limit duration to 60s (or custom)" 
            FALSE "Audio" "Mute Audio" "Remove sound track" 
            FALSE "Audio" "Normalize (R128)" "EBU R128 Standard" 
            FALSE "Audio" "Boost Volume (+6dB)" "Louder" 
            FALSE "Audio" "Downmix to Stereo" "Safely mix to 2ch" 
            FALSE "Audio" "Extract Audio (MP3)" "Save as MP3 only" 
            FALSE "Audio" "Extract Audio (WAV)" "Save as WAV only" 
            FALSE "Format" "Output as H.265" "High Efficiency (small size)" 
            FALSE "Format" "Output as WebM" "Web optimized (VP9)" 
            FALSE "Format" "Output as ProRes" "Editing Proxy/Master (MOV)" 
            FALSE "Format" "Output as GIF" "High Quality Animation" 
            FALSE "Other" "Clean Metadata" "Remove private info"
        )
        # Subtitles logic
        if [ -f "${1%.*}.srt" ]; then
            ZENITY_ARGS+=(FALSE "Subtitles" "Burn-in Subtitles" "Hardcode .srt file")
            ZENITY_ARGS+=(FALSE "Subtitles" "Mux Subtitles" "Soft-code (switchable)")
        fi
        
        # GPU detection
        GPU_CACHE="/tmp/scripts-sh-gpu-cache"
        if grep -q "nvenc" "$GPU_CACHE" 2>/dev/null; then ZENITY_ARGS+=(FALSE "GPU" "Use NVENC (Nvidia)" "Hardware Acceleration"); fi
        if grep -q "qsv" "$GPU_CACHE" 2>/dev/null; then ZENITY_ARGS+=(FALSE "GPU" "Use QSV (Intel)" "Hardware Acceleration"); fi
        if grep -q "vaapi" "$GPU_CACHE" 2>/dev/null; then ZENITY_ARGS+=(FALSE "GPU" "Use VAAPI (AMD/Intel)" "Hardware Acceleration"); fi

        # EXECUTE ZENITY
        # Capture stderr to debug log
        rm -f /tmp/zenity_debug_error.log
        CHOICES=$(zenity "${ZENITY_ARGS[@]}" --separator="|" 2> /tmp/zenity_debug_error.log)
        RET=$?
        
        # Check if Zenity failed (non-zero exit and empty output)
        if [ $RET -ne 0 ]; then
            # If cancelled (exit code 1), just exit
            if [ $RET -eq 1 ] && [ -z "$CHOICES" ]; then exit 0; fi
            
            echo "Zenity Failed! Exit Code: $RET" >> /tmp/zenity_debug_error.log
            zenity --error --text="Menu failed to open. Debug log saved to /tmp/zenity_debug_error.log\n\nPossible cause: $(head -n 1 /tmp/zenity_debug_error.log)"
            exit 1
        fi
        
        [ -z "$CHOICES" ] && continue # Back to Launchpad
        
        # GENERATE SMART SLUG FOR PRE-FILL
        SLUG=$(echo "$CHOICES" | sed 's/Speed //g; s/ (Fast)//g; s/ (Super Fast)//g; s/ (Slow)//g; s/Scale //g; s/Output as //g; s/ (R128)//g; s/ Audio//g; s/ (Vertical)//g; s/ (Landscape)//g; s/ Square 1:1//g; s/Rotate //g; s/Flip //g; s/Subtitles//g; s/Burn-in //g; s/Mux //g; s/Use //g; s/ (Nvidia)//g; s/ (Intel)//g; s/ (AMD\/Intel)//g; s/|/_/g; s/ //g' | tr '[:upper:]' '[:lower:]')
        
        # PROMPT TO SAVE AS FAVORITE
        if zenity --question --title="Save as Favorite?" --text="Would you like to save this configuration as a permanent favorite?" --ok-label="Save" --cancel-label="Just Run Once"; then
            PNAME=$(zenity --entry --title="Save Favorite" --text="Enter a name for this recipe:" --entry-text="$SLUG")
            if [ -n "$PNAME" ]; then
                echo "$PNAME|$CHOICES" >> "$PRESET_FILE"
                zenity --notification --text="Saved as '$PNAME'!"
            fi
        fi
        break

    elif grep -q "^$PICKED|" "$PRESET_FILE"; then
        # Load from Presets
        CHOICES=$(grep "^$PICKED|" "$PRESET_FILE" | head -n 1 | cut -d'|' -f2-)
        break

    else
        # Must be a History Item
        ACT=$(zenity --list --title="History Item" --text="Settings: $(echo "$PICKED" | sed 's/|/, /g')" \
            --column="Action" "▶️ Run Now" "⭐ Star as Favorite" "❌ Delete")
        
        if [ "$ACT" == "▶️ Run Now" ]; then
            CHOICES="$PICKED"
            break
        elif [ "$ACT" == "⭐ Star as Favorite" ]; then
            PNAME=$(zenity --entry --title="Save Favorite" --text="Name for this recipe:")
            if [ -n "$PNAME" ]; then
                echo "$PNAME|$PICKED" >> "$PRESET_FILE"
                zenity --notification --text="Saved to favorites!"
            fi
            continue # Back to Launchpad to see the new Star
        elif [ "$ACT" == "❌ Delete" ]; then
            # Safe delete from history
            grep -vF "$PICKED" "$HISTORY_FILE" > "${HISTORY_FILE}.tmp"
            mv "${HISTORY_FILE}.tmp" "$HISTORY_FILE"
            continue
        fi
    fi
done

# --- AUTOMATED HISTORY TRACKING ---
# 1. De-duplicate: If choices match the most recent entry, do nothing.
RECENT=$(head -n 1 "$HISTORY_FILE")
if [ "$CHOICES" != "$RECENT" ]; then
    # 2. Add to top
    echo "$CHOICES" | cat - "$HISTORY_FILE" > "${HISTORY_FILE}.tmp"
    # 3. Keep last 15
    head -n 15 "${HISTORY_FILE}.tmp" > "$HISTORY_FILE"
    rm "${HISTORY_FILE}.tmp"
fi

# 2. Logic & Prompts
VF_CHAIN=""
AF_CHAIN=""
INPUT_OPTS=""
VCODEC_OPTS="-c:v libx264 -crf 23 -preset medium"
ACODEC_OPTS="-c:a aac -b:a 192k"
GLOBAL_OPTS="-movflags +faststart"
EXT="mp4"
TAG=""
FILTER_COUNT=0
FPS_OVERRIDE=""
USE_GPU=false
GPU_TYPE=""

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
if [[ "$CHOICES" == *"Trim Start"* ]]; then
    START=$(zenity --entry --title="Trim Start" --text="Start time (seconds or hh:mm:ss):" --entry-text="00:00:10")
    if [ -n "$START" ]; then INPUT_OPTS="$INPUT_OPTS -ss $START"; TAG="${TAG}_cut"; ((FILTER_COUNT++)); fi
fi
if [[ "$CHOICES" == *"Trim End"* ]]; then
    DUR=$(zenity --entry --title="Trim Duration" --text="Duration to keep (seconds or hh:mm:ss):" --entry-text="00:01:00")
    if [ -n "$DUR" ]; then INPUT_OPTS="$INPUT_OPTS -t $DUR"; TAG="${TAG}_len"; ((FILTER_COUNT++)); fi
fi

# --- SPEED (PTS & FPS) ---
SPEED_VAL=""
if [[ "$CHOICES" == *"Speed 2x"* ]]; then SPEED_VAL="2.0"; PTS="0.5"; ATEMPO="2.0"; TAG="${TAG}_2x"; fi
if [[ "$CHOICES" == *"Speed 4x"* ]]; then SPEED_VAL="4.0"; PTS="0.25"; ATEMPO="2.0,atempo=2.0"; TAG="${TAG}_4x"; fi
if [[ "$CHOICES" == *"Speed 0.5x"* ]]; then SPEED_VAL="0.5"; PTS="2.0"; ATEMPO="0.5"; TAG="${TAG}_0.5x"; fi

if [ -n "$SPEED_VAL" ]; then
    add_vf "setpts=${PTS}*PTS"
    # Note: FPS_OVERRIDE will be calculated per-file in the loop
    if [[ "$CHOICES" != *"Mute"* && "$CHOICES" != *"Extract"* ]]; then
         add_af "$ATEMPO"
    fi
fi

# --- CROP ---
if [[ "$CHOICES" == *"Crop 9:16"* ]]; then add_vf "crop=ih*(9/16):ih:(iw-ow)/2:0"; TAG="${TAG}_9x16"; fi
if [[ "$CHOICES" == *"Crop 16:9"* ]]; then add_vf "crop=iw:iw*9/16:0:(ih-ow)/2"; TAG="${TAG}_16x9"; fi
if [[ "$CHOICES" == *"Crop Square"* ]]; then add_vf "crop=min(iw\,ih):min(iw\,ih):(iw-ow)/2:(ih-oh)/2"; TAG="${TAG}_sq"; fi

# --- SCALE ---
SCALE_W=""
if [[ "$CHOICES" == *"Scale 4K"* ]]; then SCALE_W="3840"; TAG="${TAG}_4k"; fi
if [[ "$CHOICES" == *"Scale 1080p"* ]]; then SCALE_W="1920"; TAG="${TAG}_1080p"; fi
if [[ "$CHOICES" == *"Scale 720p"* ]]; then SCALE_W="1280"; TAG="${TAG}_720p"; fi
if [[ "$CHOICES" == *"Scale 480p"* ]]; then SCALE_W="854"; TAG="${TAG}_480p"; fi
if [[ "$CHOICES" == *"Scale 50%"* ]]; then SCALE_W="iw*0.5"; TAG="${TAG}_half"; fi
if [[ "$CHOICES" == *"Custom Scale Width"* ]]; then
    W=$(zenity --entry --title="Scale Width" --text="Target Width (px):" --entry-text="1280")
    if [ -n "$W" ]; then SCALE_W="$W"; TAG="${TAG}_${W}w"; fi
fi

if [ -n "$SCALE_W" ]; then
    add_vf "scale=${SCALE_W}:-2"
fi

# --- GEOMETRY ---
if [[ "$CHOICES" == *"Rotate 90 CW"* ]]; then add_vf "transpose=1"; TAG="${TAG}_90cw"; fi
if [[ "$CHOICES" == *"Rotate 90 CCW"* ]]; then add_vf "transpose=2"; TAG="${TAG}_90ccw"; fi
if [[ "$CHOICES" == *"Flip Horizontal"* ]]; then add_vf "hflip"; TAG="${TAG}_flipH"; fi
if [[ "$CHOICES" == *"Flip Vertical"* ]]; then add_vf "vflip"; TAG="${TAG}_flipV"; fi

# --- AUDIO ---
MUTE_AUDIO=false
if [[ "$CHOICES" == *"Mute Audio"* ]]; then 
    MUTE_AUDIO=true
    TAG="${TAG}_mute"
else
    if [[ "$CHOICES" == *"Downmix to Stereo"* ]]; then ACODEC_OPTS="$ACODEC_OPTS -ac 2"; TAG="${TAG}_stereo"; fi
    if [[ "$CHOICES" == *"Normalize"* ]]; then add_af "loudnorm=I=-23:LRA=7:TP=-1.5"; TAG="${TAG}_norm"; fi
    if [[ "$CHOICES" == *"Boost Volume"* ]]; then add_af "volume=6dB"; TAG="${TAG}_boost"; fi
fi

# --- GPU LOGIC ---
if [[ "$CHOICES" == *"Use NVENC"* ]]; then USE_GPU=true; GPU_TYPE="nvenc"; TAG="${TAG}_nvenc"; fi
if [[ "$CHOICES" == *"Use QSV"* ]]; then USE_GPU=true; GPU_TYPE="qsv"; TAG="${TAG}_qsv"; fi
if [[ "$CHOICES" == *"Use VAAPI"* ]]; then USE_GPU=true; GPU_TYPE="vaapi"; TAG="${TAG}_vaapi"; fi

# --- FORMAT OVERRIDES ---
IS_audio_only=false
IS_gif=false

if [[ "$CHOICES" == *"Output as H.265"* ]]; then 
    if [ "$USE_GPU" = true ]; then
        if [ "$GPU_TYPE" = "nvenc" ]; then VCODEC_OPTS="-c:v hevc_nvenc -preset slow -rc vbr -cq 28 -pix_fmt yuv420p"; fi
        if [ "$GPU_TYPE" = "qsv" ]; then VCODEC_OPTS="-c:v hevc_qsv -load_plugin hevc_hw -preset medium -global_quality 25 -pix_fmt yuv420p"; fi
        if [ "$GPU_TYPE" = "vaapi" ]; then VCODEC_OPTS="-c:v hevc_vaapi -rc_mode CQP -qp 28"; GLOBAL_OPTS="$GLOBAL_OPTS -vaapi_device /dev/dri/renderD128 -vf format=nv12,hwupload"; fi # Complex VAAPI chain overrides standard VF
    else
        VCODEC_OPTS="-c:v libx265 -crf 28 -preset medium"
    fi
    ACODEC_OPTS="-c:a aac -b:a 128k"
    TAG="${TAG}_h265"
elif [[ "$CHOICES" == *"Output as WebM"* ]]; then 
    VCODEC_OPTS="-c:v libvpx-vp9 -b:v 0 -crf 30"
    ACODEC_OPTS="-c:a libopus"
    EXT="webm"
    TAG="${TAG}_vp9"
elif [[ "$CHOICES" == *"Output as ProRes"* ]]; then 
    VCODEC_OPTS="-c:v prores_ks -profile:v 3 -vendor apl0 -bits_per_mb 8000 -pix_fmt yuv422p10le"
    ACODEC_OPTS="-c:a pcm_s16le"
    EXT="mov"
    TAG="${TAG}_prores"
elif [[ "$CHOICES" == *"Extract Audio (MP3)"* ]]; then
    VCODEC_OPTS="-vn"
    ACODEC_OPTS="-c:a libmp3lame -q:a 2"
    EXT="mp3"
    TAG="${TAG}_audio"
    IS_audio_only=true
elif [[ "$CHOICES" == *"Extract Audio (WAV)"* ]]; then
    VCODEC_OPTS="-vn"
    ACODEC_OPTS="-c:a pcm_s16le"
    EXT="wav"
    TAG="${TAG}_audio"
    IS_audio_only=true
elif [[ "$CHOICES" == *"Output as GIF"* ]]; then
    IS_gif=true
    EXT="gif"
else
    # Default H.264
    if [ "$USE_GPU" = true ]; then
        if [ "$GPU_TYPE" = "nvenc" ]; then VCODEC_OPTS="-c:v h264_nvenc -preset slow -rc vbr -cq 23 -pix_fmt yuv420p"; fi
        if [ "$GPU_TYPE" = "qsv" ]; then VCODEC_OPTS="-c:v h264_qsv -preset medium -global_quality 23 -pix_fmt yuv420p"; fi
        if [ "$GPU_TYPE" = "vaapi" ]; then VCODEC_OPTS="-c:v h264_vaapi -rc_mode CQP -qp 23"; GLOBAL_OPTS="$GLOBAL_OPTS -vaapi_device /dev/dri/renderD128 -vf format=nv12,hwupload"; fi
    fi
fi

# --- SUBTITLES ---
HAS_SUBS=false
SUB_EXT=""
if [[ "$CHOICES" == *"Burn-in Subtitles"* ]]; then HAS_SUBS=true; SUB_TYPE="burn"; TAG="${TAG}_sub"; fi
if [[ "$CHOICES" == *"Mux Subtitles"* ]]; then HAS_SUBS=true; SUB_TYPE="mux"; TAG="${TAG}_sub"; fi

# --- METADATA ---
if [[ "$CHOICES" == *"Clean Metadata"* ]]; then
    GLOBAL_OPTS="$GLOBAL_OPTS -map_metadata -1"
fi

# --- SMART FILENAMING ---
if [ "$FILTER_COUNT" -ge 3 ]; then
    TAG="_UniversalEdit"
fi
if [ -z "$TAG" ]; then TAG="_edit"; fi

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
    if [ "$MUTE_AUDIO" = true ]; then
        CURRENT_ACORE="-an"
    else
        if [ -n "$AF_CHAIN" ] && [ "$IS_audio_only" = false ]; then 
            CURRENT_ACORE="-af \"$AF_CHAIN\" $ACODEC_OPTS"
        else
            CURRENT_ACORE="$ACODEC_OPTS"
        fi
    fi
    
    OUT_FILE="${f%.*}${FILE_TAG}.${EXT}"
    
    echo "# Processing $f..."
    
    if [ "$IS_gif" = true ]; then
        PALETTE="/tmp/palette_$(basename "$f").png"
        echo "Generating palette..." >> "$LOG_FILE"
        CMD1="ffmpeg -y $INPUT_OPTS -i \"$f\" -vf \"$FULL_VF,palettegen\" \"$PALETTE\""
        echo "$CMD1" >> "$LOG_FILE"
        eval $CMD1
        
        echo "Creating GIF..." >> "$LOG_FILE"
        CMD2="ffmpeg -y $INPUT_OPTS -i \"$f\" -i \"$PALETTE\" -lavfi \"$FULL_VF [x]; [x][1:v] paletteuse\" $FPS_ARG \"$OUT_FILE\""
        echo "$CMD2" >> "$LOG_FILE"
        eval $CMD2
        rm "$PALETTE"

    else
        # Standard Video/Audio
        # Note: SUB_MAPPING has -i inside it, so it essentially adds a second input if muxing
        CMD="ffmpeg -y $INPUT_OPTS -i \"$f\" $SUB_MAPPING $CMD_FILTERS $VCODEC_OPTS $CURRENT_ACORE $FPS_ARG $GLOBAL_OPTS \"$OUT_FILE\""
        echo "$CMD" >> "$LOG_FILE"
        eval $CMD
    fi
    
    STATUS=$?
    
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
