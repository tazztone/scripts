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


def resolve_album(album_arg, albums):
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
    selected_album = resolve_album(target_album_ref, albums)
    album_id = selected_album["id"]

    # Step 1: Get complete asset list of target album
    print(f"\nFetching assets for album: '{selected_album['albumName']}'...")
    full_album = get_album_details(album_id)
    existing_assets = full_album.get("assets", [])
    album_name = full_album.get("albumName", "Untitled Album")

    if not existing_assets:
        print(f"\nAlbum '{album_name}' is currently empty.")
        print("Cannot expand dates because there are no existing assets to extract dates from.")
        sys.exit(0)

    existing_ids = {a["id"] for a in existing_assets}
    print(f"Found {len(existing_assets)} existing asset(s) in album '{album_name}'.")

    # Step 2: Extract unique dates from existing assets
    dates = sorted(
        set(a["localDateTime"][:10] for a in existing_assets if a.get("localDateTime"))
    )

    if not dates:
        print("Could not extract capture dates from any assets in this album.")
        sys.exit(1)

    print(f"\nScanning Immich library for {len(dates)} unique date(s):")
    for d in dates:
        print(f"  - {d}")

    # Step 3: Search all photos on those dates
    all_found_ids = set()
    date_breakdown = []

    print("\nQuerying library...")
    for date_str in dates:
        date_assets = search_photos_on_date(date_str)
        date_ids = {a["id"] for a in date_assets}
        all_found_ids.update(date_ids)

        in_album_for_date = sum(
            1 for a in existing_assets if a.get("localDateTime", "").startswith(date_str)
        )
        new_for_date = len(date_ids - existing_ids)
        date_breakdown.append({
            "date": date_str,
            "library_total": len(date_ids),
            "album_current": in_album_for_date,
            "new_to_add": new_for_date,
        })

    # Step 4: Summary Table
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
        f"{'TOTALS':<14} {len(all_found_ids):<16} {len(existing_assets):<14} +{len(new_ids):<12}"
    )
    print("─" * 60)

    if not new_ids:
        print(f"\n✓ Album '{album_name}' is already completely up to date with all photos from these dates.")
        sys.exit(0)

    print(f"\nFound {len(new_ids)} new photo(s) available to add to '{album_name}'.")

    if args.dry_run:
        print("\n[DRY RUN] No changes were made to the album. Run without -n/--dry-run to apply.")
        sys.exit(0)

    if not args.yes:
        confirm = input(f"\nAdd {len(new_ids)} new photo(s) to '{album_name}'? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Aborted. No changes made.")
            sys.exit(0)

    # Step 5: Batch add assets in chunks of 500
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
