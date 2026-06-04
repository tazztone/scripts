#!/bin/bash
# testing/test_zenity_smoke.sh
# Smoke test for zenity to ensure binary is functional

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/lib_test.sh"

FAILED=0

echo -e "\n${YELLOW}=== Zenity Binary Smoke Test ===${NC}"

if [[ -z "${DISPLAY:-}" ]]; then
    log_info "Skipping zenity smoke (no DISPLAY)"
    exit 0
fi

# Test 1: Info (with timeout to avoid blocking)
echo "Test 1: Launching --info (Timeout 0.1s)"
timeout 0.1s zenity --info --text="Test" &>/dev/null
# timeout returns 124 if it timed out, which is EXPECTED for a dialog that stays open
STATUS=$?
if [ $STATUS -eq 0 ] || [ $STATUS -eq 124 ]; then
    log_pass "Zenity info launched successfully"
else
    log_fail "Zenity info failed to launch (Exit: $STATUS)"
    FAILED=1
fi

exit $FAILED
