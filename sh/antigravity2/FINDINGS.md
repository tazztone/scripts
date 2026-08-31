# Technical Findings & Architecture Discoveries: Antigravity Multi-Profile Isolation

This document records the internal architecture, reverse-engineering discoveries, root-cause analysis, and verified isolation strategy for running multiple Google Antigravity profiles side-by-side on Linux.

---

## 1. Executive Summary

Google Antigravity 2.0 uses a hybrid architecture composed of an **Electron GUI shell** and a native **Go backend daemon** (`language_server`). While the CLI (`agy`) and IDE (`antigravity-ide`) were successfully isolated in prior work, the Desktop app (`antigravity`) continued reverting to Account 1 (`tazztone2@gmail.com`).

Reverse-engineering the binaries revealed that the Go backend daemon queries the **host Linux Secret Service (GNOME Keyring)** over D-Bus by default. Because the previous Desktop wrapper did not isolate D-Bus and lacked a token file in the Desktop-specific app subdirectory, the daemon fell back to reading Account 1 credentials from the host keyring.

By neutralizing D-Bus keyring queries (`DBUS_SESSION_BUS_ADDRESS="unix:path=/dev/null"`), setting basic Chromium password storage (`--password-store=basic`), and symlinking the CLI OAuth token into the Desktop app directory, Antigravity Desktop achieves 100% clean isolation under Account 2 (`nataliegemini91@gmail.com`).

---

## 2. Reverse-Engineering Discoveries

### A. Desktop Application Architecture
* **Binary Location:** `/opt/antigravity/Antigravity-x64/antigravity`
* **Resource Bundle:** `/opt/antigravity/Antigravity-x64/resources/app.asar`
* **Backend Daemon:** `/opt/antigravity/Antigravity-x64/resources/bin/language_server`

When launched, the Electron main process (`main.js`):
1. Starts an internal Host Bridge server.
2. Spawns `language_server` with the following arguments:
   ```bash
   language_server \
     --standalone \
     --override_ide_name antigravity \
     --subclient_type hub \
     --override_ide_version <version> \
     --override_user_agent_name antigravity \
     --https_server_port 0 \
     --csrf_token <token> \
     --app_data_dir antigravity \
     --api_server_url https://generativelanguage.googleapis.com \
     --cloud_code_endpoint https://daily-cloudcode-pa.googleapis.com \
     --enable_sidecars
   ```
3. The `language_server` starts an internal HTTP/HTTPS web server on a random local port (e.g., `https://127.0.0.1:33011/`).
4. Electron opens a BrowserWindow that loads this local URL (the AGY Hub UI).

### B. Auth & Token Storage Internals (`codeassistclient`)
Inspection of the Go symbol table and string tables in `language_server` identified the exact authentication subsystem:

* **Auth Provider:** `*codeassistclient.StandaloneAuthProvider`
* **Token Storage Pipeline:** `*codeassistclient.compositeTokenStorage`
  * **Tier 1 — `KeyringTokenStorage`:** Invokes `github.com/zalando/go-keyring` via `secret_service` (`org.freedesktop.secrets`). It connects to the D-Bus session bus defined by `DBUS_SESSION_BUS_ADDRESS`.
  * **Keyring Detector (`keyring_detector_dbus.go`):** Probes D-Bus responsiveness. If D-Bus is unreachable, errors out, or times out, it triggers `keyringRecentlyUnavailable` and falls back to Tier 2.
  * **Tier 2 — `FileTokenStorage`:** Reads/writes the OAuth token on disk as JSON.

### C. App Data Directory Partitioning
The location of disk tokens and state files depends strictly on the `--app_data_dir` flag passed to `language_server`:

| Component | Flag Passed | Storage Path Relative to `~/.gemini/` |
| :--- | :--- | :--- |
| **CLI (`agy`)** | `--app_data_dir antigravity-cli` | `~/.gemini/antigravity-cli/antigravity-oauth-token` |
| **Desktop (`antigravity`)** | `--app_data_dir antigravity` | `~/.gemini/antigravity/antigravity-oauth-token` |
| **IDE (`antigravity-ide`)** | `--app_data_dir antigravity-ide` | `~/.gemini/antigravity-ide/` (Auth in VSCode db) |

---

## 3. Root-Cause Analysis of Previous Desktop Failure

When `antigravity-profile2` was launched previously:

1. **Host Keyring Leak:**
   * In `setup-profile2.sh`, `bwrap` bound `~/.antigravity-cli-account2/.gemini` over `~/.gemini`, but left `DBUS_SESSION_BUS_ADDRESS` untouched.
   * `language_server` connected to the host D-Bus daemon at `/run/user/1000/bus`.
   * `KeyringTokenStorage` queried GNOME Keyring and retrieved the stored OAuth credentials for **`tazztone2@gmail.com`**.
2. **Missing Token in App Directory:**
   * When `agy2 auth login` authenticated `nataliegemini91@gmail.com`, it saved the token to `~/.gemini/antigravity-cli/antigravity-oauth-token`.
   * Because Desktop uses `--app_data_dir antigravity`, it looked for `~/.gemini/antigravity/antigravity-oauth-token`, which did not exist.
   * Finding no local file token and receiving Account 1's token from GNOME Keyring, Desktop displayed Account 1.

---

## 4. The Streamlined Isolation Solution

To achieve full isolation without over-engineering:

### 1. D-Bus Neutralization
Set `--setenv DBUS_SESSION_BUS_ADDRESS "unix:path=/dev/null"` inside Bubblewrap.
* `keyring_detector_dbus` immediately detects that D-Bus is unavailable.
* `CompositeTokenStorage` bypasses the host GNOME Keyring and forces `FileTokenStorage` mode.

### 2. Chromium Password Storage Flag
Pass `--password-store=basic` to the Electron binary.
* Instructs Chromium to use local file encryption for session cookies/storage instead of querying GNOME Keyring or KWallet.
* Eliminates D-Bus startup timeouts and NSS crypto warnings.

### 3. Bidirectional Token Sync (Relative Symlink)
Create a relative symlink between the CLI and Desktop token directories:
```bash
ln -sf "../antigravity-cli/antigravity-oauth-token" "$ACCOUNT2_GEMINI/antigravity/antigravity-oauth-token"
```
* When `agy2` refreshes or updates the OAuth token, Desktop immediately uses the new token.
* When Desktop re-authenticates or updates the token, `agy2` automatically stays in sync.
* Zero copy loops or stale credential states.

### 4. Window Class & Dock Separation
Pass `--class="antigravity-profile2"` to Electron and set `StartupWMClass=antigravity-profile2` in `/usr/share/applications/antigravity-profile2.desktop`.
* GNOME Shell / Wayland treats Profile 2 as an independent application in the dash/dock rather than grouping its windows under Profile 1.

### 5. Dev Tool Credentials Passthrough
Pass `GH_CONFIG_DIR="$HOME/.config/gh"` and `GIT_CONFIG_GLOBAL="$HOME/.gitconfig"`.
* Embedded terminals and background coding agents in Desktop Profile 2 can authenticate against host Git and GitHub accounts without re-login.

---

## 5. Profile & Tool Matrix

| Component | Command | Profile 1 (`tazztone2@gmail.com`) | Profile 2 (`nataliegemini91@gmail.com`) |
| :--- | :--- | :--- | :--- |
| **CLI** | `agy` / `agy2` | Native `~/.gemini/antigravity-cli/` + Keyring | Bwrap `~/.antigravity-cli-account2/.gemini/` + D-Bus null |
| **IDE** | `antigravity-ide` / `...-profile2` | Native `~/.config/Antigravity-IDE` | Native `--user-data-dir=~/.config/Antigravity-IDE-profile2` |
| **Desktop** | `antigravity` / `...-profile2` | Native `~/.config/Antigravity` + Keyring | Bwrap `~/.antigravity-cli-account2/.gemini/` + D-Bus null + basic store |
