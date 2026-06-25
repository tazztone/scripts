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
1. Validates that the necessary `unzip` tool is installed.
2. Safely unzips the downloaded installer into a temporary subdirectory inside the ZIP file's parent folder (avoiding common `/tmp` size constraints on systems where `/tmp` is a small `tmpfs` RAM disk).
3. Launches the installer using the `SKIP_PACKAGE_CHECK=1` environment variable to bypass legacy package checks.
4. Automatically moves the conflicting bundled GLib/GObject libraries (`libglib`, `libgio`, `libgmodule`, and `libgobject`) to `/opt/resolve/libs/disabled-libs/`, forcing Resolve to use the system's newer, compatible versions.
5. Cleans up all extraction artifacts securely.

## Usage

Ensure the script is executable:
```bash
chmod +x update.sh
```

### 1. Automatic Search (Recommended)
By default, running the script with no arguments will automatically search for the newest `DaVinci_Resolve*_Linux.zip` file inside your `~/Downloads` directory:
```bash
./update.sh
```

### 2. Manual Zip Target
Alternatively, pass the direct path to the `.zip` archive:
```bash
./update.sh ~/Downloads/DaVinci_Resolve_Studio_21.0.1_Linux.zip
```
