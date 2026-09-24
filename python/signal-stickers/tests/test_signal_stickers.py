import json
import sys
from pathlib import Path

# Ensure signal-stickers directory is on sys.path
signal_stickers_dir = Path(__file__).resolve().parent.parent
if str(signal_stickers_dir) not in sys.path:
    sys.path.insert(0, str(signal_stickers_dir))

import pytest
try:
    from PIL import Image
except ImportError:
    from unittest.mock import MagicMock
    Image = MagicMock()
import yaml

from emojis import (
    EMOJI_REGISTRY,
    WHITELIST,
    extract_emojis,
    format_emoji_sequence,
    get_all_emojis,
    get_emoji_info,
    get_prompt_emoji_catalog,
    get_related_emojis,
    is_valid_emoji,
    is_valid_emoji_sequence,
)
from classify_and_build import (
    build_disambiguation_prompt,
    build_stickers_yaml,
    check_signal_constraints,
    compute_dhash,
    detect_visual_duplicates,
    hamming_distance,
    parse_json_response,
)


def test_emoji_registry_integrity():
    """Verify emoji registry is properly populated and has required fields."""
    all_emojis = get_all_emojis()
    assert len(all_emojis) >= 50
    assert "😀" in all_emojis
    assert "😎" in all_emojis
    assert "🤯" in all_emojis
    assert "🤮" in all_emojis

    info = get_emoji_info("😀")
    assert info is not None
    assert "name" in info
    assert "category" in info
    assert "description" in info

    assert is_valid_emoji("😀") is True
    assert is_valid_emoji("not_an_emoji") is False


def test_multi_emoji_helpers():
    """Verify multi-emoji extraction, sequencing, and validation."""
    extracted = extract_emojis("🤔🤨")
    assert extracted == ["🤔", "🤨"]

    # Duplicates removed, order preserved
    assert extract_emojis("🤔🤨🤔") == ["🤔", "🤨"]

    # Formatting limits to 3 emojis
    seq = format_emoji_sequence(["🤔", "🤨", "🧐", "😏"])
    assert seq == "🤔🤨🧐"
    assert len(extract_emojis(seq)) == 3

    # String format
    assert format_emoji_sequence("🤔🤨") == "🤔🤨"
    assert format_emoji_sequence(None) == "🙂"

    # Validation
    assert is_valid_emoji_sequence("🤔🤨") is True
    assert is_valid_emoji_sequence("🤔") is True
    assert is_valid_emoji_sequence("") is False


def test_prompt_catalog_and_related():
    """Verify catalog and related emoji recommendations."""
    catalog = get_prompt_emoji_catalog()
    assert "🤔" in catalog
    assert "Thinking" in catalog

    related = get_related_emojis("🤔", limit=6)
    assert len(related) == 6
    assert "🤔" in related
    assert "🤨" in related or "🧐" in related


def test_parse_json_response():
    """Verify JSON parsing handles raw JSON, Markdown-wrapped strings, and JSON lists."""
    # Direct JSON
    raw = '{"emoji": "😎", "reason": "wearing sunglasses", "confidence": 0.95}'
    parsed = parse_json_response(raw)
    assert parsed["emoji"] == "😎"
    assert parsed["confidence"] == 0.95

    # Multi-emoji JSON
    multi = '{"emojis": ["🤔", "🤨"], "reason": "skeptical thinking", "confidence": 0.9}'
    parsed_multi = parse_json_response(multi)
    assert parsed_multi["emojis"] == ["🤔", "🤨"]

    # Markdown wrapped list
    wrapped_list = (
        'Here is the result:\n```json\n[{"file": "001.webp", "emojis": ["🤔"], "reason": "thinking"}]\n```'
    )
    parsed_list = parse_json_response(wrapped_list)
    assert isinstance(parsed_list, list)
    assert parsed_list[0]["file"] == "001.webp"

    # Invalid JSON
    with pytest.raises(ValueError):
        parse_json_response("No json here")


def test_perceptual_dhash_and_duplicates(tmp_path):
    """Verify dHash detects identical and near-identical synthetic images."""
    img1_path = tmp_path / "img1.png"
    img2_path = tmp_path / "img2.png"
    img3_path = tmp_path / "img3.png"

    # Image 1: vertical stripes (alternating columns)
    im1 = Image.new("L", (64, 64))
    for x in range(64):
        for y in range(64):
            im1.putpixel((x, y), 255 if (x // 8) % 2 == 0 else 0)
    im1.save(img1_path)

    # Image 2: near-identical stripes (minor noise)
    im2 = Image.new("L", (64, 64))
    for x in range(64):
        for y in range(64):
            base = 255 if (x // 8) % 2 == 0 else 0
            im2.putpixel((x, y), max(0, min(255, base + (y % 4))))
    im2.save(img2_path)

    # Image 3: horizontal stripes (very different)
    im3 = Image.new("L", (64, 64))
    for x in range(64):
        for y in range(64):
            im3.putpixel((x, y), 255 if (y // 8) % 2 == 0 else 0)
    im3.save(img3_path)

    h1 = compute_dhash(img1_path)
    h2 = compute_dhash(img2_path)
    h3 = compute_dhash(img3_path)

    assert hamming_distance(h1, h2) <= 2
    assert hamming_distance(h1, h3) > 10

    dupes = detect_visual_duplicates([img1_path, img2_path, img3_path], max_distance=4)
    assert "img2.png" in dupes
    assert dupes["img2.png"]["reference"] == "img1.png"
    assert "img3.png" not in dupes



def test_check_signal_constraints(tmp_path):
    """Verify Signal constraint validator catches non-compliant images."""
    good_img = tmp_path / "valid.png"
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    im.save(good_img, "PNG")

    problems = check_signal_constraints(good_img)
    assert len(problems) == 0

    bad_dim = tmp_path / "wrong_dim.png"
    im_small = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    im_small.save(bad_dim, "PNG")

    problems = check_signal_constraints(bad_dim)
    assert any("!= 512x512" in p for p in problems)

    bad_ext = tmp_path / "sticker.bmp"
    im.save(bad_ext, "BMP")
    problems = check_signal_constraints(bad_ext)
    assert any("not recommended" in p for p in problems)


def test_build_stickers_yaml(tmp_path):
    """Verify YAML builder creates compliant stickers.yaml structure with multi-emoji support."""
    img1 = tmp_path / "001.webp"
    img2 = tmp_path / "002.webp"
    img3 = tmp_path / "003.webp"
    img1.touch()
    img2.touch()
    img3.touch()

    files = [img1, img2, img3]
    cache = {
        "001.webp": {"emoji": "😏", "reason": "smirk", "confidence": 0.9},
        "002.webp": {"emojis": ["🤔", "🤨"], "reason": "skeptic thinking", "confidence": 0.95},
        "003.webp": {"emoji": "😂", "emojis": ["😂", "🤣"], "confidence": 0.88},
    }

    yaml_file = build_stickers_yaml(
        folder=tmp_path,
        files=files,
        cache=cache,
        title="Test Pack",
        author="Tester",
        cover="001.webp",
    )

    assert yaml_file.exists()
    content = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))

    assert content["meta"]["title"] == "Test Pack"
    assert content["meta"]["author"] == "Tester"
    assert content["meta"]["cover"] == "001.webp"
    assert len(content["stickers"]) == 3
    assert content["stickers"][0] == {"chr": "😏", "file": "001.webp"}
    assert content["stickers"][1] == {"chr": "🤔🤨", "file": "002.webp"}
    assert content["stickers"][2] == {"chr": "😂🤣", "file": "003.webp"}


def test_build_disambiguation_prompt():
    """Verify disambiguation prompt includes related emojis and instructions against forcing."""
    prompt = build_disambiguation_prompt("🤔", ["img1.webp", "img2.webp"])
    assert "🤔" in prompt
    assert "redundant_of" in prompt
    assert "img1.webp" not in prompt or "2 Sticker-Bilder" in prompt

