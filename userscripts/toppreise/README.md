# Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler

All-in-one userscript for Toppreise.ch that highlights best price offers, excludes unwanted negative keywords, provides 1-click inline category blocking with overview chips, sorts/filters by offer count, renders dynamic deal discount heatmaps, and automates price alarm creation.

![Toppreise.ch Suite: Features Walkthrough on neue-toppreise](Screenshot.webp)

## 🚀 Installation

Requires Violentmonkey (or a compatible userscript manager):
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
- [Chrome / Brave](https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT (v2.11.10)**](https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/toppreise/toppreise.user.js)

---

## ⚡ Features

1. **🔥 Rabatt-Heatmap (100% Heiß bis 0% Kalt)**: Dynamische thermische Hintergrund-Verläufe auf allen Produktkarten anhand der Rabatthöhe (z. B. auf `neue-toppreise`). Realistische Deal-Kalibrierung: 0–15% Kaltes Mitternachtsblau ❄️ $\rightarrow$ 35% Warmes Bernstein ⚡ $\rightarrow$ 70%+ Vulkanisches Rubinrot 🔥 mit leuchtenden Akzenten. 1-Klick-Toggle direkt in der oberen Filterleiste.
2. **🚫 1-Click Product Card Category Quick-Block & Toast Undo**: Direct "🚫 [Kategorie]" action button overlay on every product card on `neue-toppreise`. Clicking instantly hides the product's category from the feed and displays a glassmorphic toast notification with a **"Rückgängig"** (Undo) action button.
3. **📋 Blocked Categories Overview Chips**: Top filter bar shows a compact overview row `🚫 Ausgeblendet (N)` with dismissable chips (`[ 💻 Externe SSD ✕ ]`, `[ 🧸 Lego ✕ ]`) and an *Alle freigeben* button whenever categories are blocked.
4. **📁 Intelligent Category Taxonomy Resolution**: Multi-level resolution algorithm with card URL path parsing (`/preisvergleich/<RootSlug>/...`), domain brand rules (*Lego*, *Playmobil*, *Cobi*, *Schleich*, *Barbie*, *Hot Wheels*, *CaDA*, *Amiibo* $\rightarrow$ 🧸 **Spielwaren** / 🎮 **Videogames**), and keyword fallback routing.
5. **🛡️ Encapsulated Shadow DOM Settings Modal (`#tp-root`)**: Floating action button (FAB) and settings dialog are isolated inside an open Shadow Root, elevated to the browser Top Layer via native `<dialog>` (`showModal()`) to bypass host site z-index and CSS reset collisions.
6. **Händler Bestpreis Highlights**: Highlights products with an emerald green border & "Best Price" badge when a filtered store is the cheapest (or within custom margin %), while dimming/hiding non-cheapest products.
7. **Negativer Textfilter (Ausschluss)**: Exclude products containing specific unwanted keywords (e.g. `SAMSUNG, Hülle, Case, Refurbished, Gebraucht`) with word-boundary precision via the inline search bar or modal.
8. **Angebote & Rabatt-Sortierung**: Filter out marketplace items with fewer than $N$ offers, plus optional client-side re-sorting by total offer count or highest discount (`% Rabatt ⬇`).
9. **Preisalarm Auto-Filler**: Automatically configures target price (e.g. 60% of current price) and 2-year duration upon clicking the price alarm bell icon, supporting Swiss currency formatting (`CHF 1'299.–`).
10. **⚡ Unified Top Filter Bar**: Consolidated single-surface toolbar containing hidden count indicator `🚫 N`, reveal preview toggle `👁️`, `🔥 Heatmap` toggle, Min-Offers stepper `[-] 0 [+]`, and `🔄 Reset` button.

---

## 🚀 Automatic Updates (`@updateURL`)

The script includes embedded `@updateURL` and `@downloadURL` metadata headers. Violentmonkey and Tampermonkey will check GitHub automatically in the background and keep your installed userscript updated without requiring manual reinstalls.

---

## ⚙️ Configuration & Persistence

Click the floating **gear button** in the bottom corner of Toppreise.ch to open the glassmorphic settings panel:

- **Händler Bestpreis**: Mode (`'dim'`, `'hide'`, `'highlight-only'`), margin %, opacity, shipping toggle.
- **Rabatt-Heatmap**: Toggle on/off, intensity slider (20% – 100%).
- **Negativer Textfilter**: Comma-separated list of keywords to hide.
- **Angebote & Sortierung**: Set threshold for minimum dealer offers and sort order (`Meiste ⬇`, `Wenigste ⬆`, `% Rabatt ⬇`).
- **Preisalarm Auto-Filler**: Target price percentage slider (default 60%), duration (default 2 years), auto-submit toggle.

> [!NOTE]
> All settings, excluded categories, and negative terms are saved **permanently** with a 2-layer storage architecture (`GM_setValue` / `GM_getValue` with domain `localStorage` auto-healing backup) that survives userscript reinstalls.

---

## 🧪 Development Checks

```bash
node --check userscripts/toppreise/toppreise.user.js
pytest userscripts/toppreise/tests
```
