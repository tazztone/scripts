#!/usr/bin/env python3
"""
Recursively stages event media (RAW/DNG photos and video files)
into flat staging folders for direct import into DaVinci Resolve, DxO PhotoLab,
Lightroom, LosslessCut, and other NLEs/editors.

Supports:
- Cross-platform NTFS hardlinks (Linux and Windows 11), symlinks, and copies.
- Direct event date discovery from Immich albums via API (--immich-album).
- Safe dry-runs, filename sanitization, and automated directory cleanup.
"""

import argparse
import json
import os
import platform
import re
import string
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Fallback event dates to look for across the archive when not using --immich-album
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

ILLEGAL_NTFS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def load_immich_env() -> tuple[str, str, str | None]:
    """Loads Immich configuration from environment variables or local .env file."""
    base_url = os.getenv("IMMICH_BASE_URL", "").rstrip("/")
    api_key = os.getenv("IMMICH_API_KEY", "")
    album_id = os.getenv("IMMICH_ALBUM_ID")

    if not base_url or not api_key:
        possible_envs = [
            Path(__file__).parent / ".env",
            Path.cwd() / ".env",
            Path.cwd() / "python" / "immich-api" / ".env",
        ]
        for env_file in possible_envs:
            if env_file.is_file():
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if "=" in line and not line.startswith("#"):
                                k, v = line.split("=", 1)
                                k, v = k.strip(), v.strip().strip("'\"")
                                if k == "IMMICH_BASE_URL" and not base_url:
                                    base_url = v.rstrip("/")
                                elif k == "IMMICH_API_KEY" and not api_key:
                                    api_key = v
                                elif k == "IMMICH_ALBUM_ID" and not album_id:
                                    album_id = v
                except Exception:
                    pass

    return base_url or "http://localhost:2283", api_key, album_id


def fetch_immich_album_dates(
    album_ref: str,
    base_url: str,
    api_key: str,
) -> tuple[str, list[str]]:
    """
    Queries Immich API for an album (by UUID or name) and extracts all unique capture dates (YYYY-MM-DD).
    Returns (album_name: str, dates: list[str]).
    """
    if not api_key:
        raise ValueError(
            "Immich API key not found. Please set IMMICH_API_KEY env var or configure .env file."
        )

    headers = {
        "x-api-key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # 1. Fetch all albums to resolve UUID / Name
    req = urllib.request.Request(f"{base_url}/api/albums", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            albums = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ConnectionError(f"Failed to connect to Immich at {base_url}/api/albums: {e}")

    target_album = None
    # Match by exact UUID
    for a in albums:
        if a.get("id", "").lower() == album_ref.lower():
            target_album = a
            break

    # Match by name (exact or substring)
    if not target_album:
        for a in albums:
            if a.get("albumName", "").lower() == album_ref.lower():
                target_album = a
                break
    if not target_album:
        for a in albums:
            if album_ref.lower() in a.get("albumName", "").lower():
                target_album = a
                break

    if not target_album:
        raise ValueError(f"No album found in Immich matching '{album_ref}'")

    album_id = target_album["id"]
    album_name = target_album.get("albumName", "Untitled Album")
    unique_dates = set()

    # 2. Query album details
    req_det = urllib.request.Request(f"{base_url}/api/albums/{album_id}", headers=headers)
    with urllib.request.urlopen(req_det, timeout=10) as resp:
        album_data = json.loads(resp.read().decode("utf-8"))

    if "assets" in album_data and isinstance(album_data["assets"], list):
        for asset in album_data["assets"]:
            dt = asset.get("localDateTime") or asset.get("fileCreatedAt") or asset.get("createdAt")
            if dt:
                unique_dates.add(str(dt)[:10])

    # 3. If timeline bucket format (Immich v3+)
    if not unique_dates:
        try:
            req_buckets = urllib.request.Request(
                f"{base_url}/api/timeline/buckets?albumId={album_id}", headers=headers
            )
            with urllib.request.urlopen(req_buckets, timeout=10) as resp:
                buckets = json.loads(resp.read().decode("utf-8"))
            for b in buckets:
                tb = b.get("timeBucket")
                if not tb:
                    continue
                req_b = urllib.request.Request(
                    f"{base_url}/api/timeline/bucket?albumId={album_id}&timeBucket={tb}",
                    headers=headers,
                )
                with urllib.request.urlopen(req_b, timeout=10) as resp:
                    b_data = json.loads(resp.read().decode("utf-8"))
                    created_ats = b_data.get("fileCreatedAt", []) or b_data.get("createdAt", [])
                    for dt in created_ats:
                        if dt:
                            unique_dates.add(str(dt)[:10])
        except Exception:
            pass

    sorted_dates = sorted(unique_dates)
    return album_name, sorted_dates


def resolve_default_paths() -> tuple[Path, Path]:
    """
    Dynamically discovers default base and staging paths across Linux, Windows, and macOS.
    Checks environment variables, Windows drive letters, and Linux mount locations.
    """
    env_base = os.getenv("STAMPF_BASE_DIR") or os.getenv("MEDIA_BASE_DIR")
    env_staging = os.getenv("STAMPF_STAGING_DIR") or os.getenv("MEDIA_STAGING_DIR")
    if env_base and env_staging:
        return Path(env_base), Path(env_staging)

    system = platform.system()

    if system == "Windows":
        for letter in string.ascii_uppercase:
            cand_base = Path(f"{letter}:/_MY PHOTOS and VIDEOS")
            cand_staging = Path(f"{letter}:/_RESOLVE_IMPORT_STAGING")
            if cand_base.is_dir():
                return cand_base, cand_staging
        return Path("D:/_MY PHOTOS and VIDEOS"), Path("D:/_RESOLVE_IMPORT_STAGING")

    # Linux / macOS / Unix detection
    standard_base = Path("/mnt/wd14tb/_MY PHOTOS and VIDEOS")
    standard_staging = Path("/mnt/wd14tb/_RESOLVE_IMPORT_STAGING")
    if standard_base.is_dir():
        return standard_base, standard_staging

    for mount_root in [Path("/media"), Path("/mnt"), Path("/Volumes")]:
        if mount_root.is_dir():
            try:
                for sub in mount_root.iterdir():
                    cand_base = sub / "_MY PHOTOS and VIDEOS"
                    cand_staging = sub / "_RESOLVE_IMPORT_STAGING"
                    if cand_base.is_dir():
                        return cand_base, cand_staging
                    if sub.is_dir():
                        for nested in sub.iterdir():
                            c_base = nested / "_MY PHOTOS and VIDEOS"
                            c_staging = nested / "_RESOLVE_IMPORT_STAGING"
                            if c_base.is_dir():
                                return c_base, c_staging
            except PermissionError:
                continue

    return standard_base, standard_staging


def sanitize_filename(name: str) -> str:
    """Removes or replaces characters forbidden on Windows NTFS."""
    sanitized = ILLEGAL_NTFS_CHARS.sub("_", name)
    sanitized = sanitized.strip(". ")
    return sanitized or "unnamed"


def generate_staged_name(event_dir_name: str, file_path: Path, root_event_dir: Path) -> str:
    """
    Creates a unique, chronologically sortable staged filename compliant with Windows and Linux.
    Format: <EventFolder>__<Subdir(if any)>__<Filename>
    """
    clean_event = sanitize_filename(event_dir_name)
    clean_file_name = sanitize_filename(file_path.name)
    try:
        rel_path = file_path.relative_to(root_event_dir)
        parts = rel_path.parts
        if len(parts) > 1:
            clean_sub = "__".join(sanitize_filename(p) for p in parts[:-1])
            return f"{clean_event}__{clean_sub}__{clean_file_name}"
    except ValueError:
        pass
    return f"{clean_event}__{clean_file_name}"


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


def validate_staging_safety(base_dir: Path, staging_dir: Path) -> None:
    """Ensures staging directory is not base directory or parent/child."""
    try:
        b_res = base_dir.resolve()
        s_res = staging_dir.resolve()
    except Exception:
        b_res = base_dir.absolute()
        s_res = staging_dir.absolute()

    if b_res == s_res:
        raise ValueError(f"Safety Error: Staging directory cannot be identical to base directory ({b_res})")
    if s_res in b_res.parents:
        raise ValueError(f"Safety Error: Staging directory ({s_res}) is a parent of base directory ({b_res})")


def clean_staging_directory(dir_path: Path, dry_run: bool = False, force: bool = False) -> int:
    """
    Safely removes staged files/hardlinks and symlinks in the staging directory.
    Will never delete directories or single-link regular files unless forced.
    """
    if not dir_path.exists():
        return 0

    if dir_path.name not in ("photos_raw", "videos", "_RESOLVE_IMPORT_STAGING"):
        print(f"⚠️  Safety Warning: Refusing to clean unexpected folder name: {dir_path}")
        return 0

    removed = 0
    for item in list(dir_path.iterdir()):
        if item.is_dir() and not item.is_symlink():
            continue

        is_link = item.is_symlink()
        is_file = item.is_file()

        if is_link:
            if not dry_run:
                try:
                    item.unlink()
                except OSError as e:
                    print(f"  ❌ Error unlinking symlink {item.name}: {e}")
                    continue
            removed += 1
        elif is_file:
            try:
                stat = item.stat()
                if stat.st_nlink > 1 or force:
                    if not dry_run:
                        item.unlink()
                    removed += 1
                else:
                    print(f"  ⚠️ Skipping potential single-copy file (nlink=1): {item.name}")
            except OSError as e:
                print(f"  ❌ Error stat/unlinking {item.name}: {e}")

    return removed


def create_staged_link(
    src: Path,
    dst: Path,
    link_type: str = "hardlink",
    dry_run: bool = False,
) -> tuple[bool, str]:
    """
    Creates a staged link (hardlink, symlink, or copy) with idempotency and self-healing.
    Returns (success: bool, action: str).
    """
    if dry_run:
        return True, "dry_run"

    if dst.is_symlink() or dst.exists():
        try:
            if dst.exists() and dst.samefile(src):
                return True, "already_staged"
        except (OSError, ValueError):
            pass

        try:
            dst.unlink()
        except OSError as e:
            print(f"  ❌ Error removing stale destination {dst.name}: {e}")
            return False, "error"

    try:
        if link_type == "hardlink":
            os.link(src, dst)
            return True, "hardlink"
        elif link_type == "symlink":
            dst.symlink_to(src)
            return True, "symlink"
        elif link_type == "copy":
            import shutil
            shutil.copy2(src, dst)
            return True, "copy"
        else:
            raise ValueError(f"Unsupported link_type: {link_type}")
    except OSError as e:
        if link_type == "hardlink" and getattr(e, "errno", None) == 18:
            print(f"  ⚠️ Cross-device hardlink impossible for {src.name}. Falling back to symlink.")
            try:
                dst.symlink_to(src)
                return True, "symlink_fallback"
            except Exception as sym_err:
                print(f"  ❌ Symlink fallback failed for {src.name}: {sym_err}")
                return False, "error"
        print(f"  ❌ Error creating {link_type} for {src.name}: {e}")
        return False, "error"


def stage_media(
    base_dir: Path,
    staging_dir: Path,
    dates: list[str],
    include_jpg: bool = False,
    mode: str = "all",
    link_type: str = "hardlink",
    dry_run: bool = False,
    album_name: str | None = None,
) -> None:
    """Recursively scans matched folders and creates flat staging folders for editors and NLEs."""
    validate_staging_safety(base_dir, staging_dir)

    photos_dir = staging_dir / "photos_raw"
    videos_dir = staging_dir / "videos"

    active_photo_exts = RAW_EXTENSIONS | (EXTRA_PHOTO_EXTENSIONS if include_jpg else set())

    if not dry_run:
        if mode in ("all", "photos"):
            photos_dir.mkdir(parents=True, exist_ok=True)
        if mode in ("all", "videos"):
            videos_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print(" Flat Media Staging Tool (Cross-Platform / Immich Integration)")
    print("=" * 65)
    print(f"Platform:              {platform.system()} ({platform.release()})")
    if album_name:
        print(f"Immich Album Source:   {album_name}")
    print(f"Source Base Directory: {base_dir}")
    print(f"Staging Directory:     {staging_dir}")
    print(f"Target Dates Count:    {len(dates)} dates")
    print(f"Mode:                  {mode}")
    print(f"Link Type:             {link_type}")
    print(f"Include JPG/HEIC:      {include_jpg}")
    print(f"Dry Run:               {dry_run}")
    print("-" * 65)

    staged_photos = 0
    staged_videos = 0
    total_photo_bytes = 0
    total_video_bytes = 0
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

            for file_path in sorted(event_dir.rglob("*")):
                if not file_path.is_file():
                    continue

                ext = file_path.suffix.lower()

                # Photos (RAW/DNG + optional JPG)
                if mode in ("all", "photos") and ext in active_photo_exts:
                    link_name = generate_staged_name(event_dir.name, file_path, event_dir)
                    dst_path = photos_dir / link_name
                    success, action = create_staged_link(
                        file_path, dst_path, link_type=link_type, dry_run=dry_run
                    )
                    if success:
                        event_photos += 1
                        staged_photos += 1
                        try:
                            total_photo_bytes += file_path.stat().st_size
                        except OSError:
                            pass

                # Videos
                elif mode in ("all", "videos") and ext in VIDEO_EXTENSIONS:
                    link_name = generate_staged_name(event_dir.name, file_path, event_dir)
                    dst_path = videos_dir / link_name
                    success, action = create_staged_link(
                        file_path, dst_path, link_type=link_type, dry_run=dry_run
                    )
                    if success:
                        event_videos += 1
                        staged_videos += 1
                        try:
                            total_video_bytes += file_path.stat().st_size
                        except OSError:
                            pass

            print(f"   -> Photos: {event_photos} | Videos: {event_videos}")

    total_gb = (total_photo_bytes + total_video_bytes) / (1024 ** 3)

    print("\n" + "=" * 65)
    print(" Staging Summary")
    print("=" * 65)
    if mode in ("all", "photos"):
        print(f"📸 Total Photos Staged: {staged_photos} -> {photos_dir}")
    if mode in ("all", "videos"):
        print(f"🎬 Total Videos Staged: {staged_videos} -> {videos_dir}")
    if link_type == "hardlink":
        print(f"💾 Storage Saved (Zero Duplication): {total_gb:.2f} GB")
    if missing_dates:
        print(f"⚠️  Missing dates on disk ({len(missing_dates)}): {', '.join(missing_dates)}")
    print("=" * 65)


def open_staging_folders(staging_dir: Path, mode: str) -> None:
    """Opens staging folders in the default file manager across Linux, Windows, and macOS."""
    paths_to_open = []
    photos_dir = staging_dir / "photos_raw"
    videos_dir = staging_dir / "videos"

    if mode in ("all", "photos") and photos_dir.exists():
        paths_to_open.append(photos_dir)
    if mode in ("all", "videos") and videos_dir.exists():
        paths_to_open.append(videos_dir)

    system = platform.system()
    for path in paths_to_open:
        print(f"Opening {path} in file manager...")
        try:
            if system == "Windows":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif system == "Darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as e:
            print(f"Could not open file manager for {path}: {e}")


def main() -> None:
    default_base, default_staging = resolve_default_paths()
    immich_url_default, immich_key_default, immich_album_default = load_immich_env()

    parser = argparse.ArgumentParser(
        description="Recursively stage event media into flat folders for DaVinci Resolve, DxO PhotoLab, and editors."
    )
    parser.add_argument(
        "--immich-album",
        "-i",
        dest="immich_album",
        nargs="?",
        const=immich_album_default or "__PROMPT__",
        help="Fetch event dates directly from an Immich album name or UUID (e.g. 'Stampf' or '86e11802...').",
    )
    parser.add_argument(
        "--immich-url",
        default=immich_url_default,
        help=f"Immich server base URL (default: {immich_url_default})",
    )
    parser.add_argument(
        "--immich-key",
        default=immich_key_default,
        help="Immich API Key (defaults to IMMICH_API_KEY from environment or .env)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing staged links in staging folders before staging.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force clean even if single-link files (nlink=1) are detected in staging folders.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open staging folders in default file manager after staging.",
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
        "--link-type",
        choices=["hardlink", "symlink", "copy"],
        default="hardlink",
        help="Link creation strategy (default: hardlink for cross-platform Win11 & Linux compatibility).",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Preview actions without modifying the filesystem.",
    )
    parser.add_argument(
        "--dates",
        nargs="+",
        default=None,
        help="Custom list of dates (YYYY-MM-DD) to stage (overrides default dates).",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=default_staging,
        help=f"Target staging directory (default: {default_staging})",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=default_base,
        help=f"Photos base directory (default: {default_base})",
    )

    args = parser.parse_args()

    album_display_name = None
    target_dates = args.dates

    if args.immich_album:
        target_ref = args.immich_album
        if target_ref == "__PROMPT__":
            target_ref = input("Enter Immich album name or UUID: ").strip()

        if not target_ref:
            print("Error: No Immich album specified.")
            sys.exit(1)

        print(f"Connecting to Immich at {args.immich_url} to fetch dates for album: '{target_ref}'...")
        try:
            album_display_name, fetched_dates = fetch_immich_album_dates(
                target_ref, base_url=args.immich_url, api_key=args.immich_key
            )
            if not fetched_dates:
                print(f"⚠️  Warning: No capture dates found in Immich album '{album_display_name}'.")
                sys.exit(1)
            print(f"✓ Found {len(fetched_dates)} event date(s) in Immich album '{album_display_name}':")
            for d in fetched_dates:
                print(f"   • {d}")
            target_dates = fetched_dates
        except Exception as e:
            print(f"❌ Error fetching dates from Immich: {e}")
            if not target_dates:
                print(f"Falling back to default dates ({len(DEFAULT_DATES)} dates).")
                target_dates = DEFAULT_DATES

    if not target_dates:
        target_dates = DEFAULT_DATES

    if args.clean:
        print("\nCleaning staging directories...")
        validate_staging_safety(args.base_dir, args.staging_dir)
        r_photos = clean_staging_directory(
            args.staging_dir / "photos_raw", dry_run=args.dry_run, force=args.force
        )
        r_videos = clean_staging_directory(
            args.staging_dir / "videos", dry_run=args.dry_run, force=args.force
        )
        clean_staging_directory(args.staging_dir, dry_run=args.dry_run, force=args.force)
        prefix = "[Dry-Run] Would remove" if args.dry_run else "Removed"
        print(f"{prefix} {r_photos} photos links and {r_videos} videos links.\n")

    stage_media(
        base_dir=args.base_dir,
        staging_dir=args.staging_dir,
        dates=target_dates,
        include_jpg=args.include_jpg,
        mode=args.mode,
        link_type=args.link_type,
        dry_run=args.dry_run,
        album_name=album_display_name,
    )

    if args.open and not args.dry_run:
        open_staging_folders(args.staging_dir, args.mode)


if __name__ == "__main__":
    main()
