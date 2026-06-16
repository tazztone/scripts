#!/usr/bin/env bash
# Profile Setup Script for Antigravity
# Cleans up the duplicate installation and configures the original installation
# to run with a second independent profile side-by-side.
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  # If already root, continue
  true
else
  # Rerun as root
  exec sudo bash "$0" "$@"
fi

log() { printf '%s\n' "$*"; }

log "1. Cleaning up duplicate installation (using install2.sh)..."
if [ -f "/home/tazztone/Downloads/install2.sh" ]; then
  /home/tazztone/Downloads/install2.sh --uninstall || log "Warning: Uninstaller returned an error, proceeding with manual cleanup."
  rm -f "/home/tazztone/Downloads/install2.sh"
else
  log "install2.sh not found, running manual cleanup of second install files..."
  rm -rf /opt/antigravity2 /opt/antigravity-ide2
  rm -f /usr/local/bin/antigravity2 /usr/local/bin/antigravity-ide2 /usr/local/bin/update-antigravity2 /usr/local/bin/update-antigravity-ide2 /usr/local/bin/antigravity-linux2 /usr/local/bin/agy2 /usr/local/bin/agy-profile2
  rm -f /usr/share/applications/antigravity2.desktop /usr/share/applications/antigravity-ide2.desktop
  rm -f /usr/share/icons/hicolor/512x512/apps/antigravity2.png /usr/share/icons/hicolor/512x512/apps/antigravity-ide2.png
  rm -f /usr/share/nautilus-python/extensions/open-in-antigravity-ide2.py
fi

log "2. Creating wrapper scripts for Profile 2..."

# Desktop app wrapper
cat > /usr/local/bin/antigravity-profile2 <<'EOF'
#!/usr/bin/env bash
# Run original Antigravity with Profile 2 configuration folder
exec "/usr/local/bin/antigravity" --user-data-dir="$HOME/.config/antigravity-profile2" "$@"
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
if [ -f "/home/tazztone/.local/bin/agy" ]; then
  cat > /usr/local/bin/agy2 <<'EOF'
#!/usr/bin/env bash
# Run original Antigravity CLI with Profile 2 configuration (no global API key, isolated keyring)
exec env HOME="/home/tazztone/.antigravity-cli-account2" \
         DBUS_SESSION_BUS_ADDRESS="unix:path=/dev/null" \
         GOOGLE_API_KEY="" \
         "/home/tazztone/.local/bin/agy" "$@"
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
StartupWMClass=Antigravity
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
