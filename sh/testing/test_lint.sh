#!/bin/bash
# testing/test_lint.sh
# Performs static syntax analysis on all shell scripts

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"

log_info "Starting Static Syntax Analysis (Linting)..."

FAILED=0
# Use -print0 and read -d '' to handle filenames with spaces and emojis
find "$PROJECT_ROOT" -name "*.sh" -not -path "*/.*" -print0 | while IFS= read -r -d '' script; do
    relative_path="${script#$PROJECT_ROOT/}"
    if bash -n "$script" 2>/tmp/lint_error.log; then
        log_pass "Syntax OK: $relative_path"
    else
        log_fail "Syntax ERROR: $relative_path"
        cat /tmp/lint_error.log
        echo "FAIL" > /tmp/lint_failed_marker
    fi
done

if [ ! -f /tmp/lint_failed_marker ]; then
    log_info "All scripts passed syntax check."
    exit 0
else
    rm /tmp/lint_failed_marker
    log_fail "Syntax check failed for one or more scripts."
    exit 1
fi
