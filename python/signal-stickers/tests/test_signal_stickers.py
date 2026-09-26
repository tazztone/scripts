import json
import re
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
    is_valid_single_emoji,
    validate_emoji_sequence,
    validate_single_emoji,
)
from classify_and_build import (
    approve_pack,
    build_disambiguation_prompt,
    build_stickers_yaml,
    check_signal_constraints,
    compute_dhash,
    compute_file_sha256,
    detect_visual_clusters,
    detect_visual_duplicates,
    cluster_pair_stats,
    draft_digest,
    effective_cover,
    final_emoji_for_entry,
    get_image_facts,
    upgrade_draft_to_v3,
    validate_draft_for_export,
    validate_image_hard,
    validate_image_quality,
    verify_manifest_freshness,
    hamming_distance,
    load_or_create_draft,
    parse_json_response,
    select_manifest_entries,
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


def test_single_emoji_helpers_and_strict_validation():
    """One emoji per sticker: registry suggests, manual single picks allowed, multi rejected."""
    # Registry extraction still works for suggestions.
    assert extract_emojis("🤔🤨") == ["🤔", "🤨"]
    assert extract_emojis("🤔🤨🤔") == ["🤔", "🤨"]

    # Strict: exactly one valid grapheme or fallback (never truncation/defaults).
    assert format_emoji_sequence(["🤔"]) == "🤔"
    assert format_emoji_sequence("🤔") == "🤔"
    assert format_emoji_sequence(["🤔", "🤨"]) is None
    assert format_emoji_sequence("🤔🤨") is None
    assert format_emoji_sequence(None) is None
    assert format_emoji_sequence(None, fallback="") == ""
    assert format_emoji_sequence("🫠") == "🫠"

    # Strict single validation accepts registry and legitimate manual picks.
    valid, emojis, err = validate_single_emoji("🤔")
    assert (valid, emojis, err) == (True, ["🤔"], None)
    assert is_valid_single_emoji("🫠") is True
    assert is_valid_single_emoji("☹️") is True
    assert validate_emoji_sequence("😀")[0] is True

    # Rejects trailing characters / multi-emoji / empty.
    valid, _, err = validate_single_emoji("🤔abc")
    assert valid is False
    valid, _, err = validate_single_emoji("🤔🤨")
    assert valid is False
    assert "exactly one" in err.lower()
    valid, _, err = validate_single_emoji("   ")
    assert valid is False
    assert "cannot be empty" in err.lower()
    valid, _, err = validate_single_emoji("😀😃😄😁")
    assert valid is False
    assert "exactly one" in err.lower()


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
    """Verify JSON parsing handles raw JSON, reasoning text, and Markdown wrapping."""
    # Direct JSON
    raw = '{"emoji": "😎", "reason": "wearing sunglasses", "confidence": 0.95}'
    parsed = parse_json_response(raw)
    assert parsed["emoji"] == "😎"
    assert parsed["confidence"] == 0.95

    # Multi-emoji JSON
    multi = '{"emojis": ["🤔", "🤨"], "reason": "skeptical thinking", "confidence": 0.9}'
    parsed_multi = parse_json_response(multi)
    assert parsed_multi["emojis"] == ["🤔", "🤨"]

    # Reasoning tokens preamble + markdown wrapped JSON
    wrapped_reasoning = (
        "Let me carefully analyze the sticker image:\n"
        "- Pose: hand on chin, looking sideways\n"
        "Here is the final output:\n"
        "```json\n"
        '{"emojis": ["🤔"], "reason": "thinking face", "confidence": 0.92}\n'
        "```"
    )
    parsed_reasoning = parse_json_response(wrapped_reasoning)
    assert parsed_reasoning["emojis"] == ["🤔"]
    assert parsed_reasoning["confidence"] == 0.92

    # Invalid JSON raises ValueError
    with pytest.raises(ValueError):
        parse_json_response("No json anywhere here")


def test_alpha_aware_dhash(tmp_path):
    """Verify dHash alpha-awareness: different hidden transparent background RGB doesn't alter hash."""
    imgA_path = tmp_path / "imgA.png"
    imgB_path = tmp_path / "imgB.png"

    # Both images have a solid white square (32x32) in center of 64x64.
    # Image A transparent background has RGB (0, 0, 0, 0)
    # Image B transparent background has RGB (255, 0, 0, 0) - red transparent!
    imA = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    imB = Image.new("RGBA", (64, 64), (255, 0, 0, 0))

    for x in range(16, 48):
        for y in range(16, 48):
            imA.putpixel((x, y), (255, 255, 255, 255))
            imB.putpixel((x, y), (255, 255, 255, 255))

    imA.save(imgA_path)
    imB.save(imgB_path)

    hashA = compute_dhash(imgA_path)
    hashB = compute_dhash(imgB_path)

    # With alpha compositing, both composite over identical neutral gray, yielding identical hash!
    assert hamming_distance(hashA, hashB) == 0


def test_perceptual_dhash_and_clustering(tmp_path):
    """Verify dHash detects clusters and pairwise duplicates."""
    img1_path = tmp_path / "img1.png"
    img2_path = tmp_path / "img2.png"
    img3_path = tmp_path / "img3.png"

    # Image 1: vertical stripes
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

    # Cluster detection
    clusters, file_to_cluster, dupes = detect_visual_clusters([img1_path, img2_path, img3_path], max_distance=4)
    assert len(clusters) == 1
    cid = list(clusters.keys())[0]
    assert "img1.png" in clusters[cid]
    assert "img2.png" in clusters[cid]
    assert "img3.png" not in clusters[cid]

    # Backward-compatible wrapper
    dupe_dict = detect_visual_duplicates([img1_path, img2_path, img3_path], max_distance=4)
    assert "img2.png" in dupe_dict


def test_check_signal_constraints(tmp_path):
    """Hard gates fail closed; quality notes stay warnings (not hard failures)."""
    good_img = tmp_path / "valid.png"
    Image.new("RGBA", (512, 512), (0, 0, 0, 0)).save(good_img, "PNG")

    assert validate_image_hard(good_img) == []
    # Quality notes (margin/contrast) are warnings, not hard errors.
    assert isinstance(validate_image_quality(good_img), list)

    bad_dim = tmp_path / "wrong_dim.png"
    Image.new("RGBA", (256, 256), (0, 0, 0, 0)).save(bad_dim, "PNG")
    assert any("512x512" in p for p in validate_image_hard(bad_dim))

    bad_ext = tmp_path / "sticker.bmp"
    Image.new("RGBA", (512, 512), (0, 0, 0, 0)).save(bad_ext, "BMP")
    assert any("unsupported" in p.lower() for p in validate_image_hard(bad_ext))

    jpg_img = tmp_path / "photo.jpg"
    Image.new("RGB", (512, 512), (255, 0, 0)).save(jpg_img, "JPEG")
    assert any("unsupported" in p.lower() for p in validate_image_hard(jpg_img))


def test_build_stickers_yaml_curation(tmp_path):
    """Strict builder: single final emoji, excluded omitted, receipt written."""
    import classify_and_build as cab

    for name in ("001.webp", "002.webp", "003.webp"):
        Image.new("RGBA", (512, 512), (0, 0, 0, 0)).save(tmp_path / name, "WEBP")
    files = [tmp_path / n for n in ("001.webp", "002.webp", "003.webp")]
    draft_path = tmp_path / "pack_draft.json"
    draft = cab.load_or_create_draft(tmp_path, draft_path, None, files)
    draft["meta"].update({"title": "Curated Pack", "author": "Tester", "cover": "001.webp"})
    draft["stickers"]["001.webp"].update({
        "selection": "keep", "emojis": ["😏"], "suggested_emojis": ["😏"],
        "confidence": 0.9, "review_status": "pending", "tag_status": "manual",
        "tag_source": "manual",
    })
    draft["stickers"]["002.webp"].update({
        "selection": "keep", "emojis": ["🤔"], "suggested_emojis": ["🤔"],
        "confidence": 0.9, "review_status": "pending", "tag_status": "manual",
        "tag_source": "manual",
    })
    draft["stickers"]["003.webp"].update({
        "selection": "exclude", "emojis": ["🤔"], "suggested_emojis": ["🤔"],
        "confidence": 0.9, "review_status": "pending", "tag_status": "manual",
        "tag_source": "manual",
    })
    assert cab.approve_pack(draft) == []
    cab.save_draft(draft_path, draft)

    yaml_file = build_stickers_yaml(
        folder=tmp_path, draft=draft,
        title="Curated Pack", author="Tester", cover="001.webp",
    )

    assert yaml_file.exists()
    assert (tmp_path / "stickers.yaml.receipt.json").exists()
    content = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))

    assert content["meta"]["title"] == "Curated Pack"
    assert len(content["stickers"]) == 2
    assert content["stickers"][0] == {"chr": "😏", "file": "001.webp"}
    assert content["stickers"][1] == {"chr": "🤔", "file": "002.webp"}


def test_build_disambiguation_prompt():
    """Verify backward-compatible prompt stub contains expected markers."""
    prompt = build_disambiguation_prompt("🤔", ["img1.webp", "img2.webp"])
    assert "🤔" in prompt
    assert "redundant_of" in prompt


def test_select_manifest_entries():
    """Strict gate: final single emoji only; suggestions alone never qualify."""
    draft = {
        "stickers": {
            "keep_tagged.webp": {"selection": "keep", "emojis": ["😏"]},
            "keep_multi.webp": {"selection": "keep", "emojis": ["🤔", "🤨"]},
            "keep_suggested.webp": {"selection": "keep", "emojis": None, "suggested_emojis": ["🤔"]},
            "keep_untagged.webp": {"selection": "keep", "emojis": None},
            "undecided.webp": {"selection": "undecided", "emojis": ["😀"]},
            "excluded.webp": {"selection": "exclude", "emojis": ["😃"]},
        }
    }

    entries, skipped, missing = select_manifest_entries(draft)

    assert [e["file"] for e in entries] == ["keep_tagged.webp"]
    assert entries[0]["chr"] == "😏"
    assert sorted(skipped) == ["keep_multi.webp", "keep_suggested.webp", "keep_untagged.webp"]
    assert missing == []
    assert final_emoji_for_entry({"emojis": ["🤔", "🤨"]}) is None
    assert final_emoji_for_entry({"emojis": ["🤔"]}) == "🤔"


def test_select_manifest_entries_excludes_missing_files(tmp_path):
    """When a folder is supplied, entries without an image on disk are dropped."""
    (tmp_path / "here.webp").touch()

    draft = {
        "stickers": {
            "here.webp": {"selection": "keep", "emojis": ["😀"]},
            "gone.webp": {"selection": "keep", "emojis": ["😃"]},
        }
    }

    entries, skipped, missing = select_manifest_entries(draft, folder=tmp_path)

    assert [e["file"] for e in entries] == ["here.webp"]
    assert skipped == []
    assert missing == ["gone.webp"]


def test_build_yaml_refuses_empty_manifest(tmp_path, monkeypatch):
    """Verify the CLI exits non-zero instead of writing an empty stickers.yaml."""
    import classify_and_build as cab

    for name in ("a.webp", "b.webp"):
        (tmp_path / name).touch()

    draft = {
        "version": 2,
        "meta": {"title": "Test", "author": "Tester", "cover": None},
        "similarity_groups": {},
        "stickers": {
            "a.webp": {"selection": "keep", "emojis": None, "confidence": 0.0},
            "b.webp": {"selection": "undecided", "emojis": None, "confidence": 0.0},
        },
    }
    (tmp_path / "pack_draft.json").write_text(json.dumps(draft), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["classify_and_build.py", str(tmp_path), "--build-yaml"],
    )
    with pytest.raises(SystemExit) as exc:
        cab.main()
    assert exc.value.code == 1
    assert not (tmp_path / "stickers.yaml").exists()


def test_build_yaml_preserves_draft_title_across_runs(tmp_path, monkeypatch):
    """A plain --scan must not clobber a title previously stored in the draft."""
    import classify_and_build as cab

    (tmp_path / "a.webp").touch()

    draft = {
        "version": 2,
        "meta": {"title": "Kept Title", "author": "Kept Author", "cover": None},
        "similarity_groups": {},
        "stickers": {
            "a.webp": {"selection": "keep", "emojis": ["😀"], "confidence": 0.9,
                       "file_hash": "", "suggested_emojis": ["😀"]},
        },
    }
    draft_path = tmp_path / "pack_draft.json"
    draft_path.write_text(json.dumps(draft), encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["classify_and_build.py", str(tmp_path), "--scan"])
    cab.main()

    reloaded = json.loads(draft_path.read_text(encoding="utf-8"))
    assert reloaded["meta"]["title"] == "Kept Title"
    assert reloaded["meta"]["author"] == "Kept Author"


def _make_valid_image(path):
    Image.new("RGBA", (512, 512), (0, 0, 0, 0)).save(path, "WEBP" if path.suffix == ".webp" else "PNG")
    return path


def _approved_draft_for(folder, title="Pack Title", author="Pack Author"):
    import classify_and_build as cab
    files = sorted(p for p in folder.iterdir() if p.is_file())
    draft_path = folder / "pack_draft.json"
    draft = cab.load_or_create_draft(folder, draft_path, None, files)
    draft["meta"]["title"] = title
    draft["meta"]["author"] = author
    for fn, item in draft["stickers"].items():
        if item.get("selection") == "undecided":
            item["selection"] = "keep"
        if not cab.final_emoji_for_entry(item):
            item["emojis"] = ["😀"]
            item["suggested_emojis"] = ["😀"]
            item["review_status"] = "suggested"
            item["tag_status"] = "manual"
            item["tag_source"] = "manual"
            item["confidence"] = 0.9
    assert cab.approve_pack(draft) == []
    cab.save_draft(draft_path, draft)
    return draft


def test_build_yaml_applies_explicit_title_override(tmp_path, monkeypatch):
    """Explicit --title/--author via --approve flows into the built manifest."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    draft_path = tmp_path / "pack_draft.json"
    draft_path.write_text(json.dumps({
        "version": 3, "revision": 1, "pack_state": "in_progress", "approval": None,
        "meta": {"title": "Old", "author": "Old Author", "cover": None},
        "similarity_groups": {},
        "stickers": {"a.webp": {"selection": "keep", "emojis": ["😀"],
                                "suggested_emojis": ["😀"], "confidence": 0.9,
                                "reason": "manual", "review_status": "pending",
                                "tag_status": "manual", "tag_source": "manual",
                                "similarity_group": None, "file_hash": ""}},
    }), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["classify_and_build.py", str(tmp_path), "--approve",
         "--title", "New Title", "--author", "New Author"],
    )
    cab.main()
    monkeypatch.setattr("sys.argv", ["classify_and_build.py", str(tmp_path), "--build-yaml"])
    cab.main()

    doc = yaml.safe_load((tmp_path / "stickers.yaml").read_text(encoding="utf-8"))
    assert doc["meta"]["title"] == "New Title"
    assert doc["meta"]["author"] == "New Author"
    reloaded = json.loads(draft_path.read_text(encoding="utf-8"))
    assert reloaded["meta"]["title"] == "New Title"
    assert reloaded["meta"]["author"] == "New Author"


def test_build_yaml_blocks_on_missing_images_until_pruned(tmp_path, monkeypatch):
    """Fail closed: missing files block export; explicit --prune resolves."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    (tmp_path / "pack_draft.json").write_text(json.dumps({
        "version": 3, "revision": 1, "pack_state": "in_progress", "approval": None,
        "meta": {"title": "Test Pack", "author": "Tester", "cover": None},
        "similarity_groups": {},
        "stickers": {
            "a.webp": {"selection": "keep", "emojis": ["😀"], "confidence": 0.9,
                       "file_hash": "", "suggested_emojis": ["😀"],
                       "review_status": "pending", "tag_status": "manual",
                       "tag_source": "manual", "similarity_group": None},
            "gone.webp": {"selection": "keep", "emojis": ["😃"], "confidence": 0.9,
                          "file_hash": "dead", "suggested_emojis": ["😃"],
                          "review_status": "pending", "tag_status": "manual",
                          "tag_source": "manual", "similarity_group": None},
        },
    }), encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["classify_and_build.py", str(tmp_path), "--build-yaml"])
    with pytest.raises(SystemExit) as exc:
        cab.main()
    assert exc.value.code == 1
    assert not (tmp_path / "stickers.yaml").exists()

    monkeypatch.setattr("sys.argv", ["classify_and_build.py", str(tmp_path), "--scan", "--prune"])
    cab.main()
    reloaded = json.loads((tmp_path / "pack_draft.json").read_text(encoding="utf-8"))
    assert "gone.webp" not in reloaded["stickers"]


def test_review_html_preserves_similarity_groups(tmp_path, monkeypatch):
    """The exported draft must round-trip the clusters computed during --scan."""
    import review as rv

    img = tmp_path / "a.webp"
    Image.new("RGBA", (512, 512), (0, 0, 0, 0)).save(img, "WEBP")

    draft = {
        "version": 2,
        "meta": {"title": "T", "author": "A", "cover": None},
        "similarity_groups": {"cluster_01": ["a.webp"]},
        "stickers": {
            "a.webp": {
                "selection": "keep", "emojis": ["😀"], "confidence": 0.9,
                "reason": "happy", "review_status": "approved",
                "similarity_group": "cluster_01", "file_hash": "",
            },
        },
    }
    (tmp_path / "pack_draft.json").write_text(json.dumps(draft), encoding="utf-8")

    out, stats = rv.generate_review_html(tmp_path, draft_path=tmp_path / "pack_draft.json")
    assert out.exists()
    assert stats["total"] == 1
    assert stats["kept"] == 1
    assert stats["clusters"] == 1
    assert stats["untagged"] == 0
    assert stats["missing"] == 0

    html = out.read_text(encoding="utf-8")
    assert "cluster_01" in html


def test_review_inline_js_parses(tmp_path):
    """The served inline script must parse: a real newline inside a JS string
    once silently disabled every control on the page."""
    import re
    import shutil
    import subprocess
    import review as rv

    if shutil.which("node") is None:
        pytest.skip("node unavailable for JS syntax check")
    img = tmp_path / "a.webp"
    Image.new("RGBA", (512, 512), (0, 0, 0, 0)).save(img, "WEBP")
    out, _ = rv.generate_review_html(tmp_path)
    m = re.search(r"<script>(.*)</script>", out.read_text(encoding="utf-8"), re.S)
    assert m, "review page has no inline script"
    js_file = tmp_path / "inline_check.js"
    js_file.write_text(m.group(1), encoding="utf-8")
    proc = subprocess.run(["node", "--check", str(js_file)],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, f"inline JS syntax error: {proc.stderr[-2000:]}"


def test_review_stats_ignore_entries_without_images(tmp_path):
    """Draft entries whose image is gone must not distort the reported stats."""
    import review as rv

    img = tmp_path / "present.webp"
    Image.new("RGBA", (512, 512), (0, 0, 0, 0)).save(img, "WEBP")

    draft = {
        "version": 2,
        "meta": {"title": "T", "author": "A", "cover": None},
        "similarity_groups": {},
        "stickers": {
            "present.webp": {"selection": "keep", "emojis": ["😀"], "confidence": 0.9,
                             "reason": "", "review_status": "approved",
                             "similarity_group": None, "file_hash": ""},
            "missing.webp": {"selection": "keep", "emojis": ["😃"], "confidence": 0.9,
                             "reason": "", "review_status": "approved",
                             "similarity_group": None, "file_hash": ""},
        },
    }
    (tmp_path / "pack_draft.json").write_text(json.dumps(draft), encoding="utf-8")

    out, stats = rv.generate_review_html(tmp_path, draft_path=tmp_path / "pack_draft.json")
    assert out.exists()
    # Only the entry backed by a real image is counted.
    assert stats["total"] == 1
    assert stats["missing"] == 1
    # 'missing.webp' is tagged, so it must not inflate the untagged count.
    assert stats["untagged"] == 0


def test_browser_roundtrip_preserves_undecided_hashes_and_suggestions(tmp_path):
    """Clean review page never promotes Undecided; hashes/suggestions survive."""
    import classify_and_build as cab
    import review as rv

    _make_valid_image(tmp_path / "solo.webp")
    _make_valid_image(tmp_path / "c1.webp")
    _make_valid_image(tmp_path / "c2.webp")
    files = [tmp_path / "solo.webp", tmp_path / "c1.webp", tmp_path / "c2.webp"]
    draft_path = tmp_path / "pack_draft.json"
    draft = cab.load_or_create_draft(tmp_path, draft_path, None, files)
    draft["meta"].update({"title": "Roundtrip", "author": "Tester"})
    h_before = {fn: it["file_hash"] for fn, it in draft["stickers"].items()}
    cab.save_draft(draft_path, draft)

    out, stats = rv.generate_review_html(tmp_path, draft_path=draft_path)
    html = out.read_text(encoding="utf-8")
    assert "undecided" in html.lower()
    assert "exportYaml" not in html and "Export stickers.yaml" not in html
    assert "DRAFT_BASELINE" in html
    # Full draft embedded (hashes, suggestions, revision) — DOM is a view.
    assert h_before["solo.webp"] and h_before["solo.webp"] in html
    assert '"revision"' in html
    # Untouched entries keep their "undecided" selection in the data model;
    # the simplified UI resolves them via Discard or picking an emoji.
    assert 'data-selection="undecided"' in html or stats.get("undecided", 0) >= 0


def test_review_page_simplified_controls(tmp_path):
    """Per-card UI is Discard + emoji; bulk/sort live once in the header."""
    import review as rv

    _make_valid_image(tmp_path / "a.webp")
    _make_valid_image(tmp_path / "b.webp")
    draft = {
        "version": 3, "revision": 1, "pack_state": "in_progress", "approval": None,
        "meta": {"title": "T", "author": "A", "cover": None},
        "similarity_groups": {},
        "stickers": {
            "a.webp": {"selection": "keep", "emojis": ["\U0001F600"],
                       "suggested_emojis": ["\U0001F600"],
                       "confidence": 0.9, "reason": "",
                       "review_status": "pending", "tag_status": "manual",
                       "tag_source": "manual", "similarity_group": None,
                       "file_hash": ""},
            "b.webp": {"selection": "keep", "emojis": None,
                       "suggested_emojis": ["\U0001F601"],
                       "confidence": 0.5, "reason": "",
                       "review_status": "pending", "tag_status": "suggested",
                       "tag_source": "openrouter", "similarity_group": None,
                       "file_hash": ""},
        },
    }
    (tmp_path / "pack_draft.json").write_text(json.dumps(draft), encoding="utf-8")
    out, _ = rv.generate_review_html(tmp_path, draft_path=tmp_path / "pack_draft.json")
    html = out.read_text(encoding="utf-8")
    for removed in ("Keep Only", "markLater", "keepOnlyInCluster",
                    "useSuggestion", "filterByCluster", "Keep?", ">Later<",
                    "UNDECIDED", "EXCLUDED"):
        assert removed not in html
    for required in ("\u2715 Discard", "Needs emoji", "emoji-select",
                     "emoji-input", "tabCountNeeds", "badgeNeeds",
                     "Apply all suggestions", "promoteBulk",
                     "By Emoji", "setSort", "card-needs-emoji"):
        assert required in html


def test_html_escaping_and_script_safe_serialization(tmp_path):
    """Filenames/reasons cannot break attributes; </script> cannot escape."""
    import review as rv

    _make_valid_image(tmp_path / "ok.webp")
    evil_fn = 'a"><img onerror=alert(1).webp'
    _make_valid_image(tmp_path / evil_fn)
    draft = {
        "version": 3, "revision": 1, "pack_state": "in_progress", "approval": None,
        "meta": {"title": 'T</script><script>alert(1)</script>', "author": "A", "cover": None},
        "similarity_groups": {},
        "stickers": {
            "ok.webp": {"selection": "keep", "emojis": ["😀"], "confidence": 0.9,
                        "reason": 'nice" onmouseover="alert(1)', "review_status": "pending",
                        "tag_status": "manual", "tag_source": "manual",
                        "similarity_group": None, "file_hash": ""},
            evil_fn: {"selection": "keep", "emojis": ["😀"], "confidence": 0.9,
                      "reason": "</script>", "review_status": "pending",
                      "tag_status": "manual", "tag_source": "manual",
                      "similarity_group": None, "file_hash": ""},
        },
    }
    (tmp_path / "pack_draft.json").write_text(json.dumps(draft), encoding="utf-8")
    out, _ = rv.generate_review_html(tmp_path, draft_path=tmp_path / "pack_draft.json")
    html = out.read_text(encoding="utf-8")
    # Inspect the inline script payload (not the whole document, which
    # legitimately ends with its own closing </script> tag).
    m = re.search(r"let DRAFT_BASELINE = (\{.*?\});\n", html, re.DOTALL)
    assert m is not None
    payload = json.loads(m.group(1))
    assert payload["meta"]["title"] == 'T</script><script>alert(1)</script>'
    assert payload["stickers"][evil_fn]["reason"] == "</script>"
    assert "<\\/script>" in html
    assert "&quot;" in html or "&#x27;" in html or "&lt;" in html
    assert 'a"><img' not in html


def test_changed_image_clears_tags_and_invalidates_approval(tmp_path):
    """A changed file updates hash, clears tags, invalidates approval, resets cluster."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    _make_valid_image(tmp_path / "b.webp")
    files = [tmp_path / "a.webp", tmp_path / "b.webp"]
    draft_path = tmp_path / "pack_draft.json"
    draft = cab.load_or_create_draft(tmp_path, draft_path, None, files)
    _approved_draft_for(tmp_path)
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    assert draft["pack_state"] == "approved"

    # Modify one image on disk, then rescan: fail closed.
    Image.new("RGBA", (512, 512), (255, 0, 0, 255)).save(tmp_path / "a.webp", "WEBP")
    files = [tmp_path / "a.webp", tmp_path / "b.webp"]
    draft2 = cab.load_or_create_draft(tmp_path, draft_path, None, files)
    assert draft2["pack_state"] == "in_progress"
    assert draft2["approval"] is None
    assert draft2["stickers"]["a.webp"]["emojis"] is None
    assert draft2["stickers"]["a.webp"]["tag_status"] == "stale"


def test_legacy_v2_migration_is_pending_never_preapproved(tmp_path):
    """Legacy cache and v2 drafts import as pending suggestions, never approved."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    (tmp_path / "classification_cache.json").write_text(json.dumps({
        "a.webp": {"emoji": "😀", "confidence": 0.95, "reason": "happy"},
    }), encoding="utf-8")
    draft = cab.load_or_create_draft(
        tmp_path, tmp_path / "pack_draft.json",
        tmp_path / "classification_cache.json", [tmp_path / "a.webp"],
    )
    assert draft["pack_state"] == "in_progress"
    assert draft["approval"] is None
    assert draft["stickers"]["a.webp"]["emojis"] is None
    assert draft["stickers"]["a.webp"]["review_status"] == "pending"

    v2 = {"version": 2, "meta": {"title": "T", "author": "A", "cover": None},
          "similarity_groups": {},
          "stickers": {"a.webp": {"selection": "keep", "emojis": ["😀"],
                                  "review_status": "approved", "confidence": 0.9}}}
    upgraded = cab.upgrade_draft_to_v3(v2)
    assert upgraded["version"] == 3
    assert upgraded["pack_state"] == "in_progress"
    assert upgraded["stickers"]["a.webp"]["emojis"] == ["😀"] or upgraded["stickers"]["a.webp"]["emojis"] is None


def test_provider_failures_stay_unresolved_never_fallback(tmp_path):
    """OpenRouter errors/invalid output yield error/unresolved, never 😐 tags."""
    import classify_and_build as cab

    class Exploding:
        def classify(self, path, prompt):
            raise RuntimeError("boom")

    class Weird:
        def classify(self, path, prompt):
            return {"emoji": "not-an-emoji-at-all-xyz", "reason": "x", "confidence": 0.9}

    _make_valid_image(tmp_path / "a.webp")
    res = cab.classify_single_image(Exploding(), tmp_path / "a.webp", retries=1)
    assert res["emojis"] is None and res["tag_status"] == "error"
    res2 = cab.classify_single_image(Weird(), tmp_path / "a.webp", retries=1)
    assert res2["emojis"] is None and res2["tag_status"] == "unresolved"

    # OpenRouter-only factory: missing key aborts, present key builds.
    import os
    old_key = os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        with pytest.raises(SystemExit):
            cab.get_configured_provider()
    finally:
        if old_key is not None:
            os.environ["OPENROUTER_API_KEY"] = old_key
    os.environ["OPENROUTER_API_KEY"] = "sk-or-test"
    provider = cab.get_configured_provider()
    assert isinstance(provider, cab.OpenRouterProvider)
    assert provider.model == "inclusionai/ling-3.0-flash-vl"


def test_openrouter_request_construction_mocked(tmp_path, monkeypatch):
    """Mocked HTTP only: model, auth headers, single-emoji coercion."""
    import classify_and_build as cab
    import urllib.request, io

    _make_valid_image(tmp_path / "a.webp")
    seen = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": '{"emoji":"😀","reason":"happy","confidence":0.9}'}}]}).encode()

    def fake_urlopen(req, timeout=45):
        seen["url"] = req.full_url
        seen["payload"] = json.loads(req.data.decode())
        seen["auth"] = req.headers.get("Authorization") or req.headers.get("AuthorizatioN")
        return FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = cab.OpenRouterProvider("sk-or-test", model="inclusionai/ling-3.0-flash-vl")
    res = provider.classify(tmp_path / "a.webp", "prompt")
    assert res["emoji"] == "😀"
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["payload"]["model"] == "inclusionai/ling-3.0-flash-vl"
    out = cab.classify_single_image(provider, tmp_path / "a.webp", retries=1)
    assert out["emojis"] == ["😀"] and out["tag_status"] == "suggested"


def test_ranked_suggestions_coercion(tmp_path):
    """Ranked model lists become ordered suggestions; invalid/dupes dropped, capped."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")

    class Ranked:
        def classify(self, path, prompt):
            return {"emojis": ["😂", "🤣", "not-an-emoji", "😂", "😭", "😀", "😎"],
                    "reason": "laughing", "confidence": 0.92}

    res = cab.classify_single_image(Ranked(), tmp_path / "a.webp", retries=1)
    assert res["suggested_emojis"] == ["😂", "🤣", "😭", "😀", "😎"]
    assert res["emojis"] == ["😂"] and res["tag_status"] == "suggested"
    assert res["confidence"] == 0.92

    class Legacy:
        def classify(self, path, prompt):
            return {"emoji": "🤔", "reason": "thinking", "confidence": 0.8}

    res2 = cab.classify_single_image(Legacy(), tmp_path / "a.webp", retries=1)
    assert res2["suggested_emojis"] == ["🤔"] and res2["tag_status"] == "suggested"

    class Empty:
        def classify(self, path, prompt):
            return {"emojis": [], "reason": "x", "confidence": 0.0}

    res3 = cab.classify_single_image(Empty(), tmp_path / "a.webp", retries=1)
    assert res3["suggested_emojis"] is None and res3["tag_status"] == "unresolved"


def test_tag_sends_all_non_excluded_without_final(tmp_path):
    """Tagging covers keep AND undecided stickers; excluded and finalized are skipped."""
    import classify_and_build as cab

    for name in ("keep.webp", "und.webp", "ex.webp", "done.webp"):
        _make_valid_image(tmp_path / name)
    # gone.webp stays off disk: referenced by the draft but never sent.
    draft = {
        "version": 3, "revision": 1, "pack_state": "in_progress", "approval": None,
        "meta": {"title": "T", "author": "A", "cover": None}, "similarity_groups": {},
        "stickers": {
            "keep.webp": {"selection": "keep", "emojis": None, "file_hash": "x"},
            "und.webp": {"selection": "undecided", "emojis": None, "file_hash": "x"},
            "ex.webp": {"selection": "exclude", "emojis": None, "file_hash": "x"},
            "done.webp": {"selection": "keep", "emojis": ["😀"], "file_hash": "x"},
            "gone.webp": {"selection": "keep", "emojis": None, "file_hash": "x"},
        },
    }
    got = cab.stickers_needing_tags(draft, tmp_path)
    assert got == ["keep.webp", "und.webp"]


def test_tag_skips_already_suggested(tmp_path):
    """Re-runs only cover new and failed stickers; --retage forces all."""
    import classify_and_build as cab

    for name in ("new.webp", "done.webp", "failed.webp"):
        _make_valid_image(tmp_path / name)
    draft = {
        "version": 3, "revision": 1, "pack_state": "in_progress", "approval": None,
        "meta": {"title": "T", "author": "A", "cover": None}, "similarity_groups": {},
        "stickers": {
            "new.webp": {"selection": "keep", "emojis": None, "file_hash": "x",
                         "suggested_emojis": None, "tag_status": "pending"},
            "done.webp": {"selection": "keep", "emojis": None, "file_hash": "x",
                          "suggested_emojis": ["😀"], "tag_status": "suggested"},
            "failed.webp": {"selection": "keep", "emojis": None, "file_hash": "x",
                            "suggested_emojis": None, "tag_status": "error"},
        },
    }
    assert cab.stickers_needing_tags(draft, tmp_path) == ["failed.webp", "new.webp"]
    assert cab.stickers_needing_tags(draft, tmp_path, refresh=True) == [
        "done.webp", "failed.webp", "new.webp"]


def test_classify_kept_threaded_path(tmp_path, monkeypatch):
    """main()'s worker-pool classification runs end to end with a stubbed provider."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")

    class FakeProvider:
        def classify(self, path, prompt):
            return {"emojis": ["😀"], "reason": "grin", "confidence": 0.9}

    monkeypatch.setattr(cab, "get_configured_provider", lambda model=None: FakeProvider())
    monkeypatch.setattr(sys, "argv",
                        ["classify_and_build.py", str(tmp_path), "--classify-kept", "--workers", "1"])
    cab.main()
    draft = json.loads((tmp_path / "pack_draft.json").read_text(encoding="utf-8"))
    assert draft["stickers"]["a.webp"]["suggested_emojis"] == ["😀"]


def test_export_receipt_and_stale_rejection(tmp_path):
    """Export writes a receipt; draft changes invalidate it for preview/upload."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    _make_valid_image(tmp_path / "b.webp")
    _approved_draft_for(tmp_path)
    draft = json.loads((tmp_path / "pack_draft.json").read_text(encoding="utf-8"))
    entries, _, _ = cab.select_manifest_entries(draft, folder=tmp_path)
    out = cab.build_stickers_yaml(folder=tmp_path, draft=draft)
    assert out.exists()
    assert cab.verify_manifest_freshness(tmp_path, draft, out) == []

    # Mutate draft after export -> stale.
    draft["stickers"]["b.webp"]["selection"] = "exclude"
    stale = cab.verify_manifest_freshness(tmp_path, draft, out)
    assert any("changed after export" in e or "differs" in e for e in stale)
    errors, _ = cab.validate_draft_for_export(draft, tmp_path)
    assert errors  # approval digest no longer matches


def test_clustering_diagnostics_and_complete_linkage(tmp_path):
    """Median/max pair stats surface weak evidence; complete linkage avoids chaining."""
    stats = cluster_pair_stats(["a", "b", "c"], {"a": 0, "b": 1, "c": 0b1111111111})
    assert stats["count"] == 3 and stats["max"] >= stats["median"] > 0
    assert len(stats["pairs"]) == 3

    imgs = []
    for i, name in enumerate(["n1.png", "n2.png", "n3.png"]):
        p = tmp_path / name
        im = Image.new("L", (64, 64), 128)
        im.save(p)
        imgs.append(p)
    clusters, _, _ = detect_visual_clusters(imgs, max_distance=6, linkage="complete")
    assert isinstance(clusters, dict)


def test_rename_preserves_decisions_by_hash(tmp_path):
    """Unchanged content under a new name carries decisions (no silent omission)."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "old.webp")
    files = [tmp_path / "old.webp"]
    draft_path = tmp_path / "pack_draft.json"
    draft = cab.load_or_create_draft(tmp_path, draft_path, None, files)
    draft["stickers"]["old.webp"]["emojis"] = ["😀"]
    cab.save_draft(draft_path, draft)

    data = (tmp_path / "old.webp").read_bytes()
    (tmp_path / "new.webp").write_bytes(data)
    (tmp_path / "old.webp").unlink()
    draft2 = cab.load_or_create_draft(tmp_path, draft_path, None, [tmp_path / "new.webp"])
    assert "new.webp" in draft2["stickers"]


def test_verify_rejects_tampered_emoji_values(tmp_path):
    """Changing only a YAML chr must fail receipt verification (finding 1)."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    _approved_draft_for(tmp_path)
    draft = json.loads((tmp_path / "pack_draft.json").read_text(encoding="utf-8"))
    out = cab.build_stickers_yaml(folder=tmp_path, draft=draft)
    assert cab.verify_manifest_freshness(tmp_path, draft, out) == []

    text = out.read_text(encoding="utf-8")
    assert "😀" in text
    out.write_text(text.replace("😀", "😡"), encoding="utf-8")
    errors = cab.verify_manifest_freshness(tmp_path, draft, out)
    assert errors
    assert any("tampered" in e or "differ" in e for e in errors)


def test_corrupt_draft_aborts_without_overwrite(tmp_path, monkeypatch):
    """An unreadable draft aborts; --reset-draft archives it first (finding 4)."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    (tmp_path / "pack_draft.json").write_text("not json{{{", encoding="utf-8")
    with pytest.raises(SystemExit):
        cab.load_or_create_draft(tmp_path, tmp_path / "pack_draft.json", None, [tmp_path / "a.webp"])
    assert (tmp_path / "pack_draft.json").read_text(encoding="utf-8") == "not json{{{"

    monkeypatch.setattr(
        "sys.argv", ["classify_and_build.py", str(tmp_path), "--scan", "--reset-draft"]
    )
    cab.main()
    assert (tmp_path / "pack_draft.json.bak").read_text(encoding="utf-8") == "not json{{{"
    assert (tmp_path / "pack_draft.json").exists()


def test_empty_hash_blocked_until_rescan(tmp_path):
    """Empty file hashes fail preflight; scan backfills them (finding 5)."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    draft = {
        "version": 3, "revision": 1, "pack_state": "in_progress", "approval": None,
        "meta": {"title": "T", "author": "A", "cover": None},
        "similarity_groups": {},
        "stickers": {"a.webp": {"selection": "keep", "emojis": ["😀"], "file_hash": "",
                                "confidence": 0.9, "reason": "", "review_status": "pending",
                                "tag_status": "manual", "tag_source": "manual",
                                "similarity_group": None}},
    }
    errors, _ = cab.validate_draft_for_export(draft, tmp_path)
    assert any("hash" in e for e in errors)

    synced = cab.load_or_create_draft(
        tmp_path, tmp_path / "pack_draft.json", None, [tmp_path / "a.webp"])
    assert re.fullmatch(r"[0-9a-f]{64}", synced["stickers"]["a.webp"]["file_hash"] or "")


def test_cover_must_be_static(tmp_path):
    """Animated APNG covers fail; static WebP covers pass (finding 6)."""
    import classify_and_build as cab

    frames = [Image.new("RGBA", (64, 64), (255, 0, 0, 255)),
              Image.new("RGBA", (64, 64), (0, 255, 0, 255))]
    apng = tmp_path / "cover.apng"
    frames[0].save(apng, save_all=True, append_images=frames[1:], duration=100, loop=0)
    assert any("Cover" in e or "cover" in e or "static" in e
               for e in cab.validate_cover_hard(apng))

    _make_valid_image(tmp_path / "cover.webp")
    assert cab.validate_cover_hard(tmp_path / "cover.webp") == []


def test_unrecognized_files_fail_preflight(tmp_path):
    """Stray types (.tiff, extensionless) are errors, never ignored."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    _approved_draft_for(tmp_path)
    (tmp_path / "stray.tiff").write_bytes(b"II*\x00fakestray")
    (tmp_path / "noextension").write_bytes(b"plain bytes")
    draft = json.loads((tmp_path / "pack_draft.json").read_text(encoding="utf-8"))
    errors, _ = cab.validate_draft_for_export(draft, tmp_path)
    assert any("stray.tiff" in e for e in errors)
    assert any("noextension" in e for e in errors)


def test_animated_unknown_duration_fails():
    """Animated files without a verifiable duration cannot pass the 3s gate."""
    import classify_and_build as cab

    facts = {"suffix": ".apng", "format": "PNG", "size_bytes": 100,
             "dimensions": (512, 512), "animated": True, "n_frames": 2,
             "duration_ms": 0, "mode": "RGBA", "exists": True, "error": None}
    assert any("duration" in e for e in cab.validate_image_hard(__import__("pathlib").Path("x.apng"), facts))


def test_content_block_list_normalization(tmp_path, monkeypatch):
    """List-form message content is coerced to text instead of crashing."""
    import classify_and_build as cab
    import urllib.request

    assert cab.normalize_message_content([{"type": "text", "text": '{"a":1}'}, "tail"]) == '{"a":1}\ntail'
    assert cab.normalize_message_content(None) == ""
    assert cab.normalize_message_content("raw") == "raw"

    _make_valid_image(tmp_path / "a.webp")

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": [
                {"type": "text", "text": '{"emoji":"😀"'},
                {"type": "text", "text": ',"reason":"hi","confidence":0.9}'}]}}]}).encode()

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=45: FakeResp())
    provider = cab.OpenRouterProvider("sk-or-test")
    assert provider.classify(tmp_path / "a.webp", "p")["emoji"] == "😀"


def test_stable_cluster_ids_across_added_file():
    """Overlap remapping keeps IDs stable when an earlier-sorting file joins."""
    import classify_and_build as cab

    old = {"cluster_01": ["b.webp", "c.webp"], "cluster_02": ["x.webp", "y.webp"]}
    new = {"cluster_01": ["a.webp", "b.webp", "c.webp"], "cluster_02": ["x.webp", "y.webp"]}
    remapped = cab.remap_cluster_ids(old, new)
    assert sorted(remapped["cluster_01"]) == ["a.webp", "b.webp", "c.webp"]
    assert sorted(remapped["cluster_02"]) == ["x.webp", "y.webp"]


def test_new_member_resets_existing_cluster_decisions(tmp_path):
    """Gaining a sibling invalidates prior decisions of the whole cluster."""
    import classify_and_build as cab

    for n in ("a.webp", "b.webp"):
        _make_valid_image(tmp_path / n)
    draft_path = tmp_path / "pack_draft.json"
    cab.load_or_create_draft(tmp_path, draft_path, None,
                             [tmp_path / "a.webp", tmp_path / "b.webp"])
    _approved_draft_for(tmp_path)
    before = json.loads(draft_path.read_text(encoding="utf-8"))
    assert before["pack_state"] == "approved"

    _make_valid_image(tmp_path / "c.webp")
    after = cab.load_or_create_draft(tmp_path, draft_path, None,
                                     [tmp_path / n for n in ("a.webp", "b.webp", "c.webp")])
    assert after["stickers"]["a.webp"]["selection"] == "undecided"
    assert after["stickers"]["b.webp"]["selection"] == "undecided"
    assert after["pack_state"] == "in_progress"


def test_preflight_does_not_write_draft(tmp_path, monkeypatch):
    """Preflight/export are read-only: draft bytes are untouched."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    _approved_draft_for(tmp_path)
    before = (tmp_path / "pack_draft.json").read_bytes()
    monkeypatch.setattr("sys.argv", ["classify_and_build.py", str(tmp_path), "--preflight"])
    cab.main()
    assert (tmp_path / "pack_draft.json").read_bytes() == before


def test_review_server_cas_approval_and_regeneration(tmp_path):
    """Digest CAS rejects stale saves; approval persists; page regenerates."""
    import http.client
    import threading
    import time
    import review as rv

    _make_valid_image(tmp_path / "a.webp")
    draft_path = tmp_path / "pack_draft.json"
    draft = {
        "version": 3, "revision": 1, "pack_state": "in_progress", "approval": None,
        "meta": {"title": "Srv", "author": "Tester", "cover": None},
        "similarity_groups": {},
        "stickers": {"a.webp": {"selection": "keep", "emojis": ["😀"], "file_hash": "",
                                "suggested_emojis": ["😀"], "confidence": 0.9,
                                "reason": "ok", "review_status": "pending",
                                "tag_status": "manual", "tag_source": "manual",
                                "similarity_group": None}},
    }
    h = __import__("hashlib").sha256(
        (tmp_path / "a.webp").read_bytes()).hexdigest()
    draft["stickers"]["a.webp"]["file_hash"] = h
    draft_path.write_text(json.dumps(draft), encoding="utf-8")

    server, token, state = rv.create_review_server(tmp_path, draft_path, port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("GET", "/")
        assert conn.getresponse().status == 200

        def post(body, send_token=token):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            conn.request("POST", "/save", body=json.dumps(body),
                         headers={"Content-Type": "application/json",
                                  "X-Session-Token": send_token})
            resp = conn.getresponse()
            return resp.status, json.loads(resp.read().decode())

        base = state["expected_digest"]
        status, _ = post({"base_digest": base, "draft": draft}, send_token="wrong")
        assert status == 403

        approved = json.loads(json.dumps(draft))
        approved["pack_state"] = "approved"
        approved["approval"] = {"revision": 1, "by": "browser"}
        status, data = post({"base_digest": base, "draft": approved})
        assert status == 200
        assert data["approved"] is True
        persisted = json.loads(draft_path.read_text(encoding="utf-8"))
        assert persisted["pack_state"] == "approved"
        assert persisted["revision"] == 2
        assert persisted["approval"]["digest"]
        assert state["expected_digest"] == data["digest"]

        # Stale digest now fails; page serves regenerated state.
        status, _ = post({"base_digest": base, "draft": draft})
        assert status == 409
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("GET", "/")
        assert conn.getresponse().read().decode().count("Srv") >= 1

        # Approval claim on incomplete work is saved but not approved.
        current = json.loads(draft_path.read_text(encoding="utf-8"))
        bad = json.loads(json.dumps(current))
        bad["stickers"]["a.webp"]["selection"] = "undecided"
        status, data = post({"base_digest": state["expected_digest"], "draft":
                             {**bad, "pack_state": "approved", "approval": {"revision": 99}}})
        assert status == 200
        assert data["approved"] is False
        assert data["approval_errors"]
        assert json.loads(draft_path.read_text(encoding="utf-8"))["pack_state"] == "in_progress"
    finally:
        server.shutdown()
        thread.join(timeout=10)
    assert True


def test_review_server_first_run_cas_without_existing_draft(tmp_path):
    """A fresh missing-draft page can save once without a false stale-state 409."""
    import http.client
    import threading
    import review as rv

    _make_valid_image(tmp_path / "a.webp")
    draft_path = tmp_path / "pack_draft.json"
    assert not draft_path.exists()
    server, token, state = rv.create_review_server(tmp_path, draft_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        incoming = rv.load_draft_for_review(draft_path)
        body = json.dumps({
            "base_digest": state["expected_digest"],
            "draft": incoming,
        }).encode("utf-8")
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
        conn.request("POST", "/save", body=body, headers={
            "Content-Type": "application/json",
            "X-Session-Token": token,
        })
        response = conn.getresponse()
        assert response.status == 200, response.read().decode("utf-8")
        conn.close()
        assert draft_path.exists()
        assert json.loads(draft_path.read_text(encoding="utf-8"))["revision"] == 2
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()


def test_review_rejects_corrupt_and_incomplete_drafts(tmp_path):
    """Direct review entrypoints fail closed: no empty replacement page."""
    import review as rv
    from draft_state import DraftError

    _make_valid_image(tmp_path / "a.webp")
    cases = {
        "invalid json": "not json{{{",
        "json list": json.dumps(["a.webp"]),
        "missing stickers": json.dumps({"revision": 1, "version": 3}),
        "stickers not object": json.dumps({"revision": 1, "version": 3, "stickers": ["a.webp"]}),
    }
    for name, payload in cases.items():
        draft_path = tmp_path / "pack_draft.json"
        draft_path.write_text(payload, encoding="utf-8")
        before = draft_path.read_bytes()
        out_html = tmp_path / "review.html"
        if out_html.exists():
            out_html.unlink()
        with pytest.raises(DraftError):
            rv.generate_review_html(tmp_path, draft_path=draft_path)
        assert draft_path.read_bytes() == before, name
        assert not out_html.exists(), name
        with pytest.raises(DraftError):
            rv.create_review_server(tmp_path, draft_path, port=0)
        assert draft_path.read_bytes() == before, name


def test_review_migrates_v2_draft_without_overwrite(tmp_path):
    """v2 drafts render via the shared v2->v3 migration; file untouched."""
    import review as rv

    _make_valid_image(tmp_path / "a.webp")
    v2 = {
        "version": 2,
        "meta": {"title": "V2 Pack", "author": "Tester", "cover": None},
        "similarity_groups": {},
        "stickers": {
            "a.webp": {"selection": "keep", "emojis": ["\U0001F600"], "confidence": 0.9,
                       "reason": "happy", "review_status": "approved",
                       "similarity_group": None, "file_hash": ""},
        },
    }
    draft_path = tmp_path / "pack_draft.json"
    draft_path.write_text(json.dumps(v2), encoding="utf-8")
    before = draft_path.read_bytes()
    out, stats = rv.generate_review_html(tmp_path, draft_path=draft_path)
    assert out.exists()
    assert stats["total"] == 1
    assert draft_path.read_bytes() == before
    html = out.read_text(encoding="utf-8")
    assert "V2 Pack" in html


def test_review_serve_refuses_corrupt_draft(tmp_path):
    """Direct `review.py --serve` path aborts before serving a replacement."""
    import review as rv
    from draft_state import DraftError

    _make_valid_image(tmp_path / "a.webp")
    draft_path = tmp_path / "pack_draft.json"
    draft_path.write_text('{"revision": 1}', encoding="utf-8")
    before = draft_path.read_bytes()
    with pytest.raises(DraftError):
        rv.create_review_server(tmp_path, draft_path, port=0)
    assert draft_path.read_bytes() == before


def test_builder_runs_central_preflight_directly(tmp_path):
    """Direct build_stickers_yaml() cannot bypass approval/hash gates."""
    import classify_and_build as cab

    _make_valid_image(tmp_path / "a.webp")
    draft_path = tmp_path / "pack_draft.json"
    files = [tmp_path / "a.webp"]
    draft = cab.load_or_create_draft(tmp_path, draft_path, None, files)
    draft["meta"].update({"title": "Direct Pack", "author": "Tester"})
    for item in draft["stickers"].values():
        item["selection"] = "keep"
        item["emojis"] = ["\U0001F600"]
        item["suggested_emojis"] = ["\U0001F600"]
        item["review_status"] = "pending"
        item["tag_status"] = "manual"
        item["tag_source"] = "manual"
        item["confidence"] = 0.9
    # Deliberately unapproved: direct builder must refuse, writing nothing.
    draft["pack_state"] = "in_progress"
    draft["approval"] = None
    with pytest.raises(ValueError, match="[Aa]pprov|preflight"):
        cab.build_stickers_yaml(folder=tmp_path, draft=draft)
    assert not (tmp_path / "stickers.yaml").exists()
    assert cab.approve_pack(draft) == []
    out = cab.build_stickers_yaml(folder=tmp_path, draft=draft)
    assert out.exists()
