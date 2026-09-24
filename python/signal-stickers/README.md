# Signal Sticker Pack Automation & Review Tool

Automates emoji classification for custom Signal stickers using Vision-Language Models (VLMs), validates strict Signal sticker requirements, and provides an interactive browser-based review tool before final encryption and upload.

---

## Features

- **Multi-Provider VLM Classification**:
  - **OpenRouter** (Default: `inclusionai/ling-3.0-flash-vl`)
  - **Google Gemini** (`gemini-2.5-flash`, `gemini-2.0-pro`, etc.)
  - **Anthropic Claude** (`claude-3-7-sonnet-latest`, `claude-3-5-sonnet`)
  - Zero heavy third-party SDK dependencies needed (uses standard Python HTTP requests).
- **Signal Constraint Verification**:
  - Exact 512 x 512 px dimension check.
  - File size (< 300 KB limit).
  - Format validation (PNG / WebP / APNG; no GIFs).
  - Pack capacity check (1 to 200 stickers maximum).
  - Transparency & margin validation.
- **Multi-Emoji Tagging & Nuanced Search**:
  - Assigns 1 to 3 emojis per sticker in `chr` (e.g., primary emotion + secondary nuance tags like `🤔🤨`), enhancing discoverability in Signal.
- **Smart Disambiguation & Deduplication (`--dedupe`)**:
  - Sends groups of stickers sharing the same primary emoji together in a comparative multi-image VLM prompt.
  - Honest nuance detection: differentiates subtle facial variations (smirk, raised brow, squint) while explicitly flagging truly identical ComfyUI variations as `redundant_of` rather than forcing ill-fitting emojis.
- **Fast Perceptual Difference Hashing (Zero Extra ML Dependencies)**:
  - 64-bit dHash calculates pairwise Hamming distances across generation batches to identify visually near-identical frames for user-driven pruning.
- **Interactive Visual Review Page**:
  - **Multi-Emoji Bar**: Directly edit or append emojis (up to 3) per card.
  - **⚡ Keep Only One-Click Action**: When reviewing a cluster of duplicate variations, click "⚡ Keep Only" on the best sticker to automatically exclude all other redundant copies in that emoji group.
  - **Sort by Emoji**: Group matching stickers side-by-side to easily compare and resolve duplicate emoji assignments.
  - **Live Duplicate Detection**: Identifies stickers with colliding emojis with orange highlights and count badges (`9x 🤔`).
  - **Mark for Deletion / Exclusion**: Exclude individual stickers with an `✕ Exclude` button (excluded stickers are omitted from `stickers.yaml`, with a helper to copy `rm` commands for disk cleanup).
  - **Theme Contrast Checker**: Live preview against Signal Light Theme, Dark Theme, Pure White, and Pure Black.
  - **Live Search & Filters**: Search by filename or emoji, filter by Duplicates, Needs Review (< 0.8), or Deleted stickers.
  - **One-Click Export**: Save the sanitized, updated `stickers.yaml`.
- **Full Resumption**:
  - `classification_cache.json` persists progress so interrupted runs can be resumed instantly with `--resume`.

---

## Signal Sticker Specifications

According to the [official Signal Sticker guidelines](https://support.signal.org/hc/en-us/articles/360031836512-Stickers#sticker_creator):

| Requirement | Specification |
| :--- | :--- |
| **Dimensions** | Exactly **512 x 512 px** |
| **Max File Size** | Maximum **300 KB** per sticker |
| **Image Format** | Separate **PNG** or **WebP** file (animated: **APNG** <= 3 seconds, 30/60 FPS, no GIFs) |
| **Margins** | **~16 px transparent margin** around each sticker |
| **Background** | Transparent background (add outlines if needed for contrast on both light and dark themes) |
| **Emoji Mapping** | **1 to 3 emojis** per sticker in `chr` (Signal uses these for sticker suggestions when typing emojis) |
| **Pack Limit** | Maximum **200 stickers** per pack |
| **Cover Image** | 512 x 512 px PNG or WebP (defaults to first sticker in pack) |

> [!WARNING]
> **Sticker pack uploads to Signal are irreversible!** Sticker packs cannot be edited or modified after upload. Always review emojis and check visual contrast in both light and dark themes before uploading.

---

## Installation

```bash
pip install -r requirements.txt
```

Set your preferred provider API key:

```bash
# OpenRouter (Default model: inclusionai/ling-3.0-flash-vl)
export OPENROUTER_API_KEY=sk-or-v1-...

# Or Google Gemini
export GEMINI_API_KEY=...
# (or GOOGLE_API_KEY=...)

# Or Anthropic Claude
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Signal Desktop Credentials (One-Time Setup)

To upload packs via `signal-sticker-tool`, link Signal Desktop on your computer, then extract your credentials:

1. Launch Signal Desktop with developer tools enabled:
   ```bash
   signal-desktop --enable-dev-tools
   ```
2. Open DevTools (**Ctrl+Shift+I** or **Cmd+Option+I**) and switch the JavaScript console context dropdown from `top` to **"Electron Isolated Context"**.
3. Run the following commands:
   ```javascript
   window.reduxStore.getState().items.uuid_id    // -> USERNAME
   window.reduxStore.getState().items.password   // -> PASSWORD
   ```
4. Authenticate `signal-sticker-tool`:
   ```bash
   signal-sticker-tool login
   ```

---

## Workflow

### 1. Check Constraints and Classify

Run the classifier on your sticker directory (e.g. `./webp`):

```bash
# OpenRouter with default inclusionai/ling-3.0-flash-vl
python classify_and_build.py ./webp --title "Grimassen" --author "tazztone"

# Using a different provider or model:
python classify_and_build.py ./webp --provider gemini --model gemini-2.5-flash
python classify_and_build.py ./webp --provider openrouter --model inclusionai/ling-3.0-flash-vl

# Run comparative disambiguation on duplicate emoji clusters:
python classify_and_build.py ./webp --dedupe

# Just check compliance & perceptual visual variations without calling VLM APIs:
python classify_and_build.py ./webp --check-only
```

### 2. Review and Adjust Emojis in Browser

Open the interactive review interface:

```bash
python review.py ./webp
```

This generates `webp/review.html`. Open it in any browser:
- **Keep Best Variation**: Click **`⚡ Keep Only`** in a duplicate cluster to keep that image and mark all other identical/redundant variations for exclusion with one click.
- **Sort by Emoji**: Group duplicates side-by-side to review similar expressions and differentiate them.
- **Filter Duplicates**: Click the **Duplicates** filter tab to isolate only colliding stickers.
- **Multi-Emoji Editing**: Type or select up to 3 emojis in the card's emoji bar.
- **Exclude / Delete**: Click **`✕ Exclude`** on any card you do not want in your pack. Excluded stickers will not be included in the exported `stickers.yaml`.
- **Test Contrast**: Toggle **Light**, **Dark**, **White BG**, and **Black BG** to ensure transparent stickers look sharp.
- **Export**: Click **Export stickers.yaml** to save your verified pack manifest.

### 3. Preview Pack

```bash
cd webp && signal-sticker-tool preview
```

### 4. Upload Pack to Signal

```bash
cd webp && signal-sticker-tool upload
```

The tool will upload the encrypted pack to Signal and output your shareable link (e.g., `https://signal.art/addstickers/#pack_id=...&pack_key=...`).

---

## CLI Options

### `classify_and_build.py`

| Flag | Default | Description |
| :--- | :--- | :--- |
| `folder` | *(required)* | Path to directory containing sticker images |
| `--title` | `"Grimassen"` | Sticker pack title shown in Signal |
| `--author` | `"tazztone"` | Artist / Author name |
| `--cover` | First sticker | Cover image filename |
| `--provider` | Auto-detect | `openrouter`, `gemini`, or `anthropic` |
| `--model` | Provider default | Model slug (`inclusionai/ling-3.0-flash-vl`, `gemini-2.5-flash`, etc.) |
| `--out` | `"stickers.yaml"` | Output YAML file name |
| `--cache` | `"classification_cache.json"` | Cache file path |
| `--workers` | `4` | Concurrency worker threads |
| `--resume` | `False` | Resume skipping cached stickers |
| `--dedupe` | `False` | Run multi-image comparative disambiguation on duplicate clusters |
| `--detect-visual-dupes` | `False` | Detect near-identical visual frames using perceptual dHash |
| `--check-only` | `False` | Validate constraints and visual hashes without API calls |


### `review.py`

| Flag | Default | Description |
| :--- | :--- | :--- |
| `folder` | *(required)* | Path to directory with stickers & `stickers.yaml` |
| `--yaml` | `"stickers.yaml"` | Manifest file name |
| `--cache` | `"classification_cache.json"` | Cache file to load confidence scores |
