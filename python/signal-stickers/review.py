#!/usr/bin/env python3
"""Interactive Signal Sticker Pack Curation & Review Tool.

Supports:
- Visual Cluster Curation: side-by-side candidate review and explicit Keep Only.
- Single-emoji review with strict in-page validation (one grapheme).
- Draft-only saves: the browser never generates stickers.yaml (single implementation).
- Contrast previews: Dark, Light, White, and Black backgrounds.
- Optional loopback save server (127.0.0.1 + token + revision check).

Usage:
  python review.py ./pack
  python review.py ./pack --serve
"""

import argparse
import base64
import html
import json
import mimetypes
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

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

# Import shared emoji registry and helpers
try:
    from emojis import EMOJI_REGISTRY, extract_emojis, format_emoji_sequence, validate_single_emoji
except ImportError:
    from .emojis import EMOJI_REGISTRY, extract_emojis, format_emoji_sequence, validate_single_emoji

# Single draft-state implementation shared with classify_and_build.py.
try:
    from draft_state import DraftError, load_draft_for_review
except ImportError:
    from .draft_state import DraftError, load_draft_for_review

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Signal Sticker Curation & Review — {title}</title>
  <style>
    :root {{
      --bg: #121316;
      --card-bg: #1c1d22;
      --border: #2c2d35;
      --text: #e1e2e6;
      --subtext: #8e909a;
      --accent: #2b6cd4;
      --accent-hover: #3d7ee8;
      --danger: #e5484d;
      --danger-hover: #f05a5f;
      --warning: #f79009;
      --success: #12b76a;
      --sticker-bg: #222329;
      --sticker-check: repeating-conic-gradient(#2b2c34 0 25%, #222329 0 50%) 0/16px 16px;
    }}

    body.theme-light {{
      --bg: #f2f3f5;
      --card-bg: #ffffff;
      --border: #dcdde3;
      --text: #1a1b1e;
      --subtext: #6c6e79;
      --sticker-bg: #ffffff;
      --sticker-check: repeating-conic-gradient(#f0f0f3 0 25%, #ffffff 0 50%) 0/16px 16px;
    }}

    body.theme-dark {{
      --bg: #0f1012;
      --card-bg: #18191d;
      --border: #25262c;
      --text: #eaebee;
      --subtext: #7c7e88;
      --sticker-bg: #1b1c1d;
      --sticker-check: #1b1c1d;
    }}

    body.theme-white-bg .sticker-img {{ background: #ffffff !important; }}
    body.theme-black-bg .sticker-img {{ background: #121212 !important; }}

    * {{ box-sizing: border-box; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 0 20px 40px;
      transition: background 0.2s, color 0.2s;
    }}

    .header-bar {{
      position: sticky;
      top: 0;
      background: var(--bg);
      border-bottom: 1px solid var(--border);
      padding: 14px 0;
      z-index: 100;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .header-row1 {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      align-items: center;
      justify-content: space-between;
    }}

    .header-left {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }}

    h1 {{
      font-size: 19px;
      font-weight: 600;
      margin: 0;
    }}

    .badge {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 13px;
      color: var(--subtext);
    }}
    .badge-active {{ color: var(--success); border-color: rgba(18, 183, 106, 0.4); }}
    .badge-deleted {{ color: var(--danger); border-color: rgba(229, 72, 77, 0.4); }}
    .badge-cluster {{ color: var(--warning); border-color: rgba(247, 144, 9, 0.4); }}

    .header-controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}

    button, .btn {{
      background: var(--accent);
      color: #fff;
      border: none;
      padding: 7px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.15s, opacity 0.15s;
    }}
    button:hover, .btn:hover {{ background: var(--accent-hover); }}
    .btn-secondary {{
      background: var(--card-bg);
      color: var(--text);
      border: 1px solid var(--border);
    }}
    .btn-secondary:hover {{ background: var(--border); }}
    .btn-danger {{ background: var(--danger); }}
    .btn-danger:hover {{ background: var(--danger-hover); }}

    .search-box {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 7px 12px;
      border-radius: 6px;
      font-size: 13px;
      min-width: 170px;
    }}

    .filter-tabs {{
      display: flex;
      gap: 3px;
      background: var(--card-bg);
      border: 1px solid var(--border);
      padding: 3px;
      border-radius: 6px;
      align-items: center;
    }}

    .filter-tab {{
      background: transparent;
      border: none;
      color: var(--subtext);
      padding: 5px 10px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
    }}
    .filter-tab.active {{ background: var(--accent); color: #fff; }}
    .filter-tab.active-warning {{ background: var(--warning); color: #fff; }}
    .filter-tab.active-danger {{ background: var(--danger); color: #fff; }}

    .ctrl-label {{
      font-size: 11px;
      font-weight: 600;
      color: var(--subtext);
      text-transform: uppercase;
      padding: 0 4px 0 6px;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }}

    .card {{
      background: var(--card-bg);
      border: 2px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
      transition: transform 0.1s, border-color 0.15s, opacity 0.2s;
    }}

    .card.conf-low {{ border-color: #e5484d; }}
    .card.conf-mid {{ border-color: #f79009; }}
    .card.conf-ok {{ border-color: var(--border); }}

    .card.in-cluster {{
      box-shadow: 0 0 0 1px #f79009 inset;
      border-color: #f79009;
    }}

    .card.is-excluded {{
      opacity: 0.38;
      background: rgba(229, 72, 77, 0.08);
      border-color: var(--danger);
      border-style: dashed;
    }}
    .card.is-excluded .sticker-container {{ filter: grayscale(80%); }}

    .card.card-invalid {{
      border-color: var(--danger) !important;
      box-shadow: 0 0 0 2px var(--danger) !important;
    }}

    .card-topbar {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      min-height: 22px;
      gap: 4px;
    }}

    .cluster-tag {{
      background: #f79009;
      color: #fff;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 10px;
      cursor: pointer;
      white-space: nowrap;
    }}

    .keep-only-btn {{
      background: transparent;
      border: 1px solid rgba(247, 144, 9, 0.6);
      color: #f79009;
      padding: 2px 6px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 11px;
      transition: background 0.15s, color 0.15s;
    }}
    .keep-only-btn:hover {{
      background: #f79009;
      color: #fff;
    }}

    .sel-btn {{
      background: transparent;
      border: 1px solid var(--border);
      color: var(--subtext);
      padding: 2px 6px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 11px;
      margin-left: auto;
    }}
    .sel-btn:hover {{
      background: var(--danger);
      border-color: var(--danger);
      color: #fff;
    }}
    .card.is-excluded .sel-btn {{
      background: var(--danger);
      color: #fff;
      border-color: var(--danger);
    }}

    .excluded-badge {{
      display: none;
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) rotate(-12deg);
      background: var(--danger);
      color: #fff;
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 4px;
      z-index: 10;
      letter-spacing: 1px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.5);
    }}
    .card.is-excluded .excluded-badge {{ display: block; }}

    .sticker-container {{
      width: 100%;
      aspect-ratio: 1;
      border-radius: 6px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      background: var(--sticker-check);
    }}

    .sticker-img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      transition: transform 0.15s;
    }}
    .sticker-img:hover {{ transform: scale(1.08); }}

    .emoji-bar {{
      width: 100%;
      display: flex;
      gap: 4px;
      margin-top: 8px;
      align-items: center;
    }}

    .emoji-input {{
      flex: 1;
      font-size: 20px;
      text-align: center;
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 3px 6px;
      height: 36px;
      min-width: 0;
    }}

    .emoji-select {{
      width: 36px;
      height: 36px;
      font-size: 16px;
      text-align: center;
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      cursor: pointer;
      padding: 0;
      flex-shrink: 0;
    }}

    #bulkConf {{
      max-width: 5em;
      flex: 0 0 auto;
    }}

    .err-msg {{
      color: var(--danger);
      font-size: 10px;
      margin-top: 4px;
      display: none;
      text-align: center;
      font-weight: 600;
    }}
    .card.card-invalid .err-msg {{ display: block; }}

    .meta-row {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: var(--subtext);
      margin-top: 6px;
    }}

    .reason {{
      font-size: 11px;
      color: var(--subtext);
      text-align: center;
      margin-top: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 155px;
    }}

    .filename {{
      font-size: 10px;
      color: var(--subtext);
      margin-top: 4px;
      word-break: break-all;
      opacity: 0.7;
    }}

    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1c1d22;
      border: 1px solid var(--border);
      color: #fff;
      padding: 12px 18px;
      border-radius: 8px;
      font-weight: 500;
      display: none;
      box-shadow: 0 4px 16px rgba(0,0,0,0.5);
      z-index: 1000;
      font-size: 13px;
    }}
    .toast.toast-undo {{
      display: flex;
      align-items: center;
      gap: 12px;
      border-color: var(--accent);
    }}
  </style>
</head>
<body class="theme-dark">
  <div class="header-bar">
    <div class="header-row1">
      <div class="header-left">
        <h1 id="packHeading">{title}</h1>
        <span class="badge badge-active" id="badgeActive">{count_active} Kept</span>
        <span class="badge badge-cluster" id="badgeCluster">{count_clusters} Clusters</span>
        <span class="badge" id="badgeUndecided">{count_undecided} Undecided</span>
        <span class="badge badge-deleted" id="badgeExcluded">{count_excluded} Excluded</span>
        <span class="badge" id="badgeApproval">{approval_label}</span>
      </div>

      <div class="header-controls">
        <button class="btn btn-secondary" id="saveServerBtn" onclick="saveDraftToServer()">Save</button>
        <button class="btn btn-secondary" onclick="exportDraftJson()">Download draft (fallback)</button>
        <button class="btn" id="approveBtn" onclick="approvePack()">Approve Pack</button>
      </div>
    </div>

    <div class="header-row1">
      <div class="header-controls">
        <label class="ctrl-label" for="metaTitle">Title</label>
        <input type="text" id="metaTitle" class="search-box" placeholder="Pack title (required)" oninput="onMetaInput()">
        <label class="ctrl-label" for="metaAuthor">Author</label>
        <input type="text" id="metaAuthor" class="search-box" placeholder="Author (required)" oninput="onMetaInput()">
        <label class="ctrl-label" for="metaCover">Cover</label>
        <input type="text" id="metaCover" class="search-box" placeholder="cover.webp (defaults to first kept)" oninput="onMetaInput()">
        <span class="ctrl-label" id="dirtyLabel"></span>
      </div>
    </div>
    <div class="header-row1"><div class="header-controls"><span class="ctrl-label" id="approvalSummary"></span></div></div>

    <div class="header-row1">
      <div class="header-controls">
        <span class="ctrl-label">Bulk:</span>
        <button class="btn btn-secondary" onclick="promoteBulk()" title="Apply every suggestion at or above the threshold as final (human-batched; review before Save)">Promote suggestions ≥</button>
        <input type="number" id="bulkConf" class="search-box" value="0.90" min="0" max="1" step="0.05" title="Confidence threshold for bulk promote">
        <span class="ctrl-label">as final (batched by you; still review before Save)</span>
      </div>
    </div>

    <div class="header-row1">
      <div class="header-controls">
        <input type="text" id="searchBox" class="search-box" placeholder="Search filename, emoji, or cluster..." oninput="filterCards()">

        <div class="filter-tabs">
          <span class="ctrl-label">Filter:</span>
          <button class="filter-tab active" onclick="setFilter('all', this)">All (<span id="tabCountAll">{count_total}</span>)</button>
          <button class="filter-tab" id="tabClusters" onclick="setFilter('clusters', this)">Clusters (<span id="tabCountClusters">{count_clustered}</span>)</button>
          <button class="filter-tab" id="tabNeedsReview" onclick="setFilter('review', this)">Needs Review (<span id="tabCountReview">0</span>)</button>
          <button class="filter-tab" onclick="setFilter('kept', this)">Kept (<span id="tabCountKept">{count_active}</span>)</button>
          <button class="filter-tab" onclick="setFilter('undecided', this)">Undecided (<span id="tabCountUndecided">{count_undecided}</span>)</button>
          <button class="filter-tab" onclick="setFilter('excluded', this)">Excluded (<span id="tabCountExcluded">{count_excluded}</span>)</button>
        </div>

        <div class="filter-tabs">
          <span class="ctrl-label">Sort:</span>
          <button class="filter-tab active" id="sortClusterBtn" onclick="setSort('cluster', this)">By Cluster</button>
          <button class="filter-tab" onclick="setSort('emoji', this)">By Emoji</button>
          <button class="filter-tab" onclick="setSort('filename', this)">By Filename</button>
          <button class="filter-tab" onclick="setSort('conf', this)">By Conf</button>
        </div>

        <div class="filter-tabs">
          <span class="ctrl-label">Theme:</span>
          <button class="filter-tab" onclick="setTheme('theme-light', this)">Light</button>
          <button class="filter-tab active" onclick="setTheme('theme-dark', this)">Dark</button>
          <button class="filter-tab" onclick="setTheme('theme-white-bg', this)">White</button>
          <button class="filter-tab" onclick="setTheme('theme-black-bg', this)">Black</button>
        </div>
      </div>
    </div>
  </div>

  <div class="grid" id="cardGrid">
    {cards}
  </div>

  <div id="toast" class="toast">Action completed!</div>

  <script>
    let DRAFT_BASELINE = {draft_json};
    let DRAFT_STATE = JSON.parse(JSON.stringify(DRAFT_BASELINE));
    const META = DRAFT_STATE.meta || {{}};
    const EMOJI_REGISTRY = {emoji_registry_json};
    const SAVE_ENDPOINT = {save_endpoint_json};
    const SAVE_TOKEN = {save_token_json};
    const PAGE_DIGEST = {save_digest_json};
    let BASE_DIGEST = PAGE_DIGEST;
    const DRAFT_REVISION = DRAFT_BASELINE.revision || 1;
    let currentFilter = 'all';
    let currentSort = 'cluster';

    // Undo history stack (snapshots of DRAFT_STATE)
    const undoStack = [];

    function draftEntries() {{ return DRAFT_STATE.stickers || {{}}; }}
    function entryFor(fn) {{ return draftEntries()[fn]; }}
    function snapshotState() {{ return JSON.stringify(DRAFT_STATE); }}
    function isDirty() {{ return snapshotState() !== JSON.stringify(DRAFT_BASELINE); }}
    function pushUndo(desc) {{
      undoStack.push({{ desc: desc, snapshot: snapshotState() }});
      if (undoStack.length > 50) undoStack.shift();
    }}
    function markApprovedDirty() {{
      DRAFT_STATE.pack_state = 'in_progress';
      DRAFT_STATE.approval = null;
    }}

    // Valid emoji set sorted by descending length for greedy matching
    const sortedEmojiKeys = Object.keys(EMOJI_REGISTRY).sort((a, b) => b.length - a.length);

    function extractKnownEmojis(text) {{
      const found = [];
      let i = 0;
      while (i < text.length) {{
        let matched = false;
        for (const em of sortedEmojiKeys) {{
          if (text.startsWith(em, i)) {{
            if (!found.includes(em)) found.push(em);
            i += em.length;
            matched = true;
            break;
          }}
        }}
        if (!matched) i++;
      }}
      return found;
    }}

    function validateSequence(text) {{
      const clean = text.replace(/\\s+/g, '');
      if (!clean) return {{ valid: false, emojis: [], msg: 'Cannot be empty' }};
      let n = 0;
      try {{
        if (window.Intl && Intl.Segmenter) {{
          n = Array.from(new Intl.Segmenter(undefined, {{ granularity: 'grapheme' }}).segment(clean)).length;
        }} else {{
          n = Array.from(clean).length;
        }}
      }} catch (e) {{ n = Array.from(clean).length; }}
      if (n !== 1) return {{ valid: false, emojis: [], msg: 'Must be exactly one emoji (found ' + n + ')' }};
      if (/[A-Za-z0-9]/.test(clean)) return {{ valid: false, emojis: [], msg: 'Invalid character' }};
      return {{ valid: true, emojis: [clean], msg: null }};
    }}

    function getCardEmoji(card) {{
      const fn = card.dataset.file;
      const entry = entryFor(fn);
      if (entry && entry.emojis && entry.emojis.length === 1) return String(entry.emojis[0]);
      const inp = card.querySelector('.emoji-input');
      return (inp ? inp.value : card.dataset.emoji || '').trim();
    }}

    function getPrimaryEmoji(card) {{
      const text = getCardEmoji(card);
      const v = validateSequence(text);
      return v.valid ? v.emojis[0] : '';
    }}

    function getUsageCounts() {{
      const counts = {{}};
      document.querySelectorAll('.card').forEach(card => {{
        const entry = entryFor(card.dataset.file);
        if (entry && entry.selection === 'exclude') return;
        const primary = getPrimaryEmoji(card);
        if (!primary) return;
        counts[primary] = (counts[primary] || 0) + 1;
      }});
      return counts;
    }}

    function renderOptionsForSelect(select, counts) {{
      let html = '<option value="" selected disabled>+ Add</option>';
      const card = select.closest('.card');
      const entry = card ? entryFor(card.dataset.file) : null;
      const ranked = (entry && Array.isArray(entry.suggested_emojis)) ? entry.suggested_emojis : [];
      if (ranked.length) {{
        html += '<optgroup label="⭐ Suggested for this sticker">';
        ranked.slice(0, 5).forEach(em => {{ html += '<option value="' + em + '">⭐ ' + em + '</option>'; }});
        html += '</optgroup>';
      }}
      const unused = [];
      const used = [];

      for (const [em, info] of Object.entries(EMOJI_REGISTRY)) {{
        const cnt = counts[em] || 0;
        const name = info.name ? ' (' + info.name + ')' : '';
        if (cnt === 0) {{
          unused.push({{ em: em, label: em + name + ' — unused' }});
        }} else {{
          used.push({{ em: em, cnt: cnt, label: em + name + ' — ' + cnt + 'x' }});
        }}
      }}

      used.sort((a, b) => b.cnt - a.cnt);

      html += '<optgroup label="✨ Available / Unused (' + unused.length + ')">';
      for (const item of unused) html += '<option value="' + item.em + '">' + item.label + '</option>';
      html += '</optgroup>';

      if (used.length > 0) {{
        html += '<optgroup label="In Use (' + used.length + ')">';
        for (const item of used) html += '<option value="' + item.em + '">' + item.label + '</option>';
        html += '</optgroup>';
      }}
      select.innerHTML = html;
    }}

    function refreshAllSelects() {{
      const counts = getUsageCounts();
      document.querySelectorAll('select.emoji-select').forEach(sel => renderOptionsForSelect(sel, counts));
    }}

    function updateCountsAndValidation() {{
      const cards = Array.from(document.querySelectorAll('.card'));
      let invalidCount = 0;
      let reviewCount = 0;
      let keptCount = 0;
      let clusterStickersCount = 0;

      cards.forEach(card => {{
        const fn = card.dataset.file;
        const entry = entryFor(fn) || {{ selection: 'keep' }};
        const sel = entry.selection || 'keep';
        const isEx = sel === 'exclude';
        const isUnd = sel === 'undecided';
        const cid = card.dataset.cluster;
        const conf = parseFloat(card.dataset.conf || '1.0');
        const text = getCardEmoji(card);
        const val = validateSequence(text);

        if (cid) clusterStickersCount++;

        if (!val.valid) {{
          card.classList.add('card-invalid');
          const errEl = card.querySelector('.err-msg');
          if (errEl) errEl.textContent = '⚠ ' + val.msg;
          if (!isEx && !isUnd) invalidCount++;
        }} else {{
          card.classList.remove('card-invalid');
        }}

        if (sel === 'keep') {{
          keptCount++;
          if (conf < 0.8 || !val.valid || card.dataset.status === 'needs_review' || card.dataset.status === 'error') {{
            reviewCount++;
          }}
        }} else if (isUnd) {{
          reviewCount++;
        }}

        card.classList.toggle('is-excluded', isEx);
        card.classList.toggle('is-undecided', isUnd);
        const btn = card.querySelector('.sel-btn');
        if (btn) btn.textContent = isEx ? '↺ Keep' : (isUnd ? 'Keep?' : '✕ Exclude');
        const laterBtn = card.querySelector('.later-btn');
        if (laterBtn) laterBtn.style.display = isUnd ? 'none' : '';
        card.dataset.selection = sel;
      }});

      const totalCount = cards.length;
      let exCount = 0;
      let undecidedCount = 0;
      Object.values(draftEntries()).forEach(e => {{
        if (e.selection === 'exclude') exCount++;
        if (e.selection === 'undecided') undecidedCount++;
      }});

      document.getElementById('badgeActive').textContent = keptCount + ' Kept';
      document.getElementById('badgeExcluded').textContent = exCount + ' Excluded';
      const badgeUnd = document.getElementById('badgeUndecided');
      if (badgeUnd) badgeUnd.textContent = undecidedCount + ' Undecided';
      const badgeAppr = document.getElementById('badgeApproval');
      if (badgeAppr) badgeAppr.textContent = (DRAFT_STATE.pack_state === 'approved') ? ('Approved r' + DRAFT_STATE.revision) : 'In progress';
      document.getElementById('tabCountAll').textContent = totalCount;
      document.getElementById('tabCountClusters').textContent = clusterStickersCount;
      document.getElementById('tabCountReview').textContent = reviewCount;
      document.getElementById('tabCountKept').textContent = keptCount;
      const tabUnd = document.getElementById('tabCountUndecided');
      if (tabUnd) tabUnd.textContent = undecidedCount;
      document.getElementById('tabCountExcluded').textContent = exCount;
      const dirtyEl = document.getElementById('dirtyLabel');
      if (dirtyEl) dirtyEl.textContent = isDirty() ? '● unsaved changes' : 'saved';
      const apprEl = document.getElementById('approvalSummary');
      if (apprEl) {{
        const metaOk = (DRAFT_STATE.meta.title || '').trim() && (DRAFT_STATE.meta.author || '').trim();
        apprEl.textContent = 'Revision ' + DRAFT_STATE.revision + ' • ' + keptCount + ' keep / ' + undecidedCount + ' undecided / ' + exCount + ' excluded • ' + invalidCount + ' invalid • title/author ' + (metaOk ? 'set' : 'MISSING');
      }}
    }}

    function toggleSelect(btn) {{
      const card = btn.closest('.card');
      const fn = card.dataset.file;
      const entry = entryFor(fn);
      const cur = entry ? entry.selection : 'keep';
      // Tri-state cycle: undecided -> keep -> exclude -> keep (explicit; never implicit).
      const next = (cur === 'undecided') ? 'keep' : (cur === 'keep' ? 'exclude' : 'keep');
      const before = snapshotState();
      entry.selection = next;
      entry.review_status = (next === 'exclude') ? 'culled' : 'pending';
      markApprovedDirty();
      undoStack.push({{ desc: cur + ' -> ' + next + ' (' + fn + ')', snapshot: before }});
      syncCardToEntry(fn);
      updateCountsAndValidation();
      refreshAllSelects();
      filterCards();
    }}

    function markLater(btn) {{
      const card = btn.closest('.card');
      const fn = card.dataset.file;
      const entry = entryFor(fn);
      if (!entry) return;
      const before = snapshotState();
      entry.selection = 'undecided';
      entry.review_status = 'pending';
      markApprovedDirty();
      undoStack.push({{ desc: 'marked undecided (' + fn + ')', snapshot: before }});
      syncCardToEntry(fn);
      updateCountsAndValidation();
      filterCards();
    }}

    function cardForFile(fn) {{
      // Exact dataset match: filenames may contain quotes or CSS metacharacters.
      const cards = document.querySelectorAll('.card');
      for (const c of cards) {{ if (c.dataset.file === fn) return c; }}
      return null;
    }}

    function syncCardToEntry(fn) {{
      const card = cardForFile(fn);
      if (!card) return;
      const entry = entryFor(fn);
      card.dataset.selection = entry.selection;
      card.dataset.emoji = (entry.emojis && entry.emojis[0]) || '';
      const inp = card.querySelector('.emoji-input');
      if (inp && document.activeElement !== inp) inp.value = card.dataset.emoji;
    }}

    function keepOnlyInCluster(btn) {{
      const currentCard = btn.closest('.card');
      const currentFile = currentCard.dataset.file;
      const cid = currentCard.dataset.cluster;
      if (!cid) return;
      const before = snapshotState();
      let countExcluded = 0;
      document.querySelectorAll('.card').forEach(card => {{
        if (card.dataset.cluster === cid) {{
          const fn = card.dataset.file;
          const entry = entryFor(fn);
          if (!entry) return;
          if (fn !== currentFile) {{
            entry.selection = 'exclude';
            entry.review_status = 'culled';
            countExcluded++;
          }} else {{
            entry.selection = 'keep';
            entry.review_status = 'pending';
          }}
          syncCardToEntry(fn);
        }}
      }});
      markApprovedDirty();
      undoStack.push({{ desc: 'Keep only ' + currentFile + ' in ' + cid, snapshot: before }});
      updateCountsAndValidation();
      refreshAllSelects();
      filterCards();
      showToast('Kept ' + currentFile + ' and excluded ' + countExcluded + ' other variations in ' + cid, true);
    }}

    function onEmojiInput(input) {{
      const card = input.closest('.card');
      const fn = card.dataset.file;
      const entry = entryFor(fn);
      const text = input.value.trim();
      card.dataset.emoji = text;
      if (entry) {{
        const beforeSnap = snapshotState();
        const v = validateSequence(text);
        const prevFinal = (entry.emojis && entry.emojis[0]) || '';
        if (v.valid) {{
          entry.emojis = v.emojis;
          entry.review_status = 'pending';
          entry.tag_status = 'manual';
          entry.tag_source = 'manual';
          markApprovedDirty();
          if (prevFinal !== v.emojis[0]) undoStack.push({{ desc: 'Emoji edit ' + fn, snapshot: beforeSnap }});
        }} else if ((entry.emojis || []).length !== 0) {{
          entry.emojis = [];
          entry.review_status = 'pending';
          entry.tag_status = 'pending';
          markApprovedDirty();
          undoStack.push({{ desc: 'Emoji cleared ' + fn, snapshot: beforeSnap }});
        }}
      }}
      updateCountsAndValidation();
      if (currentSort === 'emoji') sortCards('emoji');
    }}

    function onEmojiAdd(select) {{
      const chosen = select.value;
      if (!chosen) return;
      const card = select.closest('.card');
      const input = card.querySelector('.emoji-input');
      if (input) {{
        input.value = chosen;
        onEmojiInput(input);
      }}
      select.selectedIndex = 0;
    }}

    function applyFinalEmoji(card, entry, emoji, auditSource) {{
      const beforeSnap = snapshotState();
      const prevFinal = (entry.emojis && entry.emojis[0]) || '';
      entry.emojis = [emoji];
      entry.review_status = 'pending';
      entry.tag_status = 'approved';
      if (auditSource) {{
        const src = entry.tag_source || 'openrouter';
        entry.tag_source = src.includes('+bulk') ? src : (src + '+' + auditSource);
      }}
      const input = card.querySelector('.emoji-input');
      if (input) input.value = emoji;
      card.dataset.emoji = emoji;
      markApprovedDirty();
      if (prevFinal !== emoji) undoStack.push({{ desc: 'Promote suggestion ' + card.dataset.file, snapshot: beforeSnap }});
      updateCountsAndValidation();
      refreshAllSelects();
      if (currentSort === 'emoji') sortCards('emoji');
    }}

    function useSuggestion(btn) {{
      const card = btn.closest('.card');
      const entry = entryFor(card.dataset.file);
      if (!entry) return;
      const sugg = entry.suggested_emojis || [];
      if (!sugg.length) return;
      const v = validateSequence(String(sugg[0]));
      if (!v.valid) {{
        showToast('Top suggestion is not a valid single emoji.', false);
        return;
      }}
      applyFinalEmoji(card, entry, v.emojis[0], null);
    }}

    function promoteBulk() {{
      const thrInput = document.getElementById('bulkConf');
      let thr = parseFloat(thrInput ? thrInput.value : '0.90');
      if (!(thr >= 0 && thr <= 1)) thr = 0.90;
      const audit = 'bulk-' + thr.toFixed(2);
      const beforeSnap = snapshotState();
      let n = 0;
      document.querySelectorAll('.card').forEach(card => {{
        const entry = entryFor(card.dataset.file);
        if (!entry || entry.selection !== 'keep') return;
        if (getPrimaryEmoji(card)) return;
        const sugg = entry.suggested_emojis || [];
        if (!sugg.length) return;
        const conf = parseFloat(entry.confidence || 0);
        if (!(conf >= thr)) return;
        const v = validateSequence(String(sugg[0]));
        if (!v.valid) return;
        entry.emojis = v.emojis;
        entry.review_status = 'pending';
        entry.tag_status = 'approved';
        const src = entry.tag_source || 'openrouter';
        entry.tag_source = src.includes('+bulk') ? src : (src + '+' + audit);
        const input = card.querySelector('.emoji-input');
        if (input) input.value = v.emojis[0];
        card.dataset.emoji = v.emojis[0];
        n++;
      }});
      markApprovedDirty();
      undoStack.push({{ desc: 'Bulk promote ≥ ' + thr.toFixed(2), snapshot: beforeSnap }});
      updateCountsAndValidation();
      refreshAllSelects();
      filterCards();
      showToast('Promoted ' + n + ' suggestion(s) at ≥ ' + thr.toFixed(2) + '. Review them, then Save.', false);
    }}

    function onMetaInput() {{
      const beforeSnap = snapshotState();
      const t = document.getElementById('metaTitle');
      const a = document.getElementById('metaAuthor');
      const c = document.getElementById('metaCover');
      const nt = t ? t.value : '', na = a ? a.value : '', nc = c ? c.value : '';
      const changed = (DRAFT_STATE.meta.title !== nt) || (DRAFT_STATE.meta.author !== na) || ((DRAFT_STATE.meta.cover || '') !== nc);
      DRAFT_STATE.meta.title = nt;
      DRAFT_STATE.meta.author = na;
      DRAFT_STATE.meta.cover = nc.trim() ? nc.trim() : null;
      const head = document.getElementById('packHeading');
      if (head) head.textContent = nt || 'Signal Stickers';
      if (changed) {{
        markApprovedDirty();
        undoStack.push({{ desc: 'Metadata edit', snapshot: beforeSnap }});
      }}
      updateCountsAndValidation();
    }}

    function setSort(sortType, btn) {{
      currentSort = sortType;
      btn.parentElement.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      sortCards(sortType);
    }}

    function sortCards(sortType) {{
      const grid = document.getElementById('cardGrid');
      const cards = Array.from(grid.querySelectorAll('.card'));

      cards.sort((a, b) => {{
        if (sortType === 'cluster') {{
          const ca = a.dataset.cluster || 'zzz';
          const cb = b.dataset.cluster || 'zzz';
          if (ca !== cb) return ca.localeCompare(cb, 'en', {{ numeric: true }});
          return a.dataset.file.localeCompare(b.dataset.file, 'en', {{ numeric: true }});
        }} else if (sortType === 'emoji') {{
          const ea = getPrimaryEmoji(a);
          const eb = getPrimaryEmoji(b);
          if (ea !== eb) return ea.localeCompare(eb, 'en', {{ numeric: true }});
          return a.dataset.file.localeCompare(b.dataset.file, 'en', {{ numeric: true }});
        }} else if (sortType === 'conf') {{
          const ca = parseFloat(a.dataset.conf || '1.0');
          const cb = parseFloat(b.dataset.conf || '1.0');
          if (ca !== cb) return ca - cb;
          return a.dataset.file.localeCompare(b.dataset.file, 'en', {{ numeric: true }});
        }} else {{
          return a.dataset.file.localeCompare(b.dataset.file, 'en', {{ numeric: true }});
        }}
      }});

      cards.forEach(c => grid.appendChild(c));
      filterCards();
    }}

    function setTheme(themeClass, btn) {{
      document.body.className = themeClass;
      btn.parentElement.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }}

    function setFilter(filterType, btn) {{
      currentFilter = filterType;
      btn.parentElement.querySelectorAll('.filter-tab').forEach(b => {{
        b.classList.remove('active', 'active-warning', 'active-danger');
      }});
      if (filterType === 'clusters') btn.classList.add('active-warning');
      else if (filterType === 'excluded') btn.classList.add('active-danger');
      else btn.classList.add('active');
      filterCards();
    }}

    function filterByCluster(cid) {{
      document.getElementById('searchBox').value = cid;
      setFilter('clusters', document.getElementById('tabClusters'));
      filterCards();
    }}

    function filterCards() {{
      const q = document.getElementById('searchBox').value.toLowerCase();
      document.querySelectorAll('.card').forEach(card => {{
        const fn = card.dataset.file.toLowerCase();
        const emoji = getCardEmoji(card).toLowerCase();
        const cid = (card.dataset.cluster || '').toLowerCase();
        const conf = parseFloat(card.dataset.conf || '1.0');
        const entry = entryFor(card.dataset.file) || {{ selection: 'keep' }};
        const sel = entry.selection || 'keep';
        const isEx = sel === 'exclude';
        const isUnd = sel === 'undecided';
        const isInv = card.classList.contains('card-invalid');

        let matchFilter = true;
        if (currentFilter === 'clusters') {{
          matchFilter = !!cid;
        }} else if (currentFilter === 'review') {{
          matchFilter = (sel !== 'exclude') && (conf < 0.8 || isInv || isUnd || card.dataset.status === 'needs_review' || card.dataset.status === 'error');
        }} else if (currentFilter === 'kept') {{
          matchFilter = sel === 'keep';
        }} else if (currentFilter === 'undecided') {{
          matchFilter = isUnd;
        }} else if (currentFilter === 'excluded') {{
          matchFilter = isEx;
        }}

        let matchSearch = fn.includes(q) || emoji.includes(q) || cid.includes(q);
        card.style.display = (matchFilter && matchSearch) ? 'flex' : 'none';
      }});
    }}

    function showToast(msg, withUndo = false) {{
      const toast = document.getElementById('toast');
      // textContent only: filenames and messages must never become HTML.
      toast.textContent = '';
      if (withUndo && undoStack.length > 0) {{
        toast.className = 'toast toast-undo';
        const span = document.createElement('span');
        span.textContent = msg;
        const btn = document.createElement('button');
        btn.className = 'btn btn-secondary';
        btn.setAttribute('style', 'padding:3px 8px;font-size:11px;');
        btn.textContent = 'Undo';
        btn.addEventListener('click', undoLast);
        toast.appendChild(span);
        toast.appendChild(document.createTextNode(' '));
        toast.appendChild(btn);
      }} else {{
        toast.className = 'toast';
        toast.textContent = msg;
      }}
      toast.style.display = 'flex';
      setTimeout(() => {{ toast.style.display = 'none'; }}, 3500);
    }}

    function undoLast() {{
      if (undoStack.length === 0) return;
      const last = undoStack.pop();
      DRAFT_STATE = JSON.parse(last.snapshot);
      document.querySelectorAll('.card').forEach(card => syncCardToEntry(card.dataset.file));
      syncMetaInputs();
      updateCountsAndValidation();
      refreshAllSelects();
      filterCards();
      showToast('Reverted: ' + last.desc, false);
    }}

    function collectDraft() {{
      // The full draft object is the state source; DOM is a view. Preserve
      // file_hash, suggestions, unknown fields, and cluster membership.
      const groups = {{}};
      document.querySelectorAll('.card').forEach(card => {{
        const cid = card.dataset.cluster;
        if (!cid) return;
        if (!groups[cid]) groups[cid] = [];
        groups[cid].push(card.dataset.file);
      }});
      if (Object.keys(groups).length) DRAFT_STATE.similarity_groups = groups;
      return DRAFT_STATE;
    }}

    function downloadBlob(content, filename, type) {{
      const blob = new Blob([content], {{ type: type }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    }}

    function syncMetaInputs() {{
      const t = document.getElementById('metaTitle');
      const a = document.getElementById('metaAuthor');
      const c = document.getElementById('metaCover');
      if (t) t.value = DRAFT_STATE.meta.title || '';
      if (a) a.value = DRAFT_STATE.meta.author || '';
      if (c) c.value = DRAFT_STATE.meta.cover || '';
      const head = document.getElementById('packHeading');
      if (head) head.textContent = DRAFT_STATE.meta.title || 'Signal Stickers';
    }}

    async function saveDraftToServer() {{
      const payload = collectDraft();
      if (!SAVE_ENDPOINT) {{
        exportDraftJson();
        return;
      }}
      try {{
        const res = await fetch(SAVE_ENDPOINT, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json', 'X-Session-Token': SAVE_TOKEN }},
          body: JSON.stringify({{ base_digest: BASE_DIGEST, revision: DRAFT_STATE.revision, draft: payload }})
        }});
        const data = await res.json().catch(() => ({{}}));
        if (!res.ok) {{
          alert('Save failed: ' + (data.error || res.status));
          return;
        }}
        // Adopt the server's canonical saved state (revision, digest, approval).
        BASE_DIGEST = data.digest;
        DRAFT_STATE.revision = data.revision;
        if (data.approval !== undefined) DRAFT_STATE.approval = data.approval;
        if (!data.approved && DRAFT_STATE.pack_state === 'approved') DRAFT_STATE.pack_state = 'in_progress';
        DRAFT_BASELINE = JSON.parse(JSON.stringify(DRAFT_STATE));
        let msg = 'Saved revision ' + DRAFT_STATE.revision + ' to pack folder.';
        if (data.approved) msg += ' Pack approved.';
        else if (data.approval_errors && data.approval_errors.length) msg += ' Saved, but approval needs work: ' + data.approval_errors.slice(0, 3).join('; ');
        showToast(msg, false);
        updateCountsAndValidation();
      }} catch (e) {{
        alert('Save failed (' + e + '). Use Download draft (fallback) instead.');
      }}
    }}

    function approvePack() {{
      const beforeSnap = snapshotState();
      const problems = [];
      if (!(DRAFT_STATE.meta.title || '').trim()) problems.push('Set a pack title.');
      if (!(DRAFT_STATE.meta.author || '').trim()) problems.push('Set a pack author.');
      Object.entries(draftEntries()).forEach(([fn, e]) => {{
        if (e.selection === 'undecided') problems.push(fn + ': undecided — Keep or Exclude it.');
        if (e.selection === 'keep') {{
          const v = validateSequence((e.emojis && e.emojis[0]) || '');
          if (!v.valid) problems.push(fn + ': needs exactly one valid emoji.');
          if (e.tag_status === 'error') problems.push(fn + ': tag error — re-tag.');
        }}
      }});
      if (problems.length) {{
        alert('Cannot approve:\\n- ' + problems.slice(0, 12).join('\\n- ') + (problems.length > 12 ? '\\n... and ' + (problems.length - 12) + ' more' : ''));
        return;
      }}
      DRAFT_STATE.pack_state = 'approved';
      DRAFT_STATE.approval = {{ revision: DRAFT_STATE.revision, by: 'browser', pending_server_digest: true }};
      undoStack.push({{ desc: 'Approve pack', snapshot: beforeSnap }});
      updateCountsAndValidation();
      showToast('Pack approved for revision ' + DRAFT_STATE.revision + '. Click Save.', false);
    }}

    function exportDraftJson() {{
      downloadBlob(
        JSON.stringify(collectDraft(), null, 2),
        'pack_draft.json',
        'application/json'
      );
      showToast('Downloaded pack_draft.json — Save writes directly when served via ./stickers curate --serve; otherwise copy this file into your pack folder.', true);
    }}

    // Warn on unsaved changes: compare live draft against the loaded baseline.
    window.addEventListener('beforeunload', (e) => {{
      if (isDirty()) {{
        e.preventDefault();
        e.returnValue = '';
      }}
    }});

    window.addEventListener('DOMContentLoaded', () => {{
      syncMetaInputs();
      updateCountsAndValidation();
      refreshAllSelects();
      sortCards('cluster');
    }});
  </script>
</body>
</html>
"""


def _safe_json_for_html(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


def generate_review_html(
    folder: Path,
    draft_path: Optional[Path] = None,
    yaml_path: Optional[Path] = None,
    cache_path: Optional[Path] = None,
    save_endpoint: Optional[str] = None,
    save_token: Optional[str] = None,
    save_digest: Optional[str] = None,
) -> Path:
    """Generates the review page from pack_draft.json (sole source; no YAML trust).

    Fail-closed: a present-but-unreadable draft raises DraftError instead of
    rendering an empty replacement page. Only a missing file yields an empty
    draft. v2/legacy drafts migrate via the shared loader.
    """
    draft_file = draft_path or (folder / "pack_draft.json")
    # Shared loader aborts on malformed/incomplete/unmigratable drafts.
    draft_data = load_draft_for_review(draft_file)
    draft_data.setdefault("revision", 1)
    draft_data.setdefault("pack_state", "in_progress")
    draft_data.setdefault("approval", None)
    draft_data.setdefault("meta", {"title": "", "author": "", "cover": None})

    stickers_items = []
    meta = draft_data.get("meta", {"title": "", "author": "", "cover": None})
    if isinstance(draft_data.get("stickers"), dict):
        for fn, sdata in draft_data["stickers"].items():
            stickers_items.append((fn, sdata if isinstance(sdata, dict) else {}))

    cards = []
    clusters_set = set()

    for file_name, info in stickers_items:
        img_path = folder / file_name
        if not img_path.exists() and (folder / "webp" / file_name).exists():
            img_path = folder / "webp" / file_name
        elif not img_path.exists() and (folder.parent / "webp" / file_name).exists():
            img_path = folder.parent / "webp" / file_name

        if not img_path.exists():
            continue

        mt = mimetypes.guess_type(img_path.name)[0] or "image/png"
        b64 = base64.standard_b64encode(img_path.read_bytes()).decode("utf-8")
        src = f"data:{mt};base64,{b64}"

        cid = info.get("similarity_group") or ""
        if cid:
            clusters_set.add(cid)

        sel = info.get("selection", "undecided" if cid else "keep")
        if sel not in ("keep", "exclude", "undecided"):
            sel = "undecided" if cid else "keep"

        final = info.get("emojis")
        emoji_str = ""
        if isinstance(final, list) and len(final) == 1 and isinstance(final[0], str):
            valid, vals, _ = validate_single_emoji(final[0])
            emoji_str = vals[0] if valid else ""
        elif isinstance(final, str) and final:
            valid, vals, _ = validate_single_emoji(final)
            emoji_str = vals[0] if valid else ""
        suggested = info.get("suggested_emojis")
        sugg_list = [str(e) for e in suggested] if isinstance(suggested, list) else []
        suggested_str = sugg_list[0] if sugg_list else ""
        try:
            conf = float(info.get("confidence", 0.0) or 0.0)
        except Exception:
            conf = 0.0
        reason = str(info.get("reason", "") or "")
        status = str(info.get("review_status", "pending") or "pending")

        conf_class = "conf-low" if conf < 0.6 else ("conf-mid" if conf < 0.8 else "conf-ok")
        cluster_class = "in-cluster" if cid else ""
        ex_class = "is-excluded" if sel == "exclude" else ("is-undecided" if sel == "undecided" else "")
        try:
            size_kb = img_path.stat().st_size / 1024
        except Exception:
            size_kb = 0
        esc_file = html.escape(file_name, quote=True)
        esc_cid = html.escape(cid, quote=True)
        esc_emoji = html.escape(emoji_str, quote=True)
        esc_reason = html.escape(reason, quote=True)
        esc_reason_text = html.escape(reason or "—")
        if suggested_str and suggested_str != emoji_str:
            extra = f" (+{len(sugg_list) - 1} more)" if len(sugg_list) > 1 else ""
            esc_suggested = html.escape(f" Suggested: {suggested_str}{extra}")
        else:
            esc_suggested = ""
        use_btn_html = ""
        if sugg_list and (not emoji_str or emoji_str != sugg_list[0]):
            top_esc = html.escape(sugg_list[0], quote=True)
            use_btn_html = f'<button type="button" class="keep-only-btn" onclick="useSuggestion(this)" title="Apply suggested {top_esc} as final">✓ {top_esc}</button>'

        cluster_tag_html = (
            f'<span class="cluster-tag" onclick="filterByCluster(\'{esc_cid}\')" title="Filter by {esc_cid}">{esc_cid}</span>'
            if cid
            else ""
        )
        keep_only_html = (
            f'<button type="button" class="keep-only-btn" onclick="keepOnlyInCluster(this)" title="Keep this variation and explicitly exclude its siblings in {esc_cid}">⚡ Keep Only</button>'
            if cid
            else ""
        )
        if sel == "exclude":
            sel_label = "↺ Keep"
        elif sel == "undecided":
            sel_label = "Keep?"
        else:
            sel_label = "✕ Exclude"
        later_html = (
            '<button type="button" class="later-btn" onclick="markLater(this)" title="Leave undecided for later">Later</button>'
            if sel != "undecided"
            else ""
        )
        und_badge = '<div class="excluded-badge" style="background:#7a5b00;">UNDECIDED</div>' if sel == "undecided" else ""

        card_html = f"""
        <div class="card {conf_class} {cluster_class} {ex_class}" data-file="{esc_file}" data-cluster="{esc_cid}" data-selection="{sel}" data-emoji="{esc_emoji}" data-conf="{conf:.2f}" data-status="{html.escape(status, quote=True)}">
          <div class="card-topbar">
            {cluster_tag_html}
            {keep_only_html}
            <button type="button" class="sel-btn" onclick="toggleSelect(this)">{sel_label}</button>
            {later_html}
          </div>
          <div class="sticker-container">
            <div class="excluded-badge">EXCLUDED</div>
            {und_badge}
            <img class="sticker-img" src="{src}" loading="lazy" alt="{esc_file}">
          </div>
          <div class="emoji-bar">
            <input type="text" class="emoji-input" value="{esc_emoji}" placeholder="one emoji" title="Exactly one emoji" oninput="onEmojiInput(this)">
            {use_btn_html}
            <select class="emoji-select" onchange="onEmojiAdd(this)" title="Pick a suggested emoji"><option value="" selected disabled>+ Add</option></select>
          </div>
          <div class="err-msg">⚠ Invalid emoji</div>
          <div class="meta-row">
            <span>{size_kb:.0f} KB</span>
            <span>conf: {conf:.2f}</span>
          </div>
          <div class="reason" title="{esc_reason}">{esc_reason_text}{esc_suggested}</div>
          <div class="filename">{esc_file}</div>
        </div>
        """
        cards.append(card_html)

    total_count = len(cards)
    kept_count = sum(1 for _, info in stickers_items if info.get("selection") == "keep")
    und_count = sum(1 for _, info in stickers_items if info.get("selection") == "undecided")
    ex_count = sum(1 for _, info in stickers_items if info.get("selection") == "exclude")
    clustered_count = sum(1 for _, info in stickers_items if info.get("similarity_group"))
    title_str = str(meta.get("title") or "Signal Stickers")
    appr = draft_data.get("approval")
    approval_label = ("Approved r" + str(draft_data.get("revision", 1))) if draft_data.get("pack_state") == "approved" and appr else "In progress"

    if save_digest is None:
        save_digest = _state_digest(draft_data)
    html_content = HTML_TEMPLATE.format(
        title=html.escape(title_str),
        count_total=total_count,
        count_active=kept_count,
        count_undecided=und_count,
        count_excluded=ex_count,
        approval_label=html.escape(approval_label),
        count_clusters=len(clusters_set),
        count_clustered=clustered_count,
        cards="".join(cards),
        draft_json=_safe_json_for_html(draft_data),
        emoji_registry_json=_safe_json_for_html(EMOJI_REGISTRY),
        save_endpoint_json=_safe_json_for_html(save_endpoint),
        save_token_json=_safe_json_for_html(save_token),
        save_digest_json=_safe_json_for_html(save_digest),
    )

    out_path = folder / "review.html"
    out_path.write_text(html_content, encoding="utf-8")

    untagged = 0
    for _, info in stickers_items:
        final = info.get("emojis")
        ok = False
        if isinstance(final, list) and len(final) == 1 and isinstance(final[0], str):
            valid, _, _ = validate_single_emoji(final[0])
            ok = valid
        elif isinstance(final, str) and final:
            valid, _, _ = validate_single_emoji(final)
            ok = valid
        if info.get("selection") == "keep" and not ok:
            untagged += 1
    stats = {
        "total": total_count,
        "kept": kept_count,
        "undecided": und_count,
        "excluded": ex_count,
        "clusters": len(clusters_set),
        "untagged": untagged,
        "missing": len(stickers_items) - total_count,
    }
    return out_path, stats


def _state_digest(obj: Any) -> str:
    """Canonical digest for compare-and-swap (same form as draft_digest)."""
    import hashlib as _hashlib

    canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _server_validate_approval(draft: Dict[str, Any]) -> List[str]:
    """Authoritative approval check used when the browser claims approval."""
    try:
        from classify_and_build import approve_pack as _approve
    except Exception:
        _approve = None  # type: ignore
    if _approve is None:
        # No validator available: never persist an unverified approval.
        return ["server validator unavailable; approve via CLI"]
    probe = json.loads(json.dumps(draft))
    probe["pack_state"] = "in_progress"
    probe["approval"] = None
    return _approve(probe)


def create_review_server(folder: Path, draft_path: Path, port: int = 0):
    """Builds (but does not run) the loopback save server.

    Returns (server, token, state). Compare-and-swap uses the persisted draft
    digest, so a stale page cannot overwrite a draft changed by a later scan.
    The served page is regenerated after every accepted save.

    Fail-closed: a present-but-unreadable draft raises DraftError before any
    page is rendered or served.
    """
    token = secrets.token_urlsafe(24)
    # Shared loader: aborts on malformed/incomplete drafts; missing file -> empty.
    current = load_draft_for_review(draft_path)
    state: Dict[str, Any] = {
        "folder": folder,
        "draft_path": draft_path,
        "token": token,
        "expected_digest": _state_digest(current),
        "expected_revision": int(current.get("revision") or 1),
        "out_file": None,
    }

    def _render() -> None:
        out_file, _ = generate_review_html(
            folder,
            draft_path=draft_path,
            save_endpoint="/save",
            save_token=token,
            save_digest=state["expected_digest"],
        )
        state["out_file"] = out_file

    _render()

    class Handler(BaseHTTPRequestHandler):
        def _headers(self, code: int = 200, ctype: str = "text/html; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Security-Policy", "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()

        def log_message(self, *a: Any) -> None:
            pass

        def do_GET(self) -> None:
            if self.path.split("?")[0] not in ("/", "/review.html"):
                self._headers(404, "text/plain")
                self.wfile.write(b"not found")
                return
            try:
                data = state["out_file"].read_bytes()
            except Exception as e:
                self._headers(500, "text/plain")
                self.wfile.write(f"cannot read review page: {e}".encode())
                return
            self._headers(200, "text/html; charset=utf-8")
            self.wfile.write(data)

        def do_POST(self) -> None:
            if self.path.split("?")[0] != "/save":
                self._headers(404, "text/plain")
                self.wfile.write(b"not found")
                return
            if self.headers.get("X-Session-Token") != state["token"]:
                self._headers(403, "application/json")
                self.wfile.write(b'{"error":"bad session token"}')
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except Exception:
                length = 0
            if length <= 0 or length > 100 * 1024 * 1024:
                self._headers(400, "application/json")
                self.wfile.write(b'{"error":"bad payload size"}')
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._headers(400, "application/json")
                self.wfile.write(b'{"error":"invalid JSON"}')
                return
            incoming = payload.get("draft")
            if not isinstance(incoming, dict) or not isinstance(incoming.get("stickers"), dict):
                self._headers(400, "application/json")
                self.wfile.write(b'{"error":"invalid draft"}')
                return
            # Compare-and-swap on the persisted digest: a scan (or any other
            # writer) that changed the draft after this page was generated fails
            # the save instead of being silently overwritten.
            try:
                # Use the same loader as page generation so a missing file or
                # a v2 migration has one canonical digest on both sides of CAS.
                disk = load_draft_for_review(draft_path)
            except DraftError as e:
                self._headers(409, "application/json")
                self.wfile.write(json.dumps({"error": f"draft unreadable on disk ({e}); back it up before saving"}).encode())
                return
            disk_digest = _state_digest(disk)
            if payload.get("base_digest") != state["expected_digest"] or disk_digest != state["expected_digest"]:
                self._headers(409, "application/json")
                self.wfile.write(b'{"error":"draft changed since page load (stale page); regenerate the page"}')
                return
            incoming["version"] = 3
            incoming["revision"] = int(disk.get("revision") or 1) + 1
            # Authoritative approval: the browser's claim is re-validated here and
            # persisted with a server-computed digest, never silently dropped.
            approval_errors: List[str] = []
            approved = False
            if incoming.get("pack_state") == "approved":
                approval_errors = _server_validate_approval(incoming)
                if approval_errors:
                    incoming["pack_state"] = "in_progress"
                    incoming["approval"] = None
                else:
                    try:
                        from classify_and_build import approve_pack as _approve
                    except Exception:
                        _approve = None  # type: ignore
                    if _approve is None:
                        incoming["pack_state"] = "in_progress"
                        incoming["approval"] = None
                        approval_errors = ["server validator unavailable; approve via CLI"]
                    else:
                        _approve(incoming)
                        approved = True
            tmp = draft_path.parent / f".{draft_path.name}.{os.getpid()}.tmp"
            tmp.write_text(json.dumps(incoming, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, draft_path)
            state["expected_digest"] = _state_digest(incoming)
            state["expected_revision"] = int(incoming.get("revision") or 1)
            _render()
            self._headers(200, "application/json")
            self.wfile.write(json.dumps({
                "ok": True,
                "revision": state["expected_revision"],
                "digest": state["expected_digest"],
                "approved": approved,
                "approval": incoming.get("approval"),
                "approval_errors": approval_errors,
            }).encode())

    server = HTTPServer(("127.0.0.1", port), Handler)
    return server, token, state


def serve_review(folder: Path, draft_path: Path, port: int = 0) -> None:
    """Runs the loopback save server until interrupted."""
    server, _token, state = create_review_server(folder, draft_path, port=port)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/"
    # Flush: when stdout is redirected to a file (wizard server log, CI),
    # block buffering would otherwise hide the banner indefinitely.
    print(f"Review server (loopback only): {url}", flush=True)
    print(f"  Folder: {folder.resolve()}", flush=True)
    print(f"  Draft:  {draft_path}", flush=True)
    print(f"  Static fallback: file://{state['out_file'].resolve()}", flush=True)
    print("Press Ctrl+C to stop. Saves compare-and-swap on the draft digest and regenerate the page.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser(description="Signal Stickers Review & Curation Page Generator")
    parser.add_argument("folder", help="Directory containing stickers (explicit; required)")
    parser.add_argument("--draft", default="pack_draft.json", help="Path to pack_draft.json")
    parser.add_argument("--yaml", default="stickers.yaml", help="Legacy manifest name (never trusted as input)")
    parser.add_argument("--serve", action="store_true", help="Serve the page on loopback with direct save")
    parser.add_argument("--port", type=int, default=0, help="Loopback port (0 = random)")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"Error: pack folder '{folder}' does not exist.")
    draft_path = folder / args.draft if not Path(args.draft).is_absolute() else Path(args.draft)

    if args.serve:
        try:
            serve_review(folder, draft_path, port=args.port)
        except DraftError as e:
            sys.exit(f"Error: {e}")
        return
    try:
        out_file, stats = generate_review_html(folder, draft_path=draft_path)
    except DraftError as e:
        sys.exit(f"Error: {e}")
    size_mb = out_file.stat().st_size / 1024 / 1024

    print(f"Review page: {out_file.resolve()} ({size_mb:.1f} MB, images embedded)")
    print(
        f"  {stats['total']} sticker(s): {stats['kept']} kept, "
        f"{stats.get('undecided', 0)} undecided, {stats['excluded']} excluded, "
        f"{stats['untagged']} awaiting a final single emoji"
    )
    if stats["clusters"]:
        print(f"  {stats['clusters']} visually similar group(s) to curate (candidates, not duplicates)")
    if stats["missing"]:
        print(f"  Warning: {stats['missing']} draft entry/entries have no image on disk and were skipped.")

    print("\nIn the page:")
    print("  1. Resolve every Undecided card (Keep Only / Keep? / Exclude / Later).")
    print("  2. Give each kept sticker exactly one emoji; Save marks dirty state.")
    print("  3. Set title/author/cover, then Approve Pack and Save.")
    print("  4. For turnkey saves: ./stickers curate --serve (loopback server).")
    print("\nStatic fallback: click Download draft and copy it over")
    print(f"     {draft_path}")
    print("  then run: ./stickers export" + (f" {folder}" if folder else ""))


if __name__ == "__main__":
    main()
