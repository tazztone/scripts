#!/bin/bash

# Target directories for Nautilus scripts
FFMPEG_TARGET="$HOME/.local/share/nautilus/scripts/ffmpeg"
IMAGE_TARGET="$HOME/.local/share/nautilus/scripts/imagemagick"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting uninstallation of Nautilus Media Scripts...${NC}"

# Absolute path of the project root
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

remove_links() {
    local TARGET_DIR="$1"
    local NAME="$2"

    if [ -d "$TARGET_DIR" ]; then
        echo -e "${YELLOW}Cleaning $NAME scripts from $TARGET_DIR...${NC}"
        local found=0
        for link in "$TARGET_DIR"/*.sh; do
            [ -e "$link" ] || continue
            # Check if it's a symlink and where it points
            if [ -L "$link" ]; then
                local target
                target=$(readlink -f "$link")
                if [[ "$target" == "$PROJECT_ROOT"* ]]; then
                    echo "  Removing symlink: $(basename "$link")"
                    rm "$link"
                    ((found++))
                fi
            fi
        done
        
        if [ $found -eq 0 ]; then
            echo "  No project symlinks found in $TARGET_DIR."
        else
            echo -e "${GREEN}  Removed $found symlinks.${NC}"
        fi

        # Remove directory if empty
        if [ -z "$(ls -A "$TARGET_DIR" 2>/dev/null)" ]; then
            echo "  Removing empty directory: $TARGET_DIR"
            rmdir "$TARGET_DIR"
        fi
    else
        echo "  $NAME target directory does not exist. Skipping."
    fi
}

remove_links "$FFMPEG_TARGET" "FFmpeg"
remove_links "$IMAGE_TARGET" "ImageMagick"

echo -e "${GREEN}Uninstallation complete!${NC}"
