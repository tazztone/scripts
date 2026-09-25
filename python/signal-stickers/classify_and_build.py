#!/usr/bin/env python3
"""Signal Sticker Pack Classifier & Builder (Curation-First).

1. Inventory & Constraints: Checks 512x512 project policy, 300KB max,
   static PNG/WebP or animated APNG<=3s (hard gates) plus quality warnings.
2. Perceptual Clustering: Groups visually similar candidates requiring review
   using alpha-aware dHash (connected components by default).
3. Persistent Draft State: Tracks selection (keep/exclude/undecided), hashes,
   clusters, tags, and pack approval in pack_draft.json (schema v3).
4. Targeted VLM Classification: OpenRouter-only; classifies ONLY 'keep'
   stickers lacking a final emoji. Failures stay unresolved, never 😐 fallback.
5. Build Manifest: Generates stickers.yaml plus a build receipt from an
   approved, fully reviewed draft. Preview/upload re-verify before use.

Usage:
  python classify_and_build.py ./pack --scan
  python classify_and_build.py ./pack --classify-kept --title "My Pack" --author "me"
  python classify_and_build.py ./pack --approve --title "My Pack" --author "me"
  python classify_and_build.py ./pack --build-yaml
  python classify_and_build.py ./pack --preflight
  python classify_and_build.py ./pack --scan --prune
"""

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Automatically re-exec with workspace .venv if invoked with system python
_venv_python = Path(__file__).resolve().parent.parent.parent / ".venv" / "bin" / "python"
if _venv_python.exists() and Path(sys.executable).resolve() != _venv_python.resolve():
    if os.environ.get("_SIGNAL_STICKERS_BOOTSTRAPPED") != "1":
        os.environ["_SIGNAL_STICKERS_BOOTSTRAPPED"] = "1"
        os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)

try:
    import yaml
except ImportError:
    sys.exit("Error: PyYAML not installed. Run: pip install PyYAML")

try:
    from PIL import Image
except ImportError:
    sys.exit("Error: Pillow not installed. Run: pip install Pillow")

# Import shared emoji registry and helpers
try:
    from emojis import (
        EMOJI_REGISTRY,
        WHITELIST,
        extract_emojis,
        format_emoji_sequence,
        get_all_emojis,
        get_emoji_info,
        get_prompt_emoji_catalog,
        get_related_emojis,
        is_valid_emoji_sequence,
        is_valid_single_emoji,
        validate_emoji_sequence,
        validate_single_emoji,
    )
except ImportError:
    from .emojis import (
        EMOJI_REGISTRY,
        WHITELIST,
        extract_emojis,
        format_emoji_sequence,
        get_all_emojis,
        get_emoji_info,
        get_prompt_emoji_catalog,
        get_related_emojis,
        is_valid_emoji_sequence,
        is_valid_single_emoji,
        validate_emoji_sequence,
        validate_single_emoji,
    )

# Single draft-state implementation shared with review.py (fail-closed).
try:
    from draft_state import (
        DRAFT_SCHEMA_VERSION,
        DraftError,
        draft_digest,
        load_draft_for_review,
        new_draft_empty,
        upgrade_draft_to_v3,
    )
except ImportError:
    from .draft_state import (
        DRAFT_SCHEMA_VERSION,
        DraftError,
        draft_digest,
        load_draft_for_review,
        new_draft_empty,
        upgrade_draft_to_v3,
    )

DEFAULT_DRAFT = "pack_draft.json"
DEFAULT_CACHE = "classification_cache.json"
SUPPORTED_EXTENSIONS = {".webp", ".png", ".apng", ".jpg", ".jpeg"}
# Extensions eligible for sticker candidacy. Anything else on disk is either an
# expected sidecar or a hard-gate failure — never silently ignored.
INVENTORY_EXTENSIONS = {".webp", ".png", ".apng", ".jpg", ".jpeg", ".gif", ".bmp"}
HARD_IMAGE_EXTENSIONS = {".png", ".webp", ".apng"}
# Files that live alongside the pack but are not sticker candidates.
# preview.html is the documented output of `signal-sticker-tool preview`
# run inside the pack folder, so it must not fail a later preflight.
SIDECAR_NAMES = {
    "pack_draft.json", "stickers.yaml", "stickers.yaml.receipt.json",
    "review.html", "preview.html", "classification_cache.json", "uploaded.yaml",
}
SIDECAR_SUFFIXES = {".tmp", ".bak"}

# DRAFT_SCHEMA_VERSION, DraftError, draft_digest, load_draft_for_review,
# new_draft_empty, upgrade_draft_to_v3 are imported from draft_state above
# (single implementation shared with review.py).
BUILDER_VERSION = "signal-stickers-builder/3.0"
MAX_STICKERS = 200
MAX_BYTES = 300 * 1024
REQUIRED_DIMENSIONS = (512, 512)

PLACEHOLDER_TITLES = {"", "signal stickers", "author", "unknown", "untitled", "todo", "test"}
PLACEHOLDER_AUTHORS = {"", "author", "unknown", "untitled", "todo", "test"}


def compute_file_sha256(path: Path) -> str:
    """Computes SHA-256 digest of file content for cache invalidation."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_dhash(image_path: Path, hash_size: int = 8) -> int:
    """Computes a 64-bit difference hash (dHash) using Pillow.

    Alpha-aware: composites transparent images onto neutral 50% gray
    so transparent background RGB artifacts do not distort hash gradients.
    """
    with Image.open(image_path) as img:
        # If image has an alpha channel, composite over neutral 50% gray (128, 128, 128)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            bg = Image.new("RGBA", img.size, (128, 128, 128, 255))
            bg.alpha_composite(img.convert("RGBA"))
            gray = bg.convert("L")
        else:
            gray = img.convert("L")

        resized = gray.resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
        pixels = (
            list(resized.get_flattened_data())
            if hasattr(resized, "get_flattened_data")
            else list(resized.getdata())
        )

        diff = []
        for row in range(hash_size):
            row_start = row * (hash_size + 1)
            for col in range(hash_size):
                left = pixels[row_start + col]
                right = pixels[row_start + col + 1]
                diff.append(left > right)
        hash_val = 0
        for bit in diff:
            hash_val = (hash_val << 1) | bit
        return hash_val


def hamming_distance(h1: int, h2: int) -> int:
    """Computes Hamming distance between two 64-bit hashes."""
    return bin(h1 ^ h2).count("1")


def detect_visual_clusters(
    files: List[Path], max_distance: int = 6, linkage: str = "single"
) -> Tuple[Dict[str, List[str]], Dict[str, str], Dict[str, Dict[str, Any]]]:
    """Groups visually similar candidates requiring review.

    Connected components ("single" linkage, default) may chain through
    intermediate images; "complete" linkage only groups images where every
    pair is within max_distance, preventing single-link chaining.

    Returns:
        clusters: mapping cluster_id -> list of filenames (clusters with >= 2 members)
        file_to_cluster: mapping filename -> cluster_id
        dupe_info: mapping filename -> {'reference': ref_name, 'distance': dist}
    """
    hashes: Dict[str, int] = {}
    for p in files:
        try:
            hashes[p.name] = compute_dhash(p)
        except Exception:
            pass

    names = list(hashes.keys())
    adj = defaultdict(list)
    dupe_info: Dict[str, Dict[str, Any]] = {}

    for i in range(len(names)):
        n1 = names[i]
        for j in range(i + 1, len(names)):
            n2 = names[j]
            dist = hamming_distance(hashes[n1], hashes[n2])
            if dist <= max_distance:
                adj[n1].append((n2, dist))
                adj[n2].append((n1, dist))
                if n2 not in dupe_info or dist < dupe_info[n2]["distance"]:
                    dupe_info[n2] = {"reference": n1, "distance": dist}

    # Pairwise distances for diagnostics (symmetric).
    pair_dist: Dict[Tuple[str, str], int] = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            d = hamming_distance(hashes[names[i]], hashes[names[j]])
            pair_dist[(names[i], names[j])] = d
            pair_dist[(names[j], names[i])] = d

    visited: Set[str] = set()
    clusters: Dict[str, List[str]] = {}
    file_to_cluster: Dict[str, str] = {}
    cluster_idx = 1

    if linkage == "complete":
        # Greedy complete-linkage: grow groups only while every pair stays
        # within max_distance, preventing single-link chaining.
        unassigned = set(names)
        for seed in names:
            if seed not in unassigned:
                continue
            group = [seed]
            for cand in names:
                if cand not in unassigned or cand == seed:
                    continue
                if all(pair_dist.get((cand, m), 10**9) <= max_distance for m in group):
                    group.append(cand)
            if len(group) >= 2:
                for m in group:
                    unassigned.discard(m)
                    visited.add(m)
                group.sort()
                cid = f"cluster_{cluster_idx:02d}"
                cluster_idx += 1
                clusters[cid] = group
                for member in group:
                    file_to_cluster[member] = cid
            else:
                unassigned.discard(seed)
                visited.add(seed)
        return clusters, file_to_cluster, dupe_info

    for name in names:
        if name in visited or name not in adj:
            continue
        # BFS / Connected Component (single linkage; may chain).
        component = []
        queue = [name]
        visited.add(name)
        while queue:
            curr = queue.pop(0)
            component.append(curr)
            for neighbor, _ in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        if len(component) >= 2:
            cid = f"cluster_{cluster_idx:02d}"
            cluster_idx += 1
            component.sort()
            clusters[cid] = component
            for member in component:
                file_to_cluster[member] = cid

    return clusters, file_to_cluster, dupe_info


def cluster_pair_stats(members: List[str], hashes: Dict[str, int]) -> Dict[str, Any]:
    """Median/max all-pairs dHash distance plus pair data for diagnostics."""
    dists: List[int] = []
    pairs: List[Dict[str, Any]] = []
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            d = hamming_distance(hashes[members[i]], hashes[members[j]])
            dists.append(d)
            pairs.append({"a": members[i], "b": members[j], "distance": d})
    if not dists:
        return {"count": len(members), "median": 0, "max": 0, "pairs": []}
    ordered = sorted(dists)
    mid = len(ordered) // 2
    median = float(ordered[mid]) if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
    return {"count": len(members), "median": median, "max": max(dists), "pairs": pairs}


def detect_visual_duplicates(
    files: List[Path], max_distance: int = 6
) -> Dict[str, Dict[str, Any]]:
    """Backward-compatible wrapper returning filename -> {'reference': ref, 'distance': dist}."""
    _, _, dupe_info = detect_visual_clusters(files, max_distance=max_distance)
    return dupe_info


def get_classification_prompt() -> str:
    """Builds system prompt for single-emoji classification with strict JSON."""
    catalog = get_prompt_emoji_catalog()
    return (
        "Du bewertest Gesichtsausdruecke und Gesten auf Sticker-Bildern fuer Signal.\n"
        "Waehle GENAU EIN Emoji, das den Ausdruck, die Emotion oder das Overlay "
        "am praezisesten trifft (Signal unterstuetzt ein Emoji pro Sticker).\n\n"
        "Vorgeschlagene Emojis nach Kategorien (du darfst auch ein anderes passendes Emoji waehlen):\n"
        f"{catalog}\n\n"
        "Regeln:\n"
        "- Achte auf Augen, Mund, Haende/Gesten und Overlays (Dampf, Traenen, Sonnenbrille, Herz etc.).\n"
        "- Overlays, Requisiten und markante Gesten haben Vorrang vor rein neutraler Mimik.\n"
        "- WICHTIG: Antworte AUSSCHLIESSLICH als valides JSON-Objekt ohne jeden Begleittext:\n"
        '{"emoji":"<genau ein Emoji>","reason":"<max 8 Woerter Begruendung>","confidence":<0.0-1.0>}'
    )


SYSTEM_PROMPT = get_classification_prompt()


def build_disambiguation_prompt(provisional_emoji: str, filenames: List[str]) -> str:
    """Backward-compatible prompt helper."""
    return f"Vergleiche {len(filenames)} Sticker fuer '{provisional_emoji}' (redundant_of)."


class BaseProvider:
    """Base class for VLM classification providers."""

    def classify(self, image_path: Path, prompt: str) -> Dict[str, Any]:
        raise NotImplementedError


class OpenRouterProvider(BaseProvider):
    """OpenRouter provider supporting vision models (e.g. inclusionai/ling-3.0-flash-vl)."""

    def __init__(self, api_key: str, model: str = "inclusionai/ling-3.0-flash-vl"):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def classify(self, image_path: Path, prompt: str) -> Dict[str, Any]:
        mime_type, b64_data = encode_image_base64(image_path)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64_data}"},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Welches EINE Emoji passt am besten zu diesem Sticker? "
                                "Antworte NUR mit dem JSON-Objekt."
                            ),
                        },
                    ],
                },
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/tazztone/scripts",
            "X-Title": "Signal Sticker Builder",
        }
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            content = msg.get("content")
            if content is None:
                content = msg.get("reasoning") or ""
            return parse_json_response(normalize_message_content(content))


# NOTE: OpenRouter-only by product decision; provider failures must surface
# as unresolved entries, never fallbacks.


def normalize_message_content(content: Any) -> str:
    """Coerces chat message content to text (string or content-block list)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: List[str] = []
        for block in content:
            if isinstance(block, str):
                texts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    texts.append(text)
                    continue
                nested = block.get("content")
                if isinstance(nested, str):
                    texts.append(nested)
                elif isinstance(nested, list):
                    texts.append(normalize_message_content(nested))
        return "\n".join(t for t in texts if t)
    return str(content)


def encode_image_base64(path: Path) -> Tuple[str, str]:
    """Encodes image file to base64 and determines MIME type."""
    mt = mimetypes.guess_type(path.name)[0] or "image/png"
    if mt == "image/apng":
        mt = "image/png"
    return mt, base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def parse_json_response(content: str) -> Any:
    """Safely extracts and parses JSON response handling reasoning tokens and markdown."""
    content = content.strip()

    # 1. Check for markdown code blocks ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if m:
        block = m.group(1).strip()
        try:
            return json.loads(block)
        except Exception:
            content = block

    # 2. Extract outermost JSON object { ... }
    brace_start = content.find("{")
    brace_end = content.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(content[brace_start : brace_end + 1])
        except Exception:
            pass

    # 3. Extract outermost JSON array [ ... ]
    bracket_start = content.find("[")
    bracket_end = content.rfind("]")
    if bracket_start != -1 and bracket_end > bracket_start:
        try:
            return json.loads(content[bracket_start : bracket_end + 1])
        except Exception:
            pass

    # 4. Fallback direct parse
    try:
        return json.loads(content)
    except Exception as e:
        raise ValueError(f"Invalid JSON format in response: {content[:120]}") from e


def get_configured_provider(model: Optional[str] = None) -> BaseProvider:
    """OpenRouter-only provider factory."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        sys.exit("Error: OPENROUTER_API_KEY environment variable not set.")
    m = model or "inclusionai/ling-3.0-flash-vl"
    print(f"Using Provider: OpenRouter (model: {m})")
    return OpenRouterProvider(openrouter_key, model=m)


def get_image_facts(path: Path) -> Dict[str, Any]:
    """Reads format, animation, duration, size, and dimensions without mutating."""
    facts: Dict[str, Any] = {
        "exists": path.exists(),
        "size_bytes": 0,
        "suffix": path.suffix.lower(),
        "format": None,
        "mode": None,
        "dimensions": None,
        "animated": False,
        "n_frames": 1,
        "duration_ms": 0,
        "error": None,
    }
    if not path.exists():
        facts["error"] = "missing file"
        return facts
    try:
        facts["size_bytes"] = path.stat().st_size
    except Exception as e:
        facts["error"] = f"Cannot stat file: {e}"
        return facts
    try:
        with Image.open(path) as img:
            facts["format"] = (img.format or "").upper() or None
            facts["mode"] = img.mode
            facts["dimensions"] = tuple(img.size)
            animated = bool(getattr(img, "is_animated", False))
            try:
                n_frames = int(getattr(img, "n_frames", 1) or 1)
            except Exception:
                n_frames = 2 if animated else 1
            facts["animated"] = animated or n_frames > 1
            facts["n_frames"] = max(n_frames, 2 if facts["animated"] else 1)
            total = 0
            if facts["animated"]:
                try:
                    for i in range(facts["n_frames"]):
                        try:
                            img.seek(i)
                        except EOFError:
                            facts["n_frames"] = i
                            break
                        total += int(img.info.get("duration", 0) or 0)
                except Exception:
                    pass
            facts["duration_ms"] = total
    except Exception as e:
        facts["error"] = f"Cannot read image: {e}"
    return facts


def validate_image_hard(path: Path, facts: Optional[Dict[str, Any]] = None) -> List[str]:
    """Signal/tool hard gates. Invalid input must error, never normalize."""
    facts = facts if facts is not None else get_image_facts(path)
    errors: List[str] = []
    if facts.get("error"):
        return [str(facts["error"])]
    ext = facts["suffix"]
    fmt = (facts.get("format") or "").upper()
    size_bytes = int(facts.get("size_bytes") or 0)
    if size_bytes > MAX_BYTES:
        errors.append(f"Size {size_bytes/1024:.1f} KB exceeds 300 KB limit")
    if ext not in HARD_IMAGE_EXTENSIONS:
        errors.append(f"Format {ext or '(none)'} unsupported: use PNG, WebP, or APNG")
        return errors
    # Actual-format checks (extension/format mismatch fails closed).
    if ext in (".png", ".apng") and fmt not in ("PNG", "APNG"):
        errors.append(f"Format/extension mismatch: {ext} holds {fmt or 'unknown'}")
    if ext == ".webp" and fmt != "WEBP":
        errors.append(f"Format/extension mismatch: .webp holds {fmt or 'unknown'}")
    if ext == ".webp" and facts.get("animated"):
        errors.append("Animated WebP is not supported: use static WebP or animated APNG")
    if ext == ".apng":
        if fmt not in ("PNG", "APNG"):
            errors.append(f"APNG must hold PNG data (found {fmt or 'unknown'})")
        if not facts.get("animated"):
            errors.append("Static file presented as APNG: APNG must be animated")
    if ext == ".png" and facts.get("animated"):
        errors.append("Animated PNG must use .apng, not .png")
    if facts.get("animated"):
        dur = int(facts.get("duration_ms") or 0)
        if dur <= 0:
            errors.append("Animated image has unknown duration; cannot verify 3 s maximum")
        elif dur > 3000:
            errors.append(f"Animation {dur} ms exceeds 3 s maximum")
    dims = facts.get("dimensions")
    if dims != REQUIRED_DIMENSIONS:
        errors.append(
            f"Dimensions {dims[0]}x{dims[1]} != 512x512 px (project safe-output policy)"
            if dims
            else "Dimensions unknown"
        )
    return errors


def validate_image_quality(path: Path, facts: Optional[Dict[str, Any]] = None) -> List[str]:
    """Signal recommendations (warnings, or errors under --strict-quality)."""
    facts = facts if facts is not None else get_image_facts(path)
    warnings: List[str] = []
    if facts.get("error"):
        return []
    mode = str(facts.get("mode") or "")
    if mode not in ("RGBA", "LA", "PA", "P"):
        warnings.append(f"Image mode {mode} might lack transparency (recommend transparent background)")
    else:
        # ~16px transparent margin check (best-effort; warns only).
        try:
            with Image.open(path) as img:
                rgba = img.convert("RGBA") if img.mode != "RGBA" else img
                w, h = rgba.size
                margin = 16
                if w >= 2 * margin and h >= 2 * margin:
                    alpha = rgba.split()[3]
                    edge_opaque = False
                    for x in range(w):
                        for y in list(range(margin)) + list(range(h - margin, h)):
                            if alpha.getpixel((x, y)) > 8:
                                edge_opaque = True
                                break
                        if edge_opaque:
                            break
                    if not edge_opaque:
                        for y in range(h):
                            for x in list(range(margin)) + list(range(w - margin, w)):
                                if alpha.getpixel((x, y)) > 8:
                                    edge_opaque = True
                                    break
                            if edge_opaque:
                                break
                    if edge_opaque:
                        warnings.append("No ~16 px transparent margin (recommendation)")
        except Exception:
            pass
    if facts.get("animated"):
        dur = int(facts.get("duration_ms") or 0)
        frames = int(facts.get("n_frames") or 0)
        if dur > 0 and frames > 0:
            fps = frames / (dur / 1000.0)
            if not (24 <= fps <= 62):
                warnings.append(f"Animation FPS {fps:.1f} outside recommended 30/60")
        warnings.append("Check seamless looping and first-frame clarity (recommendation)")
    else:
        warnings.append("Check contrast outline for light/dark themes (recommendation)")
    return warnings


def validate_cover_hard(path: Path, facts: Optional[Dict[str, Any]] = None) -> List[str]:
    """Cover gate: static PNG or WebP only (Signal covers are never animated)."""
    facts = facts if facts is not None else get_image_facts(path)
    errors = validate_image_hard(path, facts)
    ext = (facts.get("suffix") or path.suffix.lower())
    fmt = (facts.get("format") or "").upper()
    if facts.get("animated"):
        errors.append("Cover must be static; animated covers are not supported")
    if ext == ".apng":
        errors.append("Cover must be static PNG or WebP, not APNG")
    if fmt not in ("PNG", "WEBP"):
        errors.append(f"Cover must be PNG or WebP data (found {fmt or 'unknown'})")
    return errors


def check_signal_constraints(path: Path) -> List[str]:
    """Backward-compatible validator: hard errors plus quality notes."""
    facts = get_image_facts(path)
    return validate_image_hard(path, facts) + validate_image_quality(path, facts)


def _coerce_model_emoji_text(res: Dict[str, Any]) -> str:
    raw = res.get("emoji")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    raw_list = res.get("emojis")
    if isinstance(raw_list, str) and raw_list.strip():
        return raw_list.strip()
    if isinstance(raw_list, (list, tuple)) and raw_list:
        # A single-element list is the supported shape; longer legacy lists
        # are joined only so validation can reject them as multi-emoji.
        return "".join(str(e) for e in raw_list)
    return ""


def classify_single_image(
    provider: BaseProvider, path: Path, retries: int = 3
) -> Dict[str, Any]:
    """Classifies one sticker. Failures stay unresolved; never 😐 fallback tags."""
    last_error: Optional[str] = None
    for attempt in range(retries):
        try:
            res = provider.classify(path, SYSTEM_PROMPT)
            raw_text = _coerce_model_emoji_text(res if isinstance(res, dict) else {})
            valid, vals, err = validate_single_emoji(raw_text)
            if valid:
                return {
                    "emoji": vals[0],
                    "emojis": [vals[0]],
                    "suggested_emojis": [vals[0]],
                    "reason": str(res.get("reason", "OK"))[:80],
                    "confidence": float(res.get("confidence", 0.9)),
                    "review_status": "suggested",
                    "tag_status": "suggested",
                    "tag_source": "openrouter",
                }
            last_error = err or f"Unrecognized emoji: {raw_text[:40]}"
            # Invalid model output is not retryable as a different error; retry
            # only for transport/parse exceptions below. Record unresolved.
            return {
                "emoji": None,
                "emojis": None,
                "suggested_emojis": None,
                "reason": last_error[:80],
                "confidence": 0.0,
                "review_status": "needs_review",
                "tag_status": "unresolved",
                "tag_source": "openrouter",
            }
        except Exception as e:
            last_error = f"Classification error: {e}"
            if attempt == retries - 1:
                return {
                    "emoji": None,
                    "emojis": None,
                    "suggested_emojis": None,
                    "reason": str(last_error)[:80],
                    "confidence": 0.0,
                    "review_status": "error",
                    "tag_status": "error",
                    "tag_source": "openrouter",
                }
            time.sleep(1.5 * (attempt + 1))
    return {
        "emoji": None,
        "emojis": None,
        "suggested_emojis": None,
        "reason": (last_error or "Timeout/Max retries")[:80],
        "confidence": 0.0,
        "review_status": "error",
        "tag_status": "error",
        "tag_source": "openrouter",
    }


def atomic_write_text(path: Path, content: str) -> None:
    """Writes text atomically so interrupted writes cannot corrupt state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


# new_draft_empty, upgrade_draft_to_v3, draft_digest live in draft_state.py
# (imported above; re-exported here for backwards compatibility).


def invalidate_approval(draft: Dict[str, Any], reason: str = "") -> None:
    draft["pack_state"] = "in_progress"
    draft["approval"] = None
    if reason:
        draft["last_invalidation"] = reason


def bump_revision(draft: Dict[str, Any], reason: str = "revision bump") -> None:
    draft["revision"] = int(draft.get("revision") or 1) + 1
    invalidate_approval(draft, reason)


def remap_cluster_ids(
    old_groups: Dict[str, List[str]], new_clusters: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    """Reuses stable cluster IDs across rescans by member overlap.

    Fresh `cluster_NN` IDs are regenerated on every scan, so an added file can
    shift unrelated IDs. Greedy maximum-overlap matching keeps IDs stable;
    genuinely new groups take unused IDs past the previous maximum.
    """
    old_sets = {cid: set(m) for cid, m in (old_groups or {}).items()}
    max_n = 0
    for cid in old_sets:
        m = re.fullmatch(r"cluster_(\d+)", str(cid))
        if m:
            max_n = max(max_n, int(m.group(1)))
    ordered = sorted(new_clusters.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    used: Set[str] = set()
    remapped: Dict[str, List[str]] = {}
    counter = [max_n]

    def fresh_id() -> str:
        counter[0] += 1
        cid = f"cluster_{counter[0]:02d}"
        while cid in used or cid in old_sets:
            counter[0] += 1
            cid = f"cluster_{counter[0]:02d}"
        return cid

    for _, members in ordered:
        mset = set(members)
        best: Optional[str] = None
        best_score = 0
        for oid, oset in old_sets.items():
            if oid in used:
                continue
            inter = len(mset & oset)
            if inter > best_score:
                best, best_score = oid, inter
        cid = best if best and best_score > 0 else fresh_id()
        used.add(cid)
        remapped[cid] = sorted(members)
    return remapped


def is_sidecar(path: Path) -> bool:
    name = path.name
    if name in SIDECAR_NAMES or name.startswith("."):
        return True
    lowered = name.lower()
    return any(lowered.endswith(s) for s in SIDECAR_SUFFIXES)


def inventory_folder(folder: Path) -> List[Path]:
    """Every non-sidecar file on disk. Unlisted types fail closed, never ignored."""
    if not folder.is_dir():
        return []
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and not is_sidecar(p)),
        key=lambda p: p.name,
    )


def candidate_files(folder: Path) -> List[Path]:
    """Sticker-eligible subset of the inventory (known image extensions)."""
    return sorted(
        (p for p in inventory_folder(folder) if p.suffix.lower() in INVENTORY_EXTENSIONS),
        key=lambda p: p.name,
    )


def load_or_create_draft(
    folder: Path,
    draft_path: Path,
    legacy_cache_path: Optional[Path] = None,
    files: Optional[List[Path]] = None,
    cluster_distance: int = 6,
    linkage: str = "single",
) -> Dict[str, Any]:
    """Loads pack_draft.json (migrating v2/legacy to pending), then fail-closed sync.

    A present-but-unreadable draft aborts instead of being replaced: overwriting
    it would destroy the only review state. Use --reset-draft to back it up
    explicitly and start over.
    """
    draft = new_draft_empty()
    migrated_legacy = False
    pre_existing = draft_path.exists()
    schema_changed = False

    if draft_path.exists():
        try:
            draft = load_draft_for_review(draft_path)
        except DraftError as e:
            sys.exit(f"Error: {e}")
        try:
            _raw_check = json.loads(draft_path.read_text(encoding="utf-8"))
        except Exception:
            _raw_check = {}
        if not isinstance(_raw_check, dict):
            _raw_check = {}
        schema_changed = _raw_check.get("version") != DRAFT_SCHEMA_VERSION or "revision" not in _raw_check
    elif legacy_cache_path and legacy_cache_path.exists():
        try:
            legacy = json.loads(legacy_cache_path.read_text(encoding="utf-8"))
            print(f"Migrating legacy cache ({len(legacy)} items) to pack_draft.json (pending)...")
            for fn, item in legacy.items():
                em_seq = item.get("emojis") or ([item["emoji"]] if "emoji" in item else None)
                if isinstance(em_seq, str):
                    em_seq = [em_seq]
                sel = "exclude" if item.get("visual_dupe_of") or item.get("redundant_of") else "keep"
                draft["stickers"][fn] = {
                    "file_hash": "",
                    "selection": sel,
                    "similarity_group": None,
                    "suggested_emojis": em_seq,
                    "emojis": None,
                    "confidence": float(item.get("confidence", 0.0) or 0.0),
                    "reason": str(item.get("reason", "") or ""),
                    "review_status": "pending",
                    "tag_status": "suggested" if em_seq else "pending",
                    "tag_source": "legacy-migration",
                }
            migrated_legacy = True
        except Exception as e:
            print(f"Warning: Could not read legacy cache: {e}")

    if files is None:
        return draft

    # Only cluster supported still-image inputs; unsupported files are still
    # inventoried for hard-gate failures but excluded from hashing/clusters.
    hashable = [p for p in files if p.suffix.lower() in HARD_IMAGE_EXTENSIONS]
    raw_clusters, _, _dupe = detect_visual_clusters(
        hashable, max_distance=cluster_distance, linkage=linkage
    )
    old_groups = dict(draft.get("similarity_groups", {}) or {})
    clusters = remap_cluster_ids(old_groups, raw_clusters)
    file_to_cluster: Dict[str, str] = {}
    for cid, members in clusters.items():
        for m in members:
            file_to_cluster[m] = cid
    draft["similarity_groups"] = clusters
    # Any cluster whose membership changed affects every member, including
    # members that merely gained a sibling (their own ID is unchanged).
    affected_clusters: Set[str] = set()
    for cid in set(old_groups) | set(clusters):
        if set(old_groups.get(cid, [])) != set(clusters.get(cid, [])):
            affected_clusters.add(cid)
    # Digest before per-file sync (rename carry-over, new/changed entries) so any
    # material rescan change advances the revision for compare-and-swap.
    pre_sync_digest = draft_digest(draft)

    # Hash current files.
    current_hashes: Dict[str, str] = {}
    for p in files:
        try:
            current_hashes[p.name] = compute_file_sha256(p)
        except Exception:
            continue

    # Rename preservation: match new filenames to missing entries by unchanged hash.
    missing_names = [fn for fn in draft.get("stickers", {}) if fn not in current_hashes]
    hash_to_missing: Dict[str, str] = {}
    for fn in missing_names:
        h = draft["stickers"][fn].get("file_hash")
        if h:
            hash_to_missing.setdefault(h, fn)
    for p in files:
        fn = p.name
        if fn not in draft["stickers"]:
            h = current_hashes.get(fn, "")
            donor = hash_to_missing.get(h, "") if h else ""
            if donor and donor in draft["stickers"]:
                carried = dict(draft["stickers"][donor])
                carried["file_hash"] = h
                draft["stickers"][fn] = carried
                print(f"Preserved decision across rename: {donor} -> {fn} (hash unchanged).")

    for p in files:
        fhash = current_hashes.get(p.name, "")
        fn = p.name
        cid = file_to_cluster.get(fn)

        if fn not in draft["stickers"]:
            sel = "undecided" if cid else "keep"
            draft["stickers"][fn] = {
                "file_hash": fhash,
                "selection": sel,
                "similarity_group": cid,
                "suggested_emojis": None,
                "emojis": None,
                "confidence": 0.0,
                "reason": f"Cluster: {cid}" if cid else "",
                "review_status": "pending",
                "tag_status": "pending",
                "tag_source": "scan",
            }
            if sel == "undecided":
                invalidate_approval(draft, f"new clustered file {fn}")
            else:
                invalidate_approval(draft, f"new file {fn}")
        else:
            entry = draft["stickers"][fn]
            old_cid = entry.get("similarity_group")
            entry["similarity_group"] = cid
            if entry.get("file_hash") and entry["file_hash"] != fhash:
                print(f"Sticker file modified on disk: {fn} -> clearing tags, invalidating approval.")
                entry["file_hash"] = fhash
                entry["suggested_emojis"] = None
                entry["emojis"] = None
                entry["confidence"] = 0.0
                entry["reason"] = "Image changed; re-tag required"
                entry["review_status"] = "pending"
                entry["tag_status"] = "stale"
                entry["tag_source"] = "scan"
                if cid:
                    entry["selection"] = "undecided"
                invalidate_approval(draft, f"changed image {fn}")
            elif not entry.get("file_hash"):
                entry["file_hash"] = fhash

    if affected_clusters:
        reset = 0
        for fn, entry in draft.get("stickers", {}).items():
            if fn not in current_hashes:
                continue
            if entry.get("tag_status") == "stale":
                continue
            if entry.get("similarity_group") in affected_clusters:
                entry["selection"] = "undecided"
                entry["review_status"] = "pending"
                entry["tag_status"] = "pending"
                reset += 1
        invalidate_approval(draft, "cluster membership changed")
        print(
            f"Warning: {len(affected_clusters)} cluster(s) changed membership; "
            f"decisions for {reset} affected member(s) reset to undecided."
        )

    if migrated_legacy:
        invalidate_approval(draft, "legacy migration")
    if pre_existing and (schema_changed or draft_digest(draft) != pre_sync_digest):
        # A persisted draft materially changed on rescan: advance the revision so
        # stale pages/servers fail their compare-and-swap instead of overwriting.
        draft["revision"] = int(draft.get("revision") or 1) + 1
        if draft.get("pack_state") == "approved" or draft.get("approval"):
            draft["pack_state"] = "in_progress"
            draft["approval"] = None
    return draft


def save_draft(draft_path: Path, draft: Dict[str, Any]) -> None:
    """Saves the persistent draft state atomically."""
    draft.setdefault("version", DRAFT_SCHEMA_VERSION)
    atomic_write_text(draft_path, json.dumps(draft, ensure_ascii=False, indent=2))


def final_emoji_for_entry(item: Dict[str, Any]) -> Optional[str]:
    """Strict single-emoji gate: final `emojis` only, never suggestions/fallbacks."""
    final = item.get("emojis")
    if isinstance(final, list) and len(final) == 1 and isinstance(final[0], str):
        valid, vals, _ = validate_single_emoji(final[0])
        return vals[0] if valid else None
    if isinstance(final, str) and final:
        valid, vals, _ = validate_single_emoji(final)
        return vals[0] if valid else None
    return None


def select_manifest_entries(
    draft: Dict[str, Any], folder: Optional[Path] = None
) -> Tuple[List[Dict[str, str]], List[str], List[str]]:
    """Picks exportable stickers: 'keep' + valid final single emoji + on-disk.

    Suggested emojis alone do not qualify; a human must promote them to final
    via review/approve. Invalid input is skipped here and hard-fails in
    preflight; never normalized to 🙂/😐.

    Returns:
        entries:  ordered [{'chr': ..., 'file': ...}, ...] for the manifest
        skipped:  filenames of 'keep' stickers without a valid final emoji
        missing:  filenames of tagged 'keep' stickers absent from `folder`
    """
    entries: List[Dict[str, str]] = []
    skipped: List[str] = []
    missing: List[str] = []

    for fn, item in sorted(draft.get("stickers", {}).items()):
        if item.get("selection") != "keep":
            continue
        single = final_emoji_for_entry(item)
        if not single:
            skipped.append(fn)
            continue
        if folder is not None and not (folder / fn).exists():
            missing.append(fn)
            continue
        entries.append({"chr": single, "file": fn})

    return entries, skipped, missing


def effective_cover(draft: Dict[str, Any], entries: List[Dict[str, str]]) -> Optional[str]:
    meta = draft.get("meta", {}) if isinstance(draft.get("meta"), dict) else {}
    cover = meta.get("cover")
    if isinstance(cover, str) and cover.strip():
        return cover.strip()
    if entries:
        return entries[0]["file"]
    return None


def validate_draft_for_export(
    draft: Dict[str, Any], folder: Path, strict_quality: bool = False
) -> Tuple[List[str], List[str]]:
    """Central preflight used by scan import, export, preview, and upload."""
    errors: List[str] = []
    warnings: List[str] = []

    if draft.get("version") != DRAFT_SCHEMA_VERSION:
        errors.append(f"Draft schema v{draft.get('version')} != v{DRAFT_SCHEMA_VERSION}; re-run scan to migrate.")
    meta = draft.get("meta", {}) if isinstance(draft.get("meta"), dict) else {}
    title = str(meta.get("title") or "").strip()
    author = str(meta.get("author") or "").strip()
    if not title or title.lower() in PLACEHOLDER_TITLES:
        errors.append("Missing or placeholder pack title; set an explicit --title.")
    if not author or author.lower() in PLACEHOLDER_AUTHORS:
        errors.append("Missing or placeholder pack author; set an explicit --author.")

    stickers = draft.get("stickers", {}) if isinstance(draft.get("stickers"), dict) else {}
    on_disk = {p.name: p for p in inventory_folder(folder)}
    # Missing/extra inventory checks (fail closed; never silently omit).
    for fn in sorted(stickers):
        if fn not in on_disk:
            errors.append(f"Draft references missing file: {fn} (restore it or run scan --prune).")
    for fn in sorted(on_disk):
        if fn not in stickers:
            errors.append(f"On-disk file not in draft: {fn} (re-run scan; new images are never auto-omitted).")
    # Hash verification: every current entry needs a valid recorded SHA-256.
    # Empty hashes are never accepted (and preflight never silently repairs them).
    for fn, item in sorted(stickers.items()):
        if fn not in on_disk:
            continue
        recorded = item.get("file_hash") or ""
        if not re.fullmatch(r"[0-9a-f]{64}", recorded):
            errors.append(f"{fn}: missing or invalid file hash; re-run scan to reconcile.")
            continue
        try:
            actual = compute_file_sha256(on_disk[fn])
        except Exception as e:
            errors.append(f"Cannot hash {fn}: {e}")
            continue
        if recorded != actual:
            errors.append(f"Hash mismatch (image changed after draft): {fn}.")
    undecided = sorted(fn for fn, it in stickers.items() if it.get("selection") == "undecided")
    if undecided:
        errors.append(f"Unresolved cluster decisions ({len(undecided)}): {', '.join(undecided[:8])}" + (" ..." if len(undecided) > 8 else ""))
    # Approval gate: human approval for the current revision only.
    approval = draft.get("approval") or {}
    if draft.get("pack_state") != "approved" or not approval:
        errors.append("Pack is not approved; resolve all clusters/emojis then run --approve.")
    elif int(approval.get("revision") or 0) != int(draft.get("revision") or 0):
        errors.append("Approval is stale (draft changed after approval); re-approve.")
    elif approval.get("digest") != draft_digest({k: v for k, v in draft.items() if k not in ("approval",)}):
        # Digest covers everything except the approval envelope itself.
        errors.append("Approval digest mismatch (metadata/selection/tag changed); re-approve.")

    entries, skipped, missing = select_manifest_entries(draft, folder=folder)
    for fn in skipped:
        item = stickers.get(fn, {})
        if item.get("tag_status") in ("error", "unresolved", "stale"):
            errors.append(f"{fn}: provider tag {item.get('tag_status')} ({item.get('reason','')[:60]}); re-tag required.")
        else:
            errors.append(f"{fn}: kept but missing exactly one valid final emoji.")
    for fn in missing:
        errors.append(f"{fn}: tagged but missing from disk.")
    if len(entries) > MAX_STICKERS:
        errors.append(f"Pack has {len(entries)} stickers; Signal allows at most {MAX_STICKERS}.")
    if not entries and not errors:
        errors.append("No exportable stickers (all excluded or unresolved).")

    # Per-file hard image gates + cover.
    for entry in entries:
        errs = validate_image_hard(folder / entry["file"])
        for e in errs:
            errors.append(f"{entry['file']}: {e}")
    cover = effective_cover(draft, entries)
    if not cover:
        errors.append("Missing cover (no stickers to default from).")
    elif cover not in on_disk:
        errors.append(f"Cover missing from disk: {cover}.")
    else:
        for e in validate_cover_hard(folder / cover):
            errors.append(f"Cover {cover}: {e}")

    # Quality warnings (or errors under --strict-quality).
    for entry in entries:
        for w in validate_image_quality(folder / entry["file"]):
            (errors if strict_quality else warnings).append(f"{entry['file']}: {w}")
    # Unsupported or unrecognized files anywhere in the folder fail closed.
    # inventory_folder() already excludes expected sidecars.
    for fn, p in sorted(on_disk.items()):
        if p.suffix.lower() not in HARD_IMAGE_EXTENSIONS:
            if p.suffix.lower() in INVENTORY_EXTENSIONS:
                errors.append(f"{fn}: unsupported format {p.suffix}; convert explicitly (no silent conversion).")
            else:
                errors.append(f"{fn}: unrecognized file type {p.suffix or '(no extension)'}; remove it or convert explicitly.")
    return errors, warnings


def manifest_digest(title: str, author: str, cover: Optional[str], entries: List[Dict[str, str]]) -> str:
    canonical = json.dumps(
        {"title": title, "author": author, "cover": cover, "stickers": entries},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def receipt_path_for_yaml(yaml_path: Path) -> Path:
    return yaml_path.parent / (yaml_path.name + ".receipt.json")


def build_receipt(
    draft: Dict[str, Any], folder: Path, entries: List[Dict[str, str]],
    title: str, author: str, cover: Optional[str],
) -> Dict[str, Any]:
    stickers = draft.get("stickers", {}) or {}
    ordered = [
        {"file": e["file"], "hash": str(stickers.get(e["file"], {}).get("file_hash") or "")}
        for e in entries
    ]
    return {
        "builder": BUILDER_VERSION,
        "draft_schema_version": DRAFT_SCHEMA_VERSION,
        "draft_revision": int(draft.get("revision") or 0),
        "draft_digest": draft_digest(draft),
        "title": title,
        "author": author,
        "cover": cover,
        "files": ordered,
        "manifest_digest": manifest_digest(title, author, cover, entries),
    }


def verify_manifest_freshness(
    folder: Path, draft: Dict[str, Any], yaml_path: Path
) -> List[str]:
    """Preview/upload boundary: never trust stickers.yaml by existence alone."""
    errors: List[str] = []
    if not yaml_path.exists():
        return [f"No manifest at {yaml_path}; run export first."]
    rpath = receipt_path_for_yaml(yaml_path)
    if not rpath.exists():
        return [f"No build receipt at {rpath}; re-run export (stale YAML is never trusted)."]
    try:
        receipt = json.loads(rpath.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"Cannot read build receipt: {e}."]
    try:
        doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        return [f"Cannot read manifest YAML: {e}."]
    entries, _, _ = select_manifest_entries(draft, folder=folder)
    meta = draft.get("meta", {}) or {}
    title = str(meta.get("title") or "")
    author = str(meta.get("author") or "")
    cover = effective_cover(draft, entries)
    expected_digest = manifest_digest(title, author, cover, entries)
    if receipt.get("manifest_digest") != expected_digest:
        errors.append("Manifest receipt digest mismatch: draft changed after export; re-run export.")
    if receipt.get("draft_digest") != draft_digest(draft):
        errors.append("Draft changed after export (receipt digest mismatch); re-run export.")
    # Canonicalize the on-disk YAML and verify its complete content, including
    # emoji values: filename-only comparison would miss chr tampering.
    yaml_meta = doc.get("meta", {}) or {}
    yaml_stickers_raw = doc.get("stickers", []) or []
    yaml_entries: List[Dict[str, str]] = []
    for s in yaml_stickers_raw:
        if not isinstance(s, dict) or not s.get("file"):
            errors.append("stickers.yaml contains a malformed entry; re-run export.")
            continue
        chr_val = s.get("chr")
        if not isinstance(chr_val, str) or not validate_single_emoji(chr_val)[0]:
            errors.append(f"stickers.yaml has invalid emoji for {s.get('file')}; re-run export.")
            continue
        yaml_entries.append({"chr": chr_val, "file": s["file"]})
    yaml_digest = manifest_digest(
        str(yaml_meta.get("title") or ""),
        str(yaml_meta.get("author") or ""),
        yaml_meta.get("cover"),
        yaml_entries,
    )
    if yaml_digest != receipt.get("manifest_digest"):
        errors.append("stickers.yaml content differs from its build receipt (tampered or stale); re-run export.")
    if yaml_entries != entries:
        errors.append("stickers.yaml entries differ from current draft; re-run export.")
    if yaml_meta.get("title") != title or yaml_meta.get("author") != author:
        errors.append("stickers.yaml title/author differs from draft; re-run export.")
    if yaml_meta.get("cover") != cover:
        errors.append("stickers.yaml cover differs from draft; re-run export.")
    return errors


def approve_pack(draft: Dict[str, Any]) -> List[str]:
    """Human approval gate: review-complete, no undecided, single emoji, meta set."""
    errors: List[str] = []
    meta = draft.get("meta", {}) if isinstance(draft.get("meta"), dict) else {}
    if not str(meta.get("title") or "").strip() or str(meta.get("title") or "").strip().lower() in PLACEHOLDER_TITLES:
        errors.append("Set an explicit pack title before approving.")
    if not str(meta.get("author") or "").strip() or str(meta.get("author") or "").strip().lower() in PLACEHOLDER_AUTHORS:
        errors.append("Set an explicit pack author before approving.")
    stickers = draft.get("stickers", {}) or {}
    undecided = [fn for fn, it in stickers.items() if it.get("selection") == "undecided"]
    if undecided:
        errors.append(f"Resolve {len(undecided)} undecided entries before approving.")
    for fn, item in sorted(stickers.items()):
        if item.get("selection") != "keep":
            continue
        if item.get("tag_status") in ("error", "unresolved", "stale"):
            errors.append(f"{fn}: tag {item.get('tag_status')}; re-tag before approving.")
        elif not final_emoji_for_entry(item):
            errors.append(f"{fn}: needs exactly one valid final emoji before approving.")
    if errors:
        return errors
    draft["pack_state"] = "approved"
    draft["approval"] = {
        "revision": int(draft.get("revision") or 0),
        "digest": draft_digest({k: v for k, v in draft.items() if k != "approval"}),
        "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return []


def build_stickers_yaml(
    folder: Path,
    files: Optional[List[Path]] = None,
    cache: Optional[Dict[str, Any]] = None,
    draft: Optional[Dict[str, Any]] = None,
    title: str = "",
    author: str = "",
    cover: Optional[str] = None,
    out_name: str = "stickers.yaml",
    strict_quality: bool = False,
) -> Path:
    """Builds stickers.yaml plus receipt from an approved draft (strict, atomic).

    Runs the central preflight itself so direct callers cannot bypass the
    approval/hash/inventory/image-gate invariants (CLI preflights first too).
    """
    if not (draft and "stickers" in draft):
        raise ValueError("pack_draft.json is the sole source of truth; legacy files/cache builds were removed.")
    if folder is not None:
        errors, _ = validate_draft_for_export(draft, folder, strict_quality=strict_quality)
        if errors:
            raise ValueError(
                "Refusing to build manifest: preflight failed: " + "; ".join(errors[:8])
            )
    meta_draft = draft.get("meta", {}) or {}
    eff_title = str(meta_draft.get("title") or title or "").strip()
    eff_author = str(meta_draft.get("author") or author or "").strip()
    stickers_list, skipped, missing = select_manifest_entries(draft, folder=folder)
    cover_val = (cover or meta_draft.get("cover") or effective_cover(draft, stickers_list))
    if skipped or missing:
        raise ValueError(
            "Refusing to build manifest with unresolved entries: "
            f"skipped={skipped[:5]} missing={missing[:5]}"
        )
    meta: Dict[str, Any] = {"title": eff_title, "author": eff_author}
    if cover_val:
        meta["cover"] = cover_val
    doc = {"meta": meta, "stickers": stickers_list}
    out_path = folder / out_name
    yaml_text = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
    atomic_write_text(out_path, yaml_text)
    receipt = build_receipt(draft, folder, stickers_list, eff_title, eff_author, cover_val)
    atomic_write_text(receipt_path_for_yaml(out_path), json.dumps(receipt, ensure_ascii=False, indent=2))
    return out_path


def _apply_meta_overrides(draft: Dict[str, Any], args: Any) -> bool:
    """Applies explicit --title/--author/--cover; returns True if metadata changed."""
    changed = False
    meta = draft.setdefault("meta", {})
    if getattr(args, "title", None) is not None and meta.get("title") != args.title:
        meta["title"] = args.title
        changed = True
    if getattr(args, "author", None) is not None and meta.get("author") != args.author:
        meta["author"] = args.author
        changed = True
    if getattr(args, "cover", None) and meta.get("cover") != args.cover:
        meta["cover"] = args.cover
        changed = True
    if changed:
        invalidate_approval(draft, "metadata changed")
    return changed


def _print_clusters(draft: Dict[str, Any], files: List[Path]) -> None:
    clusters = draft.get("similarity_groups", {}) or {}
    total_clustered = sum(len(m) for m in clusters.values())
    # Pairwise diagnostics: median/max per cluster + suspicious-cluster warnings.
    hashes: Dict[str, int] = {}
    for p in files:
        if p.suffix.lower() not in HARD_IMAGE_EXTENSIONS:
            continue
        try:
            hashes[p.name] = compute_dhash(p)
        except Exception:
            pass
    if clusters:
        print(f"\nDetected {len(clusters)} visually similar group(s) ({total_clustered} stickers total):")
        for cid, members in sorted(clusters.items()):
            stats = cluster_pair_stats(members, hashes) if all(m in hashes for m in members) else {"median": "?", "max": "?", "count": len(members)}
            print(f"   {cid} ({len(members)} candidates, median={stats['median']} max={stats['max']}): {', '.join(members)}")
            if isinstance(stats.get("count"), int) and stats["count"] >= 8:
                print(f"      Warning: large cluster ({stats['count']} members) — review carefully; may chain distinct expressions.")
            if isinstance(stats.get("max"), (int, float)) and stats["max"] > 10:
                print(f"      Warning: weak evidence (max distance {stats['max']}); treat as candidates, not duplicates.")
    else:
        print("\nNo visually similar groups detected.")


def main():
    parser = argparse.ArgumentParser(description="Signal Sticker Pack Curation & Classifier")
    parser.add_argument("folder", help="Directory containing sticker images (explicit; required)")
    parser.add_argument("--title", default=None, help="Pack title (explicit; preserved in draft when omitted)")
    parser.add_argument("--author", default=None, help="Pack author (explicit; preserved in draft when omitted)")
    parser.add_argument("--cover", default=None, help="Cover image filename")
    parser.add_argument("--model", default=None, help="OpenRouter model slug (e.g. inclusionai/ling-3.0-flash-vl)")
    parser.add_argument("--out", default="stickers.yaml", help="Output YAML filename")
    parser.add_argument("--draft", default=DEFAULT_DRAFT, help="Path to draft JSON")
    parser.add_argument("--cache", default=DEFAULT_CACHE, help="Legacy cache JSON (migrated once, pending)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel classification workers")
    parser.add_argument("--scan", action="store_true", help="Inventory and cluster without API calls")
    parser.add_argument("--check-only", action="store_true", help="Alias for --scan")
    parser.add_argument("--classify-kept", action="store_true", help="Classify only 'keep' stickers lacking final emoji")
    parser.add_argument("--build-yaml", action="store_true", help="Preflight + write stickers.yaml + receipt")
    parser.add_argument("--approve", action="store_true", help="Record human approval for the current revision")
    parser.add_argument("--preflight", action="store_true", help="Run strict export/upload preflight only (no writes)")
    parser.add_argument("--prune", action="store_true", help="With --scan: explicitly drop draft entries for missing files")
    parser.add_argument("--reset-draft", action="store_true", help="Back up the existing draft to .bak and start over (required for corrupt drafts)")
    parser.add_argument("--cluster-distance", type=int, default=6, help="dHash Hamming edge threshold (default 6)")
    parser.add_argument("--linkage", choices=["single", "complete"], default="single", help="Cluster linkage (default single; complete prevents chaining)")
    parser.add_argument("--strict-quality", action="store_true", help="Promote quality recommendations to errors")
    parser.add_argument("--yes", action="store_true", help="Noninteractive: allow writes without prompting (export only)")
    parser.add_argument("--resume", action="store_true", help="No-op, kept for backwards compatibility")
    parser.add_argument("--dedupe", action="store_true", help="No-op, kept for backwards compatibility")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        sys.exit(f"Error: pack folder '{folder}' does not exist. Pass an explicit folder, e.g. ./stickers scan ./my_pack.")

    draft_path = folder / args.draft if not Path(args.draft).is_absolute() else Path(args.draft)
    legacy_cache_path = folder / args.cache if not Path(args.cache).is_absolute() else Path(args.cache)
    if args.reset_draft:
        if draft_path.exists():
            backup = draft_path.parent / (draft_path.name + ".bak")
            atomic_write_text(backup, draft_path.read_text(encoding="utf-8"))
            draft_path.unlink()
            print(f"Backed up existing draft to {backup}; starting over.")
        else:
            print("No existing draft to reset.")

    files = inventory_folder(folder)
    images = candidate_files(folder)
    if not images:
        sys.exit(f"Error: No image files found in '{folder}'. Supported: {sorted(INVENTORY_EXTENSIONS)}")

    print(f"Found {len(images)} image file(s) in {folder}")
    non_candidate = [p.name for p in files if p not in images]
    if non_candidate:
        print(f"Note: {len(non_candidate)} non-candidate file(s) will fail preflight until removed/converted: "
              + ", ".join(sorted(non_candidate)[:8]))

    # Hard image gates are reported here as early signal; export/preflight enforces.
    hard_problems: Dict[str, List[str]] = {}
    quality_notes: Dict[str, List[str]] = {}
    for p in images:
        facts = get_image_facts(p)
        errs = validate_image_hard(p, facts)
        if errs:
            hard_problems[p.name] = errs
        quals = validate_image_quality(p, facts)
        if quals:
            quality_notes[p.name] = quals
    if hard_problems:
        print("\nImage hard-gate failures (export will fail until fixed):")
        for name in sorted(hard_problems)[:15]:
            print(f"   {name}: {'; '.join(hard_problems[name])}")
        if len(hard_problems) > 15:
            print(f"   ... and {len(hard_problems) - 15} more")
    else:
        print("Image hard gates: pass (512x512 project policy, 300KB, PNG/WebP/APNG<=3s).")

    draft = load_or_create_draft(
        folder, draft_path, legacy_cache_path, images,
        cluster_distance=args.cluster_distance, linkage=args.linkage,
    )
    read_only = bool(args.preflight or args.build_yaml)
    if _apply_meta_overrides(draft, args):
        print("Metadata updated; approval invalidated (re-approve after review).")
        bump_revision(draft, "metadata changed")
    _print_clusters(draft, images)
    # Preflight and export are read-only: they validate the synchronized draft
    # without persisting migration/sync side effects.
    mutating = bool(args.scan or args.check_only or args.classify_kept or args.approve or args.prune)
    if mutating and not read_only:
        save_draft(draft_path, draft)

    if args.prune:
        stickers = draft.get("stickers", {}) or {}
        on_disk_names = {p.name for p in images}
        pruned = sorted(fn for fn in stickers if fn not in on_disk_names)
        if pruned:
            for fn in pruned:
                del stickers[fn]
            bump_revision(draft, f"pruned {len(pruned)} missing")
            save_draft(draft_path, draft)
            print(f"\nPruned {len(pruned)} missing entr(y/ies): {', '.join(pruned[:10])}" + (" ..." if len(pruned) > 10 else ""))
        else:
            print("\nPrune: nothing missing; draft already matches disk.")

    if args.scan or args.check_only:
        print(f"\nScan completed. Draft saved to: {draft_path}")
        undecided = sum(1 for i in draft["stickers"].values() if i.get("selection") == "undecided")
        if undecided:
            print(f"Next: resolve {undecided} 'undecided' candidate(s) in review (Keep/Exclude per cluster).")
        else:
            print("Next: verify emojis in review, then approve:")
        print(f"  ./stickers curate {folder}")
        return

    if args.preflight:
        errors, warnings = validate_draft_for_export(draft, folder, strict_quality=args.strict_quality)
        out_guess = folder / args.out
        errors += verify_manifest_freshness(folder, draft, out_guess) if out_guess.exists() else []
        if warnings:
            print("\nQuality warnings:")
            for w in warnings[:20]:
                print(f"   {w}")
        if errors:
            print("\nPreflight FAILED:")
            for e in errors:
                print(f"   - {e}")
            sys.exit(1)
        print("\nPreflight passed.")
        entries, _, _ = select_manifest_entries(draft, folder=folder)
        meta = draft.get("meta", {}) or {}
        print(f"  Title: {meta.get('title')}  Author: {meta.get('author')}  "
              f"Stickers: {len(entries)}  Cover: {effective_cover(draft, entries)}  "
              f"Manifest: {manifest_digest(str(meta.get('title')), str(meta.get('author')), effective_cover(draft, entries), entries)[:12]}")
        return

    if args.approve:
        errs = approve_pack(draft)
        if errs:
            print("\nCannot approve:")
            for e in errs:
                print(f"   - {e}")
            sys.exit(1)
        save_draft(draft_path, draft)
        print(f"\nApproved pack revision {draft['revision']} (digest {draft['approval']['digest'][:12]}). Export is now allowed if image gates pass.")
        return

    run_classification = args.classify_kept or not (args.build_yaml or args.approve or args.preflight)
    if run_classification:
        kept_unclassified = [
            folder / fn
            for fn, item in draft["stickers"].items()
            if item.get("selection") == "keep"
            and not final_emoji_for_entry(item)
            and (folder / fn).exists()
        ]
        if kept_unclassified:
            provider = get_configured_provider(args.model)
            print(f"\nClassifying {len(kept_unclassified)} kept sticker(s) with {args.workers} workers (OpenRouter)...")
            done_count = [0]

            def process_sticker(p: Path):
                res = classify_single_image(provider, p)
                entry = draft["stickers"][p.name]
                entry["suggested_emojis"] = res.get("suggested_emojis")
                # Model suggestions never auto-approve: human promotes to final in review.
                entry["reason"] = res.get("reason", "")
                entry["confidence"] = res.get("confidence", 0.0)
                entry["review_status"] = res.get("review_status", "suggested")
                entry["tag_status"] = res.get("tag_status", "suggested")
                entry["tag_source"] = res.get("tag_source", "openrouter")
                invalidate_approval(draft, f"tag suggestion for {p.name}")
                done_count[0] += 1
                em_str = "".join(res.get("suggested_emojis") or []) or "(unresolved)"
                print(f"[{done_count[0]}/{len(kept_unclassified)}] {p.name} -> {em_str} ({res['confidence']:.2f}) {res['reason']}", flush=True)

            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                list(executor.map(process_sticker, kept_unclassified))
            bump_revision(draft, "tag suggestions")
            save_draft(draft_path, draft)
            print(f"Draft saved to {draft_path}")
            print("Next: in review, promote each suggestion to a final single emoji, then --approve.")
        else:
            print("\nAll kept stickers already carry a final emoji.")

    # Export (default when --build-yaml or no other action): strict preflight first.
    errors, warnings = validate_draft_for_export(draft, folder, strict_quality=args.strict_quality)
    if warnings:
        print("\nQuality warnings (non-blocking; use --strict-quality to enforce):")
        for w in warnings[:15]:
            print(f"   {w}")
    if errors:
        print(f"\nExport blocked by {len(errors)} preflight error(s):")
        for e in errors:
            print(f"   - {e}")
        # A failed export must not leave an apparently usable old YAML.
        out_guess = folder / args.out
        if out_guess.exists():
            try:
                out_guess.unlink()
                print(f"Removed stale {out_guess} so it cannot be mistaken for a good build.")
            except Exception:
                pass
            try:
                receipt_path_for_yaml(out_guess).unlink()
            except Exception:
                pass
        sys.exit(1)

    try:
        out_file = build_stickers_yaml(
            folder=folder, draft=draft,
            title=args.title or draft["meta"].get("title", ""),
            author=args.author or draft["meta"].get("author", ""),
            cover=args.cover, out_name=args.out,
            strict_quality=args.strict_quality,
        )
    except ValueError as e:
        print(f"\nExport failed: {e}")
        out_guess = folder / args.out
        if out_guess.exists():
            try:
                out_guess.unlink()
            except Exception:
                pass
        sys.exit(1)
    print(f"\nGenerated Signal stickers YAML: {out_file.resolve()}")
    receipt = json.loads(receipt_path_for_yaml(out_file).read_text(encoding="utf-8"))
    entries, _, _ = select_manifest_entries(draft, folder=folder)
    print(f"Pack: {receipt['title']} by {receipt['author']} — {len(entries)} stickers, cover {receipt['cover']}, manifest {receipt['manifest_digest'][:12]}")
    uploaded_marker = folder / "uploaded.yaml"
    if uploaded_marker.exists():
        print(f"Note: {uploaded_marker} exists from a prior upload; verify before re-uploading.")
    print(f"\nNext: ./stickers preview {folder}  (then ./stickers upload {folder} --yes for noninteractive)")


if __name__ == "__main__":
    main()
