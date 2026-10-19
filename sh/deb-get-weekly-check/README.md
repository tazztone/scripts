# deb-get Weekly Update Check

A weekly desktop reminder for updates that plain `apt` won't show you.
`deb-get` manages `.debs` from GitHub releases / direct downloads (e.g.
[LACT](https://github.com/ilya-zlobintsev/LACT)) that have no apt repository,
so `sudo apt upgrade` silently ignores them. This check pops up a notification
**only when updates exist**, with an `Upgrade / Later` prompt. Accepting opens
a terminal where the upgrade runs — nothing upgrades behind your back.

## The Problem
- `sudo apt upgrade` never updates `deb-get` (`github`/`direct`/`website` method) apps.
- `deb-get update && deb-get upgrade` works, but is easy to forget.

## The Solution
- [`check.sh`](check.sh) compares the installed LACT version (`dpkg-query`)
  against the latest GitHub release (authenticated API via `gh`, falls back to
  anonymous) and lists upgradable `apt` packages. The check needs **no sudo**.
- If anything is pending, it sends a `notify-send` notification and a `zenity`
  `Upgrade / Later` dialog detailing the updates found. `Upgrade` opens a terminal running
  `deb-get update && deb-get upgrade --dg-only` + `sudo apt upgrade -y`.
- [`systemd/`](systemd/) user timer runs the check weekly (Sundays 10:00,
  `Persistent=true` so missed runs catch up after the PC was off).

## Requirements
- Ubuntu/Debian with `deb-get` installed: https://github.com/wimpysworld/deb-get
- `curl`, `jq`, `zenity`, `libnotify-bin` (`notify-send`), a terminal
  providing `x-terminal-emulator`
- Optional: `gh` logged in (`gh auth login`) for a 5000/hr GitHub API limit
  instead of 60/hr anonymous. The script also honours `DEBGET_TOKEN` if exported.

## Usage

```bash
chmod +x check.sh install.sh uninstall.sh

# Install script to ~/.local/bin + enable weekly timer
./install.sh

# Force a check right now (popup appears only if updates found)
systemctl --user start deb-get-check.service

# Check timer status / next run
systemctl --user list-timers | grep deb-get

# Change schedule (e.g. daily 09:00): edit systemd/deb-get-check.timer,
# then re-run ./install.sh
```

## Files

```
deb-get-weekly-check/
├── check.sh                  # the check + popup (installed to ~/.local/bin/)
├── install.sh                # installs script + enables user timer
├── uninstall.sh              # disables timer, removes installed files
├── systemd/
│   ├── deb-get-check.service # user service running check.sh
│   └── deb-get-check.timer   # weekly schedule (Sun 10:00)
└── README.md
```

## Uninstall
```bash
./uninstall.sh
```
