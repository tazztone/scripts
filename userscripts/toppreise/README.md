# Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler

All-in-one userscript for Toppreise.ch that highlights best prices, excludes unwanted keywords, filters categories, filters/sorts by offer count, and automates price alarm creation.

## 🚀 Installation

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT**](https://github.com/tazztone/scripts/raw/refs/heads/main/userscripts/toppreise/toppreise.user.js?v=2.0.0)
*(Requires Violentmonkey / Tampermonkey)*

---

## ⚡ Features

1. **⚡ Compact Power Filter Bar**: Ultra-sleek, single-row (~38px height) top control bar prepended directly to `#FrameContent`. The Negative Keyword Filter input is always front and center, while category pills collapse into an on-demand drawer (`🏷️ Kategorien (N) ▼`).
2. **Händler Bestpreis Highlights**: Highlights products with an emerald green border & "Best Price" badge when a filtered store is the cheapest (or within custom margin %), while dimming/hiding non-cheapest products.
3. **Negativer Textfilter (Ausschluss)**: Exclude products containing specific unwanted keywords (e.g. `SAMSUNG, Hülle, Case, Refurbished, Gebraucht`) with word-boundary precision via the inline search bar or modal.
4. **Kategorien-Filter (Neue Toppreise & Suche)**: Product URL-First Category Extraction Engine (v2.0.0) parsing `/preisvergleich/CategorySlug/ProductTitle-p123` path segments with DOM dataset memoization for guaranteed 55+ category detection on `https://www.toppreise.ch/neue-toppreise/`.
5. **Angebote & Sortierung**: Filter out marketplace items with fewer than $N$ offers, plus optional client-side re-sorting by total offer count.
6. **Preisalarm Auto-Filler**: Automatically configures target price (e.g. 60% of current price) and 2-year duration upon clicking the price alarm bell icon, supporting Swiss currency formatting (`CHF 1'299.–`).
7. **Floating Quick-Control Pill Toolbar**: Bottom floating toolbar displaying hidden product count, 1-click reveal preview toggle, 1-click **Reset Filters** button, and offer count stepper.

---

## ⚙️ Configuration

Click the floating **gear button** in the bottom corner of Toppreise.ch to open the glassmorphic settings panel:

- **Händler Bestpreis**: Mode (`'dim'`, `'hide'`, `'highlight-only'`), margin %, opacity, shipping toggle.
- **Negativer Textfilter**: Comma-separated list of keywords to hide.
- **Kategorien-Filter**: Clickable pills to blacklist specific categories.
- **Angebote & Sortierung**: Set threshold for minimum dealer offers and sort order (`Meiste ⬇` / `Wenigste ⬆`).
- **Preisalarm Auto-Filler**: Target price percentage slider (default 60%), duration (default 2 years), auto-submit toggle.

All settings are saved persistently via `GM_setValue` / `GM_getValue`.
