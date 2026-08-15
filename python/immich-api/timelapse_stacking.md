# Immich Timelapse Stacker

An interactive terminal wizard to automatically detect timelapse photo sequences in your Immich library, verify them visually using temporary review albums, and group them into [Immich Stacks](https://immich.app/docs/api/create-stack/).

---

## 🎯 Purpose & Problem Solved

Burst shots and timelapse sequences can quickly clutter your Immich timeline with hundreds of nearly identical frames. Immich supports stacking assets together under a single cover frame, but detecting and grouping thousands of timelapse frames manually is impractical.

This tool:
1. **Scans your library** for candidate sequences based on timestamp intervals, frame counts, timing regularity, file size consistency, and optional GPS proximity.
2. **Creates temporary verification albums** (sorted worst-first) and opens your browser so you can visually verify candidate groups before applying changes.
3. **Stacks all confirmed sequences** via the Immich Stacks API and records a rollback log (`timelapse_stacking_last_run.json`).
4. **Optionally creates an album** of your timelapses in either **Index Mode** (covers only) or **Collection Mode** (all frames).
5. **Provides built-in rollback / undo** to unstack a previous run and clean up albums at any time.

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

Set initial defaults in a `.env` file located in `python/immich-api/` (see [.env.example](file:///home/tazztone/_coding/scripts/python/immich-api/.env.example)):

```dotenv
IMMICH_API_KEY=your_api_key_here
IMMICH_BASE_URL=http://localhost:2283
IMMICH_ALBUM_ID=86e11802-83db-44d3-bdb6-dcf0e4c0d6ca
TIMELAPSE_MIN_FRAMES=10
TIMELAPSE_MAX_GAP_SECONDS=60
TIMELAPSE_DETECTION_SOURCE=duplicates
TIMELAPSE_MIN_REQD_SPAN_SECONDS=5
TIMELAPSE_MAX_CV_GAP=0.35
TIMELAPSE_MAX_CV_SIZE=0.10
TIMELAPSE_FILTER_LOCATION=false
```

### Configuration Options

| Variable | Default | Description |
| :--- | :--- | :--- |
| `IMMICH_BASE_URL` | `http://localhost:2283` | URL of your Immich server instance. |
| `IMMICH_API_KEY` | *(None)* | Immich API key (created in Immich Web $\rightarrow$ Account Settings $\rightarrow$ API Keys). |
| `TIMELAPSE_DETECTION_SOURCE` | `duplicates` | Candidate detection strategy: `duplicates` (uses Immich AI duplicate clusters, fast) or `search` (scans entire library via metadata search, slower). |
| `TIMELAPSE_MIN_FRAMES` | `10` | Minimum number of consecutive frames required to form a timelapse sequence. |
| `TIMELAPSE_MAX_GAP_SECONDS` | `60` | Maximum allowable time delta (in seconds) between two consecutive frames in `search` mode. |
| `TIMELAPSE_MIN_REQD_SPAN_SECONDS`| `5` | Minimum total sequence duration (last frame time minus first frame time) in seconds. |
| `TIMELAPSE_MAX_CV_GAP` | `0.35` | Maximum Coefficient of Variation for timing intervals ($\sigma / \mu$). Lower values enforce stricter interval consistency. |
| `TIMELAPSE_MAX_CV_SIZE` | `0.10` | Maximum Coefficient of Variation for file sizes ($\sigma / \mu$). Lower values enforce stricter file size consistency. |
| `TIMELAPSE_FILTER_LOCATION` | `false` | When `true`, requires all frames in a candidate sequence to share the same GPS coordinates (within 0.0005°). |

---

## 🔄 Interactive Wizard Workflow

Run the script to launch the interactive terminal wizard:

```bash
python3 timelapse_stacking.py
```

```
┌──────────────────────────────────────────────────────────┐
│                   TIMELAPSE STACKER                      │
│                                                          │
│  [1] Tune Filters & Detect Candidates                   │
│  [2] Create Worst-First Verification Albums             │
│  [3] Visual Review in Web Browser                        │
│  [4] Finalize: Stack Candidates & Write JSON Log         │
│  [5] (Optional) Create / Update Stacks Album             │
│  [U] (Rollback) Unstack Last Run                         │
└──────────────────────────────────────────────────────────┘
```

### 1. Tune Filters
Review and interactively adjust detection parameters before scanning. You can alter thresholds (minimum frames, interval variation, detection mode) on the fly.

### 2. Verify Candidates (Worst-First)
When candidate sequences are detected, the wizard can create temporary review albums in Immich named `_VERIFY_#_<details>`.
- Sequences with higher `cv_gap` (most irregular timing) are ranked first so you can inspect edge cases immediately.
- The wizard automatically opens your default web browser to the Immich Albums page.

### 3. Finalize & Stack
- **Stack All**: Converts verified candidate sequences into Immich Stacks using `POST /api/stacks`.
- The run details (stack IDs and asset IDs) are saved to `timelapse_stacking_last_run.json`.
- **Restart**: Adjust filter parameters and re-scan without stacking.
- **Abort**: Cleans up all `_VERIFY_` temporary albums and exits cleanly.

### 4. Album Generation (Optional)
After stacking, you can automatically add the timelapses to an album (default name: `⏱ Timelapse Stacks`):
- **Index Mode (Recommended)**: Adds only the **cover photo** (first frame) of each sequence. Gives a clean overview album without clutter.
- **Collection Mode**: Adds **every frame** from all sequences into the album.

### 5. Rollback / Undo
If you ever need to revert a stacking run:
1. Start the script and choose `[U] Unstack last run`.
2. It reads `timelapse_stacking_last_run.json`, deletes the created stacks from Immich, and prompts to delete the created album.

---

## 🔍 Technical Details & API Endpoints

- **`GET /api/duplicates`** — Queries Immich machine-learning duplicate / burst clusters (used in `duplicates` mode).
- **`POST /api/search/metadata`** — Full-library metadata search with pagination (used in `search` mode).
- **`POST /api/stacks`** — Creates stack entities with primary assets (`POST /api/stacks` with `primaryAssetId` and `assetIds`).
- **`DELETE /api/stacks/{id}`** — Deletes stack groupings without deleting the underlying photo assets.
- **`POST /api/albums`** & **`PUT /api/albums/{id}/assets`** — Manages verification albums and the final curated album.
- **`DELETE /api/albums/{id}`** — Automatically cleans up temporary `_VERIFY_` albums upon completion or abort.

---

## 📁 Artifacts

- **[timelapse_stacking_last_run.json](file:///home/tazztone/_coding/scripts/python/immich-api/timelapse_stacking_last_run.json)**: Contains the JSON array of `{ "stack_id": "...", "asset_ids": [...] }` from the most recent run, used for rollback or downstream processing with [create_album_from_log.py](file:///home/tazztone/_coding/scripts/python/immich-api/create_album_from_log.py).
