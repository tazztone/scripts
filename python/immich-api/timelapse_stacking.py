import os
import requests
import statistics
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = os.getenv("IMMICH_BASE_URL") or "http://localhost:2283"
API_KEY = os.getenv("IMMICH_API_KEY") or "YOUR_API_KEY_HERE"
DRY_RUN = True  # ← Set to False to actually create stacks
VERIFY_MODE = True    # Creates temporary albums for manual review
VERIFY_COUNT = 20     # How many candidates to create albums for (highest CV first)
VERIFY_PREFIX = "_VERIFY_"  # Prefix for temporary review albums

# V2 configuration
DETECTION_SOURCE = os.getenv("TIMELAPSE_DETECTION_SOURCE") or "duplicates"
MIN_FRAMES = int(os.getenv("TIMELAPSE_MIN_FRAMES") or 10)
MAX_GAP_SECONDS = int(os.getenv("TIMELAPSE_MAX_GAP_SECONDS") or 60)
MIN_SPAN_SECONDS = int(os.getenv("TIMELAPSE_MIN_REQD_SPAN_SECONDS") or 5)
MAX_CV_GAP = float(os.getenv("TIMELAPSE_MAX_CV_GAP") or 0.5)
MAX_CV_SIZE = float(os.getenv("TIMELAPSE_MAX_CV_SIZE") or 0.2)
FILTER_LOCATION = os.getenv("TIMELAPSE_FILTER_LOCATION", "false").lower() == "true"

headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}


def is_regular(assets, max_cv):
    # Sort for gap calculation
    sorted_assets = sorted(assets, key=lambda a: a["localDateTime"])
    times = [datetime.fromisoformat(a["localDateTime"]) for a in sorted_assets]
    gaps = [(times[i + 1] - times[i]).total_seconds() for i in range(len(times) - 1)]
    if not gaps or sum(gaps) == 0:
        return False, 0
    mean_gap = statistics.mean(gaps)
    cv = statistics.stdev(gaps) / mean_gap if len(gaps) > 1 else 0
    return cv <= max_cv, cv


def has_min_span(assets, min_span):
    times = sorted(datetime.fromisoformat(a["localDateTime"]) for a in assets)
    span = (times[-1] - times[0]).total_seconds()
    return span >= min_span, span


def consistent_filesize(assets, max_cv):
    sizes = [a.get("exifInfo", {}).get("fileSizeInByte", 0) for a in assets]
    sizes = [s for s in sizes if s and s > 0]
    if len(sizes) < 2:
        return True, 0
    mean_size = statistics.mean(sizes)
    cv = statistics.stdev(sizes) / mean_size
    return cv <= max_cv, cv


def same_location(assets, max_dist_deg=0.0005):
    coords = [
        (a.get("exifInfo", {}).get("latitude"), a.get("exifInfo", {}).get("longitude"))
        for a in assets
        if a.get("exifInfo", {}).get("latitude")
    ]
    if len(coords) < 2:
        return True  # No GPS data to compare, or only one point
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    dist = max(max(lats) - min(lats), max(lons) - min(lons))
    return dist < max_dist_deg


def is_timelapse(assets):
    if len(assets) < MIN_FRAMES:
        return False, {}

    # Always sort by localDateTime
    assets.sort(key=lambda a: a["localDateTime"])

    ok_span, span = has_min_span(assets, MIN_SPAN_SECONDS)
    ok_regular, cv_gap = is_regular(assets, MAX_CV_GAP)
    ok_size, cv_size = consistent_filesize(assets, MAX_CV_SIZE)
    ok_loc = same_location(assets) if FILTER_LOCATION else True

    stats = {"span": span, "cv_gap": cv_gap, "cv_size": cv_size}

    return (ok_span and ok_regular and ok_size and ok_loc), stats


def cleanup_verify_albums():
    """Deletes all albums starting with the VERIFY_PREFIX."""
    print(f"Fetching albums to clean up (prefix: '{VERIFY_PREFIX}')...")
    albums = requests.get(f"{BASE_URL}/api/albums", headers=headers).json()
    to_delete = [a for a in albums if a["albumName"].startswith(VERIFY_PREFIX)]
    if not to_delete:
        print("No verification albums found.")
        return
    print(f"Deleting {len(to_delete)} verification albums...")
    for a in to_delete:
        requests.delete(f"{BASE_URL}/api/albums/{a['id']}", headers=headers)
        print(f"  ✓ Deleted: {a['albumName']}")
    print("Cleanup complete.")


# Phase 1: Gathering groups
sequences = []

if DETECTION_SOURCE == "duplicates":
    print("Fetching AI duplicate groups...")
    resp = requests.get(f"{BASE_URL}/api/duplicates", headers=headers).json()
    for group in resp:
        sequences.append(group["assets"])
else:
    print("Fetching all assets and performing gap-based grouping...")
    all_assets = []
    page = 1
    while True:
        resp = requests.post(
            f"{BASE_URL}/api/search/metadata",
            headers=headers,
            json={"size": 1000, "page": page},
        ).json()
        items = resp.get("assets", {}).get("items", [])
        all_assets.extend(items)
        if not resp["assets"].get("nextPage"):
            break
        page += 1

    unstacked = [a for a in all_assets if not a.get("stack")]
    unstacked.sort(key=lambda a: a["localDateTime"])

    if unstacked:
        current = [unstacked[0]]
        for prev, curr in zip(unstacked, unstacked[1:]):
            gap = (
                datetime.fromisoformat(curr["localDateTime"])
                - datetime.fromisoformat(prev["localDateTime"])
            ).total_seconds()
            if gap <= MAX_GAP_SECONDS:
                current.append(curr)
            else:
                sequences.append(current)
                current = [curr]
        sequences.append(current)

# Phase 2: Filtering
print(f"Analyzing {len(sequences)} potential groups...")
timelapses = []
for seq in sequences:
    valid, stats = is_timelapse(seq)
    if valid:
        timelapses.append((seq, stats))

print(f"\nFound {len(timelapses)} timelapse candidates:\n")
# Sort by CV descending to show most 'suspicious' / irregular ones first for verification
timelapses.sort(key=lambda x: x[1]["cv_gap"], reverse=True)

for i, (seq, stats) in enumerate(timelapses):
    start = seq[0]["localDateTime"]
    print(
        f"  [{i + 1}] {len(seq):4d} frames | {start[:19]} | span {stats['span']:.0f}s | "
        f"cv_gap={stats['cv_gap']:.3f} | cv_size={stats['cv_size']:.3f}"
    )

# Phase 3: Stacking / Verification
if DRY_RUN:
    print(f"\nDRY RUN — {len(timelapses)} stacks would be created.")

    if VERIFY_MODE and timelapses:
        print(f"\nCreating {min(VERIFY_COUNT, len(timelapses))} verification albums...\n")
        for i, (seq, stats) in enumerate(timelapses[:VERIFY_COUNT]):
            date_str = seq[0]["localDateTime"][:10]
            name = (f"{VERIFY_PREFIX}{i+1:03d} | "
                    f"{date_str} | "
                    f"{len(seq)}f | "
                    f"cv={stats['cv_gap']:.2f}")

            # Create album
            album = requests.post(f"{BASE_URL}/api/albums", headers=headers,
                                  json={"albumName": name}).json()
            if "id" not in album:
                print(f"  [!] Failed to create album: {name} (Response: {album})")
                continue
            album_id = album["id"]

            # Add frames
            requests.put(f"{BASE_URL}/api/albums/{album_id}/assets",
                         headers=headers,
                         json={"ids": [a["id"] for a in seq]})

            url = f"{BASE_URL}/albums/{album_id}"
            print(f"  [{i+1:3d}] {name}")
            print(f"         {url}\n")

        print(f"Review the albums in Immich, then run cleanup to delete them.")
        print(f"To clean up, uncomment 'cleanup_verify_albums()' at the bottom of the script.")

    else:
        print(f"Spot-check the first {VERIFY_COUNT} candidates in Immich:\n")
        for i, (seq, stats) in enumerate(timelapses[:VERIFY_COUNT]):
            # Link to first frame of each group
            asset_id = seq[0]["id"]
            start = seq[0]["localDateTime"]
            print(f"  [{i + 1}] {len(seq):4d} frames | {start[:19]} | "
                  f"cv_gap={stats['cv_gap']:.3f} | cv_size={stats['cv_size']:.3f} | span {stats['span']:.0f}s")
            print(f"        {BASE_URL}/photos/{asset_id}\n")

    print("\nSet DRY_RUN = False in the script to apply final stacking.")
else:
    print(f"\nStacking {len(timelapses)} sequences...")
    for i, (seq, stats) in enumerate(timelapses):
        ids = [a["id"] for a in seq]
        resp = requests.post(
            f"{BASE_URL}/api/stacks", headers=headers, json={"assetIds": ids}
        )
        status = "✓" if resp.status_code == 201 else f"✗ ({resp.status_code})"
        print(
            f"  [{i + 1}] {status} {len(ids)} frames @ {seq[0]['localDateTime'][:19]}"
        )
    print("Done!")

# --- Maintenance ---
# Uncomment and run to delete all albums with the VERIFY_PREFIX:
# cleanup_verify_albums()
