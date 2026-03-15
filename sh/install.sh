#!/bin/bash
set -euo pipefail

# Define the target directory for Nautilus scripts
SCRIPTS_TARGET="$HOME/.local/share/nautilus/scripts"

# Define the source directories (absolute paths) using robust path resolution
REAL_DIR="$(dirname "$(readlink -f "$0")")"
FFMPEG_SOURCE="$REAL_DIR/ffmpeg"
IMAGE_SOURCE="$REAL_DIR/imagemagick"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to detect package manager for hint
detect_pkg_mgr() {
    if command -v apt &> /dev/null; then echo "sudo apt update && sudo apt install"
    elif command -v dnf &> /dev/null; then echo "sudo dnf install"
    elif command -v pacman &> /dev/null; then echo "sudo pacman -S"
    elif command -v zypper &> /dev/null; then echo "sudo zypper install"
    else echo "[package-manager-install-command]"
    fi
}

echo -e "${GREEN}Starting installation of Nautilus Media Scripts...${NC}"

# Check for prerequisites
echo -e "${YELLOW}Checking for prerequisites...${NC}"
MISSING_DEPS=0
# Common deps + ffmpeg/imagemagick specifics
for cmd in ffmpeg ffprobe magick zenity bc; do
    # Handle both IM v7 (magick) and v6 (convert)
    if [[ "$cmd" == "magick" ]]; then
        if ! command -v magick &> /dev/null && ! command -v convert &> /dev/null; then
            echo -e "${RED}Error: ImageMagick is not installed.${NC}"
            MISSING_DEPS=1
        fi
        continue
    fi

    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed.${NC}"
        MISSING_DEPS=1
    else
        echo -e "${GREEN}  OK: $cmd found.${NC}"
    fi
done

if [ $MISSING_DEPS -eq 1 ]; then
    PKG_CMD=$(detect_pkg_mgr)
    echo -e "${RED}Please install missing dependencies manually:${NC}"
    echo "  $PKG_CMD ffmpeg imagemagick zenity bc"
    read -p "Do you want to continue installation anyway? (y/N) " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Installation aborted."
        exit 1
    fi
    echo -e "${YELLOW}Continuing installation with missing dependencies...${NC}"
fi

# Ensure target root directory exists
mkdir -p "$SCRIPTS_TARGET"

install_scripts() {
    local SOURCE_DIR="$1"
    local NAME="$2"
    
    if [ ! -d "$SOURCE_DIR" ]; then
        echo -e "${RED}Error: Source directory for $NAME scripts not found at $SOURCE_DIR${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Symlinking $NAME scripts to $SCRIPTS_TARGET...${NC}"
        for script in "$SOURCE_DIR"/*.sh; do
            [ -e "$script" ] || continue
            # Skip library files
            if [[ "$(basename "$script")" == "common.sh" ]]; then
                continue
            fi
            
            TARGET_LINK="$SCRIPTS_TARGET/$(basename "$script")"
            if [ -d "$TARGET_LINK" ] && [ ! -L "$TARGET_LINK" ]; then
                echo -e "${RED}Warning: $TARGET_LINK is a real directory. Skipping.${NC}"
                continue
            fi

            # Overwrite confirmation
            if [ -L "$TARGET_LINK" ]; then
                # If it's already linked to the same file, skip silently
                if [[ "$(readlink -f "$TARGET_LINK")" == "$(readlink -f "$script")" ]]; then
                    continue
                fi
                
                if command -v zenity &> /dev/null; then
                     if ! zenity --question --title="Overwrite?" --text="Existing link found for '$(basename "$script")'.\nPoints to: $(readlink -f "$TARGET_LINK")\n\nOverwrite with this version?" --ok-label="Overwrite" --cancel-label="Keep Original"; then
                         echo "  Skipped: $(basename "$script") (kept existing)"
                         continue
                     fi
                else
                     read -p "Overwrite existing link for $(basename "$script")? (y/N) " confirm
                     [[ ! "$confirm" =~ ^[Yy]$ ]] || { echo "  Skipped: $(basename "$script")"; continue; }
                fi
            fi

            # Ensure source is executable
            chmod +x "$script"
            ln -sf "$script" "$TARGET_LINK"
            echo "  Created symlink: $(basename "$script")"
        done
}

# Install Scripts from both sources to the root
install_scripts "$FFMPEG_SOURCE" "FFmpeg"
install_scripts "$IMAGE_SOURCE" "ImageMagick"

echo -e "${GREEN}Installation complete!${NC}"
echo -e "You can now right-click files in Nautilus -> Scripts"
