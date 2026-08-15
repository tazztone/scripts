# Immich API Utilities

A collection of Python automation scripts and CLI utilities interacting with the [Immich REST API](https://immich.app/docs/api/) for album management, timelapse detection, stacking, and bulk stack maintenance.

---

## 📂 Scripts & Documentation

| Script | Documentation | Description |
| :--- | :--- | :--- |
| [`timelapse_stacking.py`](timelapse_stacking.py) | [**`timelapse_stacking.md`**](timelapse_stacking.md) | Interactive terminal wizard to detect timelapse sequences, visually verify them in browser via temporary albums, and group them into Immich Stacks. |
| [`create_album_from_log.py`](create_album_from_log.py) | [**`create_album_from_log.md`**](create_album_from_log.md) | Populates or updates an Immich album from a `timelapse_stacking_last_run.json` log in Index Mode (covers only) or Collection Mode (all frames). |
| [`timelapse_unstack.py`](timelapse_unstack.py) | [**`timelapse_unstack.md`**](timelapse_unstack.md) | Lists and deletes Immich stacks by frame threshold (`MIN_FRAMES`) with dry-run support and interactive confirmation. |
| [`album_date_expansion.py`](album_date_expansion.py) | [**`album_date_expansion.md`**](album_date_expansion.md) | Expands or updates an album with all photos matching existing asset dates (e.g. newly exported RAW edits, unlocated photos) with interactive album picker. |

---

## 📋 Prerequisites & Installation

- Python 3.8+
- Dependencies: `requests`, `python-dotenv`

Install requirements:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration

Copy the template [.env.example](.env.example) to `.env`:

```bash
cp .env.example .env
```

Configure your server URL and API key in `.env`:

```dotenv
IMMICH_BASE_URL=http://localhost:2283
IMMICH_API_KEY=your_api_key_here
IMMICH_ALBUM_ID=your_album_uuid_here

# Timelapse Stacking Defaults
TIMELAPSE_DETECTION_SOURCE=duplicates
TIMELAPSE_MIN_FRAMES=10
TIMELAPSE_MAX_GAP_SECONDS=60
TIMELAPSE_MIN_REQD_SPAN_SECONDS=5
TIMELAPSE_MAX_CV_GAP=0.35
TIMELAPSE_MAX_CV_SIZE=0.10
TIMELAPSE_FILTER_LOCATION=false
```

---

## 🚀 Quick Start

### 1. Timelapse Stacking Wizard
Run the interactive wizard:
```bash
python3 timelapse_stacking.py
```

### 2. Generate Album from Stacking Log
Build an index or collection album from a previous run:
```bash
python3 create_album_from_log.py
```

### 3. Remove / Prune Stacks
Inspect and delete large stacks:
```bash
python3 timelapse_unstack.py
```

### 4. Expand Album by Date
Add missing photos from the same days to an album:
```bash
python3 album_date_expansion.py
```

---

## 🛡️ Safety & Non-Destructive Design

- **Dry-run flags**: Supported across scripts to verify operations before executing changes.
- **Media Preservation**: Stacking and unstacking operations only alter metadata relationships in Immich; underlying photo assets are never deleted.
- **Rollback Log**: `timelapse_stacking.py` generates `timelapse_stacking_last_run.json` to enable automated one-click rollback.
