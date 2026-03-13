#!/bin/bash
# testing/test_wizard_unit.sh
# Tests show_unified_wizard's internal parser logic in isolation

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"
# Source the file but we need to mock zenity so it doesn't try to open a window
source "$PROJECT_ROOT/common/wizard.sh"

log_info "Starting Isolated Wizard Parser Tests..."

# Mock zenity locally for these unit tests
zenity() {
    echo "$MOCK_RESULT"
}

test_parser() {
    local name="$1"
    local raw_input="$2"
    local expected="$3"
    
    # Inject the raw input into our local mock
    export MOCK_RESULT="$raw_input"
    
    # We need to capture the clean result. 
    # show_unified_wizard prints debug info to /tmp/scripts_debug.log and the result to stdout.
    local actual
    actual=$(show_unified_wizard "Test" "Icon|Name|Desc" "/tmp/null" "/tmp/null" 2>/dev/null | tail -n 1)
    
    if [[ "$actual" == "$expected" ]]; then
        log_pass "$name"
        return 0
    else
        log_fail "$name"
        echo "  Expected: [$expected]"
        echo "  Actual:   [$actual]"
        return 1
    fi
}

FAILED=0

# Test Group 1: Modern Zenity 4 (ALL column returns)
log_info "--- Test Group 1: Zenity 4.x (ALL Columns) ---"
test_parser "Zenity 4: Single checkbox" "TRUE|Scale|📐 Scale|Resize row|Scale" "Scale" || FAILED=$((FAILED+1))
test_parser "Zenity 4: Multiple checkboxes" "TRUE|Scale|📐 Scale|Resize row|Scale|TRUE|Crop|✂️ Crop|Crop row|Crop" "Scale|Crop" || FAILED=$((FAILED+1))
test_parser "Zenity 4: Double-Click (FALSE prefix)" "FALSE|Scale|📐 Scale|Resize row|Scale" "Scale" || FAILED=$((FAILED+1))
test_parser "Zenity 4: First row implicit (Enter key)" "FALSE|---|||---" "" || FAILED=$((FAILED+1))

# Test Group 2: Legacy Zenity 3 (Single column returns)
log_info "--- Test Group 2: Legacy Zenity 3 (Single Column) ---"
test_parser "Zenity 3: Simple string" "Scale" "Scale" || FAILED=$((FAILED+1))
test_parser "Zenity 3: Multiple pipes" "Scale|Crop" "Scale|Crop" || FAILED=$((FAILED+1))

# Test Group 3: Edge Cases
log_info "--- Test Group 3: Edge Cases ---"
test_parser "Empty return" "" "" || FAILED=$((FAILED+1))
test_parser "Pure FALSE (Cancel behavior)" "FALSE" "" || FAILED=$((FAILED+1))
test_parser "Pure TRUE (Weird state)" "TRUE" "" || FAILED=$((FAILED+1))
test_parser "Mixed garbage" "FALSE|---|||---|TRUE|Scale|📐 Scale|Resize row|Scale" "Scale" || FAILED=$((FAILED+1))

if [ $FAILED -eq 0 ]; then
    log_info "Isolated parser tests passed."
    exit 0
else
    log_fail "Isolated parser tests failed ($FAILED failures)."
    exit 1
fi
