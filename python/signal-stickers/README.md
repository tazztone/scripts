# Signal Sticker Pack Builder & Curation Tool

Turns a folder of 512x512 sticker images into a validated, emoji-tagged Signal sticker pack.

It clusters near-identical images so you pick the best variation, suggests emojis with a
Vision-Language Model, and gives you a browser page to verify everything before you build
the uploadable `stickers.yaml`.

---

## Quick Start

Prefer guidance? `./stickers wizard ./my_pack` walks the steps below one by
one (same gates; quit anytime with Ctrl-C and re-run to resume).

```bash
# 0. Check the core environment (add a folder for pack preflight)
./stickers doctor ./my_pack

# 1. Inventory images, hard-gate check, group visually similar candidates
./stickers scan ./my_pack

# 2. Let OpenRouter suggest one emoji for kept stickers lacking a final pick
#    (optional; manual emoji selection avoids needing an API key)
./stickers tag ./my_pack

# 3. Open the review page (loopback direct-save; opens automatically).
#    If you already have a review server running, restart it and reload
#    after tagging so the page is not stale.
./stickers curate ./my_pack --serve

# 4. In the browser: resolve Undecided, set exactly one emoji per kept sticker,
#    set title/author/cover, click Approve Pack, then Save.
#    With --serve the Save button writes pack_draft.json directly.
#    Static fallback: Download draft and copy it over pack_draft.json.

# 5. Approve and build. Approval is one gate with two equivalent entries:
#    browser Approve Pack + Save (server re-validates and persists it), or
#    CLI approval for non-browser flows. Only one is needed.
#    No confidence-threshold bypass.
./stickers approve ./my_pack --title "My Pack" --author "me"
./stickers export ./my_pack

# 6. Check upload readiness, preview, then upload
#    (confirmation required; --yes for scripts)
./stickers doctor --upload ./my_pack
./stickers preview ./my_pack
./stickers upload ./my_pack
```

A pack `<folder>` is required for every pack action; nothing defaults to a bundled
pack. From the repo root use `python/signal-stickers/stickers <action> <folder>`;
inside `python/signal-stickers` use `./stickers <action> <folder>`.

---

## Preparing images

`scan` deliberately rejects rather than silently fixes: images must already be
512×512 PNG/WebP (or animated APNG), ≤300 KB each. If your source files are
anything else, normalize them into a **new** folder first — the command below
never touches the source folder:

```bash
mkdir ./my_pack
.venv/bin/python - <<'PY'
from pathlib import Path
from PIL import Image, ImageOps

src = Path("./input_images")   # your files; never modified
dst = Path("./my_pack")        # normalized pack folder
dst.mkdir(exist_ok=True)

for p in sorted(src.iterdir()):
    if p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
        print(f"SKIP (not an image): {p.name}")
        continue
    try:
        im = Image.open(p).convert("RGBA")
    except Exception as e:  # corrupt/unsupported files fail closed
        print(f"SKIP (unreadable): {p.name}: {e}")
        continue
    im = ImageOps.contain(im, (512, 512))  # keep aspect ratio; never stretched
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    canvas.paste(im, ((512 - im.width) // 2, (512 - im.height) // 2), im)
    out = dst / (p.stem + ".png")
    canvas.save(out)
    print(f"{p.name} -> {out.name}")
PY
./stickers scan ./my_pack
```

Caveats:

- Animation is **not** preserved (only a still frame is taken). Animated
  stickers must be prepared as APNG (≤3 s) by hand.
- `scan` still reports oversize files (>300 KB); re-export those at higher
  compression and re-scan.
- Every conversion is printed; skipped files are reported, never silently dropped.
- The output folder then goes through the normal workflow below, including
  human review — normalization is not approval.

---

## How It Works

The workflow is a loop around one file, `pack_draft.json`:

```
  images on disk
        |
        |  scan          group visually similar candidates, hard-gate check
        v
  pack_draft.json  <------ tag        OpenRouter suggests one emoji per kept sticker
        |                  ^
        |                  |  review     browser: resolve Undecided, one emoji, title/author/cover
        |                  |  approve    human gate for the current revision
        |  export (preflight + receipt)
        v
  stickers.yaml (+ receipt)  ------->  preview / upload  (re-verify, then tool)
```

`pack_draft.json` (schema v3) in your pack folder is the sole source of truth. `scan`
and `tag` write it, the review page reads/writes it, `approve` gates it, and `export`
turns it into `stickers.yaml` + receipt. `preview`/`upload` rebuild or verify the
manifest against the current draft and hashes immediately before use.

### Workflow Commands

| Command | What it does | API calls |
| :--- | :--- | :--- |
| `./stickers doctor [--upload] [<folder>]` | Core env/capability check; `--upload` also requires the uploader + Signal login; with folder also runs pack preflight | no |
| `./stickers scan <folder>` | Inventory, hard-gate report, cluster similar candidates | no |
| `./stickers tag <folder>` | OpenRouter suggestions for `keep` stickers lacking final emoji | **yes** |
| `./stickers curate <folder> [--serve]` | `scan`, then generate/open the review page | no |
| `./stickers review <folder> [--serve]` | Regenerate/open the review page only | no |
| `./stickers approve <folder>` | Human approval for the current revision | no |
| `./stickers preflight <folder>` | Strict export/upload preflight only | no |
| `./stickers export <folder>` | Preflight + write `stickers.yaml` + receipt | no |
| `./stickers preview <folder>` | Re-verify receipt + render locally with `signal-sticker-tool` | no |
| `./stickers upload <folder> [--yes]` | Re-verify + confirm + upload to Signal | no |
| `./stickers login` / `./stickers logout` | Authenticate / de-authenticate `signal-sticker-tool` | no |
| `./stickers url <folder>` | Reprint the share URL of an uploaded pack | no |
| `./stickers wizard <folder>` | Guided walkthrough (same steps and gates, upload still confirmed) | mixed |
| `./stickers help` | Show usage (also shown with no arguments) | no |

`./stickers` is a symlink to `run.sh`; both work identically. The runner finds the workspace
`.venv` on its own, so you do not need to activate anything.

---

## Installation

```bash
# From the repository root — core (scan/curate/tag/export/review/approve)
.venv/bin/python -m pip install -r python/signal-stickers/requirements.txt
# or: uv pip install -r python/signal-stickers/requirements.txt

# Only for preview/upload (pinned; see the comment in the file before upgrading)
.venv/bin/python -m pip install -r python/signal-stickers/requirements-upload.txt
```

The scripts auto-re-exec into the workspace `.venv`, so a bare
`python classify_and_build.py` also works. Confirm with `./stickers doctor`.

### API Keys

OpenRouter-only. `tag` is the only step that needs a key:

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
```

Model override: `--model <slug>` (default `inclusionai/ling-3.0-flash-vl`).
Provider failures leave entries unresolved/error — never `😐` fallback tags.

---

## The Review Page

`./stickers curate` writes `review.html` into your pack folder. It is self-contained (images
are base64-embedded, so expect roughly 1 MB per sticker) and works offline.

| Control | Purpose |
| :--- | :--- |
| **Filter tabs** | All / Clusters / Needs Review / Kept / Undecided / Excluded |
| **Sort tabs** | By Cluster, By Emoji, By Filename, By Confidence |
| **Theme tabs** | Light, Dark, White, Black — check contrast on transparent edges |
| **Search** | Match filename, emoji, or cluster id |
| **⚡ Keep Only** | On a clustered card: keeps that one, explicitly excludes siblings |
| **Keep? / ✕ Exclude / ↺ Keep / Later** | Explicit tri-state: Undecided is preserved, never auto-promoted |
| **Emoji field** | Exactly one emoji (registry suggests; legitimate manual picks allowed) |
| **Title / Author / Cover** | Required pack metadata; edits invalidate approval |
| **Save** | Loopback direct-save with `--serve` (digest compare-and-swap; page regenerates); otherwise download fallback |
| **Approve Pack** | Same gate as CLI `--approve`: server re-validates and persists it on Save |

Cards are outlined by confidence (warning/triage only — never an export gate): red
below 0.6, orange below 0.8, neutral above. The **Needs Review** filter collects
low-confidence, unassigned, error, and Undecided stickers.

The browser never generates `stickers.yaml` (single Python implementation only).
`export`/`preview`/`upload` rebuild or verify the manifest from the current draft
and image hashes immediately before use; existing `stickers.yaml` files are never
trusted by existence alone.

### Getting your edits back into the pack

Turnkey: `./stickers curate ./my_pack --serve`, then click **Save** (writes the
draft directly; revision-checked, loopback-only with a session token).

Static fallback:

1. Click **Download draft (fallback)**.
2. Copy the downloaded `pack_draft.json` over your pack folder's draft.
3. Run `./stickers export ./my_pack`.

The page warns before you close it with unsaved changes (baseline-compared dirty
state; filter/sort/theme never mark dirty).

---

## Signal Sticker Requirements

Per the [official Signal guidelines](https://support.signal.org/hc/en-us/articles/360031836512-Stickers#sticker_creator),
split here into hard gates (export fails) versus quality recommendations (warnings
unless `--strict-quality`).

Hard gates (Signal/tool):

- Static PNG or WebP; animated APNG only
- 3 s animation maximum
- 300 KB maximum per sticker
- 200 stickers maximum
- Exactly one emoji per sticker (`chr`)
- Required title/author; valid PNG/WebP cover (defaults to first kept sticker)
- Current, approved draft state; no missing/extra files or hash mismatches

Quality warnings (recommendations, not server rejections):

- Transparent background; contrast outline for light/dark themes
- Approximately 16 px transparent margin
- 30/60 FPS; seamless looping; first frame expressing the main idea

Project safe-output policy: exactly 512x512 px is enforced at export. Signal
states that it resizes images, so this is our own safe-output rule rather than a
proven server-side rejection.

> [!WARNING]
> **Uploaded packs cannot be edited.** Signal gives you no way to change emojis or remove
> stickers after upload. Always review before uploading.

---

## Files

| File | Role |
| :--- | :--- |
| `pack_draft.json` | **Sole source of truth.** Schema v3: revision, title/author/cover, selection, hashes, clusters, suggested + final single emoji, tag source/status, confidence/reason, approval. |
| `review.html` | Generated review page. Safe to delete; rebuilt by `curate`/`review`. |
| `preview.html` | Written by `signal-sticker-tool preview`. Ignored by preflight; safe to delete. |
| `stickers.yaml` | Build output consumed by `signal-sticker-tool`. Never trusted without its receipt. |
| `stickers.yaml.receipt.json` | Build receipt: draft digest, ordered files/hashes, title/author/cover, manifest digest, builder version. |
| `uploaded.yaml` | Written by `signal-sticker-tool` on upload (`id`/`key`); while present the tool refuses to re-upload. |
| `classification_cache.json` | Legacy. Migrated once into the draft as pending suggestions, never pre-approved. |

All live in your **pack folder**, not next to the scripts, so multiple packs can be
curated independently.

Only `keep` stickers with exactly one valid final emoji **and an image still on
disk** reach `stickers.yaml`. Suggested-only tags do not qualify. `export` hard-fails
on undecided, unapproved, missing/extra, hash-mismatch, invalid emoji, image-gate,
count, cover, or stale-manifest problems — and removes a stale YAML on failure so it
cannot be mistaken for a good build. Draft and YAML writes are atomic.

---

## Command-Line Reference

Prefer `./stickers`. For anything the runner does not wrap, call the Python directly —
`./stickers` passes unrecognized arguments straight through.

### `classify_and_build.py`

```bash
python classify_and_build.py ./my_pack --scan
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `folder` | *(required, explicit)* | Directory containing sticker images |
| `--scan` | off | Inventory, hard-gate report, and cluster (no API calls) |
| `--check-only` | off | Alias for `--scan` |
| `--classify-kept` | off | Suggest one emoji for `keep` stickers lacking a final emoji |
| `--approve` | off | Human approval gate for the current revision |
| `--preflight` | off | Strict export/upload preflight only (read-only; never writes the draft) |
| `--build-yaml` | off | Preflight + write `stickers.yaml` + receipt |
| `--prune` | off | With `--scan`: explicitly drop entries for missing files |
| `--cluster-distance` | `6` | dHash Hamming edge threshold |
| `--linkage` | `single` | `single` (may chain) or `complete` (prevents chaining) |
| `--strict-quality` | off | Promote quality recommendations to errors |
| `--title` | keep draft value | Explicit pack title (required before approve) |
| `--author` | keep draft value | Explicit pack author (required before approve) |
| `--cover` | first kept | Cover image filename |
| `--model` | OpenRouter default | e.g. `inclusionai/ling-3.0-flash-vl` |
| `--out` | `stickers.yaml` | Output filename |
| `--draft` | `pack_draft.json` | Draft state file |
| `--cache` | `classification_cache.json` | Legacy cache, migrated once as pending |
| `--workers` | `4` | Parallel suggestion requests |
| `--yes` | off | Noninteractive export marker (upload confirmation lives in runner) |

With no action flag, the tool suggests tags for kept stickers lacking a final emoji
and then runs the strict export path. `--dedupe` and `--resume` are accepted but do
nothing.

### `review.py`

```bash
python review.py ./my_pack
python review.py ./my_pack --serve
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `folder` | *(required, explicit)* | Pack folder |
| `--draft` | `pack_draft.json` | Draft to read (sole source; YAML never trusted) |
| `--yaml` | `stickers.yaml` | Legacy name only; never used as input |
| `--serve` | off | Loopback save server (127.0.0.1, token, revision-checked) |
| `--port` | `0` | Loopback port (0 = random) |

---

## How Classification Works

A perceptual hash (64-bit dHash) is computed for every image, compositing transparency over
neutral grey first so hidden RGB in transparent pixels cannot distort the hash. Images within
`--cluster-distance` (default 6) are grouped as visually similar candidates requiring review
— not proven duplicates. Single linkage (default) may chain through intermediates; `--linkage
complete` prevents chaining. Scan reports per-cluster member count and median/max all-pairs
distance plus pair data; large or high-max clusters are surfaced as suspicious.

One emoji per sticker is the supported output contract. The fixed registry in `emojis.py`
remains the suggestion source, but legitimate manual picks outside it are accepted when they
form a single emoji grapheme. Invalid input is an error, never a silent `🙂`/`😐` fallback;
provider failures stay unresolved/error and block approval/export until re-tagged.

OpenRouter is the only provider (plain `urllib`, no vendor SDK; default
`inclusionai/ling-3.0-flash-vl`, key `OPENROUTER_API_KEY`).

Each sticker costs one request. Only `keep` stickers lacking a valid final emoji are sent,
and suggestions never auto-approve — a human promotes each to final in review, then records
`--approve` for the current revision. Any later metadata/selection/tag/cover/hash change
invalidates approval. Confidence stays a UI warning/triage signal only.

---

## Troubleshooting

**`OPENROUTER_API_KEY ... not set`** — `tag` needs it. See [API Keys](#api-keys).

**`Error: 'signal-sticker-tool' is not installed`** — only affects `preview` / `upload`:

```bash
.venv/bin/python -m pip install -r python/signal-stickers/requirements-upload.txt
```

**`Export blocked by N preflight error(s)`** — resolve every listed item (undecided,
unapproved, missing/placeholder title/author, invalid single emoji, provider-error tags,
missing/extra files, hash mismatch, image hard-gates, >200, bad cover, unsupported
formats, stale manifest). A failed export removes a stale YAML so it cannot be reused.
`preview`/`upload` re-run the same preflight plus receipt verification.

**`Draft references missing file`** — restore the image or run explicit
`scan --prune` (pruning is never silent; approval is invalidated).

**`draft ... exists but cannot be parsed`** — the draft is corrupt and will not be
overwritten. Back it up, then re-run with `--reset-draft` (which archives the old
file to `pack_draft.json.bak` first).

**`On-disk file not in draft`** — re-run `scan`; new images are never silently omitted.
Renames with unchanged hashes preserve decisions automatically.

**Your review edits vanished** — with static `review.html` they only existed in the tab.
Use `curate --serve` + **Save**, or Download + copy-back before closing.

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
4. Authenticate (this repo never sees or stores your credentials; the
   external tool saves them under your config home):
   ```bash
   ./stickers login
   # equivalent: signal-sticker-tool login
   ```

Check readiness without uploading:

```bash
./stickers doctor --upload ./my_pack
```

It requires `signal-sticker-tool`, a configured Signal login (presence only,
never printed), and a preflight-clean pack. `OPENROUTER_API_KEY` stays
optional (only `tag` needs it).

### Upload

```bash
./stickers preview ./my_pack             # local render, no upload
./stickers upload ./my_pack              # prompts YES (irreversible)
./stickers upload ./my_pack --yes        # noninteractive
./stickers url ./my_pack                 # reprint the share URL later
```

Before the external uploader runs, the runner re-runs preflight, verifies the
receipt (never trusts YAML by existence), prints the final title/author/count/cover/digest,
detects `uploaded.yaml`, and requires confirmation. Runner-only flags such as
`--yes` are never forwarded to `signal-sticker-tool` (its `preview`/`upload`
subcommands take no extra arguments). You get a shareable link like
`https://signal.art/addstickers/#pack_id=...&pack_key=...`.

`uploaded.yaml` is written by `signal-sticker-tool` itself on a successful
upload. While it exists, the tool refuses to upload again and shows the
previous upload instead — so an accidental re-run cannot burn a second
immutable pack. For an intentional re-upload, delete or rename
`uploaded.yaml` first.

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
- Static `review.html` cannot write to disk; use `curate --serve` for turnkey saves
  or the download fallback. Served saves are loopback-only (127.0.0.1), token-gated,
  revision-checked, with restrictive CSP and no CORS.
- `review.html` embeds every image as base64, so page size grows linearly with the pack.
