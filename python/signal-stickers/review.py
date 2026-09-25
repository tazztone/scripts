#!/usr/bin/env python3
"""Interactive Signal Sticker Pack Curation & Review Tool.

Supports:
- Visual Cluster Curation: Side-by-side variation review and 1-click 'Keep Only This' per cluster.
- Multi-Emoji Review: 1-3 emojis with strict in-page validation matching Python registry.
- Safe YAML & Draft Export: Blocks export on invalid assignments, serializes valid YAML.
- Contrast Previews: Dark, Light, White, and Black backgrounds.

Usage:
  python review.py ./webp
  # Then open the generated review.html in any web browser.
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
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
    from emojis import EMOJI_REGISTRY, extract_emojis, format_emoji_sequence, validate_emoji_sequence
except ImportError:
    from .emojis import EMOJI_REGISTRY, extract_emojis, format_emoji_sequence, validate_emoji_sequence

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
        <h1>{title}</h1>
        <span class="badge badge-active" id="badgeActive">{count_active} Kept</span>
        <span class="badge badge-cluster" id="badgeCluster">{count_clusters} Clusters</span>
        <span class="badge badge-deleted" id="badgeExcluded">{count_excluded} Excluded</span>
        <span class="badge">Author: {author}</span>
      </div>

      <div class="header-controls">
        <button class="btn btn-secondary" onclick="exportDraftJson()">Save Draft (JSON)</button>
        <button id="exportYamlBtn" onclick="exportYaml()">Export stickers.yaml</button>
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
    const META = {meta_json};
    const EMOJI_REGISTRY = {emoji_registry_json};
    let currentFilter = 'all';
    let currentSort = 'cluster';

    // Undo history stack
    const undoStack = [];

    // Track excluded files
    const excludedFiles = new Set({excluded_files_json});

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
      const found = extractKnownEmojis(clean);
      const recon = found.join('');
      if (recon !== clean) return {{ valid: false, emojis: found, msg: 'Invalid or unregistered character' }};
      if (found.length < 1 || found.length > 3) return {{ valid: false, emojis: found, msg: 'Must be 1-3 emojis' }};
      return {{ valid: true, emojis: found, msg: null }};
    }}

    function getCardEmoji(card) {{
      const inp = card.querySelector('.emoji-input');
      return (inp ? inp.value : card.dataset.emoji || '').trim();
    }}

    function getPrimaryEmoji(card) {{
      const text = getCardEmoji(card);
      const found = extractKnownEmojis(text);
      return found.length > 0 ? found[0] : '😐';
    }}

    function getUsageCounts() {{
      const counts = {{}};
      document.querySelectorAll('.card').forEach(card => {{
        if (excludedFiles.has(card.dataset.file)) return;
        const primary = getPrimaryEmoji(card);
        counts[primary] = (counts[primary] || 0) + 1;
      }});
      return counts;
    }}

    function renderOptionsForSelect(select, counts) {{
      let html = '<option value="" selected disabled>+ Add</option>';
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
        const isEx = excludedFiles.has(fn);
        const cid = card.dataset.cluster;
        const conf = parseFloat(card.dataset.conf || '1.0');
        const text = getCardEmoji(card);
        const val = validateSequence(text);

        if (cid) clusterStickersCount++;

        if (!val.valid) {{
          card.classList.add('card-invalid');
          const errEl = card.querySelector('.err-msg');
          if (errEl) errEl.textContent = '⚠ ' + val.msg;
          if (!isEx) invalidCount++;
        }} else {{
          card.classList.remove('card-invalid');
        }}

        if (!isEx) {{
          keptCount++;
          if (conf < 0.8 || !val.valid || card.dataset.status === 'needs_review') {{
            reviewCount++;
          }}
        }}

        if (isEx) {{
          card.classList.add('is-excluded');
          const btn = card.querySelector('.sel-btn');
          if (btn) btn.textContent = '↺ Restore';
        }} else {{
          card.classList.remove('is-excluded');
          const btn = card.querySelector('.sel-btn');
          if (btn) btn.textContent = '✕ Exclude';
        }}
      }});

      const totalCount = cards.length;
      const exCount = excludedFiles.size;

      document.getElementById('badgeActive').textContent = keptCount + ' Kept';
      document.getElementById('badgeExcluded').textContent = exCount + ' Excluded';
      document.getElementById('tabCountAll').textContent = totalCount;
      document.getElementById('tabCountClusters').textContent = clusterStickersCount;
      document.getElementById('tabCountReview').textContent = reviewCount;
      document.getElementById('tabCountKept').textContent = keptCount;
      document.getElementById('tabCountExcluded').textContent = exCount;

      const exportBtn = document.getElementById('exportYamlBtn');
      if (invalidCount > 0) {{
        exportBtn.style.opacity = '0.5';
        exportBtn.title = invalidCount + ' kept card(s) have invalid emoji sequences!';
      }} else {{
        exportBtn.style.opacity = '1';
        exportBtn.title = 'Export stickers.yaml';
      }}
    }}

    function toggleSelect(btn) {{
      const card = btn.closest('.card');
      const fn = card.dataset.file;
      const prev = new Set(excludedFiles);

      if (excludedFiles.has(fn)) {{
        excludedFiles.delete(fn);
        card.dataset.selection = 'keep';
      }} else {{
        excludedFiles.add(fn);
        card.dataset.selection = 'exclude';
      }}

      undoStack.push({{
        desc: 'Toggled ' + fn,
        revert: () => {{
          excludedFiles.clear();
          prev.forEach(f => excludedFiles.add(f));
          updateCountsAndValidation();
          filterCards();
        }}
      }});

      updateCountsAndValidation();
      refreshAllSelects();
      filterCards();
    }}

    function keepOnlyInCluster(btn) {{
      const currentCard = btn.closest('.card');
      const currentFile = currentCard.dataset.file;
      const cid = currentCard.dataset.cluster;
      if (!cid) return;

      const prev = new Set(excludedFiles);
      let countExcluded = 0;

      document.querySelectorAll('.card').forEach(card => {{
        if (card.dataset.cluster === cid) {{
          const fn = card.dataset.file;
          if (fn !== currentFile) {{
            excludedFiles.add(fn);
            card.dataset.selection = 'exclude';
            countExcluded++;
          }} else {{
            excludedFiles.delete(fn);
            card.dataset.selection = 'keep';
          }}
        }}
      }});

      undoStack.push({{
        desc: 'Keep only ' + currentFile + ' in ' + cid,
        revert: () => {{
          excludedFiles.clear();
          prev.forEach(f => excludedFiles.add(f));
          updateCountsAndValidation();
          filterCards();
        }}
      }});

      updateCountsAndValidation();
      refreshAllSelects();
      filterCards();
      showToast('Kept ' + currentFile + ' and excluded ' + countExcluded + ' other variations in ' + cid, true);
    }}

    function onEmojiInput(input) {{
      const card = input.closest('.card');
      card.dataset.emoji = input.value.trim();
      updateCountsAndValidation();
      refreshAllSelects();
      if (currentSort === 'emoji') sortCards('emoji');
    }}

    function onEmojiAdd(select) {{
      const chosen = select.value;
      if (!chosen) return;
      const card = select.closest('.card');
      const input = card.querySelector('.emoji-input');
      if (input) {{
        let current = input.value.trim();
        const found = extractKnownEmojis(current);
        if (found.length < 3 && !found.includes(chosen)) {{
          input.value = (current + chosen).trim();
          onEmojiInput(input);
        }}
      }}
      select.selectedIndex = 0;
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
        const isEx = excludedFiles.has(card.dataset.file);
        const isInv = card.classList.contains('card-invalid');

        let matchFilter = true;
        if (currentFilter === 'clusters') {{
          matchFilter = !!cid;
        }} else if (currentFilter === 'review') {{
          matchFilter = !isEx && (conf < 0.8 || isInv || card.dataset.status === 'needs_review');
        }} else if (currentFilter === 'kept') {{
          matchFilter = !isEx;
        }} else if (currentFilter === 'excluded') {{
          matchFilter = isEx;
        }}

        let matchSearch = fn.includes(q) || emoji.includes(q) || cid.includes(q);
        card.style.display = (matchFilter && matchSearch) ? 'flex' : 'none';
      }});
    }}

    function showToast(msg, withUndo = false) {{
      const toast = document.getElementById('toast');
      if (withUndo && undoStack.length > 0) {{
        toast.className = 'toast toast-undo';
        toast.innerHTML = '<span>' + msg + '</span> <button class="btn btn-secondary" style="padding:3px 8px;font-size:11px;" onclick="undoLast()">Undo</button>';
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
      last.revert();
      showToast('Reverted: ' + last.desc, false);
    }}

    function collectDraft() {{
      const draft = {{
        version: 2,
        meta: META,
        similarity_groups: {{}},
        stickers: {{}}
      }};

      document.querySelectorAll('.card').forEach(card => {{
        const fn = card.dataset.file;
        const isEx = excludedFiles.has(fn);
        const text = getCardEmoji(card);
        const val = validateSequence(text);
        const cid = card.dataset.cluster || null;

        draft.stickers[fn] = {{
          selection: isEx ? 'exclude' : 'keep',
          similarity_group: cid,
          emojis: val.valid ? val.emojis : [],
          confidence: parseFloat(card.dataset.conf || '1.0'),
          reason: card.querySelector('.reason') ? card.querySelector('.reason').textContent : '',
          review_status: isEx ? 'culled' : (val.valid ? 'approved' : 'needs_review')
        }};
      }});

      // Preserve the similarity groups computed during --scan. The cards only
      // carry a cluster id, so rebuild the membership lists from the DOM.
      document.querySelectorAll('.card').forEach(card => {{
        const cid = card.dataset.cluster;
        if (!cid) return;
        if (!draft.similarity_groups[cid]) draft.similarity_groups[cid] = [];
        draft.similarity_groups[cid].push(card.dataset.file);
      }});

      return draft;
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

    function exportDraftJson() {{
      downloadBlob(
        JSON.stringify(collectDraft(), null, 2),
        'pack_draft.json',
        'application/json'
      );
      showToast('Downloaded pack_draft.json — copy it into your pack folder to keep your edits.', true);
    }}

    function safeYamlEscape(val) {{
      const str = String(val);
      return '"' + str.replace(/\\\\/g, '\\\\\\\\').replace(/"/g, '\\\\"') + '"';
    }}

    function exportYaml() {{
      let hasInvalid = false;
      const stickersList = [];

      document.querySelectorAll('.card').forEach(card => {{
        const fn = card.dataset.file;
        if (excludedFiles.has(fn)) return;

        const text = getCardEmoji(card);
        const val = validateSequence(text);
        if (!val.valid) {{
          hasInvalid = true;
          return;
        }}
        stickersList.push({{ chr: val.emojis.join(''), file: fn }});
      }});

      if (hasInvalid) {{
        alert('Cannot export: Some kept stickers have invalid emoji sequences! Filter by "Needs Review" to fix them.');
        return;
      }}

      let y = 'meta:\\n';
      y += '  title: ' + safeYamlEscape(META.title || 'Signal Stickers') + '\\n';
      y += '  author: ' + safeYamlEscape(META.author || 'Author') + '\\n';
      if (stickersList.length > 0) {{
        y += '  cover: ' + safeYamlEscape(META.cover || stickersList[0].file) + '\\n';
      }}
      y += 'stickers:\\n';
      for (const item of stickersList) {{
        y += '  - chr: ' + safeYamlEscape(item.chr) + '\\n    file: ' + safeYamlEscape(item.file) + '\\n';
      }}

      downloadBlob(y, 'stickers.yaml', 'text/yaml;charset=utf-8');

      showToast(
        'Downloaded stickers.yaml (' + stickersList.length + ' stickers). ' +
        'To upload from the pack folder, save the draft and run ./stickers export instead.',
        true
      );
    }}

    // Warn before leaving the page with unsaved changes, since every edit lives
    // only in this tab until the draft is downloaded.
    window.addEventListener('beforeunload', (e) => {{
      if (excludedFiles.size > 0 || undoStack.length > 0) {{
        e.preventDefault();
        e.returnValue = '';
      }}
    }});

    window.addEventListener('DOMContentLoaded', () => {{
      updateCountsAndValidation();
      refreshAllSelects();
      sortCards('cluster');
    }});
  </script>
</body>
</html>
"""


def generate_review_html(
    folder: Path,
    draft_path: Optional[Path] = None,
    yaml_path: Optional[Path] = None,
    cache_path: Optional[Path] = None,
) -> Path:
    """Generates the responsive HTML review page from pack_draft.json (or fallback)."""
    draft_file = draft_path or (folder / "pack_draft.json")
    draft_data = {}
    if draft_file.exists():
        try:
            draft_data = json.loads(draft_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Could not read {draft_file}: {e}")

    stickers_items = []
    meta = draft_data.get("meta", {"title": "Signal Stickers", "author": "tazztone"})

    if draft_data and "stickers" in draft_data:
        for fn, sdata in draft_data["stickers"].items():
            stickers_items.append((fn, sdata))
    else:
        yp = yaml_path or (folder / "stickers.yaml")
        if yp.exists():
            doc = yaml.safe_load(yp.read_text(encoding="utf-8"))
            meta = doc.get("meta", meta)
            for s in doc.get("stickers", []):
                fn = s.get("file", "")
                stickers_items.append((fn, {"emojis": [s.get("chr", "🙂")], "selection": "keep"}))

    cards = []
    excluded_files = []
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
        if sel == "exclude":
            excluded_files.append(file_name)

        current_emojis = info.get("emojis") or info.get("suggested_emojis") or []
        emoji_str = format_emoji_sequence(current_emojis, fallback="") or ""
        conf = float(info.get("confidence", 1.0))
        reason = info.get("reason", "")
        status = info.get("review_status", "pending")

        conf_class = "conf-low" if conf < 0.6 else ("conf-mid" if conf < 0.8 else "conf-ok")
        cluster_class = "in-cluster" if cid else ""
        ex_class = "is-excluded" if sel == "exclude" else ""
        size_kb = img_path.stat().st_size / 1024

        cluster_tag_html = (
            f'<span class="cluster-tag" onclick="filterByCluster(\'{cid}\')" title="Filter by {cid}">{cid}</span>'
            if cid
            else ""
        )
        keep_only_html = (
            f'<button type="button" class="keep-only-btn" onclick="keepOnlyInCluster(this)" title="Keep this variation and exclude other variations in {cid}">⚡ Keep Only</button>'
            if cid
            else ""
        )
        sel_label = "↺ Restore" if sel == "exclude" else "✕ Exclude"

        card_html = f"""
        <div class="card {conf_class} {cluster_class} {ex_class}" data-file="{file_name}" data-cluster="{cid}" data-selection="{sel}" data-emoji="{emoji_str}" data-conf="{conf:.2f}" data-status="{status}">
          <div class="card-topbar">
            {cluster_tag_html}
            {keep_only_html}
            <button type="button" class="sel-btn" onclick="toggleSelect(this)">{sel_label}</button>
          </div>
          <div class="sticker-container">
            <div class="excluded-badge">EXCLUDED</div>
            <img class="sticker-img" src="{src}" loading="lazy" alt="{file_name}">
          </div>
          <div class="emoji-bar">
            <input type="text" class="emoji-input" value="{emoji_str}" placeholder="emoji" title="Edit emojis (1-3)" oninput="onEmojiInput(this)">
            <select class="emoji-select" onchange="onEmojiAdd(this)" title="Add an emoji from registry"><option value="" selected disabled>+ Add</option></select>
          </div>
          <div class="err-msg">⚠ Invalid emoji</div>
          <div class="meta-row">
            <span>{size_kb:.0f} KB</span>
            <span>conf: {conf:.2f}</span>
          </div>
          <div class="reason" title="{reason}">{reason or '—'}</div>
          <div class="filename">{file_name}</div>
        </div>
        """
        cards.append(card_html)

    total_count = len(cards)
    ex_count = len(excluded_files)
    active_count = total_count - ex_count
    clustered_count = sum(1 for _, info in stickers_items if info.get("similarity_group"))

    html_content = HTML_TEMPLATE.format(
        title=meta.get("title", "Signal Stickers"),
        author=meta.get("author", "Unknown"),
        count_total=total_count,
        count_active=active_count,
        count_excluded=ex_count,
        count_clusters=len(clusters_set),
        count_clustered=clustered_count,
        cards="".join(cards),
        meta_json=json.dumps(meta, ensure_ascii=False),
        emoji_registry_json=json.dumps(EMOJI_REGISTRY, ensure_ascii=False),
        excluded_files_json=json.dumps(excluded_files),
    )

    out_path = folder / "review.html"
    out_path.write_text(html_content, encoding="utf-8")

    # Counted over rendered cards, not draft entries: entries whose image is
    # missing from disk are skipped above and never reach the page.
    untagged = sum(1 for c in cards if 'value="" placeholder="emoji"' in c)
    stats = {
        "total": total_count,
        "kept": active_count,
        "excluded": ex_count,
        "clusters": len(clusters_set),
        "untagged": untagged,
        "missing": len(stickers_items) - total_count,
    }
    return out_path, stats


def main():
    parser = argparse.ArgumentParser(description="Signal Stickers Review & Curation Page Generator")
    parser.add_argument("folder", help="Directory containing stickers")
    parser.add_argument("--draft", default="pack_draft.json", help="Path to pack_draft.json")
    parser.add_argument("--yaml", default="stickers.yaml", help="Path to stickers.yaml")
    args = parser.parse_args()

    folder = Path(args.folder)
    draft_path = folder / args.draft if not Path(args.draft).is_absolute() else Path(args.draft)
    yaml_path = folder / args.yaml if not Path(args.yaml).is_absolute() else Path(args.yaml)

    out_file, stats = generate_review_html(
        folder, draft_path=draft_path, yaml_path=yaml_path
    )
    size_mb = out_file.stat().st_size / 1024 / 1024

    print(f"Review page: {out_file.resolve()} ({size_mb:.1f} MB, images embedded)")
    print(
        f"  {stats['total']} sticker(s): {stats['kept']} kept, "
        f"{stats['excluded']} excluded, {stats['untagged']} awaiting an emoji"
    )
    if stats["clusters"]:
        print(f"  {stats['clusters']} visual cluster(s) to curate")
    if stats["missing"]:
        print(
            f"  Warning: {stats['missing']} draft entry/entries have no image on disk "
            f"and were skipped."
        )

    print("\nIn the page:")
    print("  1. Click 'Keep Only' on the best variation in each orange cluster.")
    print("  2. Check the suggested emojis; fix anything wrong or untagged.")
    print("  3. Use Light/Dark/White/Black to check contrast on transparent edges.")
    print("\nThen save your work back to disk:")
    print("  a. Click 'Save Draft (JSON)' and copy the downloaded file to")
    print(f"     {draft_path}")
    print("  b. Run: ./stickers export" + (f" {folder}" if folder else ""))


if __name__ == "__main__":
    main()
