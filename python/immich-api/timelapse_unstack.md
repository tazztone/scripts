# Immich Timelapse Unstack Utility

A Python utility to inspect and delete stacks in your Immich library (e.g. to revert bulk automated stacking or remove large timelapse stacks).

---

## 🎯 Purpose & Problem Solved

If stacks were created with suboptimal filter criteria or you wish to dissolve stacks above a certain frame threshold, this script allows you to query all stacks in Immich, filter for large sequences (such as timelapses or bursts), inspect them, and delete the stack groupings safely without deleting the underlying photo assets.

This script:
1. **Fetches all stacks** from your Immich server.
2. **Filters stacks** by frame count (`MIN_FRAMES >= 10` by default).
3. **Prints an indexed breakdown** of stack IDs, frame counts, and primary asset IDs.
4. **Supports Dry Run mode** to preview which stacks would be deleted.
5. **Prompts for confirmation** before issuing deletion requests.

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

Set environment variables in `.env` (or `.env.example`):

```dotenv
IMMICH_BASE_URL=http://localhost:2283
IMMICH_API_KEY=your_api_key_here
```

### Script Options

Inside [timelapse_unstack.py](file:///home/tazztone/_coding/scripts/python/immich-api/timelapse_unstack.py):

| Option | Default | Description |
| :--- | :--- | :--- |
| `MIN_FRAMES` | `10` | Minimum frame count filter. Stacks with fewer frames are ignored. |
| `DRY_RUN` | `False` | When `True`, only previews stacks to be deleted without issuing delete requests. |

---

## 🚀 Usage

### 1. Preview (Dry Run)

Set `DRY_RUN = True` in [timelapse_unstack.py](file:///home/tazztone/_coding/scripts/python/immich-api/timelapse_unstack.py) and run:

```bash
python3 timelapse_unstack.py
```

**Sample Output:**
```text
Fetching all stacks...
Found 150 stacks total
Stacks with 10+ frames: 3

  [  1] id=30e22c03-6959-4eb8-8285-2e7f0e9e8525  frames=45  primary=851e52ea-e3ac-4a39-a7b3-9acb11eac7dd
  [  2] id=4a91f802-12aa-4dd3-99b1-3cf0e4c0d123  frames=28  primary=19a24e31-0865-446a-8f48-292af3fbb11d
  [  3] id=8e7b1a20-55cc-4ee1-b992-8ac10e8f9901  frames=110 primary=6739e700-d04b-4976-8579-abf0fadece8d

DRY RUN — 3 stacks would be deleted. Set DRY_RUN = False to apply.
```

### 2. Execute Deletion

Set `DRY_RUN = False` in [timelapse_unstack.py](file:///home/tazztone/_coding/scripts/python/immich-api/timelapse_unstack.py) and run:

```bash
python3 timelapse_unstack.py
```

You will be prompted:
```text
Delete all 3 stacks? [y/n]: y
  [  1] ✓  45f   30e22c03-6959-4eb8-8285-2e7f0e9e8525
  [  2] ✓  28f   4a91f802-12aa-4dd3-99b1-3cf0e4c0d123
  [  3] ✓  110f  8e7b1a20-55cc-4ee1-b992-8ac10e8f9901
Done!
```

---

## 🔍 Technical Details & API Endpoints

- **`GET /api/stacks`** — Retrieves all stack metadata including asset lists.
- **`DELETE /api/stacks/{id}`** — Deletes the stack association entity (returns status `204 No Content`).
- **Non-destructive to media**: Deleting a stack in Immich only un-groups the assets; individual photo assets and EXIF data remain intact in your timeline.
