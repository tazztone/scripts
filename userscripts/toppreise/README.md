# Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler

All-in-one userscript for Toppreise.ch that highlights best price offers, excludes unwanted negative keywords, filters categories into high-level groups with floating popovers, sorts/filters by offer count, and automates price alarm creation.

## 🚀 Installation

Requires Violentmonkey (or a compatible userscript manager):
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
- [Chrome / Brave](https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT (v2.9.3)**](https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/toppreise/toppreise.user.js)

---

## ⚡ Features

1. **🚫 1-Click Product Card Category Quick-Block & Toast Undo**: Direct "🚫 [Kategorie]" action button overlay on every product card (especially on `neue-toppreise`). Clicking instantly hides the product's category from the feed and displays a glassmorphic toast notification with a **"Rückgängig"** (Undo) action button.
2. **📁 Hierarchical Category Tree Engine & Zero-Orphan Resolution**: Multi-level resolution algorithm (`Root` $\rightarrow$ `Sub-Group` $\rightarrow$ `Sub-Sub-Group` $\rightarrow$ `Leaf`) with direct card URL path parsing (`/preisvergleich/<RootSlug>/...`), word-prefix matching, brand rules (*Lego*, *Playmobil*, *Cobi*, *Schleich*, *Barbie*, *Hot Wheels*, *CaDA*, *Amiibo* $\rightarrow$ 🧸 **Spielwaren** / 🎮 **Videogames**), and keyword fallback routing. Eliminates orphan categories in `Sonstiges`.
3. **💬 Multi-Level Exclusion & Single-Click Group Toggling**: Group pills feature custom category emojis (🎬, 🧸, 💻, 🎮, 🎧, 📱, ☕, ⚽, 🚗, ⌚, etc.).
   - **1-Click Title Toggle**: Click a group pill title to toggle the **entire main group** ON/OFF (`GROUP:<Name>`) instantly.
   - **Chevron `▼` Dropdown**: Click the chevron to open a floating glassmorphic popover dropdown for granular sub-branch toggling.
4. **🔍 Real-Time Popover Quick-Search & Semantic Group States**: Popover dropdowns feature an inline real-time search bar to quickly isolate subcategories (e.g. typing "star" or "lego"). Popover pills feature distinct visual states:
   - **Strikethrough Line-Through Red**: Explicit full group block (`[Alle ausblenden]`) — blocks all current and future subcategories.
   - **Solid Red (No Strikethrough)**: All current subcategories individually excluded.
   - **Amber Warning Border**: Partial exclusion state.
5. **🛡️ Encapsulated Shadow DOM Settings Modal (`#tp-root`)**: Floating action button (FAB) and settings dialog are isolated inside an open Shadow Root, elevated to the browser Top Layer via native `<dialog popover="auto">` to bypass host site z-index and CSS reset collisions. Popovers inside modal are mounted directly inside the dialog element.
6. **⚡ INP & Yield Protection**: Asynchronous chunked DOM processing with `requestAnimationFrame`, `scheduler.yield()`, DOM metadata caching on `dataset`, memory-buffered dynamic category updates, and Run-ID cancellation guards for instant responsiveness during filter interactions.
7. **Händler Bestpreis Highlights**: Highlights products with an emerald green border & "Best Price" badge when a filtered store is the cheapest (or within custom margin %), while dimming/hiding non-cheapest products.
8. **Negativer Textfilter (Ausschluss)**: Exclude products containing specific unwanted keywords (e.g. `SAMSUNG, Hülle, Case, Refurbished, Gebraucht`) with word-boundary precision via the inline search bar or modal.
9. **Angebote & Sortierung**: Filter out marketplace items with fewer than $N$ offers, plus optional client-side re-sorting by total offer count.
10. **Preisalarm Auto-Filler**: Automatically configures target price (e.g. 60% of current price) and 2-year duration upon clicking the price alarm bell icon, supporting Swiss currency formatting (`CHF 1'299.–`).
11. **Floating Quick-Control Pill Toolbar**: Bottom floating toolbar displaying hidden product count, 1-click reveal preview toggle, 1-click **Reset Filters** button, and offer count stepper.

---

## 🛠️ Category Hierarchy Generator Tool & Verification

The repository includes an automated category map crawler and verification tools in `tools/`:

- **Crawler & Injector**: [`tools/generate_category_map.py`](file:///home/tazztone/_coding/scripts/userscripts/toppreise/tools/generate_category_map.py)
  - Crawls taxonomy structure directly from Toppreise and automatically injects updated `CATEGORY_LOOKUP` into `toppreise.user.js`.
- **Verification Tool**: [`tools/verify_category_map.py`](file:///home/tazztone/_coding/scripts/userscripts/toppreise/tools/verify_category_map.py)
  - Reads `CATEGORY_LOOKUP` directly from `toppreise.user.js` and benchmarks mapping coverage against standard site subcategories.

### Running Tools
```bash
# Crawl site & inject category lookup map into userscript
python3 userscripts/toppreise/tools/generate_category_map.py

# Verify category lookup accuracy directly from userscript
python3 userscripts/toppreise/tools/verify_category_map.py
```

---

## 🚀 Automatic Updates (`@updateURL`)

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

---

## 🧪 Development Checks

```bash
node --check toppreise.user.js
pytest tests/test_userscript.py
```
