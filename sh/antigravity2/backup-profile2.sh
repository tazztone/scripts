#!/usr/bin/env bash
# Backup Profile 2 data and unify chats into the primary ~/.gemini tree.
# Run as your normal user (NOT via sudo): ./backup-profile2.sh [--yes] [--dry-run] [--backup-root DIR]
# Default is dry-run preview + confirmation: nothing is copied or merged until you answer yes.
#   --yes        skip confirmation, back up + merge immediately (for automation)
#   --dry-run    preview only, exit before modifying anything
# Aborts if Antigravity/agy processes are running (open .db files copy corrupt)
# and verifies backup completeness before merging. Safe to re-run: copies use "missing-only" semantics and history merge appends
# only lines not already present.
set -euo pipefail

YES=0
DRYRUN=0
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups}"

while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes) YES=1 ;;
    --dry-run) DRYRUN=1 ;;
    --backup-root) shift; [ $# -gt 0 ] || { echo "ERROR: --backup-root needs a directory" >&2; exit 1; }; BACKUP_ROOT="$1" ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
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

HOST_H="$HOME/.gemini/antigravity-cli/history.jsonl"
A2_H="$A2/antigravity-cli/history.jsonl"

# Exact process-name match (-x): matches the real binaries but can never match
# this script, its path (sh/antigravity2/), or parent launchers — unlike pgrep -f
# substring matching, which false-positives on any cmdline containing "antigravity".
check_stale() {
  local stale
  stale=$(pgrep -xa 'agy2?|antigravity(-ide)?|language_server' 2>/dev/null || true)
  if [ -n "$stale" ]; then
    echo "ERROR: Antigravity/agy processes still running (copying open .db files can corrupt the backup):" >&2
    echo "$stale" | cut -c1-160 >&2
    echo "Quit them first, then re-run." >&2
    exit 1
  fi
}

preview() {
  log "DRY RUN preview (nothing modified yet):"
  log ""
  log "Would back up (source sizes):"
  du -sh "$HOME/.antigravity-cli-account2" "$HOME/.config/antigravity-profile2" "$HOME/.config/Antigravity-IDE-profile2" 2>/dev/null | sed 's/^/  /' || true
  log "  target: $BACKUP_ROOT/antigravity-profile2-<timestamp>/"
  log ""
  log "Would merge into ~/.gemini:"
  for d in antigravity-cli antigravity; do
    [ -d "$A2/$d/conversations" ] || continue
    for f in "$A2/$d/conversations/"*.db "$A2/$d/conversations/"*.pb; do
      [ -e "$f" ] || continue
      base=$(basename "$f")
      if [ -e "$HOME/.gemini/$d/conversations/$base" ]; then
        log "  COLLISION (kept as .acct2): $d/$base"
      else
        log "  copy: $d/$base"
      fi
    done
    for sub in brain knowledge implicit crashes cache updater plugin_data scratch; do
      [ -d "$A2/$d/$sub" ] || continue
      log "  merge missing-only: $d/$sub ($(find "$A2/$d/$sub" -type f 2>/dev/null | wc -l) files on profile2 side)"
    done
  done
  if [ -f "$A2_H" ]; then
    if [ -f "$HOST_H" ]; then
      log "  history.jsonl: $(grep -Fxvc -f "$HOST_H" "$A2_H" 2>/dev/null || true) new line(s) would append"
    else
      log "  history.jsonl: host file absent, all $(wc -l < "$A2_H") acct2 line(s) would be written"
    fi
  else
    log "  history.jsonl: no profile2 history, nothing to merge"
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$A2" <<'PYEOF' || log "  (mergeability check skipped: python3 sqlite read failed)"
import sqlite3,glob,os,sys
bad=0
for f in sorted(glob.glob(sys.argv[1]+"/*/conversations/*.db")):
    try:
        con=sqlite3.connect('file:'+f+'?immutable=1',uri=True)
        m=con.execute("SELECT cascade_id FROM trajectory_meta").fetchall()
        con.close()
        if not m or m[0][0]!=os.path.basename(f)[:-3]:
            print("  ID-MISMATCH (kept aside, verify manually): "+os.path.basename(f)); bad+=1
    except Exception:
        print("  UNREADABLE (backup only, verify manually): "+os.path.basename(f)); bad+=1
if bad==0:
    print("  mergeability: all conversation files OK (readable, internal id matches filename)")
PYEOF
  else
    log "  (mergeability check skipped: python3 not found)"
  fi
  return 0
}

check_stale

preview

if [ "$DRYRUN" -eq 1 ]; then
  log ""
  log "DRY RUN only: nothing was copied or merged. Re-run without --dry-run to proceed for real."
  exit 0
fi

if [ "$YES" -eq 0 ]; then
  printf 'Proceed with backup + merge for real? [y/N] '
  read -r ans < /dev/tty || { echo "Aborted: no terminal for confirmation (re-run with --yes or --dry-run)." >&2; exit 1; }
  case "$ans" in
    [yY]*) ;;
    *) echo "Aborted." >&2; exit 1 ;;
  esac
  check_stale # re-check: something may have launched during the preview
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
for d in .antigravity-cli-account2 .config/antigravity-profile2 .config/Antigravity-IDE-profile2; do
  [ -e "$HOME/$d" ] || continue
  src_n=$(find "$HOME/$d" | wc -l)
  dst_n=$(find "$BK/$(basename "$d")" | wc -l)
  if [ "$dst_n" -lt "$src_n" ]; then
    echo "ERROR: backup of $d incomplete ($dst_n of $src_n entries). Remove $BK and re-run." >&2
    exit 1
  fi
  log "  $d: entry counts match ($dst_n)."
done

log "2. Merging chats into ~/.gemini (tokens excluded) ..."
for d in antigravity-cli antigravity; do
  [ -d "$A2/$d/conversations" ] || continue
  mkdir -p "$HOME/.gemini/$d/conversations"
  for f in "$A2/$d/conversations/"*.db "$A2/$d/conversations/"*.pb; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    if [ -e "$HOME/.gemini/$d/conversations/$base" ]; then
      cp -n "$f" "$HOME/.gemini/$d/conversations/${base%.*}.acct2.${base##*.}" 2>/dev/null || true
      log "  COLLISION kept both: $d/$base (acct2 copy has .acct2 suffix)"
    else
      cp -n "$f" "$HOME/.gemini/$d/conversations/$base" 2>/dev/null || true
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

if [ -f "$A2_H" ]; then
  mkdir -p "$(dirname "$HOST_H")"
  touch "$HOST_H"
  DIFF_LINES=$(grep -Fxv -f "$HOST_H" "$A2_H" 2>/dev/null || true)
  if [ -n "$DIFF_LINES" ]; then
    printf '%s\n' "$DIFF_LINES" >> "$HOST_H"
    NEW_LINES=$(printf '%s\n' "$DIFF_LINES" | wc -l)
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
log "conversation_summaries.db was copied aside as *.acct2.db (sqlite, merge by hand if needed)."
log "Next: open agy, confirm an old Profile-2 session is listed, then run: sudo ./uninstall-profile2.sh"
