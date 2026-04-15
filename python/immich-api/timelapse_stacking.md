# Immich Timelapse Stacker

This script provides an interactive terminal wizard to detect potential timelapse sequences in your Immich timeline and group them into [stacks](https://immich.app/docs/api/create-stack/).

## How it works

The script runs as a guided CLI wizard with four main steps:

### 1. Tune Filters
You can interactively adjust the detection parameters to fit your library:
- **Detection Source**: Choose between `duplicates` (AI clusters, fast) and `search` (Time-gap scanning, slow).
- **MIN_FRAMES**: Minimum assets in a sequence.
- **MAX_CV_GAP**: Capture regularity (0.35 means 35% variation allowed).
- **MAX_CV_SIZE**: File size consistency (0.10 means 10% variation allowed).
- **MIN_SPAN**: Minimum total duration of the sequence in seconds.

### 2. Verify Candidates
Once candidates are found, the wizard offers to create **temporary verification albums** in Immich. These albums are prefixed with `_VERIFY_` and are sorted "worst-first" (highest `cv_gap`) so you review the most suspicious ones first.

### 3. Review in Immich
If you choose to verify, the script will automatically attempt to open your browser to the Immich albums page. You can visually inspect the frames side-by-side to confirm they belong in a stack.

### 4. Finalize
Choose to:
- **Stack all**: Converts all identified candidates into Immich stacks. A local `timelapse_stacking_last_run.json` record is saved.
- **Restart**: Go back to Step 1 to re-tune filters if you saw false positives.
- **Abort**: Clean up verification albums and exit without making changes.

### 5. Album Creation (Optional)
After successful stacking, the wizard offers to create or update a permanent album (default: **"⏱ Timelapse Stacks"**). You can choose between two modes:
- **Index Mode (Recommended)**: Adds only the **cover frame** (the first photo) of every timelapse. This creates a clean, browsable gallery.
- **Collection Mode**: Adds **every single frame** from all timelapses into the album.

### 6. Undo / Re-run (Optional)
If you stacked sequences and later realized your filters were too loose, you can unstack the last run. Restart the script and choose **[U] Unstack last run**.
1. The script reads `timelapse_stacking_last_run.json` and deletes the stacks it created.
2. It will then ask if you want to **automatically delete the permanent album** as well.
3. This leaves your library exactly as it was before, allowing you to tune filters and try again immediately.


## Config

Initial defaults are handled via environment variables in your `.env` file:

- `IMMICH_BASE_URL` - Your Immich server URL.
- `IMMICH_API_KEY` - Your Immich API key.
- `TIMELAPSE_DETECTION_SOURCE` - Default mode (`duplicates` or `search`).
- `TIMELAPSE_MIN_FRAMES` - Default min frames (default: `10`).
- `TIMELAPSE_MAX_GAP_SECONDS` - Default search gap (default: `60`).
- `TIMELAPSE_MIN_REQD_SPAN_SECONDS` - Default min span (default: `15`).
- `TIMELAPSE_MAX_CV_GAP` - Max variation in timing intervals as a ratio (default: `0.35`).
- `TIMELAPSE_MAX_CV_SIZE` - Max variation in file sizes as a ratio (default: `0.10`).
- `TIMELAPSE_FILTER_LOCATION` - Set to `true` to require frames to be in the same spot by default (default: `false`).

## Usage

Run the script from the project directory:

```bash
cd python/immich-api
python3 timelapse_stacking.py
```

Follow the prompts in your terminal. The script will handle the browser opening and the temporary album cleanup automatically.

## Notes

- **Auto-Cleanup**: Verification albums are automatically deleted before you perform the final stacking or before the script exits on abort.
- **Browser**: If your terminal environment doesn't support a browser, the `webbrowser` call will fail silently; you can just open the UI manually.
- **Timestamps**: Uses `localDateTime` for all interval calculations to match the Immich timeline.
