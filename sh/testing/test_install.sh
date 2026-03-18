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

# Guaranteed cleanup
trap 'export HOME="$ORIG_HOME"; rm -rf "$MOCK_HOME"' EXIT

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
EXPECTED_LINKS=(
    "$HOME/.local/share/nautilus/scripts/🧰 Universal-Toolbox.sh"
    "$HOME/.local/share/nautilus/scripts/🖼️ Image-Magick-Toolbox.sh"
    "$HOME/.local/share/nautilus/scripts/🔒 Lossless-Operations-Toolbox.sh"
)

for LINK in "${EXPECTED_LINKS[@]}"; do
    if [ -L "$LINK" ]; then
        log_pass "install.sh created symlink successfully: $(basename "$LINK")"
    else
        log_fail "install.sh failed to create symlink at $LINK"
        FAILED=1
    fi
done

# Test 2: uninstall.sh
echo "Test 2: Running uninstall.sh"
(
    cd "$PROJECT_ROOT"
    bash uninstall.sh <<EOF
y
EOF
) &>/dev/null

for LINK in "${EXPECTED_LINKS[@]}"; do
    if [ ! -e "$LINK" ]; then
        log_pass "uninstall.sh removed symlink successfully: $(basename "$LINK")"
    else
        log_fail "uninstall.sh failed to remove symlink: $LINK"
        FAILED=1
    fi
done

exit $FAILED
