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
case "$*" in
    *--scale*) echo "1280" ;;
    *--entry*) echo "9" ;;
    *--list*|"Convert Format"*) echo "MP4" ;;
    *--list*|"Extract Audio"*) echo "MP3" ;;
    *--file-selection*) echo "/tmp/scripts_test_data/test.srt" ;;
    *--progress*) 
        while read -r line; do
            # Consume progress updates silently or echo to log
            # echo "Progress: $line" >> /tmp/zenity_mock.log
            [[ "$line" == "#"* ]] && echo "$line"
        done
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
    
    # 0. Clean test data of any previous outputs (but keep src.mp4)
    find "$TEST_DATA" -type f ! -name "src.mp4" ! -name "test.srt" -delete
    
    # 1. Capture current files
    local before=$(mktemp)
    ls -1 "$TEST_DATA" | sort > "$before"

    # 2. Run the script
    local script_log=$(mktemp)
    bash "$script_path" "$input_file" > "$script_log" 2>&1
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
    
    # Verify it's not one of our sources
    if [[ "$newest" == "src.mp4" || "$newest" == "test.srt" ]]; then
        # Try second newest if newest is source
        newest=$(ls -t "$TEST_DATA" | sed -n '2p')
    fi

    if [[ -z "$newest" || "$newest" == "src.mp4" || "$newest" == "test.srt" ]]; then
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

echo -e "\n${YELLOW}=== Running Category: Web & Social ===${NC}"
run_test "ffmpeg/1-01-H264-Universal.sh" "vcodec=h264,acodec=aac" "$TEST_DATA/src.mp4"
run_test "ffmpeg/1-06-GIF-HighQual.sh" "" "$TEST_DATA/src.mp4"
run_test "ffmpeg/1-11-Custom-Size-MB.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Category: Editing Pro ===${NC}"
run_test "ffmpeg/2-01-ProRes-422.sh" "vcodec=prores" "$TEST_DATA/src.mp4"
run_test "ffmpeg/2-06-Rewrap-MOV.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Category: Audio Ops ===${NC}"
run_test "ffmpeg/3-01-Extract-MP3-V0.sh" "no_video,acodec=mp3" "$TEST_DATA/src.mp4"
run_test "ffmpeg/3-02-Extract-WAV.sh" "no_video,acodec=pcm_s16le" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Category: Geometry & Time ===${NC}"
run_test "ffmpeg/4-01-Scale-50p.sh" "width=960,height=540" "$TEST_DATA/src.mp4"
run_test "ffmpeg/4-04-Rotate-90-CW.sh" "width=1080,height=1920" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Category: Utils ===${NC}"
run_test "ffmpeg/5-01-Extract-Thumb-50p.sh" "" "$TEST_DATA/src.mp4"
run_test "ffmpeg/5-05-Remove-Metadata.sh" "" "$TEST_DATA/src.mp4"

# --- Summary ---
echo -e "\n${YELLOW}=== Test Summary ===${NC}"
grep "FAIL" "$REPORT_FILE" && echo -e "${RED}Some tests failed! See test_report.log${NC}" || echo -e "${GREEN}All tests passed!${NC}"

# Cleanup
# rm -rf "$TEST_DATA" "$MOCK_BIN"
