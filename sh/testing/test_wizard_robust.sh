#!/bin/bash
# testing/test_wizard_robust.sh
# Comprehensive tests for show_unified_wizard's internal parser logic
# Covers Zenity 3 (single col), Zenity 4 (multiple col), and different field counts.

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"
source "$PROJECT_ROOT/common/wizard.sh"

log_info "Starting Robust Wizard Parser Tests..."

# Mock zenity locally
zenity() {
    echo "$MOCK_RESULT"
}

# Helper to test the parser in isolation
test_parser_isolated() {
    local name="$1"
    local raw_input="$2"
    local expected="$3"
    
    local actual
    actual=$(_wizard_parse_result "$raw_input")
    
    if [[ "$actual" == "$expected" ]]; then
        log_pass "$name"
        return 0
    else
        log_fail "$name"
        echo "  Input:    [$raw_input]"
        echo "  Expected: [$expected]"
        echo "  Actual:   [$actual]"
        return 1
    fi
}

FAILED=0

# --- Test Group 1: Modern Zenity 4 (Checklist with ALL columns) ---
# Format: [STATE] | [Col1:Pick] | [Col2:Action] | [Col3:Desc] | [Col4:ID] | [Col5:RawID]
# This is 6 fields per row.
log_info "--- Test Group 1: Zenity 4 (5 fields/row) ---"
test_parser_isolated "Z4: Single selection" "TRUE|📐 Scale|Scale|Resize|Scale" "Scale" || FAILED=$((FAILED+1))
test_parser_isolated "Z4: Double selection" "TRUE|📐 Scale|Scale|Resize|Scale|TRUE|✂️ Crop|Crop|Move|Crop" "Scale|Crop" || FAILED=$((FAILED+1))
test_parser_isolated "Z4: Double-Click (All FALSE, one selected)" "FALSE|📐 Scale|Scale|Resize|Scale" "Scale" || FAILED=$((FAILED+1))
test_parser_isolated "Z4: Divider selected (Should skip)" "TRUE|═══|||═══" "" || FAILED=$((FAILED+1))
test_parser_isolated "Z4: Mixed with divider" "TRUE|📐 Scale|Scale|Resize|Scale|TRUE|═══|||═══|TRUE|✂️ Crop|Crop|Move|Crop" "Scale|Crop" || FAILED=$((FAILED+1))

# --- Test Group 2: Legacy Zenity 3 (Single column) ---
log_info "--- Test Group 2: Zenity 3 (Single column) ---"
test_parser_isolated "Z3: Simple string" "Scale" "Scale" || FAILED=$((FAILED+1))
test_parser_isolated "Z3: Multiple pipes" "Scale|Crop" "Scale|Crop" || FAILED=$((FAILED+1))

# --- Test Group 3: Edge Cases ---
log_info "--- Test Group 3: Edge Cases ---"
test_parser_isolated "Empty result" "" "" || FAILED=$((FAILED+1))
test_parser_isolated "Wait/Cancel return" "FALSE" "" || FAILED=$((FAILED+1))
test_parser_isolated "Pure TRUE" "TRUE" "" || FAILED=$((FAILED+1))
test_parser_isolated "Garbage prefix" "nonsense|TRUE|📐 Scale|Scale|Resize|Scale|Scale" "nonsense|TRUE|📐 Scale|Scale|Resize|Scale|Scale" || FAILED=$((FAILED+1))

if [ $FAILED -eq 0 ]; then
    log_info "Robust parser tests passed."
    exit 0
else
    log_fail "Robust parser tests failed ($FAILED failures)."
    exit 1
fi
