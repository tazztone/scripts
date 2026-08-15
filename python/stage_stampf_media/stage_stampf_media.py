#!/usr/bin/env python3
"""
Recursively stages Stampf event media (RAW/DNG photos and video files)
into flat staging folders for direct import into DaVinci Resolve timelines/albums.
"""

import argparse
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path("/mnt/wd14tb/_MY PHOTOS and VIDEOS")
STAGING_DIR = Path("/mnt/wd14tb/_RESOLVE_IMPORT_STAGING")

# Event dates to look for across the archive
DEFAULT_DATES = [
    "2018-04-13",
    "2019-07-22",
    "2019-09-28",
    "2020-12-30",
    "2020-12-31",
    "2021-01-01",
    "2022-12-31",
    "2023-01-01",
    "2023-05-28",
    "2024-03-28",
    "2024-03-29",
    "2024-03-30",
    "2025-10-31",
    "2025-11-01",
]

RAW_EXTENSIONS = {
    ".dng",
    ".arw",
    ".rw2",
    ".cr2",
    ".cr3",
    ".nef",
    ".orf",
    ".raf",
    ".tif",
    ".tiff",
}

EXTRA_PHOTO_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".heic",
    ".png",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mxf",
    ".m4v",
    ".insv",
    ".braw",
    ".avi",
    ".mkv",
}


def find_matching_event_directories(base_dir: Path, date_str: str) -> list[Path]:
    """Finds all matching directories for a given date in year folders or base folder."""
    year = date_str[:4]
    year_dir = base_dir / year
    matched: list[Path] = []

    if year_dir.is_dir():
        for item in sorted(year_dir.iterdir()):
            if item.is_dir() and item.name.startswith(date_str):
                matched.append(item)

    if not matched:
        direct = base_dir / date_str
        if direct.is_dir():
            matched.append(direct)
        for item in sorted(base_dir.iterdir()):
            if item.is_dir() and item.name.startswith(date_str):
                if item not in matched:
                    matched.append(item)

    return matched


def clean_staging_directory(dir_path: Path) -> int:
    """Removes existing symlinks in the staging directory."""
    if not dir_path.exists():
        return 0
    removed = 0
    for item in dir_path.iterdir():
        if item.is_symlink():
            item.unlink()
            removed += 1
    return removed


def generate_symlink_name(event_dir_name: str, file_path: Path, root_event_dir: Path) -> str:
    """
    Creates a unique, chronologically sortable symlink filename.
    Format: <EventFolder>__<Subdir(if any)>__<Filename>
    """
    try:
        rel_path = file_path.relative_to(root_event_dir)
        parts = rel_path.parts
        if len(parts) > 1:
            # File is inside a subfolder, e.g. "videos/C0001.MP4"
            prefix_sub = "__".join(parts[:-1])
            return f"{event_dir_name}__{prefix_sub}__{file_path.name}"
    except ValueError:
        pass
    return f"{event_dir_name}__{file_path.name}"


def stage_media(
    base_dir: Path,
    staging_dir: Path,
    dates: list[str],
    include_jpg: bool = False,
    mode: str = "all",
) -> None:
    """Recursively scans matched folders and creates flat symlink folders for Resolve."""
    photos_dir = staging_dir / "photos_raw"
    videos_dir = staging_dir / "videos"

    active_photo_exts = RAW_EXTENSIONS | (EXTRA_PHOTO_EXTENSIONS if include_jpg else set())

    if mode in ("all", "photos"):
        photos_dir.mkdir(parents=True, exist_ok=True)
    if mode in ("all", "videos"):
        videos_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" DaVinci Resolve Flat Media Staging Tool")
    print("=" * 60)
    print(f"Source Base Directory: {base_dir}")
    print(f"Staging Directory:     {staging_dir}")
    print(f"Mode:                  {mode}")
    print(f"Include JPG/HEIC:      {include_jpg}")
    print("-" * 60)

    staged_photos = 0
    staged_videos = 0
    missing_dates = []

    for date_str in dates:
        matched_dirs = find_matching_event_directories(base_dir, date_str)
        if not matched_dirs:
            missing_dates.append(date_str)
            continue

        for event_dir in matched_dirs:
            print(f"\n📁 Processing event: {event_dir.name}")
            event_photos = 0
            event_videos = 0

            # Scan recursively for all files
            for file_path in sorted(event_dir.rglob("*")):
                if not file_path.is_file():
                    continue

                ext = file_path.suffix.lower()

                # Photos (RAW/DNG + optional JPG)
                if mode in ("all", "photos") and ext in active_photo_exts:
                    link_name = generate_symlink_name(event_dir.name, file_path, event_dir)
                    link_path = photos_dir / link_name
                    if not link_path.exists() and not link_path.is_symlink():
                        try:
                            link_path.symlink_to(file_path)
                            event_photos += 1
                            staged_photos += 1
                        except Exception as e:
                            print(f"  ❌ Error symlinking photo {file_path.name}: {e}")
                    else:
                        event_photos += 1

                # Videos
                elif mode in ("all", "videos") and ext in VIDEO_EXTENSIONS:
                    link_name = generate_symlink_name(event_dir.name, file_path, event_dir)
                    link_path = videos_dir / link_name
                    if not link_path.exists() and not link_path.is_symlink():
                        try:
                            link_path.symlink_to(file_path)
                            event_videos += 1
                            staged_videos += 1
                        except Exception as e:
                            print(f"  ❌ Error symlinking video {file_path.name}: {e}")
                    else:
                        event_videos += 1

            print(f"   -> Photos: {event_photos} | Videos: {event_videos}")

    print("\n" + "=" * 60)
    print(" Staging Summary")
    print("=" * 60)
    if mode in ("all", "photos"):
        print(f"📸 Total Photos Staged: {staged_photos} -> {photos_dir}")
    if mode in ("all", "videos"):
        print(f"🎬 Total Videos Staged: {staged_videos} -> {videos_dir}")
    if missing_dates:
        print(f"⚠️  Missing dates ({len(missing_dates)}): {', '.join(missing_dates)}")
    print("=" * 60)


def open_staging_folders(staging_dir: Path, mode: str) -> None:
    """Opens staging folders in the default file manager."""
    paths_to_open = []
    photos_dir = staging_dir / "photos_raw"
    videos_dir = staging_dir / "videos"

    if mode in ("all", "photos") and photos_dir.exists():
        paths_to_open.append(photos_dir)
    if mode in ("all", "videos") and videos_dir.exists():
        paths_to_open.append(videos_dir)

    for path in paths_to_open:
        print(f"Opening {path} in file manager...")
        try:
            subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as e:
            print(f"Could not open file manager for {path}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recursively stage Stampf media into flat folders for DaVinci Resolve albums/timelines."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing symlinks in staging folders before staging.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open staging folders in file manager after staging.",
    )
    parser.add_argument(
        "--include-jpg",
        action="store_true",
        help="Include JPG, JPEG, PNG, HEIC in photos staging (default: RAW/DNG only).",
    )
    parser.add_argument(
        "--mode",
        choices=["all", "photos", "videos"],
        default="all",
        help="Filter which media to stage (default: all).",
    )
    parser.add_argument(
        "--dates",
        nargs="+",
        default=DEFAULT_DATES,
        help="Custom list of dates (YYYY-MM-DD) to stage.",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=STAGING_DIR,
        help=f"Target staging directory (default: {STAGING_DIR})",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=BASE_DIR,
        help=f"Photos base directory (default: {BASE_DIR})",
    )

    args = parser.parse_args()

    if args.clean:
        print("Cleaning staging directories...")
        r_photos = clean_staging_directory(args.staging_dir / "photos_raw")
        r_videos = clean_staging_directory(args.staging_dir / "videos")
        clean_staging_directory(args.staging_dir)
        print(f"Removed {r_photos} photos symlinks and {r_videos} videos symlinks.\n")

    stage_media(
        base_dir=args.base_dir,
        staging_dir=args.staging_dir,
        dates=args.dates,
        include_jpg=args.include_jpg,
        mode=args.mode,
    )

    if args.open:
        open_staging_folders(args.staging_dir, args.mode)


if __name__ == "__main__":
    main()
