import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("IMMICH_BASE_URL", "http://localhost:2283")
API_KEY = os.getenv("IMMICH_API_KEY")
DRY_RUN = False  # ← set to False to actually delete

headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

# Fetch all stacks
print("Fetching all stacks...")
stacks = requests.get(f"{BASE_URL}/api/stacks", headers=headers).json()
print(f"Found {len(stacks)} stacks total")

# Each stack has a primaryAssetId and assetCount — filter by size if needed
MIN_FRAMES = 10  # only show stacks that look like timelapses
large = [s for s in stacks if len(s.get("assets", [])) >= MIN_FRAMES]
print(f"Stacks with {MIN_FRAMES}+ frames: {len(large)}\n")

for i, s in enumerate(large):
    print(
        f"  [{i + 1:3d}] id={s['id']}  frames={len(s.get('assets', []))}  primary={s['primaryAssetId']}"
    )

if DRY_RUN:
    print(
        f"\nDRY RUN — {len(large)} stacks would be deleted. Set DRY_RUN = False to apply."
    )
else:
    confirm = input(f"\nDelete all {len(large)} stacks? [y/n]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
    else:
        for i, s in enumerate(large):
            resp = requests.delete(f"{BASE_URL}/api/stacks/{s['id']}", headers=headers)
            status = "✓" if resp.status_code == 204 else f"✗ {resp.status_code}"
            print(f"  [{i + 1:3d}] {status}  {len(s.get('assets', []))}f  {s['id']}")
        print("Done!")
