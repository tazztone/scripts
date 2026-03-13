#!/bin/bash

# Define the target directories for Nautilus scripts
FFMPEG_TARGET="$HOME/.local/share/nautilus/scripts/ffmpeg"
IMAGE_TARGET="$HOME/.local/share/nautilus/scripts/imagemagick"

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

    if ! command -v $cmd &> /dev/null; then
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
fi

# Install FFmpeg Scripts
if [ -d "$FFMPEG_SOURCE" ]; then
    echo -e "${YELLOW}Symlinking FFmpeg scripts to $FFMPEG_TARGET...${NC}"
    mkdir -p "$FFMPEG_TARGET"
    for script in "$FFMPEG_SOURCE"/*.sh; do
        ln -sf "$script" "$FFMPEG_TARGET/$(basename "$script")"
    done
fi

# Install ImageMagick Scripts
if [ -d "$IMAGE_SOURCE" ]; then
    echo -e "${YELLOW}Symlinking ImageMagick scripts to $IMAGE_TARGET...${NC}"
    mkdir -p "$IMAGE_TARGET"
    for script in "$IMAGE_SOURCE"/*.sh; do
        ln -sf "$script" "$IMAGE_TARGET/$(basename "$script")"
    done
fi

echo -e "${GREEN}Installation complete!${NC}"
echo -e "You can now right-click files in Nautilus -> Scripts"
