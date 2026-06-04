#!/usr/bin/env bash
#
# Antigravity Update Helper
# Automatically detects downloaded Antigravity tarballs and safely updates Applications folders.
#

set -euo pipefail

DOWNLOADS_DIRS=(
  "$HOME/Downloads"
  "$HOME/Downloads/Software_and_Archives"
)

APPS_DIR="$HOME/Applications"
IDE_TARGET="$APPS_DIR/Antigravity-IDE"
STANDALONE_TARGET="$APPS_DIR/Antigravity-x64"

echo "======================================================"
echo "          ANTIGRAVITY TARBALL UPDATE HELPER"
echo "======================================================"
echo

# 1. Look for downloaded tarballs
FOUND_IDE=""
FOUND_STANDALONE=""

for dir in "${DOWNLOADS_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    # Find newest Antigravity IDE tarball
    ide_file=$(find "$dir" -maxdepth 1 -iname "*antigravity*ide*.tar.gz" -o -iname "*antigravity*ide*.tgz" 2>/dev/null | sort -V | tail -n 1 || true)
    if [ -n "$ide_file" ] && [ -f "$ide_file" ]; then
      FOUND_IDE="$ide_file"
    fi

    # Find newest Antigravity Standalone tarball
    standalone_file=$(find "$dir" -maxdepth 1 -iname "*antigravity*x64*.tar.gz" -o -iname "*antigravity*x64*.tgz" -o \( -iname "*antigravity*.tar.gz" -a ! -iname "*ide*" \) 2>/dev/null | sort -V | tail -n 1 || true)
    if [ -n "$standalone_file" ] && [ -f "$standalone_file" ]; then
      FOUND_STANDALONE="$standalone_file"
    fi
  fi
done

if [ -z "$FOUND_IDE" ] && [ -z "$FOUND_STANDALONE" ]; then
  echo "[-] No new Antigravity tarballs found in your Downloads folders."
  echo "    Please download the latest v2 tarball from: https://antigravity.google/download"
  echo "    and place it in ~/Downloads."
  exit 1
fi

update_app() {
  local archive="$1"
  local target_dir="$2"
  local label="$3"

  echo "[+] Found $label tarball: $(basename "$archive")"
  echo "    Target directory: $target_dir"
  
  # Confirm extraction
  echo "    Updating..."
  
  # Create a safe backup of the existing directory
  local backup_dir="${target_dir}.bak"
  if [ -d "$target_dir" ]; then
    rm -rf "$backup_dir"
    mv "$target_dir" "$backup_dir"
  fi

  # Extract tarball
  mkdir -p "$target_dir"
  if tar -xzf "$archive" -C "$target_dir" --strip-components=1; then
    echo "[+] Successfully updated $label!"
    rm -rf "$backup_dir" # Delete backup only on success
    # Clean up the downloaded archive
    rm -f "$archive"
    echo "[+] Cleaned up $archive"
  else
    echo "[-] Extraction failed! Restoring backup..."
    if [ -d "$backup_dir" ]; then
      rm -rf "$target_dir"
      mv "$backup_dir" "$target_dir"
    fi
    exit 1
  fi
  echo
}

if [ -n "$FOUND_IDE" ]; then
  update_app "$FOUND_IDE" "$IDE_TARGET" "Antigravity IDE"
fi

if [ -n "$FOUND_STANDALONE" ]; then
  update_app "$FOUND_STANDALONE" "$STANDALONE_TARGET" "Antigravity Standalone"
fi

echo "======================================================"
echo "[+] Upgrade complete! Enjoy your updated Antigravity!"
echo "======================================================"
