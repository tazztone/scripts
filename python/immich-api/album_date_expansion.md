# Immich Album Date Expansion & Update

A Python utility to expand or incrementally update an Immich album by automatically querying the Immich API for all photos taken on the same dates as existing album assets, and batch-adding missing photos (e.g. newly exported RAW edits, unlocated photos, or secondary camera shots).

---

## 🎯 Purpose & Problem Solved

### 🏔️ Real-World Origin & User Story
> **The Alpine Hut Archival Project**:
> "I was hired to deliver a comprehensive photo and video collection of an alpine mountain hut we visited over multiple years. 
> To collect everything, I first used GPS location metadata in Immich to tag all photos taken directly at the hut. From those GPS-tagged photos, I extracted the specific visit dates. Because many photos and videos (e.g. DSLR RAWs, drone shots, action cameras, or edited exports) lacked GPS metadata, I knew that *any photo or video captured on those same days* was also from that location.
> `album_date_expansion.py` automated querying the entire multi-year Immich library for those dates and populating the album. From there, those same dates were fed into our DaVinci Resolve staging tool to assemble the final film and photo album."

### Common Scenarios
1. **Adding Exported RAW Edits / Derivatives**: You edited photos in Lightroom/Capture One/Darktable and uploaded the exports to Immich. Because they retain the original capture dates in EXIF, this script detects the new edits and adds them to your existing album without duplicate effort.
2. **Expanding Location-Based Albums**: When an album was originally built from location search or face tagging, photos taken on the same days without GPS metadata are often missed.
3. **Multi-Camera Event Aggregation**: Bring together all shots from multiple devices across the event days.


### How It Works
1. **Selects Target Album**: Via CLI argument, fuzzy name search, UUID, or interactive menu.
2. **Reads Existing Assets**: Fetches all assets currently in the album.
3. **Extracts Unique Capture Dates**: Identifies all dates (`YYYY-MM-DD`) represented in the album.
4. **Scans the Immich Library**: Queries Immich metadata search for all photos taken on those dates.
5. **Generates a Per-Date Breakdown Table**: Previews library totals, album counts, and new photos found.
6. **Prompts for Confirmation**: Asks before modifying the album (unless `-y`/`--yes` or `-n`/`--dry-run` is specified).
7. **Batch Inserts**: Adds new photos in safe chunks of 500.

---

## 📋 Requirements & Dependencies

- Python 3.8+
- Python packages: `requests`, `python-dotenv`

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Configure your server URL and API key in `.env` (or copy from [.env.example](.env.example)):

```dotenv
IMMICH_BASE_URL=http://localhost:2283
IMMICH_API_KEY=your_api_key_here
IMMICH_ALBUM_ID=86e11802-83db-44d3-bdb6-dcf0e4c0d6ca # Optional default album
```

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `IMMICH_BASE_URL` | Yes | Base URL of your Immich server instance | `http://localhost:2283` |
| `IMMICH_API_KEY` | Yes | API key from Immich Account Settings | `v8...` |
| `IMMICH_ALBUM_ID` | Optional | Default album UUID to suggest when no argument is given | `86e11802-83db-44d3...` |

---

## 🚀 Usage

### 1. Interactive Selection (Recommended)
Run without arguments to launch the interactive album picker:

```bash
python3 album_date_expansion.py
```

```text
Select an album to expand / update:
  [ 1] Summer Trip 2024 (142 assets)
  [ 2] City Architecture (48 assets)
  [ 3] ⏱ Timelapse Stacks (35 assets)

Enter album number or name to search: 1
```

### 2. Targeting an Album by Name or UUID
Pass the album name (exact or partial) or UUID directly:

```bash
# By name (case-insensitive)
python3 album_date_expansion.py "Summer Trip 2024"

# By UUID
python3 album_date_expansion.py -a 86e11802-83db-44d3-bdb6-dcf0e4c0d6ca
```

### 3. Preview Mode (Dry Run)
Inspect what would be added without making any changes to the album:

```bash
python3 album_date_expansion.py "Summer Trip 2024" --dry-run
```

**Sample Output:**
```text
Fetching assets for album: 'Summer Trip 2024'...
Found 142 existing asset(s) in album 'Summer Trip 2024'.

Scanning Immich library for 3 unique date(s):
  - 2024-07-12
  - 2024-07-13
  - 2024-07-14

Querying library...

────────────────────────────────────────────────────────────
Date           Library Total    In Album       New to Add  
────────────────────────────────────────────────────────────
2024-07-12     85               42             +43         
2024-07-13     130              60             +70         
2024-07-14     64               40             +24         
────────────────────────────────────────────────────────────
TOTALS         279              142            +137        
────────────────────────────────────────────────────────────

Found 137 new photo(s) available to add to 'Summer Trip 2024'.

[DRY RUN] No changes were made to the album. Run without -n/--dry-run to apply.
```

### 4. Non-Interactive / Scripting (`--yes`)
Skip the confirmation prompt to run in automated scripts:

```bash
python3 album_date_expansion.py "Summer Trip 2024" --yes
```

### 5. List All Albums
Quickly view all albums and their IDs on your Immich server:

```bash
python3 album_date_expansion.py --list
```

---

## 🛠️ CLI Options Reference

| Option | Flag | Description |
| :--- | :--- | :--- |
| `album` | Positional | Album name (fuzzy/exact match) or UUID. |
| `--album-id` | `-a` | Explicit album UUID. |
| `--verbose` | `-v` | Display all new filenames and timestamps without truncating to 30. |
| `--dry-run` | `-n` | Preview matching photos, breakdown table, and filenames without modifying album. |
| `--yes` | `-y` | Automatically confirm and apply changes without prompt. |
| `--list` | *(None)* | List all albums on the server and exit. |
| `--help` | `-h` | Display command-line help and usage. |

---

## 🔍 Technical Details & API Endpoints

- **`GET /api/albums`** — Fetches album names, IDs, and asset counts for interactive selection.
- **`GET /api/albums/{id}`** — Fetches existing asset lists and capture timestamps.
- **`POST /api/search/metadata`** — Queries metadata search with pagination (`size: 1000`) for date bounds `takenAfter` and `takenBefore`.
- **`PUT /api/albums/{id}/assets`** — Performs bulk additions in batches of 500 IDs.
- **Idempotent & Non-Destructive**: Does not duplicate assets already in the album and never deletes or overwrites existing photos.