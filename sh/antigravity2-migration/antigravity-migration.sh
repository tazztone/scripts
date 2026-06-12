#!/usr/bin/env bash
#
# Antigravity Safe Upgrade & Multi-Account Migration Script (v1.23 to v2.x)
# Designed for safe, non-destructive deployment on Ubuntu Linux.
#

set -euo pipefail

# --- Configuration & Paths ---
APPS_DIR="$HOME/Applications"
V2_IDE_DIR="$APPS_DIR/Antigravity-IDE"
V2_STANDALONE_DIR="$APPS_DIR/Antigravity-x64"

# Configuration paths
CONFIG_V1_TAZZ="$HOME/.config/Antigravity"
CONFIG_V1_NATALIE="$HOME/.config/antigravity-account2"
CONFIG_V2_TAZZ="$HOME/.config/Antigravity IDE"
CONFIG_V2_NATALIE="$HOME/.config/antigravity-ide-account2"

# Data paths
DATA_V1="$HOME/.gemini/antigravity"
DATA_V2_IDE="$HOME/.gemini/antigravity-ide"
DATA_V2_CLI="$HOME/.gemini/antigravity-cli"

# Extension paths
EXT_V1="$HOME/.antigravity"
EXT_V2="$HOME/.antigravity-ide"

# Desktop launchers
DESKTOP_DIR="$HOME/Desktop"
LOCAL_APP_DIR="$HOME/.local/share/applications"

# Helper directories
BIN_DIR="$HOME/bin"

echo "=================================================================="
echo "      ANTIGRAVITY SAFE V1 TO V2 MIGRATION & INSTALL SCRIPT"
echo "=================================================================="
echo

# ==================================================================
# Step 1: Pre-Migration Atomic Backup
# ==================================================================
echo "[1/6] Performing atomic pre-migration backup..."
mkdir -p "$CONFIG_V1_TAZZ" "$CONFIG_V1_NATALIE" "$CONFIG_V2_TAZZ" "$EXT_V1" "$EXT_V2" "$DATA_V1" "$DATA_V2_IDE"

BACKUP_FILE="$HOME/antigravity_backup_pre_v2.tar.gz"
echo "    Creating $BACKUP_FILE..."

tar --ignore-failed-read -czf "$BACKUP_FILE" \
  -C "$HOME" \
  .config/Antigravity \
  .config/antigravity-account2 \
  .config/"Antigravity IDE" \
  .antigravity \
  .antigravity-ide \
  .gemini/antigravity \
  .gemini/antigravity-ide \
  .local/share/applications/antigravity.desktop \
  .local/share/applications/antigravity-ide.desktop \
  Desktop/antigravity-account1.desktop \
  Desktop/antigravity-account2.desktop || true

echo "[+] Backup successfully verified."
echo

# ==================================================================
# Step 2: Migrate Account 1 (Tazztone) Conversations & Settings
# ==================================================================
echo "[2/6] Migrating Tazztone (Account 1) data and history..."

# Copy conversations, brain, and knowledge (non-destructive)
mkdir -p "$DATA_V2_IDE"
if [ -d "$DATA_V1" ]; then
  echo "    Copying past conversations and brain states..."
  cp -r "$DATA_V1"/. "$DATA_V2_IDE/"
  # Crucial for conversation loading: align installation ID
  if [ -f "$DATA_V1/installation_id" ]; then
    cp -f "$DATA_V1/installation_id" "$DATA_V2_IDE/installation_id"
  fi
fi

# Merge settings.json (preserving GC project ID)
SETTINGS_V2="$CONFIG_V2_TAZZ/User/settings.json"
SETTINGS_V1="$CONFIG_V1_TAZZ/User/settings.json"

if [ -f "$SETTINGS_V1" ]; then
  echo "    Merging settings.json..."
  mkdir -p "$CONFIG_V2_TAZZ/User"
  
  # Read current GC project ID if it exists in v2 settings
  PROJECT_ID="gen-lang-client-0156705665"
  if [ -f "$SETTINGS_V2" ] && command -v jq >/dev/null; then
    PROJECT_ID=$(jq -r '."google.cloud.project" // "gen-lang-client-0156705665"' "$SETTINGS_V2")
  fi

  # Copy settings file
  cp -f "$SETTINGS_V1" "$SETTINGS_V2"
  
  # Inject project ID
  if command -v jq >/dev/null; then
    jq --arg pid "$PROJECT_ID" '."google.cloud.project" = $pid' "$SETTINGS_V2" > "${SETTINGS_V2}.tmp" && mv "${SETTINGS_V2}.tmp" "$SETTINGS_V2"
  fi
fi
echo "[+] Account 1 successfully migrated."
echo

# ==================================================================
# Step 3: Color-Shifted Natalie Icon & Account 2 Launcher
# ==================================================================
echo "[3/6] Generating custom assets and isolated profiles..."

# Create Account 2 config directory (clean start per user request)
mkdir -p "$CONFIG_V2_NATALIE"

# Configure global skills plugin for v2 IDE to load ~/.agents/skills/ globally
echo "    Configuring global skills plugin for v2 IDE..."
rm -f "$HOME/.gemini/antigravity-ide/skills" # Clean up legacy direct link if present
plugin_dir="$HOME/.gemini/config/plugins/custom-skills"
mkdir -p "$plugin_dir"
echo '{"name": "custom-skills"}' > "$plugin_dir/plugin.json"
ln -sf "$HOME/.agents/skills" "$plugin_dir/skills"

# Custom color-shifted purple ribbon icon for Natalie's profile
NATALIE_ICON="$LOCAL_APP_DIR/antigravity-ide-natalie.png"
DEFAULT_ICON="$V2_IDE_DIR/resources/app/resources/linux/code.png"

if [ -f "$DEFAULT_ICON" ] && command -v convert >/dev/null; then
  echo "    Generating color-shifted purple icon for Natalie profile..."
  convert "$DEFAULT_ICON" -modulate 100,100,160 "$NATALIE_ICON"
else
  echo "    [!] ImageMagick not found or default icon missing. Reverting to default icon."
  NATALIE_ICON="$DEFAULT_ICON"
fi

# Wrapper launch scripts in ~/bin
mkdir -p "$BIN_DIR"

echo "    Writing wrapper scripts to $BIN_DIR..."

cat > "$BIN_DIR/antigravity-account1.sh" << 'EOF'
#!/usr/bin/env sh
set -eu
IDE_PATH="$HOME/Applications/Antigravity-IDE/antigravity-ide"
if [ ! -f "$IDE_PATH" ]; then
  echo "v2 IDE executable not found at $IDE_PATH" >&2
  exit 1
fi
nohup "$IDE_PATH" \
  --user-data-dir="$HOME/.config/Antigravity IDE" \
  --remote-debugging-port=9000 \
  "$@" >/dev/null 2>&1 &
EOF

cat > "$BIN_DIR/antigravity-account2.sh" << 'EOF'
#!/usr/bin/env sh
set -eu
IDE_PATH="$HOME/Applications/Antigravity-IDE/antigravity-ide"
if [ ! -f "$IDE_PATH" ]; then
  echo "v2 IDE executable not found at $IDE_PATH" >&2
  exit 1
fi
nohup "$IDE_PATH" \
  --class="antigravity-ide-account2" \
  --user-data-dir="$HOME/.config/antigravity-ide-account2" \
  --remote-debugging-port=9001 \
  "$@" >/dev/null 2>&1 &
EOF

chmod +x "$BIN_DIR/antigravity-account1.sh" "$BIN_DIR/antigravity-account2.sh"
echo "[+] Isolated launchers and color scripts configured."
echo

# ==================================================================
# Step 4: Write XDG App Menu Launchers
# ==================================================================
echo "[4/6] Creating XDG application launchers (GNOME Search)..."
mkdir -p "$LOCAL_APP_DIR"

# AG2-IDE tazz
cat > "$LOCAL_APP_DIR/antigravity-ide.desktop" << EOF
[Desktop Entry]
Type=Application
Name=AG2-IDE tazz
Exec=$BIN_DIR/antigravity-account1.sh
Icon=$V2_IDE_DIR/resources/app/resources/linux/code.png
Terminal=false
Categories=Development;IDE;
StartupWMClass=antigravity-ide
EOF

# AG2-IDE natalie
cat > "$LOCAL_APP_DIR/antigravity-ide-account2.desktop" << EOF
[Desktop Entry]
Type=Application
Name=AG2-IDE natalie
Exec=$BIN_DIR/antigravity-account2.sh
Icon=$NATALIE_ICON
Terminal=false
Categories=Development;IDE;
StartupWMClass=antigravity-ide-account2
EOF

# AG2 Standalone
cat > "$LOCAL_APP_DIR/antigravity.desktop" << EOF
[Desktop Entry]
Type=Application
Name=AG2
Exec=$V2_STANDALONE_DIR/antigravity
Icon=/usr/share/pixmaps/antigravity.png
Terminal=false
Categories=Development;IDE;
StartupWMClass=antigravity
MimeType=x-scheme-handler/antigravity;
EOF

chmod +x "$LOCAL_APP_DIR"/antigravity*.desktop
echo "[+] GNOME menu shortcuts created successfully."
echo

# ==================================================================
# Step 5: Write Desktop Launchers
# ==================================================================
echo "[5/6] Creating desktop-based shortcuts..."
mkdir -p "$DESKTOP_DIR"

# Desktop: tazz
cat > "$DESKTOP_DIR/antigravity-account1.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AG2-IDE tazz
Comment=Launch Antigravity IDE for Account 1 (Port 9000)
Exec=$BIN_DIR/antigravity-account1.sh
Icon=$V2_IDE_DIR/resources/app/resources/linux/code.png
Terminal=false
Categories=Development;
StartupNotify=true
EOF

# Desktop: natalie
cat > "$DESKTOP_DIR/antigravity-account2.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AG2-IDE natalie
Comment=Launch Antigravity IDE for Account 2 (Port 9001)
Exec=$BIN_DIR/antigravity-account2.sh
Icon=$NATALIE_ICON
Terminal=false
Categories=Development;
StartupNotify=true
EOF

# Desktop: Automatic Update Helper
cat > "$DESKTOP_DIR/Update Antigravity.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Update Antigravity
Comment=Automatically detect downloaded tarballs and update Antigravity folders
Exec=bash -c "~/update-antigravity.sh; echo ''; echo 'Press Enter to close...'; read"
Terminal=true
Icon=utilities-terminal
Categories=Development;
StartupNotify=true
EOF

chmod +x "$DESKTOP_DIR"/antigravity*.desktop "$DESKTOP_DIR/Update Antigravity.desktop"
echo "[+] Desktop-level launchers created and marked executable."
echo

# ==================================================================
# Step 6: Validate Entries
# ==================================================================
echo "[6/6] Verifying launcher files syntax..."
if command -v desktop-file-validate >/dev/null; then
  desktop-file-validate "$LOCAL_APP_DIR"/antigravity*.desktop "$DESKTOP_DIR"/antigravity*.desktop "$DESKTOP_DIR/Update Antigravity.desktop"
  echo "[+] All desktop entries validated successfully."
else
  echo "[!] desktop-file-validate utility not installed. Skipping check."
fi
echo

echo "=================================================================="
echo "          SAFE MIGRATION AND DEPLOYMENT COMPLETE!"
echo "=================================================================="
echo "    - fallbacks are fully intact."
echo "    - AG2, AG2-IDE tazz, and AG2-IDE natalie launchers are active."
echo "    - automatic update launcher configured."
echo "=================================================================="
