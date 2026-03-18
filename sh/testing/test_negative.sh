#!/bin/bash
# testing/test_negative.sh
# Tests edge cases, failures, and user cancellations

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"

FAILED=0

echo -e "\n${YELLOW}=== Negative & Edge-Case Tests ===${NC}"

setup_mock_zenity
generate_test_media

# Test 1: Missing Input
echo "Test 1: Missing input file"
run_fail_test "$PROJECT_ROOT/ffmpeg/🧰 Universal-Toolbox.sh" "Error: File not found" "/tmp/scripts_test_data/non_existent.mp4" || FAILED=1

# Test 2: Invalid CLI Preset
echo "Test 2: Invalid CLI Preset"
run_fail_test "$PROJECT_ROOT/ffmpeg/🧰 Universal-Toolbox.sh" "Error: Preset 'InvalidName' not found" "--preset" "InvalidName" "$TEST_DATA/input.mp4" || FAILED=1

# Test 3: Zenity Cancel (Graceful Exit)
# When the response queue is empty, mock zenity exits 1, which the scripts should handle as user cancellation.
echo "Test 3: Zenity Cancel (Graceful Exit)"
> /tmp/zenity_responses
bash "$PROJECT_ROOT/ffmpeg/🧰 Universal-Toolbox.sh" "$TEST_DATA/input.mp4" &>/dev/null
STATUS=$?
if [ $STATUS -eq 0 ]; then
    log_pass "Script exited gracefully (status 0) on wizard cancel"
else
    log_fail "Script failed on cancel (Exit: $STATUS)"
    FAILED=1
fi

# Test 4: Corrupt File (Simulated with empty file)
echo "Test 4: Corrupt/Empty input file"
touch "$TEST_DATA/empty.mp4"
# Using regex that matches actual script output for empty files.
# The Lossless Operations Toolbox checks for empty files before processing.
run_fail_test "$PROJECT_ROOT/ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "Error: File is empty" "$TEST_DATA/empty.mp4" || FAILED=1
rm "$TEST_DATA/empty.mp4"

echo -e "\n${YELLOW}Negative & Edge-Case Tests Finished!${NC}"
exit $FAILED
