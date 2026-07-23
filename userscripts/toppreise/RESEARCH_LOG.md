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

## 2. Event & Auto-Close Handling

When a price alarm bell icon is clicked:
1. Modal mounts dynamically into `#tmpAbstractDialogContainer`.
2. Script detects `.Plugin_NewInfoMailForm` and sets `dataset.tpAlarmProcessed = "true"`.
3. Target price is set and dispatches `input` and `change` events.
4. Terms checkbox is set `.checked = true`.
5. Submit button `.click()` fires AJAX request.
6. A 200ms polling loop checks `!document.contains(modalContainer)`. Once detached, the script invokes `closeButton.click()` to dismiss the wrapper dialog cleanly.

---

## 3. Category Link & URL Patterns (Neue Toppreise & Search)

- **Category Links in Product Cards (`a[href*="-c"]`)**:
  - Single-level: `/produktsuche/HiFi-Audio-c653`
  - Multi-level nested: `/produktsuche/Computer-Zubehoer/Notebooks-Tablets-eReader/Notebooks-c13`
  - Category extraction regex: `/\/produktsuche\/(?:.*\/)?([^\/-]+(?:-[^\/-]+)*)-c\d+/i`
- **Product Links with Category Subpath**:
  - Pattern: `/preisvergleich/Category/Subcategory/ProductTitle-p123456`
  - Product URL extraction regex: `/\/preisvergleich\/(.+)\/[^\/]+-p\d+/i`
- **Breadcrumb Fallback**: `.breadcrumb a:last-of-type, [class*="breadcrumb"] a:last-of-type`

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
