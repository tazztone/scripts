# Stampf Media Staging for DaVinci Resolve

Recursively discovers and symlinks Stampf event media from archive years into dedicated flat folders for DaVinci Resolve import.

## Staging Folders Created
- `/mnt/wd14tb/_RESOLVE_IMPORT_STAGING/photos_raw`: Flat symlinks to all `.dng`, `.arw`, `.rw2`, `.cr2`, `.nef`, `.tif` files.
- `/mnt/wd14tb/_RESOLVE_IMPORT_STAGING/videos`: Flat symlinks to all `.mp4`, `.mov`, `.mxf`, `.insv` video files.

## Usage

### Run using Bash Wrapper
```bash
./stage_stampf_media.sh
```
*(By default runs `--clean --open`)*

### Run using Python with Options
```bash
# Stage both RAW photos and videos, then open in file manager:
python3 stage_stampf_media.py --open

# Clean existing links before staging:
python3 stage_stampf_media.py --clean

# Include JPG/JPEG/HEIC along with RAW/DNG:
python3 stage_stampf_media.py --include-jpg

# Stage only photos or only videos:
python3 stage_stampf_media.py --mode photos
python3 stage_stampf_media.py --mode videos
```
