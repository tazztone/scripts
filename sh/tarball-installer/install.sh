#!/usr/bin/env bash

# Exit on error
set -e

# Save original IFS
OLD_IFS="$IFS"

show_help() {
    echo "Usage: install-tarball.sh [options] <path-to-tarball>"
    echo ""
    echo "Options:"
    echo "  -n, --name <name>      Specify custom application name (default: derived from filename)"
    echo "  -d, --dest <dir>       Specify installation destination directory (default: ~/Applications)"
    echo "  -b, --bin-dir <dir>    Specify binary symlink directory (default: ~/bin)"
    echo "  -h, --help             Show this help message"
    echo ""
}

# Default values
DEST_DIR="$HOME/Applications"
BIN_DIR="$HOME/bin"
APP_NAME=""

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--name)
            APP_NAME="$2"
            shift 2
            ;;
        -d|--dest)
            DEST_DIR="$2"
            shift 2
            ;;
        -b|--bin-dir)
            BIN_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            show_help
            exit 1
            ;;
        *)
            TARBALL="$1"
            shift
            ;;
    esac
done

if [ -z "$TARBALL" ]; then
    echo "Error: Missing path to tarball." >&2
    show_help
    exit 1
fi

if [ ! -f "$TARBALL" ]; then
    echo "Error: Tarball file not found: $TARBALL" >&2
    exit 1
fi

# Determine default app name if not provided
if [ -z "$APP_NAME" ]; then
    BASENAME=$(basename "$TARBALL")
    # Strip common suffixes
    APP_NAME="${BASENAME%.tar.*}"
    APP_NAME="${APP_NAME%.tgz}"
    # Strip architectures/version-like patterns (e.g. -linux-x64-3.4.27)
    APP_NAME=$(echo "$APP_NAME" | sed -E 's/[-_]linux.*$//I' | sed -E 's/[-_]x64.*$//I' | sed -E 's/[-_][0-9]+(\.[0-9]+)*.*$//')
fi

# Normalize app name for folders/commands
APP_ID=$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]//g')
# Friendly display name
APP_DISPLAY_NAME=$(echo "$APP_NAME" | sed -E 's/[-_]+/ /g' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')

echo "Installing $APP_DISPLAY_NAME ($APP_ID)..."

# Ensure destination and bin directories exist
mkdir -p "$DEST_DIR"
mkdir -p "$BIN_DIR"

# Get top-level directories/files in tarball to see if we need a wrapper directory
TOP_LEVELS=$(tar -tf "$TARBALL" | awk -F/ '{print $1}' | sort -u)
TOP_LEVEL_COUNT=$(echo "$TOP_LEVELS" | wc -l)
TOP_LEVEL_FIRST=$(echo "$TOP_LEVELS" | head -n 1)

INSTALL_PATH="$DEST_DIR/$APP_ID"

if [ "$TOP_LEVEL_COUNT" -eq 1 ] && [ -n "$TOP_LEVEL_FIRST" ]; then
    # Tarball has a single root directory. We extract directly to DEST_DIR and rename if necessary.
    echo "Tarball has a single root directory: $TOP_LEVEL_FIRST"
    TEMP_EXTRACT=$(mktemp -d -p "$DEST_DIR" .tmp-extract-XXXXXX)
    tar -xf "$TARBALL" -C "$TEMP_EXTRACT"
    
    # Remove existing install path if it exists
    if [ -d "$INSTALL_PATH" ]; then
        echo "Removing existing installation at $INSTALL_PATH..."
        rm -rf "$INSTALL_PATH"
    fi
    
    mv "$TEMP_EXTRACT/$TOP_LEVEL_FIRST" "$INSTALL_PATH"
    rm -rf "$TEMP_EXTRACT"
else
    # Tarball has multiple root items. We extract into a dedicated subdirectory.
    echo "Tarball has multiple root items. Creating wrapper directory at $INSTALL_PATH..."
    if [ -d "$INSTALL_PATH" ]; then
        echo "Removing existing installation at $INSTALL_PATH..."
        rm -rf "$INSTALL_PATH"
    fi
    mkdir -p "$INSTALL_PATH"
    tar -xf "$TARBALL" -C "$INSTALL_PATH"
fi

echo "Extracted to $INSTALL_PATH"

# Find executable
echo "Locating executable..."
# Prioritize files that are executable, not directories, not .sh wrappers if direct binaries exist
IFS=$'\n'
EXECUTABLES=$(find "$INSTALL_PATH" -maxdepth 3 -type f -executable ! -name "*.sh" ! -name "*.so*" ! -name "*.node")
# If no binaries found, try scripts
if [ -z "$EXECUTABLES" ]; then
    EXECUTABLES=$(find "$INSTALL_PATH" -maxdepth 3 -type f -executable -name "*.sh")
fi

BEST_EXEC=""
for exec in $EXECUTABLES; do
    exec_base=$(basename "$exec")
    exec_base_lower=$(echo "$exec_base" | tr '[:upper:]' '[:lower:]')
    if [ "$exec_base_lower" = "$APP_ID" ] || [ "$exec_base_lower" = "${APP_ID}-desktop" ] || [ "$exec_base_lower" = "bin" ]; then
        BEST_EXEC="$exec"
        break
    fi
done

if [ -z "$BEST_EXEC" ]; then
    # Fallback to first executable found
    BEST_EXEC=$(echo "$EXECUTABLES" | head -n 1)
fi

if [ -z "$BEST_EXEC" ]; then
    echo "Warning: Could not automatically detect an executable binary. You may need to create links/launchers manually."
else
    echo "Found executable: $BEST_EXEC"
    
    # Symlink to bin
    BIN_LINK="$BIN_DIR/$APP_ID"
    ln -sf "$BEST_EXEC" "$BIN_LINK"
    echo "Created CLI symlink: $BIN_LINK"
fi

# Find icon
echo "Locating icon..."
# Prioritize icons in standard places, or search for png/svg
ICONS=$(find "$INSTALL_PATH" -type f \( -name "*.png" -o -name "*.svg" \) | grep -v 'node_modules' || true)

BEST_ICON=""
# Prioritize paths containing 'resources', 'icon', 'logo', 'linux'
for icon in $ICONS; do
    if echo "$icon" | grep -qiE '(logo|icon|linux|app)'; then
        BEST_ICON="$icon"
        break
    fi
done

if [ -z "$BEST_ICON" ]; then
    # Fallback to first icon found
    BEST_ICON=$(echo "$ICONS" | head -n 1)
fi

if [ -n "$BEST_ICON" ]; then
    echo "Found icon: $BEST_ICON"
else
    echo "No icon found. Using default application icon."
fi

# Restore IFS
IFS="$OLD_IFS"

# Generate desktop file
DESKTOP_FILE="$HOME/.local/share/applications/$APP_ID.desktop"
echo "Creating desktop launcher at $DESKTOP_FILE..."

mkdir -p "$(dirname "$DESKTOP_FILE")"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_DISPLAY_NAME
Comment=Launch $APP_DISPLAY_NAME
EOF

if [ -n "$BEST_EXEC" ]; then
    echo "Exec=$BEST_EXEC %F" >> "$DESKTOP_FILE"
fi

if [ -n "$BEST_ICON" ]; then
    echo "Icon=$BEST_ICON" >> "$DESKTOP_FILE"
fi

cat <<EOF >> "$DESKTOP_FILE"
Terminal=false
StartupNotify=true
Categories=Utility;Development;
EOF

# Update desktop database
if command -v update-desktop-database >/dev/null; then
    update-desktop-database "$HOME/.local/share/applications"
fi

echo "Installation of $APP_DISPLAY_NAME complete!"
