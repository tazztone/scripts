#!/bin/bash
# testing/lib_test.sh

# --- Configuration ---
TEST_DATA="/tmp/scripts_test_data"
MOCK_BIN="/tmp/scripts_mock_bin"
REPORT_FILE="/tmp/scripts_test_report.log"
HEADLESS=true

mkdir -p "$TEST_DATA" "$MOCK_BIN"
if [ -z "$TEST_SUITE_RUNNING" ]; then
    > "$REPORT_FILE"
    printf "0\n0\n" > /tmp/scripts_test_count.log
    export TEST_SUITE_RUNNING=1
fi

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

setup_mock_zenity() {
    # Initialize call log
    printf "" > /tmp/zenity_call_log.txt
    cat <<'MOCK_EOF' > "$MOCK_BIN/zenity"
#!/bin/bash
# Log every call for debugging and loop detection
printf "CALL: %s\n" "$*" >> /tmp/zenity_call_log.txt

# 1. Informational & Required Flags (no response needed)
if [[ "$*" == *"--version"* ]]; then
    if [[ "${ZENITY_PROFILE:-}" == "zenity3" ]]; then
        echo "3.92.0"
    else
        echo "4.0.1"
    fi
    exit 0
fi

if [[ "$*" == *"--progress"* ]]; then
    while read -r line; do :; done
    exit 0
fi

if [[ "$*" == *"--question"* ]]; then
    exit ${ZENITY_QUESTION_EXIT:-1}
fi

if [[ "$*" == *"--info"* || "$*" == *"--notification"* || "$*" == *"--error"* || "$*" == *"--warning"* ]]; then
    exit 0
fi

# 2. Keyed Dispatch: Each dialog type reads from its own environment variable
# If the variable has multiple lines, we consume them sequentially
_consume_env_mock() {
    local var_name="$1"
    local val="${!var_name:-}"
    # Debug: log seen variables
    printf "MOCK DEBUG: %s=%s\n" "$var_name" "$val" >> /tmp/zenity_call_log.txt
    [ -z "$val" ] && return 1
    
    # Use a temp file to track consumption state across subshells if needed
    # (Actually, for most tests, the script runs in the same shell as the test, 
    # but Zenity runs as a separate process. So we need a persistent state).
    local state_file="/tmp/mock_state_${var_name}"
    if [ ! -f "$state_file" ]; then
        # Ensure it has content and is never truly empty during this call
        echo "$val" > "$state_file"
    fi
    
    if [ -s "$state_file" ]; then
        local line
        line=$(head -n 1 "$state_file")
        echo "$line"
        # Atomically remove the first line
        sed -i '1d' "$state_file"
        return 0
    fi
    return 1
}

if [[ "$*" == *"--list"* ]]; then
    _consume_env_mock "MOCK_LIST" && exit 0
fi

if [[ "$*" == *"--forms"* ]]; then
    _consume_env_mock "MOCK_FORMS" && exit 0
fi

if [[ "$*" == *"--entry"* ]]; then
    _consume_env_mock "MOCK_ENTRY" && exit 0
fi

if [[ "$*" == *"--file-selection"* ]]; then
    _consume_env_mock "MOCK_FILE" && exit 0
fi

# 3. Fallback: Legacy Sequential FIFO (for backwards compatibility)
RESP_FILE="/tmp/zenity_responses"
if [ -f "$RESP_FILE" ] && [ -s "$RESP_FILE" ]; then
    PICK=$(head -n 1 "$RESP_FILE")
    # Use temporary file for atomic-ish update
    tail -n +2 "$RESP_FILE" > "${RESP_FILE}.tmp" && mv "${RESP_FILE}.tmp" "$RESP_FILE"
    echo "$PICK"
    exit ${ZENITY_MOCK_EXIT_CODE:-0}
else
    # Mock cancel/close for input-requiring dialogs (list, entry, etc.)
    exit ${ZENITY_MOCK_EXIT_CODE:-1}
fi
MOCK_EOF
    chmod +x "$MOCK_BIN/zenity"
    export PATH="$MOCK_BIN:$PATH"
}

_count_test() {
    local pass=$1
    if [ -f /tmp/scripts_test_count.log ]; then
        local counts=()
        mapfile -t counts < /tmp/scripts_test_count.log
        local total=$(( ${counts[0]:-0} + 1 ))
        local passed=$(( ${counts[1]:-0} + pass ))
        printf "%s\n%s\n" "$total" "$passed" > /tmp/scripts_test_count.log
    fi
}

log_pass() { 
    echo -e "${GREEN}[PASS]${NC} $1"
    _count_test 1
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo "FAIL: $1" >> "$REPORT_FILE"
    _count_test 0
}
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

generate_test_media() {
    # Guard against redundant calls
    if [[ -f "$TEST_DATA/input.mp4" && -f "$TEST_DATA/input.jpg" && -f "$TEST_DATA/src.mp4" && -f "$TEST_DATA/src.jpg" ]]; then
        return 0
    fi

    log_info "Generating safe test media..."
    # Standardized names that don't match output wildcards (which start with input_name_)
    ffmpeg -y -nostdin -f lavfi -i color=c=black:s=1280x720:d=1:r=30 -f lavfi -i anullsrc=r=44100:cl=stereo:d=1 \
           -c:v libx264 -c:a aac -pix_fmt yuv420p "$TEST_DATA/input.mp4" &>/dev/null
    ffmpeg -y -nostdin -f lavfi -i color=c=blue:s=1280x720:d=1 -vframes 1 "$TEST_DATA/input.jpg" &>/dev/null
    magick -size 100x100 xc:transparent "$TEST_DATA/alpha.png" &>/dev/null

    # Create src.* copies for compatibility with legacy tests
    cp "$TEST_DATA/input.mp4" "$TEST_DATA/src.mp4"
    cp "$TEST_DATA/input.jpg" "$TEST_DATA/src.jpg"
}

cleanup_test_data() {
    log_info "Cleaning up temporary test data..."
    rm -rf "$TEST_DATA" "$MOCK_BIN"
}

seed_gpu_cache() {
    local type="$1"
    local cache="${XDG_CACHE_HOME:-$HOME/.cache}/scripts-sh-gpu-cache"
    log_info "Seeding GPU cache with: $type"
    mkdir -p "$(dirname "$cache")"
    echo "$type" > "$cache"
}

validate_media() {
    local file="$1"
    local rules="$2"
    local failed=0
    
    if [[ ! -f "$file" ]]; then
        log_fail "File does not exist: $file"
        return 1
    fi

    IFS=',' read -ra ADDR <<< "$rules"
    for rule in "${ADDR[@]}"; do
        local key="${rule%%=*}"
        local val="${rule#*=}"
        
        case "$key" in
            vcodec)
                local codec=$(ffprobe -v error -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 -select_streams v:0 "$file" | head -n 1)
                [[ "$codec" != *"$val"* ]] && { log_fail "V-Codec mismatch: expected $val, got $codec"; failed=1; }
                ;;
            acodec)
                local codec=$(ffprobe -v error -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 -select_streams a:0 "$file" | head -n 1)
                [[ "$codec" != *"$val"* ]] && { log_fail "A-Codec mismatch: expected $val, got $codec"; failed=1; }
                ;;
            fps)
                local fps_raw=$(ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of default=noprint_wrappers=1:nokey=1 "$file")
                local fps=$(echo "scale=2; $fps_raw" | bc -l)
                # Tolerance check for FPS (handles 29.97 vs 30 etc)
                local diff=$(awk -v f="$fps" -v v="$val" 'BEGIN { d = f - v; if (d < 0) d = -d; print d }')
                if (( $(echo "$diff > 0.1" | bc -l) )); then
                    log_fail "FPS mismatch: expected $val, got $fps (diff=$diff)"
                    failed=1
                fi
                ;;
            duration)
                local d=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file")
                local diff=$(awk -v d="$d" -v val="$val" 'BEGIN { diff = d - val; if (diff < 0) diff = -diff; print diff }')
                # 0.1s tolerance handles keyframe-alignment in lossless trims and container overhead
                (( $(echo "$diff > 0.1" | bc -l) )) && { log_fail "Duration mismatch: expected $val, got $d (diff=$diff)"; failed=1; }
                ;;
            width)
                local w=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ "$w" != "$val" ]] && { log_fail "Width mismatch: expected $val, got $w"; failed=1; }
                ;;
            height)
                local h=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ "$h" != "$val" ]] && { log_fail "Height mismatch: expected $val, got $h"; failed=1; }
                ;;
            format)
                local fmt=""
                if [[ "$file" =~ \.(jpg|png|webp|gif|jpeg)$ ]]; then
                    fmt=$(magick identify -format "%m" "$file" 2>/dev/null | tr '[:upper:]' '[:lower:]' | head -n 1)
                else
                    fmt=$(ffprobe -v error -show_entries format=format_name -of default=noprint_wrappers=1:nokey=1 "$file" | head -n 1 | cut -d',' -f1 | tr -d '\n\r' | tr '[:upper:]' '[:lower:]')
                fi
                # Use simple substring match to handle redundant strings (e.g. gifgifgif)
                if [[ "$fmt" != *"$val"* ]]; then
                    # Compatibility for containers
                    if [[ "$fmt" == "matroska" && "$val" == "webm" ]] || [[ "$fmt" == "webm" && "$val" == "matroska" ]]; then
                        :
                    # Fallback for image formats like 'jpeg' matching 'jpg'
                    elif [[ "$fmt" == "jpeg" && "$val" == "jpg" ]] || [[ "$fmt" == "jpg" && "$val" == "jpeg" ]]; then
                        :
                    else
                        log_fail "Format mismatch: expected $val in $fmt"
                        failed=1
                    fi
                fi
                ;;
            has_audio)
                local a=$(ffprobe -v error -select_streams a -show_entries stream=index -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ -z "$a" ]] && { log_fail "Audio stream missing"; failed=1; }
                ;;
            no_audio)
                local a=$(ffprobe -v error -select_streams a -show_entries stream=index -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ -n "$a" ]] && { log_fail "Audio stream found (expected none)"; failed=1; }
                ;;
            no_video)
                local v=$(ffprobe -v error -select_streams v -show_entries stream=index -of default=noprint_wrappers=1:nokey=1 "$file")
                [[ -n "$v" ]] && { log_fail "Video stream found (expected none)"; failed=1; }
                ;;
            subtitle_stream)
                local s=$(ffprobe -v error -select_streams s -show_entries stream=index -of default=noprint_wrappers=1:nokey=1 "$file" | grep -c .)
                [[ "$s" -ne "$val" ]] && { log_fail "Subtitle streams mismatch: expected $val, got $s"; failed=1; }
                ;;
            bitrate)
                # Note: bitrate uses raw bits/second as reported by ffprobe
                local b=$(ffprobe -v error -show_entries format=bitrate -of default=noprint_wrappers=1:nokey=1 "$file")
                if [[ "$b" == "N/A" ]] || [[ "$b" -eq 0 ]]; then
                     log_fail "Invalid or missing bitrate: $b"
                     failed=1
                elif [[ "$val" =~ ^[0-9]+$ ]]; then
                    local diff=$(awk -v b="$b" -v val="$val" 'BEGIN { diff = b - val; if (diff < 0) diff = -diff; print diff }')
                    local threshold=$(awk -v val="$val" 'BEGIN { print val * 0.1 }')
                    if (( $(echo "$diff > $threshold" | bc -l) )); then
                        log_fail "Bitrate mismatch: expected approx $val, got $b (diff=$diff > $threshold)"
                        failed=1
                    fi
                fi
                ;;
            file_size_gt)
                local s=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file")
                [[ "$s" -le "$val" ]] && { log_fail "File size too small: $s <= $val"; failed=1; }
                ;;
            file_size_lt)
                local s=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file")
                [[ "$s" -ge "$val" ]] && { log_fail "File size too large: $s >= $val"; failed=1; }
                ;;
            tags)
                local filename=$(basename -- "$file")
                for t in $(echo "$val" | tr '|' ' '); do
                    [[ "$filename" != *"$t"* ]] && { log_fail "Tag missing: $t ($filename)"; failed=1; }
                done
                ;;
            title)
                local title=$(ffprobe -v error -show_entries format_tags=title -of default=noprint_wrappers=1:nokey=1 "$file")
                if [[ "$val" == "EMPTY" ]]; then
                    [[ -n "$title" ]] && { log_fail "Title not empty: got $title"; failed=1; }
                else
                    [[ "$title" != *"$val"* ]] && { log_fail "Title mismatch: expected $val, got $title"; failed=1; }
                fi
                ;;
        esac
    done
    return $failed
}

run_test() {
    local script_rel="$1"
    local rules="$2"
    local pattern=""
    local files_rel=()
    local script_abs=$(readlink -f -- "$script_rel")

    if [[ "$3" == "--pattern" ]]; then
        pattern="$4"
        files_rel=("${@:5}")
    else
        pattern=""
        files_rel=("${@:3}")
        local first_file="${files_rel[0]}"
        if [[ -n "$first_file" && "$first_file" != "-"* ]]; then
            local base=$(basename -- "${first_file%.*}")
            pattern="${base}_*.*"
        fi
    fi

    # Support absolute paths or relative patterns for finding output
    local find_arg="-name"
    [[ "$pattern" == *"/"* ]] && find_arg="-wholename"

    # --- Isolation Layer ---
    local TEMP_DIR=$(mktemp -d -p "/tmp" -t scripts_test_XXXXXX)
    local INPUT_BASENAMES=()
    for f in "${files_rel[@]}"; do
        if [[ "$f" == "-"* ]]; then
            INPUT_BASENAMES+=("$f")
        elif [[ -f "$f" ]]; then
            local fname=$(basename -- "$f")
            cp "$(readlink -f "$f")" "$TEMP_DIR/$fname"
            INPUT_BASENAMES+=("$fname")
        else
            INPUT_BASENAMES+=("$f")
        fi
    done

    log_info "Testing: $(basename -- "$script_abs") in $TEMP_DIR"
    local out_log=$(mktemp)
    local trace_log=$(mktemp)
    
    (
        cd "$TEMP_DIR" || exit 1
        # Clear mock state files to ensure fresh consumption for this run
        rm -f /tmp/mock_state_*
        # Run with -x and capture to trace_log (BASH_XTRACEFD is very robust)
        BASH_XTRACEFD=3 DEBUG_MODE=1 bash -x "$script_abs" "${INPUT_BASENAMES[@]}" 3>"$trace_log"
    ) &> "$out_log"
    local status=$?
    export LAST_TEMP_DIR="$TEMP_DIR"
    
    # Clear mock environment for next test in the same script
    unset MOCK_LIST MOCK_FORMS MOCK_ENTRY MOCK_FILE MOCK_FFMPEG_NVENC MOCK_FFMPEG_QSV MOCK_FFMPEG_VAAPI

    
    # Post-run: Find the new output file in TEMP_DIR
    local newest_file=""
    if [[ -n "$pattern" ]]; then
        newest_file=$(find "$TEMP_DIR" -maxdepth 1 $find_arg "$pattern" -type f -printf "%T@ %p\n" 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    fi

    if [ $status -ne 0 ] || [[ -z "$newest_file" ]]; then
        log_fail "Test execution failed or no output matching $pattern (Exit: $status)"
        echo "--- LOG ---" >> "$REPORT_FILE"
        cat "$out_log" >> "$REPORT_FILE"
        echo "--- TRACE ---" >> "$REPORT_FILE"
        cat "$trace_log" >> "$REPORT_FILE"
        echo "-----------" >> "$REPORT_FILE"
        rm -f "$out_log" "$trace_log"
        return 1
    fi
    
    log_info "Detected: $(basename -- "$newest_file")"
    validate_media "$newest_file" "$rules" || {
        echo "--- LOG ---" >> "$REPORT_FILE"
        cat "$out_log" >> "$REPORT_FILE"
        echo "--- FILES in $TEMP_DIR ---" >> "$REPORT_FILE"
        ls -R "$TEMP_DIR" >> "$REPORT_FILE"
        echo "-----------" >> "$REPORT_FILE"
        rm -f "$out_log" "$trace_log"
        return 1
    }
    
    rm -f "$out_log" "$trace_log"
    return 0
}

# Negative testing: Expect script to FAIL (non-zero exit)
# Usage: run_fail_test "script" "expected_error_regex" "input_files..."
run_fail_test() {
    local script_rel="$1"
    local err_regex="$2"
    local files_rel=("${@:3}")
    local script_abs=$(readlink -f -- "$script_rel")
    
    local files_base=()
    local dir="."
    for f in "${files_rel[@]}"; do 
        if [[ "$f" == "-"* ]]; then
            files_base+=("$f")
        else
            files_base+=("$(basename -- "$f")")
            if [ "$dir" == "." ]; then
                dir=$(dirname -- "$(readlink -f -- "$f")")
            fi
        fi
    done

    log_info "Testing (Expect Failure): $(basename -- "$script_abs") with [${files_rel[*]}]"
    local out_log=$(mktemp)
    (
        cd "$dir" || exit 1
        bash "$script_abs" "${files_base[@]}"
    ) &> "$out_log"
    local status=$?
    
    if [ $status -eq 0 ]; then
        log_fail "Script passed but was expected to fail: $(basename -- "$script_abs")"
        echo "--- LOG ---"; cat "$out_log"; echo "-----------"
        rm -f "$out_log"
        return 1
    fi

    if [[ -n "$err_regex" ]]; then
        if ! grep -qiE "$err_regex" "$out_log"; then
            log_fail "Script failed as expected, but error message did not match '$err_regex'"
            echo "--- LOG ---"; cat "$out_log"; echo "-----------"
            rm -f "$out_log"
            return 1
        fi
    fi
    
    log_pass "Script failed as expected with status $status"
    rm -f "$out_log"
    return 0
}

# Negative testing: Expect script to exit 0 (user cancel)
run_negative_test() {
    local script_rel="$1"
    local files_rel=("${@:2}")
    local script_abs=$(readlink -f -- "$script_rel")
    
    local files_base=()
    local dir="."
    for f in "${files_rel[@]}"; do 
        files_base+=("$(basename -- "$f")")
        if [ "$dir" == "." ]; then
            dir=$(dirname -- "$(readlink -f -- "$f")")
        fi
    done

    log_info "Testing (Expect Cancel): $(basename -- "$script_abs") with [${files_rel[*]}]"
    local out_log=$(mktemp)
    (
        cd "$dir" || exit 1
        bash "$script_abs" "${files_base[@]}"
    ) &> "$out_log"
    local status=$?
    
    if [ $status -eq 0 ]; then
        log_pass "Script exited gracefully (status 0) on wizard cancel"
        rm -f "$out_log"
        return 0
    else
        log_fail "Script failed on cancel (Exit: $status)"
        echo "--- LOG ---"; cat "$out_log"; echo "-----------"
        rm -f "$out_log"
        return 1
    fi
}

# Setup a mock ffmpeg binary
setup_mock_ffmpeg() {
    mkdir -p "$MOCK_BIN"
    export PATH="$MOCK_BIN:$PATH"
    
    cat <<'EOF' > "$MOCK_BIN/ffmpeg"
#!/bin/bash
# Find real ffmpeg by stripping any 'mock_bin' from PATH
REAL_FFMPEG=$(PATH=$(echo "$PATH" | sed -E 's|[^:]*mock_bin:?||g') which ffmpeg)

# Check for hardware encoder usage (both probing and real encoding)
if [[ "$*" == *"nvenc"* ]]; then
    if [ "${MOCK_FFMPEG_NVENC:-0}" == "1" ]; then
        touch "${@: -1}" 2>/dev/null
        exit 0
    else
        exit 1
    fi
fi
if [[ "$*" == *"qsv"* ]]; then
    if [ "${MOCK_FFMPEG_QSV:-0}" == "1" ]; then
        touch "${@: -1}" 2>/dev/null
        exit 0
    else
        exit 1
    fi
fi
if [[ "$*" == *"vaapi"* ]]; then
    if [ "${MOCK_FFMPEG_VAAPI:-0}" == "1" ]; then
        touch "${@: -1}" 2>/dev/null
        exit 0
    else
        exit 1
    fi
fi
if [[ "$*" == *"-c:v h264_v4l2m2m"* ]]; then
    [ "${MOCK_FFMPEG_V4L2:-0}" == "1" ] && exit 0 || exit 1
fi

# Not a probe? Delegate to real ffmpeg
if [ -x "$REAL_FFMPEG" ]; then
    exec "$REAL_FFMPEG" "$@"
else
    echo "Error: Real ffmpeg not found in PATH (after stripping mock)" >&2
    exit 127
fi
EOF
    chmod +x "$MOCK_BIN/ffmpeg"
}

# Resilience testing: Expect script to survive cancellations and eventually succeed
run_resilience_test() {
    local script_rel="$1"
    local rules="$2"
    local files_rel=("${@:3}")
    local script_abs=$(readlink -f -- "$script_rel")
    
    log_info "Testing Resilience: $(basename -- "$script_abs")"
    run_test "$script_rel" "$rules" "${files_rel[@]}"
}
