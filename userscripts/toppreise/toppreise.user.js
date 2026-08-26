// ==UserScript==
// @name         Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler
// @namespace    https://github.com/tazztone/scripts
// @version      2.11.2
// @description  All-in-one suite for Toppreise.ch: Highlights best prices, discount heatmap, excludes negative keywords, filters categories, sorts/filters by offer count/discount, and automates price alarms.
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
  // Best Price & Highlighting
  MODE: 'dim',
  MARGIN_PERCENT: 0.0,
  DIM_OPACITY: 0.25,
  USE_SHIPPING_PRICE: true,

  // Discount Heatmap
  HEATMAP_ENABLED: true,
  HEATMAP_INTENSITY: 1.0,
  HEATMAP_CURVE: 'calibrated',

  // Power Filters
  NEGATIVE_TERMS: '',
  EXCLUDED_CATEGORIES: [],
  MIN_OFFERS: 0,
  SORT_BY_OFFERS: 'none', // 'none', 'desc', 'asc', 'discount-desc'

  // Price Alarm Automation
  ALARM_ENABLED: true,
  ALARM_TARGET_PERCENT: 0.60, // 60% of present value
  ALARM_DURATION_DAYS: "730",  // 2 years (730 days)
  ALARM_AUTO_SUBMIT: true,

  // System
  OBSERVER_DEBOUNCE_MS: 200,
  DEBUG: true
};

// ─── STYLES ──────────────────────────────────────────────────────────────────
const STYLES = `
  /* Discount Heatmap Cards */
  .Plugin_Product.tp-heatmap-active {
    background: var(--tp-heat-bg) !important;
    border: 1.5px solid var(--tp-heat-border) !important;
    box-shadow: var(--tp-heat-glow, 0 2px 8px rgba(0, 0, 0, 0.25)) !important;
    transition: background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, transform 0.2s ease, filter 0.2s ease !important;
  }
  .Plugin_Product.tp-heatmap-active:hover {
    filter: brightness(1.15) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35), var(--tp-heat-glow, none) !important;
  }
  .Plugin_Product.tp-heatmap-active .badge.badge-dif {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 10px var(--tp-heat-border) !important;
    transition: box-shadow 0.3s ease !important;
  }

  /* Glow and border for products with best price */
  .Plugin_Product.mixedBrowsingList.tp-is-cheapest {
    border: 2px solid #10b981 !important;
    border-radius: 8px !important;
    position: relative !important;
    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15) !important;
    transition: all 0.3s ease !important;
  }
  .Plugin_Product.mixedBrowsingList.tp-is-cheapest.tp-heatmap-active {
    border: 2px solid #10b981 !important;
    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.25), var(--tp-heat-glow, none) !important;
  }
  
  /* Best Price Badge styling */
  .tp-best-price-badge {
    position: absolute;
    top: 12px;
    right: 50px;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 20px;
    text-transform: uppercase;
    z-index: 10;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
    letter-spacing: 0.5px;
    pointer-events: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }

  /* Dim mode actions */
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

  /* Hide mode actions */
  .tp-mode-hide .Plugin_Product.mixedBrowsingList.tp-not-cheapest,
  .tp-mode-hide .Plugin_Product.mixedBrowsingList.tp-no-store-offer {
    display: none !important;
  }

  /* Additional Filter Hide Rules */
  .tp-negative-filtered,
  .tp-category-filtered,
  .tp-min-offers-filtered {
    display: none !important;
  }

  /* Temporary reveal mode for filtered elements */
  body.tp-reveal-filtered .tp-negative-filtered,
  body.tp-reveal-filtered .tp-category-filtered,
  body.tp-reveal-filtered .tp-min-offers-filtered {
    display: block !important;
    opacity: var(--tp-dim-opacity, 0.25) !important;
    filter: grayscale(40%) !important;
    outline: 2px dashed #f59e0b !important;
    outline-offset: -2px !important;
    transition: opacity 0.3s ease, filter 0.3s ease !important;
  }
  body.tp-reveal-filtered .tp-negative-filtered:hover,
  body.tp-reveal-filtered .tp-category-filtered:hover,
  body.tp-reveal-filtered .tp-min-offers-filtered:hover {
    opacity: 0.6 !important;
    filter: grayscale(10%) !important;
  }

  /* 1-Click Card Quick-Block Category Action Button (Bottom-Left Overlay) */
  .tp-card-quick-block {
    position: absolute !important;
    bottom: 1px !important;
    left: 8px !important;
    background: rgba(15, 23, 42, 0.92) !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(244, 63, 94, 0.5) !important;
    color: #fda4af !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    padding: 3px 8px !important;
    border-radius: 6px !important;
    cursor: pointer !important;
    opacity: 0 !important;
    transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), background 0.2s ease !important;
    z-index: 9999 !important;
    pointer-events: auto !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 4px !important;
    text-decoration: none !important;
    user-select: none !important;
    max-width: 160px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
  }
  .Plugin_Product:hover .tp-card-quick-block,
  .mixedBrowsingListProduct:hover .tp-card-quick-block {
    opacity: 1 !important;
    z-index: 9999 !important;
  }
  .tp-card-quick-block:hover {
    background: #e11d48 !important;
    border-color: #f43f5e !important;
    color: #ffffff !important;
    transform: scale(1.04) !important;
    box-shadow: 0 4px 12px rgba(225, 29, 72, 0.5) !important;
    z-index: 10000 !important;
  }
  @media (hover: none) {
    .tp-card-quick-block {
      opacity: 0.85 !important;
    }
  }

  /* Compact Consolidated Power Filter Bar */
  #tp-suite-filter-bar {
    margin: 8px auto 12px auto !important;
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    padding: 8px 12px !important;
    color: #f8fafc !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2) !important;
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
    width: 100% !important;
    box-sizing: border-box !important;
    flex-wrap: wrap !important;
  }

  .tp-filter-badge {
    font-size: 13px !important;
    font-weight: 700 !important;
    color: #10b981 !important;
    display: flex !important;
    align-items: center !important;
    user-select: none !important;
    flex-shrink: 0 !important;
  }

  .tp-input-wrapper {
    flex: 1 1 200px !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }

  .tp-input-label-inline {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #94a3b8 !important;
    white-space: nowrap !important;
    user-select: none !important;
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
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
    min-width: 0 !important;
    background: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #fff !important;
    padding: 6px 26px 6px 10px !important;
    font-size: 12px !important;
    outline: none !important;
    transition: border-color 0.2s ease !important;
    box-sizing: border-box !important;
  }
  #tp-inline-negative-input:focus {
    border-color: #10b981 !important;
  }

  #tp-clear-neg-btn {
    position: absolute !important;
    right: 8px !important;
    background: transparent !important;
    border: none !important;
    color: #64748b !important;
    font-size: 12px !important;
    cursor: pointer !important;
    padding: 2px 6px !important;
    border-radius: 50% !important;
  }
  #tp-clear-neg-btn:hover {
    color: #f43f5e !important;
  }

  /* Control buttons in Top Bar */
  .tp-bar-btn {
    background: rgba(51, 65, 85, 0.6) !important;
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
    transition: all 0.2s ease !important;
    user-select: none !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
  }
  .tp-bar-btn:hover {
    background: #334155 !important;
    color: #fff !important;
  }
  .tp-bar-btn.tp-active {
    background: rgba(16, 185, 129, 0.2) !important;
    border-color: rgba(16, 185, 129, 0.4) !important;
    color: #34d399 !important;
  }

  .tp-bar-stepper-group {
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid #334155 !important;
    padding: 2px 6px !important;
    border-radius: 8px !important;
    font-size: 11px !important;
    color: #94a3b8 !important;
    user-select: none !important;
    flex-shrink: 0 !important;
  }
  .tp-stepper-btn {
    width: 20px !important;
    height: 20px !important;
    border-radius: 50% !important;
    background: rgba(255, 255, 255, 0.1) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    color: #fff !important;
    font-weight: 700 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    font-size: 11px !important;
    transition: background 0.2s ease !important;
    padding: 0 !important;
  }
  .tp-stepper-btn:hover {
    background: rgba(16, 185, 129, 0.5) !important;
  }

  .tp-filter-bar-reset {
    background: rgba(244, 63, 94, 0.15) !important;
    border: 1px solid rgba(244, 63, 94, 0.3) !important;
    color: #fda4af !important;
    padding: 5px 10px !important;
    border-radius: 8px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
  }
  .tp-filter-bar-reset:hover {
    background: rgba(244, 63, 94, 0.3) !important;
    color: #fff !important;
  }

  /* Blocked Categories Overview Row */
  .tp-blocked-cats-row {
    border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
    padding-top: 6px !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    flex-wrap: wrap !important;
  }
  .tp-blocked-cats-label {
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #f43f5e !important;
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
    white-space: nowrap !important;
  }
  .tp-blocked-chip {
    display: inline-flex !important;
    align-items: center !important;
    gap: 5px !important;
    padding: 2px 8px !important;
    border-radius: 10px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    background: rgba(239, 68, 68, 0.18) !important;
    border: 1px solid rgba(239, 68, 68, 0.4) !important;
    color: #fca5a5 !important;
    user-select: none !important;
    transition: all 0.15s ease !important;
  }
  .tp-blocked-chip:hover {
    background: rgba(239, 68, 68, 0.3) !important;
    border-color: #ef4444 !important;
    color: #fff !important;
  }
  .tp-blocked-chip-remove {
    cursor: pointer !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    color: #fca5a5 !important;
    padding: 0 2px !important;
    border-radius: 3px !important;
  }
  .tp-blocked-chip-remove:hover {
    color: #fff !important;
    background: rgba(255, 255, 255, 0.2) !important;
  }
  .tp-blocked-clear-all {
    font-size: 10px !important;
    color: #94a3b8 !important;
    background: transparent !important;
    border: none !important;
    text-decoration: underline !important;
    cursor: pointer !important;
    padding: 2px 4px !important;
  }
  .tp-blocked-clear-all:hover {
    color: #f43f5e !important;
  }

  /* Mobile Responsive Fixes */
  @media (max-width: 640px) {
    #tp-suite-filter-bar {
      padding: 8px 10px !important;
      margin: 6px auto 10px auto !important;
    }
    .tp-filter-main-row {
      flex-wrap: wrap !important;
      gap: 6px !important;
    }
    .tp-input-wrapper {
      flex: 1 1 100% !important;
      width: 100% !important;
    }
    .tp-bar-btn, .tp-filter-bar-reset {
      flex: 1 1 auto !important;
      justify-content: center !important;
      text-align: center !important;
      padding: 6px 8px !important;
    }
  }
`;

const SHADOW_MODAL_STYLES = `
  :host {
    all: initial;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }

  /* Floating Settings Button */
  #tp-settings-fab {
    position: fixed;
    bottom: 14px;
    right: 14px;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: rgba(30, 41, 59, 0.85);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
    cursor: pointer;
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #f1f5f9;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  #tp-settings-fab:hover {
    background: rgba(16, 185, 129, 0.9);
    border-color: rgba(16, 185, 129, 0.2);
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.5);
    transform: scale(1.1);
  }
  #tp-settings-fab svg {
    width: 24px;
    height: 24px;
    transition: transform 0.6s ease;
  }
  #tp-settings-fab:hover svg {
    transform: rotate(90deg);
  }

  /* Settings Modal Dialog */
  dialog#tp-settings-dialog {
    box-sizing: border-box;
    width: 92%;
    max-width: 500px;
    max-height: 85vh;
    overflow-y: auto;
    background: rgba(30, 41, 59, 0.95);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
    border-radius: 16px;
    color: #f8fafc;
    padding: 24px;
    font-family: inherit;
    margin: auto;
  }
  dialog#tp-settings-dialog::backdrop {
    background: rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
  }
  dialog#tp-settings-dialog h3 {
    margin: 0 0 18px 0;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.5px;
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
    padding-right: 4px;
  }
  .tp-settings-group {
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .tp-settings-group label {
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
    margin: 0;
  }
  .tp-section-header {
    margin: 14px 0 10px 0;
    color: #10b981;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 4px;
  }

  /* Segmented Control */
  .tp-segmented-control {
    display: flex;
    background: rgba(15, 23, 42, 0.6);
    border-radius: 8px;
    padding: 2px;
    border: 1px solid rgba(255, 255, 255, 0.05);
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
    margin: 0;
    user-select: none;
  }
  .tp-segmented-control input[type="radio"] {
    display: none;
  }
  .tp-segmented-control label:hover {
    color: #f1f5f9;
  }
  .tp-segmented-control input[type="radio"]:checked + label {
    background: #10b981;
    color: #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }
  .tp-segmented-control-blue input[type="radio"]:checked + label {
    background: #3b82f6 !important;
  }

  .tp-range-container {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .tp-range-container input[type="range"] {
    flex: 1;
    accent-color: #10b981;
  }
  .tp-range-container.tp-blue input[type="range"] {
    accent-color: #3b82f6;
  }
  .tp-range-container.tp-rose input[type="range"] {
    accent-color: #f43f5e;
  }
  .tp-range-container input[type="number"] {
    width: 60px;
    padding: 4px 8px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
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
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #f8fafc;
    font-family: inherit;
    font-size: 12px;
    resize: vertical;
  }

  /* Switch Toggle */
  .tp-switch-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .tp-switch-label {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .tp-switch-desc {
    font-size: 11px;
    color: #64748b;
  }
  .tp-switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
  }
  .tp-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }
  .tp-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(15, 23, 42, 0.6);
    transition: .4s;
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .tp-slider:before {
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 3px;
    bottom: 3px;
    background-color: #94a3b8;
    transition: .4s;
    border-radius: 50%;
  }
  .tp-switch input:checked + .tp-slider {
    background-color: #10b981;
    border-color: rgba(16, 185, 129, 0.2);
  }
  .tp-switch.tp-blue input:checked + .tp-slider {
    background-color: #3b82f6;
  }
  .tp-switch.tp-rose input:checked + .tp-slider {
    background-color: #f43f5e;
  }
  .tp-switch input:checked + .tp-slider:before {
    transform: translateX(20px);
    background-color: #fff;
  }

  .tp-modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }
  .tp-btn {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;
  }
  .tp-btn-secondary {
    background: rgba(255, 255, 255, 0.08);
    color: #94a3b8;
  }
  .tp-btn-secondary:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
  }
  .tp-btn-primary {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: #fff;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
  }
  .tp-btn-primary:hover {
    box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
    transform: translateY(-1px);
  }

  #tp-toast-container {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 100000;
    display: flex;
    flex-direction: column-reverse;
    gap: 8px;
    pointer-events: none;
  }
  .tp-toast {
    background: rgba(15, 23, 42, 0.96);
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: #f8fafc;
    padding: 9px 14px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: opacity 0.3s ease, transform 0.3s ease;
  }
  .tp-toast.fade-out {
    opacity: 0;
    transform: translateY(6px);
  }
  .tp-toast-undo {
    background: rgba(56, 189, 248, 0.18);
    border: 1px solid rgba(56, 189, 248, 0.5);
    color: #38bdf8;
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s ease;
    user-select: none;
  }
  .tp-toast-undo:hover {
    background: #38bdf8;
    color: #0f172a;
  }
`;

// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  // Fast Typed Storage Helpers with GM_getValue + localStorage Fallback
  const LOCAL_STORAGE_PREFIX = 'tp_suite_v2_';

  const _getValue = (key, def) => {
    try {
      if (typeof GM_getValue !== 'undefined') {
        const val = GM_getValue(key);
        if (val !== undefined && val !== null) return val;
      }
    } catch (e) { }

    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const raw = window.localStorage.getItem(LOCAL_STORAGE_PREFIX + key);
        if (raw !== null) {
          const parsed = JSON.parse(raw);
          if (typeof GM_setValue !== 'undefined') GM_setValue(key, parsed);
          return parsed;
        }
      }
    } catch (e) { }

    return def;
  };

  const _setValue = (key, val) => {
    try {
      if (typeof GM_setValue !== 'undefined') GM_setValue(key, val);
    } catch (e) { }

    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(LOCAL_STORAGE_PREFIX + key, JSON.stringify(val));
      }
    } catch (e) { }
  };

  // Cached configuration state loaded once at startup
  const CONFIG = {
    MODE: _getValue('MODE', DEFAULTS.MODE),
    MARGIN_PERCENT: parseFloat(_getValue('MARGIN_PERCENT', DEFAULTS.MARGIN_PERCENT)),
    DIM_OPACITY: parseFloat(_getValue('DIM_OPACITY', DEFAULTS.DIM_OPACITY)),
    USE_SHIPPING_PRICE: _getValue('USE_SHIPPING_PRICE', DEFAULTS.USE_SHIPPING_PRICE),
    HEATMAP_ENABLED: _getValue('HEATMAP_ENABLED', DEFAULTS.HEATMAP_ENABLED),
    HEATMAP_INTENSITY: parseFloat(_getValue('HEATMAP_INTENSITY', DEFAULTS.HEATMAP_INTENSITY)),
    HEATMAP_CURVE: _getValue('HEATMAP_CURVE', DEFAULTS.HEATMAP_CURVE),
    NEGATIVE_TERMS: _getValue('NEGATIVE_TERMS', DEFAULTS.NEGATIVE_TERMS),
    EXCLUDED_CATEGORIES: _getValue('EXCLUDED_CATEGORIES', DEFAULTS.EXCLUDED_CATEGORIES),
    MIN_OFFERS: parseInt(_getValue('MIN_OFFERS', DEFAULTS.MIN_OFFERS)),
    SORT_BY_OFFERS: _getValue('SORT_BY_OFFERS', DEFAULTS.SORT_BY_OFFERS),
    ALARM_ENABLED: _getValue('ALARM_ENABLED', DEFAULTS.ALARM_ENABLED),
    ALARM_TARGET_PERCENT: parseFloat(_getValue('ALARM_TARGET_PERCENT', DEFAULTS.ALARM_TARGET_PERCENT)),
    ALARM_DURATION_DAYS: String(_getValue('ALARM_DURATION_DAYS', DEFAULTS.ALARM_DURATION_DAYS)),
    ALARM_AUTO_SUBMIT: _getValue('ALARM_AUTO_SUBMIT', DEFAULTS.ALARM_AUTO_SUBMIT),
    OBSERVER_DEBOUNCE_MS: parseInt(_getValue('OBSERVER_DEBOUNCE_MS', DEFAULTS.OBSERVER_DEBOUNCE_MS)),
    DEBUG: _getValue('DEBUG', DEFAULTS.DEBUG)
  };

  const saveConfigKey = (key, val) => {
    CONFIG[key] = val;
    _setValue(key, val);
  };

  const log = (...args) => { if (CONFIG.DEBUG) console.log('[Toppreise-Suite]', ...args); };

  // Inject Custom Stylesheet safely
  if (!document.getElementById('tp-unified-settings-styles')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'tp-unified-settings-styles';
    styleEl.textContent = STYLES;
    document.head.appendChild(styleEl);
  }

  function updateBodyClasses() {
    document.body.classList.remove('tp-mode-dim', 'tp-mode-hide', 'tp-mode-highlight-only');
    document.body.classList.add(`tp-mode-${CONFIG.MODE}`);
    document.documentElement.style.setProperty('--tp-dim-opacity', CONFIG.DIM_OPACITY);
  }

  updateBodyClasses();

  // Helper: Normalize names
  function normalizeName(name) {
    if (!name) return '';
    return name.toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  // Canonical Root Category Slug Mapping (Replaces static 785-line table)
  const ROOT_SLUG_MAP = {
    'computer-zubehoer': 'Computer & Zubehör',
    'videogames': 'Videogames',
    'tv-video': 'TV & Video',
    'foto-video': 'Foto & Video',
    'foto': 'Foto & Video',
    'smartphones-mobiltelefone': 'Smartphones & Mobiltelefone',
    'hifi-audio': 'HiFi & Audio',
    'haushalt-kueche': 'Haushalt & Küche',
    'drogerie': 'Drogerie',
    'sport-freizeit': 'Sport & Freizeit',
    'spielwaren': 'Spielwaren',
    'buerobedarf-schreibwaren': 'Bürobedarf & Schreibwaren',
    'haus-garten': 'Garten & Baumarkt',
    'garten-baumarkt': 'Garten & Baumarkt',
    'werkzeuge-werkstatt': 'Garten & Baumarkt',
    'auto-motorrad': 'Auto & Motorrad',
    'filme': 'Filme',
    'uhren': 'Uhren',
    'buecher-medien': 'Bücher & Medien',
    'kleidung-mode': 'Kleidung & Mode',
    'bekleidung-schuhe': 'Kleidung & Mode'
  };

  const GROUP_EMOJIS = {
    'Filme': '🎬',
    'Spielwaren': '🧸',
    'Computer & Zubehör': '💻',
    'Videogames': '🎮',
    'HiFi & Audio': '🎧',
    'TV & Video': '📺',
    'Smartphones & Mobiltelefone': '📱',
    'Drogerie': '🧴',
    'Sport & Freizeit': '⚽',
    'Haushalt & Küche': '☕',
    'Auto & Motorrad': '🚗',
    'Uhren': '⌚',
    'Foto & Video': '📷',
    'Bücher & Medien': '📚',
    'Kleidung & Mode': '👕',
    'Garten & Baumarkt': '🪴',
    'Sonstiges': '📦'
  };

  function getGroupEmoji(groupName) {
    return GROUP_EMOJIS[groupName] || '📦';
  }

  function normalizeRootSlug(slug) {
    if (!slug) return null;
    const clean = slug.split('-c')[0].toLowerCase().trim();
    return ROOT_SLUG_MAP[clean] || null;
  }

  function extractCategoryDisplay(key) {
    if (!key) return { label: '', group: '' };
    if (key.startsWith('GROUP:')) {
      const group = key.slice(6);
      return { label: group, group };
    }
    if (key.startsWith('PATH:')) {
      const parts = key.slice(5).split('/');
      const group = parts[0] || '';
      const cat = parts.slice(1).join('/') || group;
      return { label: cat, group };
    }
    return { label: key, group: '' };
  }

  const BRAND_RULES = [
    { regex: /\b(game|games|spiel|spiele|nintendo|switch|playstation|ps5|ps4|ps3|xbox|pc spiele|konsole|konsolen|gamepad|controller|lenkrad|vr headset|amiibo|simulationen|rennspiel|actionspiele|tabletop spiele)\b/i, group: 'Videogames' },
    { regex: /\b(lego|legos|playmobil|cobi|cada|mega construx|fischertechnik|ravensburger|schleich|barbie|hot wheels|action figuren|funko|nerf|spielwaren|spielzeug|puppe|puppen|pluesch|plüsch|autorennbahn|rc modelle|multicopter|puzzles|gesellschaftsspiele|familienspiele|kartenspiele|experimentierkaesten|bau konstruktionsspielzeug|outdoor spielzeug|spielzeugroboter)\b/i, group: 'Spielwaren' },
    { regex: /\b(reifen|pneus|sommerreifen|winterreifen|allwetterreifen|felgen|dachbox|dachboxen|dachtraeger|dachträger|kindersitz|kindersitze|autozubehoer|car hifi|car video|motorradhelm|dashcam)\b/i, group: 'Auto & Motorrad' },
    { regex: /\b(fritteuse|fritteusen|heissluftfritteuse|heissluftfritteusen|vollautomat|vollautomaten|kaffee|espressomaschine|espressomaschinen|kaffeemuehle|kaffeemühle|kuechengeraet|kuechengeraete|küchengerät|küchengeräte|haushaltsgeraet|haushaltsgeraete|haushaltsgerät|haushaltsgeräte|staubsauger|saugroboter|wischroboter|fensterreinigungsroboter|mikrowelle|mikrowellen|backofen|herd|kuehlschrank|kühlschrank|gefrierschrank|geschirrspueler|geschirrspüler|waschmaschine|waschmaschinen|waeschetrockner|wäschetrockner|mixer|blender|wasserkocher|toaster|thermoskanne|abfallsystem|raumduft|dampfgarer|slowcooker|saftpresse|entsafter|geschirr|besteck|glaeser|gläser|topf|toepfe|töpfe|pfanne|pfannen|kochgeschirr|spirituosen|wein|whisky|gin|rum|vodka|saug und wischroboter|klimageraete|senseo maschinen|sonstige kuechengeraete)\b/i, group: 'Haushalt & Küche' },
    { regex: /\b(haarglaetter|haarglätter|glaetteisen|glätteisen|bartschneider|haarschneider|haar bartschneider|rasierer|elektrorasierer|epilierer|haartrockner|foehn|föhn|zahnbuerste|zahnbürste|zahnbuersten|zahnbürsten|elektrozahnbuersten|elektrozahnbuerste|parfum|parfüm|duft|duefte|düfte|eau de|duschpflege|duschgel|shampoo|seife|geschenkset|geschenksets|hautpflege|koerperpflege|körperpflege|kosmetik|make-up|makeup|sonnenschutz|kontaktlinsen|hygiene)\b/i, group: 'Drogerie' },
    { regex: /\b(smartphone|smartphones|mobiltelefon|mobiltelefone|handy|handys|iphone|galaxy|pixel|smartring|smartringe|smartwatch|smartwatches|activity tracker|huelle|huellen|hülle|hüllen|cover|oberschalen cover|schutzfolie|panzerglas|ladekabel|powerbank|powerbanks|magsafe|funktelefon|festnetz)\b/i, group: 'Smartphones & Mobiltelefone' },
    { regex: /\b(kopfhoerer|kopfhörer|in-ear|earbuds|lautsprecher|bluetooth lautsprecher|soundbar|plattenspieler|receiver|av receiver|home cinema av receiver|verstaerker|verstärker|hifi|radio|cd player|dac|subwoofer|mikrofon|musikinstrument|gitarre|piano|keyboard)\b/i, group: 'HiFi & Audio' },
    { regex: /\b(tv|fernseher|tv geraete|beamer|projektor|home cinema|heimkino|blu-ray player|dvd player|actioncam|actionkamera|camcorder|media player|streaming stick|chromecast|apple tv)\b/i, group: 'TV & Video' },
    { regex: /\b(kamera|kameras|digitalkamera|spiegellose|dslr|objektiv|objektive|stativ|stative|blitz|fotostudio|drohne|sofortbildkamera)\b/i, group: 'Foto & Video' },
    { regex: /\b(dvd|blu-ray|blu ray|4k ultra hd|film|filme|kino|serie|tv serien|western|abenteuer|action|krimi|drama|komoedie|komödie|thriller|horror|anime|dokumentation)\b/i, group: 'Filme' },
    { regex: /\b(crosstrainer|laufband|laufbaender|laufbänder|ergometer|rudergeraet|rudergerät|fitness|krafttraining|fitness krafttraining|hantel|hanteln|matten|velo|velos|fahrrad|ebike|e-bike|velohelm|skihelme|skibrille|skihelm|koffer|rucksack|taschenmesser|fernglas|camping|zelt|schlafsack|tretroller|scooter|inline skates|gps|gps navigations geraete|navigation|navigations|activity tracker smartwatches)\b/i, group: 'Sport & Freizeit' },
    { regex: /\b(rasenmaeher|rasenmäher|rasenroboter|grill|gasgrill|elektrogrill|holzkohlegrill|bohrmaschine|akkuschrauber|saege|säge|schleifer|schwingschleifer|schalter|taster|steckdose|lampe|lampen|leuchtmittel|led|smart home|gartenmoebel|gartenmöbel|hochdruckreiniger|werkzeug|werkzeuge)\b/i, group: 'Garten & Baumarkt' },
    { regex: /\b(uhr|uhren|armbanduhr|damenuhr|herrenuhr|chronograph|automatikuhr|wanduhr|wecker)\b/i, group: 'Uhren' },
    { regex: /\b(kleidung|bekleidung|jacke|jacken|hose|hosen|t-shirt|pullover|hemd|kleid|schuhe|sneaker|stiefel|tasche|taschen|handtasche|rucksack|sonnenbrille|sonnenbrillen|schmuck|ring|kette)\b/i, group: 'Kleidung & Mode' },
    { regex: /\b(buch|buecher|bücher|roman|taschenbuch|sachbuch|hoerbuch|hörbuch|comic|manga|zeitschrift)\b/i, group: 'Bücher & Medien' },
    { regex: /\b(usb|speicherstick|speichersticks|ssd|hdds?|solid state|festplatte|festplatten|grafikkarte|grafikkarten|notebook|notebooks|laptop|laptops|tablet|tablets|ebook|monitore|monitor|drucker|scanner|nas|mainboard|mainboards|prozessor|prozessoren|cpu|gpu|pc gehaeuse|netzteil|netzteile|ladegeraet|ladegerät|netzadapter|ladegeraete netzadapter|kabel|hub|dockingstation|tastatur|tastaturen|maus|maeuse|mäuse|mausmatte|webcam|webcams|headset|aktenvernichter|papierschredder|arbeitsspeicher|ram|netzwerk|wlan|router|switch|server|western digital|externe solid state drives ssd|usb speichersticks)\b/i, group: 'Computer & Zubehör' }
  ];

  function resolveCategoryGroup(categoryName, card = null) {
    if (card) {
      const hrefs = getCardHrefs(card);
      for (const href of hrefs) {
        const match = href.match(/\/(?:preisvergleich|produktsuche)\/([^\/]+)\//i);
        if (match && match[1]) {
          const segs = match[1].split('/').filter(Boolean);
          for (const seg of segs) {
            const canonical = normalizeRootSlug(seg);
            if (canonical) return canonical;
            const normSeg = seg.toLowerCase().replace(/-/g, ' ');
            for (const rule of BRAND_RULES) {
              if (rule.regex.test(normSeg)) return rule.group;
            }
          }
        }
      }
    }
    if (categoryName) {
      const norm = categoryName.toLowerCase();
      for (const rule of BRAND_RULES) {
        if (rule.regex.test(norm)) return rule.group;
      }
    }
    return 'Sonstiges';
  }

  function isPathExcluded(catName, rootGroup, excludedCats = []) {
    if (!excludedCats || excludedCats.length === 0) return false;
    if (excludedCats.includes(`GROUP:${rootGroup}`)) return true;
    if (catName && excludedCats.includes(catName)) return true;
    if (catName && excludedCats.includes(`PATH:${rootGroup}/${catName}`)) return true;
    return false;
  }

  function parsePrice(priceStr) {
    if (!priceStr) return 0;
    const clean = priceStr.replace(/[.–\-]\s*$/g, '.00').replace(/[^\d,.]/g, '').replace("'", "").replace(',', '.');
    const val = parseFloat(clean);
    return isNaN(val) ? 0 : val;
  }

  // Helper: Universal Card Grabber
  function getProductCards() {
    const standardCards = Array.from(document.querySelectorAll('.Plugin_Product, .mixedBrowsingListProduct'));
    if (standardCards.length > 0) {
      return standardCards.filter(c => !c.parentElement.closest('.Plugin_Product'));
    }

    const productLinks = document.querySelectorAll('a[href*="/preisvergleich/"]');
    const gridCards = new Set();

    productLinks.forEach(link => {
      if (link.closest('header, nav, footer, .breadcrumb, #tp-suite-filter-bar')) return;

      let container = link.parentElement;
      while (container && container !== document.body && container.parentElement !== document.body) {
        if (container.querySelector('.Plugin_Price, [class*="Price"], [class*="price"]') ||
          container.querySelector('[class*="Differenz"], [class*="differenz"]')) {
          gridCards.add(container);
          break;
        }
        container = container.parentElement;
      }
    });

    return Array.from(gridCards);
  }

  // Helper: Format raw category URL slugs into clean title case
  function formatCategorySlug(slug) {
    if (!slug) return '';
    const clean = decodeURIComponent(slug).replace(/-/g, ' ').trim();
    if (!clean || clean.length < 2 || (clean.toLowerCase().startsWith('p') && !isNaN(clean.slice(1)))) return '';
    return clean.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  }

  // Helper: Collect all href strings from card element itself, its ancestors, and its descendants
  function getCardHrefs(card) {
    if (!card) return [];
    const hrefs = [];

    if (card.tagName && card.tagName.toLowerCase() === 'a') {
      const href = card.getAttribute('href') || card.href || '';
      if (href) hrefs.push(href);
    }

    const closestA = card.closest ? card.closest('a[href]') : null;
    if (closestA) {
      const href = closestA.getAttribute('href') || closestA.href || '';
      if (href && !hrefs.includes(href)) hrefs.push(href);
    }

    if (card.querySelectorAll) {
      card.querySelectorAll('a[href]').forEach(a => {
        if (a.closest('header, nav, footer, .breadcrumb, #tp-suite-filter-bar')) return;
        const href = a.getAttribute('href') || a.href || '';
        if (href && !hrefs.includes(href)) hrefs.push(href);
      });
    }

    return hrefs;
  }

  // Helper: Universal Category Extractor (Prioritizes Product URL Category Path)
  function extractCardCategory(card) {
    if (!card) return '';
    if (card.dataset && card.dataset.tpCategory) return card.dataset.tpCategory;

    let extracted = '';
    const hrefs = getCardHrefs(card);

    // Tier 1 (Primary): Product URL Category Path (/preisvergleich/CategorySlug/ProductTitle-p123)
    for (const href of hrefs) {
      const match = href.match(/\/preisvergleich\/(.+)\/[^\/]+-p\d+/i);
      if (match && match[1]) {
        const segments = match[1].split('/').filter(Boolean);
        if (segments.length > 0) {
          const subCat = segments[segments.length - 1];
          const formatted = formatCategorySlug(subCat);
          if (formatted) {
            extracted = formatted;
            break;
          }
        }
      }
    }

    // Tier 2: Category Search Links (/produktsuche/.../CategoryName-c123)
    if (!extracted) {
      for (const href of hrefs) {
        const catMatch = href.match(/\/produktsuche\/(?:.*\/)?([^\/-]+(?:-[^\/-]+)*)-c\d+/i) || href.match(/(?:.*\/)?([^\/]+)-c\d+/i);
        if (catMatch && catMatch[1]) {
          const formatted = formatCategorySlug(catMatch[1]);
          if (formatted) {
            extracted = formatted;
            break;
          }
        }
      }
    }

    // Tier 3: DOM Category Classes & Data Attributes
    if (!extracted && card.querySelector) {
      const catEl = card.querySelector('.subCategory, .productCategory, .categoryLink, [class*="Category"], [data-category]');
      if (catEl) {
        const text = (catEl.getAttribute('data-category') || catEl.textContent).trim().replace(/\(\d+\)/g, '').trim();
        if (text && text.length > 1 && !text.includes('CHF') && !text.includes('Angebot') && !text.includes('%')) {
          extracted = text;
        }
      }
    }

    // Tier 4: Fallback to Active Breadcrumb section
    if (!extracted) {
      const activeBreadcrumb = document.querySelector('.breadcrumb a:last-of-type, [class*="breadcrumb"] a:last-of-type');
      if (activeBreadcrumb) {
        const text = activeBreadcrumb.textContent.trim().replace(/\(\d+\)/g, '').trim();
        if (text && text.length > 1 && !['home', 'toppreise', 'neue toppreise', 'startseite'].includes(text.toLowerCase())) {
          extracted = text;
        }
      }
    }

    if (extracted && card.dataset) {
      card.dataset.tpCategory = extracted;
    }
    return extracted;
  }

  // Helper: Extract Offer Count with dataset caching
  function extractOfferCount(card) {
    if (card.dataset && card.dataset.tpOfferCount) {
      return parseInt(card.dataset.tpOfferCount, 10);
    }
    const text = card.textContent || '';
    const match = text.match(/(\d+)\s*(?:Angebote|Angebot)/i);
    const count = match ? parseInt(match[1], 10) : card.querySelectorAll('.Plugin_DealerRelProdPriceInfo').length;
    if (card.dataset) card.dataset.tpOfferCount = String(count);
    return count;
  }

  // Helper: Check Negative Term Match
  function matchesNegativeTerms(card, termsList) {
    if (!termsList || termsList.length === 0) return false;
    const visibleText = (card.innerText || card.textContent || '').toLowerCase();
    return termsList.some(term => {
      if (!term) return false;
      if (term.length <= 3) {
        const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return new RegExp(`\\b${escaped}\\b`, 'i').test(visibleText);
      }
      return visibleText.includes(term);
    });
  }

  // ─── DISCOUNT HEATMAP ENGINE ────────────────────────────────────────────────
  function extractCardDiscount(card) {
    if (card.dataset && card.dataset.tpDiscount !== undefined) {
      const cached = parseFloat(card.dataset.tpDiscount);
      return isNaN(cached) ? null : cached;
    }

    let discount = null;
    const badgeEl = card.querySelector('.badge-dif, .badge, [class*="badge-dif"]');
    if (badgeEl) {
      const match = badgeEl.textContent.match(/([+-]?\d+(?:[\.,]\d+)?)\s*%/);
      if (match) {
        discount = Math.abs(parseFloat(match[1].replace(',', '.')));
      }
    }

    if (discount === null) {
      const match = card.textContent.match(/(?:Differenz|Rabatt|Discount)[\s\S]*?([+-]?\d+(?:[\.,]\d+)?)\s*%/i) ||
                    card.textContent.match(/-\s*(\d+(?:[\.,]\d+)?)\s*%/);
      if (match) {
        discount = Math.abs(parseFloat(match[1].replace(',', '.')));
      }
    }

    if (discount !== null && !isNaN(discount)) {
      discount = Math.min(100, Math.max(0, discount));
      if (card.dataset) card.dataset.tpDiscount = String(discount);
      return discount;
    }

    if (card.dataset) card.dataset.tpDiscount = '';
    return null;
  }

  function interpolateRgb(c1, c2, factor) {
    return [
      Math.round(c1[0] + (c2[0] - c1[0]) * factor),
      Math.round(c1[1] + (c2[1] - c1[1]) * factor),
      Math.round(c1[2] + (c2[2] - c1[2]) * factor)
    ];
  }

  function getHeatmapStyles(discountPercent, intensity = 1.0, curve = 'calibrated') {
    let t = 0;
    const clampedDiscount = Math.max(0, Math.min(100, discountPercent));
    if (curve === 'linear') {
      t = clampedDiscount / 100;
    } else {
      if (clampedDiscount <= 10.0) {
        t = (clampedDiscount / 10.0) * 0.12;
      } else if (clampedDiscount >= 50.0) {
        t = Math.min(1.0, 0.85 + ((clampedDiscount - 50.0) / 25.0) * 0.15);
      } else {
        t = 0.12 + ((clampedDiscount - 10.0) / 40.0) * 0.73;
      }
    }

    const stops = [
      { t: 0.00, base: [18, 48, 88],   acc: [28, 92, 175],   border: [56, 140, 248, 0.70] },
      { t: 0.25, base: [12, 58, 64],   acc: [16, 130, 125],  border: [20, 210, 190, 0.75] },
      { t: 0.50, base: [68, 48, 10],   acc: [180, 118, 15],  border: [245, 175, 20, 0.80] },
      { t: 0.75, base: [85, 28, 12],   acc: [228, 76, 18],   border: [251, 115, 36, 0.88] },
      { t: 1.00, base: [98, 14, 32],   acc: [238, 25, 65],   border: [244, 63, 94, 0.95] }
    ];

    let base = stops[0].base;
    let acc = stops[0].acc;
    let borderRgb = stops[0].border.slice(0, 3);
    let borderAlpha = stops[0].border[3];

    for (let i = 0; i < stops.length - 1; i++) {
      const s0 = stops[i];
      const s1 = stops[i + 1];
      if (t >= s0.t && t <= s1.t) {
        const factor = (t - s0.t) / (s1.t - s0.t);
        base = interpolateRgb(s0.base, s1.base, factor);
        acc = interpolateRgb(s0.acc, s1.acc, factor);
        borderRgb = interpolateRgb(s0.border.slice(0, 3), s1.border.slice(0, 3), factor);
        borderAlpha = s0.border[3] + (s1.border[3] - s0.border[3]) * factor;
        break;
      }
    }

    const safeIntensity = Math.max(0.2, Math.min(1.0, intensity));
    const alphaBase = (0.92 + 0.04 * t);
    const alphaAcc = (0.75 + 0.20 * t) * safeIntensity;
    const effectiveBorderAlpha = (borderAlpha * safeIntensity).toFixed(2);

    const bg = `linear-gradient(135deg, rgba(${base[0]}, ${base[1]}, ${base[2]}, ${alphaBase.toFixed(2)}) 0%, rgba(${acc[0]}, ${acc[1]}, ${acc[2]}, ${alphaAcc.toFixed(2)}) 100%)`;
    const border = `rgba(${borderRgb[0]}, ${borderRgb[1]}, ${borderRgb[2]}, ${effectiveBorderAlpha})`;
    const glow = t >= 0.45 ? `0 4px 18px rgba(${acc[0]}, ${acc[1]}, ${acc[2]}, ${(0.32 * safeIntensity).toFixed(2)})` : 'none';

    return { bg, border, glow };
  }

  // Central Filter Reset Helper
  function resetAllFilters() {
    saveConfigKey('NEGATIVE_TERMS', '');
    saveConfigKey('EXCLUDED_CATEGORIES', []);
    saveConfigKey('MIN_OFFERS', 0);

    const inlineInput = document.getElementById('tp-inline-negative-input');
    if (inlineInput) inlineInput.value = '';
    const clearBtn = document.getElementById('tp-clear-neg-btn');
    if (clearBtn) clearBtn.style.display = 'none';

    if (uiShadowRoot) {
      const modalNegInput = uiShadowRoot.getElementById('tp-negative-terms-input');
      if (modalNegInput) modalNegInput.value = '';
      const modalMinOffersVal = uiShadowRoot.getElementById('tp-min-offers-val');
      const modalMinOffersRange = uiShadowRoot.getElementById('tp-min-offers-range');
      if (modalMinOffersVal) modalMinOffersVal.value = 0;
      if (modalMinOffersRange) modalMinOffersRange.value = 0;
    }

    processListings();
    showToast('Alle Filter zurückgesetzt');
  }

  // Dedicated Power Filter Bar Placement Selector
  function getSuiteBarPlacement() {
    const bar = document.getElementById('tp-suite-filter-bar');

    const isSafe = (el) => {
      if (!el) return false;
      return !el.closest('.header, [class*="MainTopHead"], [class*="MainHead"], .f_filter_plugin, .filters, .filterBox, #tp-root, dialog');
    };

    const mainTargets = [
      '#Page_ListTopPriceReductionProducts',
      '#Page_ListTop100Products',
      '[id^="Page_List"]',
      '#Page_Browsing',
      '.f_browsingListContainer',
      '#Plugin_MixedBrowsingList',
      '[id^="Plugin_MixedBrowsingList"]',
      '.standardList',
      '#product-list'
    ];

    for (const sel of mainTargets) {
      const target = document.querySelector(sel);
      if (target && target.parentElement && isSafe(target.parentElement) && target !== bar) {
        return { container: target.parentElement, reference: target };
      }
    }

    const contentContainers = [
      document.getElementById('FrameContent'),
      document.querySelector('#tpContent .pageContent'),
      document.querySelector('.pageContent'),
      document.querySelector('#browseContent'),
      document.querySelector('main'),
      document.querySelector('#content')
    ];

    for (const container of contentContainers) {
      if (container && isSafe(container) && container !== bar) {
        let ref = container.firstElementChild;
        while (ref && (ref === bar || !isSafe(ref))) {
          ref = ref.nextElementSibling;
        }
        return { container, reference: ref || null };
      }
    }

    return { container: document.body, reference: document.body.firstElementChild };
  }

  // Consolidated Top Filter Bar with Blocked Categories Overview
  function renderSuiteFilterBar(counts = { neg: 0, cat: 0, min: 0 }, pageHasOffers = false) {
    const placement = getSuiteBarPlacement();
    if (!placement || !placement.container) return;

    let bar = document.getElementById('tp-suite-filter-bar');
    const excluded = CONFIG.EXCLUDED_CATEGORIES || [];
    const isRevealed = document.body.classList.contains('tp-reveal-filtered');
    const totalHidden = counts.neg + counts.cat + counts.min;

    const safeInsert = (container, node, ref) => {
      try {
        if (ref && ref.parentElement === container && ref !== node) {
          container.insertBefore(node, ref);
        } else {
          container.appendChild(node);
        }
      } catch (e) {
        container.appendChild(node);
      }
    };

    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'tp-suite-filter-bar';
      bar.innerHTML = `
        <div class="tp-filter-main-row">
          <div class="tp-input-wrapper" title="Kommagetrennte Begriffe eingeben (z.B. Hülle, Refurbished, Gebraucht), um passende Produkte auszublenden">
            <span class="tp-filter-badge" title="Toppreise Power Filter">⚡</span>
            <span class="tp-input-label-inline">🚫 Negativ-Filter:</span>
            <div class="tp-input-field-box">
              <input type="text" id="tp-inline-negative-input" placeholder="Wörter ausschließen (z. B. Hülle, Case, Refurbished...)" value="${CONFIG.NEGATIVE_TERMS || ''}">
              <button id="tp-clear-neg-btn" title="Text leeren" style="display: ${CONFIG.NEGATIVE_TERMS ? 'block' : 'none'};">✕</button>
            </div>
          </div>

          <button class="tp-bar-btn ${isRevealed ? 'tp-active' : ''}" id="tp-bar-reveal-btn" title="Ausgeblendete Produkte anzeigen/verbergen">
            👁️ <span id="tp-bar-reveal-count">${totalHidden}</span>
          </button>

          <button class="tp-bar-btn ${CONFIG.HEATMAP_ENABLED ? 'tp-active' : ''}" id="tp-bar-heat-btn" title="Rabatt-Heatmap ein-/ausschalten">
            🔥 Heatmap
          </button>

          <div class="tp-bar-stepper-group" id="tp-bar-min-offers-group" style="display: ${pageHasOffers ? 'flex' : 'none'};" title="Mindestanzahl benötigter Händler-Angebote">
            <span>Min:</span>
            <button class="tp-stepper-btn" id="tp-bar-min-minus" title="Verringern">-</button>
            <span id="tp-bar-min-val" style="min-width: 14px; text-align: center;">${CONFIG.MIN_OFFERS}</span>
            <button class="tp-stepper-btn" id="tp-bar-min-plus" title="Erhöhen">+</button>
          </div>

          <button class="tp-filter-bar-reset" id="tp-bar-reset-btn" title="Alle Filter (Text &amp; Kategorien) zurücksetzen">🔄 Reset</button>
        </div>

        <div id="tp-blocked-cats-container" class="tp-blocked-cats-row" style="display: ${excluded.length > 0 ? 'flex' : 'none'};">
          <span class="tp-blocked-cats-label">🚫 Ausgeblendet (${excluded.length}):</span>
          <div id="tp-blocked-chips-list" style="display: inline-flex; flex-wrap: wrap; gap: 4px; align-items: center;"></div>
          <button class="tp-blocked-clear-all" id="tp-blocked-clear-all-btn" title="Alle blockierten Kategorien freigeben">Alle freigeben</button>
        </div>
      `;

      safeInsert(placement.container, bar, placement.reference);

      const input = bar.querySelector('#tp-inline-negative-input');
      const clearBtn = bar.querySelector('#tp-clear-neg-btn');

      input.oninput = (e) => {
        saveConfigKey('NEGATIVE_TERMS', e.target.value);
        if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
        if (uiShadowRoot) {
          const modalInput = uiShadowRoot.getElementById('tp-negative-terms-input');
          if (modalInput) modalInput.value = e.target.value;
        }
        processListings();
      };

      if (clearBtn) {
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
      }

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

      const updateMinOffers = (delta) => {
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
    } else {
      if (bar.parentElement !== placement.container || (bar.nextSibling !== placement.reference && placement.reference !== bar)) {
        safeInsert(placement.container, bar, placement.reference);
      }
    }

    bar.style.display = 'flex';

    const input = bar.querySelector('#tp-inline-negative-input');
    const clearBtn = bar.querySelector('#tp-clear-neg-btn');
    if (input && document.activeElement !== input) {
      input.value = CONFIG.NEGATIVE_TERMS || '';
      if (clearBtn) clearBtn.style.display = CONFIG.NEGATIVE_TERMS ? 'block' : 'none';
    }

    const revealBtn = bar.querySelector('#tp-bar-reveal-btn');
    const revealCount = bar.querySelector('#tp-bar-reveal-count');
    if (revealBtn) revealBtn.classList.toggle('tp-active', isRevealed);
    if (revealCount) revealCount.textContent = totalHidden > 0 ? `${totalHidden}` : '0';

    const heatBtn = bar.querySelector('#tp-bar-heat-btn');
    if (heatBtn) heatBtn.classList.toggle('tp-active', CONFIG.HEATMAP_ENABLED !== false);

    const minGroup = bar.querySelector('#tp-bar-min-offers-group');
    const minVal = bar.querySelector('#tp-bar-min-val');
    if (minGroup) minGroup.style.display = pageHasOffers ? 'flex' : 'none';
    if (minVal) minVal.textContent = CONFIG.MIN_OFFERS;

    // Render blocked category chips
    const blockedContainer = bar.querySelector('#tp-blocked-cats-container');
    const chipsList = bar.querySelector('#tp-blocked-chips-list');
    if (blockedContainer && chipsList) {
      if (excluded.length === 0) {
        blockedContainer.style.display = 'none';
        chipsList.innerHTML = '';
      } else {
        blockedContainer.style.display = 'flex';
        chipsList.innerHTML = '';
        const labelEl = blockedContainer.querySelector('.tp-blocked-cats-label');
        if (labelEl) labelEl.textContent = `🚫 Ausgeblendet (${excluded.length}):`;

        excluded.forEach(key => {
          const info = extractCategoryDisplay(key);
          const emoji = getGroupEmoji(info.group);
          const chip = document.createElement('span');
          chip.className = 'tp-blocked-chip';
          chip.innerHTML = `${emoji} <span>${info.label}</span> <span class="tp-blocked-chip-remove" title="Wieder einblenden">✕</span>`;
          chip.querySelector('.tp-blocked-chip-remove').onclick = (e) => {
            e.stopPropagation();
            const updated = (CONFIG.EXCLUDED_CATEGORIES || []).filter(c => c !== key);
            saveConfigKey('EXCLUDED_CATEGORIES', updated);
            processListings();
            showToast(`Kategorie "${info.label}" wieder eingeblendet`);
          };
          chipsList.appendChild(chip);
        });
      }
    }
  }

  function isNeueToppreisePage() {
    const path = (window.location.pathname || '') + (window.location.search || '');
    const currentUrl = document.body?.getAttribute('data-current_url') || '';
    return path.includes('neue-toppreise') ||
           path.includes('new-best-prices') ||
           path.includes('nouveaux-meilleurs-prix') ||
           currentUrl.includes('neue-toppreise') ||
           currentUrl.includes('new-best-prices') ||
           currentUrl.includes('nouveaux-meilleurs-prix') ||
           document.body?.classList.contains('Page_ListTopPriceReductionProducts') ||
           !!document.getElementById('Page_ListTopPriceReductionProducts');
  }

  let isModifyingDOM = false;

  function processListings() {
    if (isModifyingDOM) return;
    isModifyingDOM = true;
    try {
      log('Processing product listings...');

      const cards = getProductCards();
      if (cards.length === 0) {
        renderSuiteFilterBar({ neg: 0, cat: 0, min: 0 }, false);
        return;
      }

      // Parse Store Best Price Filters
      const filterElements = document.querySelectorAll('.filters .f_remove_filter[data-target-type="df"]');
      const activeStores = Array.from(filterElements).map(el => {
        const clone = el.cloneNode(true);
        const closeIcons = clone.querySelectorAll('.icon-close, .f_remove_icon, .close, span');
        closeIcons.forEach(icon => icon.remove());
        return normalizeName(clone.textContent);
      }).filter(name => name.length > 0);

      const rawTerms = CONFIG.NEGATIVE_TERMS || '';
      const termsList = rawTerms.split(/[,;\n]/).map(t => t.trim().toLowerCase()).filter(t => t.length > 0);
      const excludedCats = CONFIG.EXCLUDED_CATEGORIES || [];
      const counts = { neg: 0, cat: 0, min: 0 };
      let pageHasOffers = false;
      const isNeueFeed = isNeueToppreisePage();

      for (const card of cards) {
        // 0. Discount Heatmap Highlighting
        const discountVal = extractCardDiscount(card);
        if (CONFIG.HEATMAP_ENABLED && discountVal !== null) {
          const heatStyles = getHeatmapStyles(discountVal, CONFIG.HEATMAP_INTENSITY, CONFIG.HEATMAP_CURVE);
          card.style.setProperty('--tp-heat-bg', heatStyles.bg);
          card.style.setProperty('--tp-heat-border', heatStyles.border);
          card.style.setProperty('--tp-heat-glow', heatStyles.glow);
          card.classList.add('tp-heatmap-active');
        } else {
          card.classList.remove('tp-heatmap-active');
          card.style.removeProperty('--tp-heat-bg');
          card.style.removeProperty('--tp-heat-border');
          card.style.removeProperty('--tp-heat-glow');
        }

        // 1. Category extraction
        const catName = extractCardCategory(card);
        const rootGroup = resolveCategoryGroup(catName, card);

        // 1b. Inject 1-Click Card Quick-Block Action Button (on Neue Toppreise feed)
        if (isNeueFeed) {
          if (catName && !card.querySelector('.tp-card-quick-block')) {
            const quickBlockBtn = document.createElement('button');
            quickBlockBtn.type = 'button';
            quickBlockBtn.className = 'tp-card-quick-block';
            quickBlockBtn.title = `Kategorie "${catName}" (${rootGroup}) ausblenden`;
            quickBlockBtn.innerHTML = `🚫 <span>${catName}</span>`;
            quickBlockBtn.onclick = (e) => {
              e.preventDefault();
              e.stopPropagation();
              e.stopImmediatePropagation();
              const curr = CONFIG.EXCLUDED_CATEGORIES || [];
              const key = `PATH:${rootGroup}/${catName}`;
              if (!curr.includes(key) && !curr.includes(catName)) {
                const updated = [...curr, key];
                saveConfigKey('EXCLUDED_CATEGORIES', updated);
                processListings();
                showToast(`Kategorie "${catName}" ausgeblendet`, 4000, 'Rückgängig', () => {
                  const restored = (CONFIG.EXCLUDED_CATEGORIES || []).filter(c => c !== key && c !== catName);
                  saveConfigKey('EXCLUDED_CATEGORIES', restored);
                  processListings();
                  showToast(`Kategorie "${catName}" wieder eingeblendet`);
                });
              }
            };
            card.appendChild(quickBlockBtn);
          }
        } else {
          const existingQuickBlock = card.querySelector('.tp-card-quick-block');
          if (existingQuickBlock) existingQuickBlock.remove();
        }

        // 2. Negative Text Filter
        const isNeg = matchesNegativeTerms(card, termsList);
        card.classList.toggle('tp-negative-filtered', isNeg);
        if (isNeg) counts.neg++;

        // 3. Category Filter
        const isCatExcluded = catName && isPathExcluded(catName, rootGroup, excludedCats);
        card.classList.toggle('tp-category-filtered', isCatExcluded);
        if (isCatExcluded) counts.cat++;

        // 4. Offer Count Filter
        const offerCount = extractOfferCount(card);
        if (offerCount > 0) pageHasOffers = true;

        const isLowOffers = pageHasOffers && CONFIG.MIN_OFFERS > 0 && offerCount < CONFIG.MIN_OFFERS;
        card.classList.toggle('tp-min-offers-filtered', isLowOffers);
        if (isLowOffers) counts.min++;

        // 5. Best Price Highlighting / Dimming
        if (activeStores.length === 0) {
          card.classList.remove('tp-is-cheapest', 'tp-not-cheapest', 'tp-no-store-offer');
          const badge = card.querySelector('.tp-best-price-badge');
          if (badge) badge.remove();
        } else {
          const dealerRows = card.querySelectorAll('.Plugin_DealerRelProdPriceInfo');
          let matchedRow = null;

          for (const row of dealerRows) {
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
              ? (card.querySelector('.price_information_product .shippingPrice .Plugin_Price') || card.querySelector('.price_information_product .productPrice .Plugin_Price'))
              : (card.querySelector('.price_information_product .productPrice .Plugin_Price') || card.querySelector('.price_information_product .shippingPrice .Plugin_Price'));
            const bestPrice = bestPriceEl ? parsePrice(bestPriceEl.textContent) : 0;

            if (storePrice > 0 && bestPrice > 0) {
              const threshold = bestPrice * (1 + CONFIG.MARGIN_PERCENT / 100);
              const isCheapest = storePrice <= threshold;

              if (isCheapest) {
                card.classList.add('tp-is-cheapest');
                card.classList.remove('tp-not-cheapest', 'tp-no-store-offer');

                let badge = card.querySelector('.tp-best-price-badge');
                if (!badge) {
                  badge = document.createElement('div');
                  badge.className = 'tp-best-price-badge';
                  badge.textContent = 'Best Price';
                  card.appendChild(badge);
                }
              } else {
                card.classList.add('tp-not-cheapest');
                card.classList.remove('tp-is-cheapest', 'tp-no-store-offer');
                const badge = card.querySelector('.tp-best-price-badge');
                if (badge) badge.remove();
              }
            } else {
              card.classList.add('tp-no-store-offer');
              card.classList.remove('tp-is-cheapest', 'tp-not-cheapest');
              const badge = card.querySelector('.tp-best-price-badge');
              if (badge) badge.remove();
            }
          } else {
            card.classList.add('tp-no-store-offer');
            card.classList.remove('tp-is-cheapest', 'tp-not-cheapest');
            const badge = card.querySelector('.tp-best-price-badge');
            if (badge) badge.remove();
          }
        }
      }

      // 6. Re-sorting by Offer Count or Discount
      if (CONFIG.SORT_BY_OFFERS === 'discount-desc' && cards.length > 1) {
        const parent = cards[0].parentElement;
        if (parent) {
          const cardArray = Array.from(cards);
          cardArray.sort((a, b) => {
            const discA = extractCardDiscount(a) ?? -1;
            const discB = extractCardDiscount(b) ?? -1;
            return discB - discA;
          });
          cardArray.forEach(c => parent.appendChild(c));
        }
      } else if (pageHasOffers && CONFIG.SORT_BY_OFFERS !== 'none' && cards.length > 1) {
        const parent = cards[0].parentElement;
        if (parent) {
          const cardArray = Array.from(cards);
          cardArray.sort((a, b) => {
            const countA = extractOfferCount(a);
            const countB = extractOfferCount(b);
            return CONFIG.SORT_BY_OFFERS === 'desc' ? countB - countA : countA - countB;
          });
          cardArray.forEach(c => parent.appendChild(c));
        }
      }

      // 7. Render UI Top Filter Bar
      renderSuiteFilterBar(counts, pageHasOffers);
    } finally {
      isModifyingDOM = false;
    }
  }

  // ─── MODULE 2: PRICE ALARM AUTOMATION ────────────────────────────────────────
  function processPriceAlarmModal() {
    if (!CONFIG.ALARM_ENABLED) return;

    const modalContainer = document.querySelector('.Plugin_NewInfoMailForm');
    if (!modalContainer || modalContainer.dataset.tpAlarmProcessed === 'true') return;

    modalContainer.dataset.tpAlarmProcessed = 'true';
    log('Price Alarm modal detected! Automating configuration...');

    const dialogContainer = modalContainer.closest('.AbstractDialog');
    const closeButton = dialogContainer ? dialogContainer.querySelector('.AbstractDialog_CloseButton') : null;

    const priceEl = modalContainer.querySelector('.shippingPrice .Plugin_Price') ||
      modalContainer.querySelector('.productPrice .Plugin_Price') ||
      document.querySelector('.pageContent .priceContainer .Plugin_Price');

    if (!priceEl) {
      log('Could not parse present price for price alarm.');
      return;
    }

    const presentValue = parsePrice(priceEl.textContent);
    if (presentValue <= 0) {
      log('Parsed price <= 0, skipping alarm automation.');
      return;
    }

    const targetPrice = (presentValue * CONFIG.ALARM_TARGET_PERCENT).toFixed(2);
    log(`Present Price: CHF ${presentValue} -> Setting Target Price: CHF ${targetPrice}`);

    const priceInput = modalContainer.querySelector('input#f_NewInfoMailForm_priceFrom') ||
      modalContainer.querySelector('input[name="im_nimf_pvf"]');
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
    const durationOption = modalContainer.querySelector(`li[data-value="${CONFIG.ALARM_DURATION_DAYS}"]`);
    if (durationOption) durationOption.click();

    const termsCheckbox = modalContainer.querySelector('input#im_nimf_prtrm');
    if (termsCheckbox) {
      termsCheckbox.checked = true;
      termsCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
    }

    if (CONFIG.ALARM_AUTO_SUBMIT) {
      const submitBtn = modalContainer.querySelector('input.f_submitbtn');
      if (submitBtn) {
        log('Auto-submitting price alarm...');
        submitBtn.click();

        let polls = 0;
        const autoCloseInterval = setInterval(() => {
          polls++;
          const isDetached = !document.contains(modalContainer);
          if (isDetached) {
            clearInterval(autoCloseInterval);
            if (closeButton && document.contains(closeButton)) closeButton.click();
          } else if (polls >= 15) {
            clearInterval(autoCloseInterval);
          }
        }, 200);
      }
    }
  }

  // ─── MODULE 3: UNIFIED GLASSMORPHIC SETTINGS UI IN SHADOW DOM ──────────────
  let uiShadowRoot = null;

  function showToast(message, durationMs = 2500, actionLabel = null, onAction = null) {
    ensureSkeleton();
    if (!uiShadowRoot) return;
    const container = uiShadowRoot.getElementById('tp-toast-container');
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
      actionBtn.onclick = (e) => {
        e.stopPropagation();
        toast.remove();
        onAction();
      };
      toast.appendChild(actionBtn);
    }

    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('fade-out');
      toast.addEventListener('transitionend', () => toast.remove());
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
        <dialog id="tp-settings-dialog" popover="auto" role="dialog" aria-modal="true" aria-labelledby="tp-settings-title">
          <h3 id="tp-settings-title">Toppreise Suite Einstellungen</h3>
          <div id="tp-settings-sections">
            <!-- Dynamic settings sections -->
          </div>
          <div class="tp-modal-actions">
            <button type="button" class="tp-btn tp-btn-secondary" id="tp-btn-close" title="Einstellungen abbrechen">Abbrechen</button>
            <button type="button" class="tp-btn tp-btn-primary" id="tp-btn-save" title="Einstellungen speichern">Speichern</button>
          </div>
        </dialog>
        <div id="tp-toast-container"></div>
      `;

      const fabButton = shadow.getElementById('tp-settings-fab');
      const dialog = shadow.getElementById('tp-settings-dialog');
      const btnClose = shadow.getElementById('tp-btn-close');
      const btnSave = shadow.getElementById('tp-btn-save');

      const openModal = () => {
        document.dispatchEvent(new CustomEvent('tp-settings-open'));
        if (typeof dialog.showPopover === 'function') {
          dialog.showPopover();
        } else if (typeof dialog.showModal === 'function') {
          dialog.showModal();
        } else {
          dialog.setAttribute('open', '');
        }
      };

      const closeModal = () => {
        document.documentElement.style.setProperty('--tp-dim-opacity', CONFIG.DIM_OPACITY);
        if (typeof dialog.hidePopover === 'function') {
          dialog.hidePopover();
        } else if (typeof dialog.close === 'function') {
          dialog.close();
        } else {
          dialog.removeAttribute('open');
        }
      };

      fabButton.addEventListener('click', openModal);
      btnClose.addEventListener('click', closeModal);
      shadow.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeModal();
      });

      btnSave.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('tp-settings-save'));
        closeModal();
      });
    }

    return { fabButton: shadow.getElementById('tp-settings-fab'), dialog: shadow.getElementById('tp-settings-dialog'), shadow };
  }

  function setupUI() {
    const { shadow } = ensureSkeleton();

    let section = shadow.getElementById('tp-section-unified-suite');
    if (!section) {
      const sectionsHolder = shadow.getElementById('tp-settings-sections');
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = `
        <div id="tp-section-unified-suite">
          
          <!-- Section 1: Händler Bestpreis -->
          <div class="tp-section-header">1. Händler Bestpreis Highlights</div>
          
          <div class="tp-settings-group">
            <label title="Auswählen, wie nicht-günstigste Angebote behandelt werden">Filter Modus</label>
            <div class="tp-segmented-control">
              <input type="radio" id="tp-mode-highlight-only" name="tp-mode" value="highlight-only">
              <label for="tp-mode-highlight-only" title="Nur Bestpreis-Badge anzeigen">Highlight</label>
              
              <input type="radio" id="tp-mode-dim" name="tp-mode" value="dim">
              <label for="tp-mode-dim" title="Nicht-günstigste Angebote ausgrauen/transparent machen">Dimmen</label>
              
              <input type="radio" id="tp-mode-hide" name="tp-mode" value="hide">
              <label for="tp-mode-hide" title="Nicht-günstigste Angebote komplett ausblenden">Verbergen</label>
            </div>
          </div>
          
          <div class="tp-settings-group">
            <label title="Prozentuale Abweichung vom Bestpreis, die noch als 'Bestpreis' gilt">Preis-Toleranz (%)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-margin-range" min="0" max="15" step="0.5" value="0">
              <input type="number" id="tp-margin-val" min="0" max="100" step="0.1" value="0">
            </div>
          </div>
          
          <div class="tp-settings-group" id="tp-dim-opacity-group">
            <label title="Deckkraft für gedimmte Angebote sowie eingeblendete gefilterte Produkte">Deckkraft / Dimmung (Gedimmt & Gefiltert)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-opacity-range" min="0.05" max="0.95" step="0.05" value="0.25">
              <input type="number" id="tp-opacity-val" min="5" max="95" step="5" value="25">
            </div>
          </div>

          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label title="Preise inklusive Lieferkosten vergleichen">inkl. Versandkosten vergleichen</label>
            </div>
            <label class="tp-switch">
              <input type="checkbox" id="tp-shipping-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>

          <!-- Section 2: Negativer Textfilter -->
          <div class="tp-section-header">2. Negativer Textfilter (Ausschluss)</div>
          <div class="tp-settings-group">
            <label title="Kommagetrennte Wörter eingeben, um passende Produkte auszublenden">Auszuschließende Begriffe (Kommagetrennt)</label>
            <textarea id="tp-negative-terms-input" class="tp-textarea" placeholder="z. B. Hülle, Case, Refurbished, Gebraucht"></textarea>
          </div>

          <!-- Section 3: Angebote & Sortierung -->
          <div class="tp-section-header">3. Angebote & Sortierung</div>
          <div class="tp-settings-group">
            <label title="Produkte mit weniger als N Angeboten ausblenden">Mindestanzahl Angebote (0 = Aus)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-min-offers-range" min="0" max="15" step="1" value="0">
              <input type="number" id="tp-min-offers-val" min="0" max="50" step="1" value="0">
            </div>
          </div>

          <div class="tp-settings-group">
            <label title="Produkte nach Anzahl verfügbarer Händler-Angebote oder Rabatt sortieren">Sortierung nach Angeboten / Rabatt</label>
            <div class="tp-segmented-control">
              <input type="radio" id="tp-sort-none" name="tp-sort-offers" value="none">
              <label for="tp-sort-none" title="Standard-Reihenfolge der Seite beibehalten">Standard</label>
              
              <input type="radio" id="tp-sort-desc" name="tp-sort-offers" value="desc">
              <label for="tp-sort-desc" title="Produkte mit den meisten Angeboten zuerst">Meiste ⬇</label>
              
              <input type="radio" id="tp-sort-asc" name="tp-sort-offers" value="asc">
              <label for="tp-sort-asc" title="Produkte mit den wenigsten Angeboten zuerst">Wenigste ⬆</label>

              <input type="radio" id="tp-sort-discount" name="tp-sort-offers" value="discount-desc">
              <label for="tp-sort-discount" title="Produkte mit dem höchsten Rabatt zuerst">% Rabatt ⬇</label>
            </div>
          </div>

          <!-- Section 4: Preisalarm Auto-Filler -->
          <div class="tp-section-header" style="color: #3b82f6;">4. Preisalarm Auto-Filler</div>
          
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label title="Automatisches Ausfüllen des Preisalarm-Dialogs beim Klick auf die Glocke">Preisalarm Auto-Fill aktivieren</label>
              <span class="tp-switch-desc">Beim Klick auf die Glocke Formular automatisch ausfüllen</span>
            </div>
            <label class="tp-switch tp-blue">
              <input type="checkbox" id="tp-alarm-enabled-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>

          <div class="tp-settings-group">
            <label title="Zielpreis in Prozent vom aktuellen Tiefstpreis berechnen">Zielpreis (% vom aktuellen Preis)</label>
            <div class="tp-range-container tp-blue">
              <input type="range" id="tp-alarm-target-range" min="10" max="95" step="5" value="60">
              <input type="number" id="tp-alarm-target-val" min="1" max="99" step="1" value="60">
            </div>
          </div>

          <div class="tp-settings-group">
            <label title="Laufzeit für den Preisalarm auswählen">Laufzeit Dauer</label>
            <div class="tp-segmented-control tp-segmented-control-blue">
              <input type="radio" id="tp-dur-90" name="tp-alarm-duration" value="90">
              <label for="tp-dur-90">3 Monate</label>

              <input type="radio" id="tp-dur-180" name="tp-alarm-duration" value="180">
              <label for="tp-dur-180">6 Monate</label>

              <input type="radio" id="tp-dur-365" name="tp-alarm-duration" value="365">
              <label for="tp-dur-365">1 Jahr</label>

              <input type="radio" id="tp-dur-730" name="tp-alarm-duration" value="730">
              <label for="tp-dur-730">2 Jahre</label>
            </div>
          </div>

          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label title="Nach dem Ausfüllen das Formular direkt absenden und Fenster schließen">Automatisch Absenden & Schließen</label>
              <span class="tp-switch-desc">Formular direkt einreichen und Dialog schließen</span>
            </div>
            <label class="tp-switch tp-blue">
              <input type="checkbox" id="tp-alarm-autosubmit-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>

          <!-- Section 5: Rabatt-Heatmap -->
          <div class="tp-section-header" style="color: #f43f5e;">5. Rabatt-Heatmap</div>
          
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label title="Produktkarten farblich als Heatmap nach Rabatthöhe einfärben (Heiß 🔥 bis Kalt ❄️)">Rabatt-Heatmap aktivieren</label>
              <span class="tp-switch-desc">Kartenhintergrund färbt sich nach % Rabatt (100% Heiß 🔥 | 0% Kalt ❄️)</span>
            </div>
            <label class="tp-switch tp-rose">
              <input type="checkbox" id="tp-heatmap-enabled-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>

          <div class="tp-settings-group">
            <label title="Farbintensität der Heatmap-Hintergründe">Heatmap-Intensität (%)</label>
            <div class="tp-range-container tp-rose">
              <input type="range" id="tp-heatmap-intensity-range" min="20" max="100" step="5" value="100">
              <input type="number" id="tp-heatmap-intensity-val" min="20" max="100" step="5" value="100">
            </div>
          </div>

        </div>
      `;
      section = tempDiv.firstElementChild;
      sectionsHolder.appendChild(section);
    }

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

    const heatmapEnabledToggle = shadow.getElementById('tp-heatmap-enabled-toggle');
    const heatmapIntensityRange = shadow.getElementById('tp-heatmap-intensity-range');
    const heatmapIntensityVal = shadow.getElementById('tp-heatmap-intensity-val');

    const dur90 = shadow.getElementById('tp-dur-90');
    const dur180 = shadow.getElementById('tp-dur-180');
    const dur365 = shadow.getElementById('tp-dur-365');
    const dur730 = shadow.getElementById('tp-dur-730');

    function syncFieldsFromConfig() {
      const mode = CONFIG.MODE;
      if (mode === 'highlight-only') modeHighlight.checked = true;
      else if (mode === 'hide') modeHide.checked = true;
      else modeDim.checked = true;

      marginRange.value = CONFIG.MARGIN_PERCENT;
      marginVal.value = CONFIG.MARGIN_PERCENT;

      opacityRange.value = CONFIG.DIM_OPACITY;
      opacityVal.value = Math.round(CONFIG.DIM_OPACITY * 100);

      shippingToggle.checked = CONFIG.USE_SHIPPING_PRICE;

      negTermsInput.value = CONFIG.NEGATIVE_TERMS || '';

      minOffersRange.value = CONFIG.MIN_OFFERS || 0;
      minOffersVal.value = CONFIG.MIN_OFFERS || 0;

      const sort = CONFIG.SORT_BY_OFFERS;
      if (sort === 'desc') sortDesc.checked = true;
      else if (sort === 'asc') sortAsc.checked = true;
      else if (sort === 'discount-desc') sortDiscount.checked = true;
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

      heatmapEnabledToggle.checked = CONFIG.HEATMAP_ENABLED !== false;
      const heatIntensityPct = Math.round((CONFIG.HEATMAP_INTENSITY ?? 1.0) * 100);
      heatmapIntensityRange.value = heatIntensityPct;
      heatmapIntensityVal.value = heatIntensityPct;
    }

    // Range Bindings
    marginRange.addEventListener('input', (e) => marginVal.value = e.target.value);
    marginVal.addEventListener('input', (e) => marginRange.value = parseFloat(e.target.value) || 0);

    opacityRange.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value) || 0.25;
      opacityVal.value = Math.round(val * 100);
      document.documentElement.style.setProperty('--tp-dim-opacity', val);
    });
    opacityVal.addEventListener('input', (e) => {
      const val = (parseInt(e.target.value) || 25) / 100;
      opacityRange.value = val;
      document.documentElement.style.setProperty('--tp-dim-opacity', val);
    });

    minOffersRange.addEventListener('input', (e) => minOffersVal.value = e.target.value);
    minOffersVal.addEventListener('input', (e) => minOffersRange.value = parseInt(e.target.value) || 0);

    alarmTargetRange.addEventListener('input', (e) => alarmTargetVal.value = e.target.value);
    alarmTargetVal.addEventListener('input', (e) => alarmTargetRange.value = parseInt(e.target.value) || 60);

    heatmapIntensityRange.addEventListener('input', (e) => heatmapIntensityVal.value = e.target.value);
    heatmapIntensityVal.addEventListener('input', (e) => heatmapIntensityRange.value = parseInt(e.target.value) || 100);

    document.addEventListener('tp-settings-open', () => {
      syncFieldsFromConfig();
    });

    document.addEventListener('tp-settings-save', () => {
      const checkedModeEl = shadow.querySelector('input[name="tp-mode"]:checked');
      if (!checkedModeEl) return;

      saveConfigKey('MODE', checkedModeEl.value);
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

      saveConfigKey('HEATMAP_ENABLED', heatmapEnabledToggle.checked);
      saveConfigKey('HEATMAP_INTENSITY', Math.max(0.2, Math.min(1.0, (parseInt(heatmapIntensityVal.value) || 100) / 100)));

      updateBodyClasses();
      processListings();
      showToast('Toppreise Suite Einstellungen gespeichert');
    });
  }

  // ─── OBSERVER & INITIALIZATION ───────────────────────────────────────────────
  let debounceTimer = null;

  const observer = new MutationObserver((mutations) => {
    if (isModifyingDOM) return;
    const isInternalOnly = mutations.every(m => {
      const target = m.target;
      if (!target) return false;
      const targetEl = target.nodeType === 1 ? target : target.parentElement;
      return targetEl?.id === 'tp-root' || targetEl?.closest('#tp-root');
    });
    if (isInternalOnly) return;

    try {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        processListings();
        processPriceAlarmModal();
      }, CONFIG.OBSERVER_DEBOUNCE_MS);
    } catch (e) {
      log('Observer error:', e);
    }
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: false,
    characterData: false
  });

  if (self.navigation && typeof self.navigation.addEventListener === 'function') {
    self.navigation.addEventListener('navigatesuccess', () => {
      processListings();
      processPriceAlarmModal();
    });
  }

  // Initialize UI controls, filters, and alarm listener
  setupUI();
  processListings();
  processPriceAlarmModal();

})();
