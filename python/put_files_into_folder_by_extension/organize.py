#!/usr/bin/env python3
"""Organize files in a directory into sub-folders named by their extension,
and optionally group those sub-folders into broad categories.

Usage
-----
  # Organize the current working directory interactively
  python organize.py

  # Organize a specific directory without prompts (using defaults)
  python organize.py /path/to/folder --no-prompt

  # Preview changes on a specific directory
  python organize.py --dry-run /path/to/folder
"""

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path

# Built-in fallback configuration if config.json is not found
DEFAULT_CONFIG = {
    "skip_names": [
        "organize.py",
        "put_files_into_folder_by_extension.py",
        "categorize_organized_folders.py",
        "readme.md",
        ".gitignore",
        ".gitkeep",
        "config.json"
    ],
    "no_extension_folder": "no_extension",
    "categories": {
        "Images": [
            "png", "jpg", "jpeg", "webp", "gif", "avif", "heic", "svg", "psd", "cr2", "ico"
        ],
        "Documents": [
            "pdf", "doc", "docx", "txt", "rtf", "ppt", "pptx", "xls", "xlsx", "md", "csv", "xps", "epub", "azw3", "opml", "resolved", "_PDF", "_EBOOKS"
        ],
        "Video": [
            "mp4", "mkv", "avi", "flv", "wmv", "mpg", "m4v", "ogv", "swf", "drp", "prproj", "pdrproj", "mov"
        ],
        "Audio": [
            "mp3", "wav", "flac", "ogg", "m4a", "m4b", "aac", "pls", "m3u", "xm", "_AUDIOBOOKS"
        ],
        "Software_and_Archives": [
            "zip", "rar", "7z", "gz", "bz2", "deb", "msi", "exe", "iso", "ova", "jar", "apk", "vsix", "nzb", "dlc", "btsearch", "_SOFTWARE"
        ],
        "Code_and_Scripts": [
            "py", "html", "htm", "js", "css", "sh", "bat", "ps1", "lua", "xml", "xht", "ejs", "c", "cpp", "h"
        ],
        "AI_and_Models": [
            "safetensors", "gguf", "pt", "_AI"
        ],
        "Data_and_Config": [
            "json", "yaml", "yml", "ini", "log", "db", "sqlite3", "dat", "tpx", "synapse4", "ica", "jnlp", "crdownload", "pp3", "mcf", "abs", "aspx"
        ]
    }
}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s: %(message)s", level=level)


def load_config() -> dict:
    """Load configuration from config.json or fall back to defaults."""
    config_path = Path(__file__).parent / "config.json"
    if config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning("Could not read config.json: %s. Using default configuration.", e)
    return DEFAULT_CONFIG


def _unique_destination(dest: Path, index_cache: dict[tuple[Path, str, str], int] | None = None) -> Path:
    """Return *dest* unchanged if it doesn't exist, otherwise append _1, _2 …"""
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    parent = dest.parent

    cache_key = (parent, stem, suffix)
    index = 1
    if index_cache is not None:
        index = index_cache.get(cache_key, 1)

    # Fast path: check first 10 indices directly.
    for _ in range(10):
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            if index_cache is not None:
                index_cache[cache_key] = index + 1
            return candidate
        index += 1

    # For many duplicates, scanning the directory is much faster than repeatedly
    # checking existence via the filesystem.
    prefix = f"{stem}_"
    existing_indices = set()
    try:
        with os.scandir(parent) as it:
            for entry in it:
                name = entry.name
                if name.startswith(prefix) and name.endswith(suffix):
                    mid = name[len(prefix):len(name)-len(suffix)]
                    if mid.isdigit():
                        existing_indices.add(int(mid))
    except OSError:
        pass

    while True:
        if index not in existing_indices:
            candidate = parent / f"{stem}_{index}{suffix}"
            if not candidate.exists():
                if index_cache is not None:
                    index_cache[cache_key] = index + 1
                return candidate
        index += 1


def organize_by_extension(
    folder: Path,
    *,
    skip_names: set[str],
    no_ext_folder: str = "no_extension",
    dry_run: bool = False,
    recursive: bool = False,
    categories: dict[str, list[str]] | None = None,
) -> tuple[dict[str, int], dict[str, list[Path]]]:
    """Organize files into sub-folders by extension."""
    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory.")

    pattern = "**/*" if recursive else "*"
    files = [
        p for p in folder.glob(pattern)
        if p.is_file() and p.name.lower() not in skip_names
    ]

    summary: dict[str, int] = {}
    moved_files: dict[str, list[Path]] = {}
    index_cache: dict[tuple[Path, str, str], int] = {}
    categories_set = set(categories.keys()) if categories else set()

    for src in files:
        ext = src.suffix.lower().lstrip(".") or no_ext_folder

        # Skip files that already live inside an extension sub-folder or category sub-folder
        # (only relevant for --recursive runs)
        if src.parent != folder:
            # If the file's immediate parent is a direct child of 'folder', check if it's organized.
            if src.parent.parent == folder:
                parent_name = src.parent.name
                if parent_name.lower() == ext or parent_name in categories_set:
                    logging.debug("Skipping already-organized file: %s", src)
                    continue

        target_dir = folder / ext
        dest = _unique_destination(target_dir / src.name, index_cache=index_cache)

        logging.info("%s  →  %s", src.relative_to(folder), dest.relative_to(folder))

        if not dry_run:
            target_dir.mkdir(exist_ok=True)
            shutil.move(str(src), dest)

        summary[ext] = summary.get(ext, 0) + 1
        moved_files.setdefault(ext, []).append(dest)

    return summary, moved_files


def categorize_folders(
    folder: Path,
    categories: dict[str, list[str]],
    *,
    dry_run: bool = False,
    simulated_extensions: dict[str, list[Path]] | None = None,
) -> dict[str, int]:
    """Group extension folders in *folder* into categories."""
    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory.")

    summary: dict[str, int] = {}

    for category, extensions in categories.items():
        category_dir = folder / category

        for ext in extensions:
            ext_dir = folder / ext
            # Don't try to move a category folder into itself
            if ext_dir == category_dir:
                continue

            # Gather files from disk and/or simulation
            files_to_move = []
            has_physical = ext_dir.is_dir()
            if has_physical:
                files_to_move.extend(list(ext_dir.iterdir()))
            if simulated_extensions and ext in simulated_extensions:
                existing_names = {p.name for p in files_to_move}
                for sim_p in simulated_extensions[ext]:
                    if sim_p.name not in existing_names:
                        files_to_move.append(sim_p)

            if not files_to_move:
                if has_physical:
                    logging.info("Removing empty folder: %s", ext)
                    if not dry_run:
                        ext_dir.rmdir()
                continue

            logging.info("Grouping %s/*  →  %s/", ext, category)

            if not dry_run:
                category_dir.mkdir(exist_ok=True)

            for src in files_to_move:
                dest = _unique_destination(category_dir / src.name)
                logging.debug("  %s  →  %s", src.name, dest.relative_to(folder))
                if not dry_run:
                    shutil.move(str(src), dest)

            if not dry_run and has_physical:
                try:
                    ext_dir.rmdir()
                except OSError:
                    logging.warning(
                        "Could not remove %s — folder not empty after moves.", ext
                    )

            summary[category] = summary.get(category, 0) + 1

    return summary


def get_yes_no(prompt: str, default: bool) -> bool:
    """Prompt the user for a yes/no question."""
    suffix = " [Y/n] (default: yes)" if default else " [y/N] (default: no)"
    while True:
        try:
            val = input(prompt + suffix + ": ").strip().lower()
            if not val:
                return default
            if val in ("y", "yes"):
                return True
            if val in ("n", "no"):
                return False
            print("Please answer with 'y' or 'n'.")
        except (KeyboardInterrupt, EOFError):
            print()
            raise SystemExit("Aborted by user.")


def run_wizard() -> tuple[Path, bool, bool, bool]:
    """Interactive wizard to get configuration settings."""
    print("=== File Organizer CLI Wizard ===")
    
    # Target directory selection
    downloads = Path.home() / "Downloads"
    default_dir = downloads if downloads.is_dir() else Path.cwd()
    
    print(f"\nSelect target directory to organize:")
    print(f"  [1] {default_dir} (Default)")
    print(f"  [2] Current working directory ({Path.cwd()})")
    print(f"  [3] Custom path...")
    
    while True:
        try:
            choice = input("Enter choice [1-3, default 1]: ").strip()
            if not choice or choice == "1":
                target = default_dir
                break
            elif choice == "2":
                target = Path.cwd()
                break
            elif choice == "3":
                custom = input("Enter custom path: ").strip()
                target = Path(custom).expanduser().resolve()
                if not target.is_dir():
                    print(f"Error: '{target}' is not a valid directory. Please try again.")
                    continue
                break
            print("Please enter 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print()
            raise SystemExit("Aborted by user.")

    print(f"\nTarget directory: {target}")

    # Recursive
    print("\nNote: Recursive scanning pulls files from all nested subfolders.")
    print("      (Warning: This can break project directories or application structures!)")
    recursive = get_yes_no("Scan directories recursively?", default=False)

    # Categorize
    categorize = get_yes_no("Categorize extension folders into groups (Images, Documents, etc.)?", default=True)

    # Dry-run default: Yes (for safety)
    dry_run = get_yes_no("Run as a preview / dry-run (no files will be moved)?", default=True)

    return target, recursive, categorize, dry_run


def run_stages(
    target: Path,
    skip_names: set[str],
    no_ext_folder: str,
    categories: dict[str, list[str]],
    run_categorize: bool,
    recursive: bool,
    dry_run: bool
) -> tuple[dict[str, int], dict[str, int]]:
    """Helper to run Phase 1 and Phase 2."""
    logging.info("\n--- Phase 1: Organizing by Extension ---")
    ext_summary, moved_files = organize_by_extension(
        target,
        skip_names=skip_names,
        no_ext_folder=no_ext_folder,
        dry_run=dry_run,
        recursive=recursive,
        categories=categories,
    )

    cat_summary = {}
    if run_categorize:
        logging.info("\n--- Phase 2: Categorizing Folders ---")
        cat_summary = categorize_folders(
            target,
            categories,
            dry_run=dry_run,
            simulated_extensions=moved_files
        )

    return ext_summary, cat_summary


def print_summary(
    ext_summary: dict[str, int],
    cat_summary: dict[str, int],
    no_ext_folder: str,
    run_categorize: bool,
    dry_run: bool
) -> None:
    """Print final console summary."""
    logging.info("\n=== Execution Summary ===")
    verb = "Would move" if dry_run else "Moved"
    
    if ext_summary:
        logging.info("Sorted by Extension:")
        for ext, count in sorted(ext_summary.items()):
            label = f".{ext}" if ext != no_ext_folder else f"({no_ext_folder})"
            logging.info("  %-20s %d file(s)", label, count)
        total_files = sum(ext_summary.values())
        logging.info("%s %d file(s) in total.", verb, total_files)
    else:
        logging.info("No files organized by extension.")

    if run_categorize:
        if cat_summary:
            logging.info("\nSorted by Category:")
            for cat, count in sorted(cat_summary.items()):
                logging.info("  %-20s %d extension folder(s) merged", cat, count)
        else:
            logging.info("\nNo folders categorized.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Organize files into subfolders by extension and category."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=None,
        help="Directory to organize (triggers interactive wizard if omitted).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview moves without actually touching files.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Also organize files found in sub-directories.",
    )
    parser.add_argument(
        "--no-categorize",
        action="store_true",
        help="Skip grouping extension folders into categories.",
    )
    parser.add_argument(
        "-y", "--no-prompt",
        action="store_true",
        help="Skip all confirmation prompts (ideal for scripts/cron).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show debug output.",
    )
    args = parser.parse_args()
    _setup_logging(args.verbose)

    config = load_config()
    
    # Build skip list (always skip the script itself)
    skip_names = {name.lower() for name in config.get("skip_names", [])}
    skip_names.add(Path(__file__).name.lower())
    
    no_ext_folder = config.get("no_extension_folder", "no_extension")
    categories = config.get("categories", {})

    is_interactive = sys.stdin.isatty() and not args.no_prompt

    if args.folder is None and is_interactive:
        target, recursive, run_categorize, dry_run = run_wizard()
    else:
        target = Path(args.folder).resolve() if args.folder else Path.cwd()
        recursive = args.recursive
        run_categorize = not args.no_categorize
        dry_run = args.dry_run

    logging.info("Target directory: %s", target)
    if not target.is_dir():
        logging.error("'%s' is not a directory.", target)
        raise SystemExit(1)

    if dry_run:
        logging.info("DRY RUN — previewing changes only.")
        ext_sum, cat_sum = run_stages(
            target, skip_names, no_ext_folder, categories, run_categorize, recursive, dry_run=True
        )
        print_summary(ext_sum, cat_sum, no_ext_folder, run_categorize, dry_run=True)
    else:
        if is_interactive:
            # For interactive real execution, run a silent dry-run preview first,
            # then ask for confirmation.
            print("\nGenerating preview...")
            ext_sum, cat_sum = run_stages(
                target, skip_names, no_ext_folder, categories, run_categorize, recursive, dry_run=True
            )
            
            if not ext_sum and not cat_sum:
                print("No files to organize.")
                return

            print_summary(ext_sum, cat_sum, no_ext_folder, run_categorize, dry_run=True)
            
            proceed = get_yes_no("\nAre you sure you want to proceed with organizing files?", default=False)
            if not proceed:
                print("Aborted.")
                return

        # Perform the actual execution
        ext_sum, cat_sum = run_stages(
            target, skip_names, no_ext_folder, categories, run_categorize, recursive, dry_run=False
        )
        print_summary(ext_sum, cat_sum, no_ext_folder, run_categorize, dry_run=False)


if __name__ == "__main__":
    main()
