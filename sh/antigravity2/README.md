# Antigravity Multi-Profile Management

Based on [github.com/opensnap/antigravity](https://github.com/opensnap/antigravity) with local installer caching and multi-profile enhancements.

This directory contains utility scripts to set up, configure, and manage multiple isolated user profiles/accounts for a single installation of Google Antigravity and Antigravity IDE on Linux.

---

## Directory Contents

| File | Description |
| :--- | :--- |
| **[install.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/install.sh)** | Enhanced Antigravity Linux installer script with local script caching, clean sudo execution, and offline fallback support. |
| **[setup-profile2.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/setup-profile2.sh)** | Portable helper script that cleans up duplicate installations and configures isolated wrapper launchers for Profile 2. |
| **[backup-profile2.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/backup-profile2.sh)** | Backs up all Profile 2 data and merges its chats into the primary `~/.gemini` tree. Dry-run preview + confirmation by default. |
| **[uninstall-profile2.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/uninstall-profile2.sh)** | Removes Profile 2 wrappers, desktop entries, and data dirs after a verified backup. Dry-run preview + confirmation by default. |

---

## 1. Installing & Updating Antigravity

Run `install.sh` to install or update Antigravity 2.0 Desktop and Antigravity IDE:

```bash
./install.sh --all
```

### System Management Commands
Once installed, helper commands are available system-wide:

* **Check status:** `antigravity-linux --status`
* **Update all components:** `sudo antigravity-linux update --all`
* **Update desktop app only:** `sudo update-antigravity`
* **Update IDE only:** `sudo update-antigravity-ide`
* **Uninstall system files:** `sudo antigravity-linux --uninstall`

*Note: The installer automatically caches a local copy at `/usr/local/share/antigravity-linux/install.sh`. This ensures `antigravity-linux update --all` can query https://antigravity.google/download directly for updates without requiring access to GitHub.*

---

## 2. Why Use Multiple Profiles?

Instead of installing two separate copies of the binary packages (which duplicates binaries, consumes excess disk space, and complicates updates), running two isolated user accounts side-by-side is best accomplished using command-line flags on the *original* installation.

The `setup-profile2.sh` script configures wrapper launchers and desktop menu entries for **Profile 2**.

---

## 3. How Profile Isolation Works

Both profiles share the core application binaries from the original installation. When launching Profile 2, the wrapper scripts pass parameters to isolate user data:

* **Desktop App (Profile 2):** Launched via `bwrap` with `--no-sandbox` and `~/.antigravity-cli-account2/.gemini` mounted over `~/.gemini`.
  * `DBUS_SESSION_BUS_ADDRESS="unix:path=/dev/null"` isolates Secret Service queries, preventing `language_server` from reading Account 1 from the host GNOME Keyring.
  * `--password-store=basic` enables plaintext local encryption for Chromium cookies in `~/.config/antigravity-profile2`.
  * `--class="antigravity-profile2"` pairs with `StartupWMClass=antigravity-profile2` in the desktop entry to keep dock and taskbar icons grouped separately from Profile 1.
  * `oauth_creds.json` (seeded with Google `id_token`, `access_token`, and `refresh_token`) and relative token symlinks (`jetski-standalone-oauth-token` and `antigravity/antigravity-oauth-token` → `antigravity-cli/antigravity-oauth-token`) allow the backend daemon to start directly authenticated as Account 2 without prompting or browser roundtrips.
* **IDE App (Profile 2):** Launched with `--user-data-dir="$HOME/.config/Antigravity-IDE-profile2"`. It shares installed extensions with Profile 1 (`~/.antigravity-ide/extensions`) while keeping settings, workspaces, and auth completely separate.
* **CLI App (Profile 2):** Launched via `bwrap` with `DBUS_SESSION_BUS_ADDRESS="unix:path=/dev/null"`, mounting `~/.antigravity-cli-account2/.gemini` over `~/.gemini` while preserving `$HOME`, dotfiles, `.ssh`, `.gitconfig`, and developer tools (`gh`, `git`).

This prevents configuration/login collisions and allows both sessions to run simultaneously.

---

## 4. Setting Up Profile 2

To configure the launchers for Profile 2:

1. Open terminal in this directory.
2. Run the setup helper script:
   ```bash
   sudo ./setup-profile2.sh
   ```

---

## 5. Launching Profile 2

Once setup is complete, you can launch Profile 2:

* **From your Application Menu:**
  * Search for and click on **Antigravity (Profile 2)** or **Antigravity IDE (Profile 2)**.
* **From the Command Line:**
  * Run Desktop (Profile 2): `antigravity-profile2`
  * Run IDE (Profile 2): `antigravity-ide-profile2`
  * Run CLI (Profile 2): `agy2`

---

## 6. Retiring Profile 2 (backup, merge, uninstall)

To consolidate back to a single profile: back up Profile 2, merge its chats into the primary tree, verify, then uninstall. Both scripts are **dry-run by default** — they always print a preview of exactly what they will do and ask `[y/N]` before modifying anything. `--dry-run` previews without prompting (and without modifying anything); `--yes` skips the confirmation for automation.

### Step 1 — Back up + merge (as your normal user, NOT via sudo)

```bash
./backup-profile2.sh [--yes] [--dry-run] [--backup-root DIR]
```

The script aborts if any `agy`/`antigravity`/`language_server` process is running (open `.db` files copy corrupt) and re-checks after confirmation. It then:

1. Copies `~/.antigravity-cli-account2`, `~/.config/antigravity-profile2`, and `~/.config/Antigravity-IDE-profile2` (plus the wrapper scripts, desktop entries, `gh` hosts file, and pre-merge host history) to `~/backups/antigravity-profile2-<timestamp>/` with a `MANIFEST.txt`, and aborts before merging if entry counts don't match on **all three** data dirs.
2. Merges chats into `~/.gemini` using missing-only semantics (safe to re-run): conversation `*.db` + `*.pb` files copy over, filename collisions are kept aside with an `.acct2` suffix (host files are never overwritten), `brain`/`knowledge`/`implicit`/`cache` and friends merge missing-only, `conversation_summaries.db` is copied aside as `*.acct2.db`, and new `history.jsonl` lines are appended (exact-line dedup, idempotent).
3. Deliberately does **not** merge identity: `antigravity-oauth-token`, `oauth_creds.json`, `google_accounts.json`, `installation_id*`, logs, and the skills symlink stay Profile 2-only (preserved in the backup).

The preview also runs a read-only mergeability check over every conversation database (readable schema, internal conversation id matches filename) and flags anomalies for manual review instead of failing.

> Size note: the bulk of Profile 2's disk footprint is regenerable cruft — tool caches (`.cache/ms-playwright-go`, pnpm, pre-commit), Chromium `Cache`, Electron `WebStorage`/`Crashpad` — none of which is merged. The valuable part (conversations, history, settings) is a small fraction.

### Step 2 — Verify in `agy`

Open `agy` and confirm an old Profile-2 session is listed (search for it — the list is sorted by recency, so older merged sessions sit further down). `agy` auto-indexes newly found `.db` files into its `conversation_summaries.db` on launch. Sessions it can't title will show with blank titles but intact previews; titles can be backfilled from the `conversation_summaries.acct2.db` copy (snapshot the host summaries db into the backup dir first, then `UPDATE … SET title=… WHERE title=''` for the merged ids).

### Step 3 — Uninstall (via sudo, after the backup is verified)

```bash
sudo ./uninstall-profile2.sh [--yes] [--dry-run] [--keep-data] [--force]
```

Removes the three wrapper scripts, both desktop entries, stale `*2` duplicates (`/opt/antigravity2`, `*2` binaries/desktops/icons), and — unless `--keep-data` — the three Profile 2 data dirs. Refuses to run directly as root, requires a backup containing `MANIFEST.txt` unless `--force`, and verifies every path is gone afterwards. Primary `agy`/`antigravity`/`antigravity-ide`, `~/.config/gh/hosts.yml`, and the (now inert) `.env` are intentionally left in place. Quit all Antigravity/`agy` processes before confirming.
