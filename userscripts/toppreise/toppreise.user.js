// ==UserScript==
// @name         Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler
// @namespace    https://github.com/tazztone/scripts
// @version      2.4.0
// @description  All-in-one suite for Toppreise.ch: Highlights best prices, excludes negative keywords, filters categories, sorts/filters by offer count, and automates price alarm creation.
// @author       tazztone
// @match        https://www.toppreise.ch/*
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
  .tp-group-pill.tp-excluded {
    background: #7f1d1d !important;
    color: #fca5a5 !important;
    border-color: #ef4444 !important;
    text-decoration: line-through !important;
  }
  .tp-group-pill.tp-partial {
    border-color: #f59e0b !important;
    color: #fef08a !important;
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
  .tp-group-children {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding-left: 10px;
    margin-top: 2px;
    border-left: 2px solid rgba(2, 132, 199, 0.3);
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
    gap: 10px !important;
    width: 100% !important;
  }

  .tp-filter-badge {
    font-size: 13px !important;
    font-weight: 700 !important;
    color: #10b981 !important;
    display: flex !important;
    align-items: center !important;
    user-select: none !important;
  }

  .tp-input-wrapper {
    flex: 1 !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    min-width: 260px !important;
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
  }

  .tp-input-field-box {
    flex: 1 !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
  }

  #tp-inline-negative-input {
    width: 100% !important;
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
  }
  .tp-filter-bar-reset:hover {
    background: rgba(244, 63, 94, 0.3) !important;
    color: #fff !important;
  }

  .tp-cat-collapsible-body {
    border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
    padding-top: 8px !important;
  }

  .tp-input-wrapper {
    flex: 1 !important;
    display: flex !important;
    align-items: center !important;
    position: relative !important;
    min-width: 240px !important;
  }

  #tp-inline-negative-input {
    width: 100% !important;
    background: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #fff !important;
    padding: 7px 30px 7px 12px !important;
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

  .tp-cat-pills-row {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    align-items: center !important;
    flex: 1 !important;
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
    } catch (e) {}

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
    } catch (e) {}

    return def;
  };

  const _setValue = (key, val) => {
    try {
      if (typeof GM_setValue !== 'undefined') GM_setValue(key, val);
    } catch (e) {}

    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(LOCAL_STORAGE_PREFIX + key, JSON.stringify(val));
      }
    } catch (e) {}
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
    "krimi": "Filme",
    "anime": "Filme",
    "mehr komoedie": "Filme",
    "tv serien": "Filme",
    "fantasy": "Filme",
    "mehr drama": "Filme",
    "thriller": "Filme",
    "dvd filme": "Filme",
    "blu ray filme": "Filme",
    "dvd kinder familie": "Filme",
    "komplettsysteme": "Computer & Zubehör",
    "grafikkarten": "Computer & Zubehör",
    "tablets": "Computer & Zubehör",
    "maeuse": "Computer & Zubehör",
    "pc gehaeuse": "Computer & Zubehör",
    "notebooks": "Computer & Zubehör",
    "gehaeuseluefter": "Computer & Zubehör",
    "sd speicherkarten": "Computer & Zubehör",
    "externe festplatten hdd": "Computer & Zubehör",
    "monitore": "Computer & Zubehör",
    "lego architecture": "Spielwaren",
    "schleich": "Spielwaren",
    "action figuren": "Spielwaren",
    "kinderspiele": "Spielwaren",
    "hot wheels": "Spielwaren",
    "disney": "Spielwaren",
    "puzzles": "Spielwaren",
    "barbie": "Spielwaren",
    "cobi": "Spielwaren",
    "playmobil wiltopia": "Spielwaren",
    "tabletop spiele": "Spielwaren",
    "playmobil action": "Spielwaren",
    "playmobil novelmore": "Spielwaren",
    "lego": "Spielwaren",
    "strategie rollenspiele": "Spielwaren",
    "zubehoer fuer nintendo switch": "Videogames",
    "jump n run geschicklichkeit": "Videogames",
    "actionspiele": "Videogames",
    "rollenspiele adventures": "Videogames",
    "action": "Filme",
    "nintendo switch games": "Videogames",
    "kopfhoerer": "HiFi & Audio",
    "plattenspieler": "HiFi & Audio",
    "bluetooth lautsprecher": "HiFi & Audio",
    "tv geraete": "TV & Video",
    "beamer": "TV & Video",
    "eau de parfum": "Drogerie",
    "elektrozahnbuersten": "Drogerie",
    "hautpflege": "Drogerie",
    "lockenstaebe buersten": "Drogerie",
    "ersatzbuersten": "Drogerie",
    "saug und wischroboter": "Haushalt & Küche",
    "abfallsysteme": "Haushalt & Küche",
    "zubehoer fuer haushaltsgeraete": "Haushalt & Küche",
    "thermoskannen bidons": "Haushalt & Küche",
    "kaffee espressomaschinen": "Haushalt & Küche",
    "skihelme": "Sport & Freizeit",
    "koffer": "Sport & Freizeit",
    "ventilatoren heizgeraete": "Sport & Freizeit",
    "einkaufstrolleys taschen": "Sport & Freizeit",
    "sportbrillen goggles": "Sport & Freizeit",
    "velotaschen": "Sport & Freizeit",
    "rucksaecke": "Sport & Freizeit",
    "inline skates rollschuhe": "Sport & Freizeit",
    "huellen": "Smartphones & Mobiltelefone",
    "oberschalen cover": "Smartphones & Mobiltelefone",
    "taschen cover fuer iphone": "Smartphones & Mobiltelefone",
    "smartphones": "Smartphones & Mobiltelefone",
    "reifen": "Auto & Motorrad",
    "autos": "Auto & Motorrad",
    "uhren": "Uhren"
  };

  // Helper: Resolve Top-Level Root Group for any Category (with DOM Fallback Auto-Learning)
  function resolveCategoryGroup(categoryName, card = null) {
    if (!categoryName) return 'Sonstiges';
    const norm = categoryName.trim().toLowerCase();
    const slug = norm.replace(/[^a-z0-9]/g, '');
    const spaceSlug = norm.replace(/-/g, ' ');

    if (CATEGORY_LOOKUP[norm]) return CATEGORY_LOOKUP[norm];
    if (CATEGORY_LOOKUP[slug]) return CATEGORY_LOOKUP[slug];
    if (CATEGORY_LOOKUP[spaceSlug]) return CATEGORY_LOOKUP[spaceSlug];

    const dynamicMap = _getValue('DYNAMIC_CAT_MAP', {});
    if (dynamicMap[norm]) return dynamicMap[norm];
    if (dynamicMap[slug]) return dynamicMap[slug];

    if (card && card.querySelectorAll) {
      const links = card.querySelectorAll('a[href*="/produktsuche/"]');
      for (const a of links) {
        const href = a.getAttribute('href') || '';
        const match = href.match(/\/produktsuche\/([^\/]+)\//i);
        if (match && match[1]) {
          const rootSlug = match[1].split('-c')[0];
          const formattedRoot = formatCategorySlug(rootSlug);
          if (formattedRoot) {
            dynamicMap[norm] = formattedRoot;
            saveConfigKey('DYNAMIC_CAT_MAP', dynamicMap);
            return formattedRoot;
          }
        }
      }
    }

    return 'Sonstiges';
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

  // Dedicated Power Filter Bar Target Selector (Targets main page frame on Toppreise.ch)
  function getSuiteBarTarget() {
    return document.getElementById('FrameContent') ||
           document.querySelector('#tpContent .pageContent') ||
           document.querySelector('main') ||
           document.querySelector('#content') ||
           document.body;
  }

  // Unified Glassmorphic Power Filter Bar prepended to top of page content (Single-row collapsed by default)
  function renderSuiteFilterBar() {
    const target = getSuiteBarTarget();
    if (!target) return;

    let bar = document.getElementById('tp-suite-filter-bar');
    const excluded = CONFIG.EXCLUDED_CATEGORIES || [];
    const allCats = new Set([...pageCategories, ...excluded]);
    const isExpanded = CONFIG.CATS_EXPANDED === true;

    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'tp-suite-filter-bar';
      bar.innerHTML = `
        <div class="tp-filter-main-row">
          <span class="tp-filter-badge" title="Toppreise Power Filter">⚡</span>
          
          <div class="tp-input-wrapper" title="Kommagetrennte Begriffe eingeben (z.B. Hülle, Refurbished, Gebraucht), um passende Produkte auszublenden">
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

      target.insertBefore(bar, target.firstChild);

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
      // Re-anchor to top of target if detached or moved
      if (bar.parentElement !== target || bar !== target.firstChild) {
        target.insertBefore(bar, target.firstChild);
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

    // Reconcile category pills & Group Pills
    const pillsHolder = bar.querySelector('#tp-inline-category-pills');
    if (pillsHolder && isExpanded) {
      if (allCats.size === 0) {
        pillsHolder.innerHTML = '<span style="font-size:11px; color:#64748b;">(Keine Kategorien auf aktueller Ansicht)</span>';
      } else {
        pillsHolder.innerHTML = '';
        
        // Group detected pageCategories by Root Category Group
        const groups = new Map();
        allCats.forEach(cat => {
          const root = resolveCategoryGroup(cat);
          if (!groups.has(root)) groups.set(root, []);
          groups.get(root).push(cat);
        });

        if (!window._tpExpandedGroups) window._tpExpandedGroups = new Set();

        groups.forEach((subcats, rootGroup) => {
          const allSubcatsExcluded = subcats.every(sc => excluded.includes(sc) || excluded.includes(`GROUP:${rootGroup}`));
          const someSubcatsExcluded = subcats.some(sc => excluded.includes(sc) || excluded.includes(`GROUP:${rootGroup}`));
          const isGroupExpanded = window._tpExpandedGroups.has(rootGroup);

          const groupWrapper = document.createElement('div');
          groupWrapper.className = 'tp-group-wrapper';

          const groupPill = document.createElement('div');
          groupPill.className = `tp-group-pill ${allSubcatsExcluded ? 'tp-excluded' : someSubcatsExcluded ? 'tp-partial' : ''}`;

          const titleSpan = document.createElement('span');
          titleSpan.textContent = `📁 ${rootGroup} (${subcats.length})`;
          titleSpan.title = allSubcatsExcluded ? `Gruppe "${rootGroup}" wieder einblenden` : `Alle Kategorien unter "${rootGroup}" ausblenden`;
          titleSpan.onclick = () => {
            const currentExcluded = CONFIG.EXCLUDED_CATEGORIES || [];
            let updated;
            if (allSubcatsExcluded) {
              updated = currentExcluded.filter(c => !subcats.includes(c) && c !== `GROUP:${rootGroup}`);
            } else {
              const toAdd = subcats.filter(sc => !currentExcluded.includes(sc));
              updated = [...currentExcluded, ...toAdd];
            }
            saveConfigKey('EXCLUDED_CATEGORIES', updated);
            processListings();
          };

          const chevronBtn = document.createElement('span');
          chevronBtn.className = 'tp-group-chevron';
          chevronBtn.textContent = isGroupExpanded ? '▲' : '▼';
          chevronBtn.title = isGroupExpanded ? 'Unterkategorien einklappen' : 'Unterkategorien ausklappen';
          chevronBtn.onclick = (e) => {
            e.stopPropagation();
            if (window._tpExpandedGroups.has(rootGroup)) {
              window._tpExpandedGroups.delete(rootGroup);
            } else {
              window._tpExpandedGroups.add(rootGroup);
            }
            renderSuiteFilterBar();
          };

          groupPill.appendChild(titleSpan);
          groupPill.appendChild(chevronBtn);
          groupWrapper.appendChild(groupPill);

          if (isGroupExpanded) {
            const childContainer = document.createElement('div');
            childContainer.className = 'tp-group-children';

            subcats.forEach(cat => {
              const isCatExcluded = excluded.includes(cat) || excluded.includes(`GROUP:${rootGroup}`);
              const childPill = document.createElement('div');
              childPill.className = `tp-cat-pill ${isCatExcluded ? 'tp-excluded' : ''}`;
              childPill.textContent = cat;
              childPill.title = isCatExcluded ? `Kategorie "${cat}" wieder einblenden` : `Kategorie "${cat}" ausblenden`;
              childPill.onclick = () => {
                const currentExcluded = CONFIG.EXCLUDED_CATEGORIES || [];
                let updated;
                if (currentExcluded.includes(cat)) {
                  updated = currentExcluded.filter(c => c !== cat && c !== `GROUP:${rootGroup}`);
                } else {
                  updated = [...currentExcluded, cat];
                }
                saveConfigKey('EXCLUDED_CATEGORIES', updated);
                processListings();
              };
              childContainer.appendChild(childPill);
            });

            groupWrapper.appendChild(childContainer);
          }

          pillsHolder.appendChild(groupWrapper);
        });
      }
    }
  }

  // ─── MODULE 1: PRODUCT LISTING PROCESSOR ─────────────────────────────────────
  function processListings() {
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
      const isCatExcluded = catName && (excludedCats.includes(catName) || excludedCats.includes(`GROUP:${rootGroup}`));
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
      catPillsContainer.innerHTML = '';
      const allCats = new Set([...pageCategories, ...currentExcludedCats]);

      if (allCats.size === 0) {
        catPillsContainer.innerHTML = '<span style="font-size:11px; color:#64748b; padding:4px;">Keine Kategorien auf Seite erkannt</span>';
        return;
      }

      allCats.forEach(cat => {
        const isExcluded = currentExcludedCats.includes(cat);
        const pill = document.createElement('div');
        pill.className = `tp-cat-pill ${isExcluded ? 'tp-excluded' : ''}`;
        pill.title = isExcluded ? `Kategorie "${cat}" wieder einblenden` : `Kategorie "${cat}" dauerhaft ausblenden`;
        pill.textContent = cat;
        pill.onclick = () => {
          if (isExcluded) {
            currentExcludedCats = currentExcludedCats.filter(c => c !== cat);
          } else {
            currentExcludedCats.push(cat);
          }
          renderCategoryPills();
        };
        catPillsContainer.appendChild(pill);
      });
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

  function safeProcessListings() {
    if (isModifyingDOM) return;
    isModifyingDOM = true;
    try {
      processListings();
    } finally {
      isModifyingDOM = false;
    }
  }

  const observer = new MutationObserver(() => {
    if (isModifyingDOM) return;
    try {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        safeProcessListings();
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
  safeProcessListings();
  processPriceAlarmModal();

})();
