#!/usr/bin/env bash
# Remove the weekly deb-get/apt update check.
set -euo pipefail

systemctl --user disable --now deb-get-check.timer 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/deb-get-check.service" \
      "$HOME/.config/systemd/user/deb-get-check.timer" \
      "$HOME/.local/bin/deb-get-weekly-check.sh"
systemctl --user daemon-reload
echo "Uninstalled."
