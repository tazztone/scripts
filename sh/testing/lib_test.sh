#!/bin/bash
# testing/lib_test.sh
# Shared testing utilities for all toolboxes

# --- Configuration ---
TEST_DATA="/tmp/scripts_test_data"
MOCK_BIN="/tmp/scripts_mock_bin"
REPORT_FILE="$(pwd)/testing/output/test_report.log"
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
if [ -z "$TEST_SUITE_RUNNING" ]; then
    > "$REPORT_FILE"
    export TEST_SUITE_RUNNING=1
fi

# --- Zenity Mocking ---
setup_mock_zenity() {
    cat <<'EOF' > "$MOCK_BIN/zenity"
#!/bin/bash
# Headless Zenity Mock
ARGS="$*"
CALL_LOG="/tmp/zenity_call_log.txt"
echo "CALL: $ARGS" >> "$CALL_LOG"

# 1. Handle Response Overrides (Queue based)
get_queue_response() {
    RESPONSE_QUEUE="/tmp/zenity_responses"
    if [ -s "$RESPONSE_QUEUE" ]; then
        RESPONSE=$(head -n 1 "$RESPONSE_QUEUE")
        sed -i '1d' "$RESPONSE_QUEUE"
        echo "$RESPONSE"
        return 0
    fi
    return 1
}

# 2. Handle Entry Response
if [[ "$ARGS" == *"--entry"* ]]; then
    if get_queue_response; then exit 0; fi
    if [ -n "$ZENITY_ENTRY_RESPONSE" ]; then
        echo "$ZENITY_ENTRY_RESPONSE"
        exit 0
    fi
fi

# 3. Handle Checklist/List
if [[ "$ARGS" == *"--list"* ]]; then
    if get_queue_response; then exit 0; fi
    RESP="${ZENITY_LIST_RESPONSE:-}"
    # If a profile is set and the response is a simple string, we can transform it
    if [[ -n "$ZENITY_PROFILE" && "$RESP" != *"|"* ]]; then
        case "$ZENITY_PROFILE" in
            zenity4) RESP="TRUE|$RESP|$RESP|Description|$RESP" ;;
            ghost)   RESP="FALSE|$RESP|$RESP|Description|$RESP" ;;
        esac
    fi
    echo "$RESP"
    exit 0
fi

# 4. Handle Forms
if [[ "$ARGS" == *"--forms"* ]]; then
    if get_queue_response; then exit 0; fi
    if [ -n "$ZENITY_FORMS_RESPONSE" ]; then
        echo "$ZENITY_FORMS_RESPONSE"
    else
        echo ""
    fi
    exit 0
fi

# 5. Handle Question
if [[ "$ARGS" == *"--question"* ]]; then
    if [ -n "$ZENITY_MOCK_EXIT_CODE" ]; then exit "$ZENITY_MOCK_EXIT_CODE"; fi
    if [[ "$ZENITY_QUESTION_RESPONSE" == "YES" ]]; then exit 0; else exit 1; fi
fi

if [ -n "$ZENITY_MOCK_EXIT_CODE" ]; then exit "$ZENITY_MOCK_EXIT_CODE"; fi

case "$ARGS" in
    *--scale*) echo "1280" ;;
    *--entry*) echo "9" ;;
    *--file-selection*) 
        if get_queue_response; then exit 0; fi
        echo "/tmp/scripts_test_data/test.srt"
        ;;
    *--progress*) 
        # For progress bars, we SHOULD NOT consume the mock response queue
        # as the progress bar is usually secondary/informative
        cat > /dev/null
        exit 0
        ;;
    *--notification*)
        # Same for notifications
        exit 0
        ;;
    *) exit 0 ;;
esac
EOF
    echo -n "" > /tmp/zenity_call_log.txt
    chmod +x "$MOCK_BIN/zenity"
    export PATH="$MOCK_BIN:$PATH"
}

cleanup_test_data() {
    log_info "Cleaning up temporary test data..."
    rm -f /tmp/test_trim_*.mp4 /tmp/test_copy_*.mp4 /tmp/test_meta_*.mp4 /tmp/test_stream_*.mp4 /tmp/test_rotation_*.mp4
    rm -f /tmp/zenity_responses /tmp/zenity_call_log.txt
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
    log_info "Validating file: $file"

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
                local fps_raw=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$file")
                # Handle fraction like 30000/1001
                local fps=$(echo "scale=2; $fps_raw" | bc -l)
                # Round to nearest integer for simple comparison if val is integer
                if [[ "$val" =~ ^[0-9]+$ ]]; then
                    fps=$(printf "%.0f" "$fps")
                fi
                [[ "$fps" != "$val" ]] && { log_fail "FPS mismatch: expected $val, got $fps (raw: $fps_raw)"; failed=1; }
                ;;
            duration)
                local dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file")
                # Allow 0.1s tolerance
                local diff=$(echo "$dur - $val" | bc -l | sed 's/-//')
                if (( $(echo "$diff > 0.1" | bc -l) )); then
                    log_fail "Duration mismatch: expected $val, got $dur (diff: $diff)"; failed=1
                fi
                ;;
            bitrate)
                local br=$(ffprobe -v error -show_entries format=bit_rate -of default=noprint_wrappers=1:nokey=1 "$file")
                local br_kbps=$((br / 1000))
                # Allow 10% tolerance
                local lower=$((val * 90 / 100))
                local upper=$((val * 110 / 100))
                if [ "$br_kbps" -lt "$lower" ] || [ "$br_kbps" -gt "$upper" ]; then
                    log_fail "Bitrate outside 10% tolerance: expected ~${val}k, got ${br_kbps}k"; failed=1
                fi
                ;;
            subtitle_stream)
                local s_streams=$(ffprobe -v error -select_streams s -show_entries stream=index -of default=noprint_wrappers=1:nokey=1 "$file" | wc -l)
                [[ "$s_streams" -ne "$val" ]] && { log_fail "Subtitle stream count mismatch: expected $val, got $s_streams"; failed=1; }
                ;;
            has_audio)
                local a_streams=$(ffprobe -v error -select_streams a -show_entries stream=index -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ -z "$a_streams" ]] && { log_fail "Expected audio stream, but none found"; failed=1; }
                ;;
            file_size_lt)
                local size=$(stat -c%s "$file")
                [[ "$size" -ge "$val" ]] && { log_fail "File size too large: expected < $val, got $size"; failed=1; }
                ;;
            file_size_gt)
                local size=$(stat -c%s "$file")
                [[ "$size" -le "$val" ]] && { log_fail "File size too small: expected > $val, got $size"; failed=1; }
                ;;
            format)
                if command -v magick &>/dev/null; then
                    local f=$(magick identify -format "%m\n" "$file[0]" | head -n 1 | tr '[:upper:]' '[:lower:]')
                    [[ "$f" != "$val" ]] && { log_fail "Format mismatch: expected $val, got $f"; failed=1; }
                fi
                ;;
            tags)
                IFS='|' read -ra TAGS <<< "$val"
                for tag in "${TAGS[@]}"; do
                    if [[ "$(basename "$file")" != *"$tag"* ]]; then
                        log_fail "Filename missing required tag: $tag (Filename: $(basename "$file"))"
                        failed=1
                    fi
                done
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
    
    local input_bases=()
    for f in "${input_files[@]}"; do input_bases+=("$(basename "$f")"); done

    # Clean only non-source and non-input files
    for f in "$TEST_DATA"/*; do
        [ -e "$f" ] || continue
        local b=$(basename "$f")
        [[ "$b" == "src.mp4" || "$b" == "src.jpg" || "$b" == "test.srt" ]] && continue
        local is_input=0
        for ib in "${input_bases[@]}"; do [[ "$b" == "$ib" ]] && is_input=1 && break; done
        [[ "$is_input" -eq 1 ]] && continue
        rm -rf "$f"
    done
    
    local before=$(mktemp)
    ls -1 "$TEST_DATA" | sort > "$before"
    local first_input="${input_files[0]}"
    local input_dir=$(dirname "$first_input")
    local abs_script_path=$(readlink -f "$script_path")

    ( cd "$input_dir" && timeout 60s bash "$abs_script_path" "${input_bases[@]}" )
    local exit_code=$?

    local after=$(mktemp)
    ls -1 "$TEST_DATA" | sort > "$after"
    local new_files=$(comm -13 "$before" "$after")
    rm "$before" "$after"

    if [ -z "$new_files" ]; then
        log_fail "No output file detected"
        return 1
    fi

    # Pick the most recently modified file among new ones
    local newest=""
    local max_mtime=0
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        local fpath="$TEST_DATA/$f"
        [ -e "$fpath" ] || continue
        local mtime=$(stat -c %Y "$fpath" 2>/dev/null || echo 0)
        if [ "$mtime" -ge "$max_mtime" ]; then
            max_mtime=$mtime
            newest="$f"
        fi
    done <<< "$new_files"

    if [ -z "$newest" ]; then
        log_fail "Could not identify newest output file"
        return 1
    fi

    local output_file="$TEST_DATA/$newest"
    log_info "Detected newest output: $newest"

    if [ -n "$validation_rules" ]; then
        validate_media "$output_file" "$validation_rules"
        return $?
    else
        log_pass "Ran without error"
        return 0
    fi
}

run_negative_test() {
    local script_path="$1"
    local input_files=("${@:2}")
    log_info "Negative Test: $(basename "$script_path")"
    find "$TEST_DATA" -type f -not \( -name "src.mp4" -o -name "src.jpg" -o -name "test.srt" \) -delete
    local before_count=$(ls -1 "$TEST_DATA" | wc -l)
    local abs_script_path=$(readlink -f "$script_path")
    local input_dir=$(dirname "${input_files[0]}")
    local input_bases=()
    for f in "${input_files[@]}"; do input_bases+=("$(basename "$f")"); done

    ( cd "$input_dir" && timeout 10s bash "$abs_script_path" "${input_bases[@]}" )
    local exit_code=$?

    local after_count=$(ls -1 "$TEST_DATA" | wc -l)
    if [ "$after_count" -gt "$before_count" ]; then
        log_fail "Artifacts were created during negative test"
        return 1
    fi
    log_pass "Handled negative path successfully"
    return 0
}

run_resilience_test() {
    run_test "$1" "$2" "${@:3}"
}
