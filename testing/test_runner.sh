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
# Allow dynamic overrides via environment variables
if [[ "$ARGS" == *"--entry"* && -n "$ZENITY_ENTRY_RESPONSE" ]]; then
    echo "$ZENITY_ENTRY_RESPONSE"
    exit 0
fi
if [[ "$ARGS" == *"--list"* && -n "$ZENITY_LIST_RESPONSE" ]]; then
    echo "$ZENITY_LIST_RESPONSE"
    exit 0
fi

case "$ARGS" in
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

    ( cd "$input_dir" && bash "$abs_script_path" "$input_base" ) > "$script_log" 2>&1
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
generate_test_media

echo -e "\n${YELLOW}=== Running Fix Verification: Special Characters ===${NC}"
# Create a file with single quote
SPECIAL_FILE="$TEST_DATA/User's Video.mp4"
cp "$TEST_DATA/src.mp4" "$SPECIAL_FILE"
# Test 5-04 Concat (Pass only one file to test the internal list generation logic)
run_test "ffmpeg/5-04 🔗 Concat-Join-Videos.sh" "" "$SPECIAL_FILE"

echo -e "\n${YELLOW}=== Running Fix Verification: Speed Limits ===${NC}"
export ZENITY_LIST_RESPONSE="4x Fast"
run_test "ffmpeg/4-05 ⏩ Video-Speed-Fast-Slow-Motion.sh" "vcodec=h264" "$TEST_DATA/src.mp4"
unset ZENITY_LIST_RESPONSE

echo -e "\n${YELLOW}=== Running Category: Web & Social ===${NC}"
run_test "ffmpeg/1-01 🌐 H264-Social-Web-Presets.sh" "vcodec=h264,acodec=aac" "$TEST_DATA/src.mp4"
run_test "ffmpeg/1-05 🎞️ GIF-Palette-Optimized.sh" "" "$TEST_DATA/src.mp4"
run_test "ffmpeg/1-03 ⚖️ H264-Compress-to-Target-Size.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Category: Editing Pro ===${NC}"
run_test "ffmpeg/2-01 🍎 ProRes-Intermediate-Transcoder.sh" "vcodec=prores" "$TEST_DATA/src.mp4"
run_test "ffmpeg/2-07 🎁 Container-Remux-Rewrap.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Category: Audio Ops ===${NC}"
run_test "ffmpeg/3-01 🔊 Audio-Format-Converter.sh" "no_video,acodec=mp3" "$TEST_DATA/src.mp4"
run_test "ffmpeg/3-02 🎚️ Audio-Normalize-Boost-Mute.sh" "acodec=aac" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Category: Geometry & Time ===${NC}"
run_test "ffmpeg/4-01 📐 Resolution-Smart-Scaler.sh" "width=1920,height=1080" "$TEST_DATA/src.mp4" # Mocked to 1080p
run_test "ffmpeg/4-02 🔄 Geometry-Rotate-Flip.sh" "width=1080,height=1920" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Category: Utils ===${NC}"
run_test "ffmpeg/5-01 🖼️ Image-Extract-Thumb-Sequence.sh" "" "$TEST_DATA/src.mp4"
run_test "ffmpeg/5-05 🧹 Metadata-Privacy-Web-Optimize.sh" "" "$TEST_DATA/src.mp4"

# --- Summary ---
echo -e "\n${YELLOW}=== Test Summary ===${NC}"
grep "FAIL" "$REPORT_FILE" && echo -e "${RED}Some tests failed! See test_report.log${NC}" || echo -e "${GREEN}All tests passed!${NC}"

# Cleanup
# rm -rf "$TEST_DATA" "$MOCK_BIN"
