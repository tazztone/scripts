#!/bin/bash

# Define the target directory for Nautilus scripts
TARGET_DIR="$HOME/.local/share/nautilus/scripts/ffmpeg"

# Define the source directory (adjust if running from a different location)
SOURCE_DIR="$(dirname "$0")/ffmpeg"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting installation of Nautilus FFmpeg Scripts...${NC}"

# Check for prerequisites
echo -e "${YELLOW}Checking for prerequisites...${NC}"
MISSING_DEPS=0
for cmd in ffmpeg ffprobe zenity bc; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed.${NC}"
        MISSING_DEPS=1
    else
        echo -e "${GREEN}  OK: $cmd found.${NC}"
    fi
done

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${RED}Please install missing dependencies manually:${NC}"
    echo "  sudo apt update && sudo apt install ffmpeg zenity bc"
    read -p "Do you want to continue installation anyway? (y/N) " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Installation aborted."
        exit 1
    fi
fi

# Ensure source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}Error: Source directory '$SOURCE_DIR' not found.${NC}"
    echo "Please run this script from the root of the repository."
    exit 1
fi

# Create target directory
echo -e "${YELLOW}Creating target directory: $TARGET_DIR${NC}"
mkdir -p "$TARGET_DIR"

# Copy scripts
echo -e "${YELLOW}Copying scripts...${NC}"
cp -r "$SOURCE_DIR"/* "$TARGET_DIR/"

# Set executable permissions
echo -e "${YELLOW}Setting executable permissions...${NC}"
chmod +x "$TARGET_DIR"/*.sh

echo -e "${GREEN}Installation complete!${NC}"
echo -e "You can now right-click video files in Nautilus -> Scripts -> ffmpeg"
