#!/bin/bash
# testing/test_zenity_smoke.sh
# Smoke test for real Zenity launch capability.

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"
source "$PROJECT_ROOT/common/wizard.sh"

echo -e "\n${YELLOW}=== Zenity Binary Smoke Test ===${NC}"

# Ensure we are NOT using the mock
export PATH=$(echo "$PATH" | sed "s|/tmp/scripts_mock_bin:||g")

# Test 1: Info Dialog
echo "Test 1: Launching --info (Timeout 0.1s)"
zenity --info --text="Smoke Test" --timeout=1 >/dev/null 2>&1
EXIT_VAL=$?
if [ $EXIT_VAL -eq 0 ] || [ $EXIT_VAL -eq 5 ]; then
    log_pass "Info dialog launched successfully"
else
    log_fail "Info dialog failed to launch (Exit: $EXIT_VAL)"
    exit 1
fi

# Test 2: Main Wizard Dialog Contract
echo "Test 2: Launching Unified Wizard (Timeout 0.5s)"
# We use a real timeout and capture the result
# If it returns "This option is not available", the exit code will be 255.
TITLE="Smoke Test Wizard"
INTENTS="📐|Scale|Desc;✂️|Crop|Desc"
TEMP_ARGS=()
_wizard_build_args TEMP_ARGS "$TITLE" "$INTENTS" "/dev/null" "/dev/null"

# Use Zenity's internal timeout + shell timeout for safety
timeout 1.5s zenity "${TEMP_ARGS[@]}" --timeout=1 >/dev/null 2>/tmp/zenity_smoke_err.log
EXIT_VAL=$?

# Exit 5 is Zenity's internal timeout code
# Exit 124 is the shell's timeout code
if [ $EXIT_VAL -eq 0 ] || [ $EXIT_VAL -eq 5 ] || [ $EXIT_VAL -eq 124 ]; then
    log_pass "Wizard UI launched and accepted arguments"
else
    log_fail "Wizard UI rejected arguments or failed to launch (Exit: $EXIT_VAL)"
    echo "  Error Log: $(cat /tmp/zenity_smoke_err.log)"
    exit 1
fi

echo -e "${GREEN}Zenity Smoke Test Passed!${NC}"
