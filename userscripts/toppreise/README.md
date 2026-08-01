# Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler

All-in-one userscript for Toppreise.ch that highlights best price offers, excludes unwanted negative keywords, filters categories into high-level groups with floating popovers, sorts/filters by offer count, and automates price alarm creation.

## 🚀 Installation

Requires Violentmonkey (or a compatible userscript manager):
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
- [Chrome / Brave](https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT (v2.8.12)**](https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/toppreise/toppreise.user.js)

---

## ⚡ Features

1. **📁 Hierarchical Category Tree Engine & Zero-Orphan Resolution**: Multi-level resolution algorithm (`Root` $\rightarrow$ `Sub-Group` $\rightarrow$ `Sub-Sub-Group` $\rightarrow$ `Leaf`) with direct card URL path parsing (`/preisvergleich/<RootSlug>/...`), word-prefix matching, brand rules (*Lego*, *Playmobil*, *Cobi*, *Schleich*, *Barbie*, *Hot Wheels*, *CaDA*, *Amiibo* $\rightarrow$ 🧸 **Spielwaren** / 🎮 **Videogames**), and keyword fallback routing (*Fensterreinigungsroboter*, *Heissluftfritteusen*, *Vollautomaten* $\rightarrow$ ☕ **Haushalt & Küche**, *Crosstrainer*, *Skihelme*, *GPS* $\rightarrow$ ⚽ **Sport & Freizeit**, *Haarglaetter*, *Duschpflege*, *Parfum* $\rightarrow$ 🧴 **Drogerie**, *Dachboxen*, *Reifen* $\rightarrow$ 🚗 **Auto & Motorrad**, *Aktenvernichter*, *SSD*, *USB SpeicherSticks* $\rightarrow$ 💻 **Computer & Zubehör**). Eliminates orphan categories in `Sonstiges`.
2. **💬 Multi-Level Exclusion & Single-Click Group Toggling**: Group pills feature custom category emojis (🎬, 🧸, 💻, 🎮, 🎧, 📱, ☕, ⚽, 🚗, ⌚, etc.).
   - **1-Click Title Toggle**: Click a group pill title to toggle the **entire main group** ON/OFF (`GROUP:<Name>`) instantly.
   - **Chevron `▼` Dropdown**: Click the chevron to open a floating glassmorphic popover dropdown for granular sub-branch toggling.
3. **🔍 Real-Time Popover Quick-Search & Semantic Group States**: Popover dropdowns feature an inline real-time search bar to quickly isolate subcategories (e.g. typing "star" or "lego"). Popover pills feature distinct visual states:
   - **Strikethrough Line-Through Red**: Explicit full group block (`[Alle ausblenden]`) — blocks all current and future subcategories.
   - **Solid Red (No Strikethrough)**: All current subcategories individually excluded — future subcategories remain enabled.
   - **Amber Warning Border**: Partial exclusion state.
4. **⚡ Compact Power Filter Bar**: Single-row top control bar prepended directly to `#FrameContent`. The Negativ-Filter (`🚫 Negativ-Filter:`) is styled cleanly with inline label text outside the input box, while category pills collapse into an on-demand drawer (`🏷️ Kategorien (N) ▼`).
5. **Händler Bestpreis Highlights**: Highlights products with an emerald green border & "Best Price" badge when a filtered store is the cheapest (or within custom margin %), while dimming/hiding non-cheapest products.
6. **Negativer Textfilter (Ausschluss)**: Exclude products containing specific unwanted keywords (e.g. `SAMSUNG, Hülle, Case, Refurbished, Gebraucht`) with word-boundary precision via the inline search bar or modal.
7. **Angebote & Sortierung**: Filter out marketplace items with fewer than $N$ offers, plus optional client-side re-sorting by total offer count.
8. **Preisalarm Auto-Filler**: Automatically configures target price (e.g. 60% of current price) and 2-year duration upon clicking the price alarm bell icon, supporting Swiss currency formatting (`CHF 1'299.–`).
9. **Floating Quick-Control Pill Toolbar**: Bottom floating toolbar displaying hidden product count, 1-click reveal preview toggle, 1-click **Reset Filters** button, and offer count stepper.

---

## 🛠️ Multi-Threaded Category Hierarchy Generator Tool & Verification

The repository includes an automated category map crawler and verification tools in `tools/`:

- **Crawler & Injector**: [`tools/generate_category_map.py`](file:///home/tazztone/_coding/scripts/userscripts/toppreise/tools/generate_category_map.py)
  - `tools/category_map.json`: Detailed category taxonomy map.
  - `tools/category_lookup_generated.js`: Generated JS lookup dictionary.
  - **Auto-Injection**: Automatically updates `CATEGORY_LOOKUP` in `toppreise.user.js`.
- **Verification Tool**: [`tools/verify_category_map.py`](file:///home/tazztone/_coding/scripts/userscripts/toppreise/tools/verify_category_map.py)
  - Benchmarks mapping coverage against standard site subcategories.

### Running Tools
```bash
# Crawl site & generate category lookup map
python3 userscripts/toppreise/tools/generate_category_map.py

# Verify category lookup accuracy
python3 userscripts/toppreise/tools/verify_category_map.py
```
The generator uses multi-threaded parallel requests across 23 root trees and 200+ subcategory pages to build complete category mappings.

---

## 🚀 Instant Auto-Installer Tool & Auto-Updates

### 1. Instant 1-Click Update Script
Run the helper tool from your terminal to launch the latest commit-pinned version directly in your browser:
```bash
python3 userscripts/toppreise/tools/install_latest.py
```
This automatically fetches the latest Git commit hash and triggers your browser's Violentmonkey / Tampermonkey installer tab with 0 caching delay.

### 2. Automatic Background Updates (`@updateURL`)
The script includes embedded `@updateURL` and `@downloadURL` metadata headers. Violentmonkey and Tampermonkey will check GitHub automatically in the background and keep your installed userscript updated without requiring manual reinstalls.

---

## ⚙️ Configuration & Persistence

Click the floating **gear button** in the bottom corner of Toppreise.ch to open the glassmorphic settings panel:

- **Händler Bestpreis**: Mode (`'dim'`, `'hide'`, `'highlight-only'`), margin %, opacity, shipping toggle.
- **Negativer Textfilter**: Comma-separated list of keywords to hide.
- **Kategorien-Filter**: Clickable group and subcategory pills with popover dropdowns to blacklist specific categories.
- **Angebote & Sortierung**: Set threshold for minimum dealer offers and sort order (`Meiste ⬇` / `Wenigste ⬆`).
- **Preisalarm Auto-Filler**: Target price percentage slider (default 60%), duration (default 2 years), auto-submit toggle.

> [!NOTE]
> All settings, excluded categories, and negative terms are saved **permanently** via `GM_setValue` / `GM_getValue` in Violentmonkey/Tampermonkey storage and persist indefinitely across browser sessions and site reloads.
