# Guide: Running Multiple Isolated Profiles of a Single Antigravity Installation

Instead of installing two completely separate copies of the application (which duplicates binaries, consumes excess disk space, and complicates updating), the recommended way to run two isolated user profiles/accounts side-by-side is to use command-line flags on the *original* installation.

We have created a ready-to-run setup script at [setup-profile2.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/setup-profile2.sh) that configures these isolated launchers automatically.

---

## How it Works

Both profiles use the same application binary from the original installation. 

When you launch the second profile:
1. **The Desktop App** is launched with `--user-data-dir="$HOME/.config/antigravity-profile2"`, isolating all logins and state.
2. **The IDE App** is launched with `--user-data-dir="$HOME/.config/Antigravity-IDE-profile2"`. By omitting the extensions directory flag, it shares all installed extensions with Profile 1 (stored in `~/.antigravity-ide/extensions`) while keeping settings, workspace states, and login sessions separate.

This allows you to run both profiles simultaneously without them conflicting or sharing sessions.

---

## How to Set It Up

To configure the second profile launchers:

1. Execute the helper script from the scripts folder:
   ```bash
   sudo /home/tazztone/_coding/scripts/sh/antigravity2/setup-profile2.sh
   ```

---

## Launching the Second Profile

Once the setup script completes, you can launch the second profile:

* **From the Command Line:**
  * Run Desktop Profile 2: `antigravity-profile2`
  * Run IDE Profile 2: `antigravity-ide-profile2`

* **From your Application Menu:**
  * Click on the new icons labeled **Antigravity (Profile 2)** or **Antigravity IDE (Profile 2)**.
