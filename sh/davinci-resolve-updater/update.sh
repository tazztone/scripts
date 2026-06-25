#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define directories
DOWNLOAD_DIR="$HOME/Downloads"
RESOLVE_LIBS="/opt/resolve/libs"
DISABLED_LIBS_DIR="$RESOLVE_LIBS/disabled-libs"

# Target GLib/GObject libraries to disable
LIBS_TO_DISABLE=(
    "libglib-2.0.so*"
    "libgio-2.0.so*"
    "libgmodule-2.0.so*"
    "libgobject-2.0.so*"
)

# Helper function for colored output
info() { echo -e "\e[34m[INFO]\e[0m $1"; }
success() { echo -e "\e[32m[SUCCESS]\e[0m $1"; }
error() { echo -e "\e[31m[ERROR]\e[0m $1" >&2; exit 1; }

# Find the ZIP file
ZIP_PATH="$1"
if [ -z "$ZIP_PATH" ]; then
    info "No ZIP file specified. Searching in $DOWNLOAD_DIR..."
    # Find the most recently modified DaVinci_Resolve*_Linux.zip file
    LATEST_ZIP=$(find "$DOWNLOAD_DIR" -maxdepth 1 -name "DaVinci_Resolve*_Linux.zip" -type f -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -z "$LATEST_ZIP" ]; then
        error "No DaVinci Resolve ZIP file found in $DOWNLOAD_DIR. Please specify path: $0 /path/to/archive.zip"
    fi
    ZIP_PATH="$LATEST_ZIP"
fi

if [ ! -f "$ZIP_PATH" ]; then
    error "File not found: $ZIP_PATH"
fi

info "Using zip archive: $ZIP_PATH"

# Check if unzip is installed
if ! command -v unzip &> /dev/null; then
    error "'unzip' utility is required but not installed. Please run: sudo apt install unzip"
fi

# Create a temporary directory for extraction
TEMP_DIR=""
TEMP_DIR=$(mktemp -d -p "$(dirname "$ZIP_PATH")" resolve-update-XXXXXXXXXX)
info "Created temporary extraction folder: $TEMP_DIR"

# Ensure cleanup on script exit
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        info "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# Extract the ZIP archive
info "Extracting installer archive..."
unzip -q "$ZIP_PATH" -d "$TEMP_DIR"

# Locate the installer (.run) file
RUN_FILE=$(find "$TEMP_DIR" -name "*Resolve*_Linux.run" -type f | head -n 1)
if [ -z "$RUN_FILE" ]; then
    error "Could not find any .run installer inside the zip."
fi

info "Found installer: $(basename "$RUN_FILE")"
chmod +x "$RUN_FILE"

# Run the installer
info "Starting DaVinci Resolve installation (requires sudo)..."
sudo SKIP_PACKAGE_CHECK=1 "$RUN_FILE" --install --noconfirm

success "DaVinci Resolve installation completed successfully."

# Move conflicting libraries
info "Relocating conflicting libraries in $RESOLVE_LIBS..."
sudo mkdir -p "$DISABLED_LIBS_DIR"

for lib_pattern in "${LIBS_TO_DISABLE[@]}"; do
    # Using sh -c allows sudo to execute glob expansion correctly
    sudo sh -c "mv $RESOLVE_LIBS/$lib_pattern $DISABLED_LIBS_DIR/ 2>/dev/null || true"
done

success "Moved conflicting libraries to $DISABLED_LIBS_DIR"
success "DaVinci Resolve has been successfully updated and patched!"
