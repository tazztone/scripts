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

# Import shared emoji registry
try:
    from emojis import EMOJI_REGISTRY, WHITELIST
except ImportError:
    from .emojis import EMOJI_REGISTRY, WHITELIST

DEFAULT_CACHE = "classification_cache.json"
SUPPORTED_EXTENSIONS = {".webp", ".png", ".apng", ".jpg", ".jpeg"}

SYSTEM_PROMPT = (
    "Du bewertest Gesichtsausdruecke und Gesten auf Sticker-Bildern fuer Signal.\n"
    "Waehle GENAU EIN Emoji aus dieser erlaubten Liste, das den Ausdruck, die Emotion "
    "oder das Overlay am praezisesten trifft:\n"
    + " ".join(WHITELIST.keys())
    + "\n\n"
    "Regeln:\n"
    "- Achte auf Augen (offen, geschlossen, verdreht, Sterne), Mund (Zunge, offen, "
    "Zaehne, Kussmund, Schmollmund), Haende/Gesten (Kinn, Schlaefe, Lippen/Pst, Wange), "
    "und sichtbare Overlays (Dampf/Rauch aus Ohren, Traenen, zZZ, Herz, Sterne, "
    "Sonnenbrille, gruene Haut/Uebelkeit, Erbrechen, explodierender Kopf).\n"
    "- Overlays, Requisiten und markante Gesten haben Vorrang vor rein neutraler Mimik.\n"
    "- Waehle ausschliesslich ein Emoji aus der erlaubten Liste.\n"
    "Antworte ausschliesslich als valides JSON:\n"
    '{"emoji":"<ein Emoji>","reason":"<max 8 Woerter Begruendung>","confidence":<0.0-1.0>}'
)


class BaseProvider:
    """Base class for VLM classification providers."""

    def classify(self, image_path: Path, prompt: str) -> Dict[str, Any]:
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
                        {"type": "text", "text": "Welches Emoji passt am besten zu diesem Sticker?"},
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
                        {"text": "Welches Emoji passt am besten zu diesem Sticker?"},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 150},
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
            "max_tokens": 150,
            "system": prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime_type, "data": b64_data},
                        },
                        {"type": "text", "text": "Welches Emoji passt am besten zu diesem Sticker?"},
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


def parse_json_response(content: str) -> Dict[str, Any]:
    """Safely extracts and parses JSON response from LLM output."""
    content = content.strip()
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        content = content[start : end + 1]
    res = json.loads(content)
    if not isinstance(res, dict) or "emoji" not in res:
        raise ValueError(f"Invalid JSON format in response: {content}")
    return res


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
    """Classifies a single sticker image with retries."""
    for attempt in range(retries):
        try:
            res = provider.classify(path, SYSTEM_PROMPT)
            emoji = res.get("emoji", "").strip()
            # If model returned emoji + extra text, extract first emoji
            if emoji not in WHITELIST:
                # Fallback to closest match or neutral if invalid
                matched = [e for e in WHITELIST if e in emoji]
                if matched:
                    res["emoji"] = matched[0]
                else:
                    raise ValueError(f"Emoji '{emoji}' not in registered whitelist")
            return {
                "emoji": res["emoji"],
                "reason": res.get("reason", "OK")[:50],
                "confidence": float(res.get("confidence", 0.9)),
            }
        except Exception as e:
            if attempt == retries - 1:
                return {
                    "emoji": "😐",
                    "reason": f"Classification error: {e}",
                    "confidence": 0.0,
                }
            time.sleep(1.5 * (attempt + 1))
    return {"emoji": "😐", "reason": "Timeout/Max retries", "confidence": 0.0}


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
                "chr": cache.get(p.name, {}).get("emoji", "🙂"),
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
        "--check-only", action="store_true", help="Only validate Signal constraints without classification"
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

    if args.check_only:
        print("Check completed. Exiting (--check-only).")
        return

    # Cache loading
    cache_path = Path(args.cache)
    cache: Dict[str, Dict[str, Any]] = {}
    if (args.resume or cache_path.exists()) and cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            print(f"Cache loaded: {len(cache)} existing classifications.")
        except Exception as e:
            print(f"Warning: Could not read cache: {e}")

    todo = [p for p in files if p.name not in cache]
    if todo:
        provider = get_configured_provider(args.provider, args.model)
        print(f"Classifying {len(todo)} stickers with {args.workers} workers...")
        done_count = [0]

        def process_sticker(p: Path):
            res = classify_single_image(provider, p)
            cache[p.name] = res
            done_count[0] += 1
            print(
                f"[{done_count[0]}/{len(todo)}] {p.name} -> {res['emoji']} "
                f"({res['confidence']:.2f}) {res['reason']}",
                flush=True,
            )

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            list(executor.map(process_sticker, todo))

        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Cache saved to {cache_path}")
    else:
        print("All stickers already classified in cache.")

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
        print(f"  {conf:.2f}  {name:<28} {info['emoji']}  {info['reason']}")

    print(f"\nNext step: Review and adjust stickers in your browser:")
    print(f"  python review.py {folder}")


if __name__ == "__main__":
    main()
