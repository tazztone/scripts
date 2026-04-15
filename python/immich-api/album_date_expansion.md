# Immich album date expansion

This script expands an existing Immich album by:

1. Reading all assets already in the album
2. Extracting the unique capture dates from those assets
3. Searching Immich for all photos taken on those same dates
4. Adding any missing photos to the album

Useful when an album was originally built from location-based matches, but you also want photos from the same dates that do not have location metadata.

## Config

Create a `.env` file in the same directory (see `.env.example` or existing `.env`) with the following variables:

- `IMMICH_BASE_URL` – your Immich server, e.g. `http://localhost:2283`
- `IMMICH_API_KEY` – an Immich API key 
- `IMMICH_ALBUM_ID` – target album ID 

In the script:
- `DRY_RUN` – `True` to preview only, `False` to actually add assets


## Run

```bash
python3 album.py
```

## Dry run

With `DRY_RUN = True`, the script only prints:

- Album name
- Dates found in the album
- Total photos found for each date
- How many new photos would be added

No album changes are made.

## Apply changes

Set:

```python
DRY_RUN = False
```

Then run the script again. New assets are added in batches.

## Notes

- Existing album items are skipped automatically
- The script does not remove anything from the album
- Large albums may take a while because results are paginated