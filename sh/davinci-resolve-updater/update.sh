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

# Request sudo privileges upfront
info "Requesting sudo privileges upfront..."
sudo -v || error "Failed to obtain sudo privileges."

# Keep sudo timestamp alive in background until the script exits
(while true; do sudo -n true; sleep 50; kill -0 "$$" 2>/dev/null || exit; done 2>/dev/null) &
SUDO_KEEP_ALIVE_PID=$!

# Ensure cleanup on script exit
cleanup() {
    local exit_code=$?

    # Stop sudo keepalive process
    if [ -n "${SUDO_KEEP_ALIVE_PID:-}" ]; then
        kill "$SUDO_KEEP_ALIVE_PID" 2>/dev/null || true
    fi

    # Clean up extraction directory only upon successful installation
    if [ "$exit_code" -eq 0 ]; then
        if [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ]; then
            info "Cleaning up temporary extraction files..."
            rm -rf "$TEMP_DIR"
        fi
    else
        if [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ]; then
            info "Installation did not complete successfully. Extracted files preserved in: $TEMP_DIR"
        fi
    fi
}
trap cleanup EXIT

# Find the installer / ZIP file
INPUT_PATH="$1"
if [ -z "$INPUT_PATH" ]; then
    info "No installer or ZIP file specified. Searching in $DOWNLOAD_DIR..."
    # Find the most recently modified DaVinci Resolve .zip or .run file
    LATEST_FILE=$(find "$DOWNLOAD_DIR" -maxdepth 1 \( -name "DaVinci_Resolve*_Linux.zip" -o -name "DaVinci_Resolve*_Linux.run" \) -type f -printf "%T@ %p\n" 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -z "$LATEST_FILE" ]; then
        error "No DaVinci Resolve ZIP or .run file found in $DOWNLOAD_DIR. Please specify path: $0 /path/to/archive.zip"
    fi
    INPUT_PATH="$LATEST_FILE"
fi

if [ ! -f "$INPUT_PATH" ]; then
    error "File not found: $INPUT_PATH"
fi

RUN_FILE=""
TEMP_DIR=""

if [[ "$INPUT_PATH" == *.run ]]; then
    RUN_FILE="$INPUT_PATH"
    info "Using installer directly: $RUN_FILE"
elif [[ "$INPUT_PATH" == *.zip ]]; then
    ZIP_PATH="$INPUT_PATH"
    info "Using zip archive: $ZIP_PATH"

    # Check if unzip is installed
    if ! command -v unzip &> /dev/null; then
        error "'unzip' utility is required but not installed. Please run: sudo apt install unzip"
    fi

    # Use deterministic extraction folder based on ZIP filename to avoid re-extracting on rerun
    ZIP_BASENAME="$(basename "$ZIP_PATH" .zip)"
    TEMP_DIR="$(dirname "$ZIP_PATH")/resolve-extracted-${ZIP_BASENAME}"
    mkdir -p "$TEMP_DIR"

    MARKER_FILE="$TEMP_DIR/.extraction_complete"
    EXISTING_RUN=$(find "$TEMP_DIR" -name "*Resolve*_Linux.run" -type f 2>/dev/null | head -n 1)

    if [ -f "$MARKER_FILE" ] && [ -n "$EXISTING_RUN" ] && [ -f "$EXISTING_RUN" ]; then
        info "Found already extracted installer: $(basename "$EXISTING_RUN") in $TEMP_DIR"
        info "Skipping extraction step."
        RUN_FILE="$EXISTING_RUN"
    else
        info "Extracting installer archive to $TEMP_DIR..."
        rm -f "$MARKER_FILE"
        unzip -q -o "$ZIP_PATH" -d "$TEMP_DIR"
        touch "$MARKER_FILE"

        RUN_FILE=$(find "$TEMP_DIR" -name "*Resolve*_Linux.run" -type f 2>/dev/null | head -n 1)
        if [ -z "$RUN_FILE" ]; then
            error "Could not find any .run installer inside the zip archive."
        fi
    fi
else
    error "Unsupported file format: $INPUT_PATH (expected .zip or .run)"
fi

info "Found installer: $(basename "$RUN_FILE")"
chmod +x "$RUN_FILE"

# Run the installer
info "Starting DaVinci Resolve installation..."
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
