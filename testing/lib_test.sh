#!/bin/bash
# testing/lib_test.sh
# Shared testing utilities for all toolboxes

# --- Configuration ---
TEST_DATA="/tmp/scripts_test_data"
MOCK_BIN="/tmp/scripts_mock_bin"
REPORT_FILE="testing/output/test_report.log"
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
mkdir -p "testing/output"

# --- Zenity Mocking ---
setup_mock_zenity() {
    cat <<'EOF' > "$MOCK_BIN/zenity"
#!/bin/bash
# Headless Zenity Mock
ARGS="$*"
echo "MOCK ZENITY CALLED WITH: $ARGS" >> "/tmp/zenity_mock.log"

# 1. Handle Response Overrides (Queue based)
RESPONSE_QUEUE="/tmp/zenity_responses"
if [ -s "$RESPONSE_QUEUE" ]; then
    RESPONSE=$(head -n 1 "$RESPONSE_QUEUE")
    sed -i '1d' "$RESPONSE_QUEUE"
    echo "$RESPONSE"
    exit 0
fi

# 2. Handle Entry Response
if [[ "$ARGS" == *"--entry"* && -n "$ZENITY_ENTRY_RESPONSE" ]]; then
    echo "$ZENITY_ENTRY_RESPONSE"
    exit 0
fi

# 3. Handle Checklist
if [[ "$ARGS" == *"--checklist"* ]]; then
    echo "${ZENITY_LIST_RESPONSE:-Action}"
    exit 0
fi

# 4. Handle Forms
if [[ "$ARGS" == *"--forms"* ]]; then
    # Default behavior if queue is empty
    echo ""
    exit 0
fi

# 5. Handle Simple Lists
if [[ "$ARGS" == *"--list"* ]]; then
    echo "${ZENITY_LIST_RESPONSE:-New Custom Edit}"
    exit 0
fi

case "$ARGS" in
    *--question*) 
        if [[ "$ZENITY_QUESTION_RESPONSE" == "YES" ]]; then exit 0; else exit 1; fi ;;
    *--scale*) echo "1280" ;;
    *--entry*) echo "9" ;;
    *--file-selection*) echo "/tmp/scripts_test_data/test.srt" ;;
    *--progress*) 
        while read -r line; do
            [[ "$line" == "#"* ]] && echo "$line"
        done
        ;;
    *) exit 0 ;;
esac
EOF
    chmod +x "$MOCK_BIN/zenity"
    export PATH="$MOCK_BIN:$PATH"
}

# --- Helper Functions ---
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; echo "FAIL: $1" >> "$REPORT_FILE"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

generate_test_media() {
    if [ ! -f "$TEST_DATA/src.mp4" ]; then
        log_info "Generating test video media..."
        ffmpeg -f lavfi -i testsrc=duration=2:size=1920x1080:rate=30 -f lavfi -i sine=frequency=1000:duration=2 -c:v libx264 -c:a aac -shortest -y "$TEST_DATA/src.mp4" > /dev/null 2>&1
    fi
    if [ ! -f "$TEST_DATA/src.jpg" ]; then
        log_info "Generating test image media..."
        if command -v magick &>/dev/null; then
            magick -size 1920x1080 canvas:red "$TEST_DATA/src.jpg"
        fi
    fi
    touch "$TEST_DATA/test.srt"
}

validate_media() {
    local file="$1"
    local rules="$2" 
    
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
                local v_streams=$(ffprobe -v error -select_streams v -show_entries stream=index -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ -n "$v_streams" ]] && { log_fail "Video stream found, expected none"; failed=1; }
                ;;
            no_audio)
                local a_streams=$(ffprobe -v error -select_streams a -show_entries stream=index -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ -n "$a_streams" ]] && { log_fail "Audio stream found, expected none"; failed=1; }
                ;;
            fps)
                local fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$file")
                fps=$(echo "scale=0; $fps" | bc -l)
                [[ "$fps" != "$val" ]] && { log_fail "FPS mismatch: expected $val, got $fps"; failed=1; }
                ;;
            format)
                # For images
                if command -v magick &>/dev/null; then
                    local f=$(magick identify -format "%m" "$file" | tr '[:upper:]' '[:lower:]')
                    [[ "$f" != "$val" ]] && { log_fail "Format mismatch: expected $val, got $f"; failed=1; }
                fi
                ;;
        esac
    done
    
    return $failed
}

run_test() {
    local script_path="$1"
    local validation_rules="$2"
    local input_files=("${@:3}")
    
    log_info "Testing: $(basename "$script_path") with [${input_files[*]}]"
    
    # Clean output data but keep sources
    find "$TEST_DATA" -type f -not \( -name "src.mp4" -o -name "src.jpg" -o -name "test.srt" -o -name "*'*.mp4" \) -delete
    
    local before=$(mktemp)
    ls -1 "$TEST_DATA" | sort > "$before"

    local script_log=$(mktemp)
    local first_input="${input_files[0]}"
    local input_dir=$(dirname "$first_input")
    local abs_script_path=$(readlink -f "$script_path")

    # Handle multiple inputs for CLI
    local input_bases=()
    for f in "${input_files[@]}"; do
        input_bases+=("$(basename "$f")")
    done

    ( cd "$input_dir" && timeout 60s bash "$abs_script_path" "${input_bases[@]}" ) > "$script_log" 2>&1
    local exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        log_fail "Script exited with code $exit_code"
        cat "$script_log"
        rm "$before" "$script_log"
        return 1
    fi

    local after=$(mktemp)
    ls -1 "$TEST_DATA" | sort > "$after"
    local new_files=$(comm -13 "$before" "$after")
    rm "$before" "$after"

    if [ -z "$new_files" ]; then
        log_fail "No output file detected"
        cat "$script_log"
        rm "$script_log"
        return 1
    fi

    local newest=$(echo "$new_files" | tail -n 1) # Take the last one created
    local output_file="$TEST_DATA/$newest"
    log_info "Detected output: $newest"

    if [ -n "$validation_rules" ]; then
        validate_media "$output_file" "$validation_rules"
        local val_status=$?
        [[ $val_status -eq 0 ]] && log_pass "$(basename "$script_path") validated successfully"
        rm "$script_log"
        return $val_status
    else
        log_pass "$(basename "$script_path") ran without error"
        rm "$script_log"
        return 0
    fi
}
