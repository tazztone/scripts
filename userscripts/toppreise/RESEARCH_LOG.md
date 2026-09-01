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
- **Top Layer Dialog**: `<dialog id="tp-settings-dialog">` renders inside the Top Layer via `showModal()`, bypassing host site stacking contexts and `z-index` collisions.
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

13. **Price Alarm Auto-Submit AJAX Lifecycle & Dialog Teardown**:
    - *Gotcha*: Synchronously clicking `.AbstractDialog_CloseButton` immediately after `input.f_submitbtn.click()` tears down the modal container (`AbstractDialog_hide()`) while Toppreise's AJAX POST request to `/plugins/infomails/NewInfoMailForm` is still in-flight, causing the request to abort and raising *"Es ist ein unerwarteter Fehler aufgetreten. Bitte versuchen Sie es noch einmal."* Furthermore, submitting in 0ms raced with Toppreise's internal duration dropdown and input validator event binding.
    - *Rule*: Always stage auto-submit asynchronously with a 300ms pre-submit settle delay and an 800ms post-submit grace period before closing the modal dialog container.

14. **Deal-Feed-Only Features on Non-Feed Pages**:
    - *Gotcha*: Heatmap, batch deal-check, Tiefstpreis toggle, and threshold selector are rendered on category/search pages where no discount badges (`.badge-dif`) exist, creating dead UI clutter with permanently-zero counters. Furthermore, when `cards.length === 0` on product detail pages (`/preisvergleich/...-pNNNNN`), the filter bar was inadvertently injected above the dealer table.
15. **Pricechart HTML Grid Structure vs `Element.closest()` Traversal**:
    - *Gotcha*: On real Toppreise pricechart endpoints, title headings carry grid classes directly (`<div class="title col-12">Tiefstpreis</div>`). Calling `found.closest('.col-12, .col-4, ...')` evaluates `closest()` on the element itself, matching `.col-12` and returning the title `<div>` (which contains only text, no price).
    - *Rule*: Always inspect adjacent element containers (`found.nextElementSibling?.querySelector('.Plugin_Price')`) or scope parent traversal to `.col-4, .col-md-3, .col-md, [class*="col-"]:not(.title)` and include regex fallbacks.

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
- **5 High-Saturation Anchor Stops**:
  - `0% – 10%` (Vibrant Cobalt/Ice Blue): Base `[18, 48, 88]`, Accent `[28, 92, 175]`, Border `[56, 140, 248, 0.70]`
  - `15% – 20%` (Vibrant Cyan/Teal): Base `[12, 58, 64]`, Accent `[16, 130, 125]`, Border `[20, 210, 190, 0.75]`
  - `28% – 35%` (Warm Golden Amber): Base `[68, 48, 10]`, Accent `[180, 118, 15]`, Border `[245, 175, 20, 0.80]`
  - `40% – 48%` (Fiery Flame Orange): Base `[85, 28, 12]`, Accent `[228, 76, 18]`, Border `[251, 115, 36, 0.88]`
  - `50% – 100%` (Blazing Volcanic Ruby Crimson): Base `[98, 14, 32]`, Accent `[238, 25, 65]`, Border `[244, 63, 94, 0.95]`
- **Feed-Calibrated Curve**: Dynamic piecewise interpolation anchored to real-world Toppreise feed discount ranges (10% cold base $\rightarrow$ 35% warm amber $\rightarrow$ 50%+ blazing flame/crimson) with high saturation and luminous badge/border accents.
- **State Marker**: `.Plugin_Product.tp-heatmap-active` with CSS properties `--tp-heat-bg`, `--tp-heat-border`, and `--tp-heat-glow`.

---

## 8. Price History, All-Time Low (Tiefstpreis) & Real Deal Engine

### 1. Product Page DOM Elements & Selectors
- **Preischart Button Wrapper**: `.Plugin_PriceChartButton` (parent container in the product header row).
- **Dialog Trigger Anchor/Div**: `.f_showPriceChartDialog` (contains `data-ajax-form-url="/plugins/product/pricechart?p_pc_pid=..."` and `data-trend-ajax-form-url="/plugins/product/pricecharttrend?p_pct_pid=..."`).
- **Thumbnail Chart Preview**: `.Plugin_PriceChart_Preview` (child `.highchartContainer.f_scrollToFullChart`, renders SVG/Highcharts).
- **Product ID Attribute**: Card element `data-entity-id="NNNNNN"` or URL match `/-p(\d+)/`.

### 2. Dual-Endpoint Architecture for Price History

#### Endpoint A: Direct Dialog HTML (`GET /plugins/product/pricechart?p_pc_pid={productId}`)
- **Method**: `GET`
- **Required Header**: `X-Requested-With: XMLHttpRequest`
- **Response**: Pre-rendered modal HTML containing calculated aggregates without needing client-side time-series reduction:
  - **Tiefstpreis (All-Time Low)**: Pre-calculated value inside `.PriceChartLegend` following `<div class="title">Tiefstpreis</div>` $\rightarrow$ `.Plugin_Price` (both shipping-inclusive and product-only).
  - **Aktueller Toppreis**: Pre-calculated value following `<div class="title">aktueller Toppreis</div>`.
  - **Höchstpreis (All-Time High)**: Pre-calculated value following `<div class="title">Höchstpreis</div>`.
  - **Time Range Windows**: `.PriceChartTabList .f_tabItem` with `data-minTimeRange` millisecond timestamps for 1M, 3M, 6M, 1Y, and All-Time.

#### Endpoint B: Raw Time-Series JSON (`POST /plugins/product/pricechart`)
- **Method**: `POST`
- **Content-Type**: `application/x-www-form-urlencoded; charset=UTF-8`
- **Required Header**: `X-Requested-With: XMLHttpRequest`, `Accept: application/json, text/javascript, */*; q=0.01`
- **Form Body**: `pcspagdpi={productId}&pcspagdfdt=0000-00-00&pcspagdtd=&p_pc_ch=&lang=de`
- **Response Payload**: 2D JSON array `[ [ [timestamp_ms, price_product], ... ], [ [timestamp_ms, price_shipping], ... ] ]`:
  - `data[0]`: Chronological `[timestamp_ms, price]` array for Produktpreis (excl. shipping).
  - `data[1]`: Chronological `[timestamp_ms, price]` array for Versandpreis (incl. shipping).
- **Time-Series Analysis Engine (`analyzePriceTimeSeries`)**:
  - **Previous Low (Bisheriger Tiefstpreis)**: Looks backwards from the current price drop window to find the prior historical minimum $P_{\text{prev\_low}}$.
  - **Real Discount vs Previous Low**: $\frac{P_{\text{prev\_low}} - P_{\text{curr}}}{P_{\text{prev\_low}}} \times 100\%$ (savings compared to prior all-time record).
  - **Real Discount vs Baseline/Average**: $\frac{P_{\text{avg}} - P_{\text{curr}}}{P_{\text{avg}}} \times 100\%$ (realistic savings vs typical street price).
- **Sparkline Integration (v2.15.0)**:
  - Single fast POST fetch (~50ms) extracts both time-series and all statistical aggregates in 1 request.
  - Cached in `localStorage` under `tp_hist_v1_{productId}`.
  - Inline SVG polyline rendering (60x18px) with color encoding: Emerald `#10b981` (new low / trending down) vs Rose `#ef4444` (trending up).

### 3. Real Deal vs Feed-Diff Discrepancy & Validation Logic
- **Feed Badge Discrepancy**: The `-XX%` badge on `/neue-toppreise` (`.badge-dif`) represents only the immediate price drop compared to the previous or baseline listing. It frequently tags non-bestpreise as massive discounts even when earlier historical prices were far lower.
- **Validation Formulas**:
  - **Is All-Time Bestpreis**: $\text{CurrentPrice} \le \text{Tiefstpreis} \times 1.01$
  - **Is New Record Low**: $P_{\text{curr}} < P_{\text{prev\_low}} \times 0.99$ (renders subline: `Bisher: CHF XX.XX (-YY%)`)
  - **Real Deal Discount % (vs Historical High)**: $\frac{\text{Höchstpreis} - \text{CurrentPrice}}{\text{Höchstpreis}} \times 100$
  - **Inflation Gap % (vs Historical Low)**: $\frac{\text{CurrentPrice} - \text{Tiefstpreis}}{\text{Tiefstpreis}} \times 100$
- **Caching & Rate-Limiting Strategy**:
  - Valid price stats cached in `localStorage` under `tp_hist_v1_{productId}` with a 48-hour TTL.
  - Negative cache (`{ unavailable: true }`) stored for 2 hours (bypassed on manual single-click).
  - LRU/cap pruning maintaining max 300 cached entries.
  - Query on-demand via native `.badge-dif` circle badge click (`🔍`) or user-initiated batch check.
  - Paced batch checks with 250–350ms jittered delay between items and automatic exponential backoff retry on transient 429/503 responses.
  - Multi-language label resolution (DE, FR, IT, EN).
- **Consolidated Differenz Badge UI Architecture**:
  - **Unchecked**: Retains original `-XX%` with subtle `.tp-badge-loupe-icon` (`🔍`) and hover scale.
  - **Loading**: In-place pulse animation with `⏳` spinner.
  - **All-Time Low**: Retains discount value with pulsing emerald halo ring (`#10b981`). For new record lows, subline displays `Bisher: CHF XX.XX (-YY%)`.
  - **Non-Bestpreis / Fake Deal**: Morphs to amber alert gradient with bold `+XX%` markup and shrunken struck-through `<s>-YY%</s>` fake discount, plus discreet `Tiefstpreis: CHF XX.XX` line under the price.

---

## 9. "Neue Bestpreise" Curated Feed Mode & Continuous Deal-Score (v2.16.2)

### 1. Architectural Concept
"Neue Bestpreise" turns `/neue-toppreise` into a genuine deal feed by filtering out unverified and non-bestpreis listings, mapping continuous real historical discounts directly onto the thermal heatmap, and auto-scanning uncached products with priority ordering.

### 2. Continuous Weighted Real Deal-Score Model
Instead of discrete artificial tier buckets, every qualifying all-time low product receives a continuous **Deal-Score %** ($S_{\text{deal}}$):

$$\text{Score} = \max\left(0, \text{round}\left((1 - W) \times D_{\text{median}} + W \times D_{\text{record}}\right)\right)$$

- **$D_{\text{median}}$ (Everyday Savings)**: Discount vs historical median price $\frac{P_{\text{median}} - P_{\text{curr}}}{P_{\text{median}}} \times 100$.
- **$D_{\text{record}}$ (Record-Breaking Margin)**: Discount vs previous all-time low $\frac{P_{\text{prev\_low}} - P_{\text{curr}}}{P_{\text{prev\_low}}} \times 100$ (or $0\%$ if matching existing record).
- **Weight $W$**: User-configurable via settings slider (default $0.50$ = 50% Median / 50% Neuer Rekord).
- **Qualification Gate**: Products must be at/below all-time low ($P_{\text{curr}} \le P_{\text{low}} \times 1.01$), have $\ge 2\%$ historical variance, and have $\ge 5$ data points. Non-qualifiers are hidden (`.tp-bestpreise-hidden`).

### 3. Integrated Thermal Heatmap & Visual Hierarchy
- **Card Thermal Background**: The computed Deal-Score directly drives `getHeatmapStyles(Score, ...)` on the card (5–15% cool cyan $\rightarrow$ 20–30% warm amber $\rightarrow$ 35%+ fiery red).
- **Circle Badge (`.badge-dif`)**:
  - Displays `Real Deal` and `-${Score}%` in clean, crisp typography.
  - Border/Halo: Pulsing gold halo (`.tp-deal-new-record`) if breaking a record, pulsing emerald halo (`.tp-deal-alltime-low`) if matching an all-time low.
  - Hover Tooltip: Full breakdown with `Ø-Rabatt: ${D_median}%` and `Rekord-Marge: ${D_record}%`.
- **Price Subline**:
  - New Record: `Bisher: CHF XX.XX (-YY%)` in emerald below the price.
  - Matching Low: `Ø-Preis: CHF XX.XX (-YY%)`.
- **Feed Sorting**: Pure continuous descending sort by Deal-Score ($S_{\text{deal}} \downarrow$).

### 4. Paced Auto-Scan Engine (`runBestpreiseScan`)
- **Pacing**: 200ms fixed delay between sequential requests.
- **Priority**: Sorts uncached queue by highest feed discount first ($D_{\text{feed}}$ descending) so the strongest deals surface immediately during streaming re-renders.
- **Cancellation**: Disabling Bestpreise mode sets `bestpreiseScanCancel = true` to abort running requests.

### 5. UI Controls & Synergy
- **Filter Bar Toggle**: `💎 Neue Bestpreise` toggle in `#tp-suite-filter-bar` with live scan counter (`⏳ Bestpreise (12/47)` $\rightarrow$ `💎 Bestpreise (23 Deals)`).
- **Redundant Control Mitigation**: Disables `🌟 Nur Tiefstpreise` and `🔍 Check Deals` with tooltips while Bestpreise mode is active to prevent user confusion.
- **Settings Modal Integration**: Managed under Section 6 with toggle and dynamic weight balance slider (`0%` 100% Median $\leftrightarrow$ `100%` 100% Neuer Rekord).
- **Empty State**: Dedicated empty state with one-click disable button when 0 items on a page qualify.

---

## 10. Statistical Refinements & Feed Stability Engine (v2.17.0)

### 1. Root-Cause Analysis: The "Disappearing / Stuck Hidden" Feed Bug
- **Blind Exclusion of Unscanned Items**: Previously, entering Bestpreise mode added `.tp-bestpreise-hidden` (`display: none !important`) to all unscanned cards immediately before network requests commenced. Since ~90% of listings on `/neue-toppreise` are regular retailer price drops rather than all-time lows, the entire feed vanished into a blank screen.
- **Grid Layout Detachment**: `applySorting()` directly appended `<a>` product elements to their common parent container, detaching them from responsive Bootstrap column wrappers (`.col-12, .col-md-4, .cell`). This broke CSS grid/flex structures and caused heights to collapse.
- **Order Loss**: Toggling Bestpreise mode off did not restore initial DOM order.
- **Solution**:
  1. *Non-Destructive Streaming UI*: Unscanned cards remain visible with a subtle loading spinner badge (`⏳ Prüfe...`), morphing into verified Real Deals as stats stream in.
  2. *Grid-Safe Sorting*: Sorting is applied to the outermost column wrapper (`card.closest('.col-*, .cell') || card`).
  3. *Natural Order Restoration*: Initial DOM order is recorded in `data-tp-initial-order` and cleanly restored on mode deactivation.

### 2. Multi-Pass Outlier Spike & Price Glitch Rejection (`sanitizeTimeSeries`)
- **Problem**: Marketplace vendor errors (e.g. CHF 15 phone case indexed under CHF 1'200 phone for a few hours) create artificial record lows that corrupt lifetime all-time low checks and cause real discounts to be rejected.
- **Algorithm**:
  - Baseline Median: Computes raw median $M_{\text{raw}}$ from all price points.
  - Candidate Outlier: Flags $(t_i, p_i)$ where $p_i < 0.35 \times M_{\text{raw}}$.
  - Duration & Surrounding Validation: Excludes candidate if drop duration $<48\text{h}$ with normal adjacent points ($p_{i-1}, p_{i+1} \ge 0.60 \times M_{\text{raw}}$), or if extreme single boundary point ($p_i < 0.25 \times M_{\text{raw}}$ and neighbor $\ge 0.70 \times M_{\text{raw}}$).
  - Clean History: Calculates $P_{\text{low}}$, $P_{\text{prev\_low}}$, and $P_{\text{median}}$ exclusively on $P_{\text{clean}}$.
  - Metadata: Stores `filteredOutliers` in stats object for tooltip transparency (`ℹ️ 1 Ausreisser ignoriert`).

### 3. Rolling Time-Horizon for Median ($D_{\text{median}}$)
- **Problem**: Multi-year-old products (e.g. GPUs, TVs) carry high launch MSRPs that artificially inflate the lifetime median price.
- **Configuration**: User can select Horizon in Section 6 settings:
  - `365 Tage (1 Jahr)` [Default]
  - `180 Tage (6 Monate)`
  - `90 Tage (3 Monate)`
  - `0 (Gesamte Historie / Lifetime)`
- **Adaptive Fallback**: If recent window contains $<3$ data points, seamlessly falls back to lifetime median.
- **Subline Formatting**: Displays contextual window label: `Ø-Preis (1J): CHF 460.00 (-12%)`.

### 4. Configurable Cache & Performance Management (v2.17.0)
- **Settings Modal Section 7 (`7. Cache & Performance`)**:
  - **Valid Data Cache TTL (`REAL_DEAL_CACHE_HOURS`)**: Configurable dropdown (24h, 48h [default], 72h, 7d, 14d).
  - **Negative Cache TTL (`NEGATIVE_CACHE_HOURS`)**: Configurable dropdown (1h, 2h [default], 6h, 12h, 24h).
  - **Live Storage Counter (`tp-cache-stats-label`)**: Displays real-time count of cached product entries (`Lokaler Cache: N Einträge`).
  - **1-Click Cache Wipe (`🗑️ Cache leeren`)**: Removes all `tp_hist_v1_*` entries from `localStorage`, refreshes listing badges, and confirms with a glassmorphic toast.






