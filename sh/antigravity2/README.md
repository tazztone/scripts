# Antigravity Multi-Profile Management Scripts

based on https://github.com/opensnap/antigravity
This directory contains utility scripts to set up and manage multiple isolated user profiles for a single installation of Google Antigravity and Antigravity IDE on Linux.

---

## Directory Contents

| File | Description |
| :--- | :--- |
| **[install.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/install.sh)** | The original Antigravity Linux installer script from https://github.com/opensnap/antigravity |
| **[setup-profile2.sh](file:///home/tazztone/_coding/scripts/sh/antigravity2/setup-profile2.sh)** | Helper script that cleans up duplicate installations and configures wrapper launchers for Profile 2. |
| **[second_installation_guide.md](file:///home/tazztone/_coding/scripts/sh/antigravity2/second_installation_guide.md)** | A detailed guide explaining how the data isolation works. |

---

## How it Works

Instead of installing multiple copies of the application (which duplicates binaries and consumes excess disk space), we use a single installation of the application binaries and pass command-line arguments to redirect user data to separate folders:

* **Desktop App (Profile 2):** Launched with `--user-data-dir="$HOME/.config/antigravity-profile2"`
* **IDE App (Profile 2):** Launched with `--user-data-dir="$HOME/.config/Antigravity-IDE-profile2"` (shares extensions with Profile 1)

This prevents configuration/login collisions and allows you to run both sessions simultaneously.

---

## Quick Start

### 1. Configure Profile 2
Run the setup script with superuser permissions (required to write to `/usr/local/bin` and update the applications database):
```bash
sudo ./setup-profile2.sh
```

### 2. Launch Profile 2
Once configured, you can launch the second profile:
* **From the Application Menu:** Search for **Antigravity (Profile 2)** or **Antigravity IDE (Profile 2)**.
* **From the Command Line:**
  * Run Desktop: `antigravity-profile2`
  * Run IDE: `antigravity-ide-profile2`
