# Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler

All-in-one userscript for Toppreise.ch that highlights best prices, excludes unwanted keywords, filters categories into high-level groups, filters/sorts by offer count, and automates price alarm creation.

## 🚀 Installation

Requires Violentmonkey (or a compatible userscript manager):
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
- [Chrome / Brave](https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT (v2.4.1)**](https://raw.githubusercontent.com/tazztone/scripts/131a9c25d400791a7df622e8b05a860a8dc3d902/userscripts/toppreise/toppreise.user.js)

---

## ⚡ Features

1. **📁 High-Level Category Group Filtering**: Maps subcategories (e.g. `Abenteuer`, `Krimi`, `Mehr Komoedie`) directly to top-level root categories (`Filme`, `Spielwaren`, `Computer & Zubehör`, `Videogames`). Filter out an entire high-level group with a single click instead of toggling dozens of individual genres.
2. **📂 Space-Saving Collapsible Accordion Pills**: Category pills collapse into high-level Group Pills (`📁 Filme (8)`, `📁 Spielwaren (13)`) by default. Click the expand chevron (`▶`/`▼`) on any group pill to reveal child subcategories on demand for fine-grained filtering.
3. **⚡ Compact Power Filter Bar**: Single-row top control bar prepended directly to `#FrameContent`. The Negativ-Filter (`🚫 Negativ-Filter:`) is styled cleanly with inline label text outside the input box, while category pills collapse into an on-demand drawer (`🏷️ Kategorien (N) ▼`).
4. **Händler Bestpreis Highlights**: Highlights products with an emerald green border & "Best Price" badge when a filtered store is the cheapest (or within custom margin %), while dimming/hiding non-cheapest products.
5. **Negativer Textfilter (Ausschluss)**: Exclude products containing specific unwanted keywords (e.g. `SAMSUNG, Hülle, Case, Refurbished, Gebraucht`) with word-boundary precision via the inline search bar or modal.
6. **Angebote & Sortierung**: Filter out marketplace items with fewer than $N$ offers, plus optional client-side re-sorting by total offer count.
7. **Preisalarm Auto-Filler**: Automatically configures target price (e.g. 60% of current price) and 2-year duration upon clicking the price alarm bell icon, supporting Swiss currency formatting (`CHF 1'299.–`).
8. **Floating Quick-Control Pill Toolbar**: Bottom floating toolbar displaying hidden product count, 1-click reveal preview toggle, 1-click **Reset Filters** button, and offer count stepper.

---

## 🛠️ Category Hierarchy Generator Tool

The repository includes an automated category map generator in the `tools/` subfolder:

- **Location**: [`tools/generate_category_map.py`](file:///home/tazztone/_coding/scripts/userscripts/toppreise/tools/generate_category_map.py)
- **Outputs**: 
  - `tools/category_map.json`: Full category hierarchy JSON.
  - `tools/category_lookup_generated.js`: Generated JS lookup dictionary.

### Running the Generator Tool
```bash
python3 userscripts/toppreise/tools/generate_category_map.py
```
The generator uses multi-threaded parallel requests and built-in offline seeds to extract Toppreise category hierarchies in under 5 seconds.

---

## ⚙️ Configuration & Persistence

Click the floating **gear button** in the bottom corner of Toppreise.ch to open the glassmorphic settings panel:

- **Händler Bestpreis**: Mode (`'dim'`, `'hide'`, `'highlight-only'`), margin %, opacity, shipping toggle.
- **Negativer Textfilter**: Comma-separated list of keywords to hide.
- **Kategorien-Filter**: Clickable group and subcategory pills to blacklist specific categories.
- **Angebote & Sortierung**: Set threshold for minimum dealer offers and sort order (`Meiste ⬇` / `Wenigste ⬆`).
- **Preisalarm Auto-Filler**: Target price percentage slider (default 60%), duration (default 2 years), auto-submit toggle.

> [!NOTE]
> All settings, excluded categories, and negative terms are saved **permanently** via `GM_setValue` / `GM_getValue` in Violentmonkey/Tampermonkey storage and persist indefinitely across browser sessions and site reloads.
