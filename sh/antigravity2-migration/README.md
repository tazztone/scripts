# Antigravity IDE v1.23 to v2.x Safe Migration

This directory contains the automated installation/migration script (`antigravity-migration.sh`) and files designed to handle the safe, non-destructive upgrade from Antigravity v1.23 (apt-installed package) to Antigravity v2.x (standalone tarball distributions).

---

## What Was Accomplished This Session

1. **Pre-Migration Safety Backup:**
   * Package all original configurations, logs, and shortcuts into a compressed tarball: `~/antigravity_backup_pre_v2.tar.gz`.
   * **Frozen Fallback Policy:** The legacy apt-installed package `antigravity` remains completely untouched, and v1 configuration directories are treated as read-only snapshots to serve as a reliable fallback.

2. **Account 1 Migration:**
   * Duplicated all **100+ conversation history files** (`.pb` protobuf files), brain states, and knowledge metadata from `~/.gemini/antigravity` into `~/.gemini/antigravity-ide`.
   * Merged user configurations and terminal profiles from `~/.config/Antigravity/User/settings.json` to `~/.config/Antigravity IDE/User/settings.json`, keeping the new Google Cloud project ID token (`gen-lang-client-...`) intact.
   * Extensions were skipped per user preference to allow a clean set of manual v2 installs.

3. **Account 2 Setup:**
   * Configured an isolated, fresh config directory `~/.config/antigravity-ide-account2` (skipping old config copying to ensure complete compatibility).
   * Generates a custom, isolated user profile upon launch to let the user switch between Tazztone and Natalie seamlessly.

4. **GNOME Search Truncation and Sorting UX Fix:**
   * GNOME Shell displays desktop shortcut labels truncated (e.g. `Antigravity IDE` became `Antigra...`).
   * Re-engineered shortcuts to use unique sorting-optimized names with identifiers first:
     * **`AG2-IDE tazz`** (Account 1 IDE) - Uses default wave icon.
     * **`AG2-IDE natalie`** (Account 2 IDE) - Uses custom ImageMagick **color-shifted purple ribbon icon**.
     * **`AG2`** (Standalone client) - Uses system-wide launcher icon.
   * Shortcuts automatically align alphabetically and remain fully readable.

5. **Automated One-Click Tarball Update Helper:**
   * Created `~/update-antigravity.sh` and a Desktop shortcut `Update Antigravity.desktop`.
   * Automatically detects newly downloaded Antigravity tarballs in `~/Downloads` or `~/Downloads/Software_and_Archives`.
   * Safely backs up active installations (`.bak`), extracts files, handles directory replacements, cleans up downloads, and features an auto-rollback in case of write errors.

6. **Global Custom Skills Resolution:**
   * In v2, skills are strictly project-isolated under `.agents/skills/` relative to the opened workspace root. 
   * Opening project subdirectories (e.g. `/home/tazztone/_coding/shinestacker`) hid your home directory's custom skills directory (`~/.agents/skills`) from the v2 IDE.
   * **Fix applied:** Created a global plugin `~/.gemini/config/plugins/custom-skills` containing a `plugin.json` manifest and a symbolic link `skills` pointing directly to `~/.agents/skills`. This maps your custom skills globally so they automatically load in the v2 IDE across all projects!

7. **Standalone Multi-Profile Isolation Setup:**
   * Created `setup-ag2-standalone-multi.sh` to configure isolated environments for Antigravity Standalone.
   * Configures Tazz (Port 9002) and Natalie (Port 9003) on isolated profiles and distinct WM classes (`--class`).
   * Backs up existing launcher files before writing updates and persists icons under `~/.local/share/icons/`.

8. **CLI (agy) Multi-Profile Isolation Setup:**
   * Created `setup-ag2-cli-multi.sh` to configure isolated environments for the `agy` CLI tool.
   * Configures Tazz (`agy` / `agy-tazz` using default home path) and Natalie (`agy2` using `HOME=~/.antigravity-cli-account2`).
   * Ensures Natalie's CLI config, conversation history, brain state, and logs are kept 100% separate from Tazz's CLI session.

---

## Directory & Port Mappings Summary

### IDE & Standalone Clients

| Component | v1.23 Legacy (Frozen Fallback) | v2.x Tazz IDE | v2.x Natalie IDE | v2.x Tazz Standalone | v2.x Natalie Standalone |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Settings Dir** | `~/.config/Antigravity` | `~/.config/Antigravity IDE` | `~/.config/antigravity-ide-account2` | `~/.config/Antigravity Standalone` | `~/.config/antigravity-standalone-account2` |
| **Extensions Dir** | `~/.antigravity` | `~/.antigravity-ide` | `~/.antigravity-ide` (Shared) | N/A | N/A |
| **Logs/History Dir**| `~/.gemini/antigravity` | `~/.gemini/antigravity-ide` | `~/.gemini/antigravity-ide` | `~/.gemini/antigravity-cli` | `~/.gemini/antigravity-cli` |
| **Debug Port** | N/A | `9000` | `9001` | `9002` | `9003` |
| **GNOME WM Class**| `antigravity` | `antigravity-ide` | `antigravity-ide-account2` | `antigravity` | `antigravity-standalone-account2` |

### CLI (agy) Client

| Profile | Command | Config / History Directory | Log File Path |
| :--- | :--- | :--- | :--- |
| **Tazz CLI** | `agy` (or `agy-tazz`) | `~/.gemini/antigravity-cli` | `~/.gemini/antigravity-cli/cli.log` |
| **Natalie CLI** | `agy2` | `~/.antigravity-cli-account2/.gemini/antigravity-cli` | `~/.antigravity-cli-account2/.gemini/antigravity-cli/cli.log` |

*Note: CLI configuration registries are isolated under separate HOME roots for `agy` and `agy2` to ensure complete authentication and history division.*

---

## Troubleshooting: Migrated Conversations Not Displaying

In Google Antigravity 2.0, conversation files (`.pb` protobuf files) are tied to a combination of:
1. The **`installation_id`** (a UUID string stored in `~/.gemini/<product>/installation_id`).
2. The local project index database or the `projects.json` file.

Because v2 generated a fresh `installation_id` upon its first run, it may fail to display the conversations copied from v1 since the UUIDs do not align.

### How to Fix:
1. **Force Installation ID Alignment:**
   Copy the legacy installation ID over to the v2 IDE path so that the applications share the identical identifier:
   ```bash
   cp -f ~/.gemini/antigravity/installation_id ~/.gemini/antigravity-ide/installation_id
   ```
2. **Re-Open Project folders:**
   Open the target directories (e.g. `/home/tazztone`) inside the v2 IDE. Antigravity will scan the folders and map past project history metadata matching the aligned installation UUID.

---

## 🧠 Architectural Lessons & Roadblocks Resolved

Here are the key roadblocks encountered during the session and how they were resolved. Documented here for reference to prevent regressions:

### 1. Keyring Leakage & DBus Session Fallbacks
* **Problem:** Isolating `$HOME` for the `agy2` CLI session still resulted in it reading and displaying Tazz's login profile (`tazztone2@gmail.com`).
* **Root Cause:** The Go-based CLI uses `go-keyring`, which connects to the system's shared Secret Service via DBus. If `DBUS_SESSION_BUS_ADDRESS` is empty or unset, modern DBus clients automatically fallback to `$XDG_RUNTIME_DIR/bus` (resolving to `/run/user/1000/bus`), accessing your main user session keyring anyway.
* **Resolution:** Set `export DBUS_SESSION_BUS_ADDRESS="unix:path=/dev/null/nonexistent"` (a valid DBus format pointing to a dead socket). This forces the keyring connection to immediately fail and aborts the automatic socket fallback, cleanly triggering the CLI's native file-based token storage fallback inside the isolated `~/.antigravity-cli-account2` directory.

### 2. Parent Process Environment Hijacking (`ANTIGRAVITY_LS_ADDRESS`)
* **Problem:** Running the isolated CLI `agy2` from inside an IDE terminal shell or subagent terminal hijacked the parent IDE's active server context.
* **Root Cause:** The CLI detects `ANTIGRAVITY_LS_ADDRESS` to latch onto a running IDE server instead of launching its own process.
* **Resolution:** Natalie's wrapper script explicitly clears the parent shell environment by matching and unsetting all `ANTIGRAVITY_*` environment variables.

### 3. GNOME Dock Stacking & Sorting UX
* **Problem:** GNOME stacked all running IDE instances behind a single icon, making switches confusing, and truncated sorting names on search.
* **Resolution:** 
  1. Set custom `--class="<id>"` startup arguments for Account 2 profile wrappers.
  2. Sync `StartupWMClass` matching entries inside desktop launcher files.
  3. Prepend short, unique alphabetical sorting labels (`AG2-IDE tazz`, `AG2-IDE natalie`) to bypass GNOME menu label truncation.
