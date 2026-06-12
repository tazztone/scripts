#!/usr/bin/env bash
#
# Antigravity 2.0 Standalone Multi-Profile Setup Script
# Isolates two accounts (Tazz and Natalie) for the Standalone/x64 client.
#

set -euo pipefail

# --- Configuration & Paths ---
APPS_DIR="$HOME/Applications"
STANDALONE_DIR="$APPS_DIR/Antigravity-x64"
BIN_DIR="$HOME/bin"
LOCAL_APP_DIR="$HOME/.local/share/applications"
LOCAL_ICON_DIR="$HOME/.local/share/icons"
DESKTOP_DIR="$HOME/Desktop"

# Unique config folders for Standalone
CONFIG_STANDALONE_TAZZ="$HOME/.config/Antigravity Standalone"
CONFIG_STANDALONE_NATALIE="$HOME/.config/antigravity-standalone-account2"

# Ensure target directories exist
mkdir -p "$BIN_DIR" "$LOCAL_APP_DIR" "$LOCAL_ICON_DIR" "$DESKTOP_DIR" "$CONFIG_STANDALONE_NATALIE"

echo "=================================================================="
# Shortened title to avoid truncation warnings
echo "       ANTIGRAVITY 2.0 STANDALONE MULTI-ACCOUNT SETUP"
echo "=================================================================="
echo

# Helper function to safely backup existing files
safe_write() {
  local target="$1"
  local content="$2"
  if [ -f "$target" ]; then
    echo "    [Backup] Backing up existing $(basename "$target") to ${target}.bak"
    cp -f "$target" "${target}.bak"
  fi
  echo "$content" > "$target"
}

# ==================================================================
# Step 1: Manage Permanent Standalone Icons
# ==================================================================
echo "[1/4] Copying and preparing icons..."

DEFAULT_SYSTEM_ICON="/usr/share/pixmaps/antigravity.png"
PERMANENT_TAZZ_ICON="$LOCAL_ICON_DIR/antigravity-standalone.png"
PERMANENT_NATALIE_ICON="$LOCAL_ICON_DIR/antigravity-standalone-natalie.png"

# Check if we have a source icon to clone
SRC_ICON=""
if [ -f "$DEFAULT_SYSTEM_ICON" ]; then
  SRC_ICON="$DEFAULT_SYSTEM_ICON"
elif [ -d "$STANDALONE_DIR" ]; then
  # Try finding an icon inside the standalone folder if system package is gone
  found_icon=$(find "$STANDALONE_DIR" -name "*.png" | head -n 1 || true)
  if [ -n "$found_icon" ] && [ -f "$found_icon" ]; then
    SRC_ICON="$found_icon"
  fi
fi

if [ -n "$SRC_ICON" ]; then
  echo "    Source icon identified at: $SRC_ICON"
  cp -f "$SRC_ICON" "$PERMANENT_TAZZ_ICON"
  echo "    [+] Saved permanent un-shifted icon to $PERMANENT_TAZZ_ICON"

  # Detect image processing commands
  CONVERT_CMD=""
  if command -v convert >/dev/null; then
    CONVERT_CMD="convert"
  elif command -v magick >/dev/null; then
    CONVERT_CMD="magick"
  fi

  if [ -n "$CONVERT_CMD" ]; then
    echo "    [+] Generating color-shifted purple icon for Natalie using $CONVERT_CMD..."
    $CONVERT_CMD "$PERMANENT_TAZZ_ICON" -modulate 100,100,160 "$PERMANENT_NATALIE_ICON"
  else
    echo "    [!] ImageMagick not found (neither 'convert' nor 'magick' in PATH)."
    echo "        Falling back to identical icons for both accounts."
    cp -f "$PERMANENT_TAZZ_ICON" "$PERMANENT_NATALIE_ICON"
  fi
else
  echo "    [!] No base icon found. Falling back to system default names in desktop files."
  PERMANENT_TAZZ_ICON="antigravity"
  PERMANENT_NATALIE_ICON="antigravity"
fi
echo

# ==================================================================
# Step 2: Write Isolated Wrapper Scripts
# ==================================================================
echo "[2/4] Generating isolated wrapper launchers..."

TAZZ_WRAPPER_CONTENT=$(cat << 'EOF'
#!/usr/bin/env sh
set -eu
APP_PATH="$HOME/Applications/Antigravity-x64/antigravity"
if [ ! -f "$APP_PATH" ]; then
  echo "AG2 Standalone executable not found at $APP_PATH" >&2
  # Warning instead of direct exit allows testing launcher configurations
  echo "Please verify installation or run Update Helper." >&2
fi
nohup "$APP_PATH" \
  --user-data-dir="$HOME/.config/Antigravity Standalone" \
  --remote-debugging-port=9002 \
  "$@" >/dev/null 2>&1 &
EOF
)

NATALIE_WRAPPER_CONTENT=$(cat << 'EOF'
#!/usr/bin/env sh
set -eu
APP_PATH="$HOME/Applications/Antigravity-x64/antigravity"
if [ ! -f "$APP_PATH" ]; then
  echo "AG2 Standalone executable not found at $APP_PATH" >&2
  echo "Please verify installation or run Update Helper." >&2
fi
nohup "$APP_PATH" \
  --class="antigravity-standalone-account2" \
  --user-data-dir="$HOME/.config/antigravity-standalone-account2" \
  --remote-debugging-port=9003 \
  "$@" >/dev/null 2>&1 &
EOF
)

safe_write "$BIN_DIR/antigravity-standalone-account1.sh" "$TAZZ_WRAPPER_CONTENT"
safe_write "$BIN_DIR/antigravity-standalone-account2.sh" "$NATALIE_WRAPPER_CONTENT"
chmod +x "$BIN_DIR"/antigravity-standalone-*.sh
echo "[+] Standalone wrappers written to $BIN_DIR"
echo

# ==================================================================
# Step 3: Write XDG Applications Menu Shortcuts
# ==================================================================
echo "[3/4] Creating XDG application launchers (GNOME Search)..."

TAZZ_XDG_CONTENT=$(cat << EOF
[Desktop Entry]
Type=Application
Name=AG2 Standalone tazz
Exec=$BIN_DIR/antigravity-standalone-account1.sh
Icon=$PERMANENT_TAZZ_ICON
Terminal=false
Categories=Development;
StartupWMClass=antigravity
EOF
)

NATALIE_XDG_CONTENT=$(cat << EOF
[Desktop Entry]
Type=Application
Name=AG2 Standalone natalie
Exec=$BIN_DIR/antigravity-standalone-account2.sh
Icon=$PERMANENT_NATALIE_ICON
Terminal=false
Categories=Development;
StartupWMClass=antigravity-standalone-account2
EOF
)

safe_write "$LOCAL_APP_DIR/antigravity-standalone-tazz.desktop" "$TAZZ_XDG_CONTENT"
safe_write "$LOCAL_APP_DIR/antigravity-standalone-natalie.desktop" "$NATALIE_XDG_CONTENT"
chmod +x "$LOCAL_APP_DIR"/antigravity-standalone-*.desktop
echo "[+] GNOME menu shortcuts created successfully."
echo

# ==================================================================
# Step 4: Write Desktop Shortcuts
# ==================================================================
echo "[4/4] Creating Desktop shortcuts..."

TAZZ_DESKTOP_CONTENT=$(cat << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AG2 Standalone tazz
Comment=Launch AG2 Standalone for Account 1 (Port 9002)
Exec=$BIN_DIR/antigravity-standalone-account1.sh
Icon=$PERMANENT_TAZZ_ICON
Terminal=false
Categories=Development;
StartupNotify=true
EOF
)

NATALIE_DESKTOP_CONTENT=$(cat << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AG2 Standalone natalie
Comment=Launch AG2 Standalone for Account 2 (Port 9003)
Exec=$BIN_DIR/antigravity-standalone-account2.sh
Icon=$PERMANENT_NATALIE_ICON
Terminal=false
Categories=Development;
StartupNotify=true
EOF
)

safe_write "$DESKTOP_DIR/antigravity-standalone-tazz.desktop" "$TAZZ_DESKTOP_CONTENT"
safe_write "$DESKTOP_DIR/antigravity-standalone-natalie.desktop" "$NATALIE_DESKTOP_CONTENT"
chmod +x "$DESKTOP_DIR"/antigravity-standalone-*.desktop
echo "[+] Desktop-level launchers created."
echo

echo "=================================================================="
echo "          STANDALONE DEPLOYMENT INITIALIZED!"
echo "=================================================================="
echo "    - Ports 9002 (Tazz) & 9003 (Natalie) configured."
echo "    - Permanent standalone icons cached in ~/.local/share/icons/"
echo "    - GNOME and Desktop launchers created."
echo "=================================================================="
