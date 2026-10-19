#!/usr/bin/env bash
# Weekly update check: shows a desktop popup only when updates exist.
# Check phase needs NO sudo. Accepting the prompt opens a terminal
# where the upgrade runs (you enter your password there).
set -euo pipefail

for cmd in curl jq dpkg-query apt notify-send zenity; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command '$cmd' is not installed" >&2
    exit 1
  fi
done
if ! command -v x-terminal-emulator >/dev/null 2>&1; then
  echo "ERROR: x-terminal-emulator is required (install gnome-terminal or equivalent)" >&2
  exit 1
fi

export DEBGET_TOKEN="$(gh auth token 2>/dev/null || true)"
MSG=""

# 1. LACT via GitHub API (deb-get managed, github method)
INSTALLED=$(dpkg-query -Wf '${Version}' lact 2>/dev/null || true)
if [ -n "$INSTALLED" ]; then
  if [ -n "${DEBGET_TOKEN:-}" ]; then
    AUTH=(-H "Authorization: token $DEBGET_TOKEN")
  else
    AUTH=()
  fi
  LATEST_DEB=$(curl -s --max-time 15 "${AUTH[@]}" https://api.github.com/repos/ilya-zlobintsev/LACT/releases/latest \
    | jq -r '.assets[].browser_download_url // empty' 2>/dev/null | grep -m1 "amd64.*ubuntu-2604\.deb" || true)
  LATEST_VER=$(basename "${LATEST_DEB:-}" 2>/dev/null | sed -E 's/^lact-([0-9.]+)-.*/\1/' || true)
  if [ -n "${LATEST_VER:-}" ] && dpkg --compare-versions "$LATEST_VER" gt "$INSTALLED" 2>/dev/null; then
    MSG="LACT $INSTALLED → $LATEST_VER\n"
  fi
fi

# 2. Regular apt updates (no sudo needed to list)
APT_N=$(apt list --upgradable 2>/dev/null | grep -cv "^Listing" || true)
if [ "${APT_N:-0}" -gt 0 ]; then
  MSG="${MSG}${APT_N} apt updates available\n"
fi

[ -z "$MSG" ] && exit 0

notify-send -a deb-get "Updates available" "$(printf "%b" "$MSG")"

if zenity --question --title="Updates available" \
  --text="$(printf "%b" "$MSG")\nUpgrade now?" \
  --ok-label="Upgrade" --cancel-label="Later" --width=400; then
  x-terminal-emulator -e bash -c 'deb-get update && deb-get upgrade --dg-only; sudo apt upgrade -y; echo; read -p "Done. Press Enter to close."'
fi
