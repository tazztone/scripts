#!/usr/bin/env python3
"""Organize files in a directory into sub-folders named by their extension.

Usage
-----
  # Organize the current working directory
  python put_files_into_folder_by_extension.py

  # Organize a specific directory
  python put_files_into_folder_by_extension.py /path/to/folder

  # Preview changes without moving anything
  python put_files_into_folder_by_extension.py --dry-run /path/to/folder

  # Also recurse into sub-directories
  python put_files_into_folder_by_extension.py --recursive /path/to/folder
"""

import argparse
import logging
import os
import shutil
from pathlib import Path

# Files without an extension land in this folder
NO_EXT_FOLDER = "no_extension"

# Names (case-insensitive) that are never moved
SKIP_NAMES: set[str] = {
    "put_files_into_folder_by_extension.py",
    "readme.md",
    ".gitignore",
    ".gitkeep",
}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s: %(message)s", level=level)


def _unique_destination(dest: Path) -> Path:
    """Return *dest* unchanged if it doesn't exist, otherwise append _1, _2 … """
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


def organize(
    folder: Path,
    *,
    dry_run: bool = False,
    recursive: bool = False,
) -> dict[str, int]:
    """Organize *folder*; return a summary dict {extension: file_count}."""
    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory.")

    pattern = "**/*" if recursive else "*"
    files = [
        p for p in folder.glob(pattern)
        if p.is_file() and p.name.lower() not in SKIP_NAMES
    ]

    summary: dict[str, int] = {}

    for src in files:
        # Skip files that already live inside an extension sub-folder we created
        # (only relevant for --recursive runs)
        if src.parent != folder:
            rel = src.relative_to(folder)
            # If the immediate parent is itself a known ext-folder, skip.
            if len(rel.parts) == 2:
                logging.debug("Skipping already-organised file: %s", src)
                continue

        ext = src.suffix.lower().lstrip(".") or NO_EXT_FOLDER
        target_dir = folder / ext
        dest = _unique_destination(target_dir / src.name)

        logging.info("%s  →  %s", src.relative_to(folder), dest.relative_to(folder))

        if not dry_run:
            target_dir.mkdir(exist_ok=True)
            shutil.move(str(src), dest)

        summary[ext] = summary.get(ext, 0) + 1

    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Organize files into sub-folders by extension."
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
        "--recursive",
        action="store_true",
        help="Also organise files found in sub-directories.",
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
        summary = organize(folder, dry_run=args.dry_run, recursive=args.recursive)
    except NotADirectoryError as exc:
        logging.error(exc)
        raise SystemExit(1) from exc

    if summary:
        logging.info("\nSummary:")
        for ext, count in sorted(summary.items()):
            label = f".{ext}" if ext != NO_EXT_FOLDER else "(no extension)"
            logging.info("  %-20s %d file(s)", label, count)
        total = sum(summary.values())
        verb = "Would move" if args.dry_run else "Moved"
        logging.info("%s %d file(s) in total.", verb, total)
    else:
        logging.info("Nothing to organise.")


if __name__ == "__main__":
    main()
