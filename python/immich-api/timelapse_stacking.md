# Immich Timelapse Stacking

This script detects potential timelapse sequences in your Immich timeline and groups them into [stacks](https://immich.app/docs/api/create-stack/).

## How it works (V2)

The script supports two detection methods, configurable via `TIMELAPSE_DETECTION_SOURCE`:

1.  **`duplicates` mode (Default)**: Uses Immich's AI-detected duplicate groups as the starting point. This is fast and accurate for high-frame-rate timelapses (bursts, hyperlapses) where frames look similar.
2.  **`search` mode**: Scans your entire library and groups assets by capture time gaps. This is slower but essential for "slow" timelapses (clouds, construction) where frames look too different for AI detection.

After gathering candidates, the script applies advanced statistical filters to eliminate "random similar photos":
- **Regularity**: Checks if frames were captured at consistent intervals (using Coefficient of Variation).
- **Duration**: Ensures the sequence spans a minimum time (to exclude sub-second bursts).
- **Consistency**: Compares file sizes to ensure frames were shot with the same camera/settings.
- **Location (Optional)**: Ensures all frames were shot from the same physical spot.

## Config

Configuration is handled via environment variables in the `.env` file:

- `IMMICH_BASE_URL` - Your Immich server URL.
- `IMMICH_API_KEY` - Your Immich API key.
- `TIMELAPSE_DETECTION_SOURCE` - `duplicates` (AI) or `search` (Time-gap).
- `TIMELAPSE_MIN_FRAMES` - Minimum frames to consider a timelapse (default: `10`).
- `TIMELAPSE_MAX_GAP_SECONDS` - (`search` mode only) Max seconds allowed between frames (default: `60`).
- `TIMELAPSE_MIN_REQD_SPAN_SECONDS` - Minimum total sequence duration in seconds (default: `5`).
- `TIMELAPSE_MAX_CV_GAP` - Max variation in timing intervals as a ratio (default: `0.5` = 50% variation allowed).
- `TIMELAPSE_MAX_CV_SIZE` - Max variation in file sizes as a ratio (default: `0.2` = 20% variation allowed).
- `TIMELAPSE_FILTER_LOCATION` - Set to `true` to require frames to be in the same spot (default: `false`).

## Usage

1.  **Dry Run**: By default, `DRY_RUN = True` is set in the script. Run it to preview candidates and see their CV values:
    ```bash
    python3 timelapse_stacking.py
    ```
2.  **Verify**: Log entries like `cv_gap=0.040 | cv_size=0.020` indicate very consistent sequences.
3.  **Apply**: Set `DRY_RUN = False` inside `timelapse_stacking.py` and run again to create the stacks.

## Notes

- **Timestamps**: Uses `localDateTime` for all interval calculations to match the Immich timeline.
- **Sorting**: Assets are always sorted chronologically before processing.
- **Batching**: Large groups are stacked using the first asset in the sequence as the cover.
