# Tarball Installer

A bash script to automate installing Linux applications packaged as tarballs (`.tar.gz`, `.tar.xz`, `.tgz`, etc.) into your user workspace. It handles extraction, binary discovery, icon detection, CLI symlink creation, and desktop launcher (`.desktop` file) registration.

## Features

- **Auto-Extraction**: Safely extracts the tarball. If the archive has a single root directory, it extracts and optionally renames it. If it has multiple root files, it creates a clean folder wrapper.
- **Smart Executable Detection**: Finds the main executable binary (or launcher script) inside the extracted folders.
- **Automatic Icon Linking**: Searches for the application's brand assets (`.png` or `.svg`) to set as the launcher icon.
- **CLI Wrapper Creation**: Places a CLI launcher symlink in a folder on your `$PATH` (e.g., `~/bin` or `~/.local/bin`).
- **Desktop Entry Generation**: Creates a `.desktop` file in `~/.local/share/applications/` so the app is instantly searchable in your system's application menus.
- **Desktop Database Update**: Triggers a rebuild of the desktop database so the application shows up immediately.

## Installation / Setup

The script is located at:
- [install.sh](file:///home/tazztone/_coding/scripts/sh/tarball-installer/install.sh)

A symlink `install-tarball.sh` is created in your `~/bin` directory so you can invoke it from anywhere:
- [install-tarball.sh](file:///home/tazztone/bin/install-tarball.sh)

## Usage

```bash
install-tarball.sh [options] <path-to-tarball>
```

### Options

| Option | Description | Default |
| :--- | :--- | :--- |
| `-n, --name <name>` | Specify custom application name | Derived from filename |
| `-d, --dest <dir>` | Installation destination directory | `~/Applications` |
| `-b, --bin-dir <dir>` | Binary symlink directory for CLI | `~/bin` |
| `-h, --help` | Show help and usage details | |

### Example

To install a tarball:
```bash
install-tarball.sh ~/Downloads/Devin-linux-x64-3.4.27.tar.gz
```
This will extract Devin to `~/Applications/devin`, find the main `devin-desktop` executable, locate the icon `code.png`, create a CLI symlink `~/bin/devin`, and register it in your application menu launcher.
