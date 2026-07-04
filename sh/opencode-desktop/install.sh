#!/usr/bin/env bash
# OpenCode Linux Installer/Updater
# Installs or updates OpenCode from the official .deb download link
# Usage: sudo install.sh [path/to/local.deb]

set -euo pipefail

DOWNLOAD_URL="https://opencode.ai/download/stable/linux-x64-deb"
TMP_DEB="/tmp/opencode_latest.deb"
SCRIPT_NAME="$(basename "$0")"

cleanup() {
    if [ -f "$TMP_DEB" ]; then
        rm -f "$TMP_DEB"
    fi
}

trap cleanup EXIT INT TERM

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root. Try: sudo $SCRIPT_NAME" >&2
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "ERROR: curl is required but not installed." >&2
    exit 1
fi

if ! command -v apt-get &> /dev/null; then
    echo "ERROR: apt-get is required but not installed." >&2
    exit 1
fi

if [ $# -gt 0 ]; then
    DEB_FILE="$1"
    if [ ! -f "$DEB_FILE" ]; then
        echo "ERROR: File not found: $DEB_FILE" >&2
        exit 1
    fi
    echo "Using local package: $DEB_FILE"
else
    DEB_FILE="$TMP_DEB"

    echo "Checking for existing OpenCode installation..."
    if dpkg -l | grep -q "opencode"; then
        echo "OpenCode is already installed. This will update it."
        OLD_VERSION=$(dpkg -l | grep opencode | awk '{print $3}')
        echo "Current version: $OLD_VERSION"
    fi

    echo "Downloading the latest OpenCode .deb package..."
    if ! curl -L# -o "$TMP_DEB" "$DOWNLOAD_URL"; then
        echo "ERROR: Failed to download OpenCode package." >&2
        exit 1
    fi

    if [ ! -s "$TMP_DEB" ]; then
        echo "ERROR: Downloaded file is empty." >&2
        exit 1
    fi

    FILE_SIZE=$(du -h "$TMP_DEB" | cut -f1)
    echo "Downloaded package size: $FILE_SIZE"
fi

echo "Installing OpenCode..."
if ! apt-get update -yq; then
    echo "WARNING: apt-get update failed, continuing with install..." >&2
fi

if ! apt-get install -y "$DEB_FILE"; then
    echo "ERROR: Failed to install OpenCode package." >&2
    exit 1
fi

NEW_VERSION=$(dpkg -l | grep opencode | awk '{print $3}')
echo "OpenCode installed/updated successfully!"
echo "Installed version: $NEW_VERSION"