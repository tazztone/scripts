#!/bin/bash
# testing/test_units.sh
# Unit tests for shared utility functions

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"
source "$PROJECT_ROOT/ffmpeg/common.sh"

echo -e "\n${YELLOW}=== Unit Tests: validate_time_format ===${NC}"

test_time() {
    local input="$1"
    local expected="$2"
    local result
    result=$(validate_time_format "$input")
    local status=$?
    
    if [ $status -eq 0 ] && [ "$result" = "$expected" ]; then
        log_pass "validate_time_format '$input' -> '$result'"
    elif [ $status -ne 0 ] && [ "$expected" = "FAIL" ]; then
        log_pass "validate_time_format '$input' -> FAILED (Expected)"
    else
        log_fail "validate_time_format '$input' -> Got '$result' (status $status), Expected '$expected'"
        return 1
    fi
}

FAILED=0
# Seconds
test_time "10" "10" || FAILED=$((FAILED+1))
test_time "10.5" "10.5" || FAILED=$((FAILED+1))

# MM:SS
test_time "01:30" "90" || FAILED=$((FAILED+1))
test_time "90:00" "5400" || FAILED=$((FAILED+1))
test_time "00:05.500" "5.500" || FAILED=$((FAILED+1))

# HH:MM:SS
test_time "01:00:00" "3600" || FAILED=$((FAILED+1))
test_time "00:01:30.500" "90.500" || FAILED=$((FAILED+1))

# Boundary & Edge Cases
log_info "Testing Boundary Cases..."
test_time "00:60" "60" || FAILED=$((FAILED+1)) # 60s is 1m, technically valid but often an input error
test_time "00:00:60" "60" || FAILED=$((FAILED+1))
test_time "-10" "FAIL" || FAILED=$((FAILED+1)) # Negative not allowed
test_time "999:99:99" "3602439" || FAILED=$((FAILED+1)) # Large value

echo -e "\n${YELLOW}=== Unit Tests: Wizard & History ===${NC}"
source "$PROJECT_ROOT/common/wizard.sh"

# 1. Test save_to_history
HIST_FILE="/tmp/scripts-sh-history-test"
echo "Old Choice" > "$HIST_FILE"
save_to_history "$HIST_FILE" "New Choice"
if [ "$(head -n 1 "$HIST_FILE")" == "New Choice" ]; then
    log_pass "save_to_history: Added new choice to top"
else
    log_fail "save_to_history: Failed to update history"
    FAILED=$((FAILED+1))
fi

# 2. Test prompt_save_preset (Mocked Zenity)
PRESET_FILE="/tmp/scripts-sh-presets-test"
> "$PRESET_FILE"
setup_mock_zenity
# Mock 'Yes' to Save and entry 'My Test Preset'
# zenity --question (choice 1) 
# zenity --entry (choice 2)
# zenity --notification (choice 3) 
printf "TRUE\nMy-Test-Preset\nSUCCESS\n" > /tmp/zenity_responses

prompt_save_preset "$PRESET_FILE" "Intent:Scale|Intent:Crop" "Suggested" "false"
if grep -q "My-Test-Preset" "$PRESET_FILE"; then
    log_pass "prompt_save_preset: Correctly saved new preset"
else
    log_fail "prompt_save_preset: Failed to save preset with mocked input"
    FAILED=$((FAILED+1))
fi

echo -e "\n${YELLOW}=== Unit Tests: ImageMagick Common ===${NC}"
source "$PROJECT_ROOT/imagemagick/common.sh"
# Test generate_safe_filename for ImageMagick specifically
# (Already tested in test_filename_safe.sh, but verifying it works when sourced from IM)
res=$(generate_safe_filename "pic" "_low" "jpg")
if [ "$res" == "pic_low.jpg" ]; then
    log_pass "IM generate_safe_filename basic success"
else
    log_fail "IM generate_safe_filename failed: got $res"
    FAILED=$((FAILED+1))
fi

rm -f "$HIST_FILE" "$PRESET_FILE"
exit $FAILED
