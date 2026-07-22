# Toppreise Power Filter & Best Price Enhancer - Research & Architecture Log

This document details the selectors, DOM extraction strategies, and filter logic for the Toppreise.ch Power Filter script.

## 1. Core Target Elements

- **Active Store Filter**: `.filters .f_remove_filter[data-target-type="df"]`
- **Product Card Container**: `.Plugin_Product.mixedBrowsingList, .Plugin_Product`
- **State Marker Classes**:
  - `tp-is-cheapest`: Filtered store has the best price (within margin).
  - `tp-not-cheapest`: Filtered store sells item, but higher price than lowest.
  - `tp-no-store-offer`: Filtered store does not sell item.
  - `tp-negative-filtered`: Card hidden by negative keyword filter.
  - `tp-category-filtered`: Card hidden by category exclusion blacklist.
  - `tp-min-offers-filtered`: Card hidden due to fewer offers than `MIN_OFFERS` threshold.
  - `tp-stock-filtered`: Card hidden due to failing delivery availability criteria.

---

## 2. Element Selectors & Extraction Rules

### Negative Text Filter
- Card Title: `.titleLink, .title`
- Specs / Description: `.specs, .description`
- Logic: Case-insensitive substring match against comma/newline separated negative terms array.

### Category Filter
- Selector: `card.querySelector('a[href*="/katalog/"], .categoryLink, .breadcrumb a, .category')`
- Logic: Dynamic scanner populates `pageCategories` Set. Cards matching `EXCLUDED_CATEGORIES` array are hidden via CSS `.tp-category-filtered`.

### Offer Count Extraction
- Regex Extraction: `card.textContent.match(/(\d+)\s*(?:Angebote|Angebot)/i)`
- Fallback: `card.querySelectorAll('.Plugin_DealerRelProdPriceInfo').length`
- Re-sorting: Parent DOM container node re-appends sorted card element array when `SORT_BY_OFFERS` is active (`'desc'` or `'asc'`).

### Availability / Stock Filter
- Selectors: `.availability`, `.stock`, `.delivery`, `.stockStatus`, `[title*="lager"]`, `[title*="lieferbar"]`, `[title*="Lieferzeit"]`
- Modes:
  - `'all'`: No stock restrictions.
  - `'in-stock'`: Requires at least one dealer with a known delivery timeline (green/yellow indicator).
  - `'immediate-only'`: Requires at least one dealer with immediate stock ("ab Lager", "sofort", "1-2 Werktage").

---

## 3. Filter Summary Status Bar
- ID: `#tp-filter-summary-bar`
- Behavior: Computes counts of hidden cards per filter reason (`counts.neg`, `counts.cat`, `counts.min`, `counts.stock`).
- Feature: Quick toggle button adds/removes `.tp-reveal-filtered` on `document.body` to outline filtered products in dashed amber for previewing without clearing settings.
