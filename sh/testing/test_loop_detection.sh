#!/bin/bash
# testing/test_loop_detection.sh
# Specifically checks if Image-Magick-Toolbox loops its menu.

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"
setup_mock_zenity
generate_test_media

echo -e "\n${YELLOW}=== Infinite Loop Detection Test ===${NC}"

# Test Case: Select "Scale & Resize"
# Mock Queue:
# 1. Main Menu -> returns "Scale & Resize"
# 2. Scale Dialog -> returns "1920x (HD)|"
# 3. Main Menu (Wait! If it loops, it calls menu again. If not, it finishes.)

# We provide 3 responses. If it loops, it will consume more than expected.
printf "Scale & Resize\n1920x (HD)|\n\n" > /tmp/zenity_responses

echo "Running Image-Magick-Toolbox.sh..."
log_file="/tmp/loop_test_script.log"
bash "$PROJECT_ROOT/imagemagick/🖼️ Image-Magick-Toolbox.sh" "$TEST_DATA/src.jpg" > "$log_file" 2>&1

CALL_COUNT=$(grep -c "CALL:" /tmp/zenity_call_log.txt)
echo "Total Zenity Calls: $CALL_COUNT"

if [ "$CALL_COUNT" -gt 3 ]; then
    log_fail "LOOP DETECTED! Zenity was called $CALL_COUNT times (Expected <= 3)."
    echo "--- Zenity Call Log ---"
    cat /tmp/zenity_call_log.txt
    exit 1
else
    log_pass "No loop detected ($CALL_COUNT calls)."
    exit 0
fi
