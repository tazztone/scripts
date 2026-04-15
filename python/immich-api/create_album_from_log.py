import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = os.getenv("IMMICH_BASE_URL") or "http://localhost:2283"
API_KEY = os.getenv("IMMICH_API_KEY") or "YOUR_API_KEY_HERE"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timelapse_stacking_last_run.json")

headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

def create_album_from_log():
    if not os.path.exists(LOG_PATH):
        print(f"Error: Log file not found at {LOG_PATH}")
        return

    with open(LOG_PATH, "r") as f:
        run_log = json.load(f)

    if not run_log:
        print("Log file is empty.")
        return

    album_name = input(f"Enter album name [⏱ Timelapse Stacks]: ").strip() or "⏱ Timelapse Stacks"
    
    # Check if album already exists
    print(f"Checking for album: '{album_name}'...")
    albums = requests.get(f"{BASE_URL}/api/albums", headers=headers).json()
    existing = [a for a in albums if a["albumName"] == album_name]
    
    if existing:
        album_id = existing[0]["id"]
        print(f"Found existing album: {album_id}")
    else:
        print("Creating new album...")
        album = requests.post(f"{BASE_URL}/api/albums", headers=headers,
                              json={"albumName": album_name}).json()
        if "id" not in album:
            print(f"Failed to create album: {album}")
            return
        album_id = album["id"]
        print(f"Created new album: {album_id}")

    print("\nModes:")
    print("  [1] Index Mode (Covers only) - Recommended")
    print("  [2] Collection Mode (ALL frames)")
    mode_choice = input("Select mode [1]: ").strip() or "1"
    
    if mode_choice == "2":
        print("Extracting ALL asset IDs (this may take a moment)...")
        assets_to_add = []
        for entry in run_log:
            assets_to_add.extend(entry["asset_ids"])
        mode_str = "Collection"
    else:
        print("Extracting cover IDs...")
        assets_to_add = [entry["asset_ids"][0] for entry in run_log]
        mode_str = "Index"

    print(f"Adding {len(assets_to_add)} assets to album ({mode_str} mode)...")
    
    # Batch add (Immich handles duplicates)
    for i in range(0, len(assets_to_add), 500):
        batch = assets_to_add[i:i+500]
        resp = requests.put(f"{BASE_URL}/api/albums/{album_id}/assets",
                            headers=headers,
                            json={"ids": batch})
        if resp.status_code != 200:
            print(f"Failed to add batch starting at {i}: {resp.status_code}")
    
    print(f"Successfully updated '{album_name}' in {mode_str} mode.")
    print(f"View here: {BASE_URL}/albums/{album_id}")

if __name__ == "__main__":
    create_album_from_log()
