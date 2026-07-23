# Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler

All-in-one userscript for Toppreise.ch that highlights best prices, excludes unwanted keywords, filters categories, filters/sorts by offer count, and automates price alarm creation.

## 🚀 Installation

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT**](https://github.com/tazztone/scripts/raw/refs/heads/main/userscripts/toppreise/toppreise.user.js?v=0.7.0)
*(Requires Violentmonkey / Tampermonkey)*

---

## ⚡ Features

1. **Händler Bestpreis Highlights**: Highlights products with an emerald green border & "Best Price" badge when a filtered store is the cheapest (or within custom margin %), while dimming/hiding non-cheapest products.
2. **Negativer Textfilter (Ausschluss)**: Exclude products containing specific unwanted keywords (e.g. `Hülle, Case, Refurbished, Gebraucht`) from title or spec text via the inline negative search bar or modal.
3. **Kategorien-Filter (Neue Toppreise & Suche)**: Dynamically scans page breadcrumbs, sidebar category trees, and product cards to provide interactive pills for permanently hiding unwanted categories.
4. **Angebote & Sortierung**: Filter out marketplace items with fewer than $N$ offers, plus optional client-side re-sorting by total offer count.
5. **Preisalarm Auto-Filler**: Automatically configures target price (e.g. 60% of current price) and 2-year duration upon clicking the price alarm bell icon, auto-submitting and closing the dialog cleanly.
6. **Floating Quick-Control Pill Toolbar**: Bottom floating toolbar displaying hidden product count, 1-click reveal preview toggle, and offer count stepper with hover tooltips.

---

## ⚙️ Configuration

Click the floating **gear button** in the bottom corner of Toppreise.ch to open the glassmorphic settings panel:

- **Händler Bestpreis**: Mode (`'dim'`, `'hide'`, `'highlight-only'`), margin %, opacity, shipping toggle.
- **Negativer Textfilter**: Comma-separated list of keywords to hide.
- **Kategorien-Filter**: Clickable pills to blacklist specific categories.
- **Angebote & Sortierung**: Set threshold for minimum dealer offers and sort order (`Meiste ⬇` / `Wenigste ⬆`).
- **Preisalarm Auto-Filler**: Target price percentage slider (default 60%), duration (default 2 years), auto-submit toggle.

All settings are saved persistently via `GM_setValue` / `GM_getValue`.
