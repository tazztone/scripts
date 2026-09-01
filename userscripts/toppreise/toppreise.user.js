// ==UserScript==
// @name         Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler
// @namespace    https://github.com/tazztone/scripts
// @version      2.16.2
// @description  All-in-one suite for Toppreise.ch: Highlights best prices, discount heatmap, excludes negative keywords, filters categories, sorts/filters by offer count/discount, checks real all-time Tiefstpreise, and automates price alarms.
// @author       tazztone
// @match        https://www.toppreise.ch/*
// @updateURL    https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/toppreise/toppreise.user.js
// @downloadURL  https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/toppreise/toppreise.user.js
// @run-at       document-idle
// @grant        GM_getValue
// @grant        GM_setValue
// @noframes
// ==/UserScript==

// ─── CONFIG DEFAULT VALUES ───────────────────────────────────────────────────
const DEFAULTS = {
  MODE: 'dim',
  MARGIN_PERCENT: 0.0,
  DIM_OPACITY: 0.25,
  USE_SHIPPING_PRICE: true,
  HEATMAP_ENABLED: true,
  HEATMAP_INTENSITY: 1.0,
  HEATMAP_CURVE: 'calibrated',
  REAL_DEAL_FILTER_ACTIVE: false,
  REAL_DEAL_MIN_DISCOUNT: 30,
  REAL_DEAL_CACHE_HOURS: 48,
  NEGATIVE_CACHE_HOURS: 2,
  BESTPREISE_MODE_ACTIVE: false,
  ENABLE_SPARKLINES: false,
  NEGATIVE_TERMS: '',
  EXCLUDED_CATEGORIES: [],
  MIN_OFFERS: 0,
  SORT_BY_OFFERS: 'none',
  ALARM_ENABLED: true,
  ALARM_TARGET_PERCENT: 0.60,
  ALARM_DURATION_DAYS: "730",
  ALARM_AUTO_SUBMIT: true,
  ALARM_SUBMIT_DELAY_MS: 300,
  ALARM_CLOSE_DELAY_MS: 800,
  OBSERVER_DEBOUNCE_MS: 200,
  DEBUG: true
};

// ─── STYLES ──────────────────────────────────────────────────────────────────
const STYLES = `
  /* ─── HEATMAP CARD STYLES & DARKREADER DYNAMIC COMPATIBILITY ─── */
  .tp-heatmap-active,
  .Plugin_Product.tp-heatmap-active,
  .mixedBrowsingListProduct.tp-heatmap-active,
  .tp-heatmap-active[data-darkreader-inline-bgcolor],
  .Plugin_Product.tp-heatmap-active[data-darkreader-inline-bgcolor],
  .mixedBrowsingListProduct.tp-heatmap-active[data-darkreader-inline-bgcolor],
  .tp-heatmap-active[data-darkreader-inline-bgimage],
  .Plugin_Product.tp-heatmap-active[data-darkreader-inline-bgimage],
  .mixedBrowsingListProduct.tp-heatmap-active[data-darkreader-inline-bgimage] {
    background: var(--tp-heat-bg) !important;
    background-color: transparent !important;
    background-image: var(--tp-heat-bg) !important;
    border: 1.5px solid var(--tp-heat-border) !important;
    border-color: var(--tp-heat-border) !important;
    box-shadow: var(--tp-heat-glow, 0 2px 8px rgba(0,0,0,0.25)) !important;
    transition: background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, transform 0.2s ease, filter 0.2s ease !important;
    --darkreader-inline-bgcolor: transparent !important;
    --darkreader-inline-bgimage: var(--tp-heat-bg) !important;
    --darkreader-inline-border: var(--tp-heat-border) !important;
    --darkreader-inline-border-top: var(--tp-heat-border) !important;
    --darkreader-inline-border-right: var(--tp-heat-border) !important;
    --darkreader-inline-border-bottom: var(--tp-heat-border) !important;
    --darkreader-inline-border-left: var(--tp-heat-border) !important;
  }
  .tp-heatmap-active:hover,
  .Plugin_Product.tp-heatmap-active:hover,
  .mixedBrowsingListProduct.tp-heatmap-active:hover {
    filter: brightness(1.15) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0,0,0,0.35), var(--tp-heat-glow, none) !important;
  }
  .tp-heatmap-active .badge.badge-dif,
  .Plugin_Product.tp-heatmap-active .badge.badge-dif {
    box-shadow: 0 2px 8px rgba(0,0,0,0.4), 0 0 10px var(--tp-heat-border) !important;
  }
  .tp-heatmap-active .product-name,
  .tp-heatmap-active .product-name[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .productDetails,
  .tp-heatmap-active .productDetails[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .price_information_product,
  .tp-heatmap-active .price_information_product[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .Plugin_PriceInformation,
  .tp-heatmap-active .Plugin_PriceInformation[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .f_product_info,
  .tp-heatmap-active .f_product_info[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .productDescription,
  .tp-heatmap-active .productDescription[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .productDetailsDescription,
  .tp-heatmap-active .productDetailsDescription[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .product-details,
  .tp-heatmap-active .product-details[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .f_product_container,
  .tp-heatmap-active .f_product_container[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .product-image,
  .tp-heatmap-active .product-image[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .productImage,
  .tp-heatmap-active .productImage[data-darkreader-inline-bgcolor],
  .tp-heatmap-active .image_container,
  .tp-heatmap-active .image_container[data-darkreader-inline-bgcolor] {
    background: transparent !important;
    background-color: transparent !important;
    --darkreader-inline-bgcolor: transparent !important;
    --darkreader-inline-bgimage: none !important;
  }
  .Plugin_Product.mixedBrowsingList.tp-is-cheapest,
  .Plugin_Product.mixedBrowsingList.tp-is-cheapest[data-darkreader-inline-border-top],
  .Plugin_Product.mixedBrowsingList.tp-is-cheapest[data-darkreader-inline-border-right],
  .Plugin_Product.mixedBrowsingList.tp-is-cheapest[data-darkreader-inline-border-bottom],
  .Plugin_Product.mixedBrowsingList.tp-is-cheapest[data-darkreader-inline-border-left] {
    border: 2px solid #10b981 !important;
    border-color: #10b981 !important;
    border-radius: 8px !important;
    position: relative !important;
    box-shadow: 0 4px 20px rgba(16,185,129,0.15) !important;
    transition: all 0.3s ease !important;
    --darkreader-inline-border: #10b981 !important;
    --darkreader-inline-border-top: #10b981 !important;
    --darkreader-inline-border-right: #10b981 !important;
    --darkreader-inline-border-bottom: #10b981 !important;
    --darkreader-inline-border-left: #10b981 !important;
  }
  .Plugin_Product.mixedBrowsingList.tp-is-cheapest.tp-heatmap-active {
    box-shadow: 0 4px 20px rgba(16,185,129,0.25), var(--tp-heat-glow, none) !important;
  }
  .tp-best-price-badge {
    position: absolute;
    top: 12px;
    right: 50px;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: #fff;
    font: 700 11px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    padding: 4px 10px;
    border-radius: 20px;
    text-transform: uppercase;
    z-index: 10;
    box-shadow: 0 2px 8px rgba(16,185,129,0.4);
    letter-spacing: 0.5px;
    pointer-events: none;
  }
  .tp-mode-dim .Plugin_Product.mixedBrowsingList.tp-not-cheapest,
  .tp-mode-dim .Plugin_Product.mixedBrowsingList.tp-no-store-offer {
    opacity: var(--tp-dim-opacity, 0.25) !important;
    filter: grayscale(40%) !important;
    transition: opacity 0.3s ease, filter 0.3s ease !important;
  }
  .tp-mode-dim .Plugin_Product.mixedBrowsingList.tp-not-cheapest:hover,
  .tp-mode-dim .Plugin_Product.mixedBrowsingList.tp-no-store-offer:hover {
    opacity: 0.6 !important;
    filter: grayscale(10%) !important;
  }
  .tp-mode-hide .Plugin_Product.mixedBrowsingList.tp-not-cheapest,
  .tp-mode-hide .Plugin_Product.mixedBrowsingList.tp-no-store-offer,
  .tp-negative-filtered, .tp-category-filtered, .tp-min-offers-filtered, .tp-non-bestpreis-filtered, .tp-bestpreise-hidden {
    display: none !important;
  }
  body.tp-reveal-filtered .tp-negative-filtered,
  body.tp-reveal-filtered .tp-category-filtered,
  body.tp-reveal-filtered .tp-min-offers-filtered,
  body.tp-reveal-filtered .tp-non-bestpreis-filtered,
  body.tp-reveal-filtered .tp-bestpreise-hidden {
    display: block !important;
    opacity: var(--tp-dim-opacity, 0.25) !important;
    filter: grayscale(40%) !important;
    outline: 2px dashed #f59e0b !important;
    outline-offset: -2px !important;
  }
  /* ─── REAL DEAL & ALLZEIT-TIEFSTPREIS STYLES ─── */
  .tp-real-deal-wrapper {
    margin-top: 4px !important;
    display: inline-flex !important;
    flex-direction: column !important;
    align-items: flex-end !important;
    gap: 3px !important;
    z-index: 25 !important;
    pointer-events: auto !important;
  }
  /* ─── NATIVE DIFFERENZ BADGE REAL DEAL INTEGRATION ─── */
  .badge.badge-dif.tp-deal-badge-interactive,
  .badge-dif.tp-deal-badge-interactive {
    cursor: pointer !important;
    user-select: none !important;
    touch-action: manipulation !important;
    transform-origin: center center !important;
    transition: transform 0.12s ease-out, box-shadow 0.12s ease-out, border-color 0.12s ease-out !important;
  }
  .badge.badge-dif.tp-deal-badge-interactive *,
  .badge-dif.tp-deal-badge-interactive * {
    pointer-events: none !important;
  }
  .badge.badge-dif.tp-deal-badge-interactive:hover,
  .badge-dif.tp-deal-badge-interactive:hover {
    transform: scale(1.08) !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.45) !important;
    z-index: 30 !important;
  }
  .badge.badge-dif.tp-deal-badge-interactive:active,
  .badge-dif.tp-deal-badge-interactive:active {
    transform: scale(0.95) !important;
  }
  .tp-badge-loupe-icon {
    position: absolute !important;
    bottom: -2px !important;
    right: -2px !important;
    font-size: 11px !important;
    line-height: 1 !important;
    filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.8)) !important;
    pointer-events: none !important;
    transition: transform 0.12s ease-out !important;
  }
  .badge.badge-dif.tp-deal-badge-interactive:hover .tp-badge-loupe-icon {
    transform: scale(1.15) rotate(-10deg) !important;
  }
  .badge.badge-dif.tp-deal-loading,
  .badge-dif.tp-deal-loading {
    cursor: wait !important;
    opacity: 0.85 !important;
    animation: tpPulse 1.2s infinite ease-in-out !important;
  }
  @keyframes tpPulse {
    0%, 100% { transform: scale(1); opacity: 0.85; }
    50% { transform: scale(1.06); opacity: 1; }
  }
  /* 3A: Verified New Record Low: Glowing Pulsing Golden Diamond Halo */
  .badge.badge-dif.tp-deal-new-record,
  .badge-dif.tp-deal-new-record {
    background: linear-gradient(135deg, #78350f 0%, #b45309 50%, #f59e0b 100%) !important;
    border-color: #fbbf24 !important;
    box-shadow: 0 0 0 2.5px #f59e0b, 0 0 18px rgba(245, 158, 11, 0.7) !important;
    animation: tpRecordPulse 2.4s infinite ease-in-out !important;
    color: #ffffff !important;
  }
  @keyframes tpRecordPulse {
    0%, 100% { box-shadow: 0 0 0 2.5px #f59e0b, 0 0 14px rgba(245, 158, 11, 0.55); }
    50% { box-shadow: 0 0 0 3.5px #fbbf24, 0 0 24px rgba(251, 191, 36, 0.8); }
  }
  /* 3B: Verified All-Time Low: Glowing Pulsing Emerald Halo */
  .badge.badge-dif.tp-deal-alltime-low,
  .badge-dif.tp-deal-alltime-low {
    box-shadow: 0 0 0 2.5px #10b981, 0 0 16px rgba(16, 185, 129, 0.75) !important;
    border-color: #10b981 !important;
    animation: tpHaloPulse 2.4s infinite ease-in-out !important;
  }
  @keyframes tpHaloPulse {
    0%, 100% { box-shadow: 0 0 0 2.5px #10b981, 0 0 14px rgba(16, 185, 129, 0.6); }
    50% { box-shadow: 0 0 0 3.5px #34d399, 0 0 22px rgba(52, 211, 153, 0.85); }
  }
  /* 2A: Verified Non-Tiefstpreis: Amber Alert Morph with Shrunken Strikethrough */
  .badge.badge-dif.tp-deal-not-low,
  .badge-dif.tp-deal-not-low {
    background: linear-gradient(135deg, #78350f 0%, #b45309 100%) !important;
    border: 1.5px solid #f59e0b !important;
    box-shadow: 0 0 12px rgba(245, 158, 11, 0.45) !important;
    color: #ffffff !important;
  }
  .badge.badge-dif.tp-deal-not-low.tp-is-severe-markup,
  .badge-dif.tp-deal-not-low.tp-is-severe-markup {
    background: linear-gradient(135deg, #881337 0%, #be123c 100%) !important;
    border-color: #f43f5e !important;
    box-shadow: 0 0 14px rgba(244, 63, 94, 0.55) !important;
  }
  .badge.badge-dif.tp-deal-not-low p.tp-markup-val {
    font-size: 13px !important;
    font-weight: 800 !important;
    margin: 0 !important;
    line-height: 1.1 !important;
    color: #ffffff !important;
  }
  .badge.badge-dif.tp-deal-not-low .tp-fake-discount {
    font-size: 9.5px !important;
    opacity: 0.75 !important;
    display: block !important;
    line-height: 1 !important;
    margin-top: 1px !important;
    color: #fde68a !important;
  }
  .tp-card-historical-price {
    font: 500 11px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    color: #94a3b8 !important;
    text-align: right !important;
    margin-top: 2px !important;
    white-space: nowrap !important;
    user-select: none !important;
    pointer-events: auto !important;
  }
  .tp-card-historical-price.tp-is-record-low {
    color: #34d399 !important;
    font-weight: 600 !important;
  }
  .tp-card-historical-price.tp-is-at-low {
    color: #10b981 !important;
  }
  .tp-card-historical-price.tp-is-markup {
    color: #fbbf24 !important;
  }
  .tp-sparkline-container {
    display: inline-flex !important;
    align-items: center !important;
    margin-top: 2px !important;
    vertical-align: middle !important;
  }
  .tp-sparkline {
    opacity: 0.85;
    transition: opacity 0.2s ease, transform 0.2s ease;
    overflow: visible;
  }
  .tp-sparkline:hover {
    opacity: 1;
    transform: scale(1.08);
  }
  .tp-bar-btn.tp-batch-active {
    background: rgba(245, 158, 11, 0.25) !important;
    border-color: rgba(245, 158, 11, 0.5) !important;
    color: #fbbf24 !important;
  }
  .tp-bar-btn.tp-bestpreise-active {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.35), rgba(245, 158, 11, 0.25)) !important;
    border-color: rgba(139, 92, 246, 0.6) !important;
    color: #e9d5ff !important;
    box-shadow: 0 0 10px rgba(139, 92, 246, 0.3) !important;
  }
  #tp-suite-filter-bar.tp-bestpreise-bar {
    border-color: rgba(139, 92, 246, 0.45) !important;
    box-shadow: 0 3px 10px rgba(0,0,0,0.2), 0 0 0 1px rgba(139, 92, 246, 0.2) !important;
  }
  .tp-bar-btn.tp-disabled {
    opacity: 0.45 !important;
    cursor: not-allowed !important;
  }
  .tp-threshold-wrapper {
    position: relative !important;
    display: inline-flex !important;
    align-items: center !important;
  }
  .tp-threshold-btn {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-left: none !important;
    color: #94a3b8 !important;
    padding: 5px 8px !important;
    border-radius: 0 8px 8px 0 !important;
    font: 600 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
  }
  .tp-threshold-btn:hover, .tp-threshold-btn.tp-open {
    color: #f8fafc !important;
    background: rgba(30, 41, 59, 0.9) !important;
  }
  .tp-threshold-popover {
    position: absolute !important;
    top: calc(100% + 4px) !important;
    left: 0 !important;
    background: rgba(15, 23, 42, 0.96) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 8px !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5) !important;
    padding: 4px !important;
    display: none;
    flex-direction: column !important;
    gap: 2px !important;
    z-index: 100000 !important;
    min-width: 84px !important;
  }
  .tp-threshold-popover.tp-show { display: flex !important; }
  .tp-threshold-option {
    background: transparent !important;
    border: none !important;
    color: #cbd5e1 !important;
    padding: 5px 10px !important;
    font: 600 11.5px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    border-radius: 5px !important;
    cursor: pointer !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
  }
  .tp-threshold-option:hover {
    background: rgba(59, 130, 246, 0.25) !important;
    color: #60a5fa !important;
  }
  .tp-threshold-option.tp-selected {
    background: #3b82f6 !important;
    color: #ffffff !important;
  }
  .tp-empty-state-notice {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 12px !important;
    background: rgba(30, 41, 59, 0.85) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px dashed rgba(255, 255, 255, 0.2) !important;
    border-radius: 12px !important;
    padding: 24px 20px !important;
    margin: 16px auto !important;
    width: 100% !important;
    box-sizing: border-box !important;
    color: #e2e8f0 !important;
    text-align: center !important;
    font: 500 13.5px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.3) !important;
  }
  .tp-empty-state-actions {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    justify-content: center !important;
  }
  .tp-empty-state-btn {
    background: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    color: #f1f5f9 !important;
    padding: 6px 12px !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
  }
  .tp-empty-state-btn:hover {
    background: #3b82f6 !important;
    border-color: #60a5fa !important;
    color: #ffffff !important;
  }
  .tp-detail-deal-badge {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    padding: 4px 10px !important;
    border-radius: 8px !important;
    font: 700 12.5px/1.3 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    vertical-align: middle !important;
    margin-left: 10px !important;
    user-select: none !important;
  }
  .tp-detail-deal-badge.tp-is-alltime-low {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.95) 0%, rgba(5, 150, 105, 0.95) 100%) !important;
    border: 1px solid #34d399 !important;
    color: #ffffff !important;
    box-shadow: 0 2px 10px rgba(16, 185, 129, 0.45) !important;
  }
  .tp-detail-deal-badge.tp-is-not-low {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.95) 0%, rgba(217, 119, 6, 0.95) 100%) !important;
    border: 1px solid #fbbf24 !important;
    color: #ffffff !important;
    box-shadow: 0 2px 10px rgba(245, 158, 11, 0.4) !important;
  }
  .tp-detail-deal-badge.tp-is-severe-markup {
    background: linear-gradient(135deg, rgba(225, 29, 72, 0.95) 0%, rgba(190, 18, 60, 0.95)) !important;
    border: 1px solid #f43f5e !important;
    color: #ffffff !important;
    box-shadow: 0 2px 10px rgba(225, 29, 72, 0.45) !important;
  }
  .tp-card-quick-block {
    position: absolute !important;
    bottom: 1px !important;
    left: 8px !important;
    background: rgba(15,23,42,0.92) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(244,63,94,0.5) !important;
    color: #fda4af !important;
    font: 600 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    padding: 3px 8px !important;
    border-radius: 6px !important;
    cursor: pointer !important;
    opacity: 0 !important;
    transition: all 0.2s ease !important;
    z-index: 9999 !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 4px !important;
    max-width: 160px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
  }
  .Plugin_Product:hover .tp-card-quick-block,
  .mixedBrowsingListProduct:hover .tp-card-quick-block { opacity: 1 !important; }
  .tp-card-quick-block:hover {
    background: #e11d48 !important;
    color: #fff !important;
    transform: scale(1.04) !important;
  }
  #tp-suite-filter-bar {
    margin: 8px auto 12px !important;
    width: 100% !important;
    box-sizing: border-box !important;
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    padding: 8px 12px !important;
    color: #f8fafc !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    box-shadow: 0 3px 10px rgba(0,0,0,0.2) !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
    z-index: 9990 !important;
    position: relative !important;
  }
  .tp-filter-main-row {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    flex-wrap: wrap !important;
  }
  .tp-filter-badge {
    font-size: 13px !important;
    font-weight: 700 !important;
    color: #10b981 !important;
    flex-shrink: 0 !important;
  }
  .tp-input-wrapper {
    flex: 1 1 200px !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    min-width: 0 !important;
  }
  .tp-input-label-inline {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #94a3b8 !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
  }
  .tp-input-field-box {
    flex: 1 !important;
    min-width: 0 !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
  }
  #tp-inline-negative-input {
    width: 100% !important;
    background: rgba(15,23,42,0.8) !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #fff !important;
    padding: 6px 26px 6px 10px !important;
    font-size: 12px !important;
    outline: none !important;
    box-sizing: border-box !important;
  }
  #tp-inline-negative-input:focus { border-color: #10b981 !important; }
  #tp-clear-neg-btn {
    position: absolute !important;
    right: 8px !important;
    background: transparent !important;
    border: none !important;
    color: #64748b !important;
    cursor: pointer !important;
    padding: 2px 6px !important;
  }
  #tp-clear-neg-btn:hover { color: #f43f5e !important; }
  .tp-bar-btn, .tp-filter-bar-reset {
    background: rgba(51,65,85,0.6) !important;
    border: 1px solid #334155 !important;
    color: #cbd5e1 !important;
    padding: 5px 10px !important;
    border-radius: 8px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
  }
  .tp-bar-btn:hover { background: #334155 !important; color: #fff !important; }
  .tp-bar-btn.tp-active {
    background: rgba(16,185,129,0.2) !important;
    border-color: rgba(16,185,129,0.4) !important;
    color: #34d399 !important;
  }
  .tp-bar-stepper-group {
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
    background: rgba(15,23,42,0.6) !important;
    border: 1px solid #334155 !important;
    padding: 2px 6px !important;
    border-radius: 8px !important;
    font-size: 11px !important;
    color: #94a3b8 !important;
  }
  .tp-stepper-btn {
    width: 20px !important;
    height: 20px !important;
    border-radius: 50% !important;
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #fff !important;
    font-weight: 700 !important;
    cursor: pointer !important;
    padding: 0 !important;
  }
  .tp-stepper-btn:hover { background: rgba(16,185,129,0.5) !important; }
  .tp-filter-bar-reset {
    background: rgba(244,63,94,0.15) !important;
    border-color: rgba(244,63,94,0.3) !important;
    color: #fda4af !important;
  }
  .tp-filter-bar-reset:hover { background: rgba(244,63,94,0.3) !important; color: #fff !important; }
  .tp-blocked-cats-row {
    border-top: 1px solid rgba(255,255,255,0.08) !important;
    padding-top: 6px !important;
    align-items: center !important;
    gap: 6px !important;
    flex-wrap: wrap !important;
    max-height: 140px !important;
    overflow-y: auto !important;
  }
  .tp-blocked-cats-row.tp-collapsed {
    display: none !important;
  }
  .tp-blocked-cats-row.tp-expanded {
    display: flex !important;
  }
  .tp-blocked-cats-label {
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #f43f5e !important;
  }
  .tp-blocked-chip {
    display: inline-flex !important;
    align-items: center !important;
    gap: 5px !important;
    padding: 2px 8px !important;
    border-radius: 10px !important;
    font: 600 11px inherit !important;
    background: rgba(239,68,68,0.18) !important;
    border: 1px solid rgba(239,68,68,0.4) !important;
    color: #fca5a5 !important;
  }
  .tp-blocked-chip-remove { cursor: pointer !important; font-weight: 700 !important; }
  .tp-blocked-clear-all {
    font-size: 10px !important;
    color: #94a3b8 !important;
    background: transparent !important;
    border: none !important;
    text-decoration: underline !important;
    cursor: pointer !important;
  }
`;

const SHADOW_MODAL_STYLES = `
  :host { all: initial; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  #tp-settings-fab {
    position: fixed;
    bottom: 14px;
    right: 14px;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: rgba(30,41,59,0.85);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 4px 14px rgba(0,0,0,0.35);
    cursor: pointer;
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #f1f5f9;
    transition: all 0.3s ease;
  }
  #tp-settings-fab:hover {
    background: rgba(16,185,129,0.9);
    transform: scale(1.1);
  }
  #tp-settings-fab svg { width: 24px; height: 24px; }
  dialog#tp-settings-dialog {
    box-sizing: border-box;
    width: 92%;
    max-width: 500px;
    max-height: 85vh;
    background: rgba(30,41,59,0.95);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.12);
    box-shadow: 0 20px 25px rgba(0,0,0,0.5);
    border-radius: 16px;
    color: #f8fafc;
    padding: 24px;
    margin: auto;
  }
  dialog#tp-settings-dialog::backdrop { background: rgba(15,23,42,0.5); backdrop-filter: blur(6px); }
  dialog#tp-settings-dialog h3 {
    margin: 0 0 18px;
    font-size: 18px;
    font-weight: 700;
    background: linear-gradient(to right, #34d399, #059669);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  #tp-settings-sections {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 55vh;
    overflow-y: auto;
  }
  .tp-settings-group { margin-bottom: 16px; display: flex; flex-direction: column; gap: 8px; }
  .tp-settings-group label { font-size: 13px; font-weight: 600; color: #94a3b8; }
  .tp-section-header {
    margin: 14px 0 10px;
    color: #10b981;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding-bottom: 4px;
  }
  .tp-segmented-control {
    display: flex;
    background: rgba(15,23,42,0.6);
    border-radius: 8px;
    padding: 2px;
    border: 1px solid rgba(255,255,255,0.05);
  }
  .tp-segmented-control label {
    flex: 1;
    text-align: center;
    padding: 7px 10px;
    cursor: pointer;
    font-size: 11px;
    font-weight: 600;
    color: #94a3b8;
    border-radius: 6px;
    transition: all 0.2s ease;
  }
  .tp-segmented-control input[type="radio"] { display: none; }
  .tp-segmented-control label:hover { color: #f1f5f9; }
  .tp-segmented-control input[type="radio"]:checked + label {
    background: #10b981;
    color: #fff;
  }
  .tp-segmented-control-blue input[type="radio"]:checked + label { background: #3b82f6 !important; }
  .tp-range-container { display: flex; align-items: center; gap: 12px; }
  .tp-range-container input[type="range"] { flex: 1; accent-color: #10b981; }
  .tp-range-container.tp-blue input[type="range"] { accent-color: #3b82f6; }
  .tp-range-container.tp-rose input[type="range"] { accent-color: #f43f5e; }
  .tp-range-container input[type="number"] {
    width: 60px;
    padding: 4px 8px;
    background: rgba(15,23,42,0.6);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 6px;
    color: #fff;
    font-size: 12px;
    text-align: center;
  }
  .tp-textarea {
    width: 100%;
    box-sizing: border-box;
    min-height: 70px;
    padding: 8px 10px;
    background: rgba(15,23,42,0.6);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    color: #f8fafc;
    font: inherit;
    font-size: 12px;
  }
  .tp-switch-container { display: flex; align-items: center; justify-content: space-between; }
  .tp-switch-label { display: flex; flex-direction: column; gap: 2px; }
  .tp-switch-desc { font-size: 11px; color: #64748b; }
  .tp-switch { position: relative; display: inline-block; width: 44px; height: 24px; }
  .tp-switch input { opacity: 0; width: 0; height: 0; }
  .tp-slider {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background-color: rgba(15,23,42,0.6);
    border-radius: 24px;
    border: 1px solid rgba(255,255,255,0.1);
    transition: .3s;
  }
  .tp-slider:before {
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 3px;
    bottom: 3px;
    background-color: #94a3b8;
    border-radius: 50%;
    transition: .3s;
  }
  .tp-switch input:checked + .tp-slider { background-color: #10b981; }
  .tp-switch.tp-blue input:checked + .tp-slider { background-color: #3b82f6; }
  .tp-switch.tp-rose input:checked + .tp-slider { background-color: #f43f5e; }
  .tp-switch.tp-purple input:checked + .tp-slider { background-color: #8b5cf6; }
  .tp-switch input:checked + .tp-slider:before { transform: translateX(20px); background-color: #fff; }
  .tp-modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid rgba(255,255,255,0.08);
  }
  .tp-btn {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: none;
  }
  .tp-btn-secondary { background: rgba(255,255,255,0.08); color: #94a3b8; }
  .tp-btn-secondary:hover { background: rgba(255,255,255,0.15); color: #fff; }
  .tp-btn-primary {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: #fff;
    box-shadow: 0 4px 12px rgba(16,185,129,0.3);
  }
  #tp-toast-container {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 100000;
    display: flex;
    flex-direction: column-reverse;
    gap: 8px;
  }
  .tp-toast {
    background: rgba(15,23,42,0.96);
    border: 1px solid rgba(56,189,248,0.3);
    color: #f8fafc;
    padding: 9px 14px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    box-shadow: 0 6px 20px rgba(0,0,0,0.45);
    display: flex;
    align-items: center;
    gap: 10px;
    transition: opacity 0.3s ease, transform 0.3s ease;
  }
  .tp-toast.fade-out { opacity: 0; transform: translateY(6px); }
  .tp-toast-undo {
    background: rgba(56,189,248,0.18);
    border: 1px solid rgba(56,189,248,0.5);
    color: #38bdf8;
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
  }
`;

// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  // Compact GM_getValue + localStorage Fallback
  const _getValue = (k, def) => (typeof GM_getValue !== 'undefined' ? GM_getValue(k, def) : JSON.parse(localStorage.getItem('tp_suite_v2_' + k) ?? 'null')) ?? def;
  const _setValue = (k, v) => (typeof GM_setValue !== 'undefined' ? GM_setValue(k, v) : localStorage.setItem('tp_suite_v2_' + k, JSON.stringify(v)));

  const CONFIG = {
    MODE: _getValue('MODE', DEFAULTS.MODE),
    MARGIN_PERCENT: parseFloat(_getValue('MARGIN_PERCENT', DEFAULTS.MARGIN_PERCENT)),
    DIM_OPACITY: parseFloat(_getValue('DIM_OPACITY', DEFAULTS.DIM_OPACITY)),
    USE_SHIPPING_PRICE: _getValue('USE_SHIPPING_PRICE', DEFAULTS.USE_SHIPPING_PRICE),
    HEATMAP_ENABLED: _getValue('HEATMAP_ENABLED', DEFAULTS.HEATMAP_ENABLED),
    HEATMAP_INTENSITY: parseFloat(_getValue('HEATMAP_INTENSITY', DEFAULTS.HEATMAP_INTENSITY)),
    HEATMAP_CURVE: _getValue('HEATMAP_CURVE', DEFAULTS.HEATMAP_CURVE),
    REAL_DEAL_FILTER_ACTIVE: _getValue('REAL_DEAL_FILTER_ACTIVE', DEFAULTS.REAL_DEAL_FILTER_ACTIVE),
    REAL_DEAL_MIN_DISCOUNT: parseInt(_getValue('REAL_DEAL_MIN_DISCOUNT', DEFAULTS.REAL_DEAL_MIN_DISCOUNT)),
    BESTPREISE_MODE_ACTIVE: _getValue('BESTPREISE_MODE_ACTIVE', DEFAULTS.BESTPREISE_MODE_ACTIVE),
    ENABLE_SPARKLINES: _getValue('ENABLE_SPARKLINES', DEFAULTS.ENABLE_SPARKLINES),
    NEGATIVE_TERMS: _getValue('NEGATIVE_TERMS', DEFAULTS.NEGATIVE_TERMS),
    EXCLUDED_CATEGORIES: _getValue('EXCLUDED_CATEGORIES', DEFAULTS.EXCLUDED_CATEGORIES),
    MIN_OFFERS: parseInt(_getValue('MIN_OFFERS', DEFAULTS.MIN_OFFERS)),
    SORT_BY_OFFERS: _getValue('SORT_BY_OFFERS', DEFAULTS.SORT_BY_OFFERS),
    ALARM_ENABLED: _getValue('ALARM_ENABLED', DEFAULTS.ALARM_ENABLED),
    ALARM_TARGET_PERCENT: parseFloat(_getValue('ALARM_TARGET_PERCENT', DEFAULTS.ALARM_TARGET_PERCENT)),
    ALARM_DURATION_DAYS: String(_getValue('ALARM_DURATION_DAYS', DEFAULTS.ALARM_DURATION_DAYS)),
    ALARM_AUTO_SUBMIT: _getValue('ALARM_AUTO_SUBMIT', DEFAULTS.ALARM_AUTO_SUBMIT),
    ALARM_SUBMIT_DELAY_MS: parseInt(_getValue('ALARM_SUBMIT_DELAY_MS', DEFAULTS.ALARM_SUBMIT_DELAY_MS)),
    ALARM_CLOSE_DELAY_MS: parseInt(_getValue('ALARM_CLOSE_DELAY_MS', DEFAULTS.ALARM_CLOSE_DELAY_MS)),
    OBSERVER_DEBOUNCE_MS: parseInt(_getValue('OBSERVER_DEBOUNCE_MS', DEFAULTS.OBSERVER_DEBOUNCE_MS)),
    DEBUG: _getValue('DEBUG', DEFAULTS.DEBUG)
  };

  const saveConfigKey = (key, val) => {
    CONFIG[key] = val;
    _setValue(key, val);
  };

  const log = (...args) => { if (CONFIG.DEBUG) console.log('[Toppreise-Suite]', ...args); };

  if (!document.getElementById('tp-unified-settings-styles')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'tp-unified-settings-styles';
    styleEl.textContent = STYLES;
    document.head.appendChild(styleEl);
  }

  let isBlockedCatsOpen = false;

  function updateBodyClasses() {
    document.body.classList.remove('tp-mode-dim', 'tp-mode-hide', 'tp-mode-highlight-only');
    document.body.classList.add(`tp-mode-${CONFIG.MODE}`);
    document.documentElement.style.setProperty('--tp-dim-opacity', CONFIG.DIM_OPACITY);
  }
  updateBodyClasses();

  const normalizeName = name => name ? name.toLowerCase().replace(/[^a-z0-9]/g, '') : '';

  const ROOT_SLUG_MAP = {
    'computer-zubehoer': 'Computer & Zubehör', 'videogames': 'Videogames', 'tv-video': 'TV & Video',
    'foto-video': 'Foto & Video', 'foto': 'Foto & Video', 'smartphones-mobiltelefone': 'Smartphones & Mobiltelefone',
    'hifi-audio': 'HiFi & Audio', 'haushalt-kueche': 'Haushalt & Küche', 'drogerie': 'Drogerie',
    'sport-freizeit': 'Sport & Freizeit', 'spielwaren': 'Spielwaren', 'buerobedarf-schreibwaren': 'Bürobedarf & Schreibwaren',
    'haus-garten': 'Garten & Baumarkt', 'garten-baumarkt': 'Garten & Baumarkt', 'werkzeuge-werkstatt': 'Garten & Baumarkt',
    'auto-motorrad': 'Auto & Motorrad', 'filme': 'Filme', 'uhren': 'Uhren', 'buecher-medien': 'Bücher & Medien',
    'kleidung-mode': 'Kleidung & Mode', 'bekleidung-schuhe': 'Kleidung & Mode'
  };

  const GROUP_EMOJIS = {
    'Filme': '🎬', 'Spielwaren': '🧸', 'Computer & Zubehör': '💻', 'Videogames': '🎮', 'HiFi & Audio': '🎧',
    'TV & Video': '📺', 'Smartphones & Mobiltelefone': '📱', 'Drogerie': '🧴', 'Sport & Freizeit': '⚽',
    'Haushalt & Küche': '☕', 'Auto & Motorrad': '🚗', 'Uhren': '⌚', 'Foto & Video': '📷', 'Bücher & Medien': '📚',
    'Kleidung & Mode': '👕', 'Garten & Baumarkt': '🪴', 'Sonstiges': '📦'
  };

  const getGroupEmoji = g => GROUP_EMOJIS[g] || '📦';
  const normalizeRootSlug = s => s ? ROOT_SLUG_MAP[s.split('-c')[0].toLowerCase().trim()] || null : null;

  function extractCategoryDisplay(key) {
    if (!key) return { label: '', group: '' };
    if (key.startsWith('GROUP:')) return { label: key.slice(6), group: key.slice(6) };
    if (key.startsWith('PATH:')) {
      const parts = key.slice(5).split('/');
      return { label: parts.slice(1).join('/') || parts[0] || '', group: parts[0] || '' };
    }
    return { label: key, group: '' };
  }

  const BRAND_RULES = [
    { regex: /\b(game|games|spiel|spiele|nintendo|switch|playstation|ps[3-5]|xbox|pc spiele|konsole|konsolen|gamepad|controller|lenkrad|vr headset|amiibo|simulationen|rennspiel|actionspiele|tabletop spiele)\b/i, group: 'Videogames' },
    { regex: /\b(lego[s]?|playmobil|cobi|cada|mega construx|fischertechnik|ravensburger|schleich|barbie|hot wheels|action figuren|funko|nerf|spielwaren|spielzeug|puppe[n]?|plue?sch|autorennbahn|rc modelle|multicopter|puzzles|gesellschaftsspiele|familienspiele|kartenspiele|experimentierkaesten|bau konstruktionsspielzeug|outdoor spielzeug|spielzeugroboter)\b/i, group: 'Spielwaren' },
    { regex: /\b(reifen|pneus|sommerreifen|winterreifen|allwetterreifen|felgen|dachbox[en]?|dachtrae?ger|kindersitz[e]?|autozubehoer|car hifi|car video|motorradhelm|dashcam)\b/i, group: 'Auto & Motorrad' },
    { regex: /\b(fritteuse[n]?|heissluftfritteuse[n]?|vollautomat[en]?|kaffee|espressomaschine[n]?|kaffeemue?hle|kue?chengera?e?te?|haushaltsgera?e?te?|staubsauger|saugroboter|wischroboter|fensterreinigungsroboter|mikrowelle[n]?|backofen|herd|kue?hlschrank|gefrierschrank|geschirrspue?ler|waschmaschine[n]?|wae?schetrockner|mixer|blender|wasserkocher|toaster|thermoskanne|abfallsystem|raumduft|dampfgarer|slowcooker|saftpresse|entsafter|geschirr|besteck|glae?ser|toe?pfe?|pfanne[n]?|kochgeschirr|spirituosen|wein|whisky|gin|rum|vodka|saug und wischroboter|klimageraete|senseo maschinen|sonstige kuechengeraete)\b/i, group: 'Haushalt & Küche' },
    { regex: /\b(haarglae?tter|glae?tteisen|bartschneider|haarschneider|haar bartschneider|rasierer|elektrorasierer|epilierer|haartrockner|foe?hn|zahnbue?rste[n]?|elektrozahnbue?rste[n]?|parfu?e?m|due?fte?|eau de|duschpflege|duschgel|shampoo|seife|geschenkset[s]?|hautpflege|koe?rperpflege|kosmetik|make-up|makeup|sonnenschutz|kontaktlinsen|hygiene)\b/i, group: 'Drogerie' },
    { regex: /\b(smartphone[s]?|mobiltelefon[e]?|handy[s]?|iphone|galaxy|pixel|smartring[e]?|smartwatch(es)?|activity tracker|hue?lle[n]?|cover|oberschalen cover|schutzfolie|panzerglas|ladekabel|powerbank[s]?|magsafe|funktelefon|festnetz)\b/i, group: 'Smartphones & Mobiltelefone' },
    { regex: /\b(kopfhoe?rer|in-ear|earbuds|lautsprecher|bluetooth lautsprecher|soundbar|plattenspieler|receiver|av receiver|home cinema av receiver|verstae?rker|hifi|radio|cd player|dac|subwoofer|mikrofon|musikinstrument|gitarre|piano|keyboard)\b/i, group: 'HiFi & Audio' },
    { regex: /\b(tv|fernseher|tv geraete|beamer|projektor|home cinema|heimkino|blu-ray player|dvd player|actioncam|actionkamera|camcorder|media player|streaming stick|chromecast|apple tv)\b/i, group: 'TV & Video' },
    { regex: /\b(kamera[s]?|digitalkamera|spiegellose|dslr|objektiv[e]?|stativ[e]?|blitz|fotostudio|drohne|sofortbildkamera)\b/i, group: 'Foto & Video' },
    { regex: /\b(dvd|blu-ray|blu ray|4k ultra hd|film[e]?|kino|serie|tv serien|western|abenteuer|action|krimi|drama|komoe?die|thriller|horror|anime|dokumentation)\b/i, group: 'Filme' },
    { regex: /\b(crosstrainer|laufband|laufbae?nder|ergometer|rudergera?e?t|fitness|krafttraining|fitness krafttraining|hantel[n]?|matten|velo[s]?|fahrrad|ebike|e-bike|velohelm|skihelme|skibrille|skihelm|koffer|rucksack|taschenmesser|fernglas|camping|zelt|schlafsack|tretroller|scooter|inline skates|gps|gps navigations geraete|navigation|navigations|activity tracker smartwatches)\b/i, group: 'Sport & Freizeit' },
    { regex: /\b(rasenmae?her|rasenroboter|grill|gasgrill|elektrogrill|holzkohlegrill|bohrmaschine|akkuschrauber|sae?ge|schleifer|schwingschleifer|schalter|taster|steckdose|lampe[n]?|leuchtmittel|led|smart home|gartenmoe?bel|hochdruckreiniger|werkzeug[e]?)\b/i, group: 'Garten & Baumarkt' },
    { regex: /\b(uhr[en]?|armbanduhr|damenuhr|herrenuhr|chronograph|automatikuhr|wanduhr|wecker)\b/i, group: 'Uhren' },
    { regex: /\b(kleidung|bekleidung|jacke[n]?|hose[n]?|t-shirt|pullover|hemd|kleid|schuhe|sneaker|stiefel|tasche[n]?|handtasche|rucksack|sonnenbrille[n]?|schmuck|ring|kette)\b/i, group: 'Kleidung & Mode' },
    { regex: /\b(buch|bue?cher|roman|taschenbuch|sachbuch|hoe?rbuch|comic|manga|zeitschrift)\b/i, group: 'Bücher & Medien' },
    { regex: /\b(usb|speicherstick[s]?|ssd|hdds?|solid state|festplatte[n]?|grafikkarte[n]?|notebook[s]?|laptop[s]?|tablet[s]?|ebook|monitore|monitor|drucker|scanner|nas|mainboard[s]?|prozessor[en]?|cpu|gpu|pc gehaeuse|netzteil[e]?|ladegera?e?t[e]?|ladegeraete netzadapter|kabel|hub|dockingstation|tastatur[en]?|maus|mae?use|mausmatte|webcam[s]?|headset|aktenvernichter|papierschredder|arbeitsspeicher|ram|netzwerk|wlan|router|switch|server|western digital|externe solid state drives ssd|usb speichersticks)\b/i, group: 'Computer & Zubehör' }
  ];

  function resolveCategoryGroup(categoryName, card = null) {
    if (card) {
      for (const href of getCardHrefs(card)) {
        const match = href.match(/\/(?:preisvergleich|produktsuche)\/([^\/]+)\//i);
        if (match && match[1]) {
          for (const seg of match[1].split('/').filter(Boolean)) {
            const canonical = normalizeRootSlug(seg);
            if (canonical) return canonical;
            const normSeg = seg.toLowerCase().replace(/-/g, ' ');
            for (const rule of BRAND_RULES) if (rule.regex.test(normSeg)) return rule.group;
          }
        }
      }
    }
    if (categoryName) {
      const norm = categoryName.toLowerCase();
      for (const rule of BRAND_RULES) if (rule.regex.test(norm)) return rule.group;
    }
    return 'Sonstiges';
  }

  const isPathExcluded = (catName, rootGroup, excludedCats = []) =>
    excludedCats.includes(`GROUP:${rootGroup}`) || (catName && (excludedCats.includes(catName) || excludedCats.includes(`PATH:${rootGroup}/${catName}`)));

  const parsePrice = str => {
    if (!str) return 0;
    let clean = str.replace(/[.–\-]\s*$/g, '.00');
    clean = clean.replace(/[^\d,.]/g, '').replace(/['’\s]/g, '');
    if (/\d+\.\d{3},\d{2}/.test(clean)) {
      clean = clean.replace(/\./g, '').replace(',', '.');
    } else {
      clean = clean.replace(',', '.');
    }
    return parseFloat(clean) || 0;
  };

  function getProductCards() {
    const standardCards = Array.from(document.querySelectorAll('a.Plugin_Product, .Plugin_Product.medium-box, .Plugin_Product.mixedBrowsingList, .mixedBrowsingListProduct, .Plugin_Product'));
    if (standardCards.length > 0) {
      const leafCards = standardCards.filter(c => !c.querySelector('.Plugin_Product, .mixedBrowsingListProduct'));
      if (leafCards.length > 0) return leafCards;
    }

    const gridCards = new Set();
    document.querySelectorAll('a[href*="/preisvergleich/"]').forEach(link => {
      if (link.closest('header, nav, footer, .breadcrumb, #tp-suite-filter-bar')) return;
      let container = link.parentElement;
      while (container && container !== document.body && container.parentElement !== document.body) {
        if (container.querySelector('.Plugin_Price, [class*="Price"], [class*="price"]') || container.querySelector('[class*="Differenz"], [class*="differenz"]')) {
          gridCards.add(container);
          break;
        }
        container = container.parentElement;
      }
    });
    return Array.from(gridCards);
  }

  function formatCategorySlug(slug) {
    if (!slug) return '';
    const clean = decodeURIComponent(slug).replace(/-/g, ' ').trim();
    if (!clean || clean.length < 2 || (clean.toLowerCase().startsWith('p') && !isNaN(clean.slice(1)))) return '';
    return clean.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  }

  function getCardHrefs(card) {
    if (!card) return [];
    const elements = [card.tagName?.toLowerCase() === 'a' ? card : null, card.closest?.('a[href]'), ...(card.querySelectorAll ? card.querySelectorAll('a[href]') : [])];
    return Array.from(new Set(elements.filter(el => el && !el.closest('header, nav, footer, .breadcrumb, #tp-suite-filter-bar')).map(el => el.getAttribute('href') || el.href || ''))).filter(Boolean);
  }

  function extractCardCategory(card) {
    if (!card) return '';
    if (card.dataset?.tpCategory) return card.dataset.tpCategory;

    let extracted = '';
    for (const href of getCardHrefs(card)) {
      const match = href.match(/\/(?:preisvergleich|produktsuche)\/(.+?)(?:\/[^\/]+-p\d+|-c\d+)/i);
      if (match && match[1]) {
        const segments = match[1].split('/').filter(Boolean);
        const subCat = segments[segments.length - 1];
        const formatted = formatCategorySlug(subCat);
        if (formatted) { extracted = formatted; break; }
      }
    }

    if (!extracted && card.querySelector) {
      const catEl = card.querySelector('.subCategory, .productCategory, .categoryLink, [class*="Category"], [data-category]');
      if (catEl) {
        const text = (catEl.getAttribute('data-category') || catEl.textContent).trim().replace(/\(\d+\)/g, '').trim();
        if (text && text.length > 1 && !text.includes('CHF') && !text.includes('Angebot') && !text.includes('%')) extracted = text;
      }
    }

    if (!extracted) {
      const activeBreadcrumb = document.querySelector('.breadcrumb a:last-of-type, [class*="breadcrumb"] a:last-of-type');
      if (activeBreadcrumb) {
        const text = activeBreadcrumb.textContent.trim().replace(/\(\d+\)/g, '').trim();
        if (text && text.length > 1 && !['home', 'toppreise', 'neue toppreise', 'startseite'].includes(text.toLowerCase())) extracted = text;
      }
    }

    if (extracted && card.dataset) card.dataset.tpCategory = extracted;
    return extracted;
  }

  function extractOfferCount(card) {
    if (card.dataset?.tpOfferCount) return parseInt(card.dataset.tpOfferCount, 10);
    const count = parseInt(card.textContent.match(/(\d+)\s*(?:Angebote|Angebot)/i)?.[1] || card.querySelectorAll('.Plugin_DealerRelProdPriceInfo').length, 10);
    if (card.dataset) card.dataset.tpOfferCount = String(count);
    return count;
  }

  function matchesNegativeTerms(card, termsList) {
    if (!termsList || termsList.length === 0) return false;
    const text = (card.innerText || card.textContent || '').toLowerCase();
    return termsList.some(term => {
      if (!term) return false;
      if (term.length <= 3) {
        return new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i').test(text);
      }
      return text.includes(term);
    });
  }

  // ─── DISCOUNT HEATMAP ENGINE ────────────────────────────────────────────────
  function extractCardDiscount(card) {
    if (card.dataset?.tpDiscount !== undefined) {
      const cached = parseFloat(card.dataset.tpDiscount);
      return isNaN(cached) ? null : cached;
    }
    const badgeEl = card.querySelector('.badge-dif, .badge, [class*="badge-dif"]');
    const match = (badgeEl ? badgeEl.textContent : (card.textContent || '')).match(/([+-]?\d+(?:[.,]\d+)?)\s*%/);
    if (match) {
      const discount = Math.min(100, Math.max(0, Math.abs(parseFloat(match[1].replace(',', '.')))));
      if (!isNaN(discount)) {
        if (card.dataset) card.dataset.tpDiscount = String(discount);
        return discount;
      }
    }
    if (card.dataset) card.dataset.tpDiscount = '';
    return null;
  }

  function getHeatmapStyles(discountPercent, intensity = 1.0, curve = 'calibrated') {
    const d = Math.max(0, Math.min(100, discountPercent));
    let t = curve === 'linear' ? d / 100 : (d <= 10 ? (d / 10) * 0.12 : d >= 50 ? Math.min(1.0, 0.85 + ((d - 50) / 25) * 0.15) : 0.12 + ((d - 10) / 40) * 0.73);
    const stops = [
      { t: 0.00, base: [18, 48, 88],   acc: [28, 92, 175],   border: [56, 140, 248, 0.70] },
      { t: 0.25, base: [12, 58, 64],   acc: [16, 130, 125],  border: [20, 210, 190, 0.75] },
      { t: 0.50, base: [68, 48, 10],   acc: [180, 118, 15],  border: [245, 175, 20, 0.80] },
      { t: 0.75, base: [85, 28, 12],   acc: [228, 76, 18],   border: [251, 115, 36, 0.88] },
      { t: 1.00, base: [98, 14, 32],   acc: [238, 25, 65],   border: [244, 63, 94, 0.95] }
    ];
    let i = stops.findIndex((s, idx) => idx < stops.length - 1 && t >= s.t && t <= stops[idx + 1].t);
    if (i < 0) i = stops.length - 2;
    const s0 = stops[i], s1 = stops[i + 1], factor = (t - s0.t) / (s1.t - s0.t || 1);
    const lerp = (a, b) => Math.round(a + (b - a) * factor);
    const base = [lerp(s0.base[0], s1.base[0]), lerp(s0.base[1], s1.base[1]), lerp(s0.base[2], s1.base[2])];
    const acc = [lerp(s0.acc[0], s1.acc[0]), lerp(s0.acc[1], s1.acc[1]), lerp(s0.acc[2], s1.acc[2])];
    const borderRgb = [lerp(s0.border[0], s1.border[0]), lerp(s0.border[1], s1.border[1]), lerp(s0.border[2], s1.border[2])];
    const borderAlpha = (s0.border[3] + (s1.border[3] - s0.border[3]) * factor);
    const safeInt = Math.max(0.2, Math.min(1.0, intensity));
    const bg = `linear-gradient(135deg, rgba(${base.join(',')},${(0.92 + 0.04 * t).toFixed(2)}) 0%, rgba(${acc.join(',')},${((0.75 + 0.20 * t) * safeInt).toFixed(2)}) 100%)`;
    const border = `rgba(${borderRgb.join(',')},${(borderAlpha * safeInt).toFixed(2)})`;
    const glow = t >= 0.45 ? `0 4px 18px rgba(${acc.join(',')},${(0.32 * safeInt).toFixed(2)})` : 'none';
    return { bg, border, glow };
  }

  // ─── REAL DEAL & PRICE HISTORY ENGINE ───────────────────────────────────────
  const STATS_CACHE_PREFIX = 'tp_hist_v1_';

  function getCardProductId(card) {
    if (!card) return null;
    if (card.dataset?.entityId) return card.dataset.entityId;
    if (card.dataset?.tpProductId) return card.dataset.tpProductId;

    const hrefs = getCardHrefs(card);
    for (const href of hrefs) {
      const match = href.match(/-p(\d+)/);
      if (match && match[1]) {
        if (card.dataset) card.dataset.tpProductId = match[1];
        return match[1];
      }
    }
    return null;
  }

  let lastPruneTimestamp = 0;

  function prunePriceStatsCache(force = false) {
    if (!window.localStorage) return;
    const now = Date.now();
    if (!force && now - lastPruneTimestamp < 10 * 60 * 1000) return;
    lastPruneTimestamp = now;

    try {
      const maxAgeMs = 14 * 24 * 3600 * 1000;
      const entries = [];
      const keysToRemove = [];

      for (let i = 0; i < window.localStorage.length; i++) {
        const key = window.localStorage.key(i);
        if (key && key.startsWith(STATS_CACHE_PREFIX)) {
          try {
            const val = JSON.parse(window.localStorage.getItem(key) || '{}');
            const age = now - (val.time || 0);
            if (!val.time || age > maxAgeMs) {
              keysToRemove.push(key);
            } else {
              entries.push({ key, time: val.time });
            }
          } catch (e) {
            keysToRemove.push(key);
          }
        }
      }

      keysToRemove.forEach(k => window.localStorage.removeItem(k));

      if (entries.length > 300) {
        entries.sort((a, b) => a.time - b.time);
        entries.slice(0, entries.length - 250).forEach(e => window.localStorage.removeItem(e.key));
      }
    } catch (e) {}
  }

  function getCachedPriceStats(productId, ignoreNegative = false) {
    if (!productId) return null;
    try {
      const raw = window.localStorage?.getItem(STATS_CACHE_PREFIX + productId);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      const now = Date.now();
      const ageMs = now - (parsed.time || 0);

      // Handle negative cache entry (unavailable)
      if (parsed.unavailable) {
        if (ignoreNegative) return null;
        const negTtlMs = (CONFIG.NEGATIVE_CACHE_HOURS || 2) * 3600 * 1000;
        if (ageMs < negTtlMs) {
          return parsed;
        }
        return null;
      }

      const ttlMs = (CONFIG.REAL_DEAL_CACHE_HOURS || 48) * 3600 * 1000;
      if (ageMs < ttlMs) {
        return parsed;
      }
    } catch (e) {}
    return null;
  }

  function setCachedPriceStats(productId, stats, isUnavailable = false) {
    if (!productId) return;
    try {
      prunePriceStatsCache();
      const payload = isUnavailable
        ? { unavailable: true, time: Date.now() }
        : { ...stats, time: Date.now() };
      window.localStorage?.setItem(STATS_CACHE_PREFIX + productId, JSON.stringify(payload));
    } catch (e) {
      try {
        prunePriceStatsCache(true);
        const payload = isUnavailable
          ? { unavailable: true, time: Date.now() }
          : { ...stats, time: Date.now() };
        window.localStorage?.setItem(STATS_CACHE_PREFIX + productId, JSON.stringify(payload));
      } catch (err) {}
    }
  }

  function parsePriceStatsFromHtml(html) {
    if (!html) return null;
    const doc = new DOMParser().parseFromString(html, 'text/html');

    const extractPrice = titleText => {
      const titleEls = Array.from(doc.querySelectorAll('.title, .col-12.title, div'));
      const found = titleEls.find(el => el.textContent.trim().toLowerCase() === titleText.toLowerCase());
      if (found) {
        if (found.nextElementSibling?.classList.contains('Plugin_Price')) {
          const val = parsePrice(found.nextElementSibling.textContent);
          if (val > 0) return val;
        }
        const nextPrice = found.nextElementSibling?.querySelector?.('.chartProductPrice .Plugin_Price, .Plugin_Price');
        if (nextPrice) {
          const val = parsePrice(nextPrice.textContent);
          if (val > 0) return val;
        }
        const parentCol = found.closest('.col-4, .col-md-3, .col-md, .cell') ||
                          (found.parentElement && !found.parentElement.classList.contains('title') ? found.parentElement : null) ||
                          found.parentElement?.parentElement;
        const priceEl = parentCol?.querySelector?.('.chartProductPrice .Plugin_Price, .Plugin_Price');
        if (priceEl) {
          const val = parsePrice(priceEl.textContent);
          if (val > 0) return val;
        }
      }
      // Robust regex fallback if DOM layout differs
      const escapedTitle = titleText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const reg = new RegExp(`${escapedTitle}[\\s\\S]{1,400}?class="[^"]*Plugin_Price[^"]*"[^>]*>\\s*([\\d.,'\\s]+)`, 'i');
      const match = html.match(reg);
      if (match && match[1]) {
        const val = parsePrice(match[1]);
        if (val > 0) return val;
      }
      return null;
    };

    const tiefstpreis = extractPrice('Tiefstpreis') ??
                        extractPrice('Prix le plus bas') ??
                        extractPrice('Prezzo più basso') ??
                        extractPrice('Lowest price');
    const hoechstpreis = extractPrice('Höchstpreis') ??
                         extractPrice('Prix le plus haut') ??
                         extractPrice('Prezzo più alto') ??
                         extractPrice('Highest price');
    const aktuellerToppreis = extractPrice('aktueller Toppreis') ??
                              extractPrice('Meilleur prix actuel') ??
                              extractPrice('Miglior prezzo attuale') ??
                              extractPrice('Current best price');

    if (tiefstpreis !== null) {
      return { tiefstpreis, hoechstpreis, aktuellerToppreis };
    }
    return null;
  }

  function analyzePriceTimeSeries(series, currentPrice = null) {
    if (!series || !Array.isArray(series) || series.length === 0) return null;

    // Flatten or handle 2D array [series0, series1]
    let rawPoints = series;
    if (Array.isArray(series[0]) && series[0].length > 0 && Array.isArray(series[0][0])) {
      rawPoints = series[0];
    }

    const points = rawPoints.map(p => {
      if (Array.isArray(p) && p.length >= 2) {
        const ts = typeof p[0] === 'number' ? p[0] : parseInt(p[0]);
        const pr = typeof p[1] === 'number' ? p[1] : parsePrice(String(p[1]));
        return pr > 0 ? [ts, pr] : null;
      }
      if (p && typeof p.price === 'number' && p.price > 0) {
        return [p.timestamp || p.time || 0, p.price];
      }
      return null;
    }).filter(Boolean);

    if (points.length === 0) return null;

    const prices = points.map(p => p[1]);
    const curr = (typeof currentPrice === 'number' && currentPrice > 0) ? currentPrice : prices[prices.length - 1];
    const allTimeLow = Math.min(...prices);
    const allTimeHigh = Math.max(...prices);

    // Calculate previous low before current price drop:
    // Look backwards from recent points while price is within 1% of current low
    let idx = prices.length - 1;
    while (idx > 0 && prices[idx] <= curr * 1.01) {
      idx--;
    }
    const historicalPrices = prices.slice(0, idx + 1);
    const previousLow = historicalPrices.length > 0 ? Math.min(...historicalPrices) : allTimeLow;

    const sorted = [...prices].sort((a, b) => a - b);
    const medianPrice = sorted[Math.floor(sorted.length / 2)];
    const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length;

    const isNewAllTimeLow = previousLow > 0 && curr < previousLow * 0.99;
    const isAtAllTimeLow = curr <= allTimeLow * 1.01;
    const isNonBest = !isAtAllTimeLow;

    const realDiscountVsPrevLow = (previousLow > 0 && isNewAllTimeLow)
      ? Math.round(((previousLow - curr) / previousLow) * 100)
      : 0;

    const realDiscountVsAvg = (avgPrice > curr)
      ? Math.round(((avgPrice - curr) / avgPrice) * 100)
      : 0;

    const markupVsLow = (allTimeLow > 0 && isNonBest)
      ? Math.round(((curr - allTimeLow) / allTimeLow) * 100)
      : 0;

    const realDiscountVsMedian = (medianPrice > curr)
      ? Math.round(((medianPrice - curr) / medianPrice) * 100)
      : 0;

    return {
      tiefstpreis: allTimeLow,
      hoechstpreis: allTimeHigh,
      aktuellerToppreis: curr,
      previousLow: previousLow > 0 ? previousLow : null,
      avgPrice: Math.round(avgPrice * 100) / 100,
      medianPrice: Math.round(medianPrice * 100) / 100,
      isNewAllTimeLow,
      isAtAllTimeLow,
      isNonBest,
      realDiscountVsPrevLow,
      realDiscountVsMedian,
      realDiscountVsAvg,
      markupVsLow,
      dataPointCount: points.length,
      timeSeries: points
    };
  }

  function getBestpreiseTier(stats, cardPrice) {
    if (!stats || stats.unavailable || !stats.tiefstpreis || stats.tiefstpreis <= 0) return null;
    if (!cardPrice || cardPrice <= 0) return null;

    // History Qualification Gate:
    // Minimum 5 historical points if timeSeries is present, and >2% variance across history
    const pointsCount = stats.dataPointCount ?? (Array.isArray(stats.timeSeries) ? stats.timeSeries.length : (stats.timeSeries ? 0 : 5));
    if (pointsCount < 5) return null;
    if (stats.hoechstpreis && stats.tiefstpreis > 0 &&
        ((stats.hoechstpreis - stats.tiefstpreis) / stats.tiefstpreis) < 0.02) {
      return null;
    }

    const isNewLow = !!stats.isNewAllTimeLow;
    const isAtLow = cardPrice <= stats.tiefstpreis * 1.01;

    if (isNewLow) {
      const realPct = stats.realDiscountVsPrevLow || 0;
      return {
        tier: 1,
        label: 'Neuer Rekord',
        emoji: '🔥',
        realPct,
        score: 1000 + realPct
      };
    }
    if (isAtLow) {
      const realPct = stats.realDiscountVsMedian || stats.realDiscountVsAvg || 0;
      return {
        tier: 2,
        label: 'Bestpreis',
        emoji: '🌟',
        realPct,
        score: 500 + realPct
      };
    }
    return null;
  }

  async function fetchPriceTimeSeries(productId) {
    if (!productId) return null;
    try {
      const baseUrl = (location.origin && location.origin.startsWith('http')) ? location.origin : 'https://www.toppreise.ch';
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);
      const postBody = `pcspagdpi=${encodeURIComponent(productId)}&pcspagdfdt=0000-00-00&pcspagdtd=&p_pc_ch=&lang=de`;
      const res = await fetch(`${baseUrl}/plugins/product/pricechart`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json, text/javascript, */*; q=0.01'
        },
        credentials: 'same-origin',
        body: postBody,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (!res.ok) return null;
      const data = await res.json();
      if (Array.isArray(data)) {
        // If 2D array of series [[series0], [series1]]
        if (Array.isArray(data[0]) && data[0].length > 0 && Array.isArray(data[0][0])) {
          return data[0]; // Series 0: Produktpreis
        }
        if (Array.isArray(data[0]) && typeof data[0][0] === 'number') {
          return data; // Raw points [[t1, p1], [t2, p2]]
        }
      }
      if (Array.isArray(data?.series)) return data.series;
      if (Array.isArray(data?.data)) return data.data;
      return null;
    } catch (err) {
      if (CONFIG.DEBUG) console.warn('[Toppreise Suite] Failed fetching time series for product', productId, err);
      return null;
    }
  }

  const activeFetches = new Map();

  async function fetchSingleProductPriceStats(productId, retries = 1, forceFresh = false) {
    if (!productId) return null;
    const cached = getCachedPriceStats(productId, forceFresh);
    if (cached) {
      if (cached.unavailable) return null;
      return cached;
    }

    if (activeFetches.has(productId)) {
      return activeFetches.get(productId);
    }

    const fetchPromise = (async () => {
      try {
        const baseUrl = (location.origin && location.origin.startsWith('http')) ? location.origin : 'https://www.toppreise.ch';
        
        // 1. Primary fast route: POST JSON time-series (gives series + all aggregates in 1 request)
        try {
          const timeSeries = await fetchPriceTimeSeries(productId);
          if (timeSeries && Array.isArray(timeSeries) && timeSeries.length >= 1) {
            const analysis = analyzePriceTimeSeries(timeSeries);
            if (analysis && analysis.tiefstpreis > 0) {
              setCachedPriceStats(productId, analysis);
              return analysis;
            }
          }
        } catch (seriesErr) {}

        // 2. Fallback route: GET HTML modal dialog
        const url = `${baseUrl}/plugins/product/pricechart?p_pc_pid=${encodeURIComponent(productId)}`;
        let resHtml = null;
        for (let attempt = 0; attempt <= retries; attempt++) {
          try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 7000);
            resHtml = await fetch(url, {
              headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'text/html, */*; q=0.01'
              },
              credentials: 'same-origin',
              signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (resHtml.ok) break;
            // If rate limited (429) or temporary server error, back off before retrying
            if (attempt < retries) {
              await new Promise(r => setTimeout(r, 400 + attempt * 400));
            }
          } catch (fetchErr) {
            if (attempt < retries) {
              await new Promise(r => setTimeout(r, 400 + attempt * 400));
            } else {
              throw fetchErr;
            }
          }
        }

        if (!resHtml || !resHtml.ok) {
          setCachedPriceStats(productId, null, true);
          return null;
        }
        const html = await resHtml.text();
        const stats = parsePriceStatsFromHtml(html);
        if (stats) {
          setCachedPriceStats(productId, stats);
          return stats;
        } else {
          setCachedPriceStats(productId, null, true);
        }
      } catch (err) {
        if (CONFIG.DEBUG) console.warn('[Toppreise Suite] Failed fetching price stats for product', productId, err);
        setCachedPriceStats(productId, null, true);
      } finally {
        activeFetches.delete(productId);
      }
      return null;
    })();

    activeFetches.set(productId, fetchPromise);
    return fetchPromise;
  }

  let isBatchChecking = false;
  let batchCancelRequested = false;

  async function runBatchDealCheck(minDiscount = 30, onProgress = null, onComplete = null) {
    if (isBatchChecking) {
      batchCancelRequested = true;
      return;
    }
    isBatchChecking = true;
    batchCancelRequested = false;

    try {
      const cards = getProductCards();
      const targets = [];

      for (const card of cards) {
        const pid = getCardProductId(card);
        if (!pid) continue;
        const discount = extractCardDiscount(card) ?? 0;
        const cached = getCachedPriceStats(pid);
        // Skip already cached items (both valid stats and negative unavailable cache)
        if (!cached && discount >= minDiscount) {
          targets.push({ pid, card, discount });
        }
      }

      const total = targets.length;
      let completed = 0;

      if (total === 0) {
        if (onComplete) onComplete(0, 0);
        return;
      }

      for (let i = 0; i < targets.length; i++) {
        if (batchCancelRequested) break;
        const item = targets[i];
        const res = await fetchSingleProductPriceStats(item.pid);
        completed++;
        if (onProgress) onProgress(completed, total);
        processListings();
        // Adaptive pacing between 250ms–350ms to respect server limits
        const paceDelay = 250 + Math.floor(Math.random() * 100);
        await new Promise(r => setTimeout(r, paceDelay));
      }

      if (onComplete) onComplete(completed, total);
    } finally {
      isBatchChecking = false;
      batchCancelRequested = false;
      processListings();
    }
  }

  function cancelBatchDealCheck() {
    batchCancelRequested = true;
  }

  let isBestpreiseScanning = false;
  let bestpreiseScanCancel = false;

  async function runBestpreiseScan(onProgress = null, onComplete = null) {
    if (isBestpreiseScanning) {
      bestpreiseScanCancel = true;
      return;
    }
    isBestpreiseScanning = true;
    bestpreiseScanCancel = false;

    try {
      const cards = getProductCards();
      const targets = [];

      for (const card of cards) {
        const pid = getCardProductId(card);
        if (!pid) continue;
        const cached = getCachedPriceStats(pid);
        if (cached) continue;
        const discount = extractCardDiscount(card) ?? 0;
        targets.push({ pid, card, discount });
      }

      // Priority: highest feed discount first (most likely genuine deals)
      targets.sort((a, b) => b.discount - a.discount);

      const total = targets.length;
      let completed = 0;

      if (total === 0) {
        processListings();
        if (onComplete) onComplete(0, 0);
        return;
      }

      for (let i = 0; i < targets.length; i++) {
        if (bestpreiseScanCancel || !CONFIG.BESTPREISE_MODE_ACTIVE) break;
        const item = targets[i];
        await fetchSingleProductPriceStats(item.pid);
        completed++;
        if (onProgress) onProgress(completed, total);
        processListings();
        await new Promise(r => setTimeout(r, 200));
      }

      if (onComplete) onComplete(completed, total);
    } finally {
      isBestpreiseScanning = false;
      bestpreiseScanCancel = false;
      processListings();
    }
  }

  function cancelBestpreiseScan() {
    bestpreiseScanCancel = true;
  }

  function resetAllFilters() {
    saveConfigKey('NEGATIVE_TERMS', '');
    saveConfigKey('EXCLUDED_CATEGORIES', []);
    saveConfigKey('MIN_OFFERS', 0);
    saveConfigKey('REAL_DEAL_FILTER_ACTIVE', false);
    saveConfigKey('BESTPREISE_MODE_ACTIVE', false);
    cancelBestpreiseScan();
    cancelBatchDealCheck();

    const inlineInput = document.getElementById('tp-inline-negative-input');
    if (inlineInput) inlineInput.value = '';
    const clearBtn = document.getElementById('tp-clear-neg-btn');
    if (clearBtn) clearBtn.style.display = 'none';

    if (uiShadowRoot) {
      const modalNeg = uiShadowRoot.getElementById('tp-negative-terms-input');
      if (modalNeg) modalNeg.value = '';
      const modalVal = uiShadowRoot.getElementById('tp-min-offers-val');
      const modalRange = uiShadowRoot.getElementById('tp-min-offers-range');
      if (modalVal) modalVal.value = 0;
      if (modalRange) modalRange.value = 0;
      const modalRealDealToggle = uiShadowRoot.getElementById('tp-real-deal-filter-toggle');
      if (modalRealDealToggle) modalRealDealToggle.checked = false;
      const modalBestpreiseToggle = uiShadowRoot.getElementById('tp-bestpreise-mode-toggle');
      if (modalBestpreiseToggle) modalBestpreiseToggle.checked = false;
    }
    processListings();
    showToast('Alle Filter zurückgesetzt');
  }

  function getSuiteBarPlacement() {
    const bar = document.getElementById('tp-suite-filter-bar');
    const isSafe = el => el && !el.closest('.header, [class*="MainTopHead"], [class*="MainHead"], .f_filter_plugin, .filters, .filterBox, #tp-root, dialog');
    const targets = ['#Page_ListTopPriceReductionProducts', '#Page_ListTop100Products', '[id^="Page_List"]', '#Page_Browsing', '.f_browsingListContainer', '#Plugin_MixedBrowsingList', '.standardList', '#product-list'];
    for (const sel of targets) {
      const el = document.querySelector(sel);
      if (el?.parentElement && isSafe(el.parentElement) && el !== bar) return { container: el.parentElement, reference: el };
    }
    const containers = [document.getElementById('FrameContent'), document.querySelector('#tpContent .pageContent'), document.querySelector('.pageContent'), document.querySelector('#browseContent'), document.querySelector('main'), document.querySelector('#content')];
    for (const c of containers) {
      if (c && isSafe(c) && c !== bar) {
        let ref = c.firstElementChild;
        while (ref && (ref === bar || !isSafe(ref))) ref = ref.nextElementSibling;
        return { container: c, reference: ref || null };
      }
    }
    return { container: document.body, reference: document.body.firstElementChild };
  }

  function renderSuiteFilterBar(counts = { neg: 0, cat: 0, min: 0, nonBest: 0, uncheckedDeals: 0, bestpreiseDeals: 0 }, pageHasOffers = false, isDealFeed = false) {
    const placement = getSuiteBarPlacement();
    if (!placement?.container) return;

    let bar = document.getElementById('tp-suite-filter-bar');
    const excluded = CONFIG.EXCLUDED_CATEGORIES || [];
    const isRevealed = document.body.classList.contains('tp-reveal-filtered');
    const totalHidden = (counts.neg || 0) + (counts.cat || 0) + (counts.min || 0) + (counts.nonBest || 0) + (counts.bestpreiseHidden || 0);
    const uncheckedDeals = counts.uncheckedDeals || 0;
    const bestpreiseDeals = counts.bestpreiseDeals || 0;

    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'tp-suite-filter-bar';
      if (CONFIG.BESTPREISE_MODE_ACTIVE) bar.classList.add('tp-bestpreise-bar');
      bar.innerHTML = `
        <div class="tp-filter-main-row">
          <div class="tp-input-wrapper" title="Kommagetrennte Begriffe eingeben">
            <span class="tp-filter-badge" title="Toppreise Power Filter">⚡</span>
            <span class="tp-input-label-inline">🚫 Negativ-Filter:</span>
            <div class="tp-input-field-box">
              <input type="text" id="tp-inline-negative-input" placeholder="Wörter ausschließen..." value="${CONFIG.NEGATIVE_TERMS || ''}">
              <button id="tp-clear-neg-btn" title="Text leeren" style="display: ${CONFIG.NEGATIVE_TERMS ? 'block' : 'none'};">✕</button>
            </div>
          </div>
          <button class="tp-bar-btn ${isRevealed ? 'tp-active' : ''}" id="tp-bar-reveal-btn" title="Ausgeblendete Produkte anzeigen/verbergen">
            👁️ <span id="tp-bar-reveal-count">${totalHidden}</span>
          </button>
          <button class="tp-bar-btn ${CONFIG.HEATMAP_ENABLED ? 'tp-active' : ''}" id="tp-bar-heat-btn" title="Rabatt-Heatmap ein-/ausschalten" style="display: ${isDealFeed ? 'flex' : 'none'};">🔥 Heatmap</button>
          <button class="tp-bar-btn ${CONFIG.BESTPREISE_MODE_ACTIVE ? 'tp-bestpreise-active' : ''}" id="tp-bar-bestpreise-btn" title="Neue Bestpreise Modus: Verifizierte Bestpreise nach echtem Rabatt filtern und sortieren" style="display: ${isDealFeed ? 'flex' : 'none'};">
            💎 Neue Bestpreise <span id="tp-bar-bestpreise-count" style="display: ${bestpreiseDeals > 0 ? 'inline' : 'none'}; font-size: 10px; opacity: 0.85;">(${bestpreiseDeals})</span>
          </button>
          <button class="tp-bar-btn ${CONFIG.REAL_DEAL_FILTER_ACTIVE ? 'tp-active' : ''} ${CONFIG.BESTPREISE_MODE_ACTIVE ? 'tp-disabled' : ''}" id="tp-bar-real-deal-btn" title="${CONFIG.BESTPREISE_MODE_ACTIVE ? 'Inaktiv: Bestpreise-Modus filtert bereits echte Tiefstpreise' : 'Nur echte Allzeit-Tiefstpreise anzeigen (Nicht-Bestpreise ausblenden)'}" style="display: ${isDealFeed ? 'flex' : 'none'};">
            🌟 Nur Tiefstpreise <span id="tp-bar-real-deal-count" style="display: ${counts.nonBest > 0 ? 'inline' : 'none'}; font-size: 10px; opacity: 0.85;">(${counts.nonBest || 0})</span>
          </button>
          <div class="tp-threshold-wrapper" id="tp-bar-threshold-wrapper" style="display: ${isDealFeed ? 'inline-flex' : 'none'};">
            <button class="tp-bar-btn ${isBatchChecking ? 'tp-batch-active' : ''} ${CONFIG.BESTPREISE_MODE_ACTIVE ? 'tp-disabled' : ''}" id="tp-bar-batch-check-btn" title="${CONFIG.BESTPREISE_MODE_ACTIVE ? 'Inaktiv: Bestpreise-Modus scannt Deals automatisch' : `Tiefstpreise für ${uncheckedDeals} Deals ab ${CONFIG.REAL_DEAL_MIN_DISCOUNT || 30}% Rabatt prüfen`}" style="border-top-right-radius: 0 !important; border-bottom-right-radius: 0 !important; border-right: none !important;">
              ${isBatchChecking ? '⏳ Prüfen...' : `🔍 Check Deals (${uncheckedDeals})`}
            </button>
            <button class="tp-threshold-btn" id="tp-bar-threshold-btn" title="Mindest-Rabatt für Deal-Check wählen (aktuell ≥${CONFIG.REAL_DEAL_MIN_DISCOUNT || 30}%)">≥${CONFIG.REAL_DEAL_MIN_DISCOUNT || 30}% ▾</button>
            <div class="tp-threshold-popover" id="tp-threshold-popover">
              <button class="tp-threshold-option ${(CONFIG.REAL_DEAL_MIN_DISCOUNT || 30) === 20 ? 'tp-selected' : ''}" data-val="20">≥ 20%</button>
              <button class="tp-threshold-option ${(CONFIG.REAL_DEAL_MIN_DISCOUNT || 30) === 30 ? 'tp-selected' : ''}" data-val="30">≥ 30%</button>
              <button class="tp-threshold-option ${(CONFIG.REAL_DEAL_MIN_DISCOUNT || 30) === 40 ? 'tp-selected' : ''}" data-val="40">≥ 40%</button>
              <button class="tp-threshold-option ${(CONFIG.REAL_DEAL_MIN_DISCOUNT || 30) === 50 ? 'tp-selected' : ''}" data-val="50">≥ 50%</button>
              <button class="tp-threshold-option ${(CONFIG.REAL_DEAL_MIN_DISCOUNT || 30) === 60 ? 'tp-selected' : ''}" data-val="60">≥ 60%</button>
            </div>
          </div>
          <button class="tp-bar-btn ${isBlockedCatsOpen ? 'tp-active' : ''}" id="tp-bar-cats-toggle" style="display: ${excluded.length > 0 ? 'flex' : 'none'};" title="Ausgeblendete Kategorien anzeigen/verbergen">
            🚫 <span id="tp-bar-cats-count">${excluded.length}</span> ${isBlockedCatsOpen ? '▴' : '▾'}
          </button>
          <div class="tp-bar-stepper-group" id="tp-bar-min-offers-group" style="display: ${pageHasOffers ? 'flex' : 'none'};">
            <span>Min:</span>
            <button class="tp-stepper-btn" id="tp-bar-min-minus">-</button>
            <span id="tp-bar-min-val" style="min-width: 14px; text-align: center;">${CONFIG.MIN_OFFERS}</span>
            <button class="tp-stepper-btn" id="tp-bar-min-plus">+</button>
          </div>
          <button class="tp-filter-bar-reset" id="tp-bar-reset-btn">🔄 Reset</button>
        </div>
        <div id="tp-blocked-cats-container" class="tp-blocked-cats-row" style="display: ${excluded.length > 0 && isBlockedCatsOpen ? 'flex' : 'none'};">
          <span class="tp-blocked-cats-label">🚫 Ausgeblendet (${excluded.length}):</span>
          <div id="tp-blocked-chips-list" style="display: inline-flex; flex-wrap: wrap; gap: 4px; align-items: center;"></div>
          <button class="tp-blocked-clear-all" id="tp-blocked-clear-all-btn">Alle freigeben</button>
        </div>
      `;

      if (placement.reference && placement.reference.parentElement === placement.container && placement.reference !== bar) {
        placement.container.insertBefore(bar, placement.reference);
      } else {
        placement.container.appendChild(bar);
      }

      const input = bar.querySelector('#tp-inline-negative-input');
      const clearBtn = bar.querySelector('#tp-clear-neg-btn');

      input.onkeydown = e => {
        if (e.key === 'Escape') {
          e.preventDefault();
          input.blur();
        }
      };

      input.oninput = e => {
        saveConfigKey('NEGATIVE_TERMS', e.target.value);
        if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
        if (uiShadowRoot) {
          const modalInput = uiShadowRoot.getElementById('tp-negative-terms-input');
          if (modalInput) modalInput.value = e.target.value;
        }
        processListings();
      };

      clearBtn.onclick = () => {
        input.value = '';
        saveConfigKey('NEGATIVE_TERMS', '');
        clearBtn.style.display = 'none';
        if (uiShadowRoot) {
          const modalInput = uiShadowRoot.getElementById('tp-negative-terms-input');
          if (modalInput) modalInput.value = '';
        }
        processListings();
      };

      bar.querySelector('#tp-bar-reveal-btn').onclick = () => {
        document.body.classList.toggle('tp-reveal-filtered');
        processListings();
      };

      bar.querySelector('#tp-bar-heat-btn').onclick = () => {
        const nextState = !CONFIG.HEATMAP_ENABLED;
        saveConfigKey('HEATMAP_ENABLED', nextState);
        if (uiShadowRoot) {
          const modalToggle = uiShadowRoot.getElementById('tp-heatmap-enabled-toggle');
          if (modalToggle) modalToggle.checked = nextState;
        }
        processListings();
      };

      const bestpreiseToggleBtn = bar.querySelector('#tp-bar-bestpreise-btn');
      if (bestpreiseToggleBtn) {
        bestpreiseToggleBtn.onclick = () => {
          const next = !CONFIG.BESTPREISE_MODE_ACTIVE;
          saveConfigKey('BESTPREISE_MODE_ACTIVE', next);
          if (uiShadowRoot) {
            const modalToggle = uiShadowRoot.getElementById('tp-bestpreise-mode-toggle');
            if (modalToggle) modalToggle.checked = next;
          }
          if (next) {
            showToast('💎 Neue Bestpreise-Modus aktiviert (Scanne Angebote...)');
            processListings();
            runBestpreiseScan(
              (curr, total) => {
                const btn = document.getElementById('tp-bar-bestpreise-btn');
                if (btn) {
                  btn.innerHTML = `⏳ Bestpreise (${curr}/${total})`;
                }
              },
              (completed, total) => {
                processListings();
                if (total > 0) {
                  showToast(`💎 Bestpreise-Scan abgeschlossen (${completed} Produkte geprüft)`);
                }
              }
            );
          } else {
            cancelBestpreiseScan();
            processListings();
            showToast('Bestpreise-Modus deaktiviert');
          }
        };
      }

      bar.querySelector('#tp-bar-real-deal-btn').onclick = () => {
        if (CONFIG.BESTPREISE_MODE_ACTIVE) return;
        const next = !CONFIG.REAL_DEAL_FILTER_ACTIVE;
        saveConfigKey('REAL_DEAL_FILTER_ACTIVE', next);
        if (uiShadowRoot) {
          const modalToggle = uiShadowRoot.getElementById('tp-real-deal-filter-toggle');
          if (modalToggle) modalToggle.checked = next;
        }
        processListings();
        showToast(next ? 'Nicht-Bestpreise ausgeblendet' : 'Alle Angebote sichtbar');
      };

      const batchBtn = bar.querySelector('#tp-bar-batch-check-btn');
      if (batchBtn) {
        batchBtn.onclick = () => {
          if (CONFIG.BESTPREISE_MODE_ACTIVE) return;
          if (isBatchChecking) {
            cancelBatchDealCheck();
            batchBtn.innerHTML = `🔍 Check Deals (${uncheckedDeals})`;
            batchBtn.classList.remove('tp-batch-active');
            showToast('Batch-Prüfung abgebrochen');
            return;
          }
          batchBtn.classList.add('tp-batch-active');
          batchBtn.innerHTML = '⏳ Starte...';
          runBatchDealCheck(
            CONFIG.REAL_DEAL_MIN_DISCOUNT || 30,
            (curr, total) => {
              if (batchBtn) {
                batchBtn.innerHTML = `⏳ Prüfe (${curr}/${total}) <span title="Abbrechen" style="font-weight:700;margin-left:4px;">✕</span>`;
              }
            },
            (completed, total) => {
              if (batchBtn) {
                batchBtn.classList.remove('tp-batch-active');
                if (total > 0) {
                  batchBtn.innerHTML = `✅ ${completed}/${total} geprüft`;
                  setTimeout(() => {
                    if (batchBtn && !isBatchChecking) {
                      processListings();
                    }
                  }, 3000);
                  showToast(`${completed} Deal-Tiefstpreise verifiziert`);
                }
              }
            }
          );
        };
      }

      const threshBtn = bar.querySelector('#tp-bar-threshold-btn');
      const threshPopover = bar.querySelector('#tp-threshold-popover');
      if (threshBtn && threshPopover) {
        threshBtn.onclick = e => {
          e.preventDefault();
          e.stopPropagation();
          const isOpen = threshPopover.classList.toggle('tp-show');
          threshBtn.classList.toggle('tp-open', isOpen);
        };

        threshPopover.querySelectorAll('.tp-threshold-option').forEach(opt => {
          opt.onclick = e => {
            e.preventDefault();
            e.stopPropagation();
            const val = parseInt(opt.dataset.val, 10);
            if (!isNaN(val)) {
              saveConfigKey('REAL_DEAL_MIN_DISCOUNT', val);
              if (uiShadowRoot) {
                const modalRange = uiShadowRoot.getElementById('tp-real-deal-min-range');
                const modalVal = uiShadowRoot.getElementById('tp-real-deal-min-val');
                if (modalRange) modalRange.value = val;
                if (modalVal) modalVal.value = val;
              }
              threshPopover.classList.remove('tp-show');
              threshBtn.classList.remove('tp-open');
              processListings();
              showToast(`Mindest-Rabatt für Deals auf ${val}% gesetzt`);
            }
          };
        });

        document.addEventListener('click', () => {
          threshPopover.classList.remove('tp-show');
          threshBtn.classList.remove('tp-open');
        });
      }

      bar.querySelector('#tp-bar-cats-toggle').onclick = () => {
        isBlockedCatsOpen = !isBlockedCatsOpen;
        processListings();
      };

      const updateMinOffers = delta => {
        const next = Math.max(0, CONFIG.MIN_OFFERS + delta);
        if (next !== CONFIG.MIN_OFFERS) {
          saveConfigKey('MIN_OFFERS', next);
          if (uiShadowRoot) {
            const modalVal = uiShadowRoot.getElementById('tp-min-offers-val');
            const modalRange = uiShadowRoot.getElementById('tp-min-offers-range');
            if (modalVal) modalVal.value = next;
            if (modalRange) modalRange.value = next;
          }
          processListings();
        }
      };

      bar.querySelector('#tp-bar-min-minus').onclick = () => updateMinOffers(-1);
      bar.querySelector('#tp-bar-min-plus').onclick = () => updateMinOffers(1);
      bar.querySelector('#tp-bar-reset-btn').onclick = resetAllFilters;
      bar.querySelector('#tp-blocked-clear-all-btn').onclick = () => {
        saveConfigKey('EXCLUDED_CATEGORIES', []);
        processListings();
        showToast('Alle blockierten Kategorien freigegeben');
      };
    } else if (bar.parentElement !== placement.container || (bar.nextSibling !== placement.reference && placement.reference !== bar)) {
      if (placement.reference && placement.reference.parentElement === placement.container && placement.reference !== bar) {
        placement.container.insertBefore(bar, placement.reference);
      } else {
        placement.container.appendChild(bar);
      }
    }

    bar.style.display = 'flex';
    bar.classList.toggle('tp-bestpreise-bar', CONFIG.BESTPREISE_MODE_ACTIVE === true);

    const input = bar.querySelector('#tp-inline-negative-input');
    const clearBtn = bar.querySelector('#tp-clear-neg-btn');
    if (input && document.activeElement !== input) {
      input.value = CONFIG.NEGATIVE_TERMS || '';
      if (clearBtn) clearBtn.style.display = CONFIG.NEGATIVE_TERMS ? 'block' : 'none';
    }

    bar.querySelector('#tp-bar-reveal-btn')?.classList.toggle('tp-active', isRevealed);
    const revealCount = bar.querySelector('#tp-bar-reveal-count');
    if (revealCount) revealCount.textContent = totalHidden > 0 ? `${totalHidden}` : '0';

    const heatBtn = bar.querySelector('#tp-bar-heat-btn');
    if (heatBtn) {
      heatBtn.classList.toggle('tp-active', CONFIG.HEATMAP_ENABLED !== false);
      heatBtn.style.setProperty('display', isDealFeed ? 'flex' : 'none', 'important');
    }

    const bestpreiseBtn = bar.querySelector('#tp-bar-bestpreise-btn');
    if (bestpreiseBtn) {
      bestpreiseBtn.classList.toggle('tp-bestpreise-active', CONFIG.BESTPREISE_MODE_ACTIVE === true);
      bestpreiseBtn.style.setProperty('display', isDealFeed ? 'flex' : 'none', 'important');
      if (isBestpreiseScanning) {
        // Leave dynamic text during scan
      } else if (CONFIG.BESTPREISE_MODE_ACTIVE) {
        bestpreiseBtn.innerHTML = `💎 Bestpreise <span id="tp-bar-bestpreise-count" style="display: ${bestpreiseDeals > 0 ? 'inline' : 'none'}; font-size: 10px; opacity: 0.85;">(${bestpreiseDeals} Deals)</span>`;
      } else {
        bestpreiseBtn.innerHTML = `💎 Neue Bestpreise <span id="tp-bar-bestpreise-count" style="display: ${bestpreiseDeals > 0 ? 'inline' : 'none'}; font-size: 10px; opacity: 0.85;">(${bestpreiseDeals})</span>`;
      }
    }

    const realDealBtn = bar.querySelector('#tp-bar-real-deal-btn');
    if (realDealBtn) {
      realDealBtn.classList.toggle('tp-active', CONFIG.REAL_DEAL_FILTER_ACTIVE !== false);
      realDealBtn.classList.toggle('tp-disabled', CONFIG.BESTPREISE_MODE_ACTIVE === true);
      realDealBtn.title = CONFIG.BESTPREISE_MODE_ACTIVE
        ? 'Inaktiv: Bestpreise-Modus filtert bereits echte Tiefstpreise'
        : 'Nur echte Allzeit-Tiefstpreise anzeigen (Nicht-Bestpreise ausblenden)';
      realDealBtn.style.setProperty('display', isDealFeed ? 'flex' : 'none', 'important');
      const countSpan = bar.querySelector('#tp-bar-real-deal-count');
      if (countSpan) {
        countSpan.textContent = counts.nonBest > 0 ? `(${counts.nonBest})` : '';
        countSpan.style.display = counts.nonBest > 0 ? 'inline' : 'none';
      }
    }

    const batchBtn = bar.querySelector('#tp-bar-batch-check-btn');
    if (batchBtn && !isBatchChecking) {
      batchBtn.classList.toggle('tp-disabled', CONFIG.BESTPREISE_MODE_ACTIVE === true);
      batchBtn.title = CONFIG.BESTPREISE_MODE_ACTIVE
        ? 'Inaktiv: Bestpreise-Modus scannt Deals automatisch'
        : `Tiefstpreise für ${uncheckedDeals} Deals ab ${CONFIG.REAL_DEAL_MIN_DISCOUNT || 30}% Rabatt prüfen`;
      batchBtn.innerHTML = `🔍 Check Deals (${uncheckedDeals})`;
      batchBtn.classList.remove('tp-batch-active');
    }

    const threshBtn = bar.querySelector('#tp-bar-threshold-btn');
    if (threshBtn) {
      const minDisc = CONFIG.REAL_DEAL_MIN_DISCOUNT || 30;
      threshBtn.textContent = `≥${minDisc}% ▾`;
      threshBtn.title = `Mindest-Rabatt für Deal-Check wählen (aktuell ≥${minDisc}%)`;
    }
    const threshPopover = bar.querySelector('#tp-threshold-popover');
    if (threshPopover) {
      const minDisc = CONFIG.REAL_DEAL_MIN_DISCOUNT || 30;
      threshPopover.querySelectorAll('.tp-threshold-option').forEach(opt => {
        opt.classList.toggle('tp-selected', parseInt(opt.dataset.val, 10) === minDisc);
      });
    }

    const threshWrapper = bar.querySelector('#tp-bar-threshold-wrapper');
    if (threshWrapper) {
      threshWrapper.style.setProperty('display', isDealFeed ? 'inline-flex' : 'none', 'important');
    }

    const catsToggleBtn = bar.querySelector('#tp-bar-cats-toggle');
    if (catsToggleBtn) {
      catsToggleBtn.style.display = excluded.length > 0 ? 'flex' : 'none';
      catsToggleBtn.classList.toggle('tp-active', isBlockedCatsOpen);
      catsToggleBtn.innerHTML = `🚫 <span id="tp-bar-cats-count">${excluded.length}</span> ${isBlockedCatsOpen ? '▴' : '▾'}`;
    }

    const minGroup = bar.querySelector('#tp-bar-min-offers-group');
    if (minGroup) minGroup.style.display = pageHasOffers ? 'flex' : 'none';
    const minVal = bar.querySelector('#tp-bar-min-val');
    if (minVal) minVal.textContent = CONFIG.MIN_OFFERS;

    const blockedContainer = bar.querySelector('#tp-blocked-cats-container');
    const chipsList = bar.querySelector('#tp-blocked-chips-list');
    if (blockedContainer && chipsList) {
      const showDrawer = excluded.length > 0 && isBlockedCatsOpen;
      blockedContainer.classList.toggle('tp-expanded', showDrawer);
      blockedContainer.classList.toggle('tp-collapsed', !showDrawer);
      blockedContainer.style.setProperty('display', showDrawer ? 'flex' : 'none', 'important');

      if (excluded.length > 0) {
        chipsList.innerHTML = '';
        const labelEl = blockedContainer.querySelector('.tp-blocked-cats-label');
        if (labelEl) labelEl.textContent = `🚫 Ausgeblendet (${excluded.length}):`;

        excluded.forEach(key => {
          const info = extractCategoryDisplay(key);
          const chip = document.createElement('span');
          chip.className = 'tp-blocked-chip';
          chip.innerHTML = `${getGroupEmoji(info.group)} <span>${info.label}</span> <span class="tp-blocked-chip-remove" title="Wieder einblenden">✕</span>`;
          chip.querySelector('.tp-blocked-chip-remove').onclick = e => {
            e.stopPropagation();
            saveConfigKey('EXCLUDED_CATEGORIES', (CONFIG.EXCLUDED_CATEGORIES || []).filter(c => c !== key));
            processListings();
            showToast(`Kategorie "${info.label}" wieder eingeblendet`);
          };
          chipsList.appendChild(chip);
        });
      } else {
        chipsList.innerHTML = '';
      }
    }
  }

  function isNeueToppreisePage() {
    return /(?:neue-toppreise|new-best-prices|nouveaux-meilleurs-prix)/i.test(location.href) ||
           /(?:neue-toppreise|new-best-prices|nouveaux-meilleurs-prix)/i.test(document.body?.getAttribute('data-current_url') || '') ||
           document.body?.classList.contains('Page_ListTopPriceReductionProducts') ||
           document.body?.classList.contains('Page_ListTop100Products') ||
           !!document.getElementById('Page_ListTopPriceReductionProducts') ||
           !!document.getElementById('Page_ListTop100Products');
  }

  function getPageType() {
    if (isProductDetailPage()) return 'detail';
    if (isNeueToppreisePage()) return 'deal-feed';
    return 'list';
  }

  let isModifyingDOM = false;

  function extractActiveStores() {
    const filterElements = document.querySelectorAll('.filters .f_remove_filter[data-target-type="df"]');
    return Array.from(filterElements).map(el => {
      const clone = el.cloneNode(true);
      clone.querySelectorAll('.icon-close, .f_remove_icon, .close, span').forEach(i => i.remove());
      return normalizeName(clone.textContent);
    }).filter(name => name.length > 0);
  }

  function parseNegativeTerms() {
    const rawTerms = CONFIG.NEGATIVE_TERMS || '';
    return rawTerms.split(/[,;\n]/).map(t => t.trim().toLowerCase()).filter(Boolean);
  }

  function extractCardData(card) {
    const pid = getCardProductId(card);
    const cardPriceEl = CONFIG.USE_SHIPPING_PRICE
      ? (card.querySelector('.price_information_product .shippingPrice .Plugin_Price') || card.querySelector('.price_information_product .productPrice .Plugin_Price') || card.querySelector('.priceContainer.shippingPrice .Plugin_Price') || card.querySelector('.priceContainer.productPrice .Plugin_Price') || card.querySelector('.Plugin_Price'))
      : (card.querySelector('.price_information_product .productPrice .Plugin_Price') || card.querySelector('.price_information_product .shippingPrice .Plugin_Price') || card.querySelector('.priceContainer.productPrice .Plugin_Price') || card.querySelector('.priceContainer.shippingPrice .Plugin_Price') || card.querySelector('.Plugin_Price'));
    const cardPrice = cardPriceEl ? parsePrice(cardPriceEl.textContent) : 0;
    const stats = pid ? getCachedPriceStats(pid) : null;
    const isVerifiedNonBest = !!(stats && cardPrice > 0 && stats.tiefstpreis > 0 && cardPrice > stats.tiefstpreis * 1.01);
    const discountVal = extractCardDiscount(card);
    const catName = extractCardCategory(card);
    const rootGroup = resolveCategoryGroup(catName, card);
    const offerCount = extractOfferCount(card);

    return {
      card,
      pid,
      cardPriceEl,
      cardPrice,
      stats,
      isVerifiedNonBest,
      discountVal,
      catName,
      rootGroup,
      offerCount
    };
  }

  function applyCardFilters(cd, termsList, excludedCats, minOffers, pageHasOffers) {
    const isNeg = matchesNegativeTerms(cd.card, termsList);
    const isCatExcluded = !!(cd.catName && isPathExcluded(cd.catName, cd.rootGroup, excludedCats));
    const isLowOffers = !!(pageHasOffers && minOffers > 0 && cd.offerCount < minOffers);
    return { isNeg, isCatExcluded, isLowOffers };
  }

  function renderSparkline(timeSeries, width = 60, height = 18) {
    if (!timeSeries || !Array.isArray(timeSeries) || timeSeries.length < 2) return null;
    const prices = timeSeries.map(p => {
      if (Array.isArray(p)) return typeof p[1] === 'number' ? p[1] : parsePrice(String(p[1]));
      if (typeof p === 'number') return p;
      if (p && typeof p.price === 'number') return p.price;
      if (p && p.price) return parsePrice(String(p.price));
      if (p && p.y) return typeof p.y === 'number' ? p.y : parsePrice(String(p.y));
      return 0;
    }).filter(p => p > 0);

    if (prices.length < 2) return null;

    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    const padding = 2;
    const usableHeight = height - padding * 2;

    const points = prices.map((p, i) => {
      const x = ((i / (prices.length - 1)) * width).toFixed(1);
      const y = (height - padding - ((p - min) / range) * usableHeight).toFixed(1);
      return `${x},${y}`;
    }).join(' ');

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', String(width));
    svg.setAttribute('height', String(height));
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.classList.add('tp-sparkline');

    const firstPrice = prices[0];
    const lastPrice = prices[prices.length - 1];
    const isTrendingDown = lastPrice <= firstPrice;
    const strokeColor = isTrendingDown ? '#10b981' : '#ef4444';

    const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    polyline.setAttribute('points', points);
    polyline.setAttribute('fill', 'none');
    polyline.setAttribute('stroke', strokeColor);
    polyline.setAttribute('stroke-width', '1.5');
    polyline.setAttribute('stroke-linecap', 'round');
    polyline.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(polyline);

    svg.setAttribute('title', `Preisverlauf: CHF ${firstPrice.toFixed(2)} → CHF ${lastPrice.toFixed(2)} (Min: ${min.toFixed(2)}, Max: ${max.toFixed(2)})`);

    return svg;
  }

  function renderCardEffects(cd, filters, isNeueFeed, activeStores) {
    const { card, pid, cardPriceEl, cardPrice, stats, isVerifiedNonBest, discountVal, catName, rootGroup } = cd;

    // 0. Heatmap (only applied for unchecked deals or verified Allzeit-Tiefstpreise)
    if (CONFIG.HEATMAP_ENABLED && discountVal !== null && !isVerifiedNonBest) {
      const heatStyles = getHeatmapStyles(discountVal, CONFIG.HEATMAP_INTENSITY, CONFIG.HEATMAP_CURVE);
      card.style.setProperty('--tp-heat-bg', heatStyles.bg);
      card.style.setProperty('--tp-heat-border', heatStyles.border);
      card.style.setProperty('--tp-heat-glow', heatStyles.glow);

      // DarkReader Dynamic Theme compatibility:
      card.style.setProperty('--darkreader-inline-bgimage', heatStyles.bg);
      card.style.setProperty('--darkreader-inline-bgcolor', 'transparent');
      card.style.setProperty('--darkreader-inline-border', heatStyles.border);
      card.style.setProperty('--darkreader-inline-border-top', heatStyles.border);
      card.style.setProperty('--darkreader-inline-border-right', heatStyles.border);
      card.style.setProperty('--darkreader-inline-border-bottom', heatStyles.border);
      card.style.setProperty('--darkreader-inline-border-left', heatStyles.border);
      card.style.setProperty('background', heatStyles.bg, 'important');
      card.style.setProperty('background-image', heatStyles.bg, 'important');
      card.style.setProperty('background-color', 'transparent', 'important');
      card.style.setProperty('border-color', heatStyles.border, 'important');

      card.removeAttribute('data-darkreader-inline-bgcolor');
      card.removeAttribute('data-darkreader-inline-bgimage');

      const subElements = card.querySelectorAll('.product-name, .productDetails, .price_information_product, .Plugin_PriceInformation, .f_product_info, .productDescription, .productDetailsDescription');
      for (let s = 0; s < subElements.length; s++) {
        const sub = subElements[s];
        sub.removeAttribute('data-darkreader-inline-bgcolor');
        sub.removeAttribute('data-darkreader-inline-bgimage');
        sub.style.setProperty('background-color', 'transparent', 'important');
        sub.style.setProperty('background', 'transparent', 'important');
        sub.style.setProperty('--darkreader-inline-bgcolor', 'transparent');
        sub.style.setProperty('--darkreader-inline-bgimage', 'none');
      }

      card.classList.add('tp-heatmap-active');
    } else {
      card.classList.remove('tp-heatmap-active');
      card.style.removeProperty('--tp-heat-bg');
      card.style.removeProperty('--tp-heat-border');
      card.style.removeProperty('--tp-heat-glow');
      card.style.removeProperty('--darkreader-inline-bgimage');
      card.style.removeProperty('--darkreader-inline-bgcolor');
      card.style.removeProperty('--darkreader-inline-border');
      card.style.removeProperty('--darkreader-inline-border-top');
      card.style.removeProperty('--darkreader-inline-border-right');
      card.style.removeProperty('--darkreader-inline-border-bottom');
      card.style.removeProperty('--darkreader-inline-border-left');
      card.style.removeProperty('background');
      card.style.removeProperty('background-image');
      card.style.removeProperty('background-color');
      card.style.removeProperty('border-color');
    }

    // 1. Category extraction & Quick-block
    if (isNeueFeed) {
      if (catName && !card.querySelector('.tp-card-quick-block')) {
        const quickBlockBtn = document.createElement('button');
        quickBlockBtn.type = 'button';
        quickBlockBtn.className = 'tp-card-quick-block';
        quickBlockBtn.title = `Kategorie "${catName}" (${rootGroup}) ausblenden`;
        quickBlockBtn.innerHTML = `🚫 <span>${catName}</span>`;
        quickBlockBtn.onclick = e => {
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          const curr = CONFIG.EXCLUDED_CATEGORIES || [];
          const key = `PATH:${rootGroup}/${catName}`;
          if (!curr.includes(key) && !curr.includes(catName)) {
            isBlockedCatsOpen = true;
            saveConfigKey('EXCLUDED_CATEGORIES', [...curr, key]);
            processListings();
            showToast(`Kategorie "${catName}" ausgeblendet`, 4000, 'Rückgängig', () => {
              saveConfigKey('EXCLUDED_CATEGORIES', (CONFIG.EXCLUDED_CATEGORIES || []).filter(c => c !== key && c !== catName));
              processListings();
              showToast(`Kategorie "${catName}" wieder eingeblendet`);
            });
          }
        };
        card.appendChild(quickBlockBtn);
      }
    } else {
      card.querySelector('.tp-card-quick-block')?.remove();
    }

    // 2. Filters
    card.classList.toggle('tp-negative-filtered', filters.isNeg);
    card.classList.toggle('tp-category-filtered', filters.isCatExcluded);
    card.classList.toggle('tp-min-offers-filtered', filters.isLowOffers);

    // 3. Best Price Highlighting
    if (activeStores.length === 0) {
      card.classList.remove('tp-is-cheapest', 'tp-not-cheapest', 'tp-no-store-offer');
      card.querySelector('.tp-best-price-badge')?.remove();
    } else {
      let matchedRow = null;
      for (const row of card.querySelectorAll('.Plugin_DealerRelProdPriceInfo')) {
        const titleEl = row.querySelector('.title');
        if (titleEl) {
          const rowStoreNormalized = normalizeName(titleEl.textContent);
          if (activeStores.some(store => rowStoreNormalized.includes(store) || store.includes(rowStoreNormalized))) {
            matchedRow = row;
            break;
          }
        }
      }

      if (matchedRow) {
        const storePriceEl = CONFIG.USE_SHIPPING_PRICE
          ? (matchedRow.querySelector('.shippingPrice .Plugin_Price') || matchedRow.querySelector('.productPrice .Plugin_Price'))
          : (matchedRow.querySelector('.productPrice .Plugin_Price') || matchedRow.querySelector('.shippingPrice .Plugin_Price'));
        const storePrice = storePriceEl ? parsePrice(storePriceEl.textContent) : 0;

        const bestPriceEl = CONFIG.USE_SHIPPING_PRICE
          ? (card.querySelector('.price_information_product .shippingPrice .Plugin_Price') || card.querySelector('.price_information_product .productPrice .Plugin_Price') || card.querySelector('.priceContainer.shippingPrice .Plugin_Price') || card.querySelector('.priceContainer.productPrice .Plugin_Price'))
          : (card.querySelector('.price_information_product .productPrice .Plugin_Price') || card.querySelector('.price_information_product .shippingPrice .Plugin_Price') || card.querySelector('.priceContainer.productPrice .Plugin_Price') || card.querySelector('.priceContainer.shippingPrice .Plugin_Price'));
        const bestPrice = bestPriceEl ? parsePrice(bestPriceEl.textContent) : 0;

        if (storePrice > 0 && bestPrice > 0 && storePrice <= bestPrice * (1 + CONFIG.MARGIN_PERCENT / 100)) {
          card.classList.add('tp-is-cheapest');
          card.classList.remove('tp-not-cheapest', 'tp-no-store-offer');
          if (!card.querySelector('.tp-best-price-badge')) {
            const badge = document.createElement('div');
            badge.className = 'tp-best-price-badge';
            badge.textContent = 'Best Price';
            card.appendChild(badge);
          }
        } else {
          card.classList.add(storePrice > 0 && bestPrice > 0 ? 'tp-not-cheapest' : 'tp-no-store-offer');
          card.classList.remove('tp-is-cheapest', storePrice > 0 && bestPrice > 0 ? 'tp-no-store-offer' : 'tp-not-cheapest');
          card.querySelector('.tp-best-price-badge')?.remove();
        }
      } else {
        cd.card.classList.add('tp-no-store-offer');
        cd.card.classList.remove('tp-is-cheapest', 'tp-not-cheapest');
        cd.card.querySelector('.tp-best-price-badge')?.remove();
      }
    }

    // 3.5 Real Deal & Allzeit-Tiefstpreis Check (Consolidated into Differenz Circle Badge)
    const badgeDifEl = card.querySelector('.badge-dif, [class*="badge-dif"]');
    // Remove any legacy floating wrappers if present
    card.querySelector('.tp-real-deal-wrapper')?.remove();

    if (badgeDifEl) {
      if (!badgeDifEl.dataset.tpOriginalDiscount) {
        const initialDiscount = extractCardDiscount(card) ?? 0;
        badgeDifEl.dataset.tpOriginalDiscount = String(initialDiscount);
      }
      const rawDiscount = parseFloat(badgeDifEl.dataset.tpOriginalDiscount) || (extractCardDiscount(card) ?? 0);

      // Bind single click handler on badge
      if (!badgeDifEl.dataset.tpDealBound) {
        badgeDifEl.dataset.tpDealBound = 'true';
        badgeDifEl.addEventListener('click', async e => {
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          if (badgeDifEl.classList.contains('tp-deal-loading')) return;
          const currentPid = getCardProductId(card);
          if (!currentPid) return;

          badgeDifEl.classList.add('tp-deal-loading');
          badgeDifEl.innerHTML = `<div class="text">Prüfe...</div><p>⏳</p>`;
          const fetchedStats = await fetchSingleProductPriceStats(currentPid, 1, true);
          badgeDifEl.classList.remove('tp-deal-loading');
          if (fetchedStats) {
            processListings();
          } else {
            badgeDifEl.classList.remove('tp-deal-alltime-low', 'tp-deal-not-low', 'tp-is-severe-markup');
            badgeDifEl.innerHTML = `<div class="text">Fehler</div><p style="font-size: 13px;">⚠️ n/v</p>`;
            badgeDifEl.title = '⚠️ Preishistorie zurzeit nicht verfügbar (Klicken für erneuten Versuch)';
            setTimeout(() => {
              if (badgeDifEl && !getCachedPriceStats(currentPid)) {
                processListings();
              }
            }, 2500);
          }
        });
      }

      if (CONFIG.BESTPREISE_MODE_ACTIVE) {
        const tier = getBestpreiseTier(stats, cardPrice);
        if (!stats && pid) {
          // Unscanned card: hide in Bestpreise mode until verified
          card.classList.add('tp-bestpreise-hidden');
          if (isBestpreiseScanning) {
            badgeDifEl.classList.add('tp-deal-loading');
            badgeDifEl.innerHTML = `<div class="text">Prüfe...</div><p>⏳</p>`;
          }
        } else if (!tier) {
          // Doesn't qualify as a genuine bestpreis deal
          card.classList.add('tp-bestpreise-hidden');
        } else if (tier.tier === 1) {
          // Tier 1: New Record Low (Golden Diamond Pulse)
          card.classList.remove('tp-bestpreise-hidden', 'tp-non-bestpreis-filtered');
          badgeDifEl.classList.add('tp-deal-new-record', 'tp-deal-badge-interactive');
          badgeDifEl.classList.remove('tp-deal-alltime-low', 'tp-deal-not-low', 'tp-is-severe-markup', 'tp-deal-loading');
          badgeDifEl.innerHTML = `<div class="text">Rekord</div><p>-${tier.realPct}%</p>`;
          const prevLow = stats.previousLow;
          const prevText = prevLow ? ` | Bisher: CHF ${prevLow.toFixed(2)}` : '';
          badgeDifEl.title = `🔥 Neuer Rekord-Tiefstpreis (CHF ${cardPrice.toFixed(2)})!${prevText} (Klicken zum Aktualisieren)`;

          let histPriceEl = card.querySelector('.tp-card-historical-price');
          if (!histPriceEl) {
            histPriceEl = document.createElement('div');
            const priceContainer = card.querySelector('.Plugin_PriceInformation, .price_information_product') ||
                                   cardPriceEl?.closest('.priceContainer, .Plugin_PriceInformation, .price_information_product') ||
                                   cardPriceEl?.parentElement ||
                                   card;
            priceContainer.appendChild(histPriceEl);
          }
          histPriceEl.className = 'tp-card-historical-price tp-is-record-low';
          histPriceEl.textContent = prevLow ? `Bisher: CHF ${prevLow.toFixed(2)} (-${tier.realPct}%)` : `Rekord-Tiefstpreis`;
          histPriceEl.title = `Neuer Rekord-Tiefstpreis! Vorheriges Tief lag bei CHF ${prevLow ? prevLow.toFixed(2) : '?'}`;
        } else if (tier.tier === 2) {
          // Tier 2: Bestpreis / All-Time Low (Glowing Emerald Halo)
          card.classList.remove('tp-bestpreise-hidden', 'tp-non-bestpreis-filtered');
          badgeDifEl.classList.add('tp-deal-alltime-low', 'tp-deal-badge-interactive');
          badgeDifEl.classList.remove('tp-deal-new-record', 'tp-deal-not-low', 'tp-is-severe-markup', 'tp-deal-loading');
          badgeDifEl.innerHTML = `<div class="text">Bestpreis</div><p>-${tier.realPct}%</p>`;
          const avgText = stats.medianPrice ? ` | Median: CHF ${stats.medianPrice.toFixed(2)}` : (stats.avgPrice ? ` | Ø: CHF ${stats.avgPrice.toFixed(2)}` : '');
          badgeDifEl.title = `🌟 Allzeit-Tiefstpreis (CHF ${cardPrice.toFixed(2)})!${avgText} (Klicken zum Aktualisieren)`;

          let histPriceEl = card.querySelector('.tp-card-historical-price');
          if (stats.medianPrice && stats.medianPrice > cardPrice) {
            if (!histPriceEl) {
              histPriceEl = document.createElement('div');
              const priceContainer = card.querySelector('.Plugin_PriceInformation, .price_information_product') ||
                                     cardPriceEl?.closest('.priceContainer, .Plugin_PriceInformation, .price_information_product') ||
                                     cardPriceEl?.parentElement ||
                                     card;
              priceContainer.appendChild(histPriceEl);
            }
            histPriceEl.className = 'tp-card-historical-price tp-is-at-low';
            histPriceEl.textContent = `Ø-Preis: CHF ${stats.medianPrice.toFixed(2)} (-${tier.realPct}%)`;
            histPriceEl.title = `Aktueller Bestpreis liegt ${tier.realPct}% unter dem Median-Preis von CHF ${stats.medianPrice.toFixed(2)}`;
          } else if (histPriceEl) {
            histPriceEl.remove();
          }
        }
      } else {
        card.classList.remove('tp-bestpreise-hidden');
        badgeDifEl.classList.remove('tp-deal-new-record');

        if (stats && cardPrice > 0 && stats.tiefstpreis > 0) {
          const isAllTimeLow = cardPrice <= stats.tiefstpreis * 1.01;
          const isNonBest = !isAllTimeLow;
          const isNewRecord = !!(stats.isNewAllTimeLow || (isAllTimeLow && stats.previousLow && stats.previousLow > cardPrice * 1.01));
          const prevLow = stats.previousLow;
          const realDropVsPrev = prevLow && prevLow > cardPrice ? Math.round(((prevLow - cardPrice) / prevLow) * 100) : (stats.realDiscountVsPrevLow || 0);

          if (isNonBest && CONFIG.REAL_DEAL_FILTER_ACTIVE) {
            card.classList.add('tp-non-bestpreis-filtered');
          } else {
            card.classList.remove('tp-non-bestpreis-filtered');
          }

          const hasSignificantPeak = stats.hoechstpreis && stats.hoechstpreis > stats.tiefstpreis * 1.02;

          if (isAllTimeLow) {
            // 3B: Verified All-Time Low (Glowing Emerald Halo)
            badgeDifEl.classList.add('tp-deal-alltime-low', 'tp-deal-badge-interactive');
            badgeDifEl.classList.remove('tp-deal-not-low', 'tp-is-severe-markup', 'tp-deal-loading');
            
            let peakContext = '';
            if (hasSignificantPeak) {
              const peakDropPct = Math.round(((stats.hoechstpreis - cardPrice) / stats.hoechstpreis) * 100);
              peakContext = ` (-${peakDropPct}% vom Höchstpreis CHF ${stats.hoechstpreis.toFixed(2)})`;
            }

            let prevLowContext = '';
            if (isNewRecord && prevLow) {
              prevLowContext = ` | Bisheriger Rekord: CHF ${prevLow.toFixed(2)} (-${realDropVsPrev}%)`;
            }
            const avgContext = stats.avgPrice && stats.avgPrice > cardPrice ? ` | Ø-Preis: CHF ${stats.avgPrice.toFixed(2)}` : '';

            badgeDifEl.title = `🌟 ${isNewRecord ? 'Neuer Allzeit-Tiefstpreis' : 'Allzeit-Tiefstpreis'} (CHF ${cardPrice.toFixed(2)})!${prevLowContext}${avgContext}${peakContext} (Klicken zum Aktualisieren)`;
            badgeDifEl.innerHTML = `<div class="text">Differenz</div><p>-${rawDiscount}%</p>`;
          } else {
            // 2A: Verified Non-Tiefstpreis (Amber Alert Morph with Shrunken Strikethrough)
            const markupPct = Math.round(((cardPrice - stats.tiefstpreis) / stats.tiefstpreis) * 100);
            const isSevere = markupPct >= 50;

            badgeDifEl.classList.add('tp-deal-not-low', 'tp-deal-badge-interactive');
            badgeDifEl.classList.remove('tp-deal-alltime-low', 'tp-deal-loading');
            if (isSevere) {
              badgeDifEl.classList.add('tp-is-severe-markup');
            } else {
              badgeDifEl.classList.remove('tp-is-severe-markup');
            }

            const peakContext = hasSignificantPeak ? ` | Höchstpreis: CHF ${stats.hoechstpreis.toFixed(2)}` : '';
            badgeDifEl.title = `⚠️ Historischer Tiefstpreis lag bei CHF ${stats.tiefstpreis.toFixed(2)} (+${markupPct}% Aufschlag) | Schein-Rabatt: -${rawDiscount}%${peakContext} (Klicken zum Aktualisieren)`;
            badgeDifEl.innerHTML = `<div class="text">Aufschlag</div><p class="tp-markup-val">+${markupPct}%</p><span class="tp-fake-discount"><s>-${rawDiscount}%</s></span>`;
          }

          // 4A: Historical Tiefstpreis line right below current price
          let histPriceEl = card.querySelector('.tp-card-historical-price');
          if (isNonBest) {
            if (!histPriceEl) {
              histPriceEl = document.createElement('div');
              const priceContainer = card.querySelector('.Plugin_PriceInformation, .price_information_product') ||
                                     cardPriceEl?.closest('.priceContainer, .Plugin_PriceInformation, .price_information_product') ||
                                     cardPriceEl?.parentElement ||
                                     card;
              priceContainer.appendChild(histPriceEl);
            }
            histPriceEl.className = 'tp-card-historical-price tp-is-markup';
            histPriceEl.textContent = `Tiefstpreis: CHF ${stats.tiefstpreis.toFixed(2)}`;
            histPriceEl.title = `Historischer Tiefstpreis lag bei CHF ${stats.tiefstpreis.toFixed(2)} (+${Math.round(((cardPrice - stats.tiefstpreis) / stats.tiefstpreis) * 100)}% Aufschlag)`;
          } else if (isNewRecord && prevLow) {
            if (!histPriceEl) {
              histPriceEl = document.createElement('div');
              const priceContainer = card.querySelector('.Plugin_PriceInformation, .price_information_product') ||
                                     cardPriceEl?.closest('.priceContainer, .Plugin_PriceInformation, .price_information_product') ||
                                     cardPriceEl?.parentElement ||
                                     card;
              priceContainer.appendChild(histPriceEl);
            }
            histPriceEl.className = 'tp-card-historical-price tp-is-record-low';
            histPriceEl.textContent = `Bisher: CHF ${prevLow.toFixed(2)} (-${realDropVsPrev}%)`;
            histPriceEl.title = `Neuer Rekord-Tiefstpreis! Vorheriges Tief lag bei CHF ${prevLow.toFixed(2)}`;
          } else if (histPriceEl) {
            histPriceEl.remove();
          }
        } else {
          // 1A: Unchecked State (Subtle Mini Loupe + Hover Scale + Tooltip)
          card.classList.remove('tp-non-bestpreis-filtered');
          card.querySelector('.tp-card-historical-price')?.remove();

          badgeDifEl.classList.add('tp-deal-badge-interactive');
          badgeDifEl.classList.remove('tp-deal-alltime-low', 'tp-deal-not-low', 'tp-is-severe-markup', 'tp-deal-loading');
          badgeDifEl.title = `🔍 Klicken: Echten Allzeit-Tiefstpreis prüfen (-${rawDiscount}% Schein-Rabatt vs Realität)`;
          badgeDifEl.innerHTML = `<div class="text">Differenz</div><p>-${rawDiscount}%</p><span class="tp-badge-loupe-icon">🔍</span>`;
        }
      }
    } else {
      card.classList.remove('tp-non-bestpreis-filtered', 'tp-bestpreise-hidden');
      card.querySelector('.tp-card-historical-price')?.remove();
    }

    // 3.6 Mini Price-Trend Sparkline (Beta Feature)
    if (CONFIG.ENABLE_SPARKLINES && stats && Array.isArray(stats.timeSeries) && stats.timeSeries.length >= 2) {
      let sparkContainer = card.querySelector('.tp-sparkline-container');
      if (!sparkContainer) {
        sparkContainer = document.createElement('div');
        sparkContainer.className = 'tp-sparkline-container';
        const priceContainer = card.querySelector('.Plugin_PriceInformation, .price_information_product') ||
                               cardPriceEl?.closest('.priceContainer, .Plugin_PriceInformation, .price_information_product') ||
                               cardPriceEl?.parentElement ||
                               card;
        priceContainer.appendChild(sparkContainer);
      }
      if (!sparkContainer.querySelector('.tp-sparkline')) {
        const svg = renderSparkline(stats.timeSeries);
        if (svg) {
          sparkContainer.innerHTML = '';
          sparkContainer.appendChild(svg);
        }
      }
    } else {
      card.querySelector('.tp-sparkline-container')?.remove();
    }
  }

  function applySorting(cards, pageHasOffers) {
    if (CONFIG.BESTPREISE_MODE_ACTIVE && cards.length > 1) {
      const parent = cards[0].parentElement;
      if (parent) {
        const scored = Array.from(cards).map(c => {
          const cd = extractCardData(c);
          const tier = getBestpreiseTier(cd.stats, cd.cardPrice);
          return { card: c, score: tier?.score ?? -1 };
        });
        scored.sort((a, b) => b.score - a.score);
        scored.forEach(s => parent.appendChild(s.card));
      }
      return;
    }
    if (CONFIG.SORT_BY_OFFERS === 'discount-desc' && cards.length > 1) {
      const parent = cards[0].parentElement;
      if (parent) {
        Array.from(cards).sort((a, b) => (extractCardDiscount(b) ?? -1) - (extractCardDiscount(a) ?? -1)).forEach(c => parent.appendChild(c));
      }
    } else if (pageHasOffers && CONFIG.SORT_BY_OFFERS !== 'none' && cards.length > 1) {
      const parent = cards[0].parentElement;
      if (parent) {
        Array.from(cards).sort((a, b) => CONFIG.SORT_BY_OFFERS === 'desc' ? extractOfferCount(b) - extractOfferCount(a) : extractOfferCount(a) - extractOfferCount(b)).forEach(c => parent.appendChild(c));
      }
    }
  }

  function renderEmptyState(cards, counts) {
    const totalHidden = (counts.neg || 0) + (counts.cat || 0) + (counts.min || 0) + (counts.nonBest || 0) + (counts.bestpreiseHidden || 0);
    const isRevealed = document.body.classList.contains('tp-reveal-filtered');
    let emptyNotice = document.getElementById('tp-empty-state-notice');

    if (cards.length > 0 && totalHidden >= cards.length && !isRevealed) {
      if (!emptyNotice) {
        emptyNotice = document.createElement('div');
        emptyNotice.id = 'tp-empty-state-notice';
        emptyNotice.className = 'tp-empty-state-notice';
        const listParent = cards[0]?.parentElement;
        if (listParent) {
          listParent.insertBefore(emptyNotice, listParent.firstChild);
        }
      }
      const isBestpreiseEmpty = CONFIG.BESTPREISE_MODE_ACTIVE && (counts.bestpreiseHidden || 0) > 0;
      emptyNotice.innerHTML = `
        <div>🚫 <strong>${isBestpreiseEmpty ? 'Keine verifizierten Bestpreise auf dieser Seite gefunden.' : `Alle ${cards.length} Angebote auf dieser Seite sind durch aktive Filter ausgeblendet.`}</strong></div>
        <div class="tp-empty-state-actions">
          <button class="tp-empty-state-btn" id="tp-empty-reveal-btn">👁️ Ausgeblendete anzeigen</button>
          ${isBestpreiseEmpty ? '<button class="tp-empty-state-btn" id="tp-empty-disable-bestpreise-btn">💎 Bestpreise-Modus ausschalten</button>' : ''}
          ${counts.nonBest > 0 && !isBestpreiseEmpty ? '<button class="tp-empty-state-btn" id="tp-empty-disable-dealfilter-btn">🌟 Tiefstpreis-Filter ausschalten</button>' : ''}
          <button class="tp-empty-state-btn" id="tp-empty-reset-btn">🔄 Filter zurücksetzen</button>
        </div>
      `;
      emptyNotice.querySelector('#tp-empty-reveal-btn')?.addEventListener('click', () => {
        document.body.classList.toggle('tp-reveal-filtered');
        processListings();
      });
      emptyNotice.querySelector('#tp-empty-disable-bestpreise-btn')?.addEventListener('click', () => {
        saveConfigKey('BESTPREISE_MODE_ACTIVE', false);
        cancelBestpreiseScan();
        if (uiShadowRoot) {
          const modalToggle = uiShadowRoot.getElementById('tp-bestpreise-mode-toggle');
          if (modalToggle) modalToggle.checked = false;
        }
        processListings();
        showToast('Bestpreise-Modus deaktiviert');
      });
      emptyNotice.querySelector('#tp-empty-disable-dealfilter-btn')?.addEventListener('click', () => {
        saveConfigKey('REAL_DEAL_FILTER_ACTIVE', false);
        if (uiShadowRoot) {
          const modalToggle = uiShadowRoot.getElementById('tp-real-deal-filter-toggle');
          if (modalToggle) modalToggle.checked = false;
        }
        processListings();
        showToast('Tiefstpreis-Filter deaktiviert');
      });
      emptyNotice.querySelector('#tp-empty-reset-btn')?.addEventListener('click', resetAllFilters);
    } else if (emptyNotice) {
      emptyNotice.remove();
    }
  }

  function processListings() {
    if (isModifyingDOM) return;
    if (isProductDetailPage()) {
      const staleBar = document.getElementById('tp-suite-filter-bar');
      if (staleBar) staleBar.remove();
      return;
    }
    isModifyingDOM = true;
    try {
      const cards = getProductCards();
      if (cards.length === 0) {
        const staleBar = document.getElementById('tp-suite-filter-bar');
        if (staleBar) staleBar.remove();
        return;
      }

      // --- Extract ---
      const activeStores = extractActiveStores();
      const termsList = parseNegativeTerms();
      const excludedCats = CONFIG.EXCLUDED_CATEGORIES || [];
      const isNeueFeed = isNeueToppreisePage();
      const minDealDiscount = CONFIG.REAL_DEAL_MIN_DISCOUNT || 30;
      const cardDataList = cards.map(extractCardData);

      // --- Filter ---
      const counts = { neg: 0, cat: 0, min: 0, nonBest: 0, uncheckedDeals: 0, bestpreiseDeals: 0, bestpreiseHidden: 0 };
      const pageHasOffers = cardDataList.some(cd => cd.offerCount > 0);

      for (const cd of cardDataList) {
        cd.filters = applyCardFilters(cd, termsList, excludedCats, CONFIG.MIN_OFFERS, pageHasOffers);
        if (cd.filters.isNeg) counts.neg++;
        if (cd.filters.isCatExcluded) counts.cat++;
        if (cd.filters.isLowOffers) counts.min++;
        if (cd.pid && !cd.stats && cd.discountVal !== null && cd.discountVal >= minDealDiscount) {
          counts.uncheckedDeals++;
        }
        if (cd.isVerifiedNonBest && CONFIG.REAL_DEAL_FILTER_ACTIVE) {
          counts.nonBest++;
        }
        const tier = getBestpreiseTier(cd.stats, cd.cardPrice);
        if (tier) {
          counts.bestpreiseDeals++;
        } else if (CONFIG.BESTPREISE_MODE_ACTIVE) {
          counts.bestpreiseHidden++;
        }
      }

      // --- Render ---
      for (const cd of cardDataList) {
        renderCardEffects(cd, cd.filters, isNeueFeed, activeStores);
      }

      // --- Sort ---
      applySorting(cards, pageHasOffers);

      // --- Empty state & filter bar ---
      renderEmptyState(cards, counts);
      renderSuiteFilterBar(counts, pageHasOffers, isNeueFeed);
    } finally {
      isModifyingDOM = false;
    }
  }

  // ─── PRODUCT DETAIL PAGE REAL DEAL ──────────────────────────────────────────
  function isProductDetailPage() {
    return /\/preisvergleich\/[^/]+\/[^/]+-p(\d+)/i.test(location.href) ||
           /\/preisvergleich\/[^/]+\/[^/]+-p(\d+)/i.test(document.body?.getAttribute('data-current_url') || '') ||
           document.body?.classList.contains('Page_Product') ||
           document.body?.classList.contains('Page_DetailProduct') ||
           !!document.querySelector('.Page_DetailProduct, #Page_DetailProduct, .product_detail_page, .Page_Product') ||
           (!!document.querySelector('.Plugin_ProductHeading h1, .productHeading h1, .product_title h1, h1.productTitle') && !!getDetailProductId());
  }

  function getDetailProductId() {
    const match = location.href.match(/-p(\d+)/i) || (document.body?.getAttribute('data-current_url') || '').match(/-p(\d+)/i);
    if (match) return match[1];
    const chartLink = document.querySelector('a[href*="pricechart"], a[href*="p_pc_pid="]');
    if (chartLink) {
      const m = chartLink.href.match(/p_pc_pid=(\d+)/i);
      if (m) return m[1];
    }
    const chartForm = document.querySelector('form[action*="pricechart"] input[name*="pid"], input[name="p_pc_pid"]');
    if (chartForm && chartForm.value) return chartForm.value;
    return null;
  }

  function getDetailLowestPrice() {
    const priceEl = document.querySelector('.productPrice .Plugin_Price, .product_price .Plugin_Price, .lowestPrice .Plugin_Price, .priceComparison .Plugin_Price, .tableDealerPriceList .Plugin_Price, .Plugin_Price');
    return priceEl ? parsePrice(priceEl.textContent) : 0;
  }

  let isProcessingDetail = false;
  async function processProductDetailPage() {
    if (isProcessingDetail) return;
    const pid = getDetailProductId();
    if (!pid) return;

    const headingEl = document.querySelector('.Plugin_ProductHeading h1, .productHeading h1, .product_title h1, h1.productTitle, h1');
    if (!headingEl) return;

    const currentPrice = getDetailLowestPrice();
    if (currentPrice <= 0) return;

    let badge = document.getElementById('tp-detail-deal-badge');
    const stats = getCachedPriceStats(pid);

    if (stats && stats.tiefstpreis > 0) {
      if (!badge) {
        badge = document.createElement('div');
        badge.id = 'tp-detail-deal-badge';
        headingEl.appendChild(badge);
      }

      const isAllTimeLow = currentPrice <= stats.tiefstpreis * 1.01;
      const hasSignificantPeak = stats.hoechstpreis && stats.hoechstpreis > stats.tiefstpreis * 1.02;

      if (isAllTimeLow) {
        badge.className = 'tp-detail-deal-badge tp-is-alltime-low';
        let peakContext = '';
        if (hasSignificantPeak) {
          const peakDropPct = Math.round(((stats.hoechstpreis - currentPrice) / stats.hoechstpreis) * 100);
          peakContext = ` (-${peakDropPct}% vom Höchstpreis CHF ${stats.hoechstpreis.toFixed(2)})`;
        }
        badge.title = `Aktueller Bestpreis (CHF ${currentPrice.toFixed(2)}) ist der historische Allzeit-Tiefstpreis!${peakContext}`;
        badge.innerHTML = `🌟 Allzeit-Tiefstpreis`;
      } else {
        const markupPct = Math.round(((currentPrice - stats.tiefstpreis) / stats.tiefstpreis) * 100);
        const isSevere = markupPct >= 50;
        badge.className = `tp-detail-deal-badge tp-is-not-low ${isSevere ? 'tp-is-severe-markup' : ''}`;
        const peakContext = hasSignificantPeak ? ` | Höchstpreis: CHF ${stats.hoechstpreis.toFixed(2)}` : '';
        badge.title = `Historischer Tiefstpreis lag bei CHF ${stats.tiefstpreis.toFixed(2)} (+${markupPct}% Aufschlag)${peakContext}`;
        badge.innerHTML = `⚠️ Tiefstpreis: CHF ${stats.tiefstpreis.toFixed(2)} (+${markupPct}%)`;
      }
    } else if (!activeFetches.has(pid)) {
      isProcessingDetail = true;
      try {
        const fetchedStats = await fetchSingleProductPriceStats(pid);
        if (fetchedStats) {
          processProductDetailPage();
        }
      } finally {
        isProcessingDetail = false;
      }
    }
  }

  // ─── PRICE ALARM AUTOMATION ─────────────────────────────────────────────────
  function processPriceAlarmModal() {
    if (!CONFIG.ALARM_ENABLED) return;
    const modalContainer = document.querySelector('.Plugin_NewInfoMailForm');
    if (!modalContainer || modalContainer.dataset.tpAlarmProcessed === 'true') return;
    modalContainer.dataset.tpAlarmProcessed = 'true';

    const priceEl = modalContainer.querySelector('.shippingPrice .Plugin_Price') ||
                    modalContainer.querySelector('.productPrice .Plugin_Price') ||
                    document.querySelector('.pageContent .priceContainer .Plugin_Price');
    if (!priceEl) return;

    const presentValue = parsePrice(priceEl.textContent);
    if (presentValue <= 0) return;

    const targetPrice = (presentValue * CONFIG.ALARM_TARGET_PERCENT).toFixed(2);
    const priceInput = modalContainer.querySelector('input#f_NewInfoMailForm_priceFrom') || modalContainer.querySelector('input[name="im_nimf_pvf"]');
    if (priceInput) {
      priceInput.value = targetPrice;
      priceInput.dispatchEvent(new Event('input', { bubbles: true }));
      priceInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const durationHidden = modalContainer.querySelector('input[name="im_nimf_du"]');
    if (durationHidden) {
      durationHidden.value = CONFIG.ALARM_DURATION_DAYS;
      durationHidden.dispatchEvent(new Event('change', { bubbles: true }));
    }
    modalContainer.querySelector(`li[data-value="${CONFIG.ALARM_DURATION_DAYS}"]`)?.click();

    const termsCheckbox = modalContainer.querySelector('input#im_nimf_prtrm');
    if (termsCheckbox) {
      termsCheckbox.checked = true;
      termsCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
    }

    if (CONFIG.ALARM_AUTO_SUBMIT) {
      const submitDelay = Math.max(0, CONFIG.ALARM_SUBMIT_DELAY_MS ?? 300);
      const closeDelay = Math.max(0, CONFIG.ALARM_CLOSE_DELAY_MS ?? 800);
      setTimeout(() => {
        const submitBtn = modalContainer.querySelector('input.f_submitbtn');
        if (submitBtn) {
          submitBtn.click();
          // Allow in-flight AJAX request to complete before closing the dialog container
          setTimeout(() => {
            const closeBtn = modalContainer.closest('.AbstractDialog')?.querySelector('.AbstractDialog_CloseButton') ||
                             document.querySelector('#tmpAbstractDialogContainer .AbstractDialog_CloseButton');
            if (closeBtn) closeBtn.click();
          }, closeDelay);
        }
      }, submitDelay);
    }
  }

  // ─── UNIFIED SETTINGS UI IN SHADOW DOM ─────────────────────────────────────
  let uiShadowRoot = null;

  function showToast(message, durationMs = 2500, actionLabel = null, onAction = null) {
    ensureSkeleton();
    const container = uiShadowRoot?.getElementById('tp-toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'tp-toast';
    const textSpan = document.createElement('span');
    textSpan.textContent = message;
    toast.appendChild(textSpan);

    if (actionLabel && typeof onAction === 'function') {
      const actionBtn = document.createElement('button');
      actionBtn.type = 'button';
      actionBtn.className = 'tp-toast-undo';
      actionBtn.textContent = actionLabel;
      actionBtn.onclick = e => {
        e.stopPropagation();
        toast.remove();
        onAction();
      };
      toast.appendChild(actionBtn);
    }

    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 400);
    }, durationMs);
  }

  function ensureSkeleton() {
    let host = document.getElementById('tp-root');
    if (!host) {
      host = document.createElement('div');
      host.id = 'tp-root';
      document.body.appendChild(host);
    }
    const shadow = host.shadowRoot || host.attachShadow({ mode: 'open' });
    uiShadowRoot = shadow;

    if (!shadow.getElementById('tp-settings-fab')) {
      shadow.innerHTML = `
        <style>${SHADOW_MODAL_STYLES}</style>
        <button id="tp-settings-fab" type="button" title="Toppreise Suite Einstellungen öffnen" aria-label="Toppreise Suite Einstellungen">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
        <dialog id="tp-settings-dialog" role="dialog" aria-modal="true" aria-labelledby="tp-settings-title">
          <h3 id="tp-settings-title">Toppreise Suite Einstellungen</h3>
          <div id="tp-settings-sections"></div>
          <div class="tp-modal-actions">
            <button type="button" class="tp-btn tp-btn-secondary" id="tp-btn-close">Abbrechen</button>
            <button type="button" class="tp-btn tp-btn-primary" id="tp-btn-save">Speichern</button>
          </div>
        </dialog>
        <div id="tp-toast-container"></div>
      `;
    }
    return { shadow };
  }

  function setupUI() {
    const { shadow } = ensureSkeleton();
    let section = shadow.getElementById('tp-section-unified-suite');
    if (!section) {
      const sectionsHolder = shadow.getElementById('tp-settings-sections');
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = `
        <div id="tp-section-unified-suite">
          <div class="tp-section-header">1. Händler Bestpreis Highlights</div>
          <div class="tp-settings-group">
            <label>Filter Modus</label>
            <div class="tp-segmented-control">
              <input type="radio" id="tp-mode-highlight-only" name="tp-mode" value="highlight-only">
              <label for="tp-mode-highlight-only">Highlight</label>
              <input type="radio" id="tp-mode-dim" name="tp-mode" value="dim">
              <label for="tp-mode-dim">Dimmen</label>
              <input type="radio" id="tp-mode-hide" name="tp-mode" value="hide">
              <label for="tp-mode-hide">Verbergen</label>
            </div>
          </div>
          <div class="tp-settings-group">
            <label>Preis-Toleranz (%)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-margin-range" min="0" max="15" step="0.5" value="0">
              <input type="number" id="tp-margin-val" min="0" max="100" step="0.1" value="0">
            </div>
          </div>
          <div class="tp-settings-group" id="tp-dim-opacity-group">
            <label>Deckkraft / Dimmung (Gedimmt & Gefiltert)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-opacity-range" min="0.05" max="0.95" step="0.05" value="0.25">
              <input type="number" id="tp-opacity-val" min="5" max="95" step="5" value="25">
            </div>
          </div>
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label"><label>inkl. Versandkosten vergleichen</label></div>
            <label class="tp-switch">
              <input type="checkbox" id="tp-shipping-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>
          <div class="tp-section-header">2. Negativer Textfilter (Ausschluss)</div>
          <div class="tp-settings-group">
            <label>Auszuschließende Begriffe (Kommagetrennt)</label>
            <textarea id="tp-negative-terms-input" class="tp-textarea" placeholder="z. B. Hülle, Case, Refurbished, Gebraucht"></textarea>
          </div>
          <div class="tp-section-header">3. Angebote & Sortierung</div>
          <div class="tp-settings-group">
            <label>Mindestanzahl Angebote (0 = Aus)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-min-offers-range" min="0" max="15" step="1" value="0">
              <input type="number" id="tp-min-offers-val" min="0" max="50" step="1" value="0">
            </div>
          </div>
          <div class="tp-settings-group">
            <label>Sortierung nach Angeboten / Rabatt</label>
            <div class="tp-segmented-control">
              <input type="radio" id="tp-sort-none" name="tp-sort-offers" value="none">
              <label for="tp-sort-none">Standard</label>
              <input type="radio" id="tp-sort-desc" name="tp-sort-offers" value="desc">
              <label for="tp-sort-desc">Meiste ⬇</label>
              <input type="radio" id="tp-sort-asc" name="tp-sort-offers" value="asc">
              <label for="tp-sort-asc">Wenigste ⬆</label>
              <input type="radio" id="tp-sort-discount" name="tp-sort-offers" value="discount-desc">
              <label for="tp-sort-discount">% Rabatt ⬇</label>
            </div>
          </div>
          <div class="tp-section-header" style="color: #3b82f6;">4. Preisalarm Auto-Filler</div>
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>Preisalarm Auto-Fill aktivieren</label>
              <span class="tp-switch-desc">Beim Klick auf die Glocke Formular automatisch ausfüllen</span>
            </div>
            <label class="tp-switch tp-blue">
              <input type="checkbox" id="tp-alarm-enabled-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>
          <div class="tp-settings-group">
            <label>Zielpreis (% vom aktuellen Preis)</label>
            <div class="tp-range-container tp-blue">
              <input type="range" id="tp-alarm-target-range" min="10" max="95" step="5" value="60">
              <input type="number" id="tp-alarm-target-val" min="1" max="99" step="1" value="60">
            </div>
          </div>
          <div class="tp-settings-group">
            <label>Laufzeit Dauer</label>
            <div class="tp-segmented-control tp-segmented-control-blue">
              <input type="radio" id="tp-dur-90" name="tp-alarm-duration" value="90"><label for="tp-dur-90">3 Monate</label>
              <input type="radio" id="tp-dur-180" name="tp-alarm-duration" value="180"><label for="tp-dur-180">6 Monate</label>
              <input type="radio" id="tp-dur-365" name="tp-alarm-duration" value="365"><label for="tp-dur-365">1 Jahr</label>
              <input type="radio" id="tp-dur-730" name="tp-alarm-duration" value="730"><label for="tp-dur-730">2 Jahre</label>
            </div>
          </div>
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>Automatisch Absenden & Schließen</label>
              <span class="tp-switch-desc">Formular direkt einreichen und Dialog schließen</span>
            </div>
            <label class="tp-switch tp-blue">
              <input type="checkbox" id="tp-alarm-autosubmit-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>
          <div class="tp-settings-group" id="tp-alarm-delays-group">
            <label>Submit-Verzögerung (ms)</label>
            <div class="tp-range-container tp-blue">
              <input type="range" id="tp-alarm-submit-delay-range" min="0" max="2000" step="50" value="300">
              <input type="number" id="tp-alarm-submit-delay-val" min="0" max="5000" step="50" value="300">
            </div>
            <label style="margin-top: 8px;">Schließ-Verzögerung nach Submit (ms)</label>
            <div class="tp-range-container tp-blue">
              <input type="range" id="tp-alarm-close-delay-range" min="0" max="3000" step="50" value="800">
              <input type="number" id="tp-alarm-close-delay-val" min="0" max="10000" step="50" value="800">
            </div>
          </div>
          <div class="tp-section-header" style="color: #f43f5e;">5. Rabatt-Heatmap</div>
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>Rabatt-Heatmap aktivieren</label>
              <span class="tp-switch-desc">Kartenhintergrund färbt sich nach % Rabatt</span>
            </div>
            <label class="tp-switch tp-rose">
              <input type="checkbox" id="tp-heatmap-enabled-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>
          <div class="tp-settings-group">
            <label>Heatmap-Intensität (%)</label>
            <div class="tp-range-container tp-rose">
              <input type="range" id="tp-heatmap-intensity-range" min="20" max="100" step="5" value="100">
              <input type="number" id="tp-heatmap-intensity-val" min="20" max="100" step="5" value="100">
            </div>
          </div>
          <div class="tp-section-header" style="color: #10b981;">6. Real Deals & Allzeit-Tiefstpreise</div>
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>💎 Neue Bestpreise Modus</label>
              <span class="tp-switch-desc">Auto-Scan + Tier-Ranking auf der Deal-Feed-Seite</span>
            </div>
            <label class="tp-switch tp-purple">
              <input type="checkbox" id="tp-bestpreise-mode-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>Nur echte Tiefstpreise filtern</label>
              <span class="tp-switch-desc">Verifizierte Nicht-Bestpreise im Feed ausblenden</span>
            </div>
            <label class="tp-switch">
              <input type="checkbox" id="tp-real-deal-filter-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>
          <div class="tp-settings-group">
            <label>Mindest-Rabatt für Batch-Check (%)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-real-deal-min-range" min="10" max="70" step="5" value="30">
              <input type="number" id="tp-real-deal-min-val" min="5" max="95" step="5" value="30">
            </div>
          </div>
          <div class="tp-section-header" style="color: #8b5cf6;">7. Experimentell / Beta</div>
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>Mini-Preiskurven (Sparklines) anzeigen</label>
              <span class="tp-switch-desc">Erfordert zusätzliche Server-Abfragen pro Produkt</span>
            </div>
            <label class="tp-switch tp-purple">
              <input type="checkbox" id="tp-sparklines-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>
          <div class="tp-section-header" style="color: #6366f1;">8. Import / Export</div>
          <div class="tp-settings-group" style="display: flex; flex-direction: row; gap: 8px;">
            <button type="button" id="tp-export-config-btn" class="tp-btn tp-btn-secondary" style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;">📥 Export (JSON)</button>
            <button type="button" id="tp-import-config-btn" class="tp-btn tp-btn-secondary" style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;">📤 Import (JSON)</button>
            <input type="file" id="tp-import-config-file" accept=".json" style="display: none;">
          </div>
        </div>
      `;
      section = tempDiv.firstElementChild;
      sectionsHolder.appendChild(section);
    }

    const dialog = shadow.getElementById('tp-settings-dialog');
    const fabButton = shadow.getElementById('tp-settings-fab');
    const btnClose = shadow.getElementById('tp-btn-close');
    const btnSave = shadow.getElementById('tp-btn-save');

    const modeHighlight = shadow.getElementById('tp-mode-highlight-only');
    const modeDim = shadow.getElementById('tp-mode-dim');
    const modeHide = shadow.getElementById('tp-mode-hide');
    const marginRange = shadow.getElementById('tp-margin-range');
    const marginVal = shadow.getElementById('tp-margin-val');
    const opacityRange = shadow.getElementById('tp-opacity-range');
    const opacityVal = shadow.getElementById('tp-opacity-val');
    const shippingToggle = shadow.getElementById('tp-shipping-toggle');
    const negTermsInput = shadow.getElementById('tp-negative-terms-input');
    const minOffersRange = shadow.getElementById('tp-min-offers-range');
    const minOffersVal = shadow.getElementById('tp-min-offers-val');
    const sortNone = shadow.getElementById('tp-sort-none');
    const sortDesc = shadow.getElementById('tp-sort-desc');
    const sortAsc = shadow.getElementById('tp-sort-asc');
    const sortDiscount = shadow.getElementById('tp-sort-discount');
    const alarmEnabledToggle = shadow.getElementById('tp-alarm-enabled-toggle');
    const alarmTargetRange = shadow.getElementById('tp-alarm-target-range');
    const alarmTargetVal = shadow.getElementById('tp-alarm-target-val');
    const alarmAutoSubmitToggle = shadow.getElementById('tp-alarm-autosubmit-toggle');
    const alarmSubmitDelayRange = shadow.getElementById('tp-alarm-submit-delay-range');
    const alarmSubmitDelayVal = shadow.getElementById('tp-alarm-submit-delay-val');
    const alarmCloseDelayRange = shadow.getElementById('tp-alarm-close-delay-range');
    const alarmCloseDelayVal = shadow.getElementById('tp-alarm-close-delay-val');
    const alarmDelaysGroup = shadow.getElementById('tp-alarm-delays-group');
    const heatmapEnabledToggle = shadow.getElementById('tp-heatmap-enabled-toggle');
    const heatmapIntensityRange = shadow.getElementById('tp-heatmap-intensity-range');
    const heatmapIntensityVal = shadow.getElementById('tp-heatmap-intensity-val');
    const realDealFilterToggle = shadow.getElementById('tp-real-deal-filter-toggle');
    const bestpreiseModeToggle = shadow.getElementById('tp-bestpreise-mode-toggle');
    const realDealMinRange = shadow.getElementById('tp-real-deal-min-range');
    const realDealMinVal = shadow.getElementById('tp-real-deal-min-val');
    const sparklinesToggle = shadow.getElementById('tp-sparklines-toggle');
    const dur90 = shadow.getElementById('tp-dur-90');
    const dur180 = shadow.getElementById('tp-dur-180');
    const dur365 = shadow.getElementById('tp-dur-365');
    const dur730 = shadow.getElementById('tp-dur-730');

    const exportBtn = shadow.getElementById('tp-export-config-btn');
    const importBtn = shadow.getElementById('tp-import-config-btn');
    const importFile = shadow.getElementById('tp-import-config-file');

    function syncFieldsFromConfig() {
      if (CONFIG.MODE === 'highlight-only') modeHighlight.checked = true;
      else if (CONFIG.MODE === 'hide') modeHide.checked = true;
      else modeDim.checked = true;

      marginRange.value = CONFIG.MARGIN_PERCENT;
      marginVal.value = CONFIG.MARGIN_PERCENT;
      opacityRange.value = CONFIG.DIM_OPACITY;
      opacityVal.value = Math.round(CONFIG.DIM_OPACITY * 100);
      shippingToggle.checked = CONFIG.USE_SHIPPING_PRICE;
      negTermsInput.value = CONFIG.NEGATIVE_TERMS || '';
      minOffersRange.value = CONFIG.MIN_OFFERS || 0;
      minOffersVal.value = CONFIG.MIN_OFFERS || 0;

      if (CONFIG.SORT_BY_OFFERS === 'desc') sortDesc.checked = true;
      else if (CONFIG.SORT_BY_OFFERS === 'asc') sortAsc.checked = true;
      else if (CONFIG.SORT_BY_OFFERS === 'discount-desc') sortDiscount.checked = true;
      else sortNone.checked = true;

      alarmEnabledToggle.checked = CONFIG.ALARM_ENABLED !== false;
      const targetPct = Math.round(CONFIG.ALARM_TARGET_PERCENT * 100);
      alarmTargetRange.value = targetPct;
      alarmTargetVal.value = targetPct;

      const dur = String(CONFIG.ALARM_DURATION_DAYS);
      if (dur === '90') dur90.checked = true;
      else if (dur === '180') dur180.checked = true;
      else if (dur === '365') dur365.checked = true;
      else dur730.checked = true;

      alarmAutoSubmitToggle.checked = CONFIG.ALARM_AUTO_SUBMIT !== false;
      if (alarmSubmitDelayRange && alarmSubmitDelayVal) {
        alarmSubmitDelayRange.value = CONFIG.ALARM_SUBMIT_DELAY_MS ?? 300;
        alarmSubmitDelayVal.value = CONFIG.ALARM_SUBMIT_DELAY_MS ?? 300;
      }
      if (alarmCloseDelayRange && alarmCloseDelayVal) {
        alarmCloseDelayRange.value = CONFIG.ALARM_CLOSE_DELAY_MS ?? 800;
        alarmCloseDelayVal.value = CONFIG.ALARM_CLOSE_DELAY_MS ?? 800;
      }
      if (alarmDelaysGroup) {
        alarmDelaysGroup.style.display = alarmAutoSubmitToggle.checked ? 'block' : 'none';
      }

      heatmapEnabledToggle.checked = CONFIG.HEATMAP_ENABLED !== false;
      const heatIntensityPct = Math.round((CONFIG.HEATMAP_INTENSITY ?? 1.0) * 100);
      heatmapIntensityRange.value = heatIntensityPct;
      heatmapIntensityVal.value = heatIntensityPct;

      if (bestpreiseModeToggle) bestpreiseModeToggle.checked = CONFIG.BESTPREISE_MODE_ACTIVE === true;
      if (realDealFilterToggle) realDealFilterToggle.checked = CONFIG.REAL_DEAL_FILTER_ACTIVE === true;
      if (realDealMinRange) realDealMinRange.value = CONFIG.REAL_DEAL_MIN_DISCOUNT || 30;
      if (realDealMinVal) realDealMinVal.value = CONFIG.REAL_DEAL_MIN_DISCOUNT || 30;
      if (sparklinesToggle) sparklinesToggle.checked = CONFIG.ENABLE_SPARKLINES === true;
    }

    const bindDual = (rangeEl, numEl, scale = 1, onInput = null) => {
      if (!rangeEl || !numEl) return;
      rangeEl.addEventListener('input', e => {
        numEl.value = Math.round(parseFloat(e.target.value) * scale);
        onInput?.(parseFloat(e.target.value));
      });
      numEl.addEventListener('input', e => {
        const val = (parseFloat(e.target.value) || 0) / scale;
        rangeEl.value = val;
        onInput?.(val);
      });
    };

    bindDual(marginRange, marginVal, 1);
    bindDual(opacityRange, opacityVal, 100, val => document.documentElement.style.setProperty('--tp-dim-opacity', val));
    bindDual(minOffersRange, minOffersVal, 1);
    bindDual(alarmTargetRange, alarmTargetVal, 1);
    bindDual(alarmSubmitDelayRange, alarmSubmitDelayVal, 1);
    bindDual(alarmCloseDelayRange, alarmCloseDelayVal, 1);
    bindDual(heatmapIntensityRange, heatmapIntensityVal, 1);
    bindDual(realDealMinRange, realDealMinVal, 1);

    alarmAutoSubmitToggle?.addEventListener('change', () => {
      if (alarmDelaysGroup) {
        alarmDelaysGroup.style.display = alarmAutoSubmitToggle.checked ? 'block' : 'none';
      }
    });

    exportBtn?.addEventListener('click', () => {
      const exportData = {
        _meta: {
          version: (typeof GM_info !== 'undefined' && GM_info?.script?.version) || '2.16.0',
          exported: new Date().toISOString()
        },
        config: { ...CONFIG }
      };
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `toppreise-suite-config-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast('Einstellungen exportiert');
    });

    importBtn?.addEventListener('click', () => {
      importFile?.click();
    });

    importFile?.addEventListener('change', e => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(reader.result);
          const importConfig = data.config || data;
          let count = 0;
          for (const [key, val] of Object.entries(importConfig)) {
            if (key in DEFAULTS && key !== 'DEBUG') {
              saveConfigKey(key, val);
              count++;
            }
          }
          updateBodyClasses();
          processListings();
          syncFieldsFromConfig();
          showToast(`${count} Einstellungen importiert`);
        } catch (err) {
          showToast('Import fehlgeschlagen: Ungültige JSON-Datei');
        }
      };
      reader.readAsText(file);
      e.target.value = '';
    });

    const openModal = () => {
      syncFieldsFromConfig();
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
    };

    const closeModal = () => {
      document.documentElement.style.setProperty('--tp-dim-opacity', CONFIG.DIM_OPACITY);
      if (typeof dialog.close === 'function') dialog.close();
      else dialog.removeAttribute('open');
    };

    fabButton.addEventListener('click', openModal);
    btnClose.addEventListener('click', closeModal);
    shadow.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

    btnSave.addEventListener('click', () => {
      const checkedModeEl = shadow.querySelector('input[name="tp-mode"]:checked');
      if (checkedModeEl) saveConfigKey('MODE', checkedModeEl.value);

      saveConfigKey('MARGIN_PERCENT', Math.max(0, Math.min(100, parseFloat(marginVal.value) || 0)));
      saveConfigKey('DIM_OPACITY', Math.max(0.05, Math.min(0.95, parseFloat(opacityRange.value) || 0.25)));
      saveConfigKey('USE_SHIPPING_PRICE', shippingToggle.checked);
      saveConfigKey('NEGATIVE_TERMS', negTermsInput.value.trim());
      saveConfigKey('MIN_OFFERS', Math.max(0, parseInt(minOffersVal.value) || 0));

      const checkedSort = shadow.querySelector('input[name="tp-sort-offers"]:checked');
      if (checkedSort) saveConfigKey('SORT_BY_OFFERS', checkedSort.value);

      saveConfigKey('ALARM_ENABLED', alarmEnabledToggle.checked);
      saveConfigKey('ALARM_TARGET_PERCENT', Math.max(0.05, Math.min(0.99, (parseInt(alarmTargetVal.value) || 60) / 100)));

      const checkedDur = shadow.querySelector('input[name="tp-alarm-duration"]:checked');
      if (checkedDur) saveConfigKey('ALARM_DURATION_DAYS', checkedDur.value);

      saveConfigKey('ALARM_AUTO_SUBMIT', alarmAutoSubmitToggle.checked);
      if (alarmSubmitDelayVal) {
        saveConfigKey('ALARM_SUBMIT_DELAY_MS', Math.max(0, parseInt(alarmSubmitDelayVal.value) ?? 300));
      }
      if (alarmCloseDelayVal) {
        saveConfigKey('ALARM_CLOSE_DELAY_MS', Math.max(0, parseInt(alarmCloseDelayVal.value) ?? 800));
      }
      saveConfigKey('HEATMAP_ENABLED', heatmapEnabledToggle.checked);
      saveConfigKey('HEATMAP_INTENSITY', Math.max(0.2, Math.min(1.0, (parseInt(heatmapIntensityVal.value) || 100) / 100)));

      if (bestpreiseModeToggle) {
        const wasActive = CONFIG.BESTPREISE_MODE_ACTIVE;
        const nowActive = bestpreiseModeToggle.checked;
        saveConfigKey('BESTPREISE_MODE_ACTIVE', nowActive);
        if (nowActive && !wasActive) {
          runBestpreiseScan();
        } else if (!nowActive && wasActive) {
          cancelBestpreiseScan();
        }
      }
      if (realDealFilterToggle) saveConfigKey('REAL_DEAL_FILTER_ACTIVE', realDealFilterToggle.checked);
      if (realDealMinVal) saveConfigKey('REAL_DEAL_MIN_DISCOUNT', Math.max(5, Math.min(95, parseInt(realDealMinVal.value) || 30)));
      if (sparklinesToggle) saveConfigKey('ENABLE_SPARKLINES', sparklinesToggle.checked);

      updateBodyClasses();
      processListings();
      showToast('Toppreise Suite Einstellungen gespeichert');
      closeModal();
    });
  }

  // ─── OBSERVER & INITIALIZATION ───────────────────────────────────────────────
  let debounceTimer = null;
  const observer = new MutationObserver(mutations => {
    if (isModifyingDOM) return;
    if (mutations.every(m => m.target?.id === 'tp-root' || m.target?.closest?.('#tp-root'))) return;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      processListings();
      processPriceAlarmModal();
      if (isProductDetailPage()) {
        processProductDetailPage();
      }
    }, CONFIG.OBSERVER_DEBOUNCE_MS);
  });

  observer.observe(document.documentElement, { childList: true, subtree: true });

  document.addEventListener('keydown', e => {
    // Skip if modifier keys other than none
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    // Skip if user is typing in an input/textarea/select or contenteditable
    const tag = document.activeElement?.tagName;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || document.activeElement?.isContentEditable) return;
    // Skip if inside shadow root (settings modal)
    if (document.activeElement?.shadowRoot || uiShadowRoot?.activeElement) return;

    if (e.key === '/') {
      const input = document.getElementById('tp-inline-negative-input');
      if (input) {
        e.preventDefault();
        input.focus();
        input.select();
      }
    } else if (e.key === 'Escape') {
      const input = document.getElementById('tp-inline-negative-input');
      if (input && document.activeElement === input) {
        input.blur();
      }
    }
  });

  if (self.navigation?.addEventListener) {
    self.navigation.addEventListener('navigatesuccess', () => {
      processListings();
      processPriceAlarmModal();
      if (isProductDetailPage()) {
        processProductDetailPage();
      }
    });
  }

  setupUI();
  processListings();
  processPriceAlarmModal();
  if (isProductDetailPage()) {
    processProductDetailPage();
  }

  if (typeof window !== 'undefined') {
    window.ToppreiseSuite = {
      processListings,
      processProductDetailPage,
      processPriceAlarmModal,
      getBestpreiseTier,
      runBestpreiseScan,
      cancelBestpreiseScan,
      CONFIG
    };
  }
})();
