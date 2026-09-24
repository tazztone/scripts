#!/usr/bin/env python3
"""Interactive Signal Sticker Pack Review Tool.

Generates a responsive HTML review page to inspect sticker images, check contrast
against Signal Dark and Light themes, adjust assigned emojis, mark unwanted stickers
for deletion, sort by emoji to identify duplicate stickers, and display in the emoji
dropdown which emojis are already used (and how many times) vs unused.

Usage:
  python review.py ./webp
  # Then open the generated review.html in any web browser.
"""

import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    sys.exit("Error: PyYAML not installed. Run: pip install PyYAML")

# Import shared emoji registry
try:
    from emojis import EMOJI_REGISTRY
except ImportError:
    from .emojis import EMOJI_REGISTRY


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Signal Sticker Review — {title}</title>
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

    body.theme-white-bg .sticker-img {{
      background: #ffffff !important;
    }}

    body.theme-black-bg .sticker-img {{
      background: #121212 !important;
    }}

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

    .badge-active {{
      color: #12b76a;
      border-color: rgba(18, 183, 106, 0.4);
    }}
    .badge-deleted {{
      color: var(--danger);
      border-color: rgba(229, 72, 77, 0.4);
    }}
    .badge-dupe {{
      color: var(--warning);
      border-color: rgba(247, 144, 9, 0.4);
    }}
    .badge-unused {{
      color: #3b82f6;
      border-color: rgba(59, 130, 246, 0.4);
    }}

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

    button:hover, .btn:hover {{
      background: var(--accent-hover);
    }}

    .btn-danger {{
      background: var(--danger);
    }}
    .btn-danger:hover {{
      background: var(--danger-hover);
    }}

    .btn-secondary {{
      background: var(--card-bg);
      color: var(--text);
      border: 1px solid var(--border);
    }}
    .btn-secondary:hover {{
      background: var(--border);
    }}

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

    .filter-tab.active {{
      background: var(--accent);
      color: #fff;
    }}

    .filter-tab.active-warning {{
      background: var(--warning);
      color: #fff;
    }}

    .filter-tab.active-danger {{
      background: var(--danger);
      color: #fff;
    }}

    .ctrl-label {{
      font-size: 11px;
      font-weight: 600;
      color: var(--subtext);
      text-transform: uppercase;
      padding: 0 4px 0 6px;
    }}

    .deletion-banner {{
      background: rgba(229, 72, 77, 0.12);
      border: 1px solid rgba(229, 72, 77, 0.3);
      border-radius: 6px;
      padding: 8px 14px;
      display: none;
      align-items: center;
      justify-content: space-between;
      font-size: 13px;
      color: #ff8b8e;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(175px, 1fr));
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

    .card.is-duplicate {{
      border-color: #f79009;
      box-shadow: 0 0 0 1px #f79009 inset;
    }}

    .card.is-deleted {{
      opacity: 0.4;
      background: rgba(229, 72, 77, 0.08);
      border-color: var(--danger);
      border-style: dashed;
    }}
    .card.is-deleted .sticker-container {{
      filter: grayscale(80%);
    }}

    .card-topbar {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      min-height: 22px;
    }}

    .dupe-tag {{
      background: #f79009;
      color: #fff;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 10px;
      display: none;
    }}

    .del-btn {{
      background: transparent;
      border: 1px solid var(--border);
      color: var(--subtext);
      padding: 2px 7px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 11px;
      margin-left: auto;
      transition: background 0.15s, color 0.15s;
    }}
    .del-btn:hover {{
      background: var(--danger);
      border-color: var(--danger);
      color: #fff;
    }}
    .card.is-deleted .del-btn {{
      background: var(--danger);
      color: #fff;
      border-color: var(--danger);
    }}

    .deleted-badge {{
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
    .card.is-deleted .deleted-badge {{
      display: block;
    }}

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

    .sticker-img:hover {{
      transform: scale(1.08);
    }}

    .emoji-select {{
      width: 100%;
      font-size: 26px;
      text-align: center;
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      margin-top: 8px;
      padding: 4px;
      cursor: pointer;
    }}

    .emoji-select option {{
      font-size: 15px;
      text-align: left;
      padding: 6px 10px;
      background: #1c1d22;
      color: #e1e2e6;
    }}

    .emoji-select optgroup {{
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      text-align: left;
      padding: 8px 10px;
      color: #8e909a;
      background: #141518;
    }}

    body.theme-light .emoji-select option {{
      background: #ffffff;
      color: #1a1b1e;
    }}
    body.theme-light .emoji-select optgroup {{
      background: #f0f0f4;
      color: #555760;
    }}

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
      max-width: 150px;
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
      background: #12b76a;
      color: #fff;
      padding: 12px 20px;
      border-radius: 8px;
      font-weight: 500;
      display: none;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 1000;
    }}
  </style>
</head>
<body class="theme-dark">
  <div class="header-bar">
    <div class="header-row1">
      <div class="header-left">
        <h1>{title}</h1>
        <span class="badge badge-active" id="badgeActive">{count} Active</span>
        <span class="badge badge-dupe" id="badgeDupe" style="display:none;">0 Duplicates</span>
        <span class="badge badge-unused" id="badgeUnused">0 Available Unused</span>
        <span class="badge badge-deleted" id="badgeDeleted" style="display:none;">0 Deleted</span>
        <span class="badge">Author: {author}</span>
      </div>

      <div class="header-controls">
        <button onclick="exportYaml()">Export stickers.yaml</button>
      </div>
    </div>

    <div class="header-row1">
      <div class="header-controls">
        <input type="text" id="searchBox" class="search-box" placeholder="Search filename or emoji..." oninput="filterCards()">

        <div class="filter-tabs">
          <span class="ctrl-label">Filter:</span>
          <button class="filter-tab active" onclick="setFilter('all', this)">All (<span id="tabCountAll">{count}</span>)</button>
          <button class="filter-tab" id="tabDupes" onclick="setFilter('dupes', this)">Duplicates (<span id="tabCountDupes">0</span>)</button>
          <button class="filter-tab" onclick="setFilter('low', this)">Needs Review (<span id="tabCountLow">0</span>)</button>
          <button class="filter-tab" onclick="setFilter('deleted', this)">Deleted (<span id="tabCountDeleted">0</span>)</button>
        </div>

        <div class="filter-tabs">
          <span class="ctrl-label">Sort:</span>
          <button class="filter-tab active" id="sortEmojiBtn" onclick="setSort('emoji', this)">By Emoji</button>
          <button class="filter-tab" onclick="setSort('filename', this)">By Filename</button>
          <button class="filter-tab" onclick="setSort('conf', this)">By Confidence</button>
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

    <div class="deletion-banner" id="deletionBanner">
      <span id="deletionMsg">0 stickers marked for deletion will be excluded from stickers.yaml</span>
      <button class="btn btn-secondary" style="padding:4px 10px;font-size:12px;" onclick="copyDeleteCommand()">Copy 'rm' command</button>
    </div>
  </div>

  <div class="grid" id="cardGrid">
    {cards}
  </div>

  <div id="toast" class="toast">YAML exported successfully!</div>

  <script>
    const META = {meta_json};
    const EMOJI_REGISTRY = {emoji_registry_json};
    let currentFilter = 'all';
    let currentSort = 'emoji';

    // Track deleted filenames
    const deletedFiles = new Set();

    function getUsageCounts() {{
      const counts = {{}};
      document.querySelectorAll('.card').forEach(card => {{
        if (deletedFiles.has(card.dataset.file)) return;
        const em = card.dataset.emoji || card.querySelector('select').value;
        counts[em] = (counts[em] || 0) + 1;
      }});
      return counts;
    }}

    function renderOptionsForSelect(select, counts) {{
      const currentVal = select.dataset.current || select.value;
      let html = '';

      // Current emoji option at top
      const currCount = counts[currentVal] || 0;
      const currInfo = EMOJI_REGISTRY[currentVal] || {{}};
      const currName = currInfo.name ? ' (' + currInfo.name + ')' : '';
      const currUsageText = currCount > 1 ? ' — [' + currCount + 'x used in pack]' : ' — [1x used]';
      html += '<option value="' + currentVal + '" selected>' + currentVal + currName + currUsageText + '</option>';

      const unused = [];
      const used = [];

      for (const [em, info] of Object.entries(EMOJI_REGISTRY)) {{
        if (em === currentVal) continue;
        const cnt = counts[em] || 0;
        const name = info.name ? ' (' + info.name + ')' : '';
        if (cnt === 0) {{
          unused.push({{ em: em, label: em + name + ' — unused' }});
        }} else {{
          used.push({{ em: em, cnt: cnt, label: em + name + ' — ' + cnt + 'x used' }});
        }}
      }}

      // Sort used by count descending (highest duplicates first)
      used.sort((a, b) => b.cnt - a.cnt || a.label.localeCompare(b.label));

      // Optgroup: Unused Emojis
      html += '<optgroup label="✨ Available / Unused (' + unused.length + ')">';
      for (const item of unused) {{
        html += '<option value="' + item.em + '">' + item.label + '</option>';
      }}
      html += '</optgroup>';

      // Optgroup: Already In Use
      if (used.length > 0) {{
        html += '<optgroup label="⚠️ Already In Use (' + used.length + ')">';
        for (const item of used) {{
          html += '<option value="' + item.em + '">' + item.label + '</option>';
        }}
        html += '</optgroup>';
      }}

      select.innerHTML = html;
    }}

    function refreshAllSelects() {{
      const counts = getUsageCounts();
      document.querySelectorAll('select.emoji-select').forEach(sel => {{
        renderOptionsForSelect(sel, counts);
      }});
    }}

    function updateDuplicatesAndCounts() {{
      const emojiCounts = getUsageCounts();
      const cards = Array.from(document.querySelectorAll('.card'));

      let dupeStickersCount = 0;
      let lowConfCount = 0;

      cards.forEach(card => {{
        const fn = card.dataset.file;
        const emoji = card.dataset.emoji || card.querySelector('select').value;
        const conf = parseFloat(card.dataset.conf || '1.0');
        const count = emojiCounts[emoji] || 0;
        const dupeTag = card.querySelector('.dupe-tag');
        const isDel = deletedFiles.has(fn);

        if (!isDel && count > 1) {{
          dupeStickersCount++;
          card.classList.add('is-duplicate');
          if (dupeTag) {{
            dupeTag.textContent = count + 'x ' + emoji;
            dupeTag.style.display = 'inline-block';
          }}
        }} else {{
          card.classList.remove('is-duplicate');
          if (dupeTag) dupeTag.style.display = 'none';
        }}

        if (!isDel && conf < 0.8) {{
          lowConfCount++;
        }}
      }});

      // Update counters in header
      const totalCount = cards.length;
      const delCount = deletedFiles.size;
      const activeCount = totalCount - delCount;

      document.getElementById('badgeActive').textContent = activeCount + ' Active';
      document.getElementById('tabCountAll').textContent = totalCount;
      document.getElementById('tabCountLow').textContent = lowConfCount;
      document.getElementById('tabCountDupes').textContent = dupeStickersCount;
      document.getElementById('tabCountDeleted').textContent = delCount;

      // Count unused available in registry
      let unusedCount = 0;
      for (const em in EMOJI_REGISTRY) {{
        if (!emojiCounts[em]) unusedCount++;
      }}
      const badgeUnused = document.getElementById('badgeUnused');
      if (badgeUnused) {{
        badgeUnused.textContent = unusedCount + ' Unused Available';
      }}

      const badgeDupe = document.getElementById('badgeDupe');
      if (dupeStickersCount > 0) {{
        badgeDupe.textContent = dupeStickersCount + ' Duplicates';
        badgeDupe.style.display = 'inline-block';
      }} else {{
        badgeDupe.style.display = 'none';
      }}

      const badgeDel = document.getElementById('badgeDeleted');
      const delBanner = document.getElementById('deletionBanner');
      if (delCount > 0) {{
        badgeDel.textContent = delCount + ' Excluded';
        badgeDel.style.display = 'inline-block';
        delBanner.style.display = 'flex';
        document.getElementById('deletionMsg').textContent =
          delCount + ' sticker(s) marked for exclusion (will not be included in exported stickers.yaml).';
      }} else {{
        badgeDel.style.display = 'none';
        delBanner.style.display = 'none';
      }}
    }}

    function toggleDelete(btn) {{
      const card = btn.closest('.card');
      const fn = card.dataset.file;
      if (deletedFiles.has(fn)) {{
        deletedFiles.delete(fn);
        card.classList.remove('is-deleted');
        btn.textContent = '✕ Exclude';
      }} else {{
        deletedFiles.add(fn);
        card.classList.add('is-deleted');
        btn.textContent = '↺ Restore';
      }}
      updateDuplicatesAndCounts();
      refreshAllSelects();
      filterCards();
    }}

    function onEmojiChange(select) {{
      const card = select.closest('.card');
      card.dataset.emoji = select.value;
      select.dataset.current = select.value;
      updateDuplicatesAndCounts();
      refreshAllSelects();
      if (currentSort === 'emoji') {{
        sortCards('emoji');
      }} else {{
        filterCards();
      }}
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
        if (sortType === 'emoji') {{
          const ea = a.dataset.emoji || a.querySelector('select').value;
          const eb = b.dataset.emoji || b.querySelector('select').value;
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
        b.classList.remove('active');
        b.classList.remove('active-warning');
        b.classList.remove('active-danger');
      }});
      if (filterType === 'dupes') btn.classList.add('active-warning');
      else if (filterType === 'deleted') btn.classList.add('active-danger');
      else btn.classList.add('active');
      filterCards();
    }}

    function filterCards() {{
      const q = document.getElementById('searchBox').value.toLowerCase();
      document.querySelectorAll('.card').forEach(card => {{
        const fn = card.dataset.file.toLowerCase();
        const emoji = card.dataset.emoji || card.querySelector('select').value;
        const conf = parseFloat(card.dataset.conf || '1.0');
        const isDel = deletedFiles.has(card.dataset.file);
        const isDupe = card.classList.contains('is-duplicate');

        let matchFilter = true;
        if (currentFilter === 'dupes') {{
          matchFilter = !isDel && isDupe;
        }} else if (currentFilter === 'low') {{
          matchFilter = !isDel && conf < 0.8;
        }} else if (currentFilter === 'deleted') {{
          matchFilter = isDel;
        }} else {{
          matchFilter = true;
        }}

        let matchSearch = fn.includes(q) || emoji.includes(q);
        card.style.display = (matchFilter && matchSearch) ? 'flex' : 'none';
      }});
    }}

    function copyDeleteCommand() {{
      if (deletedFiles.size === 0) return;
      const cmd = "rm " + Array.from(deletedFiles).map(f => '"' + f + '"').join(" ");
      navigator.clipboard.writeText(cmd).then(() => {{
        showToast("Copied deletion command to clipboard!");
      }});
    }}

    function showToast(msg) {{
      const toast = document.getElementById('toast');
      toast.textContent = msg;
      toast.style.display = 'block';
      setTimeout(() => toast.style.display = 'none', 2500);
    }}

    function exportYaml() {{
      let y = "meta:\\n";
      for (const k in META) {{
        y += "  " + k + ': "' + META[k] + '"\\n';
      }}
      y += "stickers:\\n";

      let exportedCount = 0;
      document.querySelectorAll('.card').forEach(card => {{
        const file = card.dataset.file;
        if (deletedFiles.has(file)) return;

        const emoji = card.dataset.emoji || card.querySelector('select').value;
        y += '  - chr: "' + emoji + '"\\n    file: "' + file + '"\\n';
        exportedCount++;
      }});

      const blob = new Blob([y], {{ type: "text/yaml;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "stickers.yaml";
      a.click();
      URL.revokeObjectURL(url);

      showToast("Exported " + exportedCount + " stickers to stickers.yaml!");
    }}

    // Initial setup on load
    window.addEventListener('DOMContentLoaded', () => {{
      document.querySelectorAll('.card').forEach(card => {{
        const sel = card.querySelector('select');
        sel.dataset.current = sel.value;
      }});
      updateDuplicatesAndCounts();
      refreshAllSelects();
      sortCards('emoji');
    }});
  </script>
</body>
</html>
"""


def generate_review_html(
    folder: Path, yaml_path: Path, cache_path: Optional[Path] = None
) -> Path:
    """Generates an interactive HTML review page from stickers.yaml and images."""
    if not yaml_path.exists():
        sys.exit(f"Error: {yaml_path} does not exist.")

    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    meta = doc.get("meta", {})
    stickers = doc.get("stickers", [])

    cache: Dict[str, Dict[str, Any]] = {}
    if cache_path and cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    cards = []

    for s in stickers:
        file_name = s.get("file", "")
        img_path = folder / file_name
        if not img_path.exists():
            continue

        mt = mimetypes.guess_type(img_path.name)[0] or "image/png"
        if mt == "image/apng":
            mt = "image/png"
        b64 = base64.standard_b64encode(img_path.read_bytes()).decode("utf-8")
        src = f"data:{mt};base64,{b64}"

        current_emoji = s.get("chr", "🙂")
        info = cache.get(file_name, {})
        conf = float(info.get("confidence", 1.0))
        reason = info.get("reason", "")

        conf_class = "conf-low" if conf < 0.6 else ("conf-mid" if conf < 0.8 else "conf-ok")

        # Initial fallback option before JS hydration
        options_html = f'<option value="{current_emoji}" selected>{current_emoji}</option>'

        size_kb = img_path.stat().st_size / 1024

        card_html = f"""
        <div class="card {conf_class}" data-file="{file_name}" data-emoji="{current_emoji}" data-conf="{conf:.2f}">
          <div class="card-topbar">
            <span class="dupe-tag">Dupe</span>
            <button type="button" class="del-btn" onclick="toggleDelete(this)" title="Exclude from sticker pack">✕ Exclude</button>
          </div>
          <div class="sticker-container">
            <div class="deleted-badge">EXCLUDED</div>
            <img class="sticker-img" src="{src}" loading="lazy" alt="{file_name}">
          </div>
          <select class="emoji-select" onchange="onEmojiChange(this)">{options_html}</select>
          <div class="meta-row">
            <span>{size_kb:.0f} KB</span>
            <span>conf: {conf:.2f}</span>
          </div>
          <div class="reason" title="{reason}">{reason or '—'}</div>
          <div class="filename">{file_name}</div>
        </div>
        """
        cards.append(card_html)

    html_content = HTML_TEMPLATE.format(
        title=meta.get("title", "Signal Stickers"),
        author=meta.get("author", "Unknown"),
        count=len(stickers),
        cards="".join(cards),
        meta_json=json.dumps(meta, ensure_ascii=False),
        emoji_registry_json=json.dumps(EMOJI_REGISTRY, ensure_ascii=False),
    )

    out_path = folder / "review.html"
    out_path.write_text(html_content, encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Signal Stickers Review Page Generator")
    parser.add_argument("folder", help="Directory containing stickers and stickers.yaml")
    parser.add_argument(
        "--yaml", default="stickers.yaml", help="Path to stickers.yaml relative to folder"
    )
    parser.add_argument(
        "--cache", default="classification_cache.json", help="Path to classification cache JSON"
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    yaml_path = folder / args.yaml
    cache_path = Path(args.cache)
    if not cache_path.exists():
        cache_path = folder / args.cache

    out_file = generate_review_html(folder, yaml_path, cache_path)
    print(f"Generated review page: {out_file.resolve()}")
    print("Open this file in your browser to inspect and adjust sticker emojis.")
    print("Features: Shows used counts, groups unused emojis, mark for deletion, sort by emoji.")


if __name__ == "__main__":
    main()
