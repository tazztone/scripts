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
