#!/usr/bin/env python3
"""Signal Sticker Pack Classifier & Builder (Curation-First).

1. Inventory & Constraints: Checks 512x512, <300KB, transparency.
2. Perceptual Clustering: Groups near-identical variations using alpha-aware dHash.
3. Persistent Draft State: Tracks selection (keep/exclude/undecided), clusters, and tags in pack_draft.json.
4. Targeted VLM Classification: Classifies ONLY stickers marked 'keep'.
5. Build Manifest: Generates stickers.yaml from kept and validated stickers.

Usage:
  # Scan & cluster images without API calls
  python classify_and_build.py ./webp --scan

  # Classify kept stickers using OpenRouter (or Gemini / Claude)
  python classify_and_build.py ./webp --classify-kept --title "Grimassen"

  # Build stickers.yaml from approved draft
  python classify_and_build.py ./webp --build-yaml
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
        validate_emoji_sequence,
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
        validate_emoji_sequence,
    )

DEFAULT_DRAFT = "pack_draft.json"
DEFAULT_CACHE = "classification_cache.json"
SUPPORTED_EXTENSIONS = {".webp", ".png", ".apng", ".jpg", ".jpeg"}


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
    files: List[Path], max_distance: int = 6
) -> Tuple[Dict[str, List[str]], Dict[str, str], Dict[str, Dict[str, Any]]]:
    """Finds near-identical visual variations and partitions them into connected clusters.

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

    visited: Set[str] = set()
    clusters: Dict[str, List[str]] = {}
    file_to_cluster: Dict[str, str] = {}
    cluster_idx = 1

    for name in names:
        if name in visited or name not in adj:
            continue
        # BFS / Connected Component
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


def detect_visual_duplicates(
    files: List[Path], max_distance: int = 6
) -> Dict[str, Dict[str, Any]]:
    """Backward-compatible wrapper returning filename -> {'reference': ref, 'distance': dist}."""
    _, _, dupe_info = detect_visual_clusters(files, max_distance=max_distance)
    return dupe_info


def get_classification_prompt() -> str:
    """Builds system prompt for single-sticker classification with strict JSON requirement."""
    catalog = get_prompt_emoji_catalog()
    return (
        "Du bewertest Gesichtsausdruecke und Gesten auf Sticker-Bildern fuer Signal.\n"
        "Waehle 1 bis 3 Emojis (Reihenfolge: primaere Emotion, gefolgt von feineren Nuancen), "
        "die den Ausdruck, die Emotion oder das Overlay am praezisesten treffen.\n\n"
        "Erlaubte Emojis nach Kategorien:\n"
        f"{catalog}\n\n"
        "Regeln:\n"
        "- Achte auf Augen, Mund, Haende/Gesten und Overlays (Dampf, Traenen, Sonnenbrille, Herz etc.).\n"
        "- Overlays, Requisiten und markante Gesten haben Vorrang vor rein neutraler Mimik.\n"
        "- WICHTIG: Antworte AUSSCHLIESSLICH als valides JSON-Objekt ohne jeden Begleittext:\n"
        '{"emojis":["<emoji1>", "<emoji2_optional>"],"reason":"<max 8 Woerter Begruendung>","confidence":<0.0-1.0>}'
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
                                "Welche 1-3 Emojis passen am besten zu diesem Sticker? "
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
            content = msg.get("content") or msg.get("reasoning") or ""
            return parse_json_response(content)


class GeminiProvider(BaseProvider):
    """Google Gemini provider via direct REST API."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        )

    def classify(self, image_path: Path, prompt: str) -> Dict[str, Any]:
        mime_type, b64_data = encode_image_base64(image_path)
        payload = {
            "system_instruction": {"parts": [{"text": prompt}]},
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                        {"text": "Welche 1-3 Emojis passen am besten zu diesem Sticker?"},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 300},
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return parse_json_response(content)


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider via direct REST API."""

    def __init__(self, api_key: str, model: str = "claude-3-7-sonnet-latest"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.anthropic.com/v1/messages"

    def classify(self, image_path: Path, prompt: str) -> Dict[str, Any]:
        mime_type, b64_data = encode_image_base64(image_path)
        payload = {
            "model": self.model,
            "max_tokens": 300,
            "system": prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime_type, "data": b64_data},
                        },
                        {"text": "Welche 1-3 Emojis passen am besten zu diesem Sticker?"},
                    ],
                }
            ],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["content"][0]["text"]
            return parse_json_response(content)


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


def get_configured_provider(
    name: Optional[str] = None, model: Optional[str] = None
) -> BaseProvider:
    """Instantiates the appropriate provider based on args or environment variables."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    target = name.lower() if name else None
    if not target:
        if openrouter_key:
            target = "openrouter"
        elif gemini_key:
            target = "gemini"
        elif anthropic_key:
            target = "anthropic"
        else:
            sys.exit(
                "Error: No API key found. Please set OPENROUTER_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY."
            )

    if target == "openrouter":
        if not openrouter_key:
            sys.exit("Error: OPENROUTER_API_KEY environment variable not set.")
        m = model or "inclusionai/ling-3.0-flash-vl"
        print(f"Using Provider: OpenRouter (model: {m})")
        return OpenRouterProvider(openrouter_key, model=m)
    elif target in ("gemini", "google"):
        if not gemini_key:
            sys.exit("Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set.")
        m = model or "gemini-2.5-flash"
        print(f"Using Provider: Google Gemini (model: {m})")
        return GeminiProvider(gemini_key, model=m)
    elif target in ("anthropic", "claude"):
        if not anthropic_key:
            sys.exit("Error: ANTHROPIC_API_KEY environment variable not set.")
        m = model or "claude-3-7-sonnet-latest"
        print(f"Using Provider: Anthropic (model: {m})")
        return AnthropicProvider(anthropic_key, model=m)
    else:
        sys.exit(f"Error: Unknown provider '{name}'. Supported: openrouter, gemini, anthropic")


def check_signal_constraints(path: Path) -> List[str]:
    """Validates an image against Signal sticker specifications."""
    problems = []
    size_kb = path.stat().st_size / 1024
    if size_kb >= 300:
        problems.append(f"Size {size_kb:.1f} KB exceeds 300 KB limit")

    ext = path.suffix.lower()
    if ext not in {".png", ".webp", ".apng"}:
        problems.append(f"Format {ext} not recommended by Signal (PNG/WebP/APNG)")

    try:
        with Image.open(path) as img:
            if img.size != (512, 512):
                problems.append(f"Dimensions {img.size[0]}x{img.size[1]} != 512x512 px")
            if img.mode not in ("RGBA", "LA", "P"):
                problems.append(f"Image mode {img.mode} might lack transparency")
    except Exception as e:
        problems.append(f"Cannot read image: {e}")

    return problems


def classify_single_image(
    provider: BaseProvider, path: Path, retries: int = 3
) -> Dict[str, Any]:
    """Classifies a single sticker image with retries, enforcing strict emoji validation."""
    for attempt in range(retries):
        try:
            res = provider.classify(path, SYSTEM_PROMPT)
            raw_emojis = res.get("emojis") or res.get("emoji") or []
            if isinstance(raw_emojis, str):
                raw_text = raw_emojis
            elif isinstance(raw_emojis, (list, tuple)):
                raw_text = "".join(str(e) for e in raw_emojis)
            else:
                raw_text = ""

            is_valid, valid_emojis, err_msg = validate_emoji_sequence(raw_text)
            if not is_valid:
                # Try extracting known emojis from text
                extracted = extract_emojis(raw_text)
                if extracted:
                    valid_emojis = extracted[:3]
                    is_valid = True

            if is_valid and valid_emojis:
                primary = valid_emojis[0]
                return {
                    "emoji": primary,
                    "emojis": valid_emojis[:3],
                    "reason": str(res.get("reason", "OK"))[:80],
                    "confidence": float(res.get("confidence", 0.9)),
                    "review_status": "suggested",
                }
            else:
                return {
                    "emoji": "😐",
                    "emojis": ["😐"],
                    "reason": f"Unrecognized emoji: {raw_text[:40]}",
                    "confidence": 0.0,
                    "review_status": "needs_review",
                }
        except Exception as e:
            if attempt == retries - 1:
                return {
                    "emoji": "😐",
                    "emojis": ["😐"],
                    "reason": f"Classification error: {e}",
                    "confidence": 0.0,
                    "review_status": "needs_review",
                }
            time.sleep(1.5 * (attempt + 1))
    return {
        "emoji": "😐",
        "emojis": ["😐"],
        "reason": "Timeout/Max retries",
        "confidence": 0.0,
        "review_status": "needs_review",
    }


def load_or_create_draft(
    folder: Path,
    draft_path: Path,
    legacy_cache_path: Optional[Path] = None,
    files: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """Loads pack_draft.json, upgrading from legacy cache or scanning files if needed."""
    draft: Dict[str, Any] = {
        "version": 2,
        "meta": {"title": "Grimassen", "author": "tazztone", "cover": None},
        "similarity_groups": {},
        "stickers": {},
    }

    if draft_path.exists():
        try:
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Could not read draft from {draft_path}: {e}")
    elif legacy_cache_path and legacy_cache_path.exists():
        try:
            legacy = json.loads(legacy_cache_path.read_text(encoding="utf-8"))
            print(f"Migrating legacy cache ({len(legacy)} items) to pack_draft.json...")
            for fn, item in legacy.items():
                em_seq = item.get("emojis") or ([item["emoji"]] if "emoji" in item else None)
                sel = "exclude" if item.get("visual_dupe_of") or item.get("redundant_of") else "keep"
                draft["stickers"][fn] = {
                    "file_hash": "",
                    "selection": sel,
                    "similarity_group": None,
                    "suggested_emojis": em_seq,
                    "emojis": em_seq,
                    "confidence": float(item.get("confidence", 0.9)),
                    "reason": item.get("reason", ""),
                    "review_status": "approved" if sel == "keep" else "culled",
                }
        except Exception as e:
            print(f"Warning: Could not read legacy cache: {e}")

    # Synchronize with files on disk
    if files:
        clusters, file_to_cluster, dupe_info = detect_visual_clusters(files)
        draft["similarity_groups"] = clusters

        for p in files:
            fhash = compute_file_sha256(p)
            fn = p.name
            cid = file_to_cluster.get(fn)

            if fn not in draft["stickers"]:
                # New sticker: default standalone to keep, cluster variations to undecided
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
                }
            else:
                entry = draft["stickers"][fn]
                # Update cluster assignment
                entry["similarity_group"] = cid
                # Check for file content changes
                if entry.get("file_hash") and entry["file_hash"] != fhash:
                    print(f"Sticker file modified on disk: {fn} -> resetting review status.")
                    entry["file_hash"] = fhash
                    entry["review_status"] = "pending"
                elif not entry.get("file_hash"):
                    entry["file_hash"] = fhash

    return draft


def save_draft(draft_path: Path, draft: Dict[str, Any]) -> None:
    """Saves the persistent draft state."""
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")


def build_stickers_yaml(
    folder: Path,
    files: Optional[List[Path]] = None,
    cache: Optional[Dict[str, Any]] = None,
    draft: Optional[Dict[str, Any]] = None,
    title: str = "Grimassen",
    author: str = "tazztone",
    cover: Optional[str] = None,
    out_name: str = "stickers.yaml",
) -> Path:
    """Builds and writes stickers.yaml for signal-sticker-tool from kept stickers."""
    meta: Dict[str, Any] = {"title": title, "author": author}

    stickers_list = []

    # If draft provided (preferred)
    if draft and "stickers" in draft:
        meta_draft = draft.get("meta", {})
        meta["title"] = meta_draft.get("title", title)
        meta["author"] = meta_draft.get("author", author)
        cover_val = cover or meta_draft.get("cover")

        for fn, item in sorted(draft["stickers"].items()):
            if item.get("selection") != "keep":
                continue
            emojis = item.get("emojis") or item.get("suggested_emojis")
            if not emojis:
                continue
            chr_str = format_emoji_sequence(emojis)
            stickers_list.append({"chr": chr_str, "file": fn})

        if cover_val:
            meta["cover"] = cover_val
        elif stickers_list:
            meta["cover"] = stickers_list[0]["file"]

    # Backward compatibility with legacy (files, cache) call
    elif files is not None:
        c = cache or {}
        if cover:
            meta["cover"] = cover
        elif files:
            meta["cover"] = files[0].name

        for p in files:
            info = c.get(p.name, {})
            # Only exclude if explicitly marked redundant or deleted
            if info.get("selection") == "exclude":
                continue
            emojis = info.get("emojis") or info.get("emoji", "🙂")
            stickers_list.append({"chr": format_emoji_sequence(emojis), "file": p.name})

    doc = {"meta": meta, "stickers": stickers_list}
    out_path = folder / out_name
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Signal Sticker Pack Curation & Classifier"
    )
    parser.add_argument("folder", help="Directory containing sticker images")
    parser.add_argument("--title", default="Grimassen", help="Sticker pack title")
    parser.add_argument("--author", default="tazztone", help="Sticker pack author")
    parser.add_argument("--cover", default=None, help="Cover image filename")
    parser.add_argument("--provider", default=None, help="VLM Provider: openrouter, gemini, anthropic")
    parser.add_argument("--model", default=None, help="Model slug (e.g. inclusionai/ling-3.0-flash-vl)")
    parser.add_argument("--out", default="stickers.yaml", help="Output YAML filename")
    parser.add_argument("--draft", default=DEFAULT_DRAFT, help="Path to draft JSON")
    parser.add_argument("--cache", default=DEFAULT_CACHE, help="Path to legacy cache JSON")
    parser.add_argument("--workers", type=int, default=4, help="Parallel classification workers")
    parser.add_argument("--scan", action="store_true", help="Inventory and cluster without API calls")
    parser.add_argument(
        "--check-only", action="store_true", help="Alias for --scan"
    )
    parser.add_argument(
        "--classify-kept", action="store_true", help="Classify only stickers marked 'keep'"
    )
    parser.add_argument(
        "--build-yaml", action="store_true", help="Compile stickers.yaml from kept stickers"
    )
    parser.add_argument("--resume", action="store_true", help="Resume from existing draft/cache")
    parser.add_argument(
        "--dedupe", action="store_true", help="Run visual variation clustering"
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        sys.exit(f"Error: Directory '{folder}' does not exist.")

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not files:
        sys.exit(f"Error: No image files found in '{folder}'. Supported: {SUPPORTED_EXTENSIONS}")

    print(f"Found {len(files)} sticker images in {folder}")

    # Validate Signal constraints
    all_problems = {}
    for p in files:
        probs = check_signal_constraints(p)
        if probs:
            all_problems[p.name] = probs

    if all_problems:
        print("\nSignal Constraint Warnings:")
        for name, probs in all_problems.items():
            print(f"   {name}: {', '.join(probs)}")
    else:
        print("All stickers adhere to Signal constraints (512x512 px, <300 KB).")

    # Load/initialize draft
    draft_path = folder / args.draft if not Path(args.draft).is_absolute() else Path(args.draft)
    legacy_cache_path = folder / args.cache if not Path(args.cache).is_absolute() else Path(args.cache)
    draft = load_or_create_draft(folder, draft_path, legacy_cache_path, files)
    draft["meta"]["title"] = args.title
    draft["meta"]["author"] = args.author
    if args.cover:
        draft["meta"]["cover"] = args.cover

    # Visual clusters
    clusters = draft.get("similarity_groups", {})
    total_clustered = sum(len(members) for members in clusters.values())
    if clusters:
        print(f"\nDetected {len(clusters)} visual variation cluster(s) ({total_clustered} stickers total):")
        for cid, members in clusters.items():
            print(f"   {cid} ({len(members)} variations): {', '.join(members)}")
    else:
        print("\nNo near-identical visual variation clusters detected.")

    save_draft(draft_path, draft)

    if args.scan or args.check_only:
        print(f"\nScan completed. Draft saved to: {draft_path}")
        print("Next step: Curate variations in your browser or run:")
        print(f"  python review.py {folder}")
        return

    # Classification pass (Targeted: only for stickers where selection == 'keep' and emojis is missing)
    run_classification = args.classify_kept or not (args.scan or args.check_only or args.build_yaml)
    if run_classification:
        kept_unclassified = [
            folder / fn
            for fn, item in draft["stickers"].items()
            if item.get("selection") == "keep"
            and not (item.get("emojis") and item.get("confidence", 0) > 0)
            and (folder / fn).exists()
        ]

        if kept_unclassified:
            provider = get_configured_provider(args.provider, args.model)
            print(
                f"\nClassifying {len(kept_unclassified)} kept sticker(s) with {args.workers} workers..."
            )
            done_count = [0]

            def process_sticker(p: Path):
                res = classify_single_image(provider, p)
                draft["stickers"][p.name]["emojis"] = res.get("emojis")
                draft["stickers"][p.name]["suggested_emojis"] = res.get("emojis")
                draft["stickers"][p.name]["reason"] = res.get("reason", "")
                draft["stickers"][p.name]["confidence"] = res.get("confidence", 0.0)
                draft["stickers"][p.name]["review_status"] = res.get("review_status", "suggested")
                done_count[0] += 1
                em_str = "".join(res.get("emojis", []))
                print(
                    f"[{done_count[0]}/{len(kept_unclassified)}] {p.name} -> {em_str} "
                    f"({res['confidence']:.2f}) {res['reason']}",
                    flush=True,
                )

            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                list(executor.map(process_sticker, kept_unclassified))

            save_draft(draft_path, draft)
            print(f"Draft saved to {draft_path}")
        else:
            print("\nAll kept stickers already classified.")

    # Build stickers.yaml
    out_file = build_stickers_yaml(
        folder=folder,
        draft=draft,
        title=args.title,
        author=args.author,
        cover=args.cover,
        out_name=args.out,
    )
    print(f"\nGenerated Signal stickers YAML: {out_file.resolve()}")

    # Summary
    kept_count = sum(1 for item in draft["stickers"].values() if item.get("selection") == "keep")
    excluded_count = sum(1 for item in draft["stickers"].values() if item.get("selection") == "exclude")
    undecided_count = sum(1 for item in draft["stickers"].values() if item.get("selection") == "undecided")
    print(f"Pack Summary: {kept_count} Kept, {excluded_count} Excluded, {undecided_count} Undecided")

    print(f"\nNext step: Open review UI to curate and finalize:")
    print(f"  python review.py {folder}")


if __name__ == "__main__":
    main()
