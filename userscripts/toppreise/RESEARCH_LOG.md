# Toppreise.ch Suite - Research & Selector Reference

This document details the DOM selectors, event management, and filter logic for the unified Toppreise.ch Suite.

## 1. Core Target Elements & Selectors

### Product Listings & Filters
- **Active Store Filter**: `.filters .f_remove_filter[data-target-type="df"]`
- **Product Card Container**: `.Plugin_Product.mixedBrowsingList, .Plugin_Product`
- **State Marker Classes**:
  - `tp-is-cheapest`: Filtered store has best price (within margin %).
  - `tp-not-cheapest`: Filtered store sells item, but higher price.
  - `tp-no-store-offer`: Filtered store does not sell item.
  - `tp-negative-filtered`: Card hidden by negative keyword filter.
  - `tp-category-filtered`: Card hidden by category exclusion blacklist.
  - `tp-min-offers-filtered`: Card hidden due to fewer offers than `MIN_OFFERS`.
  - `tp-stock-filtered`: Card hidden due to failing delivery availability criteria.

### Price Alarm Automation
- **Modal Container**: `.Plugin_NewInfoMailForm` inside `.AbstractDialog.AbstractDialog_NewInfoMailFormDialog`
- **Present Price**: `.Plugin_NewInfoMailForm .shippingPrice .Plugin_Price`, fallback `.productPrice .Plugin_Price`
- **Target Price Input**: `input#f_NewInfoMailForm_priceFrom` or `input[name="im_nimf_pvf"]`
- **Duration Input**: Hidden input `input[name="im_nimf_du"]` + dropdown `li[data-value="730"]` (2 years)
- **GDPR Terms Checkbox**: `input#im_nimf_prtrm`
- **Submit Button**: `.Plugin_NewInfoMailForm input.f_submitbtn`
- **Dialog Close Button**: `.AbstractDialog_CloseButton`

---

## 2. UI Encapsulation & Shadow DOM Architecture

- **Root Container**: `<div id="tp-root">` attached to `document.body` with an open Shadow Root.
- **Top Layer Dialog**: `<dialog id="tp-settings-dialog" popover="auto">` renders inside the Top Layer, bypassing host site stacking contexts and `z-index` collisions.
- **Dual-Layer Style Separation**:
  - Host document styles (`.Plugin_Product.mixedBrowsingList.tp-is-cheapest`, `.tp-negative-filtered`, `#tp-suite-filter-bar`, `#tp-quick-toolbar`) live in a host `<style>` tag.
  - Settings dialog and FAB styles live strictly inside the `#tp-root` Shadow Root (`SHADOW_MODAL_STYLES`).
- **Toasts**: Non-blocking toast notifications render inside `#tp-toast-container` within the shadow root.

---

## 3. INP Protection & Asynchronous Chunked Batching

- `processListings()` processes product cards in chunked batches of 20 with `requestAnimationFrame` + `globalThis.scheduler?.yield()`.
- A monotonically increasing `listingRunId` sequence token cancels stale in-flight batches when users type into filter inputs or resize the window.
- Extracted metadata is cached on `card.dataset.tpCategory` and `card.dataset.tpOfferCount` to avoid repeated parsing during DOM mutations.

---

## 4. Reinstall-Proof 2-Layer Storage Architecture (v2.3.0)

- **Layer 1 (Extension Sandbox)**: `GM_setValue` / `GM_getValue` stores user settings inside Violentmonkey / Tampermonkey storage partition.
- **Layer 2 (Domain Storage Backup)**: `window.localStorage.setItem('tp_suite_v2_' + key, JSON.stringify(val))` stores a mirrored backup directly inside `toppreise.ch` domain storage.
- **Auto-Healing Recovery**: If `GM_getValue` returns `undefined` (e.g. after a clean script uninstall/reinstall), `_getValue` reads `tp_suite_v2_[key]` from `localStorage` and automatically re-seeds `GM_setValue` so settings are preserved indefinitely across script re-installations.

---

## 5. Architectural Gotchas & Session Roadblocks

1. **Card Elements as Anchor Tags (`<a class="Plugin_Product">`)**:
   - *Gotcha*: On `neue-toppreise`, cards are `<a>` tags itself. Calling `card.querySelectorAll('a')` returns `0` elements because `querySelectorAll` only matches descendant children.
   - *Rule*: Always inspect `card.tagName === 'A'`, `card.closest('a[href]')`, and `card.querySelectorAll('a[href]')`.

2. **Absolute Positioned Icons vs Variable Emoji Width**:
   - *Gotcha*: `position: absolute; left: 10px` icons inside text inputs cause text overlap because emoji width varies across operating systems and browser fonts.
   - *Rule*: Prefer flexbox layout with inline label elements (`<span class="tp-input-label-inline">`) positioned *outside* the `<input>` box.

3. **Extension Storage Wipe on Reinstall**:
   - *Gotcha*: Tampermonkey/Violentmonkey purges `GM_getValue` data when a script is uninstalled or reinstalled clean.
   - *Rule*: Dual-sync state to `window.localStorage` on the target web domain (`toppreise.ch`). Domain `localStorage` is persistent across extension script uninstalls.

4. **Flat Pill Overflow at Scale**:
   - *Gotcha*: Rendering 55+ raw subcategory pills creates visual clutter and high cognitive load.
   - *Rule*: Map subcategories into high-level root groups (`Filme`, `Spielwaren`, `Computer & Zubehör`) with collapsible accordion pills.

5. **Transparent Overlays Blocking Page Clicks**:
   - *Gotcha*: Full-screen wrapper containers (`position: fixed; inset: 0`) without `pointer-events: none` capture pointer events across the viewport, preventing users from clicking underlying page elements.
   - *Rule*: Always set `pointer-events: none;` on fixed root wrappers/overlays, and explicitly set `pointer-events: auto;` only on interactive child elements (modals, toolbars, buttons).

6. **MutationObserver Infinite Re-render Pulsing Loop**:
   - *Gotcha*: Un-guarded DOM mutations inside a `MutationObserver` callback trigger the observer again, causing infinite re-render loops where UI elements flicker and pulse continuously.
   - *Rule*: Always guard DOM manipulations with element ID checks (`if (document.getElementById('tp-suite-filter-bar')) return;`) or `dataset.processed` flags to ensure idempotency and prevent self-observation loops.

8. **Top-Layer Dialog Popover Z-Index & Backdrop Trap**:
   - *Gotcha*: When a `<dialog popover="auto">` is open in the browser Top Layer (Shadow DOM), child popovers appended to `document.body` render in the standard document layer behind the modal backdrop and are unclickable or invisible.
   - *Rule*: Pass `mountContainer` to popover controllers and mount popovers directly inside the dialog element when open inside a Top-Layer modal.

9. **Event Interception on Anchor Product Cards**:
   - *Gotcha*: Action buttons (like 1-click quick-block) injected onto `<a class="Plugin_Product">` cards will navigate the browser to the product URL if the click event bubbles.
   - *Rule*: Always invoke `e.preventDefault()`, `e.stopPropagation()`, and `e.stopImmediatePropagation()` inside card action button handlers.

10. **Storage I/O Micro-Optimization during Batch DOM Processing**:
    - *Gotcha*: Writing dynamic category mappings to `GM_setValue` / `localStorage` per card during DOM loops causes repeated synchronous I/O.
    - *Rule*: Buffer updates in an in-memory map during the chunked batch run and flush with `flushDynamicMap()` once at the end of `processListings()`.

11. **Scoped Feed Action Buttons (Neue Toppreise Only)**:
    - *Gotcha*: Quick-block category buttons on search result pages or specific category catalog pages clutter targeted user browsing where category-blocking is unnecessary.
    - *Rule*: Restrict `.tp-card-quick-block` strictly to Neue Toppreise feed pages (`isNeueToppreisePage()`), and actively clean up lingering buttons on regular catalog/search listings.

12. **Safe Placement Anchor (Avoid `.f_filter_plugin` and Site Header)**:
    - *Gotcha*: Anchoring the filter bar inside `.f_filter_plugin` or `.filters` caused Toppreise's native `standard.js` AJAX replacement and jQuery event capture to intercept clicks and wipe the bar on filter changes. Anchoring inside the site header placed it beneath backdrop overlays.
    - *Rule*: Always mount `#tp-suite-filter-bar` as a direct child of `#FrameContent` / `.pageContent` directly preceding the primary product browsing container (`#Page_List...`, `#Page_Browsing`, `.f_browsingListContainer`, `#Plugin_MixedBrowsingList`), and strictly verify `parentElement` is not an unsafe container.

---

## 6. Comprehensive Category Taxonomy & Resolution Engine (v2.8.12)

### 1. Site Taxonomy Structure & URL Patterns
`Toppreise.ch` structures its catalog under **23 primary root category slugs** (mapped into 14–17 canonical display groups such as *Spielwaren*, *Computer & Zubehör*, *Haushalt & Küche*, *Drogerie*, *HiFi & Audio*, etc.).

Subcategories appear in two distinct patterns across the site:
- **Navigation Category Links (`/produktsuche/<Root>/<Subcat>-cNNN`)**: High-level and mid-level category nodes (e.g. `Spielwaren/Bau-Konstruktionsspielzeug-c2404`).
- **Product URL Category Paths (`/preisvergleich/<SubcatSlug>/<ProductTitle>-pNNN`)**: Leaf subcategories (e.g. `Lego-City`, `Heissluftfritteusen`, `Vollautomaten`, `USB-SpeicherSticks`, `AV-Receiver`) appear as the first path segment in product links. These leaf nodes are pagination-dependent (`?p=1..10`).

### 2. Crawl Tool & Yield (`tools/generate_category_map.py`)
- **Automated Depth & Pagination Crawler**: Crawls `/produktsuche/` pages and follows subcategory links up to depth 5, including paginated product lists (`?p=1..10`).
- **Crawl Metrics**: 1,194 pages crawled $\rightarrow$ **669 site subcategories** $\rightarrow$ **1,360 normalized lookup keys** (handling exact titles, URL slugs, space-separated forms, and German umlaut variants `ue` $\leftrightarrow$ `ü`, `ae` $\leftrightarrow$ `ä`, `oe` $\leftrightarrow$ `ö`).
- **Auto-Injection**: Injects `const CATEGORY_LOOKUP` into `toppreise.user.js`.

### 3. 6-Layer Category Resolution Pipeline (`resolveCategoryPath`)
1. **Layer 1: On-Card Product URL Root Slug Extraction**: Reads `/preisvergleich/<RootSlug>/...` or `/produktsuche/<RootSlug>/...` directly from card links (**100% authoritative**).
2. **Layer 2: Site-Crawled `CATEGORY_LOOKUP`**: Matches 1,360 auto-generated lookup keys.
3. **Layer 3: Dynamic Storage `DYNAMIC_CAT_MAP`**: Saved in `GM_setValue` / `localStorage` to learn categories at runtime as user browses.
4. **Layer 4: Brand & Keyword Rules (`BRAND_RULES`)**: Domain regex matching for brands (*CaDA*, *Playmobil*, *Cobi*, *Schleich*, etc.).
5. **Layer 5: Word-Prefix Token Fallback**: Right-to-left word trimming (`Lego Star Wars` $\rightarrow$ `Lego` $\rightarrow$ `Spielwaren`).
6. **Layer 6: DOM Breadcrumbs**: Fallback to page `.breadcrumb` links.

---

## 7. Discount Heatmap Engine & Thermal Scaling (v2.10.0)

### 1. Target Selectors & Data Extraction
- **Discount Badge**: `.badge.badge-dif, .badge` with difference bracket classes (`m_1_25`, `m_26_50`, `m_51_75`, `m_76_100`).
- **Inner Markup**: `<div class="text">Differenz</div> <p>-XX%</p>`.
- **Extraction Function**: `extractCardDiscount(card)` caches parsed percentage ($0 \le D \le 100$) onto `card.dataset.tpDiscount`.

### 2. Thermal Color Keypoints & Interpolation
- **5 Anchor Stops**:
  - `0%` (Cold Navy): Base `[15, 23, 42]`, Accent `[25, 45, 80]`, Border `[59, 130, 246, 0.25]`
  - `25%` (Cool Teal): Base `[13, 28, 38]`, Accent `[14, 75, 85]`, Border `[20, 184, 166, 0.35]`
  - `50%` (Warm Amber): Base `[35, 26, 16]`, Accent `[140, 85, 15]`, Border `[245, 158, 11, 0.50]`
  - `75%` (Hot Orange-Red): Base `[42, 18, 16]`, Accent `[195, 50, 18]`, Border `[249, 115, 22, 0.70]`
  - `100%` (Blazing Crimson): Base `[48, 10, 24]`, Accent `[225, 25, 65]`, Border `[244, 63, 94, 0.85]`
- **Power Curve Calibration**: $t = (D / 75)^{0.9}$ ensures real-world clearance discounts ($\ge 60\%$) reach peak fiery thermal intensity while preserving dark-theme typography contrast.
- **State Marker**: `.Plugin_Product.tp-heatmap-active` with CSS properties `--tp-heat-bg`, `--tp-heat-border`, and `--tp-heat-glow`.

