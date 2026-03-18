#!/bin/bash
# testing/test_units.sh
# Unit tests for shared utility functions

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"
source "$PROJECT_ROOT/ffmpeg/common.sh"

echo -e "\n${YELLOW}=== Unit Tests: validate_time_format ===${NC}"

test_time() {
    local input="$1"
    local expected="$2"
    local result
    result=$(validate_time_format "$input")
    local status=$?
    
    if [ $status -eq 0 ] && [ "$result" = "$expected" ]; then
        log_pass "validate_time_format '$input' -> '$result'"
    elif [ $status -ne 0 ] && [ "$expected" = "FAIL" ]; then
        log_pass "validate_time_format '$input' -> FAILED (Expected)"
    else
        log_fail "validate_time_format '$input' -> Got '$result' (status $status), Expected '$expected'"
        return 1
    fi
}

FAILED=0
# Seconds
test_time "10" "10" || FAILED=$((FAILED+1))
test_time "10.5" "10.5" || FAILED=$((FAILED+1))

# MM:SS
test_time "01:30" "90" || FAILED=$((FAILED+1))
test_time "90:00" "5400" || FAILED=$((FAILED+1))
test_time "00:05.500" "5.500" || FAILED=$((FAILED+1))

# HH:MM:SS
test_time "01:00:00" "3600" || FAILED=$((FAILED+1))
test_time "00:01:30.500" "90.500" || FAILED=$((FAILED+1))

# Invalid
test_time "abc" "FAIL" || FAILED=$((FAILED+1))
test_time "1:2:3:4" "FAIL" || FAILED=$((FAILED+1))
test_time "60" "60" || FAILED=$((FAILED+1))

exit $FAILED
