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
from pathlib import Path

try:
    import exifread
except ImportError:
    sys.exit("Missing dependency: pip install exifread")

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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Remove camera-paired JPEGs when a RAW counterpart exists."
    )
    parser.add_argument("directory", help="Root directory to scan")
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
    return parser.parse_args()


def setup_logging(log_file=None):
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def is_valid_raw(path: Path, min_size: int) -> bool:
    try:
        return path.stat().st_size >= min_size
    except OSError:
        return False


def read_exif(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            # We need details=True to see MakerNote tags, which are stripped by editors.
            return exifread.process_file(f, details=True)
    except Exception:
        return {}


def is_camera_original(jpg_path: Path) -> tuple[bool, str]:
    """
    Returns (True, reason) if the JPG looks like a direct camera output.
    Returns (False, reason) if it looks like an editor export — should be kept.
    """
    tags = read_exif(jpg_path)
    if not tags:
        # No EXIF at all — be conservative, don't delete.
        return False, "no EXIF data found"

    # --- Check 1: Software tag (strong signal when present) ---
    software = str(tags.get("Image Software", "")).strip()
    software_lower = software.lower()
    if software_lower:
        for sig in EDITOR_SOFTWARE_SIGNATURES:
            if sig in software_lower:
                return False, f"editor software tag: '{software}'"
        # If software is present but NOT a known editor → likely camera firmware.
        # However, we still continue to other checks for extra safety.

    # --- Check 2: JFIF header (extremely reliable) ---
    # Camera JPGs (Sony, Nikon, Canon etc.) use EXIF APP1, not JFIF APP0.
    # If JFIF tags appear, the file was re-encoded by software.
    if "JFIF JFIFVersion" in tags or any(k.startswith("JFIF") for k in tags):
        return False, "JFIF header present — file was re-encoded by an editor"

    # --- Check 3: MakerNotes presence (camera-agnostic) ---
    # Camera originals always have a rich maker notes block.
    # Editor exports typically strip or omit it entirely.
    maker_tags = [
        k
        for k in tags
        if k.startswith("MakerNote")
        or any(
            k.startswith(brand)
            for brand in (
                "Sony ",
                "Canon ",
                "Nikon ",
                "Fujifilm ",
                "Olympus ",
                "Panasonic ",
                "Pentax ",
                "Leica ",
                "Ricoh ",
            )
        )
    ]
    if not maker_tags:
        return False, "no maker notes block — likely editor export (no camera maker tags found)"

    # --- Check 4: DateTimeOriginal must exist ---
    if not tags.get("EXIF DateTimeOriginal"):
        return False, "DateTimeOriginal missing — likely an edited export"

    return True, f"camera original (software='{software}')"


def process_jpg(
    jpg_path: Path,
    raw_counterpart: Path,
    dry_run: bool,
    trash_dir: Path | None,
    skip_exif: bool,
    root: Path,
) -> str:
    """Returns 'deleted', 'kept', or 'error'."""

    if not skip_exif:
        ok, reason = is_camera_original(jpg_path)
        if not ok:
            logging.info(f"KEPT (editor export): {jpg_path}  [{reason}]")
            return "kept"

    if dry_run:
        logging.info(
            f"[DRY RUN] Would remove: {jpg_path}  (RAW: {raw_counterpart.name})"
        )
        return "deleted"

    if trash_dir:
        rel = jpg_path.relative_to(root)
        dest = trash_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(jpg_path), dest)
            logging.info(f"Moved to trash: {jpg_path} → {dest}")
            return "deleted"
        except OSError as e:
            logging.error(f"Failed to move {jpg_path}: {e}")
            return "error"
    else:
        try:
            jpg_path.unlink()
            logging.info(f"Deleted: {jpg_path}  (RAW: {raw_counterpart.name})")
            return "deleted"
        except OSError as e:
            logging.error(f"Failed to delete {jpg_path}: {e}")
            return "error"


def scan_and_remove(root: Path, args):
    deleted = kept = errors = 0
    trash_dir = Path(args.trash).resolve() if args.trash else None

    for dirpath, _, files in os.walk(root):
        dir_ = Path(dirpath)

        raw_map = {
            p.stem.lower(): p
            for f in files
            if (p := dir_ / f).suffix.lower() in RAW_EXTENSIONS
            and is_valid_raw(p, args.min_raw_size)
        }

        for f in files:
            p = dir_ / f
            if p.suffix.lower() not in JPG_EXTENSIONS:
                continue

            raw_counterpart = raw_map.get(p.stem.lower())
            if raw_counterpart is None:
                if args.verbose:
                    logging.info(f"SKIPPED (no RAW): {p.name}")
                kept += 1
                continue

            result = process_jpg(
                p,
                raw_counterpart,
                dry_run=args.dry_run,
                trash_dir=trash_dir,
                skip_exif=args.skip_exif,
                root=root,
            )
            if result == "deleted":
                deleted += 1
            elif result == "kept":
                kept += 1
            else:
                errors += 1

    action = "Would remove" if args.dry_run else ("Moved" if trash_dir else "Deleted")
    logging.info(
        f"\n{action}: {deleted} JPGs  |  Kept (no RAW or editor export): {kept}  |  Errors: {errors}"
    )


def main():
    args = parse_args()
    setup_logging(args.log)

    root = Path(args.directory).resolve()
    if not root.is_dir():
        logging.error(f"Not a directory: {root}")
        sys.exit(1)

    if args.trash:
        trash_dir = Path(args.trash).resolve()
        trash_dir.mkdir(parents=True, exist_ok=True)
        if root in trash_dir.parents or root == trash_dir:
            logging.error("Trash folder must be outside the scan directory.")
            sys.exit(1)

    logging.info(
        f"Scanning: {root}  |  dry_run={args.dry_run}  |  "
        f"exif_check={not args.skip_exif}  |  trash={args.trash}"
    )
    scan_and_remove(root, args)


if __name__ == "__main__":
    main()
