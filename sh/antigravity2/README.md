# Antigravity Multi-Profile Management

Based on [github.com/opensnap/antigravity](https://github.com/opensnap/antigravity) with local installer caching and multi-profile enhancements.

This directory contains utility scripts to set up, configure, and manage multiple isolated user profiles/accounts for a single installation of Google Antigravity and Antigravity IDE on Linux.

---

## Directory Contents

| File | Description |
| :--- | :--- |
| **[install.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/install.sh)** | Enhanced Antigravity Linux installer script with local script caching, clean sudo execution, and offline fallback support. |
| **[setup-profile2.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/setup-profile2.sh)** | Portable helper script that cleans up duplicate installations and configures isolated wrapper launchers for Profile 2. |

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

* **Desktop App (Profile 2):** Launched with `--user-data-dir="$HOME/.config/antigravity-profile2"` to isolate login sessions and application state.
* **IDE App (Profile 2):** Launched with `--user-data-dir="$HOME/.config/Antigravity-IDE-profile2"`. It shares installed extensions with Profile 1 (`~/.antigravity-ide/extensions`) while keeping settings, workspaces, and auth completely separate.
* **CLI App (Profile 2):** Launched via `bwrap` to mount `~/.antigravity-cli-account2/.gemini` over `~/.gemini`, keeping `$HOME`, dotfiles, `.ssh`, `.gitconfig`, and desktop keyring / D-Bus access intact for developer tools like `gh` and `git`.

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
