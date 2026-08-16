#!/usr/bin/env python3
"""
DaVinci Resolve Automated Media Organizer & Color Grading Prep Tool

Connects to DaVinci Resolve Studio (or runs standalone in --scan-only mode),
probes video files using a 3-tier deep metadata engine (container EXIF/ffprobe tags,
stream properties, and codec signatures), organizes clips into structured Media Pool Bins,
assigns distinct Clip Colors per camera, adds Color Space Transform (CST) starting grade
marker annotations, and auto-generates dedicated Timelines with STRICT resolution & framerate matching.
"""

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Default staging directory
DEFAULT_STAGING_DIR = Path("/mnt/wd14tb/_RESOLVE_IMPORT_STAGING/videos")

# Clip color palette mapping for Resolve Color Page
CAMERA_COLOR_PALETTE = {
    "Panasonic": "Yellow",
    "DJI": "Orange",
    "Sony": "Teal",
    "GoPro": "Green",
    "Mobile": "Purple",
    "Timelapse": "Blue",
    "Render": "Navy",
    "Other": "Olive",
}


def setup_resolve_scripting_env() -> None:
    """Configures sys.path to locate DaVinciResolveScript across Linux, Windows, and macOS."""
    system = platform.system()
    if system == "Windows":
        prog_data = os.getenv("PROGRAMDATA", r"C:\ProgramData")
        win_path = os.path.join(prog_data, r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules")
        if os.path.isdir(win_path) and win_path not in sys.path:
            sys.path.append(win_path)
    elif system == "Darwin":
        mac_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
        if os.path.isdir(mac_path) and mac_path not in sys.path:
            sys.path.append(mac_path)
    else:  # Linux
        for l_path in ["/opt/resolve/Developer/Scripting/Modules", "/home/resolve/Developer/Scripting/Modules"]:
            if os.path.isdir(l_path) and l_path not in sys.path:
                sys.path.append(l_path)


def connect_to_resolve() -> Any:
    """Connects to active DaVinci Resolve application instance."""
    setup_resolve_scripting_env()
    try:
        import DaVinciResolveScript as dvr_script  # type: ignore[import-not-found]
        resolve = dvr_script.scriptapp("Resolve")
        return resolve
    except ImportError:
        return None
    except Exception:
        return None


def probe_file_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Tier 1 Deep Probe: Extracts container atoms, hardware tags, stream properties,
    and color transfer characteristics using ffprobe.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        data = json.loads(res.stdout)
    except Exception:
        data = {}

    format_info = data.get("format", {})
    format_tags = format_info.get("tags", {})
    streams = data.get("streams", [])

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    video_tags = video_stream.get("tags", {})

    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    codec = video_stream.get("codec_name") or "unknown"
    pix_fmt = video_stream.get("pix_fmt") or ""
    bit_depth = 10 if "10" in pix_fmt or "p10" in pix_fmt or video_stream.get("bits_per_raw_sample") == "10" else 8

    # Frame rate calculation
    r_frame_rate = video_stream.get("r_frame_rate", "0/0")
    fps = 0.0
    if "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        if float(den) > 0:
            fps = round(float(num) / float(den), 2)
    elif r_frame_rate:
        try:
            fps = round(float(r_frame_rate), 2)
        except ValueError:
            pass

    # Hardware & manufacturer tags
    make = format_tags.get("make") or format_tags.get("Make") or video_tags.get("make") or ""
    model = format_tags.get("model") or format_tags.get("Model") or video_tags.get("model") or ""
    handler = format_tags.get("handler_name") or video_tags.get("handler_name") or ""
    major_brand = format_tags.get("major_brand") or ""
    compatible_brands = format_tags.get("compatible_brands") or ""
    comment = format_tags.get("comment") or video_tags.get("comment") or ""
    encoder = format_tags.get("encoder") or video_tags.get("encoder") or ""

    # Color space & transfer characteristics
    color_space = video_stream.get("color_space") or ""
    color_transfer = video_stream.get("color_transfer") or ""
    color_primaries = video_stream.get("color_primaries") or ""

    return {
        "file_path": file_path,
        "filename": file_path.name,
        "width": width,
        "height": height,
        "fps": fps,
        "codec": codec,
        "pix_fmt": pix_fmt,
        "bit_depth": bit_depth,
        "make": make,
        "model": model,
        "handler": handler,
        "major_brand": major_brand,
        "compatible_brands": compatible_brands,
        "comment": comment,
        "encoder": encoder,
        "color_space": color_space,
        "color_transfer": color_transfer,
        "color_primaries": color_primaries,
    }


def get_strict_resolution_label(width: int, height: int) -> str:
    """
    Returns strict, exact resolution labels to prevent mixing 16:9, 4:3, 5.4K, 4K, 1080p, or vertical videos.
    """
    if width == 0 or height == 0:
        return "Unknown_Res"

    # Vertical / Portrait Video
    if height > width:
        if width == 1080 and height == 1920:
            return "Vertical_1080x1920"
        elif width == 2160 and height == 3840:
            return "Vertical_2160x3840"
        else:
            return f"Vertical_{width}x{height}"

    # Strict Landscape Resolutions
    if width == 5464 and height == 3070:
        return "5.4K_5464x3070"
    elif width == 4096 and height == 2160:
        return "DCI_4K_4096x2160"
    elif width == 3840 and height == 2160:
        return "4K_UHD_3840x2160"
    elif width == 2720 and height == 1530:
        return "2.7K_2720x1530"
    elif width == 1920 and height == 1080:
        return "1080p_FHD"
    elif width == 1280 and height == 720:
        return "720p_HD"
    else:
        # Photo sensor ratios (e.g. 4:3 timelapses 4032x3024, 4000x3000)
        ratio = round(width / height, 2)
        if ratio == 1.33:
            return f"Photo_4x3_{width}x{height}"
        elif ratio == 1.78:
            return f"16x9_{width}x{height}"
        else:
            return f"{width}x{height}"


def get_normalized_fps_label(fps: float) -> str:
    """Normalizes minor mobile VFR jitter while strictly segregating deliberate framerates."""
    if fps <= 0:
        return ""
    if abs(fps - 23.976) < 0.2 or abs(fps - 24.0) < 0.2:
        return "24fps"
    elif abs(fps - 25.0) < 0.2:
        return "25fps"
    elif abs(fps - 29.97) < 0.5 or abs(fps - 30.0) < 0.5:
        return "30fps"
    elif abs(fps - 50.0) < 0.5:
        return "50fps_SlowMo"
    elif abs(fps - 59.94) < 0.5 or abs(fps - 60.0) < 0.5:
        return "60fps_SlowMo"
    elif abs(fps - 100.0) < 0.5:
        return "100fps_SlowMo"
    elif abs(fps - 119.88) < 0.5 or abs(fps - 120.0) < 0.5:
        return "120fps_SlowMo"
    elif abs(fps - 240.0) < 1.0:
        return "240fps_SlowMo"
    else:
        return f"{int(round(fps))}fps"


def classify_media_clip(meta: Dict[str, Any]) -> Dict[str, str]:
    """
    3-Tier Classification Engine:
    Determines Camera Brand, Model, Strict Resolution, Framerate Bucket, Suggested Color Profile,
    Clip Color, Target Bin Name, and CST starting grade notes.
    """
    filename = meta["filename"]
    make = meta.get("make", "").lower()
    model = meta.get("model", "").lower()
    handler = meta.get("handler", "").lower()
    brand = meta.get("major_brand", "")
    comment = meta.get("comment", "")
    width = meta.get("width", 0)
    height = meta.get("height", 0)
    fps = meta.get("fps", 0.0)
    bit_depth = meta.get("bit_depth", 8)
    color_transfer = meta.get("color_transfer", "").lower()

    # 1. Camera & Device Identification
    camera_type = "Other"
    camera_model_display = "Generic"
    cst_profile = "Rec.709"

    # Panasonic Lumix
    if "panasonic" in make or "panasonic" in handler or "dc-s5" in model or "gh5" in model or filename.startswith("P10") or "__P10" in filename:
        camera_type = "Panasonic"
        camera_model_display = "Lumix DC-S5" if "s5" in model or "dc-s5" in model else "Lumix"
        if bit_depth == 10 or "v-log" in color_transfer or "vlog" in color_transfer:
            cst_profile = "Panasonic V-Gamut / V-Log"
        else:
            cst_profile = "Panasonic Standard (Rec.709)"

    # DJI Drone & Osmo
    elif "dji" in handler or "fc6310" in model or "fc3582" in model or "dji" in model or filename.startswith("DJI_") or "__DJI" in filename:
        camera_type = "DJI"
        camera_model_display = "Phantom 4 Pro (FC6310)" if "fc6310" in model else ("DJI Drone" if "drone" in filename.lower() or "dji" in filename.lower() else "DJI Osmo")
        if "d-log" in comment.lower() or "dlog" in comment.lower():
            cst_profile = "DJI D-Gamut / D-Log M"
        elif "d-cinelike" in comment.lower() or "cinelike" in comment.lower() or "truecolor" in comment.lower():
            cst_profile = "DJI D-Cinelike -> Rec.709"
        else:
            cst_profile = "DJI Standard Rec.709"

    # Sony Alpha / FX / XAVC
    elif "xavc" in brand.lower() or "sony" in make or "ilce" in model or bool(re.search(r"__C\d{4}\.MP4", filename, re.IGNORECASE)):
        camera_type = "Sony"
        camera_model_display = "Alpha / FX (XAVC)"
        if bit_depth == 10 or "slog" in color_transfer or "s-log" in color_transfer:
            cst_profile = "Sony S-Gamut3.Cine / S-Log3"
        else:
            cst_profile = "Sony S-Cinetone / Rec.709"

    # GoPro Action Cam
    elif "gopro" in make or "hero" in model or "gopro" in meta.get("encoder", "").lower() or bool(re.search(r"__(GH0|GOPR)\d+", filename, re.IGNORECASE)):
        camera_type = "GoPro"
        camera_model_display = "HERO Action Cam"
        cst_profile = "GoPro Flat / Rec.709"

    # Timelapses & Hyperlapses
    elif "hyperlapse" in filename.lower() or "__tl" in filename.lower() or "timelapse" in filename.lower():
        camera_type = "Timelapse"
        camera_model_display = "Timelapse"
        cst_profile = "Standard Rec.709"

    # Smartphone / Mobile
    elif bool(re.search(r"__20\d{6}_\d{6}", filename)) or "android" in make or "apple" in make or "iphone" in model or "samsung" in make:
        camera_type = "Mobile"
        camera_model_display = "Smartphone"
        cst_profile = "Rec.709 / sRGB"

    # Rendered Derivatives / Exports
    elif "untitled project" in filename.lower() or "render" in filename.lower() or "export" in filename.lower():
        camera_type = "Render"
        camera_model_display = "Exported Render"
        cst_profile = "Master Rec.709"

    # 2. Strict Resolution & FPS Tagging
    res_category = get_strict_resolution_label(width, height)
    fps_label = get_normalized_fps_label(fps)

    # 3. Bin Naming, Clip Color, and Starting Grade Annotations
    clip_color = CAMERA_COLOR_PALETTE.get(camera_type, "Olive")
    
    # Clean identifier without spaces or special symbols
    safe_cam = camera_type.replace(" ", "_")
    safe_model = camera_model_display.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
    bin_name = f"{safe_cam}_{safe_model}_{res_category}_{fps_label}".strip("_").replace("__", "_")
    timeline_name = f"TL - {camera_type} {camera_model_display} ({res_category} {fps_label})".replace("  ", " ").strip()
    
    starting_grade_note = (
        f"[CST Starting Grade]\n"
        f"Camera: {camera_type} ({camera_model_display})\n"
        f"Resolution: {width}x{height} @ {fps}fps ({bit_depth}-bit)\n"
        f"Recommended Input: {cst_profile}\n"
        f"Output Target: Rec.709 / Gamma 2.4"
    )

    return {
        "camera_type": camera_type,
        "camera_model": camera_model_display,
        "resolution_category": res_category,
        "fps_label": fps_label,
        "bit_depth": f"{bit_depth}-bit",
        "clip_color": clip_color,
        "bin_name": bin_name,
        "timeline_name": timeline_name,
        "cst_profile": cst_profile,
        "starting_grade_note": starting_grade_note,
    }


def scan_and_classify_directory(video_dir: Path) -> List[Tuple[Dict[str, Any], Dict[str, str]]]:
    """Scans all video files in directory and classifies each clip."""
    results = []
    if not video_dir.is_dir():
        return results

    video_exts = {".mp4", ".mov", ".mxf", ".m4v", ".insv", ".braw", ".avi", ".mkv"}
    files = sorted([p for p in video_dir.iterdir() if p.is_file() and p.suffix.lower() in video_exts])

    for f in files:
        meta = probe_file_metadata(f)
        classification = classify_media_clip(meta)
        results.append((meta, classification))

    return results


def print_metadata_breakdown_table(classified_items: List[Tuple[Dict[str, Any], Dict[str, str]]]) -> None:
    """Prints a clear summary table of detected cameras, codecs, strict resolutions, and starting grades."""
    print("\n" + "=" * 105)
    print(f"{'Camera / Device':<22} {'Strict Resolution':<22} {'FPS':<14} {'Bit':<6} {'Color':<8} {'CST Profile':<20} {'Clips'}")
    print("=" * 105)

    buckets: Dict[str, List[Tuple[Dict[str, Any], Dict[str, str]]]] = {}
    for meta, cls in classified_items:
        key = cls["bin_name"]
        buckets.setdefault(key, []).append((meta, cls))

    for key, items in sorted(buckets.items()):
        first_meta, first_cls = items[0]
        res_str = f"{first_cls['resolution_category']} ({first_meta['width']}x{first_meta['height']})"
        fps_str = f"{first_cls['fps_label']} ({first_meta['fps']})"
        count_label = f"{len(items)} clips"
        print(
            f"{first_cls['camera_type']:<10} {first_cls['camera_model']:<11} "
            f"{res_str:<22} {fps_str:<14} {first_cls['bit_depth']:<6} "
            f"{first_cls['clip_color']:<8} {first_cls['cst_profile']:<20} {count_label}"
        )
    print("=" * 105)
    print(f"Total Video Clips Analyzed: {len(classified_items)} across {len(buckets)} strict buckets")
    print("=" * 105)


def organize_in_davinci_resolve(
    classified_items: List[Tuple[Dict[str, Any], Dict[str, str]]],
    create_timelines: bool = True,
    switch_color_page: bool = True,
) -> bool:
    """
    Connects to DaVinci Resolve Studio, creates sub-bins, imports clips,
    assigns clip colors, adds CST markers, and creates dedicated timelines with zero resolution mixing.
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

    # Create Master Staging Bin
    staging_master_folder = None
    for sub in root_folder.GetSubFolderList():
        if sub.GetName() == "Staged_Clips_By_Camera":
            staging_master_folder = sub
            break
    if not staging_master_folder:
        staging_master_folder = media_pool.AddSubFolder(root_folder, "Staged_Clips_By_Camera")

    # Group items by strict bin
    bin_groups: Dict[str, List[Tuple[Dict[str, Any], Dict[str, str]]]] = {}
    for meta, cls in classified_items:
        bin_groups.setdefault(cls["bin_name"], []).append((meta, cls))

    print(f"\nCreating {len(bin_groups)} Media Pool Bins (Strict Unmixed Resolutions) and importing media...")

    for bin_name, items in sorted(bin_groups.items()):
        first_meta, first_cls = items[0]
        print(f"\n📁 Processing Bin: {bin_name} ({len(items)} clips)")

        # Create or find subfolder
        target_folder = None
        for sub in staging_master_folder.GetSubFolderList():
            if sub.GetName() == bin_name:
                target_folder = sub
                break
        if not target_folder:
            target_folder = media_pool.AddSubFolder(staging_master_folder, bin_name)

        media_pool.SetCurrentFolder(target_folder)

        # Import media directly into target bin
        file_paths = [str(meta["file_path"]) for meta, _ in items]
        imported_clips = media_pool.ImportMedia(file_paths) or []

        print(f"   -> Imported {len(imported_clips)} clip(s) into '{bin_name}'")

        # Color-code clips and add CST markers
        for clip in imported_clips:
            try:
                clip.SetClipColor(first_cls["clip_color"])
                clip.AddMarker(
                    0,
                    "Cyan",
                    "Starting Grade CST",
                    first_cls["starting_grade_note"],
                    1,
                )
            except Exception:
                pass

        # Create dedicated timeline per bucket
        if create_timelines and imported_clips:
            tl_name = first_cls["timeline_name"]
            print(f"   -> Creating Timeline: '{tl_name}'...")
            try:
                timeline = media_pool.CreateTimelineFromClips(tl_name, imported_clips)
                if timeline:
                    print(f"      ✓ Timeline '{tl_name}' created successfully.")
            except Exception as e:
                print(f"      ⚠️ Timeline creation error: {e}")

    # Switch to Color Page
    if switch_color_page:
        try:
            resolve.OpenPage("color")
            print("\n🎨 Switched DaVinci Resolve to Color Page.")
        except Exception:
            pass

    print("\n" + "=" * 65)
    print("✓ DaVinci Resolve Organization & Starting Grade Prep Complete!")
    print("=" * 65)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated DaVinci Resolve Media Pool Organizer, Clip Color Coder & Timeline Generator with Strict Resolution Matching."
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=DEFAULT_STAGING_DIR,
        help=f"Path to staged videos directory (default: {DEFAULT_STAGING_DIR})",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Scan and display deep metadata table without connecting to DaVinci Resolve.",
    )
    parser.add_argument(
        "--no-timelines",
        action="store_true",
        help="Organize Bins and Clip Colors only; skip automatic timeline creation.",
    )
    parser.add_argument(
        "--color-page",
        action="store_true",
        default=True,
        help="Automatically switch DaVinci Resolve to the Color page upon completion (default: True).",
    )

    args = parser.parse_args()

    if not args.staging_dir.exists():
        print(f"Error: Staging directory not found: {args.staging_dir}")
        sys.exit(1)

    print("=" * 65)
    print(" DaVinci Resolve Media Organizer & Starting Grade Engine")
    print("=" * 65)
    print(f"Staging Directory: {args.staging_dir}")
    print(f"Scan Only:         {args.scan_only}")
    print(f"Create Timelines:  {not args.no_timelines}")
    print("-" * 65)

    print("Scanning and probing video metadata...")
    classified_items = scan_and_classify_directory(args.staging_dir)

    if not classified_items:
        print("No video files found in the specified directory.")
        sys.exit(0)

    print_metadata_breakdown_table(classified_items)

    if args.scan_only:
        print("\n[SCAN ONLY] Completed inspection. Pass without --scan-only to apply to DaVinci Resolve.")
        sys.exit(0)

    # Apply to Resolve
    organize_in_davinci_resolve(
        classified_items,
        create_timelines=not args.no_timelines,
        switch_color_page=args.color_page,
    )


if __name__ == "__main__":
    main()
