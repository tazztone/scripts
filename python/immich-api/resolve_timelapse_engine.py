#!/usr/bin/env python3
"""
DaVinci Resolve Automated Timelapse & Hyperlapse Sequence Engine

Mathematically detects true timelapse / hyperlapse image sequences in staged photos
using EXIF capture interval regularity (Delta t clustering and low Coefficient of Variation),
stages them via zero-copy hardlinks into clean per-sequence directories (frame_%04d.dng),
and imports them into DaVinci Resolve Studio as native CinemaDNG Image Sequences
(1 frame per photo @ 25fps) with strict aspect-ratio & orientation segregation
(Landscape 4:3 4032x3024 vs Vertical 3:4 3024x4032), Color Page Camera RAW controls,
and starting grade annotations.

Why CinemaDNG / DNG?
---------------------
DaVinci Resolve's image sequence engine natively supports CinemaDNG (.dng), TIFF, EXR, DPX,
and JPEG/PNG sequences. Proprietary camera RAW formats (Sony .ARW, Panasonic .RW2, Nikon .NEF,
Canon .CR3) cannot be imported as NLE image sequences directly by Resolve and are treated as
individual still photos. By targeting .DNG sequences, Resolve unlocks full GPU-accelerated
debayering and direct control over White Balance, Tint, Exposure, and Highlight Recovery
in the Color Page Camera RAW palette.
"""

import argparse
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Default directory locations
DEFAULT_STAGING_DIR = Path("/mnt/wd14tb/_RESOLVE_IMPORT_STAGING/photos_raw")
DEFAULT_OUTPUT_DIR = Path("/mnt/wd14tb/_RESOLVE_IMPORT_STAGING/timelapses")
CACHE_FILENAME = ".exif_timelapse_cache.json"


@dataclass
class PhotoMetadata:
    filename: str
    file_path: Path
    model: str
    make: str
    dt: datetime
    subsec: str
    width: int
    height: int
    flavor: str  # "original", "enhanced_nr", "hdr", etc.
    event_prefix: str
    subfolder_prefix: str
    orientation: str
    is_vertical: bool


@dataclass
class TimelapseCluster:
    cluster_id: str
    sequence_name: str
    sequence_type: str  # "Hyperlapse", "PanoSpin", "Timelapse"
    camera_model: str
    width: int
    height: int
    flavor: str
    is_vertical: bool
    frames: List[PhotoMetadata]
    mean_interval: float
    min_interval: float
    max_interval: float
    cv_interval: float
    total_duration_sec: float


# --- DaVinci Resolve Scripting Environment Setup ---


def setup_resolve_scripting_env() -> None:
    """Configures sys.path to locate DaVinciResolveScript across Linux, Windows, and macOS."""
    system = platform.system()
    if system == "Windows":
        prog_data = os.getenv("PROGRAMDATA", r"C:\ProgramData")
        win_path = os.path.join(
            prog_data, r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
        )
        if os.path.isdir(win_path) and win_path not in sys.path:
            sys.path.append(win_path)
    elif system == "Darwin":
        mac_path = (
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
        )
        if os.path.isdir(mac_path) and mac_path not in sys.path:
            sys.path.append(mac_path)
    else:  # Linux
        for l_path in [
            "/opt/resolve/Developer/Scripting/Modules",
            "/home/resolve/Developer/Scripting/Modules",
        ]:
            if os.path.isdir(l_path) and l_path not in sys.path:
                sys.path.append(l_path)


def connect_to_resolve() -> Any:
    """Connects to active DaVinci Resolve Studio application instance."""
    setup_resolve_scripting_env()
    try:
        import DaVinciResolveScript as dvr_script  # type: ignore[import-not-found]

        resolve = dvr_script.scriptapp("Resolve")
        return resolve
    except ImportError:
        return None
    except Exception:
        return None


# --- EXIF Batch Extraction & Caching ---


def get_cache_file_path(staging_dir: Path) -> Path:
    """Returns local cache path for EXIF metadata."""
    local_dir = Path(__file__).parent
    return local_dir / CACHE_FILENAME


def load_or_extract_exif(
    staging_dir: Path, clear_cache: bool = False
) -> List[Dict[str, Any]]:
    """
    Extracts EXIF metadata in fast parallel batch using exiftool, with automatic
    mtime/count caching to ensure sub-second re-runs.
    """
    cache_path = get_cache_file_path(staging_dir)

    # Gather all DNG files
    dng_files = sorted(
        [
            p
            for p in staging_dir.iterdir()
            if p.is_file() and p.suffix.lower() == ".dng"
        ]
    )

    if not dng_files:
        return []

    dir_stat = staging_dir.stat()
    cache_key = {
        "staging_dir": str(staging_dir.resolve()),
        "file_count": len(dng_files),
        "dir_mtime": dir_stat.st_mtime,
        "schema_version": 2,  # Version 2 includes -Orientation
    }

    if not clear_cache and cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            if cached_data.get("key") == cache_key and "records" in cached_data:
                return cached_data["records"]
        except Exception:
            pass

    print(f"Extracting EXIF metadata from {len(dng_files)} DNG photos via exiftool...")
    start_t = time.time()
    cmd = [
        "exiftool",
        "-json",
        "-FileName",
        "-Model",
        "-Make",
        "-DateTimeOriginal",
        "-SubSecTimeOriginal",
        "-ImageSize",
        "-Orientation",
        str(staging_dir),
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw_records = json.loads(res.stdout)
    except Exception as e:
        print(f"Error running exiftool: {e}")
        return []

    elapsed = time.time() - start_t
    print(f"✓ Extracted EXIF data in {elapsed:.2f}s ({len(raw_records)/max(elapsed, 0.001):.1f} files/s)")

    # Save to cache
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"key": cache_key, "records": raw_records}, f, indent=2)
    except Exception:
        pass

    return raw_records


def parse_photo_metadata(
    raw_records: List[Dict[str, Any]], staging_dir: Path
) -> List[PhotoMetadata]:
    """Parses raw exiftool records into structured PhotoMetadata instances with orientation detection."""
    items: List[PhotoMetadata] = []

    for rec in raw_records:
        fn = rec.get("FileName", "")
        if not fn.lower().endswith(".dng"):
            continue

        dt_str = rec.get("DateTimeOriginal")
        if not dt_str:
            continue

        try:
            dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        except Exception:
            continue

        subsec = str(rec.get("SubSecTimeOriginal") or "0")
        model = rec.get("Model") or rec.get("Make") or "Unknown_Camera"
        make = rec.get("Make") or ""

        # Parse width / height from ImageSize e.g. "4032x3024"
        img_size = rec.get("ImageSize", "0x0")
        if "x" in img_size:
            parts = img_size.split("x")
            width, height = int(parts[0]), int(parts[1])
        else:
            width, height = 0, 0

        # Staged naming format: <EventFolder>__<Subdir(if any)>__<Filename>
        staged_parts = fn.split("__")
        event_prefix = staged_parts[0] if len(staged_parts) > 1 else "misc"
        subfolder_prefix = staged_parts[1] if len(staged_parts) > 2 else ""

        # Check Orientation (e.g. "Rotate 270 CW", "Rotate 90 CW", or portrait naming)
        orientation = str(rec.get("Orientation") or "Horizontal (normal)")
        fn_lower = fn.lower()
        sub_lower = subfolder_prefix.lower()

        is_vertical = (
            "90" in orientation
            or "270" in orientation
            or "portrait" in fn_lower
            or "vertical" in fn_lower
            or "portrait" in sub_lower
            or "vertical" in sub_lower
        )

        # If vertical/portrait, swap width and height so pixel canvas matches display aspect ratio
        if is_vertical and width > height:
            width, height = height, width

        # Determine derivative flavor: separate edited/enhanced versions from base captures
        if "enhanced-nr" in fn_lower or "-enhanced" in fn_lower or "_enhanced" in fn_lower:
            flavor = "enhanced_nr"
        elif "-hdr" in fn_lower or "_hdr" in fn_lower:
            flavor = "hdr"
        else:
            flavor = "original"

        items.append(
            PhotoMetadata(
                filename=fn,
                file_path=staging_dir / fn,
                model=model,
                make=make,
                dt=dt,
                subsec=subsec,
                width=width,
                height=height,
                flavor=flavor,
                event_prefix=event_prefix,
                subfolder_prefix=subfolder_prefix,
                orientation=orientation,
                is_vertical=is_vertical,
            )
        )

    return items


# --- Mathematical Sequence Detection Engine ---


def detect_timelapse_clusters(
    photos: List[PhotoMetadata],
    min_frames: int = 5,
    min_interval: float = 0.5,
    max_interval: float = 60.0,
    max_cv: float = 0.25,
    min_span: float = 5.0,
) -> List[TimelapseCluster]:
    """
    Groups photos by Camera + Event + Staged Subfolder + Flavor + Orientation,
    clusters consecutive frames within the target interval delta, and validates cadence regularity.
    """
    # 1. Group by (Model, Event, Subfolder, Flavor, is_vertical) to strictly segregate orientations
    buckets: Dict[str, List[PhotoMetadata]] = {}
    for p in photos:
        key = f"{p.model}__{p.event_prefix}__{p.subfolder_prefix}__{p.flavor}__vert_{p.is_vertical}"
        buckets.setdefault(key, []).append(p)

    clusters: List[TimelapseCluster] = []
    cluster_idx = 1

    for group_key, group_photos in sorted(buckets.items()):
        # Sort chronologically by capture timestamp
        group_photos.sort(key=lambda x: (x.dt, x.subsec, x.filename))

        current_cluster: List[PhotoMetadata] = []

        for i in range(len(group_photos)):
            if not current_cluster:
                current_cluster.append(group_photos[i])
                continue

            prev = current_cluster[-1]
            curr = group_photos[i]
            delta = (curr.dt - prev.dt).total_seconds()

            if min_interval <= delta <= max_interval:
                current_cluster.append(curr)
            else:
                # Evaluate and finalize current cluster
                cluster = _evaluate_cluster(
                    current_cluster,
                    cluster_idx,
                    min_frames,
                    max_cv,
                    min_span,
                )
                if cluster:
                    clusters.append(cluster)
                    cluster_idx += 1
                current_cluster = [curr]

        # Evaluate tail cluster
        if current_cluster:
            cluster = _evaluate_cluster(
                current_cluster,
                cluster_idx,
                min_frames,
                max_cv,
                min_span,
            )
            if cluster:
                clusters.append(cluster)
                cluster_idx += 1

    return clusters


def _evaluate_cluster(
    cluster_photos: List[PhotoMetadata],
    cluster_idx: int,
    min_frames: int,
    max_cv: float,
    min_span: float,
) -> Optional[TimelapseCluster]:
    """Validates cluster size, duration span, and interval coefficient of variation."""
    if len(cluster_photos) < min_frames:
        return None

    first = cluster_photos[0]
    last = cluster_photos[-1]
    total_dur = (last.dt - first.dt).total_seconds()

    # Minimum duration span (prevents 0-second single-burst AEB brackets)
    if total_dur < min_span:
        return None

    # Calculate intervals between consecutive frames
    gaps: List[float] = []
    for i in range(len(cluster_photos) - 1):
        gap = (cluster_photos[i + 1].dt - cluster_photos[i].dt).total_seconds()
        gaps.append(gap)

    if not gaps or sum(gaps) == 0:
        return None

    mean_gap = statistics.mean(gaps)
    std_gap = statistics.stdev(gaps) if len(gaps) > 1 else 0.0
    cv = (std_gap / mean_gap) if mean_gap > 0 else 0.0

    # Strict regularity check
    if cv > max_cv and len(gaps) > 2:
        return None

    # Identify Sequence Type
    name_check = f"{first.event_prefix}_{first.subfolder_prefix}_{first.filename}".lower()
    if "pano" in name_check or "360" in name_check:
        seq_type = "PanoSpin"
    elif "hyperlapse" in name_check or "hl" in name_check or "portrait" in name_check:
        seq_type = "Hyperlapse"
    else:
        seq_type = "Timelapse"

    # Construct clean, unique sequence folder name
    # Format: <Event>_<SubdirOrTime>_<Type>_<Orientation>_<Flavor>
    time_str = first.dt.strftime("%H%M%S")
    clean_sub = first.subfolder_prefix.replace(" ", "_").replace("__", "_").strip("_")
    sub_tag = clean_sub if clean_sub else time_str

    orient_tag = "_Vertical" if first.is_vertical else ""
    flavor_tag = "" if first.flavor == "original" else f"_{first.flavor}"
    seq_name = f"{first.event_prefix}_{sub_tag}_{seq_type}{orient_tag}{flavor_tag}".strip("_").replace("__", "_")

    return TimelapseCluster(
        cluster_id=f"SEQ_{cluster_idx:03d}",
        sequence_name=seq_name,
        sequence_type=seq_type,
        camera_model=first.model,
        width=first.width,
        height=first.height,
        flavor=first.flavor,
        is_vertical=first.is_vertical,
        frames=cluster_photos,
        mean_interval=round(mean_gap, 2),
        min_interval=round(min(gaps), 2),
        max_interval=round(max(gaps), 2),
        cv_interval=round(cv, 3),
        total_duration_sec=round(total_dur, 1),
    )


# --- Zero-Copy Staging Engine ---


def stage_timelapse_hardlinks(
    clusters: List[TimelapseCluster],
    output_base_dir: Path,
    dry_run: bool = False,
) -> List[Tuple[TimelapseCluster, Path]]:
    """
    Creates clean, isolated sequence folders with sequentially numbered frames
    (frame_0001.dng ... frame_NNNN.dng) using zero-copy hardlinks.
    """
    staged_results: List[Tuple[TimelapseCluster, Path]] = []

    if not dry_run:
        output_base_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nStaging {len(clusters)} timelapse sequence(s) into '{output_base_dir}'...")

    total_links_created = 0

    for cluster in clusters:
        seq_dir = output_base_dir / cluster.sequence_name
        if not dry_run:
            seq_dir.mkdir(parents=True, exist_ok=True)

        orient_desc = "Vertical 3:4" if cluster.is_vertical else "Landscape 4:3"
        print(f"📁 Staging [{cluster.cluster_id}] {cluster.sequence_name} ({len(cluster.frames)} frames, {orient_desc})")

        for idx, photo in enumerate(cluster.frames, start=1):
            dst_frame = seq_dir / f"frame_{idx:04d}.dng"

            if dry_run:
                continue

            if dst_frame.exists():
                try:
                    if dst_frame.samefile(photo.file_path):
                        continue
                    dst_frame.unlink()
                except Exception:
                    pass

            try:
                os.link(photo.file_path, dst_frame)
                total_links_created += 1
            except OSError as e:
                # Fallback to symlink if cross-filesystem
                if getattr(e, "errno", None) == 18:
                    try:
                        dst_frame.symlink_to(photo.file_path)
                        total_links_created += 1
                    except Exception as sym_err:
                        print(f"  ❌ Symlink fallback failed for {dst_frame.name}: {sym_err}")
                else:
                    print(f"  ❌ Failed to link {photo.filename} -> {dst_frame.name}: {e}")

        staged_results.append((cluster, seq_dir))

    if not dry_run:
        print(f"✓ Successfully staged {total_links_created} frames with zero storage duplication.")

    return staged_results


# --- Display Summary Table ---


def print_timelapse_summary_table(clusters: List[TimelapseCluster], output_dir: Path) -> None:
    """Prints a clear breakdown table of all mathematically detected timelapse sequences."""
    print("\n" + "=" * 125)
    print(
        f"{'ID':<8} {'Sequence Name':<42} {'Type':<12} {'Orientation':<12} {'Resolution':<12} {'Frames':<8} {'Interval':<12} {'Duration'}"
    )
    print("=" * 125)

    total_frames = 0
    for c in clusters:
        total_frames += len(c.frames)
        orient_str = "Vertical" if c.is_vertical else "Landscape"
        res_str = f"{c.width}x{c.height}"
        interval_str = f"{c.mean_interval}s (CV:{c.cv_interval})"
        dur_str = f"{c.total_duration_sec}s"
        print(
            f"{c.cluster_id:<8} {c.sequence_name:<42} {c.sequence_type:<12} {orient_str:<12} {res_str:<12} {len(c.frames):<8} {interval_str:<12} {dur_str}"
        )

    print("=" * 125)
    print(
        f"Total Detected Sequences: {len(clusters)} ({total_frames} total DNG frames)"
    )
    print(f"Staging Destination:      {output_dir}")
    print("=" * 125)


# --- DaVinci Resolve Studio Automation ---


def import_and_organize_in_resolve(
    staged_results: List[Tuple[TimelapseCluster, Path]],
    fps: float = 25.0,
    create_timelines: bool = True,
    individual_timelines: bool = False,
    switch_color_page: bool = True,
) -> bool:
    """
    Connects to DaVinci Resolve Studio, creates dedicated Media Pool Bins
    (strictly separating Landscape 4:3 vs Vertical 3:4), imports CinemaDNG clips,
    assigns Blue clip color, adds Frame 0 Camera RAW markers, and generates native-canvas timelines.
    """
    resolve = connect_to_resolve()
    if not resolve:
        print("\n❌ Could not connect to DaVinci Resolve.")
        print("Please ensure DaVinci Resolve Studio is open with an active project.")
        return False

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    if not project:
        print("\n❌ No active project is open in DaVinci Resolve. Please open or create a project.")
        return False

    print(f"\n✓ Connected to DaVinci Resolve Project: '{project.GetName()}'")
    media_pool = project.GetMediaPool()
    root_folder = media_pool.GetRootFolder()

    # Collect existing timelines
    existing_tl_count = project.GetTimelineCount()
    existing_tl_names = set()
    for i in range(1, existing_tl_count + 1):
        tl = project.GetTimelineByIndex(i)
        if tl:
            existing_tl_names.add(tl.GetName())

    # Create Master Staging Bin: Staged_Clips_By_Camera
    staging_master_folder = None
    for sub in root_folder.GetSubFolderList():
        if sub.GetName() == "Staged_Clips_By_Camera":
            staging_master_folder = sub
            break
    if not staging_master_folder:
        staging_master_folder = media_pool.AddSubFolder(root_folder, "Staged_Clips_By_Camera")

    # Group sequences by strict geometry & orientation (Landscape vs Vertical)
    bin_groups: Dict[str, List[Tuple[TimelapseCluster, Path]]] = {}
    for cluster, seq_dir in staged_results:
        orient_label = "Vertical" if cluster.is_vertical else "Landscape"
        bin_name = f"Timelapse_CinemaDNG_{orient_label}_{cluster.width}x{cluster.height}_{int(fps)}fps"
        bin_groups.setdefault(bin_name, []).append((cluster, seq_dir))

    for bin_name, items in sorted(bin_groups.items()):
        print(f"\n📁 Processing Media Pool Bin: {bin_name} ({len(items)} sequence(s))")

        # Find or create subfolder
        target_folder = None
        for sub in staging_master_folder.GetSubFolderList():
            if sub.GetName() == bin_name:
                target_folder = sub
                break
        if not target_folder:
            target_folder = media_pool.AddSubFolder(staging_master_folder, bin_name)

        media_pool.SetCurrentFolder(target_folder)

        # Collect all imported clips for this resolution bucket
        all_bin_clips = []
        first_cluster = items[0][0]
        existing_clips = target_folder.GetClipList() or []

        for cluster, seq_dir in items:
            frame_files = sorted([str(p) for p in seq_dir.iterdir() if p.suffix.lower() == ".dng"])
            if not frame_files:
                continue

            first_frame_path = frame_files[0]
            first_frame_name = Path(first_frame_path).name

            # Check if sequence is already imported
            matching_clip = None
            for c in existing_clips:
                c_name = c.GetName()
                if "frame_" in c_name or c_name == first_frame_name or cluster.sequence_name in c_name:
                    matching_clip = c
                    break

            if not matching_clip:
                # Import sequence by passing the frame list
                print(f"   -> Importing CinemaDNG Sequence: '{cluster.sequence_name}' ({len(frame_files)} frames)...")
                new_clips = media_pool.ImportMedia(frame_files) or []
                if new_clips:
                    matching_clip = new_clips[0]
                    # Rename clip to descriptive sequence name in Media Pool
                    try:
                        matching_clip.SetClipProperty("Clip Name", cluster.sequence_name)
                    except Exception:
                        pass
            else:
                print(f"   -> Sequence '{cluster.sequence_name}' already imported (reusing clip).")

            if not matching_clip:
                continue

            all_bin_clips.append(matching_clip)

            # Assign Blue Clip Color & Frame 0 Camera RAW Marker
            try:
                matching_clip.SetClipColor("Blue")
            except Exception:
                pass

            orient_desc = "Vertical (3:4)" if cluster.is_vertical else "Landscape (4:3)"
            starting_grade_note = (
                f"[CinemaDNG Photographic Starting Grade]\n"
                f"Sequence: {cluster.sequence_name}\n"
                f"Frames: {len(cluster.frames)} frames @ {fps}fps\n"
                f"Format: {cluster.width}x{cluster.height} ({orient_desc})\n"
                f"Camera: {cluster.camera_model}\n"
                f"Cadence: {cluster.mean_interval}s interval ({cluster.sequence_type})\n"
                f"Color Settings: Color Page -> Camera RAW palette (bottom-left):\n"
                f"  • Decode Using: Clip\n"
                f"  • Color Space: sRGB (or Rec.709)\n"
                f"  • Gamma: sRGB (or Gamma 2.2)\n"
                f"  • White Balance: As Shot (or adjust Temp/Tint)\n"
                f"  • Highlight Recovery: On (restores sky highlights)\n"
                f"Optional CST Node:\n"
                f"  • Input: sRGB / sRGB -> Output: Rec.709 / Gamma 2.4"
            )

            try:
                matching_clip.AddMarker(
                    0,
                    "Cyan",
                    "CinemaDNG Starting Grade",
                    starting_grade_note,
                    1,
                )
            except Exception:
                pass

            # Optional individual timeline per sequence
            if individual_timelines:
                tl_name = f"TL - {cluster.sequence_type} {cluster.sequence_name} ({cluster.width}x{cluster.height} {int(fps)}fps)"
                if tl_name in existing_tl_names:
                    print(f"   -> Timeline '{tl_name}' already exists (skipping).")
                else:
                    print(f"   -> Creating Native Timeline: '{tl_name}'...")
                    try:
                        timeline = media_pool.CreateTimelineFromClips(tl_name, [matching_clip])
                        if timeline:
                            timeline.SetSetting("useCustomSettings", "1")
                            timeline.SetSetting("timelineResolutionWidth", str(cluster.width))
                            timeline.SetSetting("timelineResolutionHeight", str(cluster.height))
                            timeline.SetSetting("timelineFrameRate", str(int(fps)))
                            print(f"      ✓ Timeline created ({cluster.width}x{cluster.height} @ {int(fps)}fps).")
                            existing_tl_names.add(tl_name)
                    except Exception as tl_err:
                        print(f"      ⚠️ Timeline creation error: {tl_err}")

        # Create Master Consolidated Timeline containing all clips in this resolution & orientation bucket
        if create_timelines and all_bin_clips:
            orient_label = "Vertical" if first_cluster.is_vertical else "Landscape"
            master_tl_name = f"TL - All Timelapses ({orient_label} {first_cluster.width}x{first_cluster.height} {int(fps)}fps)"
            if master_tl_name in existing_tl_names:
                print(f"   -> Master Timeline '{master_tl_name}' already exists (skipping).")
            else:
                print(f"\n   -> 🎬 Creating Consolidated Master Timeline: '{master_tl_name}' ({len(all_bin_clips)} clips)...")
                try:
                    timeline = media_pool.CreateTimelineFromClips(master_tl_name, all_bin_clips)
                    if timeline:
                        timeline.SetSetting("useCustomSettings", "1")
                        timeline.SetSetting("timelineResolutionWidth", str(first_cluster.width))
                        timeline.SetSetting("timelineResolutionHeight", str(first_cluster.height))
                        timeline.SetSetting("timelineFrameRate", str(int(fps)))
                        print(f"      ✓ Master Timeline created with {len(all_bin_clips)} {orient_label} timelapses ({first_cluster.width}x{first_cluster.height} @ {int(fps)}fps).")
                        existing_tl_names.add(master_tl_name)
                except Exception as tl_err:
                    print(f"      ⚠️ Master Timeline creation error: {tl_err}")

    # Switch to Color Page
    if switch_color_page:
        try:
            resolve.OpenPage("color")
            print("\n🎨 Switched DaVinci Resolve to Color Page.")
        except Exception:
            pass

    print("\n" + "=" * 65)
    print("✓ DaVinci Resolve Timelapse Ingestion & Prep Complete!")
    print("=" * 65)
    return True


# --- Main CLI Entrypoint ---


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated EXIF-driven Timelapse & Hyperlapse Sequence Detection, Staging, and DaVinci Resolve Importer."
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=DEFAULT_STAGING_DIR,
        help=f"Directory containing staged photos (default: {DEFAULT_STAGING_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to output clean sequence folders (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Scan and display detected timelapse clusters without modifying filesystem or DaVinci Resolve.",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Force re-extraction of EXIF metadata and rebuild the cache file.",
    )
    parser.add_argument(
        "--min-frames",
        type=int,
        default=5,
        help="Minimum number of consecutive frames required to form a timelapse sequence (default: 5).",
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=0.5,
        help="Minimum interval in seconds between consecutive shots (default: 0.5s).",
    )
    parser.add_argument(
        "--max-interval",
        type=float,
        default=60.0,
        help="Maximum interval in seconds between consecutive shots (default: 60.0s).",
    )
    parser.add_argument(
        "--max-cv",
        type=float,
        default=0.25,
        help="Maximum Coefficient of Variation (std_dev / mean) for cadence regularity (default: 0.25).",
    )
    parser.add_argument(
        "--min-span",
        type=float,
        default=5.0,
        help="Minimum total capture duration in seconds (default: 5.0s).",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=25.0,
        help="Target framerate for image sequences and timelines (default: 25.0 fps).",
    )
    parser.add_argument(
        "--no-timelines",
        action="store_true",
        help="Stage and import to Media Pool only; skip timeline creation.",
    )
    parser.add_argument(
        "--individual-timelines",
        action="store_true",
        help="Create separate individual timelines for each timelapse in addition to the consolidated master timeline.",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Simulate staging operations without creating hardlinks on disk.",
    )

    args = parser.parse_args()

    if not args.staging_dir.exists():
        print(f"Error: Staging directory not found: {args.staging_dir}")
        sys.exit(1)

    print("=" * 65)
    print(" DaVinci Resolve Timelapse & Hyperlapse Sequence Engine")
    print("=" * 65)
    print(f"Source Directory:     {args.staging_dir}")
    print(f"Output Directory:     {args.output_dir}")
    print(f"Interval Window:      [{args.min_interval}s .. {args.max_interval}s]")
    print(f"Min Frames Threshold: {args.min_frames} frames (Min Span: {args.min_span}s)")
    print(f"Max Cadence CV:       {args.max_cv}")
    print(f"Target Frame Rate:    {args.fps} fps")
    print(f"Scan Only Mode:       {args.scan_only}")
    print("-" * 65)

    # 1. Load EXIF metadata
    raw_records = load_or_extract_exif(args.staging_dir, clear_cache=args.clear_cache)
    if not raw_records:
        print("No DNG photo records found in the specified directory.")
        sys.exit(0)

    # 2. Parse into structured PhotoMetadata with Orientation detection
    photos = parse_photo_metadata(raw_records, args.staging_dir)
    print(f"✓ Parsed {len(photos)} DNG photo records from metadata.")

    # 3. Detect mathematically regular sequence clusters
    clusters = detect_timelapse_clusters(
        photos,
        min_frames=args.min_frames,
        min_interval=args.min_interval,
        max_interval=args.max_interval,
        max_cv=args.max_cv,
        min_span=args.min_span,
    )

    if not clusters:
        print("No timelapse sequences met the regularity and frame count criteria.")
        sys.exit(0)

    print_timelapse_summary_table(clusters, args.output_dir)

    if args.scan_only:
        print("\n[SCAN ONLY] Completed inspection. Re-run without --scan-only to stage and import into DaVinci Resolve.")
        sys.exit(0)

    # 4. Zero-copy staging into clean sequence directories
    staged_results = stage_timelapse_hardlinks(
        clusters,
        args.output_dir,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("\n[DRY RUN] Staging simulation complete.")
        sys.exit(0)

    # 5. DaVinci Resolve Automation
    import_and_organize_in_resolve(
        staged_results,
        fps=args.fps,
        create_timelines=not args.no_timelines,
        individual_timelines=args.individual_timelines,
    )


if __name__ == "__main__":
    main()
