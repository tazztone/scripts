#!/bin/bash

# Target directory for Nautilus scripts
SCRIPTS_ROOT="$HOME/.local/share/nautilus/scripts"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting uninstallation of Nautilus Media Scripts...${NC}"

# Absolute path of the project root
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

remove_project_links() {
    local TARGET_DIR="$1"
    
    if [ -d "$TARGET_DIR" ]; then
        echo -e "${YELLOW}Cleaning project scripts from $TARGET_DIR...${NC}"
        local found=0
        for link in "$TARGET_DIR"/*; do
            [ -e "$link" ] || [ -L "$link" ] || continue
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
            echo -e "${GREEN}  Removed $found symlinks from $TARGET_DIR.${NC}"
        fi

        # Remove directory if empty and it's not the root SCRIPTS_ROOT
        if [[ "$TARGET_DIR" != "$SCRIPTS_ROOT" ]] && [ -d "$TARGET_DIR" ] && [ -z "$(ls -A "$TARGET_DIR" 2>/dev/null)" ]; then
            echo "  Removing empty legacy directory: $TARGET_DIR"
            rmdir "$TARGET_DIR"
        fi
    fi
}

# 1. Clean from root directory
remove_project_links "$SCRIPTS_ROOT"

# 2. Clean from legacy subdirectories (if they exist)
[ -d "$SCRIPTS_ROOT/ffmpeg" ] && remove_project_links "$SCRIPTS_ROOT/ffmpeg"
[ -d "$SCRIPTS_ROOT/imagemagick" ] && remove_project_links "$SCRIPTS_ROOT/imagemagick"

echo -e "${GREEN}Uninstallation complete!${NC}"
