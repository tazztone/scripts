#!/usr/bin/env python3
"""Signal Sticker Pack Classifier & Builder.

Classifies sticker images using Vision-Language Models (OpenRouter, Gemini, Claude, OpenAI)
and builds the `stickers.yaml` file required by `signal-sticker-tool`.
Performs full validation against official Signal Sticker guidelines (512x512, <300KB, max 200).

Usage:
  # Using OpenRouter (default model: inclusionai/ling-3.0-flash-vl)
  export OPENROUTER_API_KEY=sk-or-v1-...
  python classify_and_build.py ./webp --title "Grimassen" --author "tazztone"

  # Resume previously interrupted classification
  python classify_and_build.py ./webp --resume

  # Check sticker files against Signal requirements without calling API
  python classify_and_build.py ./webp --check-only
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        get_emoji_info,
        get_prompt_emoji_catalog,
        get_related_emojis,
        is_valid_emoji_sequence,
    )
except ImportError:
    from .emojis import (
        EMOJI_REGISTRY,
        WHITELIST,
        extract_emojis,
        format_emoji_sequence,
        get_emoji_info,
        get_prompt_emoji_catalog,
        get_related_emojis,
        is_valid_emoji_sequence,
    )

DEFAULT_CACHE = "classification_cache.json"
SUPPORTED_EXTENSIONS = {".webp", ".png", ".apng", ".jpg", ".jpeg"}

def compute_dhash(image_path: Path, hash_size: int = 8) -> int:
    """Computes a 64-bit difference hash (dHash) using Pillow.
    
    Fast, deterministic, and requires no external ML dependencies.
    """
    with Image.open(image_path) as img:
        resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
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


def detect_visual_duplicates(files: List[Path], max_distance: int = 6) -> Dict[str, Dict[str, Any]]:
    """Detects near-identical visual frames among sticker images.
    
    Returns mapping: filename -> {'reference': ref_name, 'distance': dist}
    """
    hashes: Dict[str, int] = {}
    for p in files:
        try:
            hashes[p.name] = compute_dhash(p)
        except Exception:
            pass

    dupe_info: Dict[str, Dict[str, Any]] = {}
    names = list(hashes.keys())
    for i in range(len(names)):
        n1 = names[i]
        for j in range(i + 1, len(names)):
            n2 = names[j]
            dist = hamming_distance(hashes[n1], hashes[n2])
            if dist <= max_distance:
                if n2 not in dupe_info or dist < dupe_info[n2]["distance"]:
                    dupe_info[n2] = {"reference": n1, "distance": dist}
    return dupe_info


def get_classification_prompt() -> str:
    """Builds the system prompt for single-sticker classification with multi-emoji support."""
    catalog = get_prompt_emoji_catalog()
    return (
        "Du bewertest Gesichtsausdruecke und Gesten auf Sticker-Bildern fuer Signal.\n"
        "Waehle 1 bis 3 Emojis (Reihenfolge: primaere Emotion, gefolgt von feineren Nuancen), "
        "die den Ausdruck, die Emotion oder das Overlay am praezisesten treffen.\n\n"
        "Erlaubte Emojis nach Kategorien:\n"
        f"{catalog}\n\n"
        "Regeln:\n"
        "- Achte auf Augen (offen, geschlossen, verdreht, Sterne), Mund (Zunge, offen, "
        "Zaehne, Kussmund, Schmollmund), Haende/Gesten (Kinn, Schlaefe, Lippen/Pst, Wange), "
        "und sichtbare Overlays (Dampf/Rauch aus Ohren, Traenen, zZZ, Herz, Sterne, "
        "Sonnenbrille, gruene Haut/Uebelkeit, Erbrechen, explodierender Kopf).\n"
        "- Overlays, Requisiten und markante Gesten haben Vorrang vor rein neutraler Mimik.\n"
        "- Falls ein Bild mehrere Gefuehle vereint (z.B. skeptisches Nachdenken oder weinend vor Lachen), "
        "gib bis zu 3 Emojis als Liste an.\n"
        "Antworte ausschliesslich als valides JSON:\n"
        '{"emojis":["<emoji1>", "<emoji2_optional>"],"reason":"<max 8 Woerter Begruendung>","confidence":<0.0-1.0>}'
    )


# Default system prompt for single image classification
SYSTEM_PROMPT = get_classification_prompt()


def build_disambiguation_prompt(provisional_emoji: str, filenames: List[str]) -> str:
    """Builds the comparative prompt for multi-image nuance & redundancy disambiguation."""
    related = get_related_emojis(provisional_emoji, limit=12)
    related_desc = ", ".join(
        f"{e} ({get_emoji_info(e)['name'] if get_emoji_info(e) else ''})" for e in related
    )
    return (
        f"Du siehst {len(filenames)} Sticker-Bilder fuer Signal, die vorlaeufig alle das Emoji '{provisional_emoji}' erhalten haben.\n\n"
        "Aufgabe:\n"
        "1. Vergleiche die Bilder direkt miteinander. Achte auf feine Nuancen:\n"
        "   - Augenbrauen (hochgezogen, gerunzelt, entspannt)\n"
        "   - Mund (geschlossen, schief/Smirk, offen, Zaehne, Mundwinkel)\n"
        "   - Blickrichtung (direkt, seitlich, nach oben, verdreht)\n"
        "   - Kopfneigung und Handgesten\n"
        "2. Falls ein Bild eine spezifischere Emotion oder Nuance zeigt, waehle 1 bis 3 passende Emojis.\n"
        f"   Erlaubte/empfohlene Emojis zur Differenzierung: {related_desc}\n"
        "3. WICHTIG (Keine kuenstlichen Erfindungen):\n"
        "   Wenn mehrere Bilder wirklich die EXAKT GLEICHE Mimik/Pose ohne nennenswerte Unterschiede zeigen (z.B. nahe Duplikate einer ComfyUI-Generierung):\n"
        f"   - Erfinde KEINE unpassenden Emojis! Behalte '{provisional_emoji}'.\n"
        "   - Setze 'redundant_of': '<dateiname_des_ersten_bildes>' fuer die ueberfluessigen Kopien, damit der Nutzer sie loeschen kann.\n\n"
        "Antworte ausschliesslich als valides JSON-Array:\n"
        '[\n'
        '  {"file":"<dateiname>", "emojis":["<primaer>", "<sekundaer_optional>"], "reason":"<kurze Begruendung>", "redundant_of": null}\n'
        ']'
    )


class BaseProvider:
    """Base class for VLM classification providers."""

    def classify(self, image_path: Path, prompt: str) -> Dict[str, Any]:
        raise NotImplementedError

    def classify_group(self, images: List[Path], prompt: str) -> List[Dict[str, Any]]:
        raise NotImplementedError



class OpenRouterProvider(BaseProvider):
    """OpenRouter provider supporting vision models (e.g., inclusionai/ling-3.0-flash-vl)."""

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
                        {"type": "text", "text": "Welche 1-3 Emojis passen am besten zu diesem Sticker?"},
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

    def classify_group(self, images: List[Path], prompt: str) -> List[Dict[str, Any]]:
        content_parts: List[Dict[str, Any]] = [
            {"type": "text", "text": prompt + "\n\nHier sind die Sticker-Bilder im direkten Vergleich:"}
        ]
        for idx, p in enumerate(images, 1):
            mt, b64 = encode_image_base64(p)
            content_parts.append({"type": "text", "text": f"\n--- Bild {idx}: {p.name} ---"})
            content_parts.append(
                {"type": "image_url", "image_url": {"url": f"data:{mt};base64,{b64}"}}
            )

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content_parts}],
            "temperature": 0.1,
            "max_tokens": 2000,
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            text = msg.get("content") or msg.get("reasoning") or ""
            res = parse_json_response(text)
            if isinstance(res, list):
                return res
            if isinstance(res, dict) and "stickers" in res:
                return res["stickers"]
            return [res]


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
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200},
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

    def classify_group(self, images: List[Path], prompt: str) -> List[Dict[str, Any]]:
        parts: List[Dict[str, Any]] = [
            {"text": prompt + "\n\nHier sind die Sticker-Bilder im direkten Vergleich:"}
        ]
        for idx, p in enumerate(images, 1):
            mt, b64 = encode_image_base64(p)
            parts.append({"text": f"\n--- Bild {idx}: {p.name} ---"})
            parts.append({"inline_data": {"mime_type": mt, "data": b64}})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000},
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            res = parse_json_response(content)
            if isinstance(res, list):
                return res
            if isinstance(res, dict) and "stickers" in res:
                return res["stickers"]
            return [res]


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
            "max_tokens": 200,
            "system": prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime_type, "data": b64_data},
                        },
                        {"type": "text", "text": "Welche 1-3 Emojis passen am besten zu diesem Sticker?"},
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

    def classify_group(self, images: List[Path], prompt: str) -> List[Dict[str, Any]]:
        content_parts: List[Dict[str, Any]] = [
            {"type": "text", "text": prompt + "\n\nHier sind die Sticker-Bilder im direkten Vergleich:"}
        ]
        for idx, p in enumerate(images, 1):
            mt, b64 = encode_image_base64(p)
            content_parts.append({"type": "text", "text": f"\n--- Bild {idx}: {p.name} ---"})
            content_parts.append(
                {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}}
            )

        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": content_parts}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["content"][0]["text"]
            res = parse_json_response(content)
            if isinstance(res, list):
                return res
            if isinstance(res, dict) and "stickers" in res:
                return res["stickers"]
            return [res]


def encode_image_base64(path: Path) -> Tuple[str, str]:
    """Encodes image file to base64 and determines MIME type."""
    mt = mimetypes.guess_type(path.name)[0] or "image/png"
    if mt == "image/apng":
        mt = "image/png"
    return mt, base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def parse_json_response(content: str) -> Any:
    """Safely extracts and parses JSON response (dict or list) from LLM output."""
    content = content.strip()
    if "```json" in content:
        start_idx = content.find("```json") + 7
        end_idx = content.find("```", start_idx)
        if end_idx != -1:
            content = content[start_idx:end_idx].strip()
    elif "```" in content:
        start_idx = content.find("```") + 3
        end_idx = content.find("```", start_idx)
        if end_idx != -1:
            content = content[start_idx:end_idx].strip()

    start_bracket = content.find("[")
    start_brace = content.find("{")

    if start_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
        end_bracket = content.rfind("]")
        if end_bracket != -1:
            try:
                res = json.loads(content[start_bracket : end_bracket + 1])
                if isinstance(res, list):
                    return res
            except Exception:
                pass

    if start_brace != -1:
        end_brace = content.rfind("}")
        if end_brace != -1:
            try:
                res = json.loads(content[start_brace : end_brace + 1])
                if isinstance(res, dict):
                    return res
            except Exception:
                pass

    try:
        res = json.loads(content)
        if isinstance(res, (dict, list)):
            return res
    except Exception:
        pass

    raise ValueError(f"Invalid JSON format in response: {content[:100]}")



def get_configured_provider(
    name: Optional[str] = None, model: Optional[str] = None
) -> BaseProvider:
    """Instantiates the appropriate provider based on args or environment variables."""
    # Priority when unspecified: OpenRouter -> Gemini -> Anthropic
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
    """Validates an image against Signal sticker specifications:

    - Resolution: exactly 512 x 512 px
    - Max size: < 300 KB
    - Format: PNG, WebP (or APNG)
    - Has transparency
    """
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
    provider: BaseProvider, path: Path, retries: int = 4
) -> Dict[str, Any]:
    """Classifies a single sticker image with retries, supporting multi-emoji tagging."""
    for attempt in range(retries):
        try:
            res = provider.classify(path, SYSTEM_PROMPT)
            raw_emojis = res.get("emojis") or res.get("emoji") or []
            valid_emojis = extract_emojis(format_emoji_sequence(raw_emojis))
            if not valid_emojis:
                raw_text = str(raw_emojis)
                valid_emojis = [e for e in WHITELIST if e in raw_text][:3]
                if not valid_emojis:
                    valid_emojis = ["🙂"]

            primary = valid_emojis[0]
            return {
                "emoji": primary,
                "emojis": valid_emojis[:3],
                "reason": str(res.get("reason", "OK"))[:80],
                "confidence": float(res.get("confidence", 0.9)),
            }
        except Exception as e:
            if attempt == retries - 1:
                return {
                    "emoji": "😐",
                    "emojis": ["😐"],
                    "reason": f"Classification error: {e}",
                    "confidence": 0.0,
                }
            time.sleep(1.5 * (attempt + 1))
    return {"emoji": "😐", "emojis": ["😐"], "reason": "Timeout/Max retries", "confidence": 0.0}


def run_disambiguation_pass(
    provider: BaseProvider,
    files: List[Path],
    cache: Dict[str, Dict[str, Any]],
    batch_size: int = 6,
) -> int:
    """Finds groups sharing the same primary emoji (count >= 2) and sends each group
    
    to the VLM to differentiate nuances and flag genuine redundancies.
    """
    file_map = {p.name: p for p in files}
    groups: Dict[str, List[str]] = {}
    for name, info in cache.items():
        if name not in file_map:
            continue
        primary = info.get("emoji") or (info.get("emojis") and info["emojis"][0]) or "🙂"
        groups.setdefault(primary, []).append(name)

    # Sort groups by count descending so biggest duplicate pools are addressed first
    sorted_groups = sorted(
        ((emoji, names) for emoji, names in groups.items() if len(names) >= 2),
        key=lambda x: len(x[1]),
        reverse=True,
    )

    if not sorted_groups:
        print("No duplicate emoji groups found to disambiguate.")
        return 0

    print(f"\n--- Running Multi-Image Nuance Disambiguation ({len(sorted_groups)} groups) ---")
    updated_count = 0

    for emoji, names in sorted_groups:
        print(f"\nDisambiguating group '{emoji}' ({len(names)} stickers)...")
        for i in range(0, len(names), batch_size):
            chunk = names[i : i + batch_size]
            chunk_paths = [file_map[n] for n in chunk]
            prompt = build_disambiguation_prompt(emoji, chunk)
            try:
                results = provider.classify_group(chunk_paths, prompt)
                if not isinstance(results, list):
                    results = [results]
                for item in results:
                    fname = item.get("file")
                    if fname and fname in cache:
                        new_emojis = extract_emojis(
                            format_emoji_sequence(item.get("emojis") or item.get("emoji") or [])
                        )
                        if new_emojis:
                            cache[fname]["emoji"] = new_emojis[0]
                            cache[fname]["emojis"] = new_emojis
                        if item.get("reason"):
                            cache[fname]["reason"] = str(item["reason"])[:80]
                        if item.get("redundant_of"):
                            cache[fname]["redundant_of"] = item["redundant_of"]
                        updated_count += 1
                        em_str = "".join(cache[fname].get("emojis", [cache[fname]["emoji"]]))
                        red_str = (
                            f" [Redundant of {cache[fname]['redundant_of']}]"
                            if cache[fname].get("redundant_of")
                            else ""
                        )
                        print(f"  {fname:<28} -> {em_str:<6} {cache[fname].get('reason', '')}{red_str}")
            except Exception as e:
                print(f"  Disambiguation failed for batch {chunk}: {e}")
    return updated_count


def build_stickers_yaml(
    folder: Path,
    files: List[Path],
    cache: Dict[str, Dict[str, Any]],
    title: str,
    author: str,
    cover: Optional[str] = None,
    out_name: str = "stickers.yaml",
) -> Path:
    """Builds and writes the stickers.yaml manifest for signal-sticker-tool."""
    meta: Dict[str, Any] = {"title": title, "author": author}
    if cover:
        meta["cover"] = cover
    elif files:
        meta["cover"] = files[0].name

    doc = {
        "meta": meta,
        "stickers": [
            {
                "chr": format_emoji_sequence(
                    cache.get(p.name, {}).get("emojis")
                    or cache.get(p.name, {}).get("emoji", "🙂")
                ),
                "file": p.name,
            }
            for p in files
        ],
    }

    out_path = folder / out_name
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Signal Sticker Pack VLM Classifier & YAML Builder"
    )
    parser.add_argument("folder", help="Directory containing sticker images")
    parser.add_argument("--title", default="Grimassen", help="Sticker pack title")
    parser.add_argument("--author", default="tazztone", help="Sticker pack author")
    parser.add_argument("--cover", default=None, help="Cover image filename (default: first sticker)")
    parser.add_argument("--provider", default=None, help="VLM Provider: openrouter, gemini, anthropic")
    parser.add_argument(
        "--model",
        default=None,
        help="Model slug (e.g., inclusionai/ling-3.0-flash-vl for OpenRouter)",
    )
    parser.add_argument("--out", default="stickers.yaml", help="Output YAML filename")
    parser.add_argument("--cache", default=DEFAULT_CACHE, help="Path to classification cache JSON")
    parser.add_argument("--workers", type=int, default=4, help="Parallel classification workers")
    parser.add_argument("--resume", action="store_true", help="Resume from existing cache")
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Run multi-image comparative disambiguation on duplicate emoji groups",
    )
    parser.add_argument(
        "--detect-visual-dupes",
        action="store_true",
        help="Compute perceptual dHash to flag near-identical visual variations",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only validate Signal constraints and visual hashes without calling API",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        sys.exit(f"Error: Directory '{folder}' does not exist.")

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not files:
        sys.exit(f"Error: No image files found in '{folder}'. Supported: {SUPPORTED_EXTENSIONS}")

    print(f"Found {len(files)} sticker images in {folder}")

    # Signal constraints check
    if len(files) > 200:
        print(f"WARNING: Signal allows a maximum of 200 stickers per pack (found {len(files)}).")

    all_problems = {}
    for p in files:
        probs = check_signal_constraints(p)
        if probs:
            all_problems[p.name] = probs

    if all_problems:
        print("\nSignal Constraint Warnings:")
        for name, probs in all_problems.items():
            print(f"   {name}: {', '.join(probs)}")
        print("   Upload might fail unless resized to 512x512 px / compressed under 300 KB.\n")
    else:
        print("All stickers adhere to Signal constraints (512x512 px, <300 KB).")

    # Visual duplicate detection (dHash)
    visual_dupes = detect_visual_duplicates(files)
    if visual_dupes:
        print(f"\nDetected {len(visual_dupes)} near-identical visual variation(s):")
        for fn, info in visual_dupes.items():
            print(f"   {fn} ~ {info['reference']} (Hamming distance: {info['distance']}/64)")
    else:
        print("No near-identical visual duplicates detected by perceptual hash.")

    if args.check_only:
        print("Check completed. Exiting (--check-only).")
        return

    # Cache loading
    cache_path = Path(args.cache)
    cache: Dict[str, Dict[str, Any]] = {}
    if (args.resume or args.dedupe or cache_path.exists()) and cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            print(f"Cache loaded: {len(cache)} existing classifications.")
        except Exception as e:
            print(f"Warning: Could not read cache: {e}")

    # Annotate cache with visual duplicate hints
    for fn, info in visual_dupes.items():
        if fn in cache:
            cache[fn]["visual_dupe_of"] = info["reference"]

    todo = [p for p in files if p.name not in cache]
    provider = None
    if todo or args.dedupe:
        provider = get_configured_provider(args.provider, args.model)

    if todo and provider:
        print(f"Classifying {len(todo)} stickers with {args.workers} workers...")
        done_count = [0]

        def process_sticker(p: Path):
            res = classify_single_image(provider, p)
            cache[p.name] = res
            done_count[0] += 1
            em_str = "".join(res.get("emojis", [res["emoji"]]))
            print(
                f"[{done_count[0]}/{len(todo)}] {p.name} -> {em_str} "
                f"({res['confidence']:.2f}) {res['reason']}",
                flush=True,
            )

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            list(executor.map(process_sticker, todo))

        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Cache saved to {cache_path}")
    elif not args.dedupe:
        print("All stickers already classified in cache.")

    # Deduplication pass if requested
    if args.dedupe and provider:
        updated = run_disambiguation_pass(provider, files, cache)
        if updated > 0:
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Cache updated with {updated} disambiguated stickers.")

    # Build stickers.yaml
    out_file = build_stickers_yaml(
        folder=folder,
        files=files,
        cache=cache,
        title=args.title,
        author=args.author,
        cover=args.cover,
        out_name=args.out,
    )
    print(f"\nGenerated Signal stickers YAML: {out_file.resolve()}")

    # Display least confident predictions
    low_conf = sorted(
        ((cache[p.name]["confidence"], p.name, cache[p.name]) for p in files if p.name in cache),
        key=lambda x: x[0],
    )[:10]

    print("\n--- Low Confidence Classifications (Review Recommended) ---")
    for conf, name, info in low_conf:
        em_str = "".join(info.get("emojis", [info["emoji"]]))
        print(f"  {conf:.2f}  {name:<28} {em_str}  {info['reason']}")

    print(f"\nNext step: Review and adjust stickers in your browser:")
    print(f"  python review.py {folder}")



if __name__ == "__main__":
    main()
