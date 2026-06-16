# Antigravity Multi-Profile Management

Based on [github.com/opensnap/antigravity](https://github.com/opensnap/antigravity).

This directory contains utility scripts to set up, configure, and manage multiple isolated user profiles/accounts for a single installation of Google Antigravity and Antigravity IDE on Linux.

---

## Why Use Multiple Profiles?

Instead of installing two completely separate copies of the application (which duplicates binaries, consumes excess disk space, and complicates updating), the recommended way to run two isolated user profiles/accounts side-by-side is to use command-line flags on the *original* installation.

We use a helper script that automatically configures isolated wrapper scripts and desktop launchers for a second profile (**Profile 2**).

---

## Directory Contents

| File | Description |
| :--- | :--- |
| **[install.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/install.sh)** | The original Antigravity Linux installer script from https://github.com/opensnap/antigravity. |
| **[setup-profile2.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/setup-profile2.sh)** | Helper script that cleans up duplicate installations and configures wrapper launchers for Profile 2. |

---

## How it Works

Both profiles use the same application binaries from the original installation. When you launch the second profile, they are invoked with command-line flags that redirect user data:

* **Desktop App (Profile 2):** Launched with `--user-data-dir="$HOME/.config/antigravity-profile2"` to isolate all login sessions and application state.
* **IDE App (Profile 2):** Launched with `--user-data-dir="$HOME/.config/Antigravity-IDE-profile2"`. By omitting the extensions directory flag, it shares all installed extensions with Profile 1 (stored in `~/.antigravity-ide/extensions`) while keeping settings, workspace states, and login sessions completely separate.
* **CLI App (Profile 2):** Launched with `env HOME="/home/tazztone/.antigravity-cli-account2"`, with `DBUS_SESSION_BUS_ADDRESS` set to `unix:path=/dev/null` (disabling GNOME Keyring access by blocking D-Bus fallbacks, forcing token storage inside the isolated home folder) and `GOOGLE_API_KEY` cleared (forcing the OAuth flow).

This prevents configuration/login collisions and allows you to run both sessions simultaneously.

---

## How to Set It Up

To clean up duplicate installations and configure the launchers for Profile 2:

1. Open your terminal.
2. Run the setup helper script with superuser permissions (required to write to `/usr/local/bin` and update the applications database):
   ```bash
   sudo /home/tazztone/_coding/scripts/sh/antigravity2/setup-profile2.sh
   ```

---

## Launching the Second Profile

Once the setup script completes, you can launch the second profile:

* **From your Application Menu:**
  * Search for and click on **Antigravity (Profile 2)** or **Antigravity IDE (Profile 2)**.
* **From the Command Line:**
  * Run Desktop: `antigravity-profile2`
  * Run IDE: `antigravity-ide-profile2`
  * Run CLI: `agy2`
