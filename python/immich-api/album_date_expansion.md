# Immich Album Date Expansion

A Python utility to expand an existing Immich album by automatically querying the Immich API for all photos taken on the same dates as existing album assets, and batch-adding any missing assets.

---

## 🎯 Purpose & Problem Solved

When creating an album in Immich (for instance, via location-based searches, face detection, or manual curation), some photos taken on the same days may be left out—especially if those photos lack GPS metadata or were shot on a secondary camera.

This script:
1. **Reads all assets** currently inside the target Immich album.
2. **Extracts unique capture dates** (`YYYY-MM-DD`) from each asset's `localDateTime`.
3. **Searches your entire Immich library** for all photos taken between `00:00:00` and `23:59:59` on those specific dates.
4. **Calculates the set difference** to identify missing photos not yet in the album.
5. **Batch adds** the missing photos to the album in chunks of 500.

---

## 📋 Requirements & Dependencies

- Python 3.8+
- Python packages:
  - `requests`
  - `python-dotenv`

Install dependencies:
```bash
pip install requests python-dotenv
```

---

## ⚙️ Configuration

Create a `.env` file in `python/immich-api/` (or copy from `.env.example`):

```dotenv
IMMICH_BASE_URL=http://localhost:2283
IMMICH_API_KEY=your_api_key_here
IMMICH_ALBUM_ID=86e11802-83db-44d3-bdb6-dcf0e4c0d6ca
```

### Environment Variables

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `IMMICH_BASE_URL` | Yes | Base URL of your Immich server instance | `http://localhost:2283` or `https://photos.yourdomain.com` |
| `IMMICH_API_KEY` | Yes | API key generated in your Immich Account Settings | `v8...` |
| `IMMICH_ALBUM_ID` | Yes | UUID of the target album to expand | `86e11802-83db-44d3-bdb6-dcf0e4c0d6ca` |

### Script Options

Inside [album_date_expansion.py](file:///home/tazztone/_coding/scripts/python/immich-api/album_date_expansion.py):

| Option | Default | Description |
| :--- | :--- | :--- |
| `DRY_RUN` | `False` | When set to `True`, only previews changes without modifying the album. Set to `False` to execute additions. |

---

## 🚀 Usage

### 1. Preview Mode (Dry Run)

To safely preview which photos will be added without modifying the album, ensure `DRY_RUN = True` in [album_date_expansion.py](file:///home/tazztone/_coding/scripts/python/immich-api/album_date_expansion.py), then run:

```bash
python3 album_date_expansion.py
```

**Sample Output:**
```text
Album: 'Summer Trip 2024' — 142 existing assets
Dates in album: ['2024-07-12', '2024-07-13', '2024-07-14']
  2024-07-12: 85 total photos found
  2024-07-13: 130 total photos found
  2024-07-14: 64 total photos found

137 new photos would be added to the album
DRY RUN — no changes made. Set DRY_RUN = False to apply.
```

### 2. Apply Changes

Set `DRY_RUN = False` in [album_date_expansion.py](file:///home/tazztone/_coding/scripts/python/immich-api/album_date_expansion.py) and re-run:

```bash
python3 album_date_expansion.py
```

**Sample Output:**
```text
Album: 'Summer Trip 2024' — 142 existing assets
Dates in album: ['2024-07-12', '2024-07-13', '2024-07-14']
  2024-07-12: 85 total photos found
  2024-07-13: 130 total photos found
  2024-07-14: 64 total photos found

137 new photos would be added to the album
Batch 1: added 137, failed 0
Done!
```

---

## 🔍 Technical Details & API Endpoints

- **`GET /api/albums/{id}`** — Fetches existing album asset metadata and name.
- **`POST /api/search/metadata`** — Queries metadata search with pagination (`size: 1000`) for date bounds `takenAfter` and `takenBefore`.
- **`PUT /api/albums/{id}/assets`** — Performs bulk additions in batches of 500 IDs.
- Existing items in the album are automatically ignored via set difference (`all_ids_to_add - existing_ids`).
- Non-destructive: Does not delete or overwrite any existing assets or metadata in the album.