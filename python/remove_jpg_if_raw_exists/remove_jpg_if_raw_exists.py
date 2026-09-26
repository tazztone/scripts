#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "exifread",
# ]
# ///
"""
remove_jpg_if_raw_exists.py
Only removes a JPEG if:
  1. A valid RAW file with the same stem exists in the same folder, AND
  2. EXIF evidence suggests it was shot by the camera (not exported by an editor)
"""

import os
import sys
import logging
import argparse
import shutil
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

logging.getLogger("exifread").setLevel(logging.ERROR)  # suppress MakerNote parse noise

try:
    import exifread
except ImportError:
    sys.exit("Missing dependency: run 'uv add --script ... exifread'")

RAW_EXTENSIONS = {
    ".dng",
    ".cr2",
    ".cr3",
    ".nef",
    ".arw",
    ".orf",
    ".raf",
    ".rw2",
    ".pef",
    ".srw",
}
JPG_EXTENSIONS = {".jpg", ".jpeg"}

# Software strings that indicate the JPG was produced by a post-processing tool.
# Case-insensitive substring match.
EDITOR_SOFTWARE_SIGNATURES = [
    "adobe lightroom",
    "adobe photoshop",
    "capture one",
    "darktable",
    "luminar",
    "on1",
    "dxo",
    "affinity",
    "gimp",
    "rawtherapee",
    "silkypix",
    "rapidraw",
    "pixelmator",
    "acdsee",
    "skylum",
]

EDITOR_SOFTWARE_REGEX = re.compile("|".join(map(re.escape, EDITOR_SOFTWARE_SIGNATURES)))

# Manufacturer prefixes seen in exifread. Decoding varies by brand.
MAKER_NOTE_PREFIXES = (
    "MakerNote",  # Canon, Nikon, Olympus, Fuji, Apple, DJI, Casio, Panasonic raw
    "Sony ",  # Sony decoded tags
    "Canon ",  # Canon decoded (redundant but explicit)
    "Nikon ",  # Nikon decoded
    "Fujifilm ",
    "Olympus ",
    "Panasonic ",
    "Pentax ",
    "Leica ",
    "Ricoh ",
    "Apple ",  # iPhone MakerNotes
    "DJI ",  # Drone cameras
    "Casio ",
    "Minolta ",
    "Samsung ",
    "Sigma ",
)
MAKER_SET = frozenset(MAKER_NOTE_PREFIXES)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Remove camera-paired JPEGs when a RAW counterpart exists."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=None,
        help="Root directory to scan (prompted when --wizard)",
    )
    parser.add_argument(
        "--wizard",
        action="store_true",
        help="Interactive mode: prompts for folder, dry-runs, then confirms a trash move",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without deleting"
    )
    parser.add_argument(
        "--trash", metavar="DIR", help="Move to trash folder instead of deleting"
    )
    parser.add_argument("--log", metavar="FILE", help="Write log to this file")
    parser.add_argument(
        "--min-raw-size",
        type=int,
        default=100_000,
        help="Min RAW file size in bytes (default: 100 KB)",
    )
    parser.add_argument(
        "--skip-exif",
        action="store_true",
        help="Skip EXIF check (revert to stem-only matching)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Log skipped files with no RAW counterpart"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel EXIF threads (default: 4; use 2 for HDDs, 8+ for SSDs)",
    )
    args = parser.parse_args()
    if not args.wizard and not args.directory:
        parser.error("directory is required without --wizard")
    if args.workers < 1:
        parser.error("--workers must be >= 1")
    if args.min_raw_size < 0:
        parser.error("--min-raw-size must be >= 0")
    return args


def setup_logging(args, log_file=None):
    level = logging.DEBUG if args.verbose else logging.INFO

    # Terminal handler: clean message-only output
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(message)s"))

    handlers = [console]

    # File handler: full timestamps and levels for the audit trail
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        handlers.append(fh)

    # Manual root logger configuration (safer than basicConfig)
    logger = logging.getLogger()
    logger.setLevel(level)
    for h in handlers:
        logger.addHandler(h)


def is_valid_raw(path: Path, min_size: int) -> bool:
    try:
        return path.stat().st_size >= min_size
    except OSError:
        return False


def read_exif(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            # We must use details=True to see MakerNote tags, which are stripped by editors.
            # No stop_tag: it halts parsing at the first matching tag, which can
            # hide the MakerNote/JFIF/Software tags the safety checks need.
            return exifread.process_file(f, details=True)
    except Exception:
        return {}


def _check_exif(jpg_path: Path) -> tuple[bool, str]:
    """Internal EXIF logic. Returns (is_camera_original, reason)."""
    tags = read_exif(jpg_path)
    if not tags:
        return False, "no EXIF data found"

    # --- Check 1: Software tag (strong signal when present) ---
    software = str(tags.get("Image Software", "")).strip()
    software_lower = software.lower()
    if software_lower and EDITOR_SOFTWARE_REGEX.search(software_lower):
        return False, f"editor software tag: '{software}'"

    # --- Check 2: JFIF header (extremely reliable) ---
    if "JFIF JFIFVersion" in tags or any(k.startswith("JFIF") for k in tags):
        return False, "JFIF header present — was re-encoded by software"

    # --- Check 3: MakerNotes presence (camera-agnostic) ---
    # Captures both decoded tags (e.g., 'Sony Quality') and raw blobs (e.g., 'EXIF MakerNote').
    has_maker = any(
        any(k.startswith(p) for p in MAKER_SET) or "MakerNote" in k for k in tags
    )
    if not has_maker:
        return False, "no maker notes block — likely editor export"

    # --- Check 4: DateTimeOriginal must exist ---
    if not tags.get("EXIF DateTimeOriginal"):
        return False, "DateTimeOriginal missing — likely an edited export"

    return True, f"camera original (software='{software}')"


def is_camera_original(jpg_path: Path) -> tuple[bool, str]:
    """Wrapper that emits exactly one debug log per file."""
    result, reason = _check_exif(jpg_path)
    logging.debug(f"EXIF {jpg_path.name}: {reason}")
    return result, reason


def process_jpg(
    jpg_path: Path,
    raw_counterpart: Path,
    dry_run: bool,
    trash_dir: Path | None,
    skip_exif: bool,
    root: Path,
) -> str:
    """Returns 'deleted', 'kept_edited', or 'error'."""

    # Log paths relative to the scan root: basenames repeat across
    # folders (DSC00001.JPG, ...) and a bare name is unauditable.
    try:
        display = str(jpg_path.relative_to(root))
    except ValueError:
        display = jpg_path.name

    if not skip_exif:
        ok, reason = is_camera_original(jpg_path)
        if not ok:
            logging.info(f"  KEPT  {display:<45}  ← {reason}")
            return "kept_edited"

    if dry_run:
        logging.info(f"  DEL   {display:<45}  ← RAW: {raw_counterpart.name}")
        return "deleted"

    if trash_dir:
        rel = jpg_path.relative_to(root)
        dest = trash_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            if dest.exists():
                logging.error(f"  ERROR Refusing to overwrite {dest}")
                return "error"
            shutil.move(str(jpg_path), dest)
            logging.info(f"  DEL   {display:<45}  ← Moved to trash")
            return "deleted"
        except OSError as e:
            logging.error(f"  ERROR Failed to move {display}: {e}")
            return "error"
    else:
        try:
            jpg_path.unlink()
            logging.info(f"  DEL   {display:<45}  ← {raw_counterpart.name}")
            return "deleted"
        except OSError as e:
            logging.error(f"  ERROR Failed to delete {display}: {e}")
            return "error"


def scan_and_remove(root: Path, trash_dir: Path | None, args):
    deleted = kept_no_raw = kept_edited = errors = 0

    logging.info(f"Scan dir : {root}")
    logging.info(f"Mode     : {'DRY RUN' if args.dry_run else 'LIVE'}")
    logging.info(f"EXIF     : {'on' if not args.skip_exif else '⚠ OFF (stem-only — skipping safety checks)'}")
    logging.info(f"Trash    : {trash_dir or 'hard delete'}")
    logging.info("-" * 60)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for dirpath, dirnames, files in os.walk(root):
            dir_ = Path(dirpath)

            # Never rescan the trash: it may live inside the scan root
            # (e.g. <root>/_TRASH) and holds only already-moved files.
            if trash_dir and (
                dir_ == trash_dir or trash_dir in dir_.parents
            ):
                dirnames[:] = []
                continue

            raw_map = {
                p.stem.lower(): p
                for f in files
                if (p := dir_ / f).suffix.lower() in RAW_EXTENSIONS
                and is_valid_raw(p, args.min_raw_size)
            }

            futures = []
            for f in files:
                p = dir_ / f
                if p.suffix.lower() not in JPG_EXTENSIONS:
                    continue

                raw_counterpart = raw_map.get(p.stem.lower())
                if raw_counterpart is None:
                    if args.verbose:
                        logging.info(f"  SKIP  {p.name:<45}  [no RAW match]")
                    kept_no_raw += 1
                    continue

                futures.append(
                    executor.submit(
                        process_jpg,
                        p,
                        raw_counterpart,
                        args.dry_run,
                        trash_dir,
                        args.skip_exif,
                        root,
                    )
                )

            for future in futures:
                result = future.result()
                if result == "deleted":
                    deleted += 1
                elif result == "kept_edited":
                    kept_edited += 1
                else:
                    errors += 1

    action = "Would remove" if args.dry_run else ("Moved" if trash_dir else "Deleted")
    logging.info("")
    logging.info(f"{action:<13}: {deleted} JPGs")
    logging.info(f"  No RAW match  : {kept_no_raw}")
    logging.info(f"  Editor export : {kept_edited}")
    logging.info(f"  Errors        : {errors}")

    return {
        "deleted": deleted,
        "kept_no_raw": kept_no_raw,
        "kept_edited": kept_edited,
        "errors": errors,
    }


def prompt(text: str, default: str | None = None) -> str:
    """Prompt with an optional default. Ctrl-C / Ctrl-D aborts cleanly."""
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(130)
    return value or default or ""


def run_wizard(args) -> dict:
    """Interactive flow: folder -> dry-run summary -> confirm -> trash move."""
    print("Photo cleanup wizard (nothing is deleted until you confirm).")
    print()

    root = None
    while root is None:
        answer = prompt("Photo folder to scan", args.directory)
        candidate = Path(answer).expanduser().resolve() if answer else None
        if candidate and candidate.is_dir():
            root = candidate
        else:
            print(f"  Not a directory: {answer or '(empty)'}")

    default_trash = str(root / "_TRASH")
    trash_dir = None
    while trash_dir is None:
        answer = prompt("Trash folder (files are moved here)", args.trash or default_trash)
        candidate = Path(answer).expanduser().resolve() if answer else None
        if candidate is None:
            print("  Please enter a trash folder.")
        else:
            trash_dir = candidate

    print()
    print(f"Step 1/2: previewing {root} ...")
    dry_args = argparse.Namespace(**{**vars(args), "dry_run": True})
    preview = scan_and_remove(root, None, dry_args)

    if preview["deleted"] == 0:
        print("Nothing to move: no deletable camera JPEGs found.")
        return preview

    if args.dry_run:
        print("Dry-run requested: stopping after the preview.")
        return preview

    print()
    answer = prompt(
        f"Step 2/2: move {preview['deleted']} JPG(s) to {trash_dir}? [y/N]"
    )
    if answer.lower() not in ("y", "yes"):
        print("Aborted: no files were moved.")
        return preview

    trash_dir.mkdir(parents=True, exist_ok=True)
    live_args = argparse.Namespace(**{**vars(args), "dry_run": False})
    result = scan_and_remove(root, trash_dir, live_args)
    print()
    print(f"Moved {result['deleted']} JPG(s) to {trash_dir}.")
    print("Undo: move them back from the trash folder preserving its tree.")
    return result


def main():
    args = parse_args()
    setup_logging(args, args.log)

    if args.wizard:
        run_wizard(args)
        return

    root = Path(args.directory).resolve()
    if not root.is_dir():
        logging.error(f"Not a directory: {root}")
        sys.exit(1)

    trash_dir = None
    if args.trash:
        trash_dir = Path(args.trash).resolve()
        trash_dir.mkdir(parents=True, exist_ok=True)
        # Trash may live inside the scan root: scan_and_remove prunes it
        # from the walk so trashed files are never rescanned.

    scan_and_remove(root, trash_dir, args)


if __name__ == "__main__":
    main()
