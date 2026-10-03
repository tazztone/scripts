#!/usr/bin/env bash
# Backup Profile 2 data and unify chats into the primary ~/.gemini tree.
# Run as your normal user (NOT via sudo): ./backup-profile2.sh [--yes] [--backup-root DIR]
# Aborts if Antigravity/agy processes are running (open .db files copy corrupt)
# and verifies backup completeness before merging. Safe to re-run: copies use "missing-only" semantics and history merge appends
# only lines not already present.
set -euo pipefail

YES=0
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups}"

while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes) YES=1 ;;
    --backup-root) shift; [ $# -gt 0 ] || { echo "ERROR: --backup-root needs a directory" >&2; exit 1; }; BACKUP_ROOT="$1" ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "ERROR: Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

log() { printf '%s\n' "$*"; }

if [ "$(id -u)" -eq 0 ]; then
  echo "ERROR: run as your normal user, not root/sudo (paths are resolved via \$HOME)." >&2
  exit 1
fi

A2="$HOME/.antigravity-cli-account2/.gemini"
if [ ! -d "$A2" ]; then
  echo "ERROR: nothing to back up: $A2 not found." >&2
  exit 1
fi

# Exact process-name match (-x): matches the real binaries but can never match
# this script, its path (sh/antigravity2/), or parent launchers — unlike pgrep -f
# substring matching, which false-positives on any cmdline containing "antigravity".
STALE=$(pgrep -xa 'agy2?|antigravity(-ide)?|language_server' 2>/dev/null || true)
if [ -n "$STALE" ]; then
  echo "ERROR: Antigravity/agy processes still running (copying open .db files can corrupt the backup):" >&2
  echo "$STALE" | cut -c1-160 >&2
  echo "Quit them first, then re-run." >&2
  exit 1
fi

if [ "$YES" -eq 0 ]; then
  log "No Antigravity/agy processes running. Press Enter to back up + merge (Ctrl-C to abort)."
  # shellcheck disable=SC2034
  read -r _ < /dev/tty || { echo "Aborted." >&2; exit 1; }
fi

TS=$(date +%Y%m%d_%H%M%S)
BK="$BACKUP_ROOT/antigravity-profile2-$TS"
mkdir -p "$BK"

log "1. Backing up to $BK ..."
cp -a "$HOME/.antigravity-cli-account2" "$BK/" 2>/dev/null || true
[ -d "$HOME/.config/antigravity-profile2" ] && cp -a "$HOME/.config/antigravity-profile2" "$BK/" || true
[ -d "$HOME/.config/Antigravity-IDE-profile2" ] && cp -a "$HOME/.config/Antigravity-IDE-profile2" "$BK/" || true
cp -a /usr/local/bin/agy2 /usr/local/bin/antigravity-profile2 /usr/local/bin/antigravity-ide-profile2 "$BK/" 2>/dev/null || true
cp -a /usr/share/applications/antigravity-profile2.desktop /usr/share/applications/antigravity-ide-profile2.desktop "$BK/" 2>/dev/null || true
[ -f "$HOME/.config/gh/hosts.yml" ] && cp -a "$HOME/.config/gh/hosts.yml" "$BK/gh-hosts.yml" || true
[ -f "$HOME/.gemini/antigravity-cli/history.jsonl" ] && cp -a "$HOME/.gemini/antigravity-cli/history.jsonl" "$BK/host-history.jsonl" || true

{
  echo "backup-ts: $TS"
  echo "account2: $A2"
  du -sh "$HOME/.antigravity-cli-account2" "$HOME/.config/antigravity-profile2" "$HOME/.config/Antigravity-IDE-profile2" 2>/dev/null || true
} > "$BK/MANIFEST.txt"

log "Verifying backup completeness (aborts before merging on mismatch)..."
src_n=$(find "$HOME/.antigravity-cli-account2" | wc -l)
dst_n=$(find "$BK/.antigravity-cli-account2" | wc -l)
if [ "$dst_n" -lt "$src_n" ]; then
  echo "ERROR: backup incomplete ($dst_n of $src_n entries). Remove $BK and re-run." >&2
  exit 1
fi
log "  entry counts match ($dst_n)."

log "2. Merging chats into ~/.gemini (tokens excluded) ..."
for d in antigravity-cli antigravity; do
  [ -d "$A2/$d/conversations" ] || continue
  mkdir -p "$HOME/.gemini/$d/conversations"
  for f in "$A2/$d/conversations/"*.db; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    if [ -e "$HOME/.gemini/$d/conversations/$base" ]; then
      cp -n "$f" "$HOME/.gemini/$d/conversations/${base%.db}.acct2.db" 2>/dev/null || true
      log "  COLLISION kept both: $d/$base (acct2 copy has .acct2.db suffix)"
    else
      cp -n "$f" "$HOME/.gemini/$d/conversations/$base"
    fi
  done
  for sub in brain knowledge implicit crashes cache updater plugin_data scratch; do
    [ -d "$A2/$d/$sub" ] || continue
    mkdir -p "$HOME/.gemini/$d/$sub"
    cp -rn "$A2/$d/$sub/." "$HOME/.gemini/$d/$sub/" 2>/dev/null || true
  done
  [ -f "$A2/$d/conversation_summaries.db" ] \
    && cp -n "$A2/$d/conversation_summaries.db" "$HOME/.gemini/$d/conversation_summaries.acct2.db" 2>/dev/null || true
done

HOST_H="$HOME/.gemini/antigravity-cli/history.jsonl"
A2_H="$A2/antigravity-cli/history.jsonl"
if [ -f "$A2_H" ]; then
  touch "$HOST_H"
  NEW_LINES=$(grep -Fxv -f "$HOST_H" "$A2_H" 2>/dev/null | wc -l || true)
  if [ "${NEW_LINES:-0}" -gt 0 ]; then
    grep -Fxv -f "$HOST_H" "$A2_H" >> "$HOST_H" || true
    log "  history.jsonl: appended $NEW_LINES new line(s)"
  else
    log "  history.jsonl: already up to date (idempotent, nothing appended)"
  fi
fi

{
  echo "host cli conversations now: $(ls "$HOME/.gemini/antigravity-cli/conversations" 2>/dev/null | wc -l)"
  echo "host desktop conversations now: $(ls "$HOME/.gemini/antigravity/conversations" 2>/dev/null | wc -l)"
} | tee -a "$BK/MANIFEST.txt"

log ""
log "BACKUP_OK: $BK"
log "NOT merged (identity, re-auth from scratch): antigravity-oauth-token, oauth_creds.json,"
log "  google_accounts.json, installation_id*, jetski_state.pbtxt, cli.log, skills symlink."
log "Next: open agy, confirm an old Profile-2 session is listed, then run: sudo ./uninstall-profile2.sh"
