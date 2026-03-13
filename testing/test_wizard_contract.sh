#!/bin/bash
# testing/test_wizard_contract.sh
# Verifies the contract between Zenity headers and data rows.

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"
source "$PROJECT_ROOT/common/wizard.sh"

echo -e "\n${YELLOW}=== Zenity Wizard Contract Validation ===${NC}"

# Helper to capture ARGS without running Zenity
capture_wizard_args() {
    local -a ARGS=()
    _wizard_build_args ARGS "Test" "📐|Scale|Desc;✂️|Crop|Desc" "/tmp/nonexistent_presets" "/tmp/nonexistent_history"
    
    local COLUMNS=0
    local DATA=0
    local IN_DATA=false
    
    local i=0
    while [ $i -lt ${#ARGS[@]} ]; do
        local arg="${ARGS[i]}"
        if [[ "$arg" == "--column" ]]; then
            ((COLUMNS++))
            ((i+=2)) # Skip flag and the header name
        elif [[ "$arg" == "--"* ]]; then
            # This is a flag. Does it take a value?
            # In our wizard, these flags take values:
            if [[ "$arg" == "--width" || "$arg" == "--height" || "$arg" == "--title" || "$arg" == "--separator" || "$arg" == "--print-column" || "$arg" == "--text" || "$arg" == "--hide-column" ]]; then
                ((i+=2))
            else
                ((i++))
            fi
        else
            # Positional argument (DATA)
            ((DATA++))
            ((i++))
        fi
    done
    
    echo "$COLUMNS|$DATA"
}

check_contract() {
    local RESULT=$(capture_wizard_args)
    IFS='|' read -r COLS DATA <<< "$RESULT"
    
    echo "  Detected Columns: $COLS"
    echo "  Detected Data Items (total): $DATA"
    
    local EXPECTED_PER_ROW=$COLS # All data items correspond to explicitly declared columns
    echo "  Expected Items Per Row: $EXPECTED_PER_ROW"
    echo "  Internal WIZARD_ROW_SIZE: $WIZARD_ROW_SIZE"
    
    if [ "$EXPECTED_PER_ROW" -ne "$WIZARD_ROW_SIZE" ]; then
        log_fail "Contract Mismatch: WIZARD_ROW_SIZE ($WIZARD_ROW_SIZE) does not match Headers ($EXPECTED_PER_ROW)"
        return 1
    fi
    
    if [ $((DATA % WIZARD_ROW_SIZE)) -ne 0 ]; then
        log_fail "Data Alignment Error: Total data items ($DATA) is not a multiple of WIZARD_ROW_SIZE ($WIZARD_ROW_SIZE)"
        return 1
    fi
    
    log_pass "Zenity Contract Validated"
    return 0
}

check_contract || exit 1
