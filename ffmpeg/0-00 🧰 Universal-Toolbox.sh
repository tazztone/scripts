#!/bin/bash
# Universal FFmpeg Toolbox
# Combine multiple operations (Speed, Scale, Crop, Audio, Format) in one pass.

# Function to get video duration
get_duration() {
    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$1" | cut -d. -f1
}

# 1. Main Menu Selection (Checklist)
CHOICES=$(zenity --list --checklist --width=600 --height=600 \
    --title="Universal FFmpeg Toolbox" --print-column=3 \
    --column="Pick" --column="Category" --column="Option" --column="Description" \
    FALSE "Speed" "Speed 2x (Fast)" "Double speed (50% duration)" \
    FALSE "Speed" "Speed 4x (Super Fast)" "Quadruple speed (25% duration)" \
    FALSE "Speed" "Speed 0.5x (Slow)" "Half speed (2x duration)" \
    FALSE "Resolution" "Scale 4K" "3840x2160" \
    FALSE "Resolution" "Scale 1080p" "1920x1080" \
    FALSE "Resolution" "Scale 720p" "1280x720" \
    FALSE "Resolution" "Scale 480p" "854x480" \
    FALSE "Resolution" "Scale 50%" "Half current dimensions" \
    FALSE "Resolution" "Custom Scale Width" "Enter specific width" \
    FALSE "Geometry" "Rotate 90 CW" "Clockwise" \
    FALSE "Geometry" "Rotate 90 CCW" "Counter-Clockwise" \
    FALSE "Geometry" "Flip Horizontal" "Mirror" \
    FALSE "Geometry" "Flip Vertical" "Upside down" \
    FALSE "Crop" "Crop 9:16 (Vertical)" "For Shorts/TikTok" \
    FALSE "Crop" "Crop 16:9 (Landscape)" "Standard Widescreen" \
    FALSE "Crop" "Crop Square 1:1" "Instagram/perfect square" \
    FALSE "Video" "Trim Start" "Skip first 10 seconds (or custom)" \
    FALSE "Video" "Trim End" "Limit duration to 60s (or custom)" \
    FALSE "Audio" "Mute Audio" "Remove sound track" \
    FALSE "Audio" "Normalize (R128)" "EBU R128 Standard" \
    FALSE "Audio" "Boost Volume (+6dB)" "Louder" \
    FALSE "Audio" "Mix to Mono" "Combine channels" \
    FALSE "Audio" "Extract Audio (MP3)" "Save as MP3 only" \
    FALSE "Audio" "Extract Audio (WAV)" "Save as WAV only" \
    FALSE "Format" "Output as H.265" "High Efficiency (small size)" \
    FALSE "Format" "Output as WebM" "Web optimized (VP9)" \
    FALSE "Format" "Output as ProRes" "Editing Proxy/Master (MOV)" \
    FALSE "Format" "Output as GIF" "High Quality Animation" \
    FALSE "Other" "Clean Metadata" "Remove private info" \
    --separator="|")

if [ -z "$CHOICES" ]; then exit; fi

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
    if [[ "$CHOICES" == *"Mix to Mono"* ]]; then ACODEC_OPTS="$ACODEC_OPTS -ac 1"; TAG="${TAG}_mono"; fi
    if [[ "$CHOICES" == *"Normalize"* ]]; then add_af "loudnorm=I=-23:LRA=7:TP=-1.5"; TAG="${TAG}_norm"; fi
    if [[ "$CHOICES" == *"Boost Volume"* ]]; then add_af "volume=6dB"; TAG="${TAG}_boost"; fi
fi

# --- FORMAT OVERRIDES ---
IS_audio_only=false
IS_gif=false

if [[ "$CHOICES" == *"Output as H.265"* ]]; then 
    VCODEC_OPTS="-c:v libx265 -crf 28 -preset medium"
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
fi

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

    CMD_FILTERS=""
    if [ -n "$VF_CHAIN" ]; then CMD_FILTERS="-vf \"$VF_CHAIN\""; fi
    
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
        CMD1="ffmpeg -y $INPUT_OPTS -i \"$f\" -vf \"$VF_CHAIN,palettegen\" \"$PALETTE\""
        echo "$CMD1" >> "$LOG_FILE"
        eval $CMD1
        
        echo "Creating GIF..." >> "$LOG_FILE"
        CMD2="ffmpeg -y $INPUT_OPTS -i \"$f\" -i \"$PALETTE\" -lavfi \"$VF_CHAIN [x]; [x][1:v] paletteuse\" $FPS_ARG \"$OUT_FILE\""
        echo "$CMD2" >> "$LOG_FILE"
        eval $CMD2
        rm "$PALETTE"
    else
        # Standard Video/Audio
        CMD="ffmpeg -y $INPUT_OPTS -i \"$f\" $CMD_FILTERS $VCODEC_OPTS $CURRENT_ACORE $FPS_ARG $GLOBAL_OPTS \"$OUT_FILE\""
        echo "$CMD" >> "$LOG_FILE"
        eval $CMD
    fi
    
    STATUS=$?
    if [ $STATUS -ne 0 ]; then
        echo "ERROR: Failed on file $f" >> "$LOG_FILE"
        zenity --error --text="FFmpeg failed on $(basename "$f").\nCheck logs details." --ok-label="Close" --extra-button="Details" --title="Error" < "$LOG_FILE"
    fi
done
) | zenity --progress --title="Universal Toolbox" --pulsate --auto-close

zenity --notification --text="Universal Toolbox Finished!"
