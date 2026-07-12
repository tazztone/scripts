# Toppreise Store Best Price Highlight & Filter - Research Log

This document details the selectors and extraction logic for the store-based price comparison on Toppreise.ch search and listing pages.

## 1. Trigger & Target Elements

- **Active Store Filter**:
  - Selector: `.filters .f_remove_filter[data-target-type="df"]`
  - Extraction: The element contains the store name (e.g., `Media Markt`). If multiple stores are filtered, the script will match against any active store filter.
- **Product Card Container**:
  - Selector: `.Plugin_Product.mixedBrowsingList`
  - State Markers: We will apply class attributes to these product containers:
    - `tp-is-cheapest`: The filtered store has the best price (within margin).
    - `tp-not-cheapest`: The filtered store sells it, but is more expensive than the best price (beyond margin).
    - `tp-no-store-offer`: The filtered store does not sell this product.

---

## 2. Element Selectors

Within each product card `.Plugin_Product.mixedBrowsingList`:

### Filtered Store Price Data
- **Store-specific price row container**: `.Plugin_DealerRelProdPriceInfo`
  - Store Name: `.Plugin_DealerRelProdPriceInfo .title`
  - Price (Excl. Shipping): `.Plugin_DealerRelProdPriceInfo .productPrice .Plugin_Price`
  - Price (Incl. Shipping): `.Plugin_DealerRelProdPriceInfo .shippingPrice .Plugin_Price`

### Overall Lowest Price Data
- **Lowest price wrapper**: `.price_information_product`
  - Price (Excl. Shipping): `.price_information_product .productPrice .Plugin_Price`
  - Price (Incl. Shipping): `.price_information_product .shippingPrice .Plugin_Price`

---

## 3. Price Parsing logic
Toppreise price text formats:
- Examples: `CHF 359.95`, `CHF 1'234.50`, `CHF 1,234.50`.
- Processing:
  1. Strip out non-numeric characters except digits, comma `,`, dot `.`, and single quote `'`.
  2. Remove single quotes `'` (thousands separators).
  3. Replace commas `,` with dots `.` if any.
  4. Parse as Float.

---

## 4. Lifecycle & Dynamic Updates

Toppreise.ch updates listings via AJAX when checkboxes are clicked or sorting is modified.
- **MutationObserver**: Monitor the document tree (specifically `.pageContent` or `body`) for changes.
- **Debounce**: Throttle execution by 150-250ms to prevent thrashing during rapid DOM updates.
- **Reset**: If no store filter is active, strip all highlighting/hiding classes so the page renders normally.
