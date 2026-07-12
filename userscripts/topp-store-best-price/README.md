# Toppreise.ch Store Best Price Highlighter & Filter

Userscript that highlights or filters products on Toppreise.ch based on whether a filtered store currently offers the cheapest price (or within a customizable margin %).

![Toppreise Store Best Price Highlighter](Best%20Price%20Highlighter%20Filter.webp)

## 🚀 Installation

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT**](https://github.com/tazztone/scripts/raw/refs/heads/main/userscripts/topp-store-best-price/topp-store-best-price.user.js)
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
Edit the `CONFIG` block at the top of the script to customize settings:

| Key | Default | Description |
| :--- | :--- | :--- |
| `MODE` | `'dim'` | Action for non-cheapest products. Choose `'dim'` (reduce opacity), `'hide'` (remove from display), or `'highlight-only'` (only show badge on cheapest). |
| `MARGIN_PERCENT` | `0.0` | Margin percentage to count as cheapest (e.g. `0.0` means absolute cheapest, `3.0` means within 3% of the lowest price). |
| `DIM_OPACITY` | `0.25` | Opacity of non-cheapest products when `MODE` is set to `'dim'`. |
| `USE_SHIPPING_PRICE` | `true` | Compare price including shipping. Set `false` to compare base product prices excluding shipping. |
| `OBSERVER_DEBOUNCE_MS`| `200` | Safety debounce time to prevent layout thrashing on dynamic updates. |
