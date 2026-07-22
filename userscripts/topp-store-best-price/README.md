# Toppreise.ch Power Filter & Best Price Enhancer

Userscript that highlights best prices, excludes unwanted keywords, filters categories, filters/sorts by offer count, and enforces delivery stock availability on Toppreise.ch.

![Toppreise Store Best Price Highlighter](Best%20Price%20Highlighter%20Filter.webp)

## 🚀 Installation

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT**](https://github.com/tazztone/scripts/raw/refs/heads/main/userscripts/topp-store-best-price/topp-store-best-price.user.js?v=0.4.0)
*(Requires Violentmonkey / Tampermonkey)*

## Features

1. **Händler Bestpreis Highlights**: When filtering by a dealer/store (e.g. `Anbieter: Media Markt`), detects the store's price and highlights cheapest items with an emerald green border & "Best Price" badge, while dimming or hiding non-cheapest products.
2. **Negativer Textfilter (Ausschluss)**: Exclude products containing unwanted keywords (e.g. `Hülle, Case, Refurbished, Gebraucht`) from title or spec text.
3. **Kategorien-Filter (Neue Toppreise)**: Dynamically scans categories on the page and provides interactive pills to permanently hide unwanted categories (e.g. *Handyzubehör*, *Parfum*).
4. **Angebote & Sortierung**: Filter out marketplace items with fewer than $N$ offers, plus optional client-side re-sorting by total offer count.
5. **Verfügbarkeits- & Lieferbarkeitsfilter**: Enforce stock delivery requirements (`[Alle]`, `[Lieferbar]`, `[Sofort ab Lager]`).
6. **Filter-Zähler Statusleiste**: Floating status summary bar displaying how many products were hidden and why, with a 1-click toggle to temporarily reveal filtered items.

## Configuration

Click the floating **gear button** in the bottom corner of Toppreise.ch to open the glassmorphic settings panel:

- **Filter Mode**: `'dim'` (reduce opacity of non-cheapest listings), `'hide'` (remove from view), or `'highlight-only'`.
- **Preis-Toleranz (%)**: Percentage difference allowed for the store to still be considered "cheapest".
- **Negativer Textfilter**: Comma-separated list of keywords to hide.
- **Kategorien-Filter**: Clickable pills to blacklist specific categories.
- **Mindestanzahl Angebote & Sortierung**: Set threshold for minimum dealer offers and sort order.
- **Verfügbarkeits-Filter**: Filter products by immediate stock or known delivery status.

Settings are saved persistently via `GM_setValue` / `GM_getValue` APIs.
