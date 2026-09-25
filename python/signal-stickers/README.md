# Signal Sticker Pack Builder & Curation Tool

Turns a folder of 512x512 sticker images into a validated, emoji-tagged Signal sticker pack.

It clusters near-identical images so you pick the best variation, suggests emojis with a
Vision-Language Model, and gives you a browser page to verify everything before you build
the uploadable `stickers.yaml`.

---

## Quick Start

```bash
# 0. Check your environment (Python, deps, API key, pack folder)
./stickers doctor

# 1. Inventory images, check Signal constraints, find duplicate variations
./stickers scan

# 2. Open the review page, pick the best variation per cluster
./stickers curate          # opens your browser automatically

# 3. Let a VLM suggest emojis for the stickers you kept
./stickers tag

# 4. In the browser: verify emojis, check contrast, click "Save Draft (JSON)",
#    then copy the downloaded file back into your pack folder
cp ~/Downloads/pack_draft.json ./webp/

# 5. Build the manifest
./stickers export

# 6. Preview, then upload
./stickers preview
./stickers upload
```

All commands default to the `./webp` folder. Pass a different one as the first argument:

```bash
./stickers scan ./my_stickers
```

> [!IMPORTANT]
> Step 4 is not optional. The review page is a static file and cannot write to your disk,
> so **every edit you make in the browser exists only in that tab**. Save the draft and copy
> it back before exporting, or your changes are lost when you close the page.

---

## How It Works

The workflow is a loop around one file, `pack_draft.json`:

```
  images on disk
        |
        |  scan          group near-identical images, check Signal constraints
        v
  pack_draft.json  <------ tag        suggest emojis for kept stickers
        |                  ^
        |                  |  review     browser page: pick variations, edit emojis
        |                  |
        |  export
        v
  stickers.yaml  ------->  preview / upload  (signal-sticker-tool)
```

`pack_draft.json` in your pack folder is the single source of truth. `scan` and `tag` write
it, the review page reads it, and `export` turns it into `stickers.yaml`. Losing it means
re-classifying from scratch.

### Workflow Commands

| Command | What it does | API calls |
| :--- | :--- | :--- |
| `./stickers doctor` | Verify Python, dependencies, API key, and pack folder (non-zero exit if anything is missing) | no |
| `./stickers scan` | Inventory images, validate Signal constraints, cluster near-identical variations | no |
| `./stickers curate` | `scan`, then generate and open the review page | no |
| `./stickers tag` | Ask a VLM for emoji suggestions on `keep` stickers, then rebuild the review page | **yes** |
| `./stickers review` | Regenerate and open the review page only | no |
| `./stickers export` | Write `stickers.yaml` from the approved draft | no |
| `./stickers preview` | Render the pack locally with `signal-sticker-tool` | no |
| `./stickers upload` | Encrypt and upload to Signal, printing a share link | no |
| `./stickers help` | Show usage | no |

`./stickers` is a symlink to `run.sh`; both work identically. The runner finds the workspace
`.venv` on its own, so you do not need to activate anything.

---

## Installation

```bash
# From the repository root
.venv/bin/pip install -r python/signal-stickers/requirements.txt
```

This installs `PyYAML`, `Pillow`, and `signal-sticker-tool` (needed for `preview` / `upload`).
The scripts auto-re-exec into the workspace `.venv`, so a bare `python classify_and_build.py`
also works.

Confirm with `./stickers doctor`.

### API Keys

`tag` is the only step that needs a key. Set whichever provider you prefer:

```bash
export OPENROUTER_API_KEY=sk-or-v1-...   # default provider
export GEMINI_API_KEY=...                # or GOOGLE_API_KEY=...
export ANTHROPIC_API_KEY=sk-ant-...
```

With more than one set, OpenRouter wins. Pass `--provider` to be explicit.

---

## The Review Page

`./stickers curate` writes `review.html` into your pack folder. It is self-contained (images
are base64-embedded, so expect roughly 1 MB per sticker) and works offline.

| Control | Purpose |
| :--- | :--- |
| **Filter tabs** | All / Clusters / Needs Review / Kept / Excluded |
| **Sort tabs** | By Cluster, By Emoji, By Filename, By Confidence |
| **Theme tabs** | Light, Dark, White, Black — check contrast on transparent edges |
| **Search** | Match filename, emoji, or cluster id |
| **⚡ Keep Only** | On a clustered card: keeps that one, excludes its siblings |
| **✕ Exclude / ↺ Restore** | Mark a sticker out of (or back into) the pack |
| **Emoji field** | Type up to 3 emojis, or use the `+ Add` dropdown |
| **Save Draft (JSON)** | Download your edits as `pack_draft.json` — **this is the one to use** |
| **Export stickers.yaml** | Download a manifest snapshot (see the note below) |

Cards are outlined by confidence: red below 0.6, orange below 0.8, neutral above.
The **Needs Review** filter collects low-confidence and unassigned stickers.

> [!NOTE]
> The **Export stickers.yaml** button downloads a file to your browser's download folder, which
> `signal-sticker-tool` will not read. To build the manifest in the pack folder, use
> **Save Draft (JSON)**, copy it back over `pack_draft.json`, then run `./stickers export`.

### Getting your edits back into the pack

1. Click **Save Draft (JSON)**.
2. Copy the downloaded `pack_draft.json` into your pack folder, overwriting the old one.
3. Run `./stickers export`.

The page warns before you close it with unsaved changes.

---

## Signal Sticker Requirements

Per the [official Signal guidelines](https://support.signal.org/hc/en-us/articles/360031836512-Stickers#sticker_creator):

| Requirement | Specification |
| :--- | :--- |
| **Dimensions** | Exactly **512 x 512 px** |
| **Max file size** | **300 KB** per sticker |
| **Format** | **PNG** or **WebP** (animated: **APNG** <= 3 s, 30/60 FPS; no GIFs) |
| **Margins** | ~**16 px** transparent margin |
| **Background** | Transparent; add outlines for contrast on light and dark themes |
| **Emoji mapping** | **1 to 3** emojis in `chr`, used for sticker suggestions |
| **Pack limit** | **200** stickers |
| **Cover** | 512 x 512 px PNG or WebP (defaults to the first sticker) |

`scan` reports every violation it finds. Note the actual Signal limit is 200 stickers, and
`export` warns if your manifest exceeds it.

> [!WARNING]
> **Uploaded packs cannot be edited.** Signal gives you no way to change emojis or remove
> stickers after upload. Always review before uploading.

---

## Files

| File | Role |
| :--- | :--- |
| `pack_draft.json` | **Source of truth.** Selection, clusters, emoji suggestions, confidence. |
| `review.html` | Generated review page. Safe to delete; rebuilt by `curate`. |
| `stickers.yaml` | Build output consumed by `signal-sticker-tool`. |
| `classification_cache.json` | Legacy. Migrated into the draft on first run. |

All four live in your **pack folder** (e.g. `./webp/`), not next to the scripts, so multiple
packs can be curated independently. They are gitignored for that reason.

Note that only `keep` stickers with an emoji assignment **and an image still on disk** reach
`stickers.yaml`. `export` reports how many were written, skipped, or left undecided, and
refuses to write an empty manifest.

---

## Command-Line Reference

Prefer `./stickers`. For anything the runner does not wrap, call the Python directly —
`./stickers` passes unrecognized arguments straight through.

### `classify_and_build.py`

```bash
python classify_and_build.py ./webp --scan
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `folder` | *(required)* | Directory containing sticker images |
| `--scan` | off | Inventory, validate, and cluster without API calls |
| `--check-only` | off | Alias for `--scan` |
| `--classify-kept` | off | Classify only stickers marked `keep` |
| `--build-yaml` | off | Write `stickers.yaml` from kept stickers |
| `--title` | keep draft value | Pack title. Omitting it preserves the title in `pack_draft.json`. |
| `--author` | keep draft value | Pack author |
| `--cover` | first sticker | Cover image filename |
| `--provider` | auto-detect | `openrouter`, `gemini`, or `anthropic` |
| `--model` | provider default | e.g. `inclusionai/ling-3.0-flash-vl`, `gemini-2.5-flash` |
| `--out` | `stickers.yaml` | Output filename |
| `--draft` | `pack_draft.json` | Draft state file |
| `--cache` | `classification_cache.json` | Legacy cache, auto-migrated |
| `--workers` | `4` | Parallel VLM requests |

With no action flag, the tool classifies kept stickers and then writes the manifest.

`--dedupe` and `--resume` are accepted but do nothing; clustering always runs and the draft
is always reused.

### `review.py`

```bash
python review.py ./webp
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `folder` | *(required)* | Pack folder |
| `--draft` | `pack_draft.json` | Draft to read |
| `--yaml` | `stickers.yaml` | Manifest to fall back on when no draft exists |

---

## How Classification Works

A perceptual hash (64-bit dHash) is computed for every image, compositing transparency over
neutral grey first so hidden RGB in transparent pixels cannot distort the hash. Images whose
Hamming distance is within a threshold are grouped into connected components and flagged as
variations of one another.

Emojis come from a fixed registry in `emojis.py` (94 entries). Every assignment is validated
against it: 1 to 3 registered emojis, nothing else. Invalid input falls back to `😐` with
confidence `0.0` and is flagged for review rather than being dropped.

Providers are plain `urllib` HTTP calls — no vendor SDKs:

| Provider | Default model | Key |
| :--- | :--- | :--- |
| OpenRouter | `inclusionai/ling-3.0-flash-vl` | `OPENROUTER_API_KEY` |
| Google Gemini | `gemini-2.5-flash` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` |
| Anthropic | `claude-3-7-sonnet-latest` | `ANTHROPIC_API_KEY` |

Each sticker costs one request. Only `keep` stickers without a confident assignment are sent,
so re-running `tag` after new curation is cheap.

---

## Troubleshooting

**`No API key found`** — `tag` needs one of the three environment variables. See
[API Keys](#api-keys).

**`Error: 'signal-sticker-tool' is not installed`** — only affects `preview` / `upload`:

```bash
.venv/bin/pip install signal-sticker-tool
```

**`refusing to write an empty stickers.yaml`** — `export` found no `keep` sticker it could
write. Usually means the draft has not been classified yet, or your saved draft landed in the
wrong folder. Run `./stickers tag`, or check that the `pack_draft.json` you copied back is the
one in your pack folder.

**`tagged sticker(s) are no longer on disk`** — the draft references images you deleted or
moved. They are excluded from the manifest so the upload cannot fail on them. Re-run
`./stickers scan` to prune them from the draft permanently.

**Your review edits vanished** — they only ever existed in the browser tab. Click
**Save Draft (JSON)** before closing.

**`review.html` is huge and slow** — every image is base64-embedded, so roughly 1 MB per
sticker. For large packs, review in batches by pointing at a subset folder.

**No clusters detected** — clustering has a strict distance threshold. Genuinely distinct
expressions will not cluster, which is expected.

**A run left files in a weird state** — `pack_draft.json` and `review.html` are both
regenerable; only deleting the draft loses classification work.

---

## Uploading

### One-time Signal Desktop credentials

`signal-sticker-tool` links against Signal Desktop. To authenticate:

1. Launch Signal Desktop with dev tools:
   ```bash
   signal-desktop --enable-dev-tools
   ```
2. Open DevTools (**Ctrl+Shift+I** / **Cmd+Option+I**) and switch the console context from
   `top` to **Electron Isolated Context**.
3. Read your credentials:
   ```javascript
   window.reduxStore.getState().items.uuid_id    // username
   window.reduxStore.getState().items.password   // password
   ```
4. Authenticate:
   ```bash
   signal-sticker-tool login
   ```

### Upload

```bash
./stickers upload        # or: cd ./webp && signal-sticker-tool upload
```

You get a shareable link like `https://signal.art/addstickers/#pack_id=...&pack_key=...`.

---

## Requirements

Python 3.9+, `PyYAML`, `Pillow`. `signal-sticker-tool` for preview and upload. See
[Signal Sticker Requirements](#signal-sticker-requirements) for image constraints.

## Tests

From the repository root:

```bash
.venv/bin/pytest python/signal-stickers
```

---

## Known Issues

- `--dedupe` and `--resume` are accepted but do nothing. Clustering always runs, and the
  draft is always reused. They exist so old command lines keep working.
- `build_disambiguation_prompt()` and `detect_visual_duplicates()` in
  `classify_and_build.py` are dead code retained only for backwards compatibility.
- The review page cannot write to disk, so browser edits require a manual
  **Save Draft (JSON)** and copy-back. This is inherent to a static page; a local HTTP
  server would remove the step.
- `review.html` embeds every image as base64, so page size grows linearly with the pack.
