# Antigravity IDE v1.23 to v2.x Safe Migration

This directory contains the automated installation/migration script (`antigravity-migration.sh`) and files designed to handle the safe, non-destructive upgrade from Antigravity v1.23 (apt-installed package) to Antigravity v2.x (standalone tarball distributions).

---

## What Was Accomplished This Session

1. **Pre-Migration Safety Backup:**
   * Package all original configurations, logs, and shortcuts into a compressed tarball: `~/antigravity_backup_pre_v2.tar.gz`.
   * **Frozen Fallback Policy:** The legacy apt-installed package `antigravity` remains completely untouched, and v1 configuration directories are treated as read-only snapshots to serve as a reliable fallback.

2. **Account 1 (`tazztone2@gmail.com`) Migration:**
   * Duplicated all **100+ conversation history files** (`.pb` protobuf files), brain states, and knowledge metadata from `~/.gemini/antigravity` into `~/.gemini/antigravity-ide`.
   * Merged user configurations and terminal profiles from `~/.config/Antigravity/User/settings.json` to `~/.config/Antigravity IDE/User/settings.json`, keeping the new Google Cloud project ID token (`gen-lang-client-...`) intact.
   * Extensions were skipped per user preference to allow a clean set of manual v2 installs.

3. **Account 2 (`nataliegemini91@gmail.com`) Setup:**
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

---

## Directory Mappings Summary

| Component | v1.23 Legacy (Frozen Fallback) | v2.x Tazztone IDE | v2.x Natalie IDE | v2.x Standalone App |
| :--- | :--- | :--- | :--- | :--- |
| **Settings Directory** | `~/.config/Antigravity` | `~/.config/Antigravity IDE` | `~/.config/antigravity-ide-account2` | `~/.config/Antigravity` |
| **Extensions Directory** | `~/.antigravity` | `~/.antigravity-ide` | `~/.antigravity-ide` (Shared) | N/A |
| **Logs & History Data** | `~/.gemini/antigravity` | `~/.gemini/antigravity-ide` | `~/.gemini/antigravity-ide` | `~/.gemini/antigravity-cli` |

*Note: CLI configuration registries remain fully isolated in `~/.antigravitycli` and `~/.gemini/antigravity-cli` and are never touched by this script.*

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
