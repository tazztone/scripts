#!/usr/bin/env bash
# Undo everything setup-profile2.sh created (system wrappers + Profile 2 data dirs).
# Run AFTER backup-profile2.sh verified: sudo ./uninstall-profile2.sh [--yes] [--dry-run] [--keep-data] [--force]
# Default is dry-run preview + confirmation: nothing is removed until you answer yes.
#   --yes        skip confirmation, remove immediately (for automation)
#   --dry-run    preview only, exit before removing anything
#   --keep-data  remove only system wrappers/desktop entries, keep home data dirs
#   --force      skip the backup-exists safety check (you backed up manually)
set -euo pipefail

[ "$(id -u)" -eq 0 ] || exec sudo bash "$0" "$@"

log() { printf '%s\n' "$*"; }

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

if [ -z "${SUDO_USER:-}" ]; then
  log "ERROR: run via sudo as your normal user (sudo ./uninstall-profile2.sh), not directly as root:"
  log "SUDO_USER is unset, so the Profile 2 data dirs cannot be resolved safely."
  exit 1
fi
if [ -z "$REAL_HOME" ] || [ ! -d "$REAL_HOME" ]; then
  log "ERROR: cannot resolve home dir for user $REAL_USER."
  exit 1
fi

YES=0
DRYRUN=0
KEEP_DATA=0
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes) YES=1 ;;
    --dry-run) DRYRUN=1 ;;
    --keep-data) KEEP_DATA=1 ;;
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "ERROR: Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

if ! ls -d "$REAL_HOME"/backups/antigravity-profile2-*/MANIFEST.txt >/dev/null 2>&1; then
  if [ "$DRYRUN" -eq 1 ]; then
    log "WARNING: no backup found yet (expected before the real run)."
  elif [ "$FORCE" -eq 0 ]; then
    log "ERROR: no backup found at $REAL_HOME/backups/antigravity-profile2-*/MANIFEST.txt."
    log "Run ./backup-profile2.sh first (as $REAL_USER), or re-run with --force."
    log "(If you backed up with --backup-root to a custom location, re-run with --force.)"
    exit 1
  fi
fi

SYS_PATHS="/usr/local/bin/antigravity-profile2 /usr/local/bin/antigravity-ide-profile2 /usr/local/bin/agy2
/usr/share/applications/antigravity-profile2.desktop /usr/share/applications/antigravity-ide-profile2.desktop
/opt/antigravity2 /opt/antigravity-ide2
/usr/local/bin/antigravity2 /usr/local/bin/antigravity-ide2 /usr/local/bin/update-antigravity2
/usr/local/bin/update-antigravity-ide2 /usr/local/bin/antigravity-linux2 /usr/local/bin/agy-profile2
/usr/share/applications/antigravity2.desktop /usr/share/applications/antigravity-ide2.desktop
/usr/share/icons/hicolor/512x512/apps/antigravity2.png /usr/share/icons/hicolor/512x512/apps/antigravity-ide2.png
/usr/share/nautilus-python/extensions/open-in-antigravity-ide2.py"

preview() {
  log "DRY RUN preview (nothing removed yet):"
  # shellcheck disable=SC2086
  for p in $SYS_PATHS; do
    if [ -e "$p" ]; then log "  REMOVE  $p"; else log "  (absent) $p"; fi
  done
  if [ "$KEEP_DATA" -eq 0 ]; then
    log "  data dirs for $REAL_USER (with sizes):"
    du -sh "$REAL_HOME/.antigravity-cli-account2" "$REAL_HOME/.config/antigravity-profile2" "$REAL_HOME/.config/Antigravity-IDE-profile2" 2>/dev/null | sed 's/^/    /' || true
  else
    log "  (--keep-data: home data dirs are kept)"
  fi
  log "  untouched: primary agy/antigravity/antigravity-ide, ~/.config/gh/hosts.yml, .env"
}

preview

if [ "$DRYRUN" -eq 1 ]; then
  log ""
  log "DRY RUN only: nothing was removed. Re-run without --dry-run to proceed for real."
  exit 0
fi

if [ "$YES" -eq 0 ]; then
  printf 'Proceed with removal for real? [y/N] '
  read -r ans < /dev/tty || { echo "Aborted: no terminal for confirmation (re-run with --yes or --dry-run)." >&2; exit 1; }
  case "$ans" in
    [yY]*) ;;
    *) echo "Aborted." >&2; exit 1 ;;
  esac
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
# shellcheck disable=SC2086
for p in $SYS_PATHS; do
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
