#!/usr/bin/env bash
# Install the weekly deb-get/apt update check (user systemd timer).
set -euo pipefail
cd "$(dirname "$0")"

install -Dm755 check.sh "$HOME/.local/bin/deb-get-weekly-check.sh"
mkdir -p "$HOME/.config/systemd/user"
install -Dm644 systemd/deb-get-check.service "$HOME/.config/systemd/user/deb-get-check.service"
install -Dm644 systemd/deb-get-check.timer "$HOME/.config/systemd/user/deb-get-check.timer"

systemctl --user daemon-reload
systemctl --user enable --now deb-get-check.timer
systemctl --user list-timers | grep -E "deb-get|NEXT" || true
echo "Installed. Next run shown above. Test now with: systemctl --user start deb-get-check.service"
