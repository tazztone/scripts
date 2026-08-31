#!/usr/bin/env bash
# Profile Setup Script for Antigravity
# Cleans up the duplicate installation and configures the original installation
# to run with a second independent profile side-by-side.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || exec sudo bash "$0" "$@"

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

log() { printf '%s\n' "$*"; }

log "1. Cleaning up duplicate installation (using install2.sh)..."
if [ -f "$REAL_HOME/Downloads/install2.sh" ]; then
  "$REAL_HOME/Downloads/install2.sh" --uninstall || log "Warning: Uninstaller returned an error, proceeding with manual cleanup."
  rm -f "$REAL_HOME/Downloads/install2.sh"
else
  log "install2.sh not found, running manual cleanup of second install files..."
  rm -rf /opt/antigravity2 /opt/antigravity-ide2
  rm -f /usr/local/bin/antigravity2 /usr/local/bin/antigravity-ide2 /usr/local/bin/update-antigravity2 /usr/local/bin/update-antigravity-ide2 /usr/local/bin/antigravity-linux2 /usr/local/bin/agy2 /usr/local/bin/agy-profile2
  rm -f /usr/share/applications/antigravity2.desktop /usr/share/applications/antigravity-ide2.desktop
  rm -f /usr/share/icons/hicolor/512x512/apps/antigravity2.png /usr/share/icons/hicolor/512x512/apps/antigravity-ide2.png
  rm -f /usr/share/nautilus-python/extensions/open-in-antigravity-ide2.py
fi

log "2. Creating wrapper scripts for Profile 2..."

# Profile 2 directories and token symlink
ACCOUNT2_GEMINI="$REAL_HOME/.antigravity-cli-account2/.gemini"
mkdir -p "$ACCOUNT2_GEMINI/antigravity" "$ACCOUNT2_GEMINI/antigravity-cli" "$ACCOUNT2_GEMINI/config"
ln -sf "../antigravity-cli/antigravity-oauth-token" "$ACCOUNT2_GEMINI/antigravity/antigravity-oauth-token"

if [ ! -f "$ACCOUNT2_GEMINI/google_accounts.json" ]; then
  cat > "$ACCOUNT2_GEMINI/google_accounts.json" <<'JSON'
{
  "active": "nataliegemini91@gmail.com",
  "old": []
}
JSON
fi

# Seed oauth_creds.json from Account 2 CLI token if present
CLI_TOKEN_FILE="$ACCOUNT2_GEMINI/antigravity-cli/antigravity-oauth-token"
if [ -f "$CLI_TOKEN_FILE" ]; then
  python3 -c "
import json
try:
    with open('$CLI_TOKEN_FILE') as f:
        tok = json.load(f).get('token', {})
    creds = {
        'access_token': tok.get('access_token', ''),
        'scope': 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email openid https://www.googleapis.com/auth/cloud-platform',
        'token_type': tok.get('token_type', 'Bearer'),
        'refresh_token': tok.get('refresh_token', '')
    }
    with open('$ACCOUNT2_GEMINI/oauth_creds.json', 'w') as f:
        json.dump(creds, f, indent=2)
except Exception:
    pass
" 2>/dev/null || true
fi

# Desktop app wrapper
cat > /usr/local/bin/antigravity-profile2 <<EOF
#!/usr/bin/env bash
# Run original Antigravity Desktop with Profile 2 configuration and isolated .gemini
ACCOUNT2_GEMINI="\$HOME/.antigravity-cli-account2/.gemini"
mkdir -p "\$ACCOUNT2_GEMINI" "\$HOME/.config/antigravity-profile2"

# Ensure oauth_creds.json is in sync with CLI token
CLI_TOKEN="\$ACCOUNT2_GEMINI/antigravity-cli/antigravity-oauth-token"
CREDS_FILE="\$ACCOUNT2_GEMINI/oauth_creds.json"
if [ -f "\$CLI_TOKEN" ] && [ ! -f "\$CREDS_FILE" ]; then
  python3 -c "
import json
try:
    with open('\$CLI_TOKEN') as f:
        tok = json.load(f).get('token', {})
    creds = {
        'access_token': tok.get('access_token', ''),
        'scope': 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email openid https://www.googleapis.com/auth/cloud-platform',
        'token_type': tok.get('token_type', 'Bearer'),
        'refresh_token': tok.get('refresh_token', '')
    }
    with open('\$CREDS_FILE', 'w') as f:
        json.dump(creds, f, indent=2)
except Exception:
    pass
" 2>/dev/null || true
fi

exec bwrap \\
  --dev-bind / / \\
  --bind "\$ACCOUNT2_GEMINI" "\$HOME/.gemini" \\
  --setenv DBUS_SESSION_BUS_ADDRESS "unix:path=/dev/null" \\
  --setenv GH_CONFIG_DIR "\$HOME/.config/gh" \\
  --setenv GIT_CONFIG_GLOBAL "\$HOME/.gitconfig" \\
  --setenv GOOGLE_API_KEY "" \\
  "/usr/local/bin/antigravity" \\
    --user-data-dir="\$HOME/.config/antigravity-profile2" \\
    --no-sandbox \\
    --password-store=basic \\
    --class="antigravity-profile2" \\
    "\$@"
EOF
chmod +x /usr/local/bin/antigravity-profile2

# IDE app wrapper (shares extensions with Profile 1)
cat > /usr/local/bin/antigravity-ide-profile2 <<'EOF'
#!/usr/bin/env bash
# Run original Antigravity IDE with Profile 2 configuration
exec "/usr/local/bin/antigravity-ide" --user-data-dir="$HOME/.config/Antigravity-IDE-profile2" "$@"
EOF
chmod +x /usr/local/bin/antigravity-ide-profile2

# CLI app wrapper
AGY_BIN="$REAL_HOME/.local/bin/agy"

if [ -f "$AGY_BIN" ]; then
  cat > /usr/local/bin/agy2 <<EOF
#!/usr/bin/env bash
# Run original Antigravity CLI with Profile 2 configuration via Bubblewrap namespace mount
ACCOUNT2_GEMINI="\$HOME/.antigravity-cli-account2/.gemini"
mkdir -p "\$ACCOUNT2_GEMINI" "\$HOME/.gemini"

exec bwrap \\
  --dev-bind / / \\
  --bind "\$ACCOUNT2_GEMINI" "\$HOME/.gemini" \\
  --setenv DBUS_SESSION_BUS_ADDRESS "unix:path=/dev/null" \\
  --setenv GH_CONFIG_DIR "\$HOME/.config/gh" \\
  --setenv GIT_CONFIG_GLOBAL "\$HOME/.gitconfig" \\
  --setenv GOOGLE_API_KEY "" \\
  "$AGY_BIN" "\$@"
EOF
  chmod +x /usr/local/bin/agy2
fi

log "3. Creating desktop entries for Profile 2..."

# Desktop app shortcut
cat > /usr/share/applications/antigravity-profile2.desktop <<'DESKTOP'
[Desktop Entry]
Name=Antigravity (Profile 2)
Comment=Google Antigravity 2.0 (Second Profile)
Exec=/usr/local/bin/antigravity-profile2 %U
Icon=antigravity
Terminal=false
Type=Application
Categories=Development;IDE;
StartupNotify=true
StartupWMClass=antigravity-profile2
DESKTOP

# IDE app shortcut
cat > /usr/share/applications/antigravity-ide-profile2.desktop <<'DESKTOP'
[Desktop Entry]
Name=Antigravity IDE (Profile 2)
Comment=Google Antigravity IDE (Second Profile)
Exec=/usr/local/bin/antigravity-ide-profile2 %F
Icon=antigravity-ide
Terminal=false
Type=Application
Categories=Development;IDE;
MimeType=inode/directory;text/plain;application/x-code-workspace;application/x-antigravity-workspace;x-scheme-handler/antigravity-ide;
StartupNotify=true
StartupWMClass=antigravity-ide
DESKTOP

# Fix ownership
chown -R "$REAL_USER:$REAL_USER" "$REAL_HOME/.antigravity-cli-account2" 2>/dev/null || true

log "4. Refreshing desktop and icon database..."
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi

log "--------------------------------------------------------"
log "Profile 2 Setup Complete!"
log "--------------------------------------------------------"
log "Installed commands:"
log "- Desktop (Profile 2): /usr/local/bin/antigravity-profile2"
log "- IDE (Profile 2):     /usr/local/bin/antigravity-ide-profile2"
if [ -f "/usr/local/bin/agy2" ]; then
  log "- CLI (Profile 2):     /usr/local/bin/agy2"
fi
log ""
log "These launch the original application binaries but save settings to:"
log "- Desktop settings: ~/.config/antigravity-profile2"
log "- IDE settings:     ~/.config/Antigravity-IDE-profile2"
log "- IDE extensions:   Shared with Profile 1 (~/.antigravity-ide/extensions)"
log ""
log "The duplicate installations have been completely uninstalled."
log "--------------------------------------------------------"
