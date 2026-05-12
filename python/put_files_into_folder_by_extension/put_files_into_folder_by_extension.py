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

# Names (case-insensitive) that are never moved.
# Using Path(__file__).name ensures the skip-list stays correct if the script is renamed.
SKIP_NAMES: set[str] = {
    Path(__file__).name.lower(),
    "readme.md",
    ".gitignore",
    ".gitkeep",
}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s: %(message)s", level=level)


def _unique_destination(dest: Path, index_cache: dict[tuple[Path, str, str], int] | None = None) -> Path:
    """Return *dest* unchanged if it doesn't exist, otherwise append _1, _2 … """
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
    index_cache: dict[tuple[Path, str, str], int] = {}

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
        dest = _unique_destination(target_dir / src.name, index_cache=index_cache)

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
