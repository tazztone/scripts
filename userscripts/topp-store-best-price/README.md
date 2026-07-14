# Toppreise.ch Store Best Price Highlighter & Filter

Userscript that highlights or filters products on Toppreise.ch based on whether a filtered store currently offers the cheapest price (or within a customizable margin %).

![Toppreise Store Best Price Highlighter](Best%20Price%20Highlighter%20Filter.webp)

## 🚀 Installation

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT**](https://github.com/tazztone/scripts/raw/refs/heads/main/userscripts/topp-store-best-price/topp-store-best-price.user.js?v=0.3.0)
*(Requires Violentmonkey / Tampermonkey)*

## Logic
When you filter a search page or product listing by a dealer/store (e.g. `Anbieter: Media Markt`):
1. The script automatically detects the filtered store name from the active filters.
2. It parses each product card to find the store-specific price.
3. Compares the store's price with the best price of the item.
4. Highlights the product with a beautiful emerald green border and a "Best Price" badge if the store is the cheapest.
5. Dims (or completely hides) products where the store is not the cheapest.

If no store filter is active, the script stays inactive and the page renders normally.

## Configuration

You can configure the script directly on Toppreise.ch! A small floating **gear button** appears in the bottom-right corner of the window. Clicking it opens a premium, glassmorphic settings panel where you can edit and apply configurations instantly:

- **Filter Mode**: `'dim'` (reduce opacity of non-cheapest listings), `'hide'` (remove from view), or `'highlight-only'` (only show badges).
- **Price Margin Tolerance (%)**: The percentage difference allowed for the store to still be considered "cheapest".
- **Non-Cheapest Opacity**: Opacity level for dimmed listings (5% to 95%).
- **Compare Shipping**: Compare prices including or excluding shipping costs.

These settings are saved persistently in your browser using the userscript manager's `GM_getValue` and `GM_setValue` APIs (with an automatic `localStorage` fallback).

For manual default settings, you can also edit the `DEFAULTS` block at the top of the userscript.
