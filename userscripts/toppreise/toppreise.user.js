// ==UserScript==
// @name         Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler
// @namespace    https://github.com/tazztone/scripts
// @version      2.9.4
// @description  All-in-one suite for Toppreise.ch: Highlights best prices, excludes negative keywords, filters categories, sorts/filters by offer count, and automates price alarm creation.
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

  // Power Filters
  NEGATIVE_TERMS: '',
  EXCLUDED_CATEGORIES: [],
  MIN_OFFERS: 0,
  SORT_BY_OFFERS: 'none',
  ENABLE_FILTER_COUNTER: true,
  CATS_EXPANDED: false,

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
  /* Glow and border for products with best price */
  .Plugin_Product.mixedBrowsingList.tp-is-cheapest {
    border: 2px solid #10b981 !important;
    border-radius: 8px !important;
    position: relative !important;
    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15) !important;
    transition: all 0.3s ease !important;
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
    opacity: 0.35 !important;
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
    max-width: 150px !important;
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

  /* Floating Quick-Control Pill Toolbar */
  #tp-quick-toolbar {
    position: fixed;
    bottom: 14px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(30, 41, 59, 0.92);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 24px;
    padding: 6px 16px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    z-index: 99990;
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #f8fafc;
    font-size: 12px;
    font-weight: 600;
  }

  .tp-toolbar-group {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .tp-toolbar-divider {
    width: 1px;
    height: 16px;
    background: rgba(255, 255, 255, 0.15);
  }

  .tp-toolbar-btn {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #cbd5e1;
    padding: 4px 10px;
    border-radius: 14px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 4px;
    user-select: none;
  }
  .tp-toolbar-btn:hover {
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
  }
  .tp-toolbar-btn.tp-active {
    background: rgba(16, 185, 129, 0.25);
    border-color: rgba(16, 185, 129, 0.5);
    color: #34d399;
  }
  .tp-stepper-btn {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #fff;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    user-select: none;
    font-size: 12px;
    transition: background 0.2s ease;
  }
  .tp-stepper-btn:hover {
    background: rgba(16, 185, 129, 0.4);
  }

  /* Compact Single-Row Power Filter Bar with Collapsible Category Drawer */
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
    overflow: visible !important;
  }

  .tp-filter-main-row {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    width: 100% !important;
    max-width: 100% !important;
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
    flex: 1 1 240px !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    min-width: 0 !important;
    max-width: 100% !important;
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

  .tp-btn-toggle {
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
  .tp-btn-toggle:hover {
    background: #334155 !important;
    color: #fff !important;
  }
  .tp-btn-toggle.tp-active {
    background: rgba(16, 185, 129, 0.2) !important;
    border-color: rgba(16, 185, 129, 0.4) !important;
    color: #34d399 !important;
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

  .tp-cat-collapsible-body {
    border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
    padding-top: 8px !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
  }

  .tp-cat-pills-row {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    align-items: center !important;
    flex: 1 !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
  }

  /* High-Contrast Crisp Readable Category Pills */
  .tp-cat-pill {
    padding: 4px 10px !important;
    border-radius: 12px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    user-select: none !important;
    transition: all 0.2s ease !important;
    background: #1e293b !important;
    color: #f8fafc !important;
    border: 1px solid #334155 !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15) !important;
    display: inline-flex !important;
    align-items: center !important;
  }
  .tp-cat-pill:hover {
    background: #334155 !important;
    color: #ffffff !important;
  }
  .tp-cat-pill.tp-excluded {
    background: #7f1d1d !important;
    color: #fca5a5 !important;
    border-color: #ef4444 !important;
    text-decoration: line-through !important;
  }

  /* Group Pills & Collapsible Subcategories */
  .tp-group-wrapper {
    display: inline-flex !important;
    flex-direction: column !important;
    gap: 4px !important;
    position: relative !important;
  }
  .tp-group-pill {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    padding: 4px 10px !important;
    border-radius: 12px !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    cursor: pointer !important;
    user-select: none !important;
    transition: all 0.2s ease !important;
    background: #0f172a !important;
    color: #38bdf8 !important;
    border: 1px solid #0284c7 !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2) !important;
  }
  .tp-group-pill:hover {
    background: #1e293b !important;
    color: #7dd3fc !important;
    border-color: #38bdf8 !important;
  }
  .tp-group-pill.tp-excluded-all {
    background: #7f1d1d !important;
    color: #fca5a5 !important;
    border-color: #ef4444 !important;
    text-decoration: line-through !important;
  }
  .tp-group-pill.tp-excluded-individual {
    background: #9a3412 !important;
    color: #ffedd5 !important;
    border-color: #f97316 !important;
    text-decoration: none !important;
  }
  .tp-group-pill.tp-partial {
    border-color: #f59e0b !important;
    color: #fef08a !important;
    text-decoration: none !important;
  }
  .tp-group-chevron {
    font-size: 9px !important;
    padding: 1px 5px !important;
    border-radius: 4px !important;
    background: rgba(255, 255, 255, 0.15) !important;
    cursor: pointer !important;
    margin-left: 2px !important;
  }
  .tp-group-chevron:hover {
    background: rgba(255, 255, 255, 0.3) !important;
  }

  /* Floating Glassmorphic Group Popover */
  .tp-group-popover {
    position: absolute !important;
    z-index: 100000 !important;
    min-width: 260px !important;
    max-width: 380px !important;
    padding: 10px !important;
    background: rgba(15, 23, 42, 0.95) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important;
    border-radius: 12px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(56, 189, 248, 0.1) !important;
    animation: tpPopoverFadeIn 0.15s cubic-bezier(0.16, 1, 0.3, 1) !important;
  }
  @keyframes tpPopoverFadeIn {
    from { opacity: 0; transform: translateY(-4px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  .tp-popover-header {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding-bottom: 8px !important;
    margin-bottom: 8px !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  }
  .tp-popover-title {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #38bdf8 !important;
  }
  .tp-popover-actions {
    display: flex !important;
    gap: 6px !important;
  }
  .tp-popover-btn {
    font-size: 10px !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    background: rgba(255, 255, 255, 0.1) !important;
    color: #cbd5e1 !important;
    cursor: pointer !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    transition: all 0.15s ease !important;
  }
  .tp-popover-btn:hover {
    background: rgba(56, 189, 248, 0.2) !important;
    color: #ffffff !important;
    border-color: rgba(56, 189, 248, 0.4) !important;
  }
  .tp-popover-search {
    width: 100% !important;
    box-sizing: border-box !important;
    padding: 4px 8px !important;
    margin-bottom: 8px !important;
    font-size: 11px !important;
    color: #e2e8f0 !important;
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(56, 189, 248, 0.25) !important;
    border-radius: 6px !important;
    outline: none !important;
  }
  .tp-popover-search:focus {
    border-color: rgba(56, 189, 248, 0.6) !important;
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.2) !important;
  }
  .tp-popover-body {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    max-height: 250px !important;
    overflow-y: auto !important;
    padding: 2px !important;
  }
  .tp-branch-wrapper {
    width: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 4px !important;
    margin-bottom: 4px !important;
  }
  .tp-branch-header {
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
  }
  .tp-branch-children {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 4px !important;
    padding-left: 12px !important;
    margin-top: 2px !important;
    border-left: 2px solid rgba(56, 189, 248, 0.2) !important;
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
      min-width: 0 !important;
    }
    .tp-btn-toggle, .tp-filter-bar-reset {
      flex: 1 1 auto !important;
      justify-content: center !important;
      text-align: center !important;
      font-size: 11px !important;
      padding: 6px 8px !important;
    }
    #tp-quick-toolbar {
      width: 95% !important;
      max-width: 95% !important;
      flex-wrap: wrap !important;
      justify-content: center !important;
      padding: 6px 10px !important;
      border-radius: 16px !important;
      gap: 6px !important;
    }
    .tp-toolbar-group {
      flex-wrap: wrap !important;
      justify-content: center !important;
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

  /* Top Layer Settings Modal Dialog */
  dialog#tp-settings-dialog {
    box-sizing: border-box;
    width: 92%;
    max-width: 520px;
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
    margin-bottom: 18px;
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
    margin: 16px 0 12px 0;
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

  .tp-cat-pills-container {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    max-height: 140px;
    overflow-y: auto;
    padding: 4px;
    background: rgba(15, 23, 42, 0.4);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }
  .tp-group-wrapper {
    display: inline-flex;
    align-items: center;
    position: relative;
  }
  .tp-group-pill {
    display: inline-flex;
    align-items: center;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.08);
    color: #cbd5e1;
    border: 1px solid rgba(255, 255, 255, 0.05);
    cursor: pointer;
    user-select: none;
    transition: all 0.15s ease;
  }
  .tp-group-pill.tp-excluded-all {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border-color: rgba(239, 68, 68, 0.3);
    text-decoration: line-through;
  }
  .tp-group-pill.tp-excluded-individual,
  .tp-group-pill.tp-partial {
    background: rgba(245, 158, 11, 0.2);
    color: #fcd34d;
    border-color: rgba(245, 158, 11, 0.3);
  }
  .tp-group-chevron {
    margin-left: 4px;
    font-size: 9px;
    opacity: 0.7;
    padding: 2px;
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

  /* Popover styles within Shadow DOM */
  .tp-group-popover {
    position: absolute !important;
    z-index: 100000 !important;
    min-width: 260px !important;
    max-width: 380px !important;
    padding: 10px !important;
    background: rgba(15, 23, 42, 0.95) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important;
    border-radius: 12px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(56, 189, 248, 0.1) !important;
    animation: tpPopoverFadeIn 0.15s cubic-bezier(0.16, 1, 0.3, 1) !important;
  }
  .tp-popover-header {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    margin-bottom: 8px !important;
    gap: 8px !important;
  }
  .tp-popover-title {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #38bdf8 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
  }
  .tp-popover-actions {
    display: flex !important;
    gap: 4px !important;
    flex-shrink: 0 !important;
  }
  .tp-popover-btn {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    color: #cbd5e1 !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
  }
  .tp-popover-btn:hover {
    background: rgba(255, 255, 255, 0.2) !important;
    color: #fff !important;
  }
  .tp-popover-search {
    width: 100% !important;
    box-sizing: border-box !important;
    background: rgba(2, 6, 23, 0.7) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    color: #fff !important;
    padding: 5px 8px !important;
    border-radius: 6px !important;
    font-size: 11px !important;
    margin-bottom: 8px !important;
    outline: none !important;
  }
  .tp-popover-search:focus {
    border-color: #38bdf8 !important;
  }
  .tp-popover-body {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 4px !important;
    max-height: 220px !important;
    overflow-y: auto !important;
    padding-right: 2px !important;
  }
  .tp-cat-pill {
    padding: 4px 10px !important;
    border-radius: 12px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    user-select: none !important;
    transition: all 0.2s ease !important;
    background: #1e293b !important;
    color: #f8fafc !important;
    border: 1px solid #334155 !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15) !important;
    display: inline-flex !important;
    align-items: center !important;
  }
  .tp-cat-pill:hover {
    background: #334155 !important;
    color: #ffffff !important;
  }
  .tp-cat-pill.tp-excluded {
    background: #7f1d1d !important;
    color: #fca5a5 !important;
    border-color: #ef4444 !important;
    text-decoration: line-through !important;
  }
`;

// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  // Fast 2-Layer Storage Helpers with GM_setValue + domain localStorage Failover (Reinstall-Proof)
  const LOCAL_STORAGE_PREFIX = 'tp_suite_v2_';

  const _getValue = (key, def) => {
    try {
      if (typeof GM_getValue !== 'undefined') {
        const val = GM_getValue(key);
        if (val !== undefined && val !== null) return val;
      }
    } catch (e) { }

    // Failover: Try domain localStorage backup if GM_getValue was wiped on script reinstall
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const raw = window.localStorage.getItem(LOCAL_STORAGE_PREFIX + key);
        if (raw !== null) {
          const parsed = JSON.parse(raw);
          // Re-seed extension storage for future fast access
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
    NEGATIVE_TERMS: _getValue('NEGATIVE_TERMS', DEFAULTS.NEGATIVE_TERMS),
    EXCLUDED_CATEGORIES: _getValue('EXCLUDED_CATEGORIES', DEFAULTS.EXCLUDED_CATEGORIES),
    MIN_OFFERS: parseInt(_getValue('MIN_OFFERS', DEFAULTS.MIN_OFFERS)),
    SORT_BY_OFFERS: _getValue('SORT_BY_OFFERS', DEFAULTS.SORT_BY_OFFERS),
    ENABLE_FILTER_COUNTER: _getValue('ENABLE_FILTER_COUNTER', DEFAULTS.ENABLE_FILTER_COUNTER),
    CATS_EXPANDED: _getValue('CATS_EXPANDED', DEFAULTS.CATS_EXPANDED),
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

  // Set of categories detected on active page cards
  const pageCategories = new Set();

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

  // Auto-generated Toppreise Category Lookup Table
  const CATEGORY_LOOKUP = {
    "abenteuer": "Filme",
    "abenteür": "Filme",
    "accessoires": "Garten & Baumarkt",
    "action": "Filme",
    "action cameras": "TV & Video",
    "actioncameras": "TV & Video",
    "actioncams": "TV & Video",
    "actionspiele": "Videogames",
    "activity tracker": "Sport & Freizeit",
    "activity tracker smartwatches": "Sport & Freizeit",
    "activitytracker": "Sport & Freizeit",
    "activitytrackersmartwatches": "Sport & Freizeit",
    "after shave": "Drogerie",
    "aftershave": "Drogerie",
    "akku bohrmaschinen": "Garten & Baumarkt",
    "akku schrauber": "Garten & Baumarkt",
    "akkubohrmaschinen": "Garten & Baumarkt",
    "akkus": "Smartphones & Mobiltelefone",
    "akkus ladegeraete": "Garten & Baumarkt",
    "akkus ladegeräte": "Garten & Baumarkt",
    "akkuschrauber": "Garten & Baumarkt",
    "akkusladegeraete": "Garten & Baumarkt",
    "akkusladegeräte": "Garten & Baumarkt",
    "aktenordner": "Bürobedarf & Schreibwaren",
    "analoge funktelefone": "Smartphones & Mobiltelefone",
    "analoge telefone": "Smartphones & Mobiltelefone",
    "analogefunktelefone": "Smartphones & Mobiltelefone",
    "analogetelefone": "Smartphones & Mobiltelefone",
    "android": "Smartphones & Mobiltelefone",
    "anh&auml;nger &amp; charms": "Uhren",
    "anh&auml;nger&amp;charms": "Uhren",
    "anz&uuml;ge": "Garten & Baumarkt",
    "apple": "Smartphones & Mobiltelefone",
    "apple h10": "Smartphones & Mobiltelefone",
    "apple watch": "Smartphones & Mobiltelefone",
    "appleh10": "Smartphones & Mobiltelefone",
    "applewatch": "Smartphones & Mobiltelefone",
    "arbeitsplatz": "Bürobedarf & Schreibwaren",
    "armbanduhren": "Uhren",
    "audio streaming": "HiFi & Audio",
    "audiostreaming": "HiFi & Audio",
    "auto": "Auto & Motorrad",
    "auto &amp; motorrad": "Auto & Motorrad",
    "auto motorrad": "Auto & Motorrad",
    "auto&amp;motorrad": "Auto & Motorrad",
    "automotorrad": "Auto & Motorrad",
    "autorennbahnen": "Spielwaren",
    "autos": "Spielwaren",
    "av receiver": "HiFi & Audio",
    "avreceiver": "HiFi & Audio",
    "b&uuml;robedarf &amp; schreibwaren": "Bürobedarf & Schreibwaren",
    "b&uuml;robedarf&amp;schreibwaren": "Bürobedarf & Schreibwaren",
    "b&uuml;roeinrichtung": "Bürobedarf & Schreibwaren",
    "b&uuml;roelektronik": "Bürobedarf & Schreibwaren",
    "b&uuml;röinrichtung": "Bürobedarf & Schreibwaren",
    "b&uuml;rölektronik": "Bürobedarf & Schreibwaren",
    "baby": "Haushalt & Küche",
    "baby  &amp; kinderpflege": "Drogerie",
    "baby kinderpflege": "Drogerie",
    "baby&amp;kinderpflege": "Drogerie",
    "babykinderpflege": "Drogerie",
    "back ofenformen": "Haushalt & Küche",
    "backofenformen": "Haushalt & Küche",
    "bademode": "Garten & Baumarkt",
    "batterien &amp; akkus": "Garten & Baumarkt",
    "batterien akkus ladegeraete": "Garten & Baumarkt",
    "batterien akkus ladegeräte": "Garten & Baumarkt",
    "batterien&amp;akkus": "Garten & Baumarkt",
    "batterienakkusladegeraete": "Garten & Baumarkt",
    "batterienakkusladegeräte": "Garten & Baumarkt",
    "bau &amp; konstruktionsspielzeug": "Spielwaren",
    "bau konstruktionsspielzeug": "Spielwaren",
    "bau&amp;konstruktionsspielzeug": "Spielwaren",
    "baukonstruktionsspielzeug": "Spielwaren",
    "beamer": "TV & Video",
    "beat em up": "Videogames",
    "beatemup": "Videogames",
    "bekleidung &amp; schuhe": "Bekleidung & Schuhe",
    "bekleidung accessoires": "Garten & Baumarkt",
    "bekleidung schuhe": "Bekleidung & Schuhe",
    "bekleidung&amp;schuhe": "Bekleidung & Schuhe",
    "bekleidungaccessoires": "Garten & Baumarkt",
    "bekleidungschuhe": "Bekleidung & Schuhe",
    "binden &amp; laminieren": "Bürobedarf & Schreibwaren",
    "binden laminieren": "Bürobedarf & Schreibwaren",
    "binden&amp;laminieren": "Bürobedarf & Schreibwaren",
    "bindenlaminieren": "Bürobedarf & Schreibwaren",
    "biografie": "Filme",
    "blu ray 4k ultra hd filme": "Filme",
    "blu ray filme": "Filme",
    "blu ray player": "TV & Video",
    "bluetooth lautsprecher": "HiFi & Audio",
    "bluetoothlautsprecher": "HiFi & Audio",
    "bluray4kultrahdfilme": "Filme",
    "blurayfilme": "Filme",
    "blurayplayer": "TV & Video",
    "blütooth lautsprecher": "HiFi & Audio",
    "blütoothlautsprecher": "HiFi & Audio",
    "bohrmaschinen &amp; schrauber": "Garten & Baumarkt",
    "bohrmaschinen schrauber": "Garten & Baumarkt",
    "bohrmaschinen&amp;schrauber": "Garten & Baumarkt",
    "bohrmaschinenschrauber": "Garten & Baumarkt",
    "braeter dampfgarer": "Haushalt & Küche",
    "braeterdampfgarer": "Haushalt & Küche",
    "brixies": "Spielwaren",
    "bräter dampfgarer": "Haushalt & Küche",
    "bräterdampfgarer": "Haushalt & Küche",
    "buerobedarf &amp; schreibwaren": "Bürobedarf & Schreibwaren",
    "buerobedarf schreibwaren": "Bürobedarf & Schreibwaren",
    "buerobedarf&amp;schreibwaren": "Bürobedarf & Schreibwaren",
    "buerobedarfschreibwaren": "Bürobedarf & Schreibwaren",
    "bueroeinrichtung": "Bürobedarf & Schreibwaren",
    "bueroelektronik": "Bürobedarf & Schreibwaren",
    "bürobedarf &amp; schreibwaren": "Bürobedarf & Schreibwaren",
    "bürobedarf schreibwaren": "Bürobedarf & Schreibwaren",
    "bürobedarf&amp;schreibwaren": "Bürobedarf & Schreibwaren",
    "bürobedarfschreibwaren": "Bürobedarf & Schreibwaren",
    "büröinrichtung": "Bürobedarf & Schreibwaren",
    "bürölektronik": "Bürobedarf & Schreibwaren",
    "cada": "Spielwaren",
    "camcorder": "TV & Video",
    "camping outdoor": "Sport & Freizeit",
    "campingoutdoor": "Sport & Freizeit",
    "car hifi / car video": "Auto & Motorrad",
    "car hifi car video": "Auto & Motorrad",
    "carhifi/carvideo": "Auto & Motorrad",
    "carhificarvideo": "Auto & Motorrad",
    "cd &amp; sacd player": "HiFi & Audio",
    "cd sacd player": "HiFi & Audio",
    "cd&amp;sacdplayer": "HiFi & Audio",
    "cdsacdplayer": "HiFi & Audio",
    "cobi": "Spielwaren",
    "computer &amp; zubeh&ouml;r": "Computer & Zubehör",
    "computer &amp; zubehoer": "Computer & Zubehör",
    "computer &amp; zubehör": "Computer & Zubehör",
    "computer zubehoer": "Computer & Zubehör",
    "computer zubehör": "Computer & Zubehör",
    "computer&amp;zubeh&ouml;r": "Computer & Zubehör",
    "computer&amp;zubehoer": "Computer & Zubehör",
    "computer&amp;zubehör": "Computer & Zubehör",
    "computerspiele fuer windows": "Videogames",
    "computerspiele für windows": "Videogames",
    "computerspielefuerwindows": "Videogames",
    "computerspielefürwindows": "Videogames",
    "computerzubehoer": "Computer & Zubehör",
    "computerzubehör": "Computer & Zubehör",
    "cover": "Smartphones & Mobiltelefone",
    "damen deodorants": "Drogerie",
    "damend&uuml;fte": "Drogerie",
    "damendeodorants": "Drogerie",
    "damenduefte": "Drogerie",
    "damendüfte": "Drogerie",
    "damenmode": "Garten & Baumarkt",
    "dashboards buttonboxes": "Videogames",
    "dashboardsbuttonboxes": "Videogames",
    "decken wandhalterungen": "TV & Video",
    "deckenwandhalterungen": "TV & Video",
    "deodorant": "Drogerie",
    "digitalkameras": "Foto & Video",
    "djing": "HiFi & Audio",
    "drogerie": "Drogerie",
    "drucker &amp; scanner": "Computer & Zubehör",
    "drucker scanner": "Computer & Zubehör",
    "drucker&amp;scanner": "Computer & Zubehör",
    "druckerscanner": "Computer & Zubehör",
    "dvb receiver": "TV & Video",
    "dvbreceiver": "TV & Video",
    "dvd action thriller horror": "Filme",
    "dvd filme": "Filme",
    "dvd kinder familie": "Filme",
    "dvd komoedie drama": "Filme",
    "dvd komödie drama": "Filme",
    "dvd science fiction fantasy": "Filme",
    "dvd tv dokumentationen": "Filme",
    "dvdactionthrillerhorror": "Filme",
    "dvdfilme": "Filme",
    "dvdkinderfamilie": "Filme",
    "dvdkomoediedrama": "Filme",
    "dvdkomödiedrama": "Filme",
    "dvdsciencefictionfantasy": "Filme",
    "dvdtvdokumentationen": "Filme",
    "e scooter": "Sport & Freizeit",
    "eastern": "Filme",
    "eau de parfum": "Drogerie",
    "eau de toilette": "Drogerie",
    "eaudeparfum": "Drogerie",
    "eaudetoilette": "Drogerie",
    "ebook reader": "Computer & Zubehör",
    "ebookreader": "Computer & Zubehör",
    "einzelkomponenten": "HiFi & Audio",
    "elektrogrills": "Garten & Baumarkt",
    "elektronik": "Computer & Zubehör",
    "elektrozahnbuersten": "Drogerie",
    "elektrozahnbürsten": "Drogerie",
    "erotik": "Garten & Baumarkt",
    "ersatzbuersten": "Drogerie",
    "ersatzbürsten": "Drogerie",
    "escooter": "Sport & Freizeit",
    "experimentierk&auml;sten": "Spielwaren",
    "experimentierkaesten": "Spielwaren",
    "experimentierkästen": "Spielwaren",
    "externe solid state drives ssd": "Computer & Zubehör",
    "externe ssd": "Computer & Zubehör",
    "externesolidstatedrivesssd": "Computer & Zubehör",
    "externessd": "Computer & Zubehör",
    "fairphone": "Smartphones & Mobiltelefone",
    "fairphone h3048": "Smartphones & Mobiltelefone",
    "fairphoneh3048": "Smartphones & Mobiltelefone",
    "familienspiele": "Spielwaren",
    "fantasy": "Filme",
    "fenster tuer": "Garten & Baumarkt",
    "fenster tür": "Garten & Baumarkt",
    "fensterreinigungsroboter": "Haushalt & Küche",
    "fenstertuer": "Garten & Baumarkt",
    "fenstertür": "Garten & Baumarkt",
    "ferngl&auml;ser": "Sport & Freizeit",
    "fernglaeser": "Sport & Freizeit",
    "ferngläser": "Sport & Freizeit",
    "festnetz telefone": "Smartphones & Mobiltelefone",
    "festnetztelefone": "Smartphones & Mobiltelefone",
    "festplatten &amp; ssd": "Computer & Zubehör",
    "festplatten ssd": "Computer & Zubehör",
    "festplatten&amp;ssd": "Computer & Zubehör",
    "festplattenssd": "Computer & Zubehör",
    "filme": "Filme",
    "fischertechnik": "Spielwaren",
    "flight sticks sim flying": "Videogames",
    "flightstickssimflying": "Videogames",
    "fondue": "Haushalt & Küche",
    "fondü": "Haushalt & Küche",
    "foto": "Foto & Video",
    "funkger&auml;te": "Smartphones & Mobiltelefone",
    "funkgeraete": "Smartphones & Mobiltelefone",
    "funkgeräte": "Smartphones & Mobiltelefone",
    "funktelefone": "Smartphones & Mobiltelefone",
    "games": "Videogames",
    "garten": "Garten & Baumarkt",
    "gartenger&auml;te": "Garten & Baumarkt",
    "gartengeraete": "Garten & Baumarkt",
    "gartengeräte": "Garten & Baumarkt",
    "gartenm&ouml;bel": "Garten & Baumarkt",
    "gartenmoebel": "Garten & Baumarkt",
    "gartenmöbel": "Garten & Baumarkt",
    "gasgrills": "Garten & Baumarkt",
    "geschenksets": "Drogerie",
    "geschirr besteck glaeser": "Haushalt & Küche",
    "geschirr besteck gläser": "Haushalt & Küche",
    "geschirr, besteck &amp; gl&auml;ser": "Haushalt & Küche",
    "geschirr,besteck&amp;gl&auml;ser": "Haushalt & Küche",
    "geschirrbesteckglaeser": "Haushalt & Küche",
    "geschirrbesteckgläser": "Haushalt & Küche",
    "gesellschaftsspiele": "Spielwaren",
    "gin": "Haushalt & Küche",
    "google": "Smartphones & Mobiltelefone",
    "google h1825": "Smartphones & Mobiltelefone",
    "googleh1825": "Smartphones & Mobiltelefone",
    "gps geraete": "Sport & Freizeit",
    "gps geräte": "Sport & Freizeit",
    "gps module": "Computer & Zubehör",
    "gps navigations geraete": "Computer & Zubehör",
    "gps navigations geräte": "Computer & Zubehör",
    "gpsgeraete": "Sport & Freizeit",
    "gpsgeräte": "Sport & Freizeit",
    "gpsmodule": "Computer & Zubehör",
    "gpsnavigationsgeraete": "Computer & Zubehör",
    "gpsnavigationsgeräte": "Computer & Zubehör",
    "grafikkarten": "Computer & Zubehör",
    "grafikkarten zubehoer": "Computer & Zubehör",
    "grafikkarten zubehör": "Computer & Zubehör",
    "grafikkartenzubehoer": "Computer & Zubehör",
    "grafikkartenzubehör": "Computer & Zubehör",
    "grappa": "Haushalt & Küche",
    "grillieren": "Garten & Baumarkt",
    "halterungen": "Computer & Zubehör",
    "handfunkgeraete": "Smartphones & Mobiltelefone",
    "handfunkgeräte": "Smartphones & Mobiltelefone",
    "handwerkzeuge": "Garten & Baumarkt",
    "haus": "Garten & Baumarkt",
    "haus &amp; garten": "Garten & Baumarkt",
    "haus garten": "Garten & Baumarkt",
    "haus sicherheitstechnik": "Garten & Baumarkt",
    "haus&amp;garten": "Garten & Baumarkt",
    "hausgarten": "Garten & Baumarkt",
    "haushalt &amp; k&uuml;che": "Haushalt & Küche",
    "haushalt &amp; kueche": "Haushalt & Küche",
    "haushalt &amp; küche": "Haushalt & Küche",
    "haushalt kueche": "Haushalt & Küche",
    "haushalt küche": "Haushalt & Küche",
    "haushalt&amp;k&uuml;che": "Haushalt & Küche",
    "haushalt&amp;kueche": "Haushalt & Küche",
    "haushalt&amp;küche": "Haushalt & Küche",
    "haushaltkueche": "Haushalt & Küche",
    "haushaltküche": "Haushalt & Küche",
    "haushaltsger&auml;te": "Haushalt & Küche",
    "haushaltsgeraete": "Haushalt & Küche",
    "haushaltsgeräte": "Haushalt & Küche",
    "haussicherheitstechnik": "Garten & Baumarkt",
    "headsets": "Smartphones & Mobiltelefone",
    "heften": "Bürobedarf & Schreibwaren",
    "heizung klima": "Garten & Baumarkt",
    "heizungklima": "Garten & Baumarkt",
    "hemden &amp; blusen": "Garten & Baumarkt",
    "hemden&amp;blusen": "Garten & Baumarkt",
    "herren after shave": "Drogerie",
    "herrenaftershave": "Drogerie",
    "herrend&uuml;fte": "Drogerie",
    "herrenduefte": "Drogerie",
    "herrendüfte": "Drogerie",
    "herrenmode": "Garten & Baumarkt",
    "hifi": "HiFi & Audio",
    "hifi &amp; audio": "HiFi & Audio",
    "hifi audio": "HiFi & Audio",
    "hifi einzelkomponenten": "HiFi & Audio",
    "hifi&amp;audio": "HiFi & Audio",
    "hifiaudio": "HiFi & Audio",
    "hifieinzelkomponenten": "HiFi & Audio",
    "holzkohlegrills": "Garten & Baumarkt",
    "home cinema av receiver": "HiFi & Audio",
    "home cinema video": "TV & Video",
    "homecinemaavreceiver": "HiFi & Audio",
    "homecinemavideo": "TV & Video",
    "horror": "Filme",
    "horrorkomoedie": "Filme",
    "horrorkomödie": "Filme",
    "hosen": "Garten & Baumarkt",
    "huelle": "Smartphones & Mobiltelefone",
    "huellen": "Smartphones & Mobiltelefone",
    "hülle": "Smartphones & Mobiltelefone",
    "hüllen": "Smartphones & Mobiltelefone",
    "jeans": "Garten & Baumarkt",
    "jump &#39;n run &amp; geschicklichkeit": "Videogames",
    "jump n run geschicklichkeit": "Videogames",
    "jump&#39;nrun&amp;geschicklichkeit": "Videogames",
    "jumpnrungeschicklichkeit": "Videogames",
    "k&ouml;rperpflege": "Drogerie",
    "k&uuml;chenger&auml;te": "Haushalt & Küche",
    "kaffee  &amp; espressomaschinen": "Haushalt & Küche",
    "kaffee espressomaschinen": "Haushalt & Küche",
    "kaffee&amp;espressomaschinen": "Haushalt & Küche",
    "kaffeeespressomaschinen": "Haushalt & Küche",
    "kalender": "Bürobedarf & Schreibwaren",
    "karten software": "Computer & Zubehör",
    "kartensoftware": "Computer & Zubehör",
    "kartenspiele": "Spielwaren",
    "ketten": "Uhren",
    "kindermode": "Garten & Baumarkt",
    "kindersitze": "Auto & Motorrad",
    "kinderspiele": "Spielwaren",
    "kinderspielzeug": "Spielwaren",
    "klassisches drama": "Filme",
    "klassischesdrama": "Filme",
    "kleider": "Garten & Baumarkt",
    "klimageraete": "Haushalt & Küche",
    "klimageräte": "Haushalt & Küche",
    "klingel tuersprechanlage": "Garten & Baumarkt",
    "klingel türsprechanlage": "Garten & Baumarkt",
    "klingeltuersprechanlage": "Garten & Baumarkt",
    "klingeltürsprechanlage": "Garten & Baumarkt",
    "kochgeschirr": "Haushalt & Küche",
    "kochkellen": "Haushalt & Küche",
    "koerperpflege": "Drogerie",
    "komoedie": "Filme",
    "komödie": "Filme",
    "kontaktlinsen": "Drogerie",
    "kopfh&ouml;rer": "HiFi & Audio",
    "kopfhoerer": "HiFi & Audio",
    "kopfhörer": "HiFi & Audio",
    "krimikomoedie": "Filme",
    "krimikomödie": "Filme",
    "kuechengeraete": "Haushalt & Küche",
    "kuechenhelfer": "Haushalt & Küche",
    "körperpflege": "Drogerie",
    "küchengeräte": "Haushalt & Küche",
    "küchenhelfer": "Haushalt & Küche",
    "ladegeraete netzadapter": "Smartphones & Mobiltelefone",
    "ladegeraetenetzadapter": "Smartphones & Mobiltelefone",
    "ladegeräte netzadapter": "Smartphones & Mobiltelefone",
    "ladegerätenetzadapter": "Smartphones & Mobiltelefone",
    "lampen": "Garten & Baumarkt",
    "lampen leuchtmittel": "Garten & Baumarkt",
    "lampenleuchtmittel": "Garten & Baumarkt",
    "lautsprecher": "HiFi & Audio",
    "lego": "Spielwaren",
    "lego city": "Spielwaren",
    "lego editions": "Spielwaren",
    "lego icons": "Spielwaren",
    "lego ideas": "Spielwaren",
    "lego marvel": "Spielwaren",
    "lego pokemon": "Spielwaren",
    "lego super mario": "Spielwaren",
    "lego technic": "Spielwaren",
    "lego the legend of zelda": "Spielwaren",
    "lego the lord of the rings": "Spielwaren",
    "legocity": "Spielwaren",
    "legoeditions": "Spielwaren",
    "legoicons": "Spielwaren",
    "legoideas": "Spielwaren",
    "legomarvel": "Spielwaren",
    "legopokemon": "Spielwaren",
    "legosupermario": "Spielwaren",
    "legotechnic": "Spielwaren",
    "legothelegendofzelda": "Spielwaren",
    "legothelordoftherings": "Spielwaren",
    "lenkrad komplettsets": "Videogames",
    "lenkradkomplettsets": "Videogames",
    "lenkraeder": "Videogames",
    "lenkräder": "Videogames",
    "lesegeraete fuer speicherkarten": "TV & Video",
    "lesegeraetefuerspeicherkarten": "TV & Video",
    "lesegeräte für speicherkarten": "TV & Video",
    "lesegerätefürspeicherkarten": "TV & Video",
    "lik&ouml;re": "Haushalt & Küche",
    "luftbefeuchter luftentfeuchter luftreiniger": "Haushalt & Küche",
    "luftbefeuchterluftentfeuchterluftreiniger": "Haushalt & Küche",
    "lumibricks funwhole": "Spielwaren",
    "lumibricksfunwhole": "Spielwaren",
    "lust &amp; liebe": "Drogerie",
    "lust liebe": "Drogerie",
    "lust&amp;liebe": "Drogerie",
    "lustliebe": "Drogerie",
    "mainboards": "Computer & Zubehör",
    "mattel brick shop": "Spielwaren",
    "mattelbrickshop": "Spielwaren",
    "mega construx": "Spielwaren",
    "megaconstrux": "Spielwaren",
    "mehr drama": "Filme",
    "mehr komoedie": "Filme",
    "mehr komödie": "Filme",
    "mehrdrama": "Filme",
    "mehrkomoedie": "Filme",
    "mehrkomödie": "Filme",
    "microsd speicherkarten": "TV & Video",
    "microsdspeicherkarten": "TV & Video",
    "mobile akku ladegeraete powerbanks": "Garten & Baumarkt",
    "mobile akku ladegeräte powerbanks": "Garten & Baumarkt",
    "mobileakkuladegeraetepowerbanks": "Garten & Baumarkt",
    "mobileakkuladegerätepowerbanks": "Garten & Baumarkt",
    "mobilteile": "Smartphones & Mobiltelefone",
    "monitore": "Computer & Zubehör",
    "mould king": "Spielwaren",
    "mouldking": "Spielwaren",
    "multicopter": "Spielwaren",
    "multimedia player": "TV & Video",
    "multimediaplayer": "TV & Video",
    "mund  &amp; zahnpflege": "Drogerie",
    "mund zahnpflege": "Drogerie",
    "mund&amp;zahnpflege": "Drogerie",
    "mundduschen": "Drogerie",
    "mundzahnpflege": "Drogerie",
    "musikinstrumente": "HiFi & Audio",
    "musikinstrumente &amp; pro audio": "HiFi & Audio",
    "musikinstrumente pro audio": "HiFi & Audio",
    "musikinstrumente&amp;proaudio": "HiFi & Audio",
    "musikinstrumenteproaudio": "HiFi & Audio",
    "nas systeme": "Computer & Zubehör",
    "nassysteme": "Computer & Zubehör",
    "natur": "Filme",
    "navigation": "Computer & Zubehör",
    "navigationsger&auml;te": "Computer & Zubehör",
    "netzwerktechnik": "Computer & Zubehör",
    "nintendo switch": "Videogames",
    "nintendo switch 2": "Videogames",
    "nintendo switch 2 games": "Videogames",
    "nintendo switch 2 konsolen": "Videogames",
    "nintendo switch games": "Videogames",
    "nintendoswitch": "Videogames",
    "nintendoswitch2": "Videogames",
    "nintendoswitch2games": "Videogames",
    "nintendoswitch2konsolen": "Videogames",
    "nintendoswitchgames": "Videogames",
    "notebooks": "Computer & Zubehör",
    "notebooks tablets ereader": "Computer & Zubehör",
    "notebookstabletsereader": "Computer & Zubehör",
    "oberschalen cover": "Smartphones & Mobiltelefone",
    "oberschalencover": "Smartphones & Mobiltelefone",
    "objektive": "Foto & Video",
    "ohrringe": "Uhren",
    "oneplus": "Smartphones & Mobiltelefone",
    "oneplus h2516": "Smartphones & Mobiltelefone",
    "oneplush2516": "Smartphones & Mobiltelefone",
    "oppo": "Smartphones & Mobiltelefone",
    "oppo h2007": "Smartphones & Mobiltelefone",
    "oppoh2007": "Smartphones & Mobiltelefone",
    "optik": "Sport & Freizeit",
    "outdoor spielzeug": "Spielwaren",
    "outdoorspielzeug": "Spielwaren",
    "pantasy": "Spielwaren",
    "papier": "Bürobedarf & Schreibwaren",
    "parf&uuml;merie": "Drogerie",
    "parfuemerie": "Drogerie",
    "parfum": "Drogerie",
    "parfüm": "Drogerie",
    "parfümerie": "Drogerie",
    "pc komponenten": "Computer & Zubehör",
    "pckomponenten": "Computer & Zubehör",
    "pedale": "Videogames",
    "peripheriegeraete": "Computer & Zubehör",
    "peripheriegeräte": "Computer & Zubehör",
    "pfannensets": "Haushalt & Küche",
    "plattenspieler": "HiFi & Audio",
    "playstation 4": "Videogames",
    "playstation 5": "Videogames",
    "playstation4": "Videogames",
    "playstation5": "Videogames",
    "portable lautsprecher": "HiFi & Audio",
    "portablelautsprecher": "HiFi & Audio",
    "portables": "HiFi & Audio",
    "powerbanks": "Garten & Baumarkt",
    "produktpreis": "Garten & Baumarkt",
    "professional audio djing": "HiFi & Audio",
    "professionalaudiodjing": "HiFi & Audio",
    "prozessoren": "Computer & Zubehör",
    "ps4 games": "Videogames",
    "ps4games": "Videogames",
    "ps5 games": "Videogames",
    "ps5games": "Videogames",
    "radios": "HiFi & Audio",
    "radios radio recorder": "HiFi & Audio",
    "radiosradiorecorder": "HiFi & Audio",
    "rasur &amp; haarpflege": "Drogerie",
    "rasur haarpflege": "Drogerie",
    "rasur&amp;haarpflege": "Drogerie",
    "rasurhaarpflege": "Drogerie",
    "rc modelle": "Spielwaren",
    "rcmodelle": "Spielwaren",
    "receiver": "HiFi & Audio",
    "reifen": "Auto & Motorrad",
    "rennspiele": "Videogames",
    "ringe": "Uhren",
    "rollenspiele &amp; adventures": "Videogames",
    "rollenspiele adventures": "Videogames",
    "rollenspiele&amp;adventures": "Videogames",
    "rollenspieleadventures": "Videogames",
    "romantische komoedie": "Filme",
    "romantische komödie": "Filme",
    "romantischekomoedie": "Filme",
    "romantischekomödie": "Filme",
    "ros&eacute;weine": "Haushalt & Küche",
    "rotweine": "Haushalt & Küche",
    "rum": "Haushalt & Küche",
    "s&auml;gen &amp; fr&auml;sen": "Garten & Baumarkt",
    "s&auml;gen&amp;fr&auml;sen": "Garten & Baumarkt",
    "s&uuml;ssweine": "Haushalt & Küche",
    "saegen fraesen": "Garten & Baumarkt",
    "saegenfraesen": "Garten & Baumarkt",
    "samsung": "Smartphones & Mobiltelefone",
    "samsung h1": "Smartphones & Mobiltelefone",
    "samsungh1": "Smartphones & Mobiltelefone",
    "saug und wischroboter": "Haushalt & Küche",
    "saugroboter": "Haushalt & Küche",
    "saugroboter wischroboter": "Haushalt & Küche",
    "saugroboterwischroboter": "Haushalt & Küche",
    "saugundwischroboter": "Haushalt & Küche",
    "schaumweine": "Haushalt & Küche",
    "scheren": "Haushalt & Küche",
    "schleifen wetzen": "Haushalt & Küche",
    "schleifenwetzen": "Haushalt & Küche",
    "schmuck": "Uhren",
    "schneidunterlagen": "Haushalt & Küche",
    "schreibmaterial": "Bürobedarf & Schreibwaren",
    "schuhe": "Garten & Baumarkt",
    "science fiction": "Filme",
    "sciencefiction": "Filme",
    "sd speicherkarten": "TV & Video",
    "sdspeicherkarten": "TV & Video",
    "sensoren melder": "Garten & Baumarkt",
    "sensorenmelder": "Garten & Baumarkt",
    "shirts": "Garten & Baumarkt",
    "sicherheit ueberwachung": "Garten & Baumarkt",
    "sicherheit überwachung": "Garten & Baumarkt",
    "sicherheitstechnik": "Garten & Baumarkt",
    "sicherheitueberwachung": "Garten & Baumarkt",
    "sicherheitüberwachung": "Garten & Baumarkt",
    "sim racing flying": "Videogames",
    "sim rigs rennsitze": "Videogames",
    "simracingflying": "Videogames",
    "simrigsrennsitze": "Videogames",
    "simulationen": "Videogames",
    "smart home": "Garten & Baumarkt",
    "smart speaker": "HiFi & Audio",
    "smarthome": "Garten & Baumarkt",
    "smartphone zubeh&ouml;r": "Smartphones & Mobiltelefone",
    "smartphones": "Smartphones & Mobiltelefone",
    "smartphones &amp; mobiltelefone": "Smartphones & Mobiltelefone",
    "smartphones mobiltelefone": "Smartphones & Mobiltelefone",
    "smartphones&amp;mobiltelefone": "Smartphones & Mobiltelefone",
    "smartphonesmobiltelefone": "Smartphones & Mobiltelefone",
    "smartphonezubeh&ouml;r": "Smartphones & Mobiltelefone",
    "smartspeaker": "HiFi & Audio",
    "smartwatches": "Smartphones & Mobiltelefone",
    "sofortbildkameras": "Foto & Video",
    "solid state drive": "Computer & Zubehör",
    "solidstatedrive": "Computer & Zubehör",
    "sonstiges": "Smartphones & Mobiltelefone",
    "sonstiges zubehoer fuer iphone": "Smartphones & Mobiltelefone",
    "sonstiges zubehör für iphone": "Smartphones & Mobiltelefone",
    "sonstigeszubehoerfueriphone": "Smartphones & Mobiltelefone",
    "sonstigeszubehörfüriphone": "Smartphones & Mobiltelefone",
    "soundbars": "HiFi & Audio",
    "speicherkarten": "TV & Video",
    "spiegelreflexkameras": "Foto & Video",
    "spielwaren": "Spielwaren",
    "spielwaren &amp; modellbau": "Spielwaren",
    "spielwaren&amp;modellbau": "Spielwaren",
    "spielzeugfiguren roboter": "Spielwaren",
    "spielzeugfigurenroboter": "Spielwaren",
    "spielzeugroboter": "Spielwaren",
    "spirituosen": "Haushalt & Küche",
    "sport &amp; freizeit": "Sport & Freizeit",
    "sport freizeit": "Sport & Freizeit",
    "sport pulsuhren": "Sport & Freizeit",
    "sport&amp;freizeit": "Sport & Freizeit",
    "sportfreizeit": "Sport & Freizeit",
    "sportgeraete": "Sport & Freizeit",
    "sportgeräte": "Sport & Freizeit",
    "sportpulsuhren": "Sport & Freizeit",
    "sportspiele": "Videogames",
    "ssd": "Computer & Zubehör",
    "ssds": "Computer & Zubehör",
    "stative": "Foto & Video",
    "stative studiozubehoer": "Foto & Video",
    "stative studiozubehör": "Foto & Video",
    "stativestudiozubehoer": "Foto & Video",
    "stativestudiozubehör": "Foto & Video",
    "staubsauger": "Haushalt & Küche",
    "stempeln": "Bürobedarf & Schreibwaren",
    "strategie  &amp; rollenspiele": "Spielwaren",
    "strategie rollenspiele": "Spielwaren",
    "strategie&amp;rollenspiele": "Spielwaren",
    "strategierollenspiele": "Spielwaren",
    "streaming audio": "HiFi & Audio",
    "streamingaudio": "HiFi & Audio",
    "subwoofer": "HiFi & Audio",
    "systemkameras": "Foto & Video",
    "sägen fräsen": "Garten & Baumarkt",
    "sägenfräsen": "Garten & Baumarkt",
    "tablets": "Computer & Zubehör",
    "taschen &amp; cover f&uuml;r iphone": "Smartphones & Mobiltelefone",
    "taschen cover": "Smartphones & Mobiltelefone",
    "taschen cover fuer iphone": "Smartphones & Mobiltelefone",
    "taschen cover für iphone": "Smartphones & Mobiltelefone",
    "taschen&amp;coverf&uuml;riphone": "Smartphones & Mobiltelefone",
    "taschencover": "Smartphones & Mobiltelefone",
    "taschencoverfueriphone": "Smartphones & Mobiltelefone",
    "taschencoverfüriphone": "Smartphones & Mobiltelefone",
    "taschenmesser &amp; tools": "Sport & Freizeit",
    "taschenmesser tools": "Sport & Freizeit",
    "taschenmesser&amp;tools": "Sport & Freizeit",
    "taschenmessertools": "Sport & Freizeit",
    "taschenrechner": "Bürobedarf & Schreibwaren",
    "telefon &amp; funk": "Smartphones & Mobiltelefone",
    "telefon &amp; voip": "Smartphones & Mobiltelefone",
    "telefon voip": "Smartphones & Mobiltelefone",
    "telefon&amp;funk": "Smartphones & Mobiltelefone",
    "telefon&amp;voip": "Smartphones & Mobiltelefone",
    "telefone": "Smartphones & Mobiltelefone",
    "telefonvoip": "Smartphones & Mobiltelefone",
    "textilien": "Haushalt & Küche",
    "thermometer": "Haushalt & Küche",
    "thriller": "Filme",
    "tmc receiver": "Computer & Zubehör",
    "tmcreceiver": "Computer & Zubehör",
    "toepfe": "Haushalt & Küche",
    "topfdeckel": "Haushalt & Küche",
    "topfsets": "Haushalt & Küche",
    "tuner": "HiFi & Audio",
    "tv &amp; video": "TV & Video",
    "tv ger&auml;te": "TV & Video",
    "tv geraete": "TV & Video",
    "tv geraete zubehoer": "TV & Video",
    "tv geräte": "TV & Video",
    "tv geräte zubehör": "TV & Video",
    "tv receiver": "TV & Video",
    "tv video": "TV & Video",
    "tv&amp;video": "TV & Video",
    "tvger&auml;te": "TV & Video",
    "tvgeraete": "TV & Video",
    "tvgeraetezubehoer": "TV & Video",
    "tvgeräte": "TV & Video",
    "tvgerätezubehör": "TV & Video",
    "tvreceiver": "TV & Video",
    "tvvideo": "TV & Video",
    "töpfe": "Haushalt & Küche",
    "uhren": "Uhren",
    "unisexd&uuml;fte": "Drogerie",
    "unisexduefte": "Drogerie",
    "unisexdüfte": "Drogerie",
    "velos": "Sport & Freizeit",
    "velotraeger": "Sport & Freizeit",
    "veloträger": "Sport & Freizeit",
    "ventilatoren heizgeraete": "Haushalt & Küche",
    "ventilatoren heizgeräte": "Haushalt & Küche",
    "ventilatorenheizgeraete": "Haushalt & Küche",
    "ventilatorenheizgeräte": "Haushalt & Küche",
    "verbrauchsmaterial": "Computer & Zubehör",
    "verbrauchsmaterial fuer drucker": "Computer & Zubehör",
    "verbrauchsmaterial für drucker": "Computer & Zubehör",
    "verbrauchsmaterialfuerdrucker": "Computer & Zubehör",
    "verbrauchsmaterialfürdrucker": "Computer & Zubehör",
    "verpacken &amp; versand": "Bürobedarf & Schreibwaren",
    "verpacken versand": "Bürobedarf & Schreibwaren",
    "verpacken&amp;versand": "Bürobedarf & Schreibwaren",
    "verpackenversand": "Bürobedarf & Schreibwaren",
    "verst&auml;rker": "HiFi & Audio",
    "verstaerker": "HiFi & Audio",
    "verstärker": "HiFi & Audio",
    "videogames": "Videogames",
    "voice over ip voip": "Smartphones & Mobiltelefone",
    "voiceoveripvoip": "Smartphones & Mobiltelefone",
    "voip router": "Smartphones & Mobiltelefone",
    "voip telefone": "Smartphones & Mobiltelefone",
    "voiprouter": "Smartphones & Mobiltelefone",
    "voiptelefone": "Smartphones & Mobiltelefone",
    "vr brillen": "Smartphones & Mobiltelefone",
    "vrbrillen": "Smartphones & Mobiltelefone",
    "w&auml;sche": "Garten & Baumarkt",
    "wecker": "Uhren",
    "wein": "Haushalt & Küche",
    "wein &amp; spirituosen": "Haushalt & Küche",
    "wein spirituosen": "Haushalt & Küche",
    "wein&amp;spirituosen": "Haushalt & Küche",
    "weinspirituosen": "Haushalt & Küche",
    "weissweine": "Haushalt & Küche",
    "weitere...": "Garten & Baumarkt",
    "werkstatt": "Garten & Baumarkt",
    "werkzeuge &amp; werkstatt": "Garten & Baumarkt",
    "werkzeuge werkstatt": "Garten & Baumarkt",
    "werkzeuge&amp;werkstatt": "Garten & Baumarkt",
    "werkzeugewerkstatt": "Garten & Baumarkt",
    "western": "Filme",
    "wheelbases": "Videogames",
    "whiskey": "Haushalt & Küche",
    "wischroboter": "Haushalt & Küche",
    "wodka": "Haushalt & Küche",
    "wohnen": "Garten & Baumarkt",
    "wuerzen": "Haushalt & Küche",
    "würzen": "Haushalt & Küche",
    "xbox series x": "Videogames",
    "xbox series x games": "Videogames",
    "xboxseriesx": "Videogames",
    "xboxseriesxgames": "Videogames",
    "xiaomi": "Smartphones & Mobiltelefone",
    "xiaomi h2460": "Smartphones & Mobiltelefone",
    "xiaomih2460": "Smartphones & Mobiltelefone",
    "xqd cfexpress speicherkarten": "TV & Video",
    "xqdcfexpressspeicherkarten": "TV & Video",
    "zentralen starter kits": "Garten & Baumarkt",
    "zentralenstarterkits": "Garten & Baumarkt",
    "zubeh&ouml;r": "Smartphones & Mobiltelefone",
    "zubeh&ouml;r f&uuml;r iphone": "Smartphones & Mobiltelefone",
    "zubeh&ouml;rf&uuml;riphone": "Smartphones & Mobiltelefone",
    "zubehoer fuer festnetz telefone": "Smartphones & Mobiltelefone",
    "zubehoer fuer funkgeraete": "Smartphones & Mobiltelefone",
    "zubehoer fuer kochgeschirr": "Haushalt & Küche",
    "zubehoer fuer mobiltelefone": "Smartphones & Mobiltelefone",
    "zubehoer fuer nintendo switch": "Videogames",
    "zubehoer fuer nintendo switch 2": "Videogames",
    "zubehoer fuer rc modelle": "Spielwaren",
    "zubehoer fuer sportgeraete": "Sport & Freizeit",
    "zubehoerfuerfestnetztelefone": "Smartphones & Mobiltelefone",
    "zubehoerfuerfunkgeraete": "Smartphones & Mobiltelefone",
    "zubehoerfuerkochgeschirr": "Haushalt & Küche",
    "zubehoerfuermobiltelefone": "Smartphones & Mobiltelefone",
    "zubehoerfuernintendoswitch": "Videogames",
    "zubehoerfuernintendoswitch2": "Videogames",
    "zubehoerfuerrcmodelle": "Spielwaren",
    "zubehoerfuersportgeraete": "Sport & Freizeit",
    "zubehör für festnetz telefone": "Smartphones & Mobiltelefone",
    "zubehör für funkgeräte": "Smartphones & Mobiltelefone",
    "zubehör für kochgeschirr": "Haushalt & Küche",
    "zubehör für mobiltelefone": "Smartphones & Mobiltelefone",
    "zubehör für nintendo switch": "Videogames",
    "zubehör für nintendo switch 2": "Videogames",
    "zubehör für rc modelle": "Spielwaren",
    "zubehör für sportgeräte": "Sport & Freizeit",
    "zubehörfürfestnetztelefone": "Smartphones & Mobiltelefone",
    "zubehörfürfunkgeräte": "Smartphones & Mobiltelefone",
    "zubehörfürkochgeschirr": "Haushalt & Küche",
    "zubehörfürmobiltelefone": "Smartphones & Mobiltelefone",
    "zubehörfürnintendoswitch": "Videogames",
    "zubehörfürnintendoswitch2": "Videogames",
    "zubehörfürrcmodelle": "Spielwaren",
    "zubehörfürsportgeräte": "Sport & Freizeit"
};

  let dynamicCatMap = _getValue('DYNAMIC_CAT_MAP', {});
  let isDynamicMapDirty = false;

  function flushDynamicMap() {
    if (isDynamicMapDirty) {
      saveConfigKey('DYNAMIC_CAT_MAP', dynamicCatMap);
      isDynamicMapDirty = false;
    }
  }

  function normalizeRootSlug(slug) {
    if (!slug) return null;
    const clean = slug.split('-c')[0].toLowerCase().trim();
    const spaceSlug = clean.replace(/-/g, ' ');
    const noHyphen = clean.replace(/-/g, '');
    return CATEGORY_LOOKUP[clean] || CATEGORY_LOOKUP[spaceSlug] || CATEGORY_LOOKUP[noHyphen] || null;
  }

  function normalizeUmlautKey(str) {
    if (!str) return '';
    return str.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

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

  function extractSubcatFromExclusionKey(key) {
    if (!key) return null;
    if (key.startsWith('GROUP:')) return null;
    if (key.startsWith('PATH:')) {
      const parts = key.slice(5).split('/');
      return parts.slice(1).join('/');
    }
    return key;
  }

  const BRAND_RULES = [
    { regex: /\b(lego|legos|playmobil|cobi|cada|mega construx|fischertechnik|ravensburger|schleich|barbie|hot wheels|action figuren|funko|nerf|amiibo|spielwaren|spielzeug|puppe|puppen|pluesch|plüsch|autorennbahn|rc modelle|multicopter|puzzles|gesellschaftsspiele|familienspiele|kartenspiele)\b/i, group: 'Spielwaren' },
    { regex: /\b(fritteuse|fritteusen|heissluftfritteuse|heissluftfritteusen|vollautomat|vollautomaten|kaffee|espressomaschine|espressomaschinen|kaffeemuehle|kaffeemühle|kuechengeraet|kuechengeraete|küchengerät|küchengeräte|haushaltsgeraet|haushaltsgeraete|haushaltsgerät|haushaltsgeräte|staubsauger|saugroboter|wischroboter|fensterreinigungsroboter|mikrowelle|mikrowellen|backofen|herd|kuehlschrank|kühlschrank|gefrierschrank|geschirrspueler|geschirrspüler|waschmaschine|waschmaschinen|waeschetrockner|wäschetrockner|mixer|blender|wasserkocher|toaster|thermoskanne|abfallsystem|raumduft|dampfgarer|slowcooker|saftpresse|entsafter|geschirr|besteck|glaeser|gläser|topf|toepfe|töpfe|pfanne|pfannen|kochgeschirr|spirituosen|wein|whisky|gin|rum|vodka)\b/i, group: 'Haushalt & Küche' },
    { regex: /\b(haarglaetter|haarglätter|glaetteisen|glätteisen|bartschneider|haarschneider|rasierer|elektrorasierer|epilierer|haartrockner|foehn|föhn|zahnbuerste|zahnbürste|zahnbuersten|zahnbürsten|elektrozahnbuerste|parfum|parfüm|duft|duefte|düfte|eau de|duschpflege|duschgel|shampoo|seife|geschenkset|geschenksets|hautpflege|koerperpflege|körperpflege|kosmetik|make-up|makeup|sonnenschutz|kontaktlinsen|hygiene)\b/i, group: 'Drogerie' },
    { regex: /\b(usb|speicherstick|speichersticks|ssd|hdds?|solid state|festplatte|festplatten|grafikkarte|grafikkarten|notebook|notebooks|laptop|laptops|tablet|tablets|ebook|monitore|monitor|drucker|scanner|nas|mainboard|mainboards|prozessor|prozessoren|cpu|gpu|pc gehaeuse|netzteil|netzteile|ladegeraet|ladegerät|netzadapter|kabel|hub|dockingstation|tastatur|tastaturen|maus|maeuse|mäuse|mausmatte|webcam|headset|aktenvernichter|papierschredder|arbeitsspeicher|ram|netzwerk|wlan|router|switch|server|western digital)\b/i, group: 'Computer & Zubehör' },
    { regex: /\b(smartphone|smartphones|mobiltelefon|mobiltelefone|handy|handys|iphone|galaxy|pixel|smartring|smartringe|smartwatch|smartwatches|activity tracker|huelle|huellen|hülle|hüllen|cover|schutzfolie|panzerglas|ladekabel|powerbank|powerbanks|magsafe|funktelefon|festnetz)\b/i, group: 'Smartphones & Mobiltelefone' },
    { regex: /\b(kopfhoerer|kopfhörer|in-ear|earbuds|lautsprecher|bluetooth lautsprecher|soundbar|plattenspieler|receiver|av receiver|verstaerker|verstärker|hifi|radio|cd player|dac|subwoofer|mikrofon|musikinstrument|gitarre|piano|keyboard)\b/i, group: 'HiFi & Audio' },
    { regex: /\b(tv|fernseher|beamer|projektor|home cinema|heimkino|blu-ray player|dvd player|actioncam|actionkamera|camcorder|media player|streaming stick|chromecast|apple tv)\b/i, group: 'TV & Video' },
    { regex: /\b(kamera|kameras|digitalkamera|spiegellose|dslr|objektiv|objektive|stativ|stative|blitz|fotostudio|drohne|sofortbildkamera)\b/i, group: 'Foto & Video' },
    { regex: /\b(dvd|blu-ray|blu ray|4k ultra hd|film|filme|kino|serie|tv serien|western|abenteuer|action|krimi|drama|komoedie|komödie|thriller|horror|anime|dokumentation)\b/i, group: 'Filme' },
    { regex: /\b(game|games|spiel|spiele|nintendo|switch|playstation|ps5|ps4|ps3|xbox|pc spiele|konsole|konsolen|gamepad|controller|lenkrad|vr headset|amiibo|simulationen|rennspiel)\b/i, group: 'Videogames' },
    { regex: /\b(crosstrainer|laufband|laufbaender|laufbänder|ergometer|rudergeraet|rudergerät|fitness|krafttraining|hantel|hanteln|matten|velo|velos|fahrrad|ebike|e-bike|velohelm|skibrille|skihelm|koffer|rucksack|taschenmesser|fernglas|camping|zelt|schlafsack|tretroller|scooter|inline skates|gps|navigation|navigations)\b/i, group: 'Sport & Freizeit' },
    { regex: /\b(reifen|pneus|sommerreifen|winterreifen|allwetterreifen|felgen|dachbox|dachboxen|dachtraeger|dachträger|kindersitz|kindersitze|autozubehoer|car hifi|motorradhelm|dashcam)\b/i, group: 'Auto & Motorrad' },
    { regex: /\b(rasenmaeher|rasenmäher|rasenroboter|grill|gasgrill|elektrogrill|holzkohlegrill|bohrmaschine|akkuschrauber|saege|säge|schleifer|schalter|taster|steckdose|lampe|lampen|leuchtmittel|led|smart home|gartenmoebel|gartenmöbel|hochdruckreiniger|werkzeug|werkzeuge)\b/i, group: 'Garten & Baumarkt' },
    { regex: /\b(uhr|uhren|armbanduhr|damenuhr|herrenuhr|chronograph|automatikuhr|wanduhr|wecker)\b/i, group: 'Uhren' },
    { regex: /\b(kleidung|bekleidung|jacke|jacken|hose|hosen|t-shirt|pullover|hemd|kleid|schuhe|sneaker|stiefel|tasche|taschen|handtasche|rucksack|sonnenbrille|sonnenbrillen|schmuck|ring|kette)\b/i, group: 'Kleidung & Mode' },
    { regex: /\b(buch|buecher|bücher|roman|taschenbuch|sachbuch|hoerbuch|hörbuch|comic|manga|zeitschrift)\b/i, group: 'Bücher & Medien' }
  ];

  function resolveCategoryPath(categoryName, card = null) {
    if (!categoryName) return ['Sonstiges', 'Sonstiges', 'Sonstiges'];
    const norm = categoryName.trim().toLowerCase();
    const slug = norm.replace(/[^a-z0-9]/g, '');
    const spaceSlug = norm.replace(/-/g, ' ');
    const umlautNorm = normalizeUmlautKey(norm);

    if (card) {
      const hrefs = getCardHrefs(card);
      for (const href of hrefs) {
        const match = href.match(/\/(?:preisvergleich|produktsuche)\/([^\/]+)\//i);
        if (match && match[1]) {
          const rootSlug = match[1].split('-c')[0];
          const canonicalRoot = normalizeRootSlug(rootSlug);
          if (canonicalRoot) {
            if (!dynamicCatMap[norm]) { dynamicCatMap[norm] = canonicalRoot; isDynamicMapDirty = true; }
            if (!dynamicCatMap[slug]) { dynamicCatMap[slug] = canonicalRoot; isDynamicMapDirty = true; }
            if (!dynamicCatMap[spaceSlug]) { dynamicCatMap[spaceSlug] = canonicalRoot; isDynamicMapDirty = true; }
            return [canonicalRoot, categoryName, categoryName];
          }
        }
      }
    }

    let root = CATEGORY_LOOKUP[norm] || CATEGORY_LOOKUP[slug] || CATEGORY_LOOKUP[spaceSlug] || CATEGORY_LOOKUP[umlautNorm];

    if (!root) {
      root = dynamicCatMap[norm] || dynamicCatMap[slug] || dynamicCatMap[spaceSlug] || dynamicCatMap[umlautNorm];
    }

    if (!root) {
      for (const rule of BRAND_RULES) {
        if (rule.regex.test(norm) || rule.regex.test(spaceSlug)) {
          root = rule.group;
          break;
        }
      }
    }

    if (!root) {
      const words = norm.split(/\s+/);
      for (let i = words.length - 1; i >= 1; i--) {
        const prefixKey = words.slice(0, i).join(' ');
        if (CATEGORY_LOOKUP[prefixKey]) {
          root = CATEGORY_LOOKUP[prefixKey];
          break;
        }
      }
    }

    if (!root) {
      const pageBreadcrumb = document.querySelector('.breadcrumb, #Breadcrumb, [class*="breadcrumb"]');
      if (pageBreadcrumb) {
        const bcLink = pageBreadcrumb.querySelector('a[href*="/produktsuche/"], a[href*="/preisvergleich/"]');
        if (bcLink) {
          const href = bcLink.getAttribute('href') || '';
          const match = href.match(/\/(?:produktsuche|preisvergleich)\/([^\/]+)\//i);
          if (match && match[1]) {
            const formattedRoot = normalizeRootSlug(match[1].split('-c')[0]);
            if (formattedRoot) root = formattedRoot;
          }
        }
      }
    }

    if (!root) root = 'Sonstiges';

    return [root, categoryName, categoryName];
  }

  function resolveCategoryGroup(categoryName, card = null) {
    const path = resolveCategoryPath(categoryName, card);
    return path[0] || 'Sonstiges';
  }

  function isPathExcluded(catName, rootGroup, excludedCats = []) {
    if (!excludedCats || excludedCats.length === 0) return false;
    if (excludedCats.includes(`GROUP:${rootGroup}`)) return true;
    if (catName && excludedCats.includes(catName)) return true;
    if (catName && excludedCats.includes(`PATH:${rootGroup}/${catName}`)) return true;
    return false;
  }

  let activePopover = null;

  function closeActivePopover() {
    if (activePopover) {
      activePopover.remove();
      activePopover = null;
    }
  }

  document.addEventListener('click', (e) => {
    if (activePopover && !activePopover.contains(e.target) && !e.target.closest('.tp-group-pill')) {
      closeActivePopover();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && activePopover) {
      closeActivePopover();
    }
  });

  function toggleGroupPopover(anchorEl, rootGroup, subcats, getExcludedCats, updateExcludedCats, mountContainer = document.body) {
    if (activePopover && activePopover.dataset.rootGroup === rootGroup) {
      closeActivePopover();
      return;
    }
    closeActivePopover();

    const popover = document.createElement('div');
    popover.className = 'tp-group-popover';
    popover.dataset.rootGroup = rootGroup;

    const popoverWidth = 320;
    const isCustomMount = mountContainer && mountContainer !== document.body;

    if (isCustomMount) {
      const rect = anchorEl.getBoundingClientRect();
      const containerRect = mountContainer.getBoundingClientRect();
      popover.style.top = `${rect.bottom - containerRect.top + 6 + mountContainer.scrollTop}px`;
      let left = rect.left - containerRect.left;
      if (left + popoverWidth > containerRect.width - 16) {
        left = Math.max(8, containerRect.width - popoverWidth - 16);
      }
      popover.style.left = `${left}px`;
    } else {
      const rect = anchorEl.getBoundingClientRect();
      const topPos = rect.bottom + 6 + window.scrollY;
      let leftPos = rect.left + window.scrollX;
      if (rect.left + popoverWidth > window.innerWidth - 16) {
        leftPos = Math.max(16, window.innerWidth - popoverWidth - 16 + window.scrollX);
      }
      popover.style.top = `${topPos}px`;
      popover.style.left = `${leftPos}px`;
    }

    const header = document.createElement('div');
    header.className = 'tp-popover-header';

    const title = document.createElement('div');
    title.className = 'tp-popover-title';
    title.textContent = `${getGroupEmoji(rootGroup)} ${rootGroup} (${subcats.length})`;

    const actions = document.createElement('div');
    actions.className = 'tp-popover-actions';

    const btnHideAll = document.createElement('button');
    btnHideAll.className = 'tp-popover-btn';
    btnHideAll.textContent = 'Alle ausblenden';
    btnHideAll.title = `Alle Unterkategorien von "${rootGroup}" ausblenden`;
    btnHideAll.onclick = (e) => {
      e.stopPropagation();
      const excluded = getExcludedCats();
      const groupKey = `GROUP:${rootGroup}`;
      const toAdd = subcats.map(sc => `PATH:${rootGroup}/${sc}`);
      const updated = Array.from(new Set([...excluded, ...subcats, ...toAdd, groupKey]));
      updateExcludedCats(updated);
      renderPopoverBody();
    };

    const btnReset = document.createElement('button');
    btnReset.className = 'tp-popover-btn';
    btnReset.textContent = 'Reset';
    btnReset.title = `Alle Unterkategorien von "${rootGroup}" wieder einblenden`;
    btnReset.onclick = (e) => {
      e.stopPropagation();
      const excluded = getExcludedCats();
      const updated = excluded.filter(c => !subcats.includes(c) && c !== `GROUP:${rootGroup}` && !c.startsWith(`PATH:${rootGroup}/`));
      updateExcludedCats(updated);
      renderPopoverBody();
    };

    actions.appendChild(btnHideAll);
    actions.appendChild(btnReset);
    header.appendChild(title);
    header.appendChild(actions);
    popover.appendChild(header);

    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = 'Kategorien filtern...';
    searchInput.className = 'tp-popover-search';
    searchInput.oninput = () => renderPopoverBody();
    popover.appendChild(searchInput);

    const body = document.createElement('div');
    body.className = 'tp-popover-body';

    function renderPopoverBody() {
      body.innerHTML = '';
      const excluded = getExcludedCats();
      const isGroupExplicitlyBlocked = excluded.includes(`GROUP:${rootGroup}`);
      const query = (searchInput.value || '').trim().toLowerCase();

      const filteredSubcats = subcats.filter(sc => !query || sc.toLowerCase().includes(query));

      filteredSubcats.forEach(cat => {
        const isCatExcluded = isPathExcluded(cat, rootGroup, excluded);
        const pill = document.createElement('div');
        pill.className = `tp-cat-pill ${isCatExcluded ? 'tp-excluded' : ''}`;
        pill.textContent = cat;
        pill.title = isCatExcluded ? `Kategorie "${cat}" wieder einblenden` : `Kategorie "${cat}" ausblenden`;
        pill.onclick = (e) => {
          e.stopPropagation();
          const curr = getExcludedCats();
          let updated;
          if (curr.includes(cat) || curr.includes(`PATH:${rootGroup}/${cat}`) || isGroupExplicitlyBlocked) {
            const otherSubcatsToKeep = subcats.filter(sc => sc !== cat && isPathExcluded(sc, rootGroup, curr));
            updated = curr.filter(c => c !== cat && c !== `PATH:${rootGroup}/${cat}` && c !== `GROUP:${rootGroup}`);
            if (otherSubcatsToKeep.length > 0) {
              updated = Array.from(new Set([...updated, ...otherSubcatsToKeep.map(sc => `PATH:${rootGroup}/${sc}`)]));
            }
          } else {
            updated = [...curr, `PATH:${rootGroup}/${cat}`];
          }
          updateExcludedCats(updated);
          renderPopoverBody();
        };
        body.appendChild(pill);
      });
    }

    renderPopoverBody();
    popover.appendChild(body);
    mountContainer.appendChild(popover);
    activePopover = popover;
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
      if (link.closest('header, nav, footer, .breadcrumb, #tp-quick-toolbar, #tp-inline-category-bar, #tp-inline-negative-bar')) return;

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

    // 1. If card itself is an <a> tag
    if (card.tagName && card.tagName.toLowerCase() === 'a') {
      const href = card.getAttribute('href') || card.href || '';
      if (href) hrefs.push(href);
    }

    // 2. Nearest ancestor <a> tag
    const closestA = card.closest ? card.closest('a[href]') : null;
    if (closestA) {
      const href = closestA.getAttribute('href') || closestA.href || '';
      if (href && !hrefs.includes(href)) hrefs.push(href);
    }

    // 3. Descendant <a> tags
    if (card.querySelectorAll) {
      card.querySelectorAll('a[href]').forEach(a => {
        if (a.closest('header, nav, footer, .breadcrumb, #tp-quick-toolbar, #tp-suite-filter-bar')) return;
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
          const canonicalRoot = normalizeRootSlug(segments[0]);
          if (canonicalRoot) {
            segments.forEach(seg => {
              const formattedSeg = formatCategorySlug(seg);
              if (formattedSeg) {
                const norm = formattedSeg.trim().toLowerCase();
                const slug = norm.replace(/[^a-z0-9]/g, '');
                const spaceSlug = norm.replace(/-/g, ' ');
                const umlautNorm = normalizeUmlautKey(norm);
                if (!dynamicCatMap[norm]) { dynamicCatMap[norm] = canonicalRoot; isDynamicMapDirty = true; }
                if (!dynamicCatMap[slug]) { dynamicCatMap[slug] = canonicalRoot; isDynamicMapDirty = true; }
                if (!dynamicCatMap[spaceSlug]) { dynamicCatMap[spaceSlug] = canonicalRoot; isDynamicMapDirty = true; }
                if (!dynamicCatMap[umlautNorm]) { dynamicCatMap[umlautNorm] = canonicalRoot; isDynamicMapDirty = true; }
              }
            });
          }

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

    // Tier 4: Fallback to Active Breadcrumb section (for single-category search result views)
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

  // Helper: Check Negative Term Match (Checks visible innerText with word-boundary matching for short terms)
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

  // Stable Quick-Control Pill Toolbar
  function updateQuickToolbar(counts, pageHasOffers) {
    if (!CONFIG.ENABLE_FILTER_COUNTER) {
      const bar = document.getElementById('tp-quick-toolbar');
      if (bar) bar.style.display = 'none';
      return;
    }

    let bar = document.getElementById('tp-quick-toolbar');
    const totalHidden = counts.neg + counts.cat + counts.min;
    const isRevealed = document.body.classList.contains('tp-reveal-filtered');

    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'tp-quick-toolbar';
      bar.innerHTML = `
        <div class="tp-toolbar-group" title="Anzahl durch aktivierte Filter ausgeblendeter Produkte">
          <span>🚫 <strong id="tp-tb-hidden-count">0</strong></span>
          <button class="tp-toolbar-btn" id="tp-tb-reveal" title="Filter-Vorschau: Ausgeblendete Produkte gelb umrandet einblenden">
            👁️ <span id="tp-tb-reveal-label">Einblenden</span>
          </button>
          <button class="tp-toolbar-btn" id="tp-tb-reset" title="Alle Filter (Ausschlüsse &amp; Kategorien) zurücksetzen">
            🔄 Reset
          </button>
        </div>

        <div class="tp-toolbar-divider" id="tp-tb-divider-offers"></div>

        <div class="tp-toolbar-group" id="tp-tb-min-group" title="Mindestanzahl benötigter Händler-Angebote pro Produkt (Produkte mit weniger Angeboten werden ausgeblendet)">
          <span title="Filter für Mindestanzahl Angebote">Min. Angebote:</span>
          <button class="tp-stepper-btn" id="tp-tb-min-minus" title="Mindestanzahl Angebote verringern">-</button>
          <span id="tp-tb-min-val" title="Aktuelle Mindestanzahl Angebote" style="min-width: 16px; text-align: center;">0</span>
          <button class="tp-stepper-btn" id="tp-tb-min-plus" title="Mindestanzahl Angebote erhöhen">+</button>
        </div>
      `;
      document.body.appendChild(bar);

      bar.querySelector('#tp-tb-reveal').onclick = () => {
        document.body.classList.toggle('tp-reveal-filtered');
        processListings();
      };

      bar.querySelector('#tp-tb-reset').onclick = resetAllFilters;

      bar.querySelector('#tp-tb-min-minus').onclick = () => {
        if (CONFIG.MIN_OFFERS > 0) {
          saveConfigKey('MIN_OFFERS', CONFIG.MIN_OFFERS - 1);
          if (uiShadowRoot) {
            const modalVal = uiShadowRoot.getElementById('tp-min-offers-val');
            const modalRange = uiShadowRoot.getElementById('tp-min-offers-range');
            if (modalVal) modalVal.value = CONFIG.MIN_OFFERS;
            if (modalRange) modalRange.value = CONFIG.MIN_OFFERS;
          }
          processListings();
        }
      };

      bar.querySelector('#tp-tb-min-plus').onclick = () => {
        saveConfigKey('MIN_OFFERS', CONFIG.MIN_OFFERS + 1);
        if (uiShadowRoot) {
          const modalVal = uiShadowRoot.getElementById('tp-min-offers-val');
          const modalRange = uiShadowRoot.getElementById('tp-min-offers-range');
          if (modalVal) modalVal.value = CONFIG.MIN_OFFERS;
          if (modalRange) modalRange.value = CONFIG.MIN_OFFERS;
        }
        processListings();
      };
    }

    bar.style.display = 'flex';
    const countEl = bar.querySelector('#tp-tb-hidden-count');
    const revealBtn = bar.querySelector('#tp-tb-reveal');
    const revealLabel = bar.querySelector('#tp-tb-reveal-label');
    const minValEl = bar.querySelector('#tp-tb-min-val');

    const dividerOffers = bar.querySelector('#tp-tb-divider-offers');
    const minOffersGroup = bar.querySelector('#tp-tb-min-group');

    if (dividerOffers) dividerOffers.style.display = pageHasOffers ? 'block' : 'none';
    if (minOffersGroup) minOffersGroup.style.display = pageHasOffers ? 'flex' : 'none';

    if (countEl) countEl.textContent = totalHidden;
    if (minValEl) minValEl.textContent = CONFIG.MIN_OFFERS;
    if (revealBtn) revealBtn.classList.toggle('tp-active', isRevealed);
    if (revealLabel) revealLabel.textContent = isRevealed ? 'Verbergen' : 'Einblenden';
  }

  // Dedicated Power Filter Bar Target & Placement Selector
  function getSuiteBarPlacement() {
    const bar = document.getElementById('tp-suite-filter-bar');

    // 1. Native filter container on category/search pages
    const nativeFilters = document.querySelector('.filters, #filters, .filter_box, .filter-box');
    if (nativeFilters && nativeFilters.parentElement && nativeFilters !== bar) {
      return { container: nativeFilters.parentElement, reference: nativeFilters };
    }

    // 2. Main page listing container (Page_ListTopPriceReductionProducts, bestListContainer, etc.)
    const mainPage = document.querySelector('[id^="Page_List"], .bestListContainer, .pageContainer, #browseContent');
    if (mainPage && mainPage.parentElement && mainPage !== bar) {
      return { container: mainPage.parentElement, reference: mainPage };
    }

    // 3. Directly below site header (Plugin_MainHead) inside FrameContent
    const mainHead = document.querySelector('[class*="MainHead"]');
    if (mainHead && mainHead.parentElement && mainHead !== bar) {
      let ref = mainHead.nextElementSibling;
      while (ref === bar) ref = ref.nextElementSibling;
      return { container: mainHead.parentElement, reference: ref };
    }

    // 4. Main page content area fallback
    const mainContent = document.querySelector('#tpContent .pageContent') ||
      document.querySelector('#browseContent') ||
      document.querySelector('.pageContent') ||
      document.querySelector('main') ||
      document.querySelector('#content');

    if (mainContent && mainContent !== bar) {
      let ref = mainContent.firstChild;
      while (ref === bar) ref = ref.nextSibling;
      return { container: mainContent, reference: ref };
    }

    // 5. Fallback: FrameContent or Body
    const frameContent = document.getElementById('FrameContent') || document.body;
    let ref = frameContent.firstChild;
    while (ref === bar) ref = ref.nextSibling;
    return { container: frameContent, reference: ref };
  }

  // Unified Glassmorphic Power Filter Bar prepended to top of product content
  function renderSuiteFilterBar() {
    const placement = getSuiteBarPlacement();
    if (!placement || !placement.container) return;

    let bar = document.getElementById('tp-suite-filter-bar');
    const excluded = CONFIG.EXCLUDED_CATEGORIES || [];
    const allCats = new Set([
      ...pageCategories,
      ...excluded.map(extractSubcatFromExclusionKey).filter(Boolean)
    ]);
    const isExpanded = CONFIG.CATS_EXPANDED === true;

    const safeInsert = (container, node, ref) => {
      try {
        if (ref && ref.parentElement === container && ref !== node) {
          container.insertBefore(node, ref);
        } else {
          container.appendChild(node);
        }
      } catch (e) {
        log('DOM Insertion fallback:', e);
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

          <button class="tp-btn-toggle ${isExpanded ? 'tp-active' : ''}" id="tp-toggle-cats-btn" title="Kategorien-Filter aus-/einblenden">
            🏷️ <span id="tp-cat-btn-label">Kategorien (${allCats.size})</span> <span id="tp-cat-arrow">${isExpanded ? '▲' : '▼'}</span>
          </button>

          <button class="tp-filter-bar-reset" id="tp-bar-reset-btn" title="Alle Filter (Text &amp; Kategorien) zurücksetzen">🔄 Reset</button>
        </div>

        <div id="tp-collapsible-cat-row" class="tp-cat-collapsible-body" style="display: ${isExpanded ? 'block' : 'none'};">
          <div id="tp-inline-category-pills" class="tp-cat-pills-row"></div>
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

      const toggleBtn = bar.querySelector('#tp-toggle-cats-btn');
      const catRow = bar.querySelector('#tp-collapsible-cat-row');
      toggleBtn.onclick = () => {
        const nextState = !CONFIG.CATS_EXPANDED;
        saveConfigKey('CATS_EXPANDED', nextState);
        catRow.style.display = nextState ? 'block' : 'none';
        toggleBtn.classList.toggle('tp-active', nextState);
        const arrow = bar.querySelector('#tp-cat-arrow');
        if (arrow) arrow.textContent = nextState ? '▲' : '▼';
      };

      bar.querySelector('#tp-bar-reset-btn').onclick = resetAllFilters;
    } else {
      // Re-anchor to target if detached or moved
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

    const toggleBtn = bar.querySelector('#tp-toggle-cats-btn');
    const catLabel = bar.querySelector('#tp-cat-btn-label');
    const catArrow = bar.querySelector('#tp-cat-arrow');
    const catRow = bar.querySelector('#tp-collapsible-cat-row');

    if (catLabel) catLabel.textContent = `Kategorien (${allCats.size})`;
    if (catArrow) catArrow.textContent = isExpanded ? '▲' : '▼';
    if (toggleBtn) toggleBtn.classList.toggle('tp-active', isExpanded);
    if (catRow) catRow.style.display = isExpanded ? 'block' : 'none';

    // Reconcile category pills & Group Pills (In-place DOM Reconciliation to prevent pulsing)
    const pillsHolder = bar.querySelector('#tp-inline-category-pills');
    if (pillsHolder && isExpanded) {
      if (allCats.size === 0) {
        if (!pillsHolder.querySelector('.tp-empty-msg')) {
          pillsHolder.innerHTML = '<span class="tp-empty-msg" style="font-size:11px; color:#64748b;">(Keine Kategorien auf aktueller Ansicht)</span>';
        }
      } else {
        const emptyMsg = pillsHolder.querySelector('.tp-empty-msg');
        if (emptyMsg) emptyMsg.remove();

        // Group detected pageCategories by Root Category Group
        const groups = new Map();
        allCats.forEach(cat => {
          const root = resolveCategoryGroup(cat);
          if (!groups.has(root)) groups.set(root, []);
          groups.get(root).push(cat);
        });

        if (!window._tpExpandedGroups) window._tpExpandedGroups = new Set();

        // Track existing group wrappers in DOM for in-place reconciliation
        const existingGroupWrappers = new Map();
        pillsHolder.querySelectorAll('.tp-group-wrapper').forEach(wrapper => {
          if (wrapper.dataset.rootGroup) {
            existingGroupWrappers.set(wrapper.dataset.rootGroup, wrapper);
          }
        });

        groups.forEach((subcats, rootGroup) => {
          const isGroupExplicitlyBlocked = excluded.includes(`GROUP:${rootGroup}`);
          const allSubcatsExcluded = subcats.every(sc => excluded.includes(sc) || isGroupExplicitlyBlocked);
          const someSubcatsExcluded = subcats.some(sc => excluded.includes(sc) || isGroupExplicitlyBlocked);

          let groupWrapper = existingGroupWrappers.get(rootGroup);
          let groupPill, titleSpan, chevronBtn;

          if (!groupWrapper) {
            groupWrapper = document.createElement('div');
            groupWrapper.className = 'tp-group-wrapper';
            groupWrapper.dataset.rootGroup = rootGroup;

            groupPill = document.createElement('div');
            groupPill.className = 'tp-group-pill';

            titleSpan = document.createElement('span');
            titleSpan.className = 'tp-group-title';

            chevronBtn = document.createElement('span');
            chevronBtn.className = 'tp-group-chevron';

            groupPill.appendChild(titleSpan);
            groupPill.appendChild(chevronBtn);
            groupWrapper.appendChild(groupPill);
            pillsHolder.appendChild(groupWrapper);
          } else {
            existingGroupWrappers.delete(rootGroup);
            groupPill = groupWrapper.querySelector('.tp-group-pill');
            titleSpan = groupWrapper.querySelector('.tp-group-title');
            chevronBtn = groupWrapper.querySelector('.tp-group-chevron');
          }

          // Update Group Pill in-place with semantic distinction
          let stateClass = '';
          if (isGroupExplicitlyBlocked) {
            stateClass = 'tp-excluded-all';
          } else if (allSubcatsExcluded) {
            stateClass = 'tp-excluded-individual';
          } else if (someSubcatsExcluded) {
            stateClass = 'tp-partial';
          }

          const newPillClass = `tp-group-pill ${stateClass}`.trim();
          if (groupPill.className !== newPillClass) groupPill.className = newPillClass;

          const newTitleText = `${getGroupEmoji(rootGroup)} ${rootGroup} (${subcats.length})`;
          if (titleSpan.textContent !== newTitleText) titleSpan.textContent = newTitleText;

          titleSpan.title = `Klick: Gesamte Gruppe "${rootGroup}" ausblenden/einblenden | ▼: Unterkategorien`;
          titleSpan.onclick = (e) => {
            e.stopPropagation();
            const curr = CONFIG.EXCLUDED_CATEGORIES || [];
            const groupKey = `GROUP:${rootGroup}`;
            let updated;
            if (curr.includes(groupKey)) {
              updated = curr.filter(c => c !== groupKey);
            } else {
              updated = Array.from(new Set([...curr, groupKey]));
            }
            saveConfigKey('EXCLUDED_CATEGORIES', updated);
            processListings();
          };

          const newChevronText = '▼';
          if (chevronBtn.textContent !== newChevronText) chevronBtn.textContent = newChevronText;
          chevronBtn.title = `Unterkategorien von "${rootGroup}" anzeigen & verwalten`;
          chevronBtn.onclick = (e) => {
            e.stopPropagation();
            toggleGroupPopover(
              groupPill,
              rootGroup,
              subcats,
              () => CONFIG.EXCLUDED_CATEGORIES || [],
              (updated) => {
                saveConfigKey('EXCLUDED_CATEGORIES', updated);
                processListings();
              }
            );
          };
        });

        // Remove obsolete groups no longer present on page
        existingGroupWrappers.forEach(obsoleteWrapper => obsoleteWrapper.remove());
      }
    }
  }

  let listingRunId = 0;

  async function processListings() {
    if (isModifyingDOM) return;
    isModifyingDOM = true;
    const runId = ++listingRunId;
    try {
      log('Processing product listings...');

      pageCategories.clear();

      const cards = getProductCards();

      if (cards.length === 0) {
        renderSuiteFilterBar();
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

      const batchSize = 20;
      for (let i = 0; i < cards.length; i += batchSize) {
        if (runId !== listingRunId) return;

        const chunk = cards.slice(i, i + batchSize);
        for (const card of chunk) {
          // 1. Category extraction (cached on dataset.tpCategory)
          const catName = extractCardCategory(card);
          if (catName) pageCategories.add(catName);

          const rootGroup = resolveCategoryGroup(catName, card);

          // 1b. Inject 1-Click Card Quick-Block Action Button
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

          // 2. Negative Text Filter (Strictly checks full card text content)
          const isNeg = matchesNegativeTerms(card, termsList);
          card.classList.toggle('tp-negative-filtered', isNeg);
          if (isNeg) counts.neg++;

          // 3. Category Filter
          const isCatExcluded = catName && isPathExcluded(catName, rootGroup, excludedCats);
          card.classList.toggle('tp-category-filtered', isCatExcluded);
          if (isCatExcluded) counts.cat++;

          // 4. Offer Count Filter (cached on dataset.tpOfferCount)
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

        if (i + batchSize < cards.length) {
          await new Promise(resolve => requestAnimationFrame(resolve));
          if (globalThis.scheduler?.yield) await globalThis.scheduler.yield();
        }
      }

      if (runId !== listingRunId) return;

      // 6. Re-sorting by Offer Count
      if (pageHasOffers && CONFIG.SORT_BY_OFFERS !== 'none' && cards.length > 1) {
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

      // 7. Render UI Modules
      flushDynamicMap();
      updateQuickToolbar(counts, pageHasOffers);
      renderSuiteFilterBar();
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
            <button type="button" class="tp-btn tp-btn-secondary" id="tp-btn-close" title="Einstellungen abbrechen ohne Speichern">Abbrechen</button>
            <button type="button" class="tp-btn tp-btn-primary" id="tp-btn-save" title="Einstellungen dauerhaft speichern">Speichern</button>
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
            <label title="Deckkraft für gedimmte Produkte im Dimmen-Modus">Transparenz Nicht-Günstigste</label>
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

          <!-- Section 3: Kategorien Filter -->
          <div class="tp-section-header">3. Kategorien-Filter (Neue Toppreise)</div>
          <div class="tp-settings-group">
            <label title="Erkannte Kategorien anklicken, um sie dauerhaft auszublenden">Erkannte Kategorien (Klicken zum Ausblenden):</label>
            <div id="tp-category-pills" class="tp-cat-pills-container">
              <!-- Rendered dynamically -->
            </div>
          </div>

          <!-- Section 4: Angebote & Sortierung -->
          <div class="tp-section-header">4. Angebote & Sortierung</div>
          <div class="tp-settings-group">
            <label title="Produkte mit weniger als N Angeboten ausblenden">Mindestanzahl Angebote (0 = Aus)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-min-offers-range" min="0" max="15" step="1" value="0">
              <input type="number" id="tp-min-offers-val" min="0" max="50" step="1" value="0">
            </div>
          </div>

          <div class="tp-settings-group">
            <label title="Produkte nach Anzahl verfügbarer Händler-Angebote sortieren">Sortierung nach Anzahl Angebote</label>
            <div class="tp-segmented-control">
              <input type="radio" id="tp-sort-none" name="tp-sort-offers" value="none">
              <label for="tp-sort-none" title="Standard-Reihenfolge der Seite beibehalten">Standard</label>
              
              <input type="radio" id="tp-sort-desc" name="tp-sort-offers" value="desc">
              <label for="tp-sort-desc" title="Produkte mit den meisten Angeboten zuerst">Meiste ⬇</label>
              
              <input type="radio" id="tp-sort-asc" name="tp-sort-offers" value="asc">
              <label for="tp-sort-asc" title="Produkte mit den wenigsten Angeboten zuerst">Wenigste ⬆</label>
            </div>
          </div>

          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label title="Statusleiste am unteren Bildschirmrand anzeigen">Filter-Zähler Statusleiste anzeigen</label>
            </div>
            <label class="tp-switch">
              <input type="checkbox" id="tp-counter-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>

          <!-- Section 5: Preisalarm Auto-Filler -->
          <div class="tp-section-header" style="color: #3b82f6;">5. Preisalarm Auto-Filler</div>
          
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

        </div>
      `;
      section = tempDiv.firstElementChild;
      sectionsHolder.appendChild(section);
    }

    // Form Field References from Shadow DOM
    const modeHighlight = shadow.getElementById('tp-mode-highlight-only');
    const modeDim = shadow.getElementById('tp-mode-dim');
    const modeHide = shadow.getElementById('tp-mode-hide');
    const marginRange = shadow.getElementById('tp-margin-range');
    const marginVal = shadow.getElementById('tp-margin-val');
    const opacityRange = shadow.getElementById('tp-opacity-range');
    const opacityVal = shadow.getElementById('tp-opacity-val');
    const shippingToggle = shadow.getElementById('tp-shipping-toggle');

    const negTermsInput = shadow.getElementById('tp-negative-terms-input');
    const catPillsContainer = shadow.getElementById('tp-category-pills');

    const minOffersRange = shadow.getElementById('tp-min-offers-range');
    const minOffersVal = shadow.getElementById('tp-min-offers-val');

    const sortNone = shadow.getElementById('tp-sort-none');
    const sortDesc = shadow.getElementById('tp-sort-desc');
    const sortAsc = shadow.getElementById('tp-sort-asc');

    const counterToggle = shadow.getElementById('tp-counter-toggle');

    const alarmEnabledToggle = shadow.getElementById('tp-alarm-enabled-toggle');
    const alarmTargetRange = shadow.getElementById('tp-alarm-target-range');
    const alarmTargetVal = shadow.getElementById('tp-alarm-target-val');
    const alarmAutoSubmitToggle = shadow.getElementById('tp-alarm-autosubmit-toggle');

    const dur90 = shadow.getElementById('tp-dur-90');
    const dur180 = shadow.getElementById('tp-dur-180');
    const dur365 = shadow.getElementById('tp-dur-365');
    const dur730 = shadow.getElementById('tp-dur-730');

    let currentExcludedCats = [...(CONFIG.EXCLUDED_CATEGORIES || [])];

    function renderCategoryPills() {
      const allCats = new Set([...pageCategories]);
      currentExcludedCats.forEach(c => {
        const sub = extractSubcatFromExclusionKey(c);
        if (sub) allCats.add(sub);
      });

      if (allCats.size === 0) {
        if (!catPillsContainer.querySelector('.tp-empty-msg')) {
          catPillsContainer.innerHTML = '<span class="tp-empty-msg" style="font-size:11px; color:#64748b; padding:4px;">Keine Kategorien auf Seite erkannt</span>';
        }
        return;
      }

      const emptyMsg = catPillsContainer.querySelector('.tp-empty-msg');
      if (emptyMsg) emptyMsg.remove();

      const groups = new Map();
      allCats.forEach(cat => {
        const root = resolveCategoryGroup(cat);
        if (!groups.has(root)) groups.set(root, []);
        groups.get(root).push(cat);
      });

      if (!window._tpModalExpandedGroups) window._tpModalExpandedGroups = new Set();

      const existingGroupWrappers = new Map();
      catPillsContainer.querySelectorAll('.tp-group-wrapper').forEach(wrapper => {
        if (wrapper.dataset.rootGroup) {
          existingGroupWrappers.set(wrapper.dataset.rootGroup, wrapper);
        }
      });

      groups.forEach((subcats, rootGroup) => {
        const isGroupExplicitlyBlocked = currentExcludedCats.includes(`GROUP:${rootGroup}`);
        const allSubcatsExcluded = subcats.every(sc => currentExcludedCats.includes(sc) || isGroupExplicitlyBlocked);
        const someSubcatsExcluded = subcats.some(sc => currentExcludedCats.includes(sc) || isGroupExplicitlyBlocked);

        let groupWrapper = existingGroupWrappers.get(rootGroup);
        let groupPill, titleSpan, chevronBtn;

        if (!groupWrapper) {
          groupWrapper = document.createElement('div');
          groupWrapper.className = 'tp-group-wrapper';
          groupWrapper.dataset.rootGroup = rootGroup;

          groupPill = document.createElement('div');
          groupPill.className = 'tp-group-pill';

          titleSpan = document.createElement('span');
          titleSpan.className = 'tp-group-title';

          chevronBtn = document.createElement('span');
          chevronBtn.className = 'tp-group-chevron';

          groupPill.appendChild(titleSpan);
          groupPill.appendChild(chevronBtn);
          groupWrapper.appendChild(groupPill);
          catPillsContainer.appendChild(groupWrapper);
        } else {
          existingGroupWrappers.delete(rootGroup);
          groupPill = groupWrapper.querySelector('.tp-group-pill');
          titleSpan = groupWrapper.querySelector('.tp-group-title');
          chevronBtn = groupWrapper.querySelector('.tp-group-chevron');
        }

        let stateClass = '';
        if (isGroupExplicitlyBlocked) {
          stateClass = 'tp-excluded-all';
        } else if (allSubcatsExcluded) {
          stateClass = 'tp-excluded-individual';
        } else if (someSubcatsExcluded) {
          stateClass = 'tp-partial';
        }

        const newPillClass = `tp-group-pill ${stateClass}`.trim();
        if (groupPill.className !== newPillClass) groupPill.className = newPillClass;

        const newTitleText = `${getGroupEmoji(rootGroup)} ${rootGroup} (${subcats.length})`;
        if (titleSpan.textContent !== newTitleText) titleSpan.textContent = newTitleText;

        titleSpan.title = `Klick: Gesamte Gruppe "${rootGroup}" ausblenden/einblenden | ▼: Unterkategorien`;
        titleSpan.onclick = (e) => {
          e.stopPropagation();
          const groupKey = `GROUP:${rootGroup}`;
          if (currentExcludedCats.includes(groupKey)) {
            currentExcludedCats = currentExcludedCats.filter(c => c !== groupKey);
          } else {
            currentExcludedCats = Array.from(new Set([...currentExcludedCats, groupKey]));
          }
          renderCategoryPills();
        };

        const newChevronText = '▼';
        if (chevronBtn.textContent !== newChevronText) chevronBtn.textContent = newChevronText;
        chevronBtn.title = `Unterkategorien von "${rootGroup}" anzeigen & verwalten`;
        chevronBtn.onclick = (e) => {
          e.stopPropagation();
          const dialogEl = shadow.getElementById('tp-settings-dialog');
          toggleGroupPopover(
            groupPill,
            rootGroup,
            subcats,
            () => currentExcludedCats,
            (updated) => {
              currentExcludedCats = updated;
              renderCategoryPills();
            },
            dialogEl || shadow
          );
        };
      });

      existingGroupWrappers.forEach(obsoleteWrapper => obsoleteWrapper.remove());
    }

    shadow.addEventListener('click', (e) => {
      if (activePopover && !activePopover.contains(e.target) && !e.target.closest('.tp-group-pill')) {
        closeActivePopover();
      }
    });

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

      currentExcludedCats = [...(CONFIG.EXCLUDED_CATEGORIES || [])];
      renderCategoryPills();

      minOffersRange.value = CONFIG.MIN_OFFERS || 0;
      minOffersVal.value = CONFIG.MIN_OFFERS || 0;

      const sort = CONFIG.SORT_BY_OFFERS;
      if (sort === 'desc') sortDesc.checked = true;
      else if (sort === 'asc') sortAsc.checked = true;
      else sortNone.checked = true;

      counterToggle.checked = CONFIG.ENABLE_FILTER_COUNTER !== false;

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

      updateOpacityState(mode);
    }

    function updateOpacityState(selectedMode) {
      const opacityGroup = shadow.getElementById('tp-dim-opacity-group');
      if (selectedMode === 'dim') {
        opacityGroup.style.opacity = '1';
        opacityRange.disabled = false;
        opacityVal.disabled = false;
      } else {
        opacityGroup.style.opacity = '0.4';
        opacityRange.disabled = true;
        opacityVal.disabled = true;
      }
    }

    // Range Bindings
    marginRange.addEventListener('input', (e) => marginVal.value = e.target.value);
    marginVal.addEventListener('input', (e) => marginRange.value = parseFloat(e.target.value) || 0);

    opacityRange.addEventListener('input', (e) => opacityVal.value = Math.round(parseFloat(e.target.value) * 100));
    opacityVal.addEventListener('input', (e) => opacityRange.value = (parseInt(e.target.value) || 25) / 100);

    minOffersRange.addEventListener('input', (e) => minOffersVal.value = e.target.value);
    minOffersVal.addEventListener('input', (e) => minOffersRange.value = parseInt(e.target.value) || 0);

    alarmTargetRange.addEventListener('input', (e) => alarmTargetVal.value = e.target.value);
    alarmTargetVal.addEventListener('input', (e) => alarmTargetRange.value = parseInt(e.target.value) || 60);

    [modeHighlight, modeDim, modeHide].forEach(radio => {
      radio.addEventListener('change', () => {
        const selectedMode = shadow.querySelector('input[name="tp-mode"]:checked').value;
        updateOpacityState(selectedMode);
      });
    });

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
      saveConfigKey('EXCLUDED_CATEGORIES', currentExcludedCats);
      saveConfigKey('MIN_OFFERS', Math.max(0, parseInt(minOffersVal.value) || 0));

      const checkedSort = shadow.querySelector('input[name="tp-sort-offers"]:checked');
      if (checkedSort) saveConfigKey('SORT_BY_OFFERS', checkedSort.value);

      saveConfigKey('ENABLE_FILTER_COUNTER', counterToggle.checked);

      saveConfigKey('ALARM_ENABLED', alarmEnabledToggle.checked);
      saveConfigKey('ALARM_TARGET_PERCENT', Math.max(0.05, Math.min(0.99, (parseInt(alarmTargetVal.value) || 60) / 100)));

      const checkedDur = shadow.querySelector('input[name="tp-alarm-duration"]:checked');
      if (checkedDur) saveConfigKey('ALARM_DURATION_DAYS', checkedDur.value);

      saveConfigKey('ALARM_AUTO_SUBMIT', alarmAutoSubmitToggle.checked);

      updateBodyClasses();
      processListings();
      showToast('Toppreise Suite Einstellungen gespeichert');
    });
  }

  // ─── OBSERVER & INITIALIZATION ───────────────────────────────────────────────
  let debounceTimer = null;
  let isModifyingDOM = false;

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
