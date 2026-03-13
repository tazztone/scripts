#!/bin/bash
# testing/test_zenity4_repro.sh

source testing/lib_test.sh
setup_mock_zenity
generate_test_media

echo -e "\n=== Zenity 4.x 'FALSE' Return Bug Reproduction ==="

# Mock zenity to return exactly what Zenity 4.1.99 returns when double-clicking incorrectly
printf "FALSE\nFALSE\nFALSE\nFALSE\nFALSE\nFALSE\n" > /tmp/zenity_responses

log_file="/tmp/loop_zenity4.log"
# Clear debug log
# We need to source wizard.sh to get $LOG_FILE
LOG_DIR="$HOME/.local/share/scripts-sh"
LOG_FILE="$LOG_DIR/debug.log"
mkdir -p "$LOG_DIR"
> "$LOG_FILE"
export DEBUG_MODE=1

echo "Running Image-Magick-Toolbox.sh with Zenity 4.x mock..."
# Run the script with timeout just in case it hard-loops
timeout 10s bash "imagemagick/🖼️ Image-Magick-Toolbox.sh" "$TEST_DATA/src.jpg" > "$log_file" 2>&1

# Check if the recursion guard was triggered
if grep -q "RECURSION GUARD TRIGGERED" "$LOG_FILE"; then
    log_pass "Successfully reproduced the Zenity 4.x UI loop bug (Guard Tripped)."
    exit 0
else
    log_fail "Failed to reproduce infinite loop. It did not hit the recursion guard."
    cat "$LOG_FILE"
    exit 1
fi
