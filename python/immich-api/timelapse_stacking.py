import os
import json
import webbrowser
import requests
import statistics
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = os.getenv("IMMICH_BASE_URL") or "http://localhost:2283"
API_KEY = os.getenv("IMMICH_API_KEY") or "YOUR_API_KEY_HERE"
VERIFY_PREFIX = "_VERIFY_"

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timelapse_stacking_last_run.json")

headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

# --- Helpers ---

def ask(prompt, options):
    """Print a menu and return the chosen key."""
    print(f"\n{prompt}")
    for key, label in options.items():
        print(f"  [{key}] {label}")
    while True:
        choice = input("  → ").strip().upper()
        if choice in options:
            return choice
        # Also check against lowercase version of keys if they aren't numbers
        if choice.lower() in options:
            return choice.lower()
        print(f"  Please enter one of: {', '.join(options)}")

def ask_int(prompt, default):
    val = input(f"  {prompt} [{default}]: ").strip()
    return int(val) if val.isdigit() else default

def header(title, subtitle=""):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print(f"{'─'*50}")

# --- Filtering Logic ---

def is_regular(assets, max_cv):
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
        return True
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    dist = max(max(lats) - min(lats), max(lons) - min(lons))
    return dist < max_dist_deg

def get_candidates(min_frames, max_cv_gap, max_cv_size, min_span, filter_location, detection_source, max_gap_seconds_search):
    sequences = []
    if detection_source == "duplicates":
        print("  Fetching AI duplicate groups...")
        resp = requests.get(f"{BASE_URL}/api/duplicates", headers=headers).json()
        for group in resp:
            sequences.append(group["assets"])
    else:
        print("  Fetching all assets and performing gap-based grouping...")
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
                if gap <= max_gap_seconds_search:
                    current.append(curr)
                else:
                    sequences.append(current)
                    current = [curr]
            sequences.append(current)

    candidates = []
    for seq in sequences:
        if len(seq) < min_frames:
            continue
        
        seq.sort(key=lambda a: a["localDateTime"])
        ok_span, span = has_min_span(seq, min_span)
        ok_regular, cv_gap = is_regular(seq, max_cv_gap)
        ok_size, cv_size = consistent_filesize(seq, max_cv_size)
        ok_loc = same_location(seq) if filter_location else True

        if ok_span and ok_regular and ok_size and ok_loc:
            candidates.append({
                "assets": seq,
                "span": span,
                "cv_gap": cv_gap,
                "cv_size": cv_size
            })
            
    # Merge overlapping groups into unified sequences
    candidates.sort(key=lambda c: c["cv_gap"])
    merged = []

    for c in candidates:
        c_ids = set(a["id"] for a in c["assets"])
        merged_into = None

        for kept in merged:
            kept_ids = set(a["id"] for a in kept["assets"])
            intersection = len(c_ids & kept_ids)
            overlap = intersection / min(len(c_ids), len(kept_ids)) if intersection else 0
            if overlap >= 0.80:
                merged_into = kept
                break

        if merged_into is not None:
            # Union: add any frames not already in the kept group
            existing_ids = {a["id"] for a in merged_into["assets"]}
            new_frames = [a for a in c["assets"] if a["id"] not in existing_ids]
            if new_frames:
                merged_into["assets"].extend(new_frames)
                # Re-sort chronologically after merge
                merged_into["assets"].sort(key=lambda a: a["localDateTime"])
                # Recalculate stats for the merged sequence
                times = [datetime.fromisoformat(a["localDateTime"]) for a in merged_into["assets"]]
                gaps = [(times[i+1]-times[i]).total_seconds() for i in range(len(times)-1)]
                merged_into["span"] = (times[-1]-times[0]).total_seconds()
                merged_into["cv_gap"] = statistics.stdev(gaps)/statistics.mean(gaps) if len(gaps) > 1 else 0
                sizes = [a.get("exifInfo",{}).get("fileSizeInByte",0) for a in merged_into["assets"]]
                sizes = [s for s in sizes if s]
                merged_into["cv_size"] = statistics.stdev(sizes)/statistics.mean(sizes) if len(sizes) > 1 else 0
        else:
            merged.append(c)

    return merged

# --- Lifecycle Actions ---

def create_verify_albums(candidates, count):
    # Sort by CV descending to show most 'suspicious' / irregular ones first
    to_verify = sorted(candidates, key=lambda x: x["cv_gap"], reverse=True)[:count]
    print(f"\n  Creating {len(to_verify)} verification albums...")
    for i, c in enumerate(to_verify):
        date_str = c["assets"][0]["localDateTime"][:10]
        name = (f"{VERIFY_PREFIX}{i+1:03d} | "
                f"{date_str} | "
                f"{len(c['assets'])}f | "
                f"cv={c['cv_gap']:.2f}")

        album = requests.post(f"{BASE_URL}/api/albums", headers=headers,
                              json={"albumName": name}).json()
        if "id" not in album:
            print(f"    [!] Failed: {name}")
            continue
        album_id = album["id"]
        
        requests.put(f"{BASE_URL}/api/albums/{album_id}/assets",
                     headers=headers,
                     json={"ids": [a["id"] for a in c["assets"]]})
        print(f"    ✓ {name}")

def cleanup_verify_albums():
    print(f"\n  Cleaning up albums with prefix '{VERIFY_PREFIX}'...")
    albums = requests.get(f"{BASE_URL}/api/albums", headers=headers).json()
    targets = [a for a in albums if a["albumName"].startswith(VERIFY_PREFIX)]
    if not targets:
        print("  No verification albums found.")
        return
    for a in targets:
        requests.delete(f"{BASE_URL}/api/albums/{a['id']}", headers=headers)
    print(f"  Deleted {len(targets)} albums.")

def apply_stacks(candidates):
    print(f"\n  Stacking {len(candidates)} sequences...")
    run_log = []
    for i, c in enumerate(candidates):
        ids = [a["id"] for a in c["assets"]]
        resp = requests.post(f"{BASE_URL}/api/stacks", headers=headers,
                             json={"assetIds": ids})
        if resp.status_code in (200, 201):
            stack_id = resp.json().get("id")
            run_log.append({"stack_id": stack_id, "asset_ids": ids,
                            "date": c["assets"][0]["localDateTime"][:19],
                            "frames": len(ids)})
            print(f"  [{i+1:3d}] ✓  {len(ids)}f @ {c['assets'][0]['localDateTime'][:19]}")
        else:
            print(f"  [{i+1:3d}] ✗  {resp.status_code}")

    with open(LOG_PATH, "w") as f:
        json.dump(run_log, f, indent=2)
    print(f"\n  Run log saved → {LOG_PATH}")
    print("\n  Done!")

def unstack_last_run():
    if not os.path.exists(LOG_PATH):
        print("\n  No run log found. Nothing to unstack.")
        return

    with open(LOG_PATH) as f:
        run_log = json.load(f)

    print(f"\n  Unstacking {len(run_log)} stacks from last run...")
    failed = []
    for i, entry in enumerate(run_log):
        resp = requests.delete(f"{BASE_URL}/api/stacks/{entry['stack_id']}",
                               headers=headers)
        if resp.status_code == 204:
            print(f"  [{i+1:3d}] ✓  {entry['frames']}f @ {entry['date']}")
        else:
            failed.append(entry)
            print(f"  [{i+1:3d}] ✗  {resp.status_code}  {entry['frames']}f @ {entry['date']}")

    if failed:
        with open(LOG_PATH, "w") as f:
            json.dump(failed, f, indent=2)
        print(f"\n  {len(failed)} stacks failed to delete — log updated with remaining entries.")
    else:
        os.remove(LOG_PATH)
        print("\n  Log cleared. You can now re-run the wizard.")

# --- Wizard ---

def wizard():
    header("Immich Timelapse Stacker", "Wizard mode")

    # Load defaults from env
    min_frames = int(os.getenv("TIMELAPSE_MIN_FRAMES") or 10)
    max_cv_gap = float(os.getenv("TIMELAPSE_MAX_CV_GAP") or 0.35)
    max_cv_size = float(os.getenv("TIMELAPSE_MAX_CV_SIZE") or 0.1)
    min_span = int(os.getenv("TIMELAPSE_MIN_REQD_SPAN_SECONDS") or 15)
    detection_source = os.getenv("TIMELAPSE_DETECTION_SOURCE") or "duplicates"
    max_gap_seconds_search = int(os.getenv("TIMELAPSE_MAX_GAP_SECONDS") or 60)
    filter_location = os.getenv("TIMELAPSE_FILTER_LOCATION", "false").lower() == "true"

    while True:
        # Step 1 — Filters
        header("Step 1 — Tune filters",
               f"SOURCE={detection_source}  MIN_FRAMES={min_frames}  "
               f"CV_GAP={max_cv_gap}  CV_SIZE={max_cv_size}  SPAN={min_span}s")

        choice = ask("Options:", {
            "1": "Change filters", 
            "2": "Run with current", 
            "U": "Unstack last run and start fresh", 
            "Q": "Quit"
        })

        if choice == "Q":
            return
            
        if choice == "U":
            unstack_last_run()
            continue

        if choice == "1":
            src_choice = ask("Detection Source:", {"1": "AI Duplicates (Fast)", "2": "Gap-based Search (Slow)"})
            detection_source = "duplicates" if src_choice == "1" else "search"
            
            min_frames = ask_int("MIN_FRAMES (min frames per sequence)", min_frames)
            
            # Use fallbacks for float inputs to prevent crashes on empty input
            raw_gap = input(f"  MAX_CV_GAP (regularity, 0-1) [{max_cv_gap}]: ").strip()
            max_cv_gap = float(raw_gap) if raw_gap else max_cv_gap
            
            raw_size = input(f"  MAX_CV_SIZE (filesize, 0-1) [{max_cv_size}]: ").strip()
            max_cv_size = float(raw_size) if raw_size else max_cv_size
            
            min_span = ask_int("MIN_SPAN (minimum total seconds)", min_span)
            if detection_source == "search":
                max_gap_seconds_search = ask_int("MAX_GAP_SECONDS (search gap)", max_gap_seconds_search)
            filter_location = ask("Filter by Location?", {"Y": "Yes", "N": "No"}).upper() == "Y"
            continue

        candidates = get_candidates(min_frames, max_cv_gap, max_cv_size, min_span, filter_location, detection_source, max_gap_seconds_search)

        if not candidates:
            print("\n  [!] No candidates found with current filters.")
            continue

        header("Step 2 — Verify", f"{len(candidates)} candidates found")
        
        # Display the candidate table before asking for verification
        print(f"{'#':>3} | {'Frames':>6} | {'Timestamp':19} | {'Span':>6} | {'CV Gap':>7} | {'CV Size':>7}")
        print(f"{'─'*3}─┼─{'─'*6}─┼─{'─'*19}─┼─{'─'*6}─┼─{'─'*7}─┼─{'─'*7}")
        
        # Sort by CV descending to show most 'suspicious' / irregular ones first
        candidates.sort(key=lambda x: x["cv_gap"], reverse=True)
        
        for i, c in enumerate(candidates):
            start = c["assets"][0]["localDateTime"]
            print(f"  [{i+1:3d}] {len(c['assets']):6d} | {start[:19]} | {c['span']:5.0f}s | {c['cv_gap']:7.3f} | {c['cv_size']:7.3f}")

        choice = ask("Verify candidates?", {
            "1": f"Create verification albums (max {min(20, len(candidates))})",
            "2": "Skip to stacking",
            "3": "Back to filters",
            "4": "Abort"
        })

        if choice == "4":
            return
        if choice == "3":
            continue
        
        if choice == "1":
            count = ask_int("How many to verify", min(20, len(candidates)))
            create_verify_albums(candidates, count)
            
            # Open browser
            webbrowser.open(f"{BASE_URL}/albums")
            header("Step 3 — Review in Immich")
            input("  Albums created. Review them in Immich, then press Enter to continue...")
            
            choice = ask("Step 4 — Finalize", {
                "1": f"Stack all {len(candidates)} candidates",
                "2": "Restart (re-tune filters)",
                "3": "Abort (clean up and exit)"
            })
            
            cleanup_verify_albums()
            
            if choice == "3":
                return
            if choice == "2":
                continue

        apply_stacks(candidates)
        break

if __name__ == "__main__":
    wizard()
