// ==UserScript==
// @name         Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler
// @namespace    https://github.com/tazztone/scripts
// @version      2.8.12
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
    outline: 2px dashed #f59e0b !important;
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

  /* Settings Modal Backdrop */
  #tp-settings-modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 999998;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  #tp-settings-modal-backdrop.open {
    opacity: 1;
    pointer-events: auto;
  }

  /* Glassmorphic Modal Dialog Box */
  #tp-settings-modal {
    width: 92%;
    max-width: 520px;
    background: rgba(30, 41, 59, 0.92);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
    border-radius: 16px;
    color: #f8fafc;
    padding: 24px;
    transform: scale(0.95) translateY(10px);
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  #tp-settings-modal-backdrop.open #tp-settings-modal {
    transform: scale(1) translateY(0);
  }

  #tp-settings-modal h3 {
    margin: 0 0 18px 0;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.5px;
    background: linear-gradient(to right, #34d399, #059669);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  /* Form Elements & Groups */
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
    box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
  }
  .tp-segmented-control-blue input[type="radio"]:checked + label {
    background: #3b82f6 !important;
    box-shadow: 0 2px 6px rgba(59, 130, 246, 0.3) !important;
  }

  /* Range and Inputs */
  .tp-range-container {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .tp-range-container input[type="range"] {
    flex: 1;
    accent-color: #10b981;
    background: rgba(15, 23, 42, 0.6);
    height: 6px;
    border-radius: 3px;
    outline: none;
    -webkit-appearance: none;
  }
  .tp-range-container.tp-blue input[type="range"] {
    accent-color: #3b82f6;
  }
  .tp-range-container input[type="number"] {
    width: 65px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #fff;
    padding: 6px 8px;
    font-size: 13px;
    text-align: center;
    outline: none;
  }

  /* Textarea for Negative Filter */
  .tp-textarea {
    width: 100%;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #fff;
    padding: 8px 12px;
    font-size: 12px;
    font-family: inherit;
    resize: vertical;
    min-height: 54px;
    outline: none;
    box-sizing: border-box;
    transition: border-color 0.2s ease;
  }
  .tp-textarea:focus {
    border-color: #10b981;
  }

  /* Category Pills Container */
  .tp-cat-pills-container {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    max-height: 110px;
    overflow-y: auto;
    padding: 6px;
    background: rgba(15, 23, 42, 0.6);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }

  /* High-Contrast Crisp Readable Category Pills */
  .tp-cat-pill {
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    user-select: none;
    transition: all 0.2s ease;
    background: #1e293b !important;
    color: #f8fafc !important;
    border: 1px solid #334155 !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
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
    display: flex;
    flex-direction: column;
    gap: 4px;
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
    border-color: rgba(59, 130, 246, 0.2);
  }
  .tp-switch input:checked + .tp-slider:before {
    transform: translateX(20px);
    background-color: #fff;
  }

  /* Action Buttons */
  .tp-modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 20px;
  }
  .tp-btn {
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;
    outline: none;
  }
  .tp-btn-secondary {
    background: transparent;
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .tp-btn-secondary:hover {
    color: #f1f5f9;
    background: rgba(255, 255, 255, 0.05);
  }
  .tp-btn-primary {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: #fff;
    box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3);
  }
  .tp-btn-primary:hover {
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.5);
    transform: translateY(-1px);
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
    overflow: hidden !important;
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
    "2 wochenlinsen": "Drogerie",
    "2wochenlinsen": "Drogerie",
    "3d drucker": "Computer & Zubehör",
    "3d shooter fps": "Videogames",
    "3ddrucker": "Computer & Zubehör",
    "3dshooterfps": "Videogames",
    "4k uhd action thriller horror": "Filme",
    "4k uhd kinder familie": "Filme",
    "4k uhd science fiction fantasy": "Filme",
    "4k ultra hd blu ray player": "TV & Video",
    "4kuhdactionthrillerhorror": "Filme",
    "4kuhdkinderfamilie": "Filme",
    "4kuhdsciencefictionfantasy": "Filme",
    "4kultrahdblurayplayer": "TV & Video",
    "abenteuer": "Filme",
    "abenteuer actiondrama": "Filme",
    "abenteueractiondrama": "Filme",
    "abenteür": "Filme",
    "abenteür actiondrama": "Filme",
    "abenteüractiondrama": "Filme",
    "abschlagbehaelter": "Haushalt & Küche",
    "abschlagbehälter": "Haushalt & Küche",
    "access points bridges": "Computer & Zubehör",
    "accesspointsbridges": "Computer & Zubehör",
    "action": "Filme",
    "action cameras": "TV & Video",
    "actioncameras": "TV & Video",
    "actionkameras": "TV & Video",
    "actionspiele": "Videogames",
    "activity tracker smartwatches": "Sport & Freizeit",
    "activitytrackersmartwatches": "Sport & Freizeit",
    "adapterplatten": "Foto & Video",
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
    "aktenvernichter": "Bürobedarf & Schreibwaren",
    "allesschneider brotschneidemaschinen": "Haushalt & Küche",
    "allesschneiderbrotschneidemaschinen": "Haushalt & Küche",
    "anal vibratoren": "Drogerie",
    "analoge funktelefone": "Smartphones & Mobiltelefone",
    "analoge telefone": "Smartphones & Mobiltelefone",
    "analogefunktelefone": "Smartphones & Mobiltelefone",
    "analogetelefone": "Smartphones & Mobiltelefone",
    "analvibratoren": "Drogerie",
    "anime": "Filme",
    "apple h10": "Smartphones & Mobiltelefone",
    "appleh10": "Smartphones & Mobiltelefone",
    "arbeitsplatz": "Bürobedarf & Schreibwaren",
    "arbeitsplatz ausstattung": "Garten & Baumarkt",
    "arbeitsplatzausstattung": "Garten & Baumarkt",
    "arbeitsspeicher": "Computer & Zubehör",
    "audio streaming": "HiFi & Audio",
    "audiostreaming": "HiFi & Audio",
    "aufbewahren": "Haushalt & Küche",
    "auflegevibratoren": "Drogerie",
    "auto motorrad": "Auto & Motorrad",
    "automotorrad": "Auto & Motorrad",
    "autorennbahnen": "Spielwaren",
    "autos": "Spielwaren",
    "baby": "Haushalt & Küche",
    "baby kinderpflege": "Drogerie",
    "babykinderpflege": "Drogerie",
    "back ofenformen": "Haushalt & Küche",
    "backen": "Haushalt & Küche",
    "backoefen herde": "Haushalt & Küche",
    "backoefenherde": "Haushalt & Küche",
    "backofenformen": "Haushalt & Küche",
    "backöfen herde": "Haushalt & Küche",
    "backöfenherde": "Haushalt & Küche",
    "bandschleifer": "Garten & Baumarkt",
    "barbedarf": "Haushalt & Küche",
    "basteln malen": "Spielwaren",
    "bastelnmalen": "Spielwaren",
    "batterien akkus ladegeraete": "Garten & Baumarkt",
    "batterien akkus ladegeräte": "Garten & Baumarkt",
    "batterienakkusladegeraete": "Garten & Baumarkt",
    "batterienakkusladegeräte": "Garten & Baumarkt",
    "bau konstruktionsspielzeug": "Spielwaren",
    "bau und nutzfahrzeuge": "Spielwaren",
    "baukonstruktionsspielzeug": "Spielwaren",
    "baum strauchpflege": "Garten & Baumarkt",
    "baumstrauchpflege": "Garten & Baumarkt",
    "bauundnutzfahrzeuge": "Spielwaren",
    "beamer": "TV & Video",
    "beat em up": "Videogames",
    "beatemup": "Videogames",
    "bekleidung accessoires": "Drogerie",
    "bekleidung schuhe": "Bekleidung & Schuhe",
    "bekleidungaccessoires": "Drogerie",
    "bekleidungschuhe": "Bekleidung & Schuhe",
    "besteck": "Haushalt & Küche",
    "besteck set": "Haushalt & Küche",
    "besteckset": "Haushalt & Küche",
    "bewaesserungstechnik": "Garten & Baumarkt",
    "bewässerungstechnik": "Garten & Baumarkt",
    "bindegeraete": "Bürobedarf & Schreibwaren",
    "bindegeräte": "Bürobedarf & Schreibwaren",
    "binden laminieren": "Bürobedarf & Schreibwaren",
    "bindenlaminieren": "Bürobedarf & Schreibwaren",
    "biografie": "Filme",
    "blu ray 4k ultra hd filme": "Filme",
    "blu ray action thriller horror": "Filme",
    "blu ray dvd recorder": "TV & Video",
    "blu ray filme": "Filme",
    "blu ray kinder familie": "Filme",
    "blu ray komoedie drama": "Filme",
    "blu ray komödie drama": "Filme",
    "blu ray player": "TV & Video",
    "blu ray science fiction fantasy": "Filme",
    "blu ray tv dokumentationen": "Filme",
    "bluetooth lautsprecher": "HiFi & Audio",
    "bluetooth tracker": "Smartphones & Mobiltelefone",
    "bluetoothlautsprecher": "HiFi & Audio",
    "bluetoothtracker": "Smartphones & Mobiltelefone",
    "bluray4kultrahdfilme": "Filme",
    "blurayactionthrillerhorror": "Filme",
    "bluraydvdrecorder": "TV & Video",
    "blurayfilme": "Filme",
    "bluraykinderfamilie": "Filme",
    "bluraykomoediedrama": "Filme",
    "bluraykomödiedrama": "Filme",
    "blurayplayer": "TV & Video",
    "bluraysciencefictionfantasy": "Filme",
    "bluraytvdokumentationen": "Filme",
    "blütooth lautsprecher": "HiFi & Audio",
    "blütooth tracker": "Smartphones & Mobiltelefone",
    "blütoothlautsprecher": "HiFi & Audio",
    "blütoothtracker": "Smartphones & Mobiltelefone",
    "bohrmaschinen schrauber": "Garten & Baumarkt",
    "bohrmaschinenschrauber": "Garten & Baumarkt",
    "box sets": "Filme",
    "boxsets": "Filme",
    "braeter dampfgarer": "Haushalt & Küche",
    "braeterdampfgarer": "Haushalt & Küche",
    "brandschutz": "Garten & Baumarkt",
    "brett knobelspiele": "Videogames",
    "brettknobelspiele": "Videogames",
    "brixies": "Spielwaren",
    "brother tintenpatronen": "Computer & Zubehör",
    "brother toner": "Computer & Zubehör",
    "brothertintenpatronen": "Computer & Zubehör",
    "brothertoner": "Computer & Zubehör",
    "bräter dampfgarer": "Haushalt & Küche",
    "bräterdampfgarer": "Haushalt & Küche",
    "buegeleisen buegelmaschinen": "Haushalt & Küche",
    "buegeleisenbuegelmaschinen": "Haushalt & Küche",
    "bueroanwendungen": "Computer & Zubehör",
    "buerobedarf schreibwaren": "Bürobedarf & Schreibwaren",
    "buerobedarfschreibwaren": "Bürobedarf & Schreibwaren",
    "bueroeinrichtung": "Bürobedarf & Schreibwaren",
    "bueroelektronik": "Bürobedarf & Schreibwaren",
    "bügeleisen bügelmaschinen": "Haushalt & Küche",
    "bügeleisenbügelmaschinen": "Haushalt & Küche",
    "büroanwendungen": "Computer & Zubehör",
    "bürobedarf schreibwaren": "Bürobedarf & Schreibwaren",
    "bürobedarfschreibwaren": "Bürobedarf & Schreibwaren",
    "büröinrichtung": "Bürobedarf & Schreibwaren",
    "bürölektronik": "Bürobedarf & Schreibwaren",
    "cada": "Spielwaren",
    "camcorder": "TV & Video",
    "camping outdoor": "Sport & Freizeit",
    "campingoutdoor": "Sport & Freizeit",
    "campingzubehoer": "Sport & Freizeit",
    "campingzubehör": "Sport & Freizeit",
    "canon tintenpatronen": "Computer & Zubehör",
    "canontintenpatronen": "Computer & Zubehör",
    "car hifi car video": "Auto & Motorrad",
    "carhificarvideo": "Auto & Motorrad",
    "carrera hybrid": "Spielwaren",
    "carrerahybrid": "Spielwaren",
    "cd dvd receiver": "HiFi & Audio",
    "cd receiver": "Auto & Motorrad",
    "cd sacd player": "HiFi & Audio",
    "cddvdreceiver": "HiFi & Audio",
    "cdreceiver": "Auto & Motorrad",
    "cdsacdplayer": "HiFi & Audio",
    "cobi": "Spielwaren",
    "computer zubehoer": "Computer & Zubehör",
    "computer zubehör": "Computer & Zubehör",
    "computerspiele fuer windows": "Videogames",
    "computerspiele für windows": "Videogames",
    "computerspielefuerwindows": "Videogames",
    "computerspielefürwindows": "Videogames",
    "computerzubehoer": "Computer & Zubehör",
    "computerzubehör": "Computer & Zubehör",
    "dab tuner": "Auto & Motorrad",
    "dabtuner": "Auto & Motorrad",
    "damenduefte": "Drogerie",
    "damendüfte": "Drogerie",
    "dashboards buttonboxes": "Videogames",
    "dashboardsbuttonboxes": "Videogames",
    "decken wandhalterungen": "TV & Video",
    "deckenwandhalterungen": "TV & Video",
    "dekorationswerkzeuge": "Garten & Baumarkt",
    "deodorant": "Drogerie",
    "digital 124 autos": "Spielwaren",
    "digital 132 autos": "Spielwaren",
    "digital 132 sets": "Spielwaren",
    "digital media receiver": "Auto & Motorrad",
    "digital124autos": "Spielwaren",
    "digital132autos": "Spielwaren",
    "digital132sets": "Spielwaren",
    "digitale bilderrahmen": "Foto & Video",
    "digitalebilderrahmen": "Foto & Video",
    "digitalkameras": "Foto & Video",
    "digitalmediareceiver": "Auto & Motorrad",
    "displays monitore": "Auto & Motorrad",
    "displaysmonitore": "Auto & Motorrad",
    "dokumentation": "Filme",
    "dolce gusto maschinen": "Haushalt & Küche",
    "dolcegustomaschinen": "Haushalt & Küche",
    "drama": "Filme",
    "drogerie": "Drogerie",
    "drucker": "Computer & Zubehör",
    "drucker scanner": "Computer & Zubehör",
    "druckerscanner": "Computer & Zubehör",
    "drumcomputer": "HiFi & Audio",
    "dsl cable router": "Computer & Zubehör",
    "dslcablerouter": "Computer & Zubehör",
    "duschpflege": "Drogerie",
    "dvb s receiver": "TV & Video",
    "dvbsreceiver": "TV & Video",
    "dvd action thriller horror": "Filme",
    "dvd filme": "Filme",
    "dvd kinder familie": "Filme",
    "dvd komoedie drama": "Filme",
    "dvd komödie drama": "Filme",
    "dvd player": "TV & Video",
    "dvd receiver": "Auto & Motorrad",
    "dvd science fiction fantasy": "Filme",
    "dvd tv dokumentationen": "Filme",
    "dvdactionthrillerhorror": "Filme",
    "dvdfilme": "Filme",
    "dvdkinderfamilie": "Filme",
    "dvdkomoediedrama": "Filme",
    "dvdkomödiedrama": "Filme",
    "dvdplayer": "TV & Video",
    "dvdreceiver": "Auto & Motorrad",
    "dvdsciencefictionfantasy": "Filme",
    "dvdtvdokumentationen": "Filme",
    "e block 9v": "Garten & Baumarkt",
    "e block akkus 9v": "Garten & Baumarkt",
    "e drums": "HiFi & Audio",
    "e pianos": "HiFi & Audio",
    "e scooter": "Sport & Freizeit",
    "eastern": "Filme",
    "eau de cologne": "Drogerie",
    "eau de parfum": "Drogerie",
    "eau de toilette": "Drogerie",
    "eau fraiche": "Drogerie",
    "eaudecologne": "Drogerie",
    "eaudeparfum": "Drogerie",
    "eaudetoilette": "Drogerie",
    "eaufraiche": "Drogerie",
    "eblock9v": "Garten & Baumarkt",
    "eblockakkus9v": "Garten & Baumarkt",
    "ebook reader": "Computer & Zubehör",
    "ebookreader": "Computer & Zubehör",
    "echolote": "Computer & Zubehör",
    "edrums": "HiFi & Audio",
    "einbau navigationssysteme": "Auto & Motorrad",
    "einbaunavigationssysteme": "Auto & Motorrad",
    "einplatinencomputer": "Computer & Zubehör",
    "elektrogrills": "Garten & Baumarkt",
    "elektrorasierer": "Drogerie",
    "elektrozahnbuersten": "Drogerie",
    "elektrozahnbürsten": "Drogerie",
    "endstufen": "HiFi & Audio",
    "epianos": "HiFi & Audio",
    "epilierer haarentferner": "Drogerie",
    "epiliererhaarentferner": "Drogerie",
    "epson tintenpatronen": "Computer & Zubehör",
    "epsontintenpatronen": "Computer & Zubehör",
    "ersatzbuersten": "Drogerie",
    "ersatzbürsten": "Drogerie",
    "escooter": "Sport & Freizeit",
    "etiketten aufkleber": "Computer & Zubehör",
    "etikettenaufkleber": "Computer & Zubehör",
    "etikettendrucker": "Computer & Zubehör",
    "evolution autos": "Spielwaren",
    "evolutionautos": "Spielwaren",
    "experimentierkaesten": "Spielwaren",
    "experimentierkästen": "Spielwaren",
    "externe festplatten hdd": "Computer & Zubehör",
    "externe solid state drives ssd": "Computer & Zubehör",
    "externefestplattenhdd": "Computer & Zubehör",
    "externesolidstatedrivesssd": "Computer & Zubehör",
    "exzenterschleifer": "Garten & Baumarkt",
    "fairphone h3048": "Smartphones & Mobiltelefone",
    "fairphoneh3048": "Smartphones & Mobiltelefone",
    "familienspiele": "Spielwaren",
    "fantasy": "Filme",
    "farbige kontaktlinsen": "Drogerie",
    "farbigekontaktlinsen": "Drogerie",
    "fenster tuer": "Garten & Baumarkt",
    "fenster tür": "Garten & Baumarkt",
    "fensterreinigungsroboter": "Haushalt & Küche",
    "fenstertuer": "Garten & Baumarkt",
    "fenstertür": "Garten & Baumarkt",
    "fernbedienungen": "Auto & Motorrad",
    "fernglaeser": "Sport & Freizeit",
    "ferngläser": "Sport & Freizeit",
    "festnetz telefone": "Smartphones & Mobiltelefone",
    "festnetztelefone": "Smartphones & Mobiltelefone",
    "festplatten hdd": "Computer & Zubehör",
    "festplatten ssd": "Computer & Zubehör",
    "festplattenhdd": "Computer & Zubehör",
    "festplattenssd": "Computer & Zubehör",
    "film": "Filme",
    "filme": "Filme",
    "finanz wirtschaftsrechner": "Bürobedarf & Schreibwaren",
    "finanzwirtschaftsrechner": "Bürobedarf & Schreibwaren",
    "fischertechnik": "Spielwaren",
    "fisher price": "Spielwaren",
    "fisherprice": "Spielwaren",
    "fitness krafttraining": "Sport & Freizeit",
    "fitnesskrafttraining": "Sport & Freizeit",
    "flight sticks sim flying": "Videogames",
    "flightstickssimflying": "Videogames",
    "fondue": "Haushalt & Küche",
    "fondü": "Haushalt & Küche",
    "foto": "Foto & Video",
    "fotopapier": "Computer & Zubehör",
    "fuchsschwaenze": "Garten & Baumarkt",
    "fuchsschwänze": "Garten & Baumarkt",
    "funkgeraete": "Smartphones & Mobiltelefone",
    "funkgeräte": "Smartphones & Mobiltelefone",
    "g punkt vibratoren": "Drogerie",
    "gamepads": "Videogames",
    "gaming stuehle": "Videogames",
    "gaming stühle": "Videogames",
    "gamingstuehle": "Videogames",
    "gamingstühle": "Videogames",
    "gartengeraete": "Garten & Baumarkt",
    "gartengeräte": "Garten & Baumarkt",
    "gartenmoebel": "Garten & Baumarkt",
    "gartenmöbel": "Garten & Baumarkt",
    "gas elektrokochfelder": "Haushalt & Küche",
    "gaselektrokochfelder": "Haushalt & Küche",
    "gasgrills": "Garten & Baumarkt",
    "gefrierschraenke gefriertruhen": "Haushalt & Küche",
    "gefrierschraenkegefriertruhen": "Haushalt & Küche",
    "gefrierschränke gefriertruhen": "Haushalt & Küche",
    "gefrierschränkegefriertruhen": "Haushalt & Küche",
    "gehoerschutz": "Garten & Baumarkt",
    "gehörschutz": "Garten & Baumarkt",
    "geschenksets": "Drogerie",
    "geschichte": "Filme",
    "geschirr besteck glaeser": "Haushalt & Küche",
    "geschirr besteck gläser": "Haushalt & Küche",
    "geschirrbesteckglaeser": "Haushalt & Küche",
    "geschirrbesteckgläser": "Haushalt & Küche",
    "geschirrspueler": "Haushalt & Küche",
    "geschirrspüler": "Haushalt & Küche",
    "gesellschaftsspiele": "Spielwaren",
    "getraenkezubereitung": "Haushalt & Küche",
    "getränkezubereitung": "Haushalt & Küche",
    "glacemaschinen": "Haushalt & Küche",
    "go go plus autos": "Spielwaren",
    "gogoplusautos": "Spielwaren",
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
    "gpunktvibratoren": "Drogerie",
    "grafikkarten": "Computer & Zubehör",
    "grafikkarten zubehoer": "Computer & Zubehör",
    "grafikkarten zubehör": "Computer & Zubehör",
    "grafikkartenzubehoer": "Computer & Zubehör",
    "grafikkartenzubehör": "Computer & Zubehör",
    "grafische taschenrechner": "Bürobedarf & Schreibwaren",
    "grafischetaschenrechner": "Bürobedarf & Schreibwaren",
    "grillieren": "Garten & Baumarkt",
    "haar bartschneider": "Drogerie",
    "haarbartschneider": "Drogerie",
    "haarglaetter": "Drogerie",
    "haarglätter": "Drogerie",
    "haarpflege": "Drogerie",
    "haartrockner": "Drogerie",
    "halterungen": "Computer & Zubehör",
    "handfunkgeraete": "Smartphones & Mobiltelefone",
    "handfunkgeräte": "Smartphones & Mobiltelefone",
    "handwerkzeuge": "Garten & Baumarkt",
    "handzahnbuersten": "Drogerie",
    "handzahnbürsten": "Drogerie",
    "haus garten": "Garten & Baumarkt",
    "haus sicherheitstechnik": "Garten & Baumarkt",
    "hausgarten": "Garten & Baumarkt",
    "haushalt kueche": "Haushalt & Küche",
    "haushalt küche": "Haushalt & Küche",
    "haushaltkueche": "Haushalt & Küche",
    "haushaltküche": "Haushalt & Küche",
    "haushaltsgeraete": "Haushalt & Küche",
    "haushaltsgeräte": "Haushalt & Küche",
    "haussicherheitstechnik": "Garten & Baumarkt",
    "hautpflege": "Drogerie",
    "headsets": "Smartphones & Mobiltelefone",
    "health wellness": "Drogerie",
    "healthwellness": "Drogerie",
    "heften": "Bürobedarf & Schreibwaren",
    "heissluftfritteusen": "Haushalt & Küche",
    "heizung klima": "Garten & Baumarkt",
    "heizungklima": "Garten & Baumarkt",
    "herrenduefte": "Drogerie",
    "herrendüfte": "Drogerie",
    "hifi audio": "HiFi & Audio",
    "hifi einzelkomponenten": "HiFi & Audio",
    "hifi receiver": "HiFi & Audio",
    "hifi systeme": "HiFi & Audio",
    "hifi verstaerker": "HiFi & Audio",
    "hifi verstärker": "HiFi & Audio",
    "hifiaudio": "HiFi & Audio",
    "hifieinzelkomponenten": "HiFi & Audio",
    "hifireceiver": "HiFi & Audio",
    "hifisysteme": "HiFi & Audio",
    "hifiverstaerker": "HiFi & Audio",
    "hifiverstärker": "HiFi & Audio",
    "hochdruckreiniger": "Garten & Baumarkt",
    "hochtoener": "Auto & Motorrad",
    "hochtöner": "Auto & Motorrad",
    "holzkohlegrills": "Garten & Baumarkt",
    "home cinema av receiver": "HiFi & Audio",
    "home cinema verstaerker": "HiFi & Audio",
    "home cinema verstärker": "HiFi & Audio",
    "home cinema video": "TV & Video",
    "homecinemaavreceiver": "HiFi & Audio",
    "homecinemaverstaerker": "HiFi & Audio",
    "homecinemaverstärker": "HiFi & Audio",
    "homecinemavideo": "TV & Video",
    "horror": "Filme",
    "horrorkomoedie": "Filme",
    "horrorkomödie": "Filme",
    "hp tintenpatronen": "Computer & Zubehör",
    "hp toner": "Computer & Zubehör",
    "hptintenpatronen": "Computer & Zubehör",
    "hptoner": "Computer & Zubehör",
    "idisplayit": "Spielwaren",
    "induktionskochfelder": "Haushalt & Küche",
    "interdentalbuersten": "Drogerie",
    "interdentalbürsten": "Drogerie",
    "internet radio": "HiFi & Audio",
    "internetradio": "HiFi & Audio",
    "jump n run geschicklichkeit": "Videogames",
    "jumpnrungeschicklichkeit": "Videogames",
    "kaffee espressomaschinen": "Haushalt & Küche",
    "kaffee teezubereitung": "Haushalt & Küche",
    "kaffeeespressomaschinen": "Haushalt & Küche",
    "kaffeemuehlen": "Haushalt & Küche",
    "kaffeemühlen": "Haushalt & Küche",
    "kaffeeteezubereitung": "Haushalt & Küche",
    "kalender": "Bürobedarf & Schreibwaren",
    "kamera handgriffe": "Foto & Video",
    "kamerahandgriffe": "Foto & Video",
    "karaffen dekanter": "Haushalt & Küche",
    "karaffendekanter": "Haushalt & Küche",
    "karten software": "Computer & Zubehör",
    "kartensoftware": "Computer & Zubehör",
    "kartenspiele": "Spielwaren",
    "keyboards": "HiFi & Audio",
    "kfz batterien": "Auto & Motorrad",
    "kfz ladegeraete": "Auto & Motorrad",
    "kfz ladegeräte": "Auto & Motorrad",
    "kfzbatterien": "Auto & Motorrad",
    "kfzladegeraete": "Auto & Motorrad",
    "kfzladegeräte": "Auto & Motorrad",
    "kinderfahrzeuge": "Spielwaren",
    "kindersitze": "Auto & Motorrad",
    "kinderspiele": "Spielwaren",
    "kinderspielzeug": "Spielwaren",
    "klassische vibratoren": "Drogerie",
    "klassisches drama": "Filme",
    "klassischesdrama": "Filme",
    "klassischevibratoren": "Drogerie",
    "klimageraete": "Haushalt & Küche",
    "klimageräte": "Haushalt & Küche",
    "klingel tuersprechanlage": "Garten & Baumarkt",
    "klingel türsprechanlage": "Garten & Baumarkt",
    "klingeltuersprechanlage": "Garten & Baumarkt",
    "klingeltürsprechanlage": "Garten & Baumarkt",
    "knopfzellen": "Garten & Baumarkt",
    "koaxiallautsprecher": "Auto & Motorrad",
    "koch backgeraete": "Haushalt & Küche",
    "koch backgeräte": "Haushalt & Küche",
    "kochbackgeraete": "Haushalt & Küche",
    "kochbackgeräte": "Haushalt & Küche",
    "kochgeschirr": "Haushalt & Küche",
    "kochkellen": "Haushalt & Küche",
    "koerper fussmassage": "Garten & Baumarkt",
    "koerperfussmassage": "Garten & Baumarkt",
    "koerperpflege": "Drogerie",
    "komoedie": "Filme",
    "kompatible tintenpatronen": "Computer & Zubehör",
    "kompatibler toner": "Computer & Zubehör",
    "kompatiblertoner": "Computer & Zubehör",
    "kompatibletintenpatronen": "Computer & Zubehör",
    "komplett sets": "Computer & Zubehör",
    "komplettsets": "Computer & Zubehör",
    "komplettsysteme": "Computer & Zubehör",
    "komponentensysteme": "Auto & Motorrad",
    "komödie": "Filme",
    "kontaktlinsen": "Drogerie",
    "kopfhoerer": "HiFi & Audio",
    "kopfhörer": "HiFi & Audio",
    "kreissaegen": "Garten & Baumarkt",
    "kreissägen": "Garten & Baumarkt",
    "krimi": "Filme",
    "krimikomoedie": "Filme",
    "krimikomödie": "Filme",
    "kuechengeraete": "Haushalt & Küche",
    "kuechenhelfer": "Haushalt & Küche",
    "kuechenmaschinen": "Haushalt & Küche",
    "kuechenwaagen": "Haushalt & Küche",
    "kuehl gefrierkombinationen": "Haushalt & Küche",
    "kuehlboxen": "Sport & Freizeit",
    "kuehlgefrierkombinationen": "Haushalt & Küche",
    "kuehlschraenke": "Haushalt & Küche",
    "kyocera toner": "Computer & Zubehör",
    "kyoceratoner": "Computer & Zubehör",
    "körper fussmassage": "Garten & Baumarkt",
    "körperfussmassage": "Garten & Baumarkt",
    "körperpflege": "Drogerie",
    "küchengeräte": "Haushalt & Küche",
    "küchenhelfer": "Haushalt & Küche",
    "küchenmaschinen": "Haushalt & Küche",
    "küchenwaagen": "Haushalt & Küche",
    "kühl gefrierkombinationen": "Haushalt & Küche",
    "kühlboxen": "Sport & Freizeit",
    "kühlgefrierkombinationen": "Haushalt & Küche",
    "kühlschränke": "Haushalt & Küche",
    "ladegeraete netzadapter": "Smartphones & Mobiltelefone",
    "ladegeraetenetzadapter": "Smartphones & Mobiltelefone",
    "ladegeräte netzadapter": "Smartphones & Mobiltelefone",
    "ladegerätenetzadapter": "Smartphones & Mobiltelefone",
    "ladestationen": "Auto & Motorrad",
    "lager transport": "Garten & Baumarkt",
    "lagertransport": "Garten & Baumarkt",
    "laminiergeraete": "Bürobedarf & Schreibwaren",
    "laminiergeräte": "Bürobedarf & Schreibwaren",
    "lampen leuchtmittel": "Garten & Baumarkt",
    "lampen reflektoren": "Foto & Video",
    "lampenleuchtmittel": "Garten & Baumarkt",
    "lampenreflektoren": "Foto & Video",
    "laubblaeser und sauger": "Garten & Baumarkt",
    "laubblaeserundsauger": "Garten & Baumarkt",
    "laubbläser und sauger": "Garten & Baumarkt",
    "laubbläserundsauger": "Garten & Baumarkt",
    "laufschuhe": "Sport & Freizeit",
    "lautsprecher": "HiFi & Audio",
    "led leuchten": "Garten & Baumarkt",
    "led leuchtmittel": "Garten & Baumarkt",
    "ledleuchten": "Garten & Baumarkt",
    "ledleuchtmittel": "Garten & Baumarkt",
    "lego": "Spielwaren",
    "lego architecture": "Spielwaren",
    "lego botanicals": "Spielwaren",
    "lego city": "Spielwaren",
    "lego dreamzzz": "Spielwaren",
    "lego editions": "Spielwaren",
    "lego harry potter": "Spielwaren",
    "lego icons": "Spielwaren",
    "lego ideas": "Spielwaren",
    "lego marvel": "Spielwaren",
    "lego one piece": "Spielwaren",
    "lego pokemon": "Spielwaren",
    "lego simpsons": "Spielwaren",
    "lego speed champions": "Spielwaren",
    "lego star wars": "Spielwaren",
    "lego super mario": "Spielwaren",
    "lego technic": "Spielwaren",
    "lego the legend of zelda": "Spielwaren",
    "lego the lord of the rings": "Spielwaren",
    "legoarchitecture": "Spielwaren",
    "legobotanicals": "Spielwaren",
    "legocity": "Spielwaren",
    "legodreamzzz": "Spielwaren",
    "legoeditions": "Spielwaren",
    "legoharrypotter": "Spielwaren",
    "legoicons": "Spielwaren",
    "legoideas": "Spielwaren",
    "legomarvel": "Spielwaren",
    "legoonepiece": "Spielwaren",
    "legopokemon": "Spielwaren",
    "legosimpsons": "Spielwaren",
    "legospeedchampions": "Spielwaren",
    "legostarwars": "Spielwaren",
    "legosupermario": "Spielwaren",
    "legotechnic": "Spielwaren",
    "legothelegendofzelda": "Spielwaren",
    "legothelordoftherings": "Spielwaren",
    "lenkrad komplettsets": "Videogames",
    "lenkradkomplettsets": "Videogames",
    "lenkraeder": "Videogames",
    "lenkräder": "Videogames",
    "lesegeraete fuer speicherkarten": "Foto & Video",
    "lesegeraetefuerspeicherkarten": "Foto & Video",
    "lesegeräte für speicherkarten": "Foto & Video",
    "lesegerätefürspeicherkarten": "Foto & Video",
    "lexmark toner": "Computer & Zubehör",
    "lexmarktoner": "Computer & Zubehör",
    "live monitorboxen": "HiFi & Audio",
    "livemonitorboxen": "HiFi & Audio",
    "lnbs": "TV & Video",
    "lockenstaebe buersten": "Drogerie",
    "lockenstaebebuersten": "Drogerie",
    "lockenstäbe bürsten": "Drogerie",
    "lockenstäbebürsten": "Drogerie",
    "luftbefeuchter luftentfeuchter luftreiniger": "Haushalt & Küche",
    "luftbefeuchterluftentfeuchterluftreiniger": "Haushalt & Küche",
    "lufterfrischer": "Auto & Motorrad",
    "lumibricks funwhole": "Spielwaren",
    "lumibricksfunwhole": "Spielwaren",
    "lust liebe": "Drogerie",
    "lustliebe": "Drogerie",
    "maeuse": "Computer & Zubehör",
    "mainboards": "Computer & Zubehör",
    "massagestaebe": "Drogerie",
    "massagestäbe": "Drogerie",
    "masturbatoren": "Drogerie",
    "mattel brick shop": "Spielwaren",
    "mattelbrickshop": "Spielwaren",
    "maus tastatur sets": "Computer & Zubehör",
    "maustastatursets": "Computer & Zubehör",
    "mega construx": "Spielwaren",
    "megaconstrux": "Spielwaren",
    "mehr drama": "Filme",
    "mehr komoedie": "Filme",
    "mehr komödie": "Filme",
    "mehrdrama": "Filme",
    "mehrkomoedie": "Filme",
    "mehrkomödie": "Filme",
    "mess schaltgeraete": "Garten & Baumarkt",
    "mess schaltgeräte": "Garten & Baumarkt",
    "messer": "Haushalt & Küche",
    "messerbloecke": "Haushalt & Küche",
    "messerblöcke": "Haushalt & Küche",
    "messschaltgeraete": "Garten & Baumarkt",
    "messschaltgeräte": "Garten & Baumarkt",
    "messwerkzeuge": "Garten & Baumarkt",
    "micro aaa": "Garten & Baumarkt",
    "microaaa": "Garten & Baumarkt",
    "microsd speicherkarten": "Foto & Video",
    "microsdspeicherkarten": "Foto & Video",
    "midi audio interfaces": "Smartphones & Mobiltelefone",
    "midi controller": "HiFi & Audio",
    "midiaudiointerfaces": "Smartphones & Mobiltelefone",
    "midicontroller": "HiFi & Audio",
    "mignon aa": "Garten & Baumarkt",
    "mignon akkus aa": "Garten & Baumarkt",
    "mignonaa": "Garten & Baumarkt",
    "mignonakkusaa": "Garten & Baumarkt",
    "mikrofone": "HiFi & Audio",
    "mikrowellen": "Haushalt & Küche",
    "mini aaaa": "Garten & Baumarkt",
    "miniaaaa": "Garten & Baumarkt",
    "mischpulte": "HiFi & Audio",
    "mitteltoener": "Auto & Motorrad",
    "mitteltöner": "Auto & Motorrad",
    "mixer": "Haushalt & Küche",
    "mobile akku ladegeraete powerbanks": "Garten & Baumarkt",
    "mobile akku ladegeräte powerbanks": "Garten & Baumarkt",
    "mobileakkuladegeraetepowerbanks": "Garten & Baumarkt",
    "mobileakkuladegerätepowerbanks": "Garten & Baumarkt",
    "mobiles internet umts 3g lte 4g": "Computer & Zubehör",
    "mobilesinternetumts3glte4g": "Computer & Zubehör",
    "mobilteile": "Smartphones & Mobiltelefone",
    "monatslinsen": "Drogerie",
    "monitore": "Computer & Zubehör",
    "mono akkus d": "Garten & Baumarkt",
    "mono d": "Garten & Baumarkt",
    "monoakkusd": "Garten & Baumarkt",
    "monod": "Garten & Baumarkt",
    "motorrad headsets": "Auto & Motorrad",
    "motorradheadsets": "Auto & Motorrad",
    "mould king": "Spielwaren",
    "mouldking": "Spielwaren",
    "multicopter": "Spielwaren",
    "multifokale kontaktlinsen": "Drogerie",
    "multifokalekontaktlinsen": "Drogerie",
    "multifunktionsgeraete": "Computer & Zubehör",
    "multifunktionsgeräte": "Computer & Zubehör",
    "multimedia player": "TV & Video",
    "multimediaplayer": "TV & Video",
    "mund zahnpflege": "Drogerie",
    "mund zahnpflegeprodukte": "Drogerie",
    "mundduschen": "Drogerie",
    "mundzahnpflege": "Drogerie",
    "mundzahnpflegeprodukte": "Drogerie",
    "musik": "Filme",
    "musikinstrumente": "HiFi & Audio",
    "musikinstrumente pro audio": "HiFi & Audio",
    "musikinstrumenteproaudio": "HiFi & Audio",
    "mystery": "Filme",
    "mäuse": "Computer & Zubehör",
    "nas systeme": "Computer & Zubehör",
    "nass trockensauger zubehoer": "Garten & Baumarkt",
    "nass trockensauger zubehör": "Garten & Baumarkt",
    "nassrasierer": "Drogerie",
    "nasstrockensaugerzubehoer": "Garten & Baumarkt",
    "nasstrockensaugerzubehör": "Garten & Baumarkt",
    "nassysteme": "Computer & Zubehör",
    "natur": "Filme",
    "navigation": "Computer & Zubehör",
    "nespresso maschinen": "Haushalt & Küche",
    "nespressomaschinen": "Haushalt & Küche",
    "netzwerk player receiver": "HiFi & Audio",
    "netzwerkkarten": "Computer & Zubehör",
    "netzwerkplayerreceiver": "HiFi & Audio",
    "netzwerktechnik": "Computer & Zubehör",
    "nintendo switch": "Videogames",
    "nintendo switch 2": "Videogames",
    "nintendo switch 2 games": "Videogames",
    "nintendo switch 2 konsolen": "Videogames",
    "nintendo switch games": "Videogames",
    "nintendo switch konsolen": "Videogames",
    "nintendoswitch": "Videogames",
    "nintendoswitch2": "Videogames",
    "nintendoswitch2games": "Videogames",
    "nintendoswitch2konsolen": "Videogames",
    "nintendoswitchgames": "Videogames",
    "nintendoswitchkonsolen": "Videogames",
    "notebooks": "Computer & Zubehör",
    "notebooks tablets ereader": "Computer & Zubehör",
    "notebookstabletsereader": "Computer & Zubehör",
    "oberfraesen": "Garten & Baumarkt",
    "oberfräsen": "Garten & Baumarkt",
    "oberschalen cover": "Smartphones & Mobiltelefone",
    "oberschalencover": "Smartphones & Mobiltelefone",
    "objektive": "Foto & Video",
    "offroad suv ganzjahresreifen": "Auto & Motorrad",
    "offroad suv sommerreifen": "Auto & Motorrad",
    "offroad suv winterreifen": "Auto & Motorrad",
    "offroadsuvganzjahresreifen": "Auto & Motorrad",
    "offroadsuvsommerreifen": "Auto & Motorrad",
    "offroadsuvwinterreifen": "Auto & Motorrad",
    "oki toner": "Computer & Zubehör",
    "okitoner": "Computer & Zubehör",
    "oneplus h2516": "Smartphones & Mobiltelefone",
    "oneplush2516": "Smartphones & Mobiltelefone",
    "oppo h2007": "Smartphones & Mobiltelefone",
    "oppoh2007": "Smartphones & Mobiltelefone",
    "optik": "Sport & Freizeit",
    "outdoor spielzeug": "Spielwaren",
    "outdoorspielzeug": "Spielwaren",
    "pa lautsprecher": "HiFi & Audio",
    "paarvibratoren": "Drogerie",
    "palautsprecher": "HiFi & Audio",
    "panini": "Spielwaren",
    "pantasy": "Spielwaren",
    "papier": "Bürobedarf & Schreibwaren",
    "parfuemerie": "Drogerie",
    "parfum": "Drogerie",
    "parfümerie": "Drogerie",
    "pc gehaeuse": "Computer & Zubehör",
    "pc gehäuse": "Computer & Zubehör",
    "pc komponenten": "Computer & Zubehör",
    "pc lautsprechersysteme": "HiFi & Audio",
    "pc netzteile": "Computer & Zubehör",
    "pcgehaeuse": "Computer & Zubehör",
    "pcgehäuse": "Computer & Zubehör",
    "pckomponenten": "Computer & Zubehör",
    "pclautsprechersysteme": "HiFi & Audio",
    "pcnetzteile": "Computer & Zubehör",
    "pedale": "Videogames",
    "pedale effektgeraete": "HiFi & Audio",
    "pedale effektgeräte": "HiFi & Audio",
    "pedaleeffektgeraete": "HiFi & Audio",
    "pedaleeffektgeräte": "HiFi & Audio",
    "penisringe": "Drogerie",
    "peripheriegeraete": "Computer & Zubehör",
    "peripheriegeräte": "Computer & Zubehör",
    "pfannen": "Haushalt & Küche",
    "pfannensets": "Haushalt & Küche",
    "pflegemittel fluessig": "Drogerie",
    "pflegemittel flüssig": "Drogerie",
    "pflegemittelfluessig": "Drogerie",
    "pflegemittelflüssig": "Drogerie",
    "pinsel": "Haushalt & Küche",
    "pkw ganzjahresreifen": "Auto & Motorrad",
    "pkw sommerreifen": "Auto & Motorrad",
    "pkw winterreifen": "Auto & Motorrad",
    "pkwganzjahresreifen": "Auto & Motorrad",
    "pkwsommerreifen": "Auto & Motorrad",
    "pkwwinterreifen": "Auto & Motorrad",
    "plattenspieler": "HiFi & Audio",
    "playmobil knights": "Spielwaren",
    "playmobilknights": "Spielwaren",
    "playstation 4": "Videogames",
    "playstation 5": "Videogames",
    "playstation vr hardware": "Videogames",
    "playstation vr2 hardware": "Videogames",
    "playstation4": "Videogames",
    "playstation5": "Videogames",
    "playstationvr2hardware": "Videogames",
    "playstationvrhardware": "Videogames",
    "pneus": "Auto & Motorrad",
    "pools": "Garten & Baumarkt",
    "portable lautsprecher": "HiFi & Audio",
    "portablelautsprecher": "HiFi & Audio",
    "portables": "HiFi & Audio",
    "powerline adapter": "Computer & Zubehör",
    "powerlineadapter": "Computer & Zubehör",
    "praesentation": "Bürobedarf & Schreibwaren",
    "professional audio djing": "HiFi & Audio",
    "professionalaudiodjing": "HiFi & Audio",
    "prostatavibratoren": "Drogerie",
    "prozessoren": "Computer & Zubehör",
    "prozessorkuehler": "Computer & Zubehör",
    "prozessorkühler": "Computer & Zubehör",
    "präsentation": "Bürobedarf & Schreibwaren",
    "ps4 games": "Videogames",
    "ps4games": "Videogames",
    "ps5 games": "Videogames",
    "ps5 konsolen": "Videogames",
    "ps5games": "Videogames",
    "ps5konsolen": "Videogames",
    "pumpen": "Sport & Freizeit",
    "rabbit vibratoren": "Drogerie",
    "rabbitvibratoren": "Drogerie",
    "raclette wok tischgrill": "Haushalt & Küche",
    "raclettewoktischgrill": "Haushalt & Küche",
    "radar": "Sport & Freizeit",
    "radios radio recorder": "HiFi & Audio",
    "radiosradiorecorder": "HiFi & Audio",
    "radiowecker": "HiFi & Audio",
    "rasenpflege": "Garten & Baumarkt",
    "rasierschaum rasiergel": "Drogerie",
    "rasierschaumrasiergel": "Drogerie",
    "rasur enthaarung": "Drogerie",
    "rasur haarpflege": "Drogerie",
    "rasurenthaarung": "Drogerie",
    "rasurhaarpflege": "Drogerie",
    "ratgeber": "Filme",
    "raumduft": "Garten & Baumarkt",
    "rc modelle": "Spielwaren",
    "rcmodelle": "Spielwaren",
    "receiver": "HiFi & Audio",
    "reiben": "Haushalt & Küche",
    "reifen": "Auto & Motorrad",
    "reise": "Filme",
    "rennspiele": "Videogames",
    "reobrix": "Spielwaren",
    "ricoh toner": "Computer & Zubehör",
    "ricohtoner": "Computer & Zubehör",
    "rollenspiele adventures": "Videogames",
    "rollenspieleadventures": "Videogames",
    "rollentrainer": "Sport & Freizeit",
    "romantische komoedie": "Filme",
    "romantische komödie": "Filme",
    "romantischekomoedie": "Filme",
    "romantischekomödie": "Filme",
    "router modems": "Computer & Zubehör",
    "routermodems": "Computer & Zubehör",
    "rucksaecke": "Sport & Freizeit",
    "rucksäcke": "Sport & Freizeit",
    "saegen fraesen": "Garten & Baumarkt",
    "saegenfraesen": "Garten & Baumarkt",
    "samsung h1": "Smartphones & Mobiltelefone",
    "samsungh1": "Smartphones & Mobiltelefone",
    "sandwichtoaster waffeleisen": "Haushalt & Küche",
    "sandwichtoasterwaffeleisen": "Haushalt & Küche",
    "saucenloeffel": "Haushalt & Küche",
    "saucenlöffel": "Haushalt & Küche",
    "saug und wischroboter": "Haushalt & Küche",
    "saugundwischroboter": "Haushalt & Küche",
    "scanner": "Computer & Zubehör",
    "schaeler": "Haushalt & Küche",
    "scheren": "Haushalt & Küche",
    "schleifen wetzen": "Haushalt & Küche",
    "schleifenwetzen": "Haushalt & Küche",
    "schmuck": "Uhren",
    "schneidegeraete": "Bürobedarf & Schreibwaren",
    "schneidegeräte": "Bürobedarf & Schreibwaren",
    "schneideplotter": "Computer & Zubehör",
    "schneidunterlagen": "Haushalt & Küche",
    "schoepfloeffel": "Haushalt & Küche",
    "schreibmaterial": "Bürobedarf & Schreibwaren",
    "schuhe": "Drogerie",
    "schwingschleifer": "Garten & Baumarkt",
    "schäler": "Haushalt & Küche",
    "schöpflöffel": "Haushalt & Küche",
    "science fiction": "Filme",
    "sciencefiction": "Filme",
    "sd speicherkarten": "Foto & Video",
    "sdspeicherkarten": "Foto & Video",
    "seife": "Drogerie",
    "sensoren melder": "Garten & Baumarkt",
    "sensorenmelder": "Garten & Baumarkt",
    "service": "Haushalt & Küche",
    "sicherheit ueberwachung": "Garten & Baumarkt",
    "sicherheit überwachung": "Garten & Baumarkt",
    "sicherheitueberwachung": "Garten & Baumarkt",
    "sicherheitüberwachung": "Garten & Baumarkt",
    "siebtraegermaschinen": "Haushalt & Küche",
    "siebträgermaschinen": "Haushalt & Küche",
    "sim racing flying": "Videogames",
    "sim rigs rennsitze": "Videogames",
    "simracingflying": "Videogames",
    "simrigsrennsitze": "Videogames",
    "simulationen": "Videogames",
    "skihelme": "Sport & Freizeit",
    "slapstick komoedie": "Filme",
    "slapstick komödie": "Filme",
    "slapstickkomoedie": "Filme",
    "slapstickkomödie": "Filme",
    "slip vibratoren": "Drogerie",
    "slipvibratoren": "Drogerie",
    "smart home": "Garten & Baumarkt",
    "smart speaker": "HiFi & Audio",
    "smarte brillen": "Smartphones & Mobiltelefone",
    "smartebrillen": "Smartphones & Mobiltelefone",
    "smarthome": "Garten & Baumarkt",
    "smartphones": "Smartphones & Mobiltelefone",
    "smartphones mobiltelefone": "Smartphones & Mobiltelefone",
    "smartphonesmobiltelefone": "Smartphones & Mobiltelefone",
    "smartspeaker": "HiFi & Audio",
    "smartwatches": "Smartphones & Mobiltelefone",
    "sofortbildkameras": "Foto & Video",
    "software pakete microsoft": "Computer & Zubehör",
    "softwarepaketemicrosoft": "Computer & Zubehör",
    "solar ladegeraete": "Garten & Baumarkt",
    "solar ladegeräte": "Garten & Baumarkt",
    "solarladegeraete": "Garten & Baumarkt",
    "solarladegeräte": "Garten & Baumarkt",
    "solid state drives ssd": "Computer & Zubehör",
    "solidstatedrivesssd": "Computer & Zubehör",
    "sonnenbrillen": "Sport & Freizeit",
    "sonstige akkus": "Garten & Baumarkt",
    "sonstige camping outdoorprodukte": "Sport & Freizeit",
    "sonstige einzelkomponenten": "HiFi & Audio",
    "sonstige gartengeraete": "Garten & Baumarkt",
    "sonstige gartengeräte": "Garten & Baumarkt",
    "sonstige gps navigations geraete": "Computer & Zubehör",
    "sonstige gps navigations geräte": "Computer & Zubehör",
    "sonstige handheld konsolen": "Videogames",
    "sonstige haushaltsgeraete": "Haushalt & Küche",
    "sonstige haushaltsgeräte": "Haushalt & Küche",
    "sonstige kaffeemaschinen": "Haushalt & Küche",
    "sonstige kuechengeraete": "Haushalt & Küche",
    "sonstige küchengeräte": "Haushalt & Küche",
    "sonstige musikinstrumente": "HiFi & Audio",
    "sonstige rennbahnen": "Spielwaren",
    "sonstige saegen fraesen": "Garten & Baumarkt",
    "sonstige spielekonsolen": "Videogames",
    "sonstige sägen fräsen": "Garten & Baumarkt",
    "sonstigeakkus": "Garten & Baumarkt",
    "sonstigecampingoutdoorprodukte": "Sport & Freizeit",
    "sonstigeeinzelkomponenten": "HiFi & Audio",
    "sonstigegartengeraete": "Garten & Baumarkt",
    "sonstigegartengeräte": "Garten & Baumarkt",
    "sonstigegpsnavigationsgeraete": "Computer & Zubehör",
    "sonstigegpsnavigationsgeräte": "Computer & Zubehör",
    "sonstigehandheldkonsolen": "Videogames",
    "sonstigehaushaltsgeraete": "Haushalt & Küche",
    "sonstigehaushaltsgeräte": "Haushalt & Küche",
    "sonstigekaffeemaschinen": "Haushalt & Küche",
    "sonstigekuechengeraete": "Haushalt & Küche",
    "sonstigeküchengeräte": "Haushalt & Küche",
    "sonstigemusikinstrumente": "HiFi & Audio",
    "sonstigerennbahnen": "Spielwaren",
    "sonstiges": "Garten & Baumarkt",
    "sonstiges elektronisches spielzeug": "Spielwaren",
    "sonstiges gaming zubehoer": "Videogames",
    "sonstiges gaming zubehör": "Videogames",
    "sonstiges outdoor spielzeug": "Spielwaren",
    "sonstiges zubehoer": "Foto & Video",
    "sonstiges zubehoer fuer iphone": "Smartphones & Mobiltelefone",
    "sonstiges zubehör": "Foto & Video",
    "sonstiges zubehör für iphone": "Smartphones & Mobiltelefone",
    "sonstigesaegenfraesen": "Garten & Baumarkt",
    "sonstigeselektronischesspielzeug": "Spielwaren",
    "sonstigesgamingzubehoer": "Videogames",
    "sonstigesgamingzubehör": "Videogames",
    "sonstigesoutdoorspielzeug": "Spielwaren",
    "sonstigespielekonsolen": "Videogames",
    "sonstigeszubehoer": "Foto & Video",
    "sonstigeszubehoerfueriphone": "Smartphones & Mobiltelefone",
    "sonstigeszubehör": "Foto & Video",
    "sonstigeszubehörfüriphone": "Smartphones & Mobiltelefone",
    "sonstigesägenfräsen": "Garten & Baumarkt",
    "soundbars": "HiFi & Audio",
    "speicherkarten": "TV & Video",
    "spiele fuer sonstige konsolen": "Videogames",
    "spiele für sonstige konsolen": "Videogames",
    "spielefuersonstigekonsolen": "Videogames",
    "spielefürsonstigekonsolen": "Videogames",
    "spielesammlungen": "Videogames",
    "spielwaren": "Spielwaren",
    "spielzeugfiguren roboter": "Spielwaren",
    "spielzeugfigurenroboter": "Spielwaren",
    "spielzeugroboter": "Spielwaren",
    "spin master": "Spielwaren",
    "spinmaster": "Spielwaren",
    "spirituosen": "Haushalt & Küche",
    "sport": "Filme",
    "sport freizeit": "Sport & Freizeit",
    "sport pulsuhren": "Sport & Freizeit",
    "sportbrillen goggles": "Sport & Freizeit",
    "sportbrillengoggles": "Sport & Freizeit",
    "sportfreizeit": "Sport & Freizeit",
    "sportgeraete": "Sport & Freizeit",
    "sportgeräte": "Sport & Freizeit",
    "sportpulsuhren": "Sport & Freizeit",
    "sportspiele": "Videogames",
    "stative": "Foto & Video",
    "stative studiozubehoer": "Foto & Video",
    "stative studiozubehör": "Foto & Video",
    "stativestudiozubehoer": "Foto & Video",
    "stativestudiozubehör": "Foto & Video",
    "stativkoepfe": "Foto & Video",
    "stativköpfe": "Foto & Video",
    "staubsauger": "Haushalt & Küche",
    "steckdosenleisten": "Garten & Baumarkt",
    "stempeln": "Bürobedarf & Schreibwaren",
    "stichsaegen": "Garten & Baumarkt",
    "stichsägen": "Garten & Baumarkt",
    "strategie rollenspiele": "Spielwaren",
    "strategierollenspiele": "Spielwaren",
    "strategiespiele": "Videogames",
    "streaming server clients": "HiFi & Audio",
    "streamingserverclients": "HiFi & Audio",
    "stromspeicher": "Garten & Baumarkt",
    "studio mikrofone": "HiFi & Audio",
    "studio monitorboxen": "HiFi & Audio",
    "studiomikrofone": "HiFi & Audio",
    "studiomonitorboxen": "HiFi & Audio",
    "subwoofer": "Auto & Motorrad",
    "surroundsysteme": "HiFi & Audio",
    "switches 10 gbit": "Computer & Zubehör",
    "switches 1000 mbit": "Computer & Zubehör",
    "switches 2 5 gbit": "Computer & Zubehör",
    "switches1000mbit": "Computer & Zubehör",
    "switches10gbit": "Computer & Zubehör",
    "switches25gbit": "Computer & Zubehör",
    "synthesizer": "HiFi & Audio",
    "sägen fräsen": "Garten & Baumarkt",
    "sägenfräsen": "Garten & Baumarkt",
    "tablets": "Computer & Zubehör",
    "tageslinsen": "Drogerie",
    "tamper": "Haushalt & Küche",
    "taschen cover fuer iphone": "Smartphones & Mobiltelefone",
    "taschen cover für iphone": "Smartphones & Mobiltelefone",
    "taschencoverfueriphone": "Smartphones & Mobiltelefone",
    "taschencoverfüriphone": "Smartphones & Mobiltelefone",
    "taschenlampen": "Garten & Baumarkt",
    "taschenmesser tools": "Sport & Freizeit",
    "taschenmessertools": "Sport & Freizeit",
    "taschenrechner": "Bürobedarf & Schreibwaren",
    "tassen": "Haushalt & Küche",
    "tastaturen": "Computer & Zubehör",
    "tasteninstrumente": "HiFi & Audio",
    "telefon voip": "Smartphones & Mobiltelefone",
    "telefonvoip": "Smartphones & Mobiltelefone",
    "terrassenreiniger": "Garten & Baumarkt",
    "textilien": "Haushalt & Küche",
    "thermometer": "Haushalt & Küche",
    "thermoskannen bidons": "Haushalt & Küche",
    "thermoskannenbidons": "Haushalt & Küche",
    "thriller": "Filme",
    "tisch accessoires": "Haushalt & Küche",
    "tischaccessoires": "Haushalt & Küche",
    "tmc receiver": "Computer & Zubehör",
    "tmcreceiver": "Computer & Zubehör",
    "toaster": "Haushalt & Küche",
    "toepfe": "Haushalt & Küche",
    "tonabnehmer": "HiFi & Audio",
    "topfdeckel": "Haushalt & Küche",
    "topfsets": "Haushalt & Küche",
    "torische kontaktlinsen": "Drogerie",
    "torischekontaktlinsen": "Drogerie",
    "transceiver konverter": "Computer & Zubehör",
    "transceiverkonverter": "Computer & Zubehör",
    "trockner": "Haushalt & Küche",
    "tuner": "HiFi & Audio",
    "tv geraete": "TV & Video",
    "tv geraete zubehoer": "TV & Video",
    "tv geräte": "TV & Video",
    "tv geräte zubehör": "TV & Video",
    "tv receiver": "TV & Video",
    "tv serien": "Filme",
    "tv video": "TV & Video",
    "tvgeraete": "TV & Video",
    "tvgeraetezubehoer": "TV & Video",
    "tvgeräte": "TV & Video",
    "tvgerätezubehör": "TV & Video",
    "tvreceiver": "TV & Video",
    "tvserien": "Filme",
    "tvvideo": "TV & Video",
    "töpfe": "Haushalt & Küche",
    "uebersetzer": "Bürobedarf & Schreibwaren",
    "ueberwachungskameras": "Garten & Baumarkt",
    "uhren": "Uhren",
    "unisexduefte": "Drogerie",
    "unisexdüfte": "Drogerie",
    "veloanhaenger": "Sport & Freizeit",
    "veloanhänger": "Sport & Freizeit",
    "velofahren": "Sport & Freizeit",
    "velohelme": "Sport & Freizeit",
    "velos": "Sport & Freizeit",
    "velotraeger": "Sport & Freizeit",
    "veloträger": "Sport & Freizeit",
    "ventilatoren heizgeraete": "Haushalt & Küche",
    "ventilatoren heizgeräte": "Haushalt & Küche",
    "ventilatorenheizgeraete": "Haushalt & Küche",
    "ventilatorenheizgeräte": "Haushalt & Küche",
    "verbrauchsmaterial fuer drucker": "Computer & Zubehör",
    "verbrauchsmaterial für drucker": "Computer & Zubehör",
    "verbrauchsmaterialfuerdrucker": "Computer & Zubehör",
    "verbrauchsmaterialfürdrucker": "Computer & Zubehör",
    "verpacken versand": "Bürobedarf & Schreibwaren",
    "verpackenversand": "Bürobedarf & Schreibwaren",
    "verstaerker": "HiFi & Audio",
    "verstärker": "HiFi & Audio",
    "vibro eier": "Drogerie",
    "vibroeier": "Drogerie",
    "videobearbeitung": "TV & Video",
    "videogames": "Videogames",
    "videosysteme": "Garten & Baumarkt",
    "voice over ip voip": "Smartphones & Mobiltelefone",
    "voiceoveripvoip": "Smartphones & Mobiltelefone",
    "voip adapter": "Smartphones & Mobiltelefone",
    "voip router": "Smartphones & Mobiltelefone",
    "voip sonstiges": "Smartphones & Mobiltelefone",
    "voip telefone": "Smartphones & Mobiltelefone",
    "voipadapter": "Smartphones & Mobiltelefone",
    "voiprouter": "Smartphones & Mobiltelefone",
    "voipsonstiges": "Smartphones & Mobiltelefone",
    "voiptelefone": "Smartphones & Mobiltelefone",
    "vollautomaten": "Haushalt & Küche",
    "vorverstaerker": "HiFi & Audio",
    "vorverstärker": "HiFi & Audio",
    "vr brillen": "Smartphones & Mobiltelefone",
    "vrbrillen": "Smartphones & Mobiltelefone",
    "vtech": "Spielwaren",
    "wasch nass trockensauger": "Haushalt & Küche",
    "waschmaschinen": "Haushalt & Küche",
    "waschnasstrockensauger": "Haushalt & Küche",
    "wasserkocher": "Haushalt & Küche",
    "wein": "Haushalt & Küche",
    "wein spirituosen": "Haushalt & Küche",
    "weinkuehlschraenke": "Haushalt & Küche",
    "weinkühlschränke": "Haushalt & Küche",
    "weinspirituosen": "Haushalt & Küche",
    "wellness zubehoer": "Garten & Baumarkt",
    "wellness zubehör": "Garten & Baumarkt",
    "wellnesszubehoer": "Garten & Baumarkt",
    "wellnesszubehör": "Garten & Baumarkt",
    "werkzeuge werkstatt": "Garten & Baumarkt",
    "werkzeugewerkstatt": "Garten & Baumarkt",
    "werkzeugkoffer sets": "Garten & Baumarkt",
    "werkzeugkoffersets": "Garten & Baumarkt",
    "western": "Filme",
    "wetterstationen": "Garten & Baumarkt",
    "wheelbases": "Videogames",
    "winkelschleifer": "Garten & Baumarkt",
    "wirtschaftssimulationen": "Videogames",
    "wissenschaftliche taschenrechner": "Bürobedarf & Schreibwaren",
    "wissenschaftlichetaschenrechner": "Bürobedarf & Schreibwaren",
    "wlan adapter": "Computer & Zubehör",
    "wlanadapter": "Computer & Zubehör",
    "wohnen": "Garten & Baumarkt",
    "woofer": "Auto & Motorrad",
    "wuerzen": "Haushalt & Küche",
    "wurf sportspiele": "Spielwaren",
    "wurfsportspiele": "Spielwaren",
    "würzen": "Haushalt & Küche",
    "xbox one": "Videogames",
    "xbox one games": "Videogames",
    "xbox series x": "Videogames",
    "xbox series x games": "Videogames",
    "xbox series x s": "Videogames",
    "xbox series x s games": "Videogames",
    "xbox series x s konsolen": "Videogames",
    "xboxone": "Videogames",
    "xboxonegames": "Videogames",
    "xboxseriesx": "Videogames",
    "xboxseriesxgames": "Videogames",
    "xboxseriesxs": "Videogames",
    "xboxseriesxsgames": "Videogames",
    "xboxseriesxskonsolen": "Videogames",
    "xiaomi h2460": "Smartphones & Mobiltelefone",
    "xiaomih2460": "Smartphones & Mobiltelefone",
    "xqd cfexpress speicherkarten": "Foto & Video",
    "xqdcfexpressspeicherkarten": "Foto & Video",
    "zangen": "Garten & Baumarkt",
    "zelte": "Sport & Freizeit",
    "zentralen starter kits": "Garten & Baumarkt",
    "zentralenstarterkits": "Garten & Baumarkt",
    "zubehoer": "Garten & Baumarkt",
    "zubehoer fuer 3d drucker": "Computer & Zubehör",
    "zubehoer fuer blitzgeraete": "Foto & Video",
    "zubehoer fuer car hifi": "Auto & Motorrad",
    "zubehoer fuer festnetz telefone": "Smartphones & Mobiltelefone",
    "zubehoer fuer funkgeraete": "Smartphones & Mobiltelefone",
    "zubehoer fuer gardena": "Garten & Baumarkt",
    "zubehoer fuer gartengeraete": "Garten & Baumarkt",
    "zubehoer fuer getraenkezubereitung": "Haushalt & Küche",
    "zubehoer fuer grafikkarten": "Computer & Zubehör",
    "zubehoer fuer haarpflege": "Drogerie",
    "zubehoer fuer haus sicherheitstechnik": "Garten & Baumarkt",
    "zubehoer fuer haushaltsgeraete": "Haushalt & Küche",
    "zubehoer fuer kaffeemaschinen": "Haushalt & Küche",
    "zubehoer fuer kindersitze": "Auto & Motorrad",
    "zubehoer fuer kochgeschirr": "Haushalt & Küche",
    "zubehoer fuer kontaktlinsen": "Drogerie",
    "zubehoer fuer kuechengeraete": "Haushalt & Küche",
    "zubehoer fuer lampen leuchtmittel": "Garten & Baumarkt",
    "zubehoer fuer lampen reflektoren": "Foto & Video",
    "zubehoer fuer mobiltelefone": "Smartphones & Mobiltelefone",
    "zubehoer fuer nas systeme": "Computer & Zubehör",
    "zubehoer fuer nintendo switch": "Videogames",
    "zubehoer fuer nintendo switch 2": "Videogames",
    "zubehoer fuer professional audio": "HiFi & Audio",
    "zubehoer fuer ps5": "Videogames",
    "zubehoer fuer rasur enthaarung": "Drogerie",
    "zubehoer fuer rc modelle": "Spielwaren",
    "zubehoer fuer saegen fraesen": "Garten & Baumarkt",
    "zubehoer fuer sonstige konsolen": "Videogames",
    "zubehoer fuer sportgeraete": "Sport & Freizeit",
    "zubehoer fuer stative": "Foto & Video",
    "zubehoer fuer staubsauger": "Haushalt & Küche",
    "zubehoer fuer wasseraufbereiter": "Haushalt & Küche",
    "zubehoer fuer xbox series x s": "Videogames",
    "zubehoer masturbatoren": "Drogerie",
    "zubehoer vibratoren": "Drogerie",
    "zubehoer zu voip": "Smartphones & Mobiltelefone",
    "zubehoer zum grillieren": "Garten & Baumarkt",
    "zubehoerfuer3ddrucker": "Computer & Zubehör",
    "zubehoerfuerblitzgeraete": "Foto & Video",
    "zubehoerfuercarhifi": "Auto & Motorrad",
    "zubehoerfuerfestnetztelefone": "Smartphones & Mobiltelefone",
    "zubehoerfuerfunkgeraete": "Smartphones & Mobiltelefone",
    "zubehoerfuergardena": "Garten & Baumarkt",
    "zubehoerfuergartengeraete": "Garten & Baumarkt",
    "zubehoerfuergetraenkezubereitung": "Haushalt & Küche",
    "zubehoerfuergrafikkarten": "Computer & Zubehör",
    "zubehoerfuerhaarpflege": "Drogerie",
    "zubehoerfuerhaushaltsgeraete": "Haushalt & Küche",
    "zubehoerfuerhaussicherheitstechnik": "Garten & Baumarkt",
    "zubehoerfuerkaffeemaschinen": "Haushalt & Küche",
    "zubehoerfuerkindersitze": "Auto & Motorrad",
    "zubehoerfuerkochgeschirr": "Haushalt & Küche",
    "zubehoerfuerkontaktlinsen": "Drogerie",
    "zubehoerfuerkuechengeraete": "Haushalt & Küche",
    "zubehoerfuerlampenleuchtmittel": "Garten & Baumarkt",
    "zubehoerfuerlampenreflektoren": "Foto & Video",
    "zubehoerfuermobiltelefone": "Smartphones & Mobiltelefone",
    "zubehoerfuernassysteme": "Computer & Zubehör",
    "zubehoerfuernintendoswitch": "Videogames",
    "zubehoerfuernintendoswitch2": "Videogames",
    "zubehoerfuerprofessionalaudio": "HiFi & Audio",
    "zubehoerfuerps5": "Videogames",
    "zubehoerfuerrasurenthaarung": "Drogerie",
    "zubehoerfuerrcmodelle": "Spielwaren",
    "zubehoerfuersaegenfraesen": "Garten & Baumarkt",
    "zubehoerfuersonstigekonsolen": "Videogames",
    "zubehoerfuersportgeraete": "Sport & Freizeit",
    "zubehoerfuerstative": "Foto & Video",
    "zubehoerfuerstaubsauger": "Haushalt & Küche",
    "zubehoerfuerwasseraufbereiter": "Haushalt & Küche",
    "zubehoerfuerxboxseriesxs": "Videogames",
    "zubehoermasturbatoren": "Drogerie",
    "zubehoervibratoren": "Drogerie",
    "zubehoerzumgrillieren": "Garten & Baumarkt",
    "zubehoerzuvoip": "Smartphones & Mobiltelefone",
    "zubehör": "Garten & Baumarkt",
    "zubehör für 3d drucker": "Computer & Zubehör",
    "zubehör für blitzgeräte": "Foto & Video",
    "zubehör für car hifi": "Auto & Motorrad",
    "zubehör für festnetz telefone": "Smartphones & Mobiltelefone",
    "zubehör für funkgeräte": "Smartphones & Mobiltelefone",
    "zubehör für gardena": "Garten & Baumarkt",
    "zubehör für gartengeräte": "Garten & Baumarkt",
    "zubehör für getränkezubereitung": "Haushalt & Küche",
    "zubehör für grafikkarten": "Computer & Zubehör",
    "zubehör für haarpflege": "Drogerie",
    "zubehör für haus sicherheitstechnik": "Garten & Baumarkt",
    "zubehör für haushaltsgeräte": "Haushalt & Küche",
    "zubehör für kaffeemaschinen": "Haushalt & Küche",
    "zubehör für kindersitze": "Auto & Motorrad",
    "zubehör für kochgeschirr": "Haushalt & Küche",
    "zubehör für kontaktlinsen": "Drogerie",
    "zubehör für küchengeräte": "Haushalt & Küche",
    "zubehör für lampen leuchtmittel": "Garten & Baumarkt",
    "zubehör für lampen reflektoren": "Foto & Video",
    "zubehör für mobiltelefone": "Smartphones & Mobiltelefone",
    "zubehör für nas systeme": "Computer & Zubehör",
    "zubehör für nintendo switch": "Videogames",
    "zubehör für nintendo switch 2": "Videogames",
    "zubehör für professional audio": "HiFi & Audio",
    "zubehör für ps5": "Videogames",
    "zubehör für rasur enthaarung": "Drogerie",
    "zubehör für rc modelle": "Spielwaren",
    "zubehör für sonstige konsolen": "Videogames",
    "zubehör für sportgeräte": "Sport & Freizeit",
    "zubehör für stative": "Foto & Video",
    "zubehör für staubsauger": "Haushalt & Küche",
    "zubehör für sägen fräsen": "Garten & Baumarkt",
    "zubehör für wasseraufbereiter": "Haushalt & Küche",
    "zubehör für xbox series x s": "Videogames",
    "zubehör masturbatoren": "Drogerie",
    "zubehör vibratoren": "Drogerie",
    "zubehör zu voip": "Smartphones & Mobiltelefone",
    "zubehör zum grillieren": "Garten & Baumarkt",
    "zubehörfür3ddrucker": "Computer & Zubehör",
    "zubehörfürblitzgeräte": "Foto & Video",
    "zubehörfürcarhifi": "Auto & Motorrad",
    "zubehörfürfestnetztelefone": "Smartphones & Mobiltelefone",
    "zubehörfürfunkgeräte": "Smartphones & Mobiltelefone",
    "zubehörfürgardena": "Garten & Baumarkt",
    "zubehörfürgartengeräte": "Garten & Baumarkt",
    "zubehörfürgetränkezubereitung": "Haushalt & Küche",
    "zubehörfürgrafikkarten": "Computer & Zubehör",
    "zubehörfürhaarpflege": "Drogerie",
    "zubehörfürhaushaltsgeräte": "Haushalt & Küche",
    "zubehörfürhaussicherheitstechnik": "Garten & Baumarkt",
    "zubehörfürkaffeemaschinen": "Haushalt & Küche",
    "zubehörfürkindersitze": "Auto & Motorrad",
    "zubehörfürkochgeschirr": "Haushalt & Küche",
    "zubehörfürkontaktlinsen": "Drogerie",
    "zubehörfürküchengeräte": "Haushalt & Küche",
    "zubehörfürlampenleuchtmittel": "Garten & Baumarkt",
    "zubehörfürlampenreflektoren": "Foto & Video",
    "zubehörfürmobiltelefone": "Smartphones & Mobiltelefone",
    "zubehörfürnassysteme": "Computer & Zubehör",
    "zubehörfürnintendoswitch": "Videogames",
    "zubehörfürnintendoswitch2": "Videogames",
    "zubehörfürprofessionalaudio": "HiFi & Audio",
    "zubehörfürps5": "Videogames",
    "zubehörfürrasurenthaarung": "Drogerie",
    "zubehörfürrcmodelle": "Spielwaren",
    "zubehörfürsonstigekonsolen": "Videogames",
    "zubehörfürsportgeräte": "Sport & Freizeit",
    "zubehörfürstative": "Foto & Video",
    "zubehörfürstaubsauger": "Haushalt & Küche",
    "zubehörfürsägenfräsen": "Garten & Baumarkt",
    "zubehörfürwasseraufbereiter": "Haushalt & Küche",
    "zubehörfürxboxseriesxs": "Videogames",
    "zubehörmasturbatoren": "Drogerie",
    "zubehörvibratoren": "Drogerie",
    "zubehörzumgrillieren": "Garten & Baumarkt",
    "zubehörzuvoip": "Smartphones & Mobiltelefone",
    "übersetzer": "Bürobedarf & Schreibwaren",
    "überwachungskameras": "Garten & Baumarkt"
};

  const CANONICAL_ROOT_GROUPS = {
    'auto-motorrad': 'Auto & Motorrad',
    'auto motorrad': 'Auto & Motorrad',
    'bekleidung-schuhe': 'Bekleidung & Schuhe',
    'bekleidung schuhe': 'Bekleidung & Schuhe',
    'buerobedarf-schreibwaren': 'Bürobedarf & Schreibwaren',
    'buerobedarf schreibwaren': 'Bürobedarf & Schreibwaren',
    'computer-zubehoer': 'Computer & Zubehör',
    'computer zubehoer': 'Computer & Zubehör',
    'drogerie': 'Drogerie',
    'filme': 'Filme',
    'foto': 'Foto & Video',
    'foto-video': 'Foto & Video',
    'haus-garten': 'Garten & Baumarkt',
    'garten-baumarkt': 'Garten & Baumarkt',
    'haushalt-kueche': 'Haushalt & Küche',
    'haushalt kueche': 'Haushalt & Küche',
    'hifi-audio': 'HiFi & Audio',
    'hifi audio': 'HiFi & Audio',
    'lust-liebe': 'Drogerie',
    'musikinstrumente-pro-audio': 'HiFi & Audio',
    'navigation': 'Computer & Zubehör',
    'schmuck': 'Uhren',
    'smartphones-mobiltelefone': 'Smartphones & Mobiltelefone',
    'smartphones mobiltelefone': 'Smartphones & Mobiltelefone',
    'spielwaren': 'Spielwaren',
    'sport-freizeit': 'Sport & Freizeit',
    'sport freizeit': 'Sport & Freizeit',
    'telefon-voip': 'Smartphones & Mobiltelefone',
    'tv-video': 'TV & Video',
    'tv video': 'TV & Video',
    'uhren': 'Uhren',
    'videogames': 'Videogames',
    'wein-spirituosen': 'Haushalt & Küche',
    'werkzeuge-werkstatt': 'Garten & Baumarkt'
  };

  function normalizeRootSlug(slug) {
    if (!slug) return null;
    const clean = slug.split('-c')[0].toLowerCase().trim();
    return CANONICAL_ROOT_GROUPS[clean] || CANONICAL_ROOT_GROUPS[clean.replace(/-/g, ' ')] || null;
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
    // Spielwaren 🧸
    { regex: /\b(lego|legos|playmobil|cobi|cada|mega construx|fischertechnik|ravensburger|schleich|barbie|hot wheels|action figuren|funko|nerf|amiibo|spielwaren|spielzeug|puppe|puppen|pluesch|plüsch|autorennbahn|rc modelle|multicopter|puzzles|gesellschaftsspiele|familienspiele|kartenspiele)\b/i, group: 'Spielwaren', parent: 'Spielwaren' },

    // Haushalt & Küche ☕
    { regex: /\b(fritteuse|fritteusen|heissluftfritteuse|heissluftfritteusen|vollautomat|vollautomaten|kaffee|espressomaschine|espressomaschinen|kaffeemuehle|kaffeemühle|kuechengeraet|kuechengeraete|küchengerät|küchengeräte|haushaltsgeraet|haushaltsgeraete|haushaltsgerät|haushaltsgeräte|staubsauger|saugroboter|wischroboter|fensterreinigungsroboter|mikrowelle|mikrowellen|backofen|herd|kuehlschrank|kühlschrank|gefrierschrank|geschirrspueler|geschirrspüler|waschmaschine|waschmaschinen|waeschetrockner|wäschetrockner|mixer|blender|wasserkocher|toaster|thermoskanne|abfallsystem|raumduft|dampfgarer|slowcooker|saftpresse|entsafter|geschirr|besteck|glaeser|gläser|topf|toepfe|töpfe|pfanne|pfannen|kochgeschirr|spirituosen|wein|whisky|gin|rum|vodka)\b/i, group: 'Haushalt & Küche', parent: 'Haushalt & Küche' },

    // Drogerie 🧴
    { regex: /\b(haarglaetter|haarglätter|glaetteisen|glätteisen|bartschneider|haarschneider|rasierer|elektrorasierer|epilierer|haartrockner|foehn|föhn|zahnbuerste|zahnbürste|zahnbuersten|zahnbürsten|elektrozahnbuerste|parfum|parfüm|duft|duefte|düfte|eau de|duschpflege|duschgel|shampoo|seife|geschenkset|geschenksets|hautpflege|koerperpflege|körperpflege|kosmetik|make-up|makeup|sonnenschutz|kontaktlinsen|hygiene)\b/i, group: 'Drogerie', parent: 'Drogerie' },

    // Computer & Zubehör 💻
    { regex: /\b(usb|speicherstick|speichersticks|ssd|hdds?|solid state|festplatte|festplatten|grafikkarte|grafikkarten|notebook|notebooks|laptop|laptops|tablet|tablets|ebook|monitore|monitor|drucker|scanner|nas|mainboard|mainboards|prozessor|prozessoren|cpu|gpu|pc gehaeuse|netzteil|netzteile|ladegeraet|ladegerät|netzadapter|kabel|hub|dockingstation|tastatur|tastaturen|maus|maeuse|mäuse|mausmatte|webcam|headset|aktenvernichter|papierschredder|arbeitsspeicher|ram|netzwerk|wlan|router|switch|server|western digital)\b/i, group: 'Computer & Zubehör', parent: 'Computer & Zubehör' },

    // Smartphones & Mobiltelefone 📱
    { regex: /\b(smartphone|smartphones|mobiltelefon|mobiltelefone|handy|handys|iphone|galaxy|pixel|smartring|smartringe|smartwatch|smartwatches|activity tracker|huelle|huellen|hülle|hüllen|cover|schutzfolie|panzerglas|ladekabel|powerbank|powerbanks|magsafe|funktelefon|festnetz)\b/i, group: 'Smartphones & Mobiltelefone', parent: 'Smartphones & Mobiltelefone' },

    // HiFi & Audio 🎧
    { regex: /\b(kopfhoerer|kopfhörer|in-ear|earbuds|lautsprecher|bluetooth lautsprecher|soundbar|plattenspieler|receiver|av receiver|verstaerker|verstärker|hifi|radio|cd player|dac|subwoofer|mikrofon|musikinstrument|gitarre|piano|keyboard)\b/i, group: 'HiFi & Audio', parent: 'HiFi & Audio' },

    // TV & Video 📺
    { regex: /\b(tv|fernseher|beamer|projektor|home cinema|heimkino|blu-ray player|dvd player|actioncam|actionkamera|camcorder|media player|streaming stick|chromecast|apple tv)\b/i, group: 'TV & Video', parent: 'TV & Video' },

    // Foto & Video 📷
    { regex: /\b(kamera|kameras|digitalkamera|spiegellose|dslr|objektiv|objektive|stativ|stative|blitz|fotostudio|drohne|sofortbildkamera)\b/i, group: 'Foto & Video', parent: 'Foto & Video' },

    // Filme 🎬
    { regex: /\b(dvd|blu-ray|blu ray|4k ultra hd|film|filme|kino|serie|tv serien|western|abenteuer|action|krimi|drama|komoedie|komödie|thriller|horror|anime|dokumentation)\b/i, group: 'Filme', parent: 'Filme' },

    // Videogames 🎮
    { regex: /\b(game|games|spiel|spiele|nintendo|switch|playstation|ps5|ps4|ps3|xbox|pc spiele|konsole|konsolen|gamepad|controller|lenkrad|vr headset|amiibo|simulationen|rennspiel)\b/i, group: 'Videogames', parent: 'Videogames' },

    // Sport & Freizeit ⚽
    { regex: /\b(crosstrainer|laufband|laufbaender|laufbänder|ergometer|rudergeraet|rudergerät|fitness|krafttraining|hantel|hanteln|matten|velo|velos|fahrrad|ebike|e-bike|velohelm|skibrille|skihelm|koffer|rucksack|taschenmesser|fernglas|camping|zelt|schlafsack|tretroller|scooter|inline skates|gps|navigation|navigations)\b/i, group: 'Sport & Freizeit', parent: 'Sport & Freizeit' },

    // Auto & Motorrad 🚗
    { regex: /\b(reifen|pneus|sommerreifen|winterreifen|allwetterreifen|felgen|dachbox|dachboxen|dachtraeger|dachträger|kindersitz|kindersitze|autozubehoer|car hifi|motorradhelm|dashcam)\b/i, group: 'Auto & Motorrad', parent: 'Auto & Motorrad' },

    // Garten & Baumarkt 🪴
    { regex: /\b(rasenmaeher|rasenmäher|rasenroboter|grill|gasgrill|elektrogrill|holzkohlegrill|bohrmaschine|akkuschrauber|saege|säge|schleifer|schalter|taster|steckdose|lampe|lampen|leuchtmittel|led|smart home|gartenmoebel|gartenmöbel|hochdruckreiniger|werkzeug|werkzeuge)\b/i, group: 'Garten & Baumarkt', parent: 'Garten & Baumarkt' },

    // Uhren ⌚
    { regex: /\b(uhr|uhren|armbanduhr|damenuhr|herrenuhr|chronograph|automatikuhr|wanduhr|wecker)\b/i, group: 'Uhren', parent: 'Uhren' },

    // Kleidung & Mode 👕
    { regex: /\b(kleidung|bekleidung|jacke|jacken|hose|hosen|t-shirt|pullover|hemd|kleid|schuhe|sneaker|stiefel|tasche|taschen|handtasche|rucksack|sonnenbrille|sonnenbrillen|schmuck|ring|kette)\b/i, group: 'Kleidung & Mode', parent: 'Kleidung & Mode' },

    // Bücher & Medien 📚
    { regex: /\b(buch|buecher|bücher|roman|taschenbuch|sachbuch|hoerbuch|hörbuch|comic|manga|zeitschrift)\b/i, group: 'Bücher & Medien', parent: 'Bücher & Medien' }
  ];

  // Universal Hierarchical Path Resolver: Returns [RootGroup, SubGroup/Parent, LeafCategory]
  function resolveCategoryPath(categoryName, card = null) {
    if (!categoryName) return ['Sonstiges', 'Sonstiges', 'Sonstiges'];
    const norm = categoryName.trim().toLowerCase();
    const slug = norm.replace(/[^a-z0-9]/g, '');
    const spaceSlug = norm.replace(/-/g, ' ');
    const umlautNorm = normalizeUmlautKey(norm);

    // 1. Direct Link Extraction from Product Card URL (Primary & 100% Authoritative Site Taxonomy)
    if (card) {
      const hrefs = getCardHrefs(card);
      for (const href of hrefs) {
        const match = href.match(/\/(?:preisvergleich|produktsuche)\/([^\/]+)\//i);
        if (match && match[1]) {
          const rootSlug = match[1].split('-c')[0];
          const canonicalRoot = normalizeRootSlug(rootSlug);
          if (canonicalRoot) {
            const dynamicMap = _getValue('DYNAMIC_CAT_MAP', {});
            dynamicMap[norm] = canonicalRoot;
            dynamicMap[slug] = canonicalRoot;
            dynamicMap[spaceSlug] = canonicalRoot;
            saveConfigKey('DYNAMIC_CAT_MAP', dynamicMap);
            return [canonicalRoot, categoryName, categoryName];
          }
        }
      }
    }

    // 2. Direct Lookup in CATEGORY_LOOKUP
    let root = CATEGORY_LOOKUP[norm] || CATEGORY_LOOKUP[slug] || CATEGORY_LOOKUP[spaceSlug] || CATEGORY_LOOKUP[umlautNorm];

    // 3. Dynamic Map Lookup
    if (!root) {
      const dynamicMap = _getValue('DYNAMIC_CAT_MAP', {});
      root = dynamicMap[norm] || dynamicMap[slug] || dynamicMap[spaceSlug] || dynamicMap[umlautNorm];
    }

    // 4. Comprehensive Regex Keyword Rules
    if (!root) {
      for (const rule of BRAND_RULES) {
        if (rule.regex.test(norm) || rule.regex.test(spaceSlug)) {
          root = rule.group;
          break;
        }
      }
    }

    // 5. Word-Prefix Fallback (e.g. "Lego Star Wars" -> "Lego Star" -> "Lego")
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

    // 6. Page-Level Breadcrumb Fallback
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

  // Helper: Resolve Top-Level Root Group for any Category
  function resolveCategoryGroup(categoryName, card = null) {
    const path = resolveCategoryPath(categoryName, card);
    return path[0] || 'Sonstiges';
  }

  // Helper: Evaluates whether a card category or path is excluded
  function isPathExcluded(catName, rootGroup, excludedCats = []) {
    if (!excludedCats || excludedCats.length === 0) return false;
    if (excludedCats.includes(`GROUP:${rootGroup}`)) return true;
    if (catName && excludedCats.includes(catName)) return true;
    if (catName && excludedCats.includes(`PATH:${rootGroup}/${catName}`)) return true;
    return false;
  }

  // Floating Glassmorphic Group Popover Controller with Branch Search & Accordion
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

  function toggleGroupPopover(anchorEl, rootGroup, subcats, getExcludedCats, updateExcludedCats) {
    if (activePopover && activePopover.dataset.rootGroup === rootGroup) {
      closeActivePopover();
      return;
    }
    closeActivePopover();

    const rect = anchorEl.getBoundingClientRect();
    const popover = document.createElement('div');
    popover.className = 'tp-group-popover';
    popover.dataset.rootGroup = rootGroup;

    const popoverWidth = 320;
    const topPos = rect.bottom + 6 + window.scrollY;
    let leftPos = rect.left + window.scrollX;
    if (rect.left + popoverWidth > window.innerWidth - 16) {
      leftPos = Math.max(16, window.innerWidth - popoverWidth - 16 + window.scrollX);
    }

    popover.style.top = `${topPos}px`;
    popover.style.left = `${leftPos}px`;

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

    // Search Filter Bar inside Popover
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
    document.body.appendChild(popover);
    activePopover = popover;
  }

  // Helper: Parse price string into float (supports Swiss .– / .- and apostrophe separators)
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
            const dynamicMap = _getValue('DYNAMIC_CAT_MAP', {});
            let updated = false;
            segments.forEach(seg => {
              const formattedSeg = formatCategorySlug(seg);
              if (formattedSeg) {
                const norm = formattedSeg.trim().toLowerCase();
                const slug = norm.replace(/[^a-z0-9]/g, '');
                const spaceSlug = norm.replace(/-/g, ' ');
                const umlautNorm = normalizeUmlautKey(norm);
                if (!dynamicMap[norm]) { dynamicMap[norm] = canonicalRoot; updated = true; }
                if (!dynamicMap[slug]) { dynamicMap[slug] = canonicalRoot; updated = true; }
                if (!dynamicMap[spaceSlug]) { dynamicMap[spaceSlug] = canonicalRoot; updated = true; }
                if (!dynamicMap[umlautNorm]) { dynamicMap[umlautNorm] = canonicalRoot; updated = true; }
              }
            });
            if (updated) saveConfigKey('DYNAMIC_CAT_MAP', dynamicMap);
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

  // Helper: Extract Offer Count
  function extractOfferCount(card) {
    const text = card.textContent || '';
    const match = text.match(/(\d+)\s*(?:Angebote|Angebot)/i);
    if (match) return parseInt(match[1], 10);
    return card.querySelectorAll('.Plugin_DealerRelProdPriceInfo').length;
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

      bar.querySelector('#tp-tb-reset').onclick = () => {
        saveConfigKey('NEGATIVE_TERMS', '');
        saveConfigKey('EXCLUDED_CATEGORIES', []);
        saveConfigKey('MIN_OFFERS', 0);
        const modalInput = document.getElementById('tp-negative-terms-input');
        if (modalInput) modalInput.value = '';
        const inlineInput = document.getElementById('tp-inline-negative-input');
        if (inlineInput) inlineInput.value = '';
        const modalMinOffersVal = document.getElementById('tp-min-offers-val');
        const modalMinOffersRange = document.getElementById('tp-min-offers-range');
        if (modalMinOffersVal) modalMinOffersVal.value = 0;
        if (modalMinOffersRange) modalMinOffersRange.value = 0;
        processListings();
      };

      bar.querySelector('#tp-tb-min-minus').onclick = () => {
        if (CONFIG.MIN_OFFERS > 0) {
          saveConfigKey('MIN_OFFERS', CONFIG.MIN_OFFERS - 1);
          const modalVal = document.getElementById('tp-min-offers-val');
          const modalRange = document.getElementById('tp-min-offers-range');
          if (modalVal) modalVal.value = CONFIG.MIN_OFFERS;
          if (modalRange) modalRange.value = CONFIG.MIN_OFFERS;
          processListings();
        }
      };

      bar.querySelector('#tp-tb-min-plus').onclick = () => {
        saveConfigKey('MIN_OFFERS', CONFIG.MIN_OFFERS + 1);
        const modalVal = document.getElementById('tp-min-offers-val');
        const modalRange = document.getElementById('tp-min-offers-range');
        if (modalVal) modalVal.value = CONFIG.MIN_OFFERS;
        if (modalRange) modalRange.value = CONFIG.MIN_OFFERS;
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
    const allCats = new Set([...pageCategories, ...excluded.filter(c => !c.startsWith('GROUP:'))]);
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
        const modalInput = document.getElementById('tp-negative-terms-input');
        if (modalInput) modalInput.value = e.target.value;
        processListings();
      };

      if (clearBtn) {
        clearBtn.onclick = () => {
          input.value = '';
          saveConfigKey('NEGATIVE_TERMS', '');
          clearBtn.style.display = 'none';
          const modalInput = document.getElementById('tp-negative-terms-input');
          if (modalInput) modalInput.value = '';
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

      bar.querySelector('#tp-bar-reset-btn').onclick = () => {
        saveConfigKey('NEGATIVE_TERMS', '');
        saveConfigKey('EXCLUDED_CATEGORIES', []);
        saveConfigKey('MIN_OFFERS', 0);
        input.value = '';
        if (clearBtn) clearBtn.style.display = 'none';
        const modalInput = document.getElementById('tp-negative-terms-input');
        if (modalInput) modalInput.value = '';
        const modalMinOffersVal = document.getElementById('tp-min-offers-val');
        const modalMinOffersRange = document.getElementById('tp-min-offers-range');
        if (modalMinOffersVal) modalMinOffersVal.value = 0;
        if (modalMinOffersRange) modalMinOffersRange.value = 0;
        processListings();
      };
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

  function processListings() {
    if (isModifyingDOM) return;
    isModifyingDOM = true;
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

      cards.forEach(card => {
        // 1. Category extraction (DOM text + URL path slug parser + active breadcrumbs)
        const catName = extractCardCategory(card);
        if (catName) pageCategories.add(catName);

        // 2. Negative Text Filter (Strictly checks full card text content)
        const isNeg = matchesNegativeTerms(card, termsList);
        card.classList.toggle('tp-negative-filtered', isNeg);
        if (isNeg) counts.neg++;

        // 3. Category Filter
        const rootGroup = resolveCategoryGroup(catName, card);
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
      });

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
            if (closeButton) closeButton.click();
          } else if (polls >= 15) {
            clearInterval(autoCloseInterval);
          }
        }, 200);
      }
    }
  }

  // ─── MODULE 3: UNIFIED GLASSMORPHIC SETTINGS UI ─────────────────────────────
  function ensureSkeleton() {
    let fabButton = document.getElementById('tp-settings-fab');
    if (!fabButton) {
      const fabContainer = document.createElement('div');
      fabContainer.innerHTML = `
        <button id="tp-settings-fab" title="Toppreise Suite Einstellungen öffnen">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      `;
      fabButton = fabContainer.firstElementChild;
      document.body.appendChild(fabButton);
    }

    let backdrop = document.getElementById('tp-settings-modal-backdrop');
    if (!backdrop) {
      const modalContainer = document.createElement('div');
      modalContainer.innerHTML = `
        <div id="tp-settings-modal-backdrop">
          <div id="tp-settings-modal">
            <h3>Toppreise Suite Einstellungen</h3>
            <div id="tp-settings-sections" style="display: flex; flex-direction: column; gap: 8px; max-height: 72vh; overflow-y: auto; padding-right: 4px;">
              <!-- Dynamic settings sections -->
            </div>
            <div class="tp-modal-actions">
              <button type="button" class="tp-btn tp-btn-secondary" id="tp-btn-close" title="Einstellungen abbrechen ohne Speichern">Abbrechen</button>
              <button type="button" class="tp-btn tp-btn-primary" id="tp-btn-save" title="Einstellungen dauerhaft speichern">Speichern</button>
            </div>
          </div>
        </div>
      `;
      backdrop = modalContainer.firstElementChild;
      document.body.appendChild(backdrop);

      const btnClose = document.getElementById('tp-btn-close');
      const closeModal = () => backdrop.classList.remove('open');
      btnClose.addEventListener('click', closeModal);
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeModal();
      });

      fabButton.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('tp-settings-open'));
        backdrop.classList.add('open');
      });

      const btnSave = document.getElementById('tp-btn-save');
      btnSave.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('tp-settings-save'));
        closeModal();
      });
    }

    return { fabButton, backdrop };
  }

  function setupUI() {
    ensureSkeleton();

    let section = document.getElementById('tp-section-unified-suite');
    if (!section) {
      const sectionsHolder = document.getElementById('tp-settings-sections');
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

    // Form Field References
    const modeHighlight = document.getElementById('tp-mode-highlight-only');
    const modeDim = document.getElementById('tp-mode-dim');
    const modeHide = document.getElementById('tp-mode-hide');
    const marginRange = document.getElementById('tp-margin-range');
    const marginVal = document.getElementById('tp-margin-val');
    const opacityRange = document.getElementById('tp-opacity-range');
    const opacityVal = document.getElementById('tp-opacity-val');
    const shippingToggle = document.getElementById('tp-shipping-toggle');

    const negTermsInput = document.getElementById('tp-negative-terms-input');
    const catPillsContainer = document.getElementById('tp-category-pills');

    const minOffersRange = document.getElementById('tp-min-offers-range');
    const minOffersVal = document.getElementById('tp-min-offers-val');

    const sortNone = document.getElementById('tp-sort-none');
    const sortDesc = document.getElementById('tp-sort-desc');
    const sortAsc = document.getElementById('tp-sort-asc');

    const counterToggle = document.getElementById('tp-counter-toggle');

    const alarmEnabledToggle = document.getElementById('tp-alarm-enabled-toggle');
    const alarmTargetRange = document.getElementById('tp-alarm-target-range');
    const alarmTargetVal = document.getElementById('tp-alarm-target-val');
    const alarmAutoSubmitToggle = document.getElementById('tp-alarm-autosubmit-toggle');

    const dur90 = document.getElementById('tp-dur-90');
    const dur180 = document.getElementById('tp-dur-180');
    const dur365 = document.getElementById('tp-dur-365');
    const dur730 = document.getElementById('tp-dur-730');

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
          toggleGroupPopover(
            groupPill,
            rootGroup,
            subcats,
            () => currentExcludedCats,
            (updated) => {
              currentExcludedCats = updated;
              renderCategoryPills();
            }
          );
        };
      });

      existingGroupWrappers.forEach(obsoleteWrapper => obsoleteWrapper.remove());
    }

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
      const opacityGroup = document.getElementById('tp-dim-opacity-group');
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
        const selectedMode = document.querySelector('input[name="tp-mode"]:checked').value;
        updateOpacityState(selectedMode);
      });
    });

    document.addEventListener('tp-settings-open', () => {
      syncFieldsFromConfig();
    });

    document.addEventListener('tp-settings-save', () => {
      const checkedModeEl = document.querySelector('input[name="tp-mode"]:checked');
      if (!checkedModeEl) return;

      saveConfigKey('MODE', checkedModeEl.value);
      saveConfigKey('MARGIN_PERCENT', Math.max(0, Math.min(100, parseFloat(marginVal.value) || 0)));
      saveConfigKey('DIM_OPACITY', Math.max(0.05, Math.min(0.95, parseFloat(opacityRange.value) || 0.25)));
      saveConfigKey('USE_SHIPPING_PRICE', shippingToggle.checked);

      saveConfigKey('NEGATIVE_TERMS', negTermsInput.value.trim());
      saveConfigKey('EXCLUDED_CATEGORIES', currentExcludedCats);
      saveConfigKey('MIN_OFFERS', Math.max(0, parseInt(minOffersVal.value) || 0));

      const checkedSort = document.querySelector('input[name="tp-sort-offers"]:checked');
      if (checkedSort) saveConfigKey('SORT_BY_OFFERS', checkedSort.value);

      saveConfigKey('ENABLE_FILTER_COUNTER', counterToggle.checked);

      saveConfigKey('ALARM_ENABLED', alarmEnabledToggle.checked);
      saveConfigKey('ALARM_TARGET_PERCENT', Math.max(0.05, Math.min(0.99, (parseInt(alarmTargetVal.value) || 60) / 100)));

      const checkedDur = document.querySelector('input[name="tp-alarm-duration"]:checked');
      if (checkedDur) saveConfigKey('ALARM_DURATION_DAYS', checkedDur.value);

      saveConfigKey('ALARM_AUTO_SUBMIT', alarmAutoSubmitToggle.checked);

      updateBodyClasses();
      processListings();
    });
  }

  // ─── OBSERVER & INITIALIZATION ───────────────────────────────────────────────
  let debounceTimer = null;
  let isModifyingDOM = false;

  const observer = new MutationObserver(() => {
    if (isModifyingDOM) return;
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

  // Initialize UI controls, filters, and alarm listener
  setupUI();
  processListings();
  processPriceAlarmModal();

})();
