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

from emojis import EMOJI_REGISTRY, WHITELIST, get_all_emojis, get_emoji_info, is_valid_emoji
from classify_and_build import (
    check_signal_constraints,
    parse_json_response,
    build_stickers_yaml,
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


def test_parse_json_response():
    """Verify JSON parsing handles raw JSON and Markdown-wrapped strings."""
    # Direct JSON
    raw = '{"emoji": "😎", "reason": "wearing sunglasses", "confidence": 0.95}'
    parsed = parse_json_response(raw)
    assert parsed["emoji"] == "😎"
    assert parsed["confidence"] == 0.95

    # Markdown wrapped
    wrapped = 'Here is the result:\n```json\n{"emoji": "😂", "reason": "joy tear", "confidence": 0.9}\n```'
    parsed = parse_json_response(wrapped)
    assert parsed["emoji"] == "😂"

    # Invalid JSON
    with pytest.raises(ValueError):
        parse_json_response("No json here")


def test_check_signal_constraints(tmp_path):
    """Verify Signal constraint validator catches non-compliant images."""
    # 1. Compliant image: 512x512 RGBA PNG < 300 KB
    good_img = tmp_path / "valid.png"
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    im.save(good_img, "PNG")

    problems = check_signal_constraints(good_img)
    assert len(problems) == 0

    # 2. Non-compliant dimensions: 256x256
    bad_dim = tmp_path / "wrong_dim.png"
    im_small = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    im_small.save(bad_dim, "PNG")

    problems = check_signal_constraints(bad_dim)
    assert any("!= 512x512" in p for p in problems)

    # 3. Non-recommended extension: .bmp
    bad_ext = tmp_path / "sticker.bmp"
    im.save(bad_ext, "BMP")
    problems = check_signal_constraints(bad_ext)
    assert any("not recommended" in p for p in problems)


def test_build_stickers_yaml(tmp_path):
    """Verify YAML builder creates compliant stickers.yaml structure."""
    img1 = tmp_path / "001.webp"
    img2 = tmp_path / "002.webp"
    img1.touch()
    img2.touch()

    files = [img1, img2]
    cache = {
        "001.webp": {"emoji": "😏", "reason": "smirk", "confidence": 0.9},
        "002.webp": {"emoji": "😂", "reason": "laugh", "confidence": 0.95},
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
    assert len(content["stickers"]) == 2
    assert content["stickers"][0] == {"chr": "😏", "file": "001.webp"}
    assert content["stickers"][1] == {"chr": "😂", "file": "002.webp"}
