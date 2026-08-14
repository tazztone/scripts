# DaVinci Resolve Updater and Patcher for Ubuntu

This directory contains a utility script designed to automate updating DaVinci Resolve Studio (or Free edition) on modern Ubuntu versions (such as Ubuntu 24.04 and 26.04 LTS).

## The Problem
Every time DaVinci Resolve is installed or updated, it bundles older versions of GLib and GObject libraries (version 2.68.x) in `/opt/resolve/libs/`. 
On newer Ubuntu releases, the system libraries (like `libpango`) expect newer GLib libraries, causing the application to crash silently on launch with a symbol lookup error:
```
/opt/resolve/bin/resolve: symbol lookup error: /usr/lib/x86_64-linux-gnu/libpango-1.0.so.0: undefined symbol: g_once_init_leave_pointer
```

Additionally, the installer's dependency check fails on newer Ubuntu versions because of the `t64` package transition (e.g. `libasound2t64` instead of `libasound2`).

## The Solution
The [update.sh](update.sh) script automates the entire installation and patching process:
1. Requests `sudo` credentials upfront and maintains a background session keepalive throughout extraction so you can let it run unattended.
2. Accepts both `.zip` archives and `.run` installer files directly, or automatically discovers the newest installer in `~/Downloads`.
3. Safely extracts to a named cache folder and skips re-extraction if the installer was already unpacked from a previous run.
4. Launches the installer using the `SKIP_PACKAGE_CHECK=1` environment variable to bypass legacy package checks.
5. Automatically moves the conflicting bundled GLib/GObject libraries (`libglib`, `libgio`, `libgmodule`, and `libgobject`) to `/opt/resolve/libs/disabled-libs/`, forcing Resolve to use the system's newer, compatible versions.
6. Automatically cleans up temporary extracted files only upon successful installation.

## Usage

Ensure the script is executable:
```bash
chmod +x update.sh
```

### 1. Automatic Search (Recommended)
By default, running the script with no arguments will automatically search for the newest `DaVinci_Resolve*_Linux.zip` or `.run` file inside your `~/Downloads` directory:
```bash
./update.sh
```

### 2. Manual Archive or Installer Target
Alternatively, pass the direct path to either the `.zip` archive or the extracted `.run` installer:
```bash
./update.sh ~/Downloads/DaVinci_Resolve_Studio_21.0.4_Linux.zip
# or
./update.sh ~/Downloads/DaVinci_Resolve_Studio_21.0.4_Linux.run
```
