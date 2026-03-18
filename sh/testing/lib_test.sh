#!/bin/bash
# testing/lib_test.sh

# --- Configuration ---
TEST_DATA="/tmp/scripts_test_data"
MOCK_BIN="/tmp/scripts_mock_bin"
REPORT_FILE="/tmp/scripts_test_report.log"
HEADLESS=true

mkdir -p "$TEST_DATA" "$MOCK_BIN"
[ -z "$TEST_SUITE_RUNNING" ] && { > "$REPORT_FILE"; export TEST_SUITE_RUNNING=1; }

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

setup_mock_zenity() {
    cat <<'EOF' > "$MOCK_BIN/zenity"
#!/bin/bash
# Handle --progress separately
if [[ "$*" == *"--progress"* ]]; then
    while read -r line; do :; done
    exit 0
fi

# Informational dialogs exit 0 by default in mock
if [[ "$*" == *"--info"* || "$*" == *"--notification"* || "$*" == *"--error"* || "$*" == *"--warning"* ]]; then
    exit ${ZENITY_MOCK_EXIT_CODE:-0}
fi

# Override responses from environment variables if present
if [[ "$*" == *"--list"* && -n "$ZENITY_LIST_RESPONSE" ]]; then
    echo "$ZENITY_LIST_RESPONSE"
    exit ${ZENITY_MOCK_EXIT_CODE:-0}
fi
if [[ ("$*" == *"--entry"* || "$*" == *"--forms"*) && -n "$ZENITY_ENTRY_RESPONSE" ]]; then
    echo "$ZENITY_ENTRY_RESPONSE"
    exit ${ZENITY_MOCK_EXIT_CODE:-0}
fi

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
EOF
    chmod +x "$MOCK_BIN/zenity"
    export PATH="$MOCK_BIN:$PATH"
}

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo "FAIL: $1" >> "$REPORT_FILE"
}
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

generate_test_media() {
    # Guard against redundant calls
    if [[ -f "$TEST_DATA/input.mp4" && -f "$TEST_DATA/input.jpg" && -f "$TEST_DATA/alpha.png" ]]; then
        return 0
    fi

    log_info "Generating safe test media..."
    # Standardized names that don't match output wildcards (which start with input_name_)
    ffmpeg -y -nostdin -f lavfi -i color=c=black:s=1280x720:d=1:r=30 -f lavfi -i anullsrc=r=44100:cl=stereo:d=1 \
           -c:v libx264 -c:a aac -pix_fmt yuv420p "$TEST_DATA/input.mp4" &>/dev/null
    ffmpeg -y -nostdin -f lavfi -i color=c=blue:s=1280x720:d=1 -vframes 1 "$TEST_DATA/input.jpg" &>/dev/null
    magick -size 100x100 xc:transparent "$TEST_DATA/alpha.png" &>/dev/null
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
                local codec=$(ffprobe -v error -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 -select_streams v:0 "$file")
                [[ "$codec" != *"$val"* ]] && { log_fail "V-Codec mismatch: expected $val, got $codec"; failed=1; }
                ;;
            fps)
                local fps_raw=$(ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of default=noprint_wrappers=1:nokey=1 "$file")
                local fps=$(echo "scale=2; $fps_raw" | bc -l)
                [[ "$val" =~ ^[0-9]+$ ]] && fps=$(printf "%.0f" "$fps")
                [[ "$fps" != "$val" ]] && { log_fail "FPS mismatch: expected $val, got $fps"; failed=1; }
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
            format)
                local fmt=""
                if [[ "$file" =~ \.(jpg|png|webp|gif|jpeg)$ ]]; then
                    fmt=$(magick identify -format "%m" "$file" | tr '[:upper:]' '[:lower:]' | head -n 1)
                else
                    fmt=$(ffprobe -v error -show_entries format=format_name -of default=noprint_wrappers=1:nokey=1 "$file" | tr '[:upper:]' '[:lower:]')
                fi
                [[ "$fmt" != *"$val"* ]] && { log_fail "Format mismatch: expected $val in $fmt"; failed=1; }
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
                for t in $(echo "$val" | tr ',' ' '); do
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
        files_rel=("${@:3}")
        local first_file="${files_rel[0]}"
        # If first_file is a flag like --preset, pattern must be provided via --pattern
        if [[ "$first_file" == "-"* ]]; then
            log_fail "run_test: first file is a flag [$first_file], but --pattern was not used."
            return 1
        fi
        local base=$(basename -- "${first_file%.*}")
        pattern="${base}_*.*"
    fi

    local files_abs=()
    local files_base=()
    for f in "${files_rel[@]}"; do 
        if [[ "$f" == "-"* ]]; then
            files_base+=("$f")
        else
            files_abs+=("$(readlink -f -- "$f")")
            files_base+=("$(basename -- "$f")")
        fi
    done

    # Get dir from first non-flag file
    local dir="."
    for f in "${files_rel[@]}"; do
        if [[ "$f" != "-"* ]]; then
            dir=$(dirname -- "$(readlink -f -- "$f")")
            break
        fi
    done

    local failed=0
    
    # Pre-run file list
    local before=$(find "$dir" -maxdepth 1 -name "$pattern" | sort)

    log_info "Testing: $(basename -- "$script_abs") with [${files_rel[*]}]"
    local out_log=$(mktemp)
    (
        cd "$dir" || exit 1
        bash "$script_abs" "${files_base[@]}"
    ) &> "$out_log"
    local status=$?
    
    # Post-run file list
    local after=$(find "$dir" -maxdepth 1 -name "$pattern" | sort)
    
    # Find new file (comm -13 shows lines only in 'after')
    local newest_file=$(comm -13 <(echo "$before") <(echo "$after") | head -n 1)

    if [ $status -ne 0 ] || [[ -z "$newest_file" ]]; then
        log_fail "Test execution failed or no new output matching $pattern (Exit: $status)"
        echo "--- LOG ---"; cat "$out_log"; echo "-----------"
        rm -f "$out_log"
        return 1
    fi
    
    log_info "Detected: $(basename -- "$newest_file")"
    rm -f "$out_log"
    validate_media "$newest_file" "$rules" || return 1
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

# Resilience testing: Expect script to survive cancellations and eventually succeed
run_resilience_test() {
    local script_rel="$1"
    local rules="$2"
    local files_rel=("${@:3}")
    local script_abs=$(readlink -f -- "$script_rel")
    
    log_info "Testing Resilience: $(basename -- "$script_abs")"
    run_test "$script_rel" "$rules" "${files_rel[@]}"
}
