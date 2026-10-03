#!/usr/bin/env bash
# OpenCode Linux Uninstaller
# Removes the OpenCode .deb installation
# Usage: sudo uninstall.sh [--purge]

set -euo pipefail

PACKAGE="opencode"
SCRIPT_NAME="$(basename "$0")"
PURGE=false

if [ "${1:-}" = "--purge" ]; then
    PURGE=true
elif [ $# -gt 0 ]; then
    echo "Usage: sudo $SCRIPT_NAME [--purge]" >&2
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root. Try: sudo $SCRIPT_NAME" >&2
    exit 1
fi

if ! command -v apt-get &> /dev/null; then
    echo "ERROR: apt-get is required but not installed." >&2
    exit 1
fi

STATUS=$(dpkg-query -W -f='${Status}' "$PACKAGE" 2>/dev/null || echo "not-installed")

if [ "$STATUS" = "install ok installed" ]; then
    VERSION=$(dpkg-query -W -f='${Version}' "$PACKAGE" 2>/dev/null)
    echo "Found OpenCode version: $VERSION"
elif [ "$STATUS" = "deinstall ok config-files" ]; then
    if [ "$PURGE" = true ]; then
        echo "OpenCode is already removed; purging remaining config files..."
    else
        echo "OpenCode is already removed (only config files remain)."
        echo "Re-run with --purge to clear them."
        exit 0
    fi
else
    echo "OpenCode is not installed (package '$PACKAGE' not found)."
    exit 0
fi

if [ "$PURGE" = true ]; then
    echo "Purging OpenCode (including system config files)..."
    apt-get purge -y "$PACKAGE"
else
    echo "Removing OpenCode..."
    apt-get remove -y "$PACKAGE"
fi

if ! apt-get autoremove -yq; then
    echo "WARNING: apt-get autoremove failed." >&2
fi

if dpkg-query -W -f='${Status}' "$PACKAGE" 2>/dev/null | grep -q "ok installed"; then
    echo "ERROR: OpenCode package is still present." >&2
    exit 1
fi

echo "OpenCode uninstalled successfully!"
if [ "$PURGE" = false ]; then
    echo "Note: user config in ~/.opencode was left untouched. Re-run with --purge"
    echo "      + manual 'rm -rf ~/.opencode' for a full wipe."
fi
