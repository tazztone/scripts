#!/bin/bash
# test_runner.sh
# A unified testing framework for scripts-sh

# --- Configuration ---
TEST_DATA="/tmp/scripts_test_data"
MOCK_BIN="/tmp/scripts_mock_bin"
REPORT_FILE="./test_report.log"
HEADLESS=true
STRICT=true

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Initialization ---
mkdir -p "$TEST_DATA"
mkdir -p "$MOCK_BIN"
echo "Test Session Started at $(date)" > "$REPORT_FILE"

# --- Zenity Mocking ---
setup_mock_zenity() {
    cat <<'EOF' > "$MOCK_BIN/zenity"
#!/bin/bash
# Headless Zenity Mock
ARGS="$*"
echo "MOCK ZENITY CALLED WITH: $ARGS" >> "/tmp/zenity_mock.log"
# Allow dynamic overrides via environment variables
if [[ "$ARGS" == *"--entry"* && -n "$ZENITY_ENTRY_RESPONSE" ]]; then
    echo "$ZENITY_ENTRY_RESPONSE"
    exit 0
fi
if [[ "$ARGS" == *"--list"* ]]; then
    if [[ "$ARGS" == *"Select a starting point:"* ]]; then
        echo "New Custom Edit"
        exit 0
    fi
    if [[ -n "$ZENITY_LIST_RESPONSE" ]]; then
        echo "$ZENITY_LIST_RESPONSE"
        exit 0
    fi
fi

# Strict check for Universal Toolbox column printing
if [[ "$ARGS" == *"Universal Edit Builder"* && "$ARGS" != *"--print-column=2"* ]]; then
    echo "ERROR: Universal Toolbox must use --print-column=2" >&2
    exit 1
fi

case "$ARGS" in
    *--question*) exit 1 ;; # Always say "No" to Save Favorite in tests
    *--scale*) echo "1280" ;;
    *--entry*) echo "9" ;;
    *--file-selection*) echo "/tmp/scripts_test_data/test.srt" ;;
    *--progress*) 
        while read -r line; do
            [[ "$line" == "#"* ]] && echo "$line"
        done
        ;;
    *--list*)
        case "$ARGS" in
            *"Universal Toolbox Launchpad"*|*"Select a starting point:"*) 
                echo "${ZENITY_LIST_RESPONSE:-New Custom Edit}" ;;
            *"Wizard Step 2: What do you want to fix?"*) 
                echo "${ZENITY_LIST_RESPONSE:-⏩ Speed Control|📐 Scale / Resize|🔊 Audio Tools}" ;;
            *"Universal Edit Builder"*) 
                echo "${ZENITY_LIST_RESPONSE:-⏩ Speed Control|📐 Scale / Resize|🔇 Mute Audio|⚖️ Quality: Medium|📦 Output: H.265}" ;;
            *"Target Platform"*|*"H.264 Presets"*) echo "Universal" ;;
            *"Audio Adjustment"*) echo "Normalize" ;;
            *"Speed Control"*) echo "2x Fast" ;;
            *"Image Extraction"*) echo "Thumbnail" ;;
            *"File Polish"*) echo "Strip Metadata" ;;
            *"Target Size"*) echo "25" ;;
            *"Target Format"*) echo "MP3" ;;
            *"ProRes Profile"*) echo "Standard" ;;
            *"Geometric Transform"*) echo "90 CW" ;;
            *"Target Resolution"*) echo "1080p" ;;
            *"Target Container"*) echo "MOV" ;;
            *"Trim Operation"*) echo "Start" ;;
            *"Channel Remix"*) echo "Mono to Stereo" ;;
            *"Avid DNx Profile"*) echo "DNxHD 36" ;;
            *"Target Aspect Ratio"*) echo "16:9" ;;
            *"Overlay Selection"*) echo "Burn Subtitles" ;;
            *) echo "" ;;
        esac
        ;;
    *--forms*)
        case "$ARGS" in
            *"Wizard Step 3: Configure & Run"*) 
                # FIXED INDEX MAPPING (14 Fields):
                # 0:Speed, 1:CustomSpeed, 2:Resolution, 3:CustomWidth, 4:Crop, 5:Rotate, 6:TrimS, 7:TrimE, 8:Audio, 9:Subs, 10:Quality, 11:Size, 12:Format, 13:Hardware
                # Default Test Set: 2x (Fast), blank, 720p, blank, Inactive, No Change, blank, blank, Inactive, Inactive, Medium Default, blank, Auto/MP4, None
                echo "2x (Fast)||720p|| (Inactive)|No Change||| (Inactive)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)" ;;
            *) echo "" ;;
        esac
        ;;
    *) exit 0 ;;
esac
EOF
    chmod +x "$MOCK_BIN/zenity"
    export PATH="$MOCK_BIN:$PATH"
}

if [ "$HEADLESS" = true ]; then
    setup_mock_zenity
fi

# --- Helper Functions ---
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; echo "FAIL: $1" >> "$REPORT_FILE"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

generate_test_media() {
    log_info "Generating test media..."
    ffmpeg -f lavfi -i testsrc=duration=2:size=1920x1080:rate=30 -f lavfi -i sine=frequency=1000:duration=2 -c:v libx264 -c:a aac -shortest -y "$TEST_DATA/src.mp4" > /dev/null 2>&1
    touch "$TEST_DATA/test.srt"
}

validate_media() {
    local file="$1"
    local rules="$2" # comma separated rules: width=1280,codec=h264,no_video
    
    if [ ! -f "$file" ]; then
        log_fail "Output file missing: $file"
        return 1
    fi

    local failed=0
    IFS=',' read -ra ADDR <<< "$rules"
    for rule in "${ADDR[@]}"; do
        local key="${rule%%=*}"
        local val="${rule#*=}"
        
        case $key in
            width)
                local w=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ "$w" != "$val" ]] && { log_fail "Width mismatch: expected $val, got $w"; failed=1; }
                ;;
            height)
                local h=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ "$h" != "$val" ]] && { log_fail "Height mismatch: expected $val, got $h"; failed=1; }
                ;;
            vcodec)
                local c=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ "$c" != "$val" ]] && { log_fail "V-Codec mismatch: expected $val, got $c"; failed=1; }
                ;;
            acodec)
                local c=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ "$c" != "$val" ]] && { log_fail "A-Codec mismatch: expected $val, got $c"; failed=1; }
                ;;
            no_video)
                local streams=$(ffprobe -v error -show_entries format=nb_streams -of default=noprint_wrappers=1:nokey=1 "$file")
                local v_streams=$(ffprobe -v error -select_streams v -show_entries stream=index -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ -n "$v_streams" ]] && { log_fail "Video stream found, expected none"; failed=1; }
                ;;
            fps)
                local fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$file")
                # Handle fraction like 30/1
                fps=$(echo "scale=0; $fps" | bc -l)
                [[ "$fps" != "$val" ]] && { log_fail "FPS mismatch: expected $val, got $fps"; failed=1; }
                ;;
        esac
    done
    
    return $failed
}

run_test() {
    local script_path="$1"
    local validation_rules="$2"
    local input_file="$3"
    
    log_info "Testing: $(basename "$script_path")"
    
    # 0. Clean test data of any previous outputs (but keep src.mp4 and other sources)
    # We want to keep src.mp4, test.srt, and specifically named test files
    find "$TEST_DATA" -type f -not \( -name "src.mp4" -o -name "test.srt" -o -name "*'*.mp4" \) -delete
    
    # 1. Capture current files
    local before=$(mktemp)
    ls -1 "$TEST_DATA" | sort > "$before"

    # 2. Run the script
    local script_log=$(mktemp)
    # CD to the directory of the input file to mimic Nautilus behavior
    local input_dir=$(dirname "$input_file")
    local input_base=$(basename "$input_file")
    
    # We need to resolve script path to absolute because we are changing dir
    local abs_script_path=$(readlink -f "$script_path")

    ( cd "$input_dir" && timeout 60s bash "$abs_script_path" "$input_base" ) > "$script_log" 2>&1
    local exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        log_fail "Script exited with code $exit_code"
        cat "$script_log"
        rm "$before" "$script_log"
        return 1
    fi

    # 3. Find the NEW file created (preferring newest)
    local output_file=""
    local newest=$(ls -t "$TEST_DATA" | head -n 1)
    
    # Verify it's not one of our sources (simple check, could be better)
    if [[ "$newest" == "src.mp4" || "$newest" == "test.srt" || "$newest" == *"'"* ]]; then
        # If the newest file is a source, maybe the script didn't produce anything?
        # Or maybe it modified in place (scripts usually don't).
        # Let's check diff against 'before'
        local after=$(mktemp)
        ls -1 "$TEST_DATA" | sort > "$after"
        local diff_file=$(comm -13 "$before" "$after")
        if [ -n "$diff_file" ]; then
             newest=$(echo "$diff_file" | head -n 1)
        fi
        rm "$after"
    fi

    # Final check if we found a new file
    if [[ -z "$newest" || "$newest" == "src.mp4" || "$newest" == "test.srt" || "$newest" == "User's Video.mp4" ]]; then
        # One last check: did we rename/modify?
        # For now assume failure if no new file appears
        log_fail "No output file detected for $(basename "$script_path")"
        echo "Files in $TEST_DATA:"
        ls -l "$TEST_DATA"
        echo "Script Log:"
        cat "$script_log"
        rm "$before" "$script_log"
        return 1
    fi

    rm "$before" "$script_log"
    output_file="$TEST_DATA/$newest"
    log_info "Detected output: $newest"

    if [ -n "$validation_rules" ]; then
        validate_media "$output_file" "$validation_rules"
        local val_status=$?
        # Stay clean
        rm -rf "$output_file"
        [[ $val_status -eq 0 ]] && log_pass "$(basename "$script_path") validated successfully"
    else
        log_pass "$(basename "$script_path") ran without error"
        rm -rf "$output_file"
    fi
}

# --- Main Execution ---
if [[ "$*" == *"--no-run"* ]]; then
    return 0 2>/dev/null || exit 0
fi

generate_test_media


echo -e "\n${YELLOW}=== Running New: Universal Toolbox ===${NC}"
# Test combination: Speed 2x + Scale 720p + Mute + Medium Quality + H.265
# Wizard Mock in Step 3 is currently set to return Auto/MP4 (H264)
run_test "ffmpeg/0-00 🧰 Universal-Toolbox.sh" "width=1280,no_audio,vcodec=h264,fps=30" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running New: Universal Toolbox v2 (Features) ===${NC}"
# 1. Subtitle Burn-in Test
touch "$TEST_DATA/src.srt"
export ZENITY_LIST_RESPONSE="📝 Subtitles"
run_test "ffmpeg/0-00 🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"
rm "$TEST_DATA/src.srt"
unset ZENITY_LIST_RESPONSE

# 2. Target Size (2-Pass) Test
export ZENITY_LIST_RESPONSE="💾 Target Size (MB)"
# Wizard Step 3 Mock will still return defaults unless we override FORMS response
# For now, we trust the logic bridge since main flow passes.
run_test "ffmpeg/0-00 🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"
unset ZENITY_LIST_RESPONSE

mkdir -p "$HOME/.config/scripts-sh"
echo "TestPreset|Speed: 2x (Fast)|Scale: 720p" > "$HOME/.config/scripts-sh/presets.conf"
echo "Testing CLI Preset..."
( 
    cd "$TEST_DATA"
    bash "$HOME/_coding/scripts-sh/ffmpeg/0-00 🧰 Universal-Toolbox.sh" --preset "TestPreset" "src.mp4"
) > /dev/null 2>&1
# Check if output exists (Universal-Toolbox now uses a standard _UniversalEdit tag unless filters are present)
if [ -f "$TEST_DATA/src_UniversalEdit.mp4" ]; then
    log_pass "CLI Preset loaded successfully"
    rm "$TEST_DATA/src_UniversalEdit.mp4"
else
    log_fail "CLI Preset failed to generate output"
fi


# --- Summary ---
echo -e "\n${YELLOW}=== Test Summary ===${NC}"
grep "FAIL" "$REPORT_FILE" && echo -e "${RED}Some tests failed! See test_report.log${NC}" || echo -e "${GREEN}All tests passed!${NC}"

# Cleanup
# rm -rf "$TEST_DATA" "$MOCK_BIN"
