#!/bin/bash

# Define the target directory for Nautilus scripts
SCRIPTS_TARGET="$HOME/.local/share/nautilus/scripts"

# Define the source directories (absolute paths)
FFMPEG_SOURCE="$(cd "$(dirname "$0")/ffmpeg" && pwd)"
IMAGE_SOURCE="$(cd "$(dirname "$0")/imagemagick" && pwd)"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
    echo -e "${RED}Please install missing dependencies manually:${NC}"
    echo "  sudo apt update && sudo apt install ffmpeg imagemagick zenity bc"
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
    
    if [ -d "$SOURCE_DIR" ]; then
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
    fi
}

# Install Scripts from both sources to the root
install_scripts "$FFMPEG_SOURCE" "FFmpeg"
install_scripts "$IMAGE_SOURCE" "ImageMagick"

echo -e "${GREEN}Installation complete!${NC}"
echo -e "You can now right-click files in Nautilus -> Scripts"
