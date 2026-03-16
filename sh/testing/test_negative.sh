#!/bin/bash
# testing/test_negative.sh
# Validates error handling and edge cases

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"
[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media
FAILED=0

echo -e "\n${YELLOW}=== Negative & Edge-Case Tests ===${NC}"

# Test 1: Missing input file
echo "Test 1: Missing input file"
run_fail_test "$PROJECT_ROOT/ffmpeg/🧰 Universal-Toolbox.sh" "not found|readable" "$TEST_DATA/non_existent.mp4" || FAILED=1

# Test 2: Invalid CLI Preset
echo "Test 2: Invalid CLI Preset"
run_fail_test "$PROJECT_ROOT/ffmpeg/🧰 Universal-Toolbox.sh" "Error: Preset 'InvalidName' not found" --preset "InvalidName" "$TEST_DATA/input.mp4" || FAILED=1

# Test 3: Zenity Cancel (Mocked)
# We need to ensure zenity is mocked to return exit 1 (which it now does by default if no responses remain)
echo "Test 3: Zenity Cancel (Graceful Exit)"
> /tmp/zenity_responses # Clear queue so next zenity call returns exit 1
# Universal Toolbox should exit 0 if the main wizard is cancelled
(
    cd "$TEST_DATA"
    bash "$PROJECT_ROOT/ffmpeg/🧰 Universal-Toolbox.sh" "input.mp4"
)
STATUS=$?
if [ $STATUS -eq 0 ]; then
    log_pass "Script exited gracefully (status 0) on wizard cancel"
else
    log_fail "Script did not exit gracefully on wizard cancel (status $STATUS)"
    FAILED=1
fi

# Test 4: Corrupt File (Simulated with empty file)
echo "Test 4: Corrupt/Empty input file"
touch "$TEST_DATA/empty.mp4"
run_fail_test "$PROJECT_ROOT/ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "Error: File is empty" "$TEST_DATA/empty.mp4" || FAILED=1
rm "$TEST_DATA/empty.mp4"

echo -e "\n${GREEN}Negative & Edge-Case Tests Finished!${NC}"
exit $FAILED
