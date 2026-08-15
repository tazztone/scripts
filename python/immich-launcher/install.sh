#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$HOME/.local/share/immich"
APP_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$HOME/Desktop"

echo "==> Installing Immich One-Click Launcher..."

# 1. Ensure runtime directories
mkdir -p "$DATA_DIR" "$APP_DIR" "$DESKTOP_DIR"

# 2. Copy launcher script
cp "$SCRIPT_DIR/launch-immich.sh" "$DATA_DIR/launch-immich.sh"
chmod +x "$DATA_DIR/launch-immich.sh"

# 3. Copy desktop entry
cp "$SCRIPT_DIR/immich.desktop" "$APP_DIR/immich.desktop"
cp "$SCRIPT_DIR/immich.desktop" "$DESKTOP_DIR/Immich.desktop"
chmod +x "$APP_DIR/immich.desktop" "$DESKTOP_DIR/Immich.desktop"

# 4. Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi

echo "==> Installation complete! Immich launcher is ready on your Desktop and Application menu."
