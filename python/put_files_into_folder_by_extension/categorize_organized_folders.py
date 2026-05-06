#!/usr/bin/env python3
"""Group extension-named folders into higher-level categories.

Usage
-----
  # Organize the current working directory
  python categorize_organized_folders.py

  # Organize a specific directory
  python categorize_organized_folders.py /path/to/folder

  # Preview changes without moving anything
  python categorize_organized_folders.py --dry-run /path/to/folder
"""

import argparse
import logging
import shutil
import os
from pathlib import Path

# Mapping of Category Name -> List of folder names (extensions) to group
CATEGORIES = {
    "Images": [
        "png", "jpg", "jpeg", "webp", "gif", "avif", "heic", 
        "svg", "psd", "cr2", "png (1)", "gif", "ico"
    ],
    "Documents": [
        "pdf", "doc", "docx", "txt", "rtf", "ppt", "pptx", 
        "xls", "xlsx", "md", "csv", "xps", "epub", "azw3", 
        "opml", "resolved", "_PDF", "_EBOOKS"
    ],
    "Video": [
        "mp4", "mkv", "avi", "flv", "wmv", "mpg", "m4v", 
        "ogv", "swf", "drp", "prproj", "pdrproj", "mov"
    ],
    "Audio": [
        "mp3", "wav", "flac", "ogg", "m4a", "m4b", "aac", 
        "pls", "m3u", "xm", "_AUDIOBOOKS"
    ],
    "Software_and_Archives": [
        "zip", "rar", "7z", "gz", "bz2", "deb", "msi", 
        "exe", "iso", "ova", "jar", "apk", "vsix", "nzb", 
        "dlc", "btsearch", "_SOFTWARE"
    ],
    "Code_and_Scripts": [
        "py", "html", "htm", "js", "css", "sh", "bat", 
        "ps1", "lua", "xml", "xht", "ejs", "c", "cpp", "h"
    ],
    "AI_and_Models": [
        "safetensors", "gguf", "pt", "_AI"
    ],
    "Data_and_Config": [
        "json", "yaml", "yml", "ini", "log", "db", "sqlite3", 
        "dat", "tpx", "synapse4", "ica", "jnlp", "crdownload", 
        "pp3", "mcf", "abs", "aspx"
    ],
}

def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s: %(message)s", level=level)

def _unique_destination(dest: Path) -> Path:
    """Return *dest* unchanged if it doesn't exist, otherwise append _1, _2 ... """
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    parent = dest.parent
    index = 1
    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1

def categorize(folder: Path, dry_run: bool = False) -> None:
    """Group folders in *folder* into categories."""
    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory.")

    for category, extensions in CATEGORIES.items():
        category_dir = folder / category
        
        for ext in extensions:
            ext_dir = folder / ext
            if not ext_dir.is_dir():
                continue
            
            # If the category dir is the same as the ext dir (e.g. if we ran this before), skip
            if ext_dir == category_dir:
                continue

            files_to_move = list(ext_dir.iterdir())
            if not files_to_move:
                # If empty, just remove it
                if not dry_run:
                    ext_dir.rmdir()
                else:
                    logging.info("Would remove empty folder: %s", ext)
                continue

            logging.info("Grouping %s/*  →  %s/", ext, category)
            
            if not dry_run:
                category_dir.mkdir(exist_ok=True)

            for src in files_to_move:
                dest = _unique_destination(category_dir / src.name)
                
                logging.debug("  %s  →  %s", src.name, dest.relative_to(folder))
                
                if not dry_run:
                    shutil.move(str(src), dest)
            
            # Remove the now-empty extension folder
            if not dry_run:
                try:
                    ext_dir.rmdir()
                except OSError:
                    logging.warning("Could not remove folder %s (not empty after moves)", ext)

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Group extension folders into categories."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=None,
        help="Directory to organize (default: current working directory).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview moves without actually touching files.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show debug output.",
    )
    return parser.parse_args()

def main() -> None:
    args = _parse_args()
    _setup_logging(args.verbose)

    folder = Path(args.folder).resolve() if args.folder else Path.cwd()

    if args.dry_run:
        logging.info("DRY RUN — no files will be moved.")

    try:
        categorize(folder, dry_run=args.dry_run)
    except Exception as e:
        logging.error("An error occurred: %s", e)
        raise SystemExit(1)

    logging.info("Categorization complete.")

if __name__ == "__main__":
    main()
