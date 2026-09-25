#!/usr/bin/env python3
"""Shared pack_draft.json loader (fail-closed, single implementation).

Used by both classify_and_build.py (scan/tag/approve/export) and review.py
(page render + loopback save server) so direct entrypoints share the same
invariant: a present-but-unreadable draft aborts instead of being replaced.
Only a missing draft file yields a fresh empty draft.
"""

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from emojis import validate_single_emoji
except ImportError:
    from .emojis import validate_single_emoji

DRAFT_SCHEMA_VERSION = 3


class DraftError(ValueError):
    """A present draft exists but cannot be safely loaded/migrated."""


def new_draft_empty(draft_id: Optional[str] = None) -> Dict[str, Any]:
    if draft_id is None:
        draft_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
    return {
        "version": DRAFT_SCHEMA_VERSION,
        "revision": 1,
        "draft_id": str(draft_id),
        "pack_state": "in_progress",
        "approval": None,
        "meta": {"title": "", "author": "", "cover": None},
        "similarity_groups": {},
        "stickers": {},
    }


def upgrade_draft_to_v3(
    draft: Dict[str, Any], draft_id: Optional[str] = None
) -> Dict[str, Any]:
    """Migrates v2/legacy drafts to v3; imported tags are pending, never pre-approved."""
    if not isinstance(draft, dict):
        return new_draft_empty(draft_id)
    version = draft.get("version")
    if version == DRAFT_SCHEMA_VERSION and "revision" in draft:
        # Preserve an existing v3 draft's exact shape; a missing optional
        # draft_id must not change the persisted-state digest between loads.
        draft.setdefault("pack_state", "in_progress")
        draft.setdefault("approval", None)
        draft.setdefault("meta", {}).setdefault("title", "")
        draft["meta"].setdefault("author", "")
        draft["meta"].setdefault("cover", None)
        return draft
    upgraded = new_draft_empty(draft_id)
    upgraded["draft_id"] = str(draft.get("draft_id") or upgraded["draft_id"])
    old_meta = draft.get("meta", {}) if isinstance(draft.get("meta"), dict) else {}
    upgraded["meta"] = {
        "title": str(old_meta.get("title") or ""),
        "author": str(old_meta.get("author") or ""),
        "cover": old_meta.get("cover"),
    }
    upgraded["similarity_groups"] = draft.get("similarity_groups", {}) or {}
    for fn, item in (draft.get("stickers", {}) or {}).items():
        if not isinstance(item, dict):
            continue
        suggested = item.get("suggested_emojis")
        if suggested is None:
            legacy_seq = item.get("emojis") or ([item["emoji"]] if item.get("emoji") else None)
            if isinstance(legacy_seq, str):
                legacy_seq = [legacy_seq]
            suggested = legacy_seq
        # v2 "approved" tags become pending suggestions requiring human approval.
        status = item.get("review_status")
        tag_status = item.get("tag_status")
        if status in ("approved", "culled") or tag_status in ("approved",):
            review_status = "pending"
            tag_status = "suggested" if suggested else "pending"
        else:
            review_status = status or "pending"
            tag_status = tag_status or ("suggested" if suggested else "pending")
        # Legacy multi-emoji lists collapse to unresolved; human picks one.
        final = item.get("emojis")
        final_single: Optional[list] = None
        if isinstance(final, list) and len(final) == 1 and isinstance(final[0], str):
            valid, vals, _ = validate_single_emoji(final[0])
            final_single = vals if valid else None
        elif isinstance(final, str):
            valid, vals, _ = validate_single_emoji(final)
            final_single = vals if valid else None
        if final_single is None:
            review_status = "pending" if (suggested and review_status != "error") else review_status
        upgraded["stickers"][fn] = {
            "file_hash": str(item.get("file_hash") or ""),
            "selection": item.get("selection") if item.get("selection") in ("keep", "exclude", "undecided") else "undecided",
            "similarity_group": item.get("similarity_group"),
            "suggested_emojis": suggested,
            "emojis": final_single,
            "confidence": float(item.get("confidence", 0.0) or 0.0),
            "reason": str(item.get("reason", "") or ""),
            "review_status": review_status,
            "tag_status": tag_status,
            "tag_source": item.get("tag_source") or "legacy-migration",
        }
        # Preserve unknown fields conservatively.
        for k, v in item.items():
            if k not in upgraded["stickers"][fn]:
                upgraded["stickers"][fn][k] = v
    upgraded["revision"] = int(draft.get("revision") or 1)
    upgraded["pack_state"] = "in_progress"
    upgraded["approval"] = None
    return upgraded


def draft_digest(draft: Dict[str, Any]) -> str:
    canonical = json.dumps(draft, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_draft_for_review(draft_path: Path) -> Dict[str, Any]:
    """Fail-closed draft load shared by review render and save server.

    Only a missing file yields a fresh empty draft. A present file that is
    unparsable, not a JSON object, or missing the 'stickers' object raises
    DraftError instead of being replaced with an empty page. v2/legacy
    drafts are migrated via upgrade_draft_to_v3.
    """
    stable_draft_id = hashlib.sha256(
        str(draft_path.resolve()).encode("utf-8")
    ).hexdigest()[:16]
    if not draft_path.exists():
        return new_draft_empty(stable_draft_id)
    try:
        raw = json.loads(draft_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise DraftError(
            f"draft {draft_path} exists but cannot be parsed ({e}). "
            "Refusing to overwrite it. Back it up, then re-run with --reset-draft "
            "to start over explicitly."
        ) from e
    if not isinstance(raw, dict):
        raise DraftError(
            f"draft {draft_path} must be a JSON object, got {type(raw).__name__}. "
            "Refusing to overwrite it. Back it up, then re-run with --reset-draft "
            "to start over explicitly."
        )
    if not isinstance(raw.get("stickers"), dict):
        raise DraftError(
            f"draft {draft_path} is missing a 'stickers' object. "
            "Refusing to overwrite it. Back it up, then re-run with --reset-draft "
            "to start over explicitly."
        )
    return upgrade_draft_to_v3(raw, stable_draft_id)


if __name__ == "__main__":
    # CLI probe used only for debugging; callers sys.exit on DraftError.
    try:
        d = load_draft_for_review(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("pack_draft.json"))
    except DraftError as e:
        sys.exit(f"Error: {e}")
    print(f"draft ok: version={d.get('version')} revision={d.get('revision')} stickers={len(d.get('stickers', {}))}")
