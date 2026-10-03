#!/usr/bin/env bash
# Undo everything setup-profile2.sh created (system wrappers + Profile 2 data dirs).
# Run AFTER backup-profile2.sh verified: sudo ./uninstall-profile2.sh [--yes] [--keep-data] [--force]
#   --keep-data  remove only system wrappers/desktop entries, keep home data dirs
#   --force      skip the backup-exists safety check (you backed up manually)
set -euo pipefail

[ "$(id -u)" -eq 0 ] || exec sudo bash "$0" "$@"

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

YES=0
KEEP_DATA=0
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes) YES=1 ;;
    --keep-data) KEEP_DATA=1 ;;
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) echo "ERROR: Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

log() { printf '%s\n' "$*"; }

if [ "$FORCE" -eq 0 ]; then
  if ! ls -d "$REAL_HOME"/backups/antigravity-profile2-* >/dev/null 2>&1; then
    log "ERROR: no backup found at $REAL_HOME/backups/antigravity-profile2-*."
    log "Run ./backup-profile2.sh first (as $REAL_USER), or re-run with --force."
    exit 1
  fi
fi

log "The following will be removed:"
log "  /usr/local/bin/antigravity-profile2 /usr/local/bin/antigravity-ide-profile2 /usr/local/bin/agy2"
log "  /usr/share/applications/antigravity-profile2.desktop /usr/share/applications/antigravity-ide-profile2.desktop"
log "  stale duplicates: /opt/antigravity2 /opt/antigravity-ide2 and *2/*-profile2 binaries/desktops"
if [ "$KEEP_DATA" -eq 0 ]; then
  log "  $REAL_HOME/.antigravity-cli-account2"
  log "  $REAL_HOME/.config/antigravity-profile2 $REAL_HOME/.config/Antigravity-IDE-profile2"
else
  log "  (--keep-data: home data dirs are kept)"
fi

if [ "$YES" -eq 0 ]; then
  log "Press Enter to continue (Ctrl-C to abort)."
  # shellcheck disable=SC2034
  read -r _ < /dev/tty || { echo "Aborted." >&2; exit 1; }
fi

log "1. Removing system wrappers and desktop entries..."
rm -f /usr/local/bin/antigravity-profile2 /usr/local/bin/antigravity-ide-profile2 /usr/local/bin/agy2
rm -f /usr/share/applications/antigravity-profile2.desktop /usr/share/applications/antigravity-ide-profile2.desktop
rm -rf /opt/antigravity2 /opt/antigravity-ide2
rm -f /usr/local/bin/antigravity2 /usr/local/bin/antigravity-ide2 /usr/local/bin/update-antigravity2 \
  /usr/local/bin/update-antigravity-ide2 /usr/local/bin/antigravity-linux2 /usr/local/bin/agy-profile2
rm -f /usr/share/applications/antigravity2.desktop /usr/share/applications/antigravity-ide2.desktop
rm -f /usr/share/icons/hicolor/512x512/apps/antigravity2.png /usr/share/icons/hicolor/512x512/apps/antigravity-ide2.png
rm -f /usr/share/nautilus-python/extensions/open-in-antigravity-ide2.py
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi

if [ "$KEEP_DATA" -eq 0 ]; then
  log "2. Removing Profile 2 data dirs for $REAL_USER..."
  rm -rf "$REAL_HOME/.antigravity-cli-account2" \
    "$REAL_HOME/.config/antigravity-profile2" \
    "$REAL_HOME/.config/Antigravity-IDE-profile2"
fi

log "3. Verifying..."
leftover=0
for p in /usr/local/bin/antigravity-profile2 /usr/local/bin/antigravity-ide-profile2 /usr/local/bin/agy2 \
  /usr/share/applications/antigravity-profile2.desktop /usr/share/applications/antigravity-ide-profile2.desktop; do
  if [ -e "$p" ]; then log "  STILL PRESENT: $p"; leftover=1; fi
done
if [ "$KEEP_DATA" -eq 0 ]; then
  for p in "$REAL_HOME/.antigravity-cli-account2" "$REAL_HOME/.config/antigravity-profile2" \
    "$REAL_HOME/.config/Antigravity-IDE-profile2"; do
    if [ -e "$p" ]; then log "  STILL PRESENT: $p"; leftover=1; fi
  done
fi

if [ "$leftover" -eq 0 ]; then
  log "UNINSTALL_OK: Profile 2 fully removed. Primary agy/antigravity/antigravity-ide untouched."
  log "gh file-token (~/.config/gh/hosts.yml) intentionally left in place; .env in sh/antigravity2 is now inert."
else
  log "WARNING: leftovers remain (see above)." >&2
  exit 1
fi
