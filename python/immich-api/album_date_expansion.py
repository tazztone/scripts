import os
import requests
from dotenv import load_dotenv

load_dotenv()


BASE_URL = os.getenv("IMMICH_BASE_URL") or "http://localhost:2283"
API_KEY = os.getenv("IMMICH_API_KEY") or "ENTER HERE"
ALBUM_ID = os.getenv("IMMICH_ALBUM_ID") or "86e11802-83db-44d3-bdb6-dcf0e4c0d6ca"
DRY_RUN = False  # ← set to False to actually add photos

headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

# Step 1: Get all assets in your album
album = requests.get(f"{BASE_URL}/api/albums/{ALBUM_ID}", headers=headers).json()
existing_assets = album["assets"]
print(f"Album: '{album['albumName']}' — {len(existing_assets)} existing assets")

# Step 2: Extract unique dates
dates = set(a["localDateTime"][:10] for a in existing_assets)
print(f"Dates in album: {sorted(dates)}")

# Step 3: Search ALL photos on those dates
all_ids_to_add = set()
for date in sorted(dates):
    page = 1
    date_count = 0
    while True:
        resp = requests.post(
            f"{BASE_URL}/api/search/metadata",
            headers=headers,
            json={
                "takenAfter": f"{date}T00:00:00.000Z",
                "takenBefore": f"{date}T23:59:59.999Z",
                "size": 1000,
                "page": page,
            },
        ).json()
        items = resp.get("assets", {}).get("items", [])
        for item in items:
            all_ids_to_add.add(item["id"])
            date_count += 1
        if not resp["assets"].get("nextPage"):
            break
        page += 1
    print(f"  {date}: {date_count} total photos found")

# Step 4: Filter to only new ones
existing_ids = {a["id"] for a in existing_assets}
new_ids = list(all_ids_to_add - existing_ids)
print(f"\n{len(new_ids)} new photos would be added to the album")

if DRY_RUN:
    print("DRY RUN — no changes made. Set DRY_RUN = False to apply.")
else:
    for i in range(0, len(new_ids), 500):
        batch = new_ids[i : i + 500]
        result = requests.put(
            f"{BASE_URL}/api/albums/{ALBUM_ID}/assets",
            headers=headers,
            json={"ids": batch},
        ).json()
        failed = [r for r in result if not r.get("success")]
        print(
            f"Batch {i // 500 + 1}: added {len(batch) - len(failed)}, failed {len(failed)}"
        )
    print("Done!")
