#!/usr/bin/env python3
import os
import sys
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = (os.getenv("IMMICH_BASE_URL") or "http://localhost:2283").rstrip("/")
API_KEY = os.getenv("IMMICH_API_KEY") or ""
DEFAULT_ALBUM_ID = os.getenv("IMMICH_ALBUM_ID")

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def check_api_key():
    if not API_KEY or API_KEY == "ENTER HERE" or API_KEY == "YOUR_API_KEY_HERE":
        print("Error: IMMICH_API_KEY is not configured in your .env file.")
        print("Please add a valid Immich API key to continue.")
        sys.exit(1)


def fetch_all_albums():
    """Fetch all albums accessible to the user."""
    try:
        resp = requests.get(f"{BASE_URL}/api/albums", headers=headers)
        if resp.status_code != 200:
            print(f"Error fetching albums (HTTP {resp.status_code}): {resp.text}")
            sys.exit(1)
        return resp.json()
    except Exception as e:
        print(f"Error connecting to Immich at {BASE_URL}: {e}")
        sys.exit(1)


def prompt_select_album(albums):
    """Interactively prompt the user to select an album."""
    if not albums:
        print("No albums found in your Immich library.")
        sys.exit(1)

    print("\nSelect an album to expand / update:")
    for idx, album in enumerate(albums, start=1):
        asset_count = album.get("assetCount", len(album.get("assets", [])))
        print(f"  [{idx:2d}] {album['albumName']} ({asset_count} assets)")

    while True:
        choice = input("\nEnter album number or name to search: ").strip()
        if not choice:
            continue
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(albums):
                return albums[idx - 1]
            print(f"Please enter a number between 1 and {len(albums)}.")
        else:
            # Search by name substring
            matches = [a for a in albums if choice.lower() in a["albumName"].lower()]
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                print(f"Multiple matching albums found for '{choice}':")
                for m_idx, match in enumerate(matches, start=1):
                    print(f"  [{m_idx}] {match['albumName']} ({match.get('assetCount', 0)} assets)")
                sub_choice = input("Select number from matching list: ").strip()
                if sub_choice.isdigit() and 1 <= int(sub_choice) <= len(matches):
                    return matches[int(sub_choice) - 1]
            else:
                print(f"No albums matching '{choice}'. Try again.")


def resolve_album(album_arg, albums, auto_yes=False):
    """Resolve album by UUID, exact/fuzzy name match, or interactive selection."""
    if album_arg:
        # Match by ID
        for a in albums:
            if a["id"].lower() == album_arg.lower():
                return a
        # Match by exact name (case-insensitive)
        exact_matches = [a for a in albums if a["albumName"].lower() == album_arg.lower()]
        if len(exact_matches) == 1:
            return exact_matches[0]
        # Match by substring
        sub_matches = [a for a in albums if album_arg.lower() in a["albumName"].lower()]
        if len(sub_matches) == 1:
            return sub_matches[0]
        elif len(sub_matches) > 1:
            print(f"Multiple albums match '{album_arg}':")
            for idx, match in enumerate(sub_matches, start=1):
                print(f"  [{idx}] {match['albumName']} ({match.get('assetCount', 0)} assets)")
            choice = input("Select number: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(sub_matches):
                return sub_matches[int(choice) - 1]
            print("Invalid selection.")
            sys.exit(1)
        else:
            print(f"Error: No album found matching '{album_arg}'.")
            sys.exit(1)

    # If DEFAULT_ALBUM_ID is set in .env
    if DEFAULT_ALBUM_ID:
        matching = [a for a in albums if a["id"] == DEFAULT_ALBUM_ID]
        if matching:
            default_album = matching[0]
            if auto_yes:
                return default_album
            use_default = input(
                f"Use default album from .env: '{default_album['albumName']}'? [Y/n/list]: "
            ).strip().lower()
            if use_default in ("", "y", "yes"):
                return default_album
            elif use_default == "n":
                return prompt_select_album(albums)

    return prompt_select_album(albums)


def get_album_details(album_id):
    resp = requests.get(f"{BASE_URL}/api/albums/{album_id}", headers=headers)
    if resp.status_code != 200:
        print(f"Error retrieving album details (HTTP {resp.status_code}): {resp.text}")
        sys.exit(1)
    return resp.json()


def get_album_assets(album_id):
    """
    Retrieve album name, existing asset IDs, unique capture dates, and a mapping of asset_id -> date_str.
    Supports both legacy Immich (album['assets']) and Immich v3+ timeline bucket API.
    """
    album_info = get_album_details(album_id)
    album_name = album_info.get("albumName", "Untitled Album")
    existing_ids = set()
    asset_date_map = {}
    unique_dates = set()

    # 1. Check legacy format (direct 'assets' array)
    if "assets" in album_info and isinstance(album_info["assets"], list) and len(album_info["assets"]) > 0:
        for a in album_info["assets"]:
            a_id = a.get("id")
            if a_id:
                existing_ids.add(a_id)
                dt = a.get("localDateTime") or a.get("fileCreatedAt") or a.get("createdAt")
                if dt:
                    d_str = str(dt)[:10]
                    asset_date_map[a_id] = d_str
                    unique_dates.add(d_str)
        return album_name, existing_ids, sorted(unique_dates), asset_date_map

    # 2. Immich v3+ Timeline Bucket API
    try:
        buckets_resp = requests.get(
            f"{BASE_URL}/api/timeline/buckets?albumId={album_id}",
            headers=headers,
        )
        if buckets_resp.status_code == 200:
            buckets = buckets_resp.json()
            for b in buckets:
                tb = b.get("timeBucket")
                if not tb:
                    continue
                b_resp = requests.get(
                    f"{BASE_URL}/api/timeline/bucket?albumId={album_id}&timeBucket={tb}",
                    headers=headers,
                )
                if b_resp.status_code == 200:
                    b_data = b_resp.json()
                    if isinstance(b_data, dict):
                        ids = b_data.get("id", [])
                        created_ats = b_data.get("fileCreatedAt", []) or b_data.get("createdAt", [])
                        for a_id, dt in zip(ids, created_ats):
                            existing_ids.add(a_id)
                            if dt:
                                d_str = str(dt)[:10]
                                asset_date_map[a_id] = d_str
                                unique_dates.add(d_str)
                    elif isinstance(b_data, list):
                        for item in b_data:
                            if isinstance(item, dict) and "id" in item:
                                a_id = item["id"]
                                existing_ids.add(a_id)
                                dt = item.get("localDateTime") or item.get("fileCreatedAt") or item.get("createdAt")
                                if dt:
                                    d_str = str(dt)[:10]
                                    asset_date_map[a_id] = d_str
                                    unique_dates.add(d_str)
    except Exception as e:
        print(f"Warning: Timeline bucket query encountered an issue: {e}")

    return album_name, existing_ids, sorted(unique_dates), asset_date_map


def search_photos_on_date(date_str):
    """Query Immich metadata search for all photos on a specific date (YYYY-MM-DD)."""
    date_assets = []
    page = 1
    while True:
        resp = requests.post(
            f"{BASE_URL}/api/search/metadata",
            headers=headers,
            json={
                "takenAfter": f"{date_str}T00:00:00.000Z",
                "takenBefore": f"{date_str}T23:59:59.999Z",
                "size": 1000,
                "page": page,
            },
        )
        if resp.status_code != 200:
            print(f"  Warning: Search failed for {date_str} (HTTP {resp.status_code})")
            break

        data = resp.json()
        items = data.get("assets", {}).get("items", [])
        date_assets.extend(items)
        if not data.get("assets", {}).get("nextPage") or not items:
            break
        page += 1
    return date_assets


def main():
    parser = argparse.ArgumentParser(
        description="Expand or update an Immich album with all photos taken on the same dates (e.g. exported RAW edits, unlocated photos)."
    )
    parser.add_argument(
        "album",
        nargs="?",
        help="Target album name or UUID (optional; launches interactive picker if omitted)",
    )
    parser.add_argument(
        "-a", "--album-id",
        dest="album_id_opt",
        help="Target album UUID directly",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print all new asset filenames without truncating",
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Preview changes and stats without adding photos to the album",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Automatically apply changes without interactive confirmation prompt",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all albums in your Immich library and exit",
    )

    args = parser.parse_args()

    check_api_key()

    albums = fetch_all_albums()

    if args.list:
        print(f"\nImmich Albums on {BASE_URL}:")
        for idx, a in enumerate(albums, start=1):
            count = a.get("assetCount", len(a.get("assets", [])))
            print(f"  [{idx:2d}] {a['albumName']} (id: {a['id']}, assets: {count})")
        sys.exit(0)

    target_album_ref = args.album_id_opt or args.album
    selected_album = resolve_album(target_album_ref, albums, auto_yes=args.yes)
    album_id = selected_album["id"]

    # Step 1: Get complete asset list & dates of target album
    print(f"\nFetching assets for album: '{selected_album['albumName']}'...")
    album_name, existing_ids, dates, asset_date_map = get_album_assets(album_id)

    if not existing_ids:
        print(f"\nAlbum '{album_name}' is currently empty.")
        print("Cannot expand dates because there are no existing assets to extract dates from.")
        sys.exit(0)

    print(f"Found {len(existing_ids)} existing asset(s) across {len(dates)} date(s) in album '{album_name}'.")

    if not dates:
        print("Could not extract capture dates from any assets in this album.")
        sys.exit(1)

    print(f"\nScanning Immich library for {len(dates)} unique date(s):")
    for d in dates:
        print(f"  - {d}")

    # Step 2: Search all photos on those dates
    all_found_ids = set()
    all_found_assets = {}
    date_breakdown = []

    print("\nQuerying library...")
    for date_str in dates:
        date_assets = search_photos_on_date(date_str)
        date_ids = set()
        for a in date_assets:
            a_id = a.get("id")
            if a_id:
                date_ids.add(a_id)
                all_found_ids.add(a_id)
                all_found_assets[a_id] = a

        in_album_for_date = sum(
            1 for a_id, d in asset_date_map.items() if d == date_str
        )
        new_for_date = len(date_ids - existing_ids)
        date_breakdown.append({
            "date": date_str,
            "library_total": len(date_ids),
            "album_current": in_album_for_date,
            "new_to_add": new_for_date,
        })

    # Step 3: Summary Table
    new_ids = list(all_found_ids - existing_ids)

    print("\n" + "─" * 60)
    print(f"{'Date':<14} {'Library Total':<16} {'In Album':<14} {'New to Add':<12}")
    print("─" * 60)
    for row in date_breakdown:
        print(
            f"{row['date']:<14} {row['library_total']:<16} {row['album_current']:<14} +{row['new_to_add']:<12}"
        )
    print("─" * 60)
    print(
        f"{'TOTALS':<14} {len(all_found_ids):<16} {len(existing_ids):<14} +{len(new_ids):<12}"
    )
    print("─" * 60)

    if not new_ids:
        print(f"\n✓ Album '{album_name}' is already completely up to date with all photos from these dates.")
        sys.exit(0)

    # Detailed list of new assets to add
    new_assets = [all_found_assets[aid] for aid in new_ids if aid in all_found_assets]
    new_assets.sort(key=lambda a: a.get("localDateTime") or a.get("fileCreatedAt") or "")

    print(f"\nNew asset(s) to add ({len(new_assets)} total):")
    new_by_date = {}
    for a in new_assets:
        d = (a.get("localDateTime") or a.get("fileCreatedAt") or "Unknown")[:10]
        new_by_date.setdefault(d, []).append(a)

    MAX_DISPLAY = len(new_assets) if args.verbose else 30
    displayed_count = 0

    for d in sorted(new_by_date.keys()):
        if displayed_count >= MAX_DISPLAY and not args.verbose:
            break
        d_items = new_by_date[d]
        print(f"\n  📅 {d} (+{len(d_items)} new):")
        for a in d_items:
            if displayed_count >= MAX_DISPLAY and not args.verbose:
                break
            filename = a.get("originalFileName") or "Unnamed"
            asset_type = a.get("type", "IMAGE")
            time_str = (a.get("localDateTime") or a.get("fileCreatedAt") or "")[11:19]
            time_label = f" at {time_str}" if time_str else ""
            photo_url = f"{BASE_URL}/photos/{a['id']}"
            print(f"    • {filename:<25} [{asset_type:<5}]{time_label}  →  {photo_url}")
            displayed_count += 1

    if displayed_count < len(new_assets):
        remaining = len(new_assets) - displayed_count
        print(f"\n    ... and {remaining} more new asset(s) (pass -v / --verbose to view all)")

    if args.dry_run:
        print("\n[DRY RUN] No changes were made to the album. Run without -n/--dry-run to apply.")
        sys.exit(0)

    if not args.yes:
        confirm = input(f"\nAdd {len(new_ids)} new photo(s) to '{album_name}'? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Aborted. No changes made.")
            sys.exit(0)

    # Step 4: Batch add assets in chunks of 500
    print(f"\nAdding {len(new_ids)} asset(s) to '{album_name}' in batches of 500...")
    total_added = 0
    total_failed = 0

    for i in range(0, len(new_ids), 500):
        batch = new_ids[i : i + 500]
        batch_num = i // 500 + 1
        resp = requests.put(
            f"{BASE_URL}/api/albums/{album_id}/assets",
            headers=headers,
            json={"ids": batch},
        )
        if resp.status_code in (200, 201):
            result = resp.json()
            failed = [r for r in result if not r.get("success")] if isinstance(result, list) else []
            added = len(batch) - len(failed)
            total_added += added
            total_failed += len(failed)
            print(f"  Batch {batch_num}: added {added}, failed {len(failed)}")
        else:
            print(f"  Batch {batch_num} failed (HTTP {resp.status_code}): {resp.text}")
            total_failed += len(batch)

    print(f"\n✓ Done! Successfully added {total_added} photo(s) to '{album_name}'.")
    if total_failed > 0:
        print(f"  Warning: {total_failed} asset(s) failed to add.")
    print(f"View album: {BASE_URL}/albums/{album_id}")


if __name__ == "__main__":
    main()
