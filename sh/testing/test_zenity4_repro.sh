#!/bin/bash
# testing/test_zenity4_repro.sh

source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"
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
timeout 5s bash "imagemagick/🖼️ Image-Magick-Toolbox.sh" "$TEST_DATA/src.jpg" > "$log_file" 2>&1
STATUS=$?

# If the fix works, it should exit 0 immediately after receiving "FALSE"
if [ $STATUS -eq 0 ] && ! grep -q "RECURSION GUARD TRIGGERED" "$LOG_FILE"; then
    log_pass "Zenity 4.x 'FALSE' bug handled correctly (Graceful exit, no loop)."
    exit 0
elif grep -q "RECURSION GUARD TRIGGERED" "$LOG_FILE"; then
    log_fail "Recursion guard was hit! The script looped 10+ times."
    exit 1
else
    log_fail "Script failed with status $STATUS"
    cat "$log_file"
    exit 1
fi
