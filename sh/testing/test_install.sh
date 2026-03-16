#!/bin/bash
# testing/test_install.sh
# Tests install.sh and uninstall.sh by mocking HOME

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"

FAILED=0

echo -e "\n${YELLOW}=== Installation & Uninstallation Tests ===${NC}"

# Setup mock environment
MOCK_HOME=$(mktemp -d)
ORIG_HOME="$HOME"
export HOME="$MOCK_HOME"

# Mock zenity to always "Overwrite" or "Confirm"
setup_mock_zenity
echo "Overwrite" > /tmp/zenity_responses # For install.sh question if any

# Test 1: install.sh
echo "Test 1: Running install.sh"
(
    cd "$PROJECT_ROOT"
    bash install.sh <<EOF
y
EOF
) &>/dev/null

# Verify symlinks
EXPECTED_LINK="$HOME/.local/share/nautilus/scripts/🧰 Universal-Toolbox.sh"
if [ -L "$EXPECTED_LINK" ]; then
    log_pass "install.sh created symlink successfully"
else
    log_fail "install.sh failed to create symlink at $EXPECTED_LINK"
    ls -R "$HOME" # Debug
    FAILED=1
fi

# Test 2: uninstall.sh
echo "Test 2: Running uninstall.sh"
(
    cd "$PROJECT_ROOT"
    bash uninstall.sh <<EOF
y
EOF
) &>/dev/null

if [ ! -e "$EXPECTED_LINK" ]; then
    log_pass "uninstall.sh removed symlink successfully"
else
    log_fail "uninstall.sh failed to remove symlink"
    FAILED=1
fi

# Cleanup
export HOME="$ORIG_HOME"
rm -rf "$MOCK_HOME"

exit $FAILED
