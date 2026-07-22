// ==UserScript==
// @name         Toppreise.ch Suite: Power Filter & Price Alarm Auto-Filler
// @namespace    https://github.com/tazztone/scripts
// @version      0.5.0
// @description  All-in-one suite for Toppreise.ch: Highlights best prices, excludes negative keywords, filters categories, sorts/filters by offer count, enforces delivery stock availability, and automates price alarm creation.
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
  STOCK_FILTER: 'all',
  ENABLE_FILTER_COUNTER: true,
  
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
  .tp-min-offers-filtered,
  .tp-stock-filtered {
    display: none !important;
  }

  /* Temporary reveal mode for filtered elements */
  body.tp-reveal-filtered .tp-negative-filtered,
  body.tp-reveal-filtered .tp-category-filtered,
  body.tp-reveal-filtered .tp-min-offers-filtered,
  body.tp-reveal-filtered .tp-stock-filtered {
    display: block !important;
    opacity: 0.35 !important;
    outline: 2px dashed #f59e0b !important;
  }

  /* Floating Settings Button */
  #tp-settings-fab {
    position: fixed;
    bottom: 12px;
    right: 12px;
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
  .tp-cat-pill {
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    user-select: none;
    transition: all 0.2s ease;
    background: rgba(255, 255, 255, 0.08);
    color: #cbd5e1;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .tp-cat-pill:hover {
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
  }
  .tp-cat-pill.tp-excluded {
    background: rgba(239, 68, 68, 0.25);
    color: #fca5a5;
    border-color: rgba(239, 68, 68, 0.4);
    text-decoration: line-through;
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

  /* Filter Summary Counter Bar */
  #tp-filter-summary-bar {
    position: fixed;
    bottom: 14px;
    left: 14px;
    background: rgba(30, 41, 59, 0.88);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: 600;
    color: #f8fafc;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    z-index: 99990;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    transition: all 0.3s ease;
  }
  .tp-summary-chip {
    background: rgba(255, 255, 255, 0.1);
    padding: 2px 7px;
    border-radius: 10px;
    font-size: 10px;
    color: #cbd5e1;
  }
  .tp-summary-toggle-btn {
    background: rgba(16, 185, 129, 0.2);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34d399;
    padding: 2px 8px;
    border-radius: 10px;
    cursor: pointer;
    font-size: 10px;
    font-weight: 700;
    transition: all 0.2s ease;
  }
  .tp-summary-toggle-btn:hover {
    background: rgba(16, 185, 129, 0.4);
  }
`;

// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  // Persistent GM storage helpers with localStorage fallback
  const _getValue = (key, def) => {
    try {
      if (typeof GM_getValue !== 'undefined') return GM_getValue(key, def);
    } catch (e) {}
    try {
      const local = localStorage.getItem(`tp_suite_${key}`);
      return local !== null ? JSON.parse(local) : def;
    } catch (e) {}
    return def;
  };

  const _setValue = (key, val) => {
    try {
      if (typeof GM_setValue !== 'undefined') {
        GM_setValue(key, val);
        return;
      }
    } catch (e) {}
    try {
      localStorage.setItem(`tp_suite_${key}`, JSON.stringify(val));
    } catch (e) {}
  };

  // Dynamic config bindings using getters and setters
  const CONFIG = {
    get MODE() { return _getValue('MODE', DEFAULTS.MODE); },
    set MODE(v) { _setValue('MODE', v); },
    
    get MARGIN_PERCENT() { return parseFloat(_getValue('MARGIN_PERCENT', DEFAULTS.MARGIN_PERCENT)); },
    set MARGIN_PERCENT(v) { _setValue('MARGIN_PERCENT', parseFloat(v)); },
    
    get DIM_OPACITY() { return parseFloat(_getValue('DIM_OPACITY', DEFAULTS.DIM_OPACITY)); },
    set DIM_OPACITY(v) { _setValue('DIM_OPACITY', parseFloat(v)); },
    
    get USE_SHIPPING_PRICE() { return _getValue('USE_SHIPPING_PRICE', DEFAULTS.USE_SHIPPING_PRICE); },
    set USE_SHIPPING_PRICE(v) { _setValue('USE_SHIPPING_PRICE', v); },

    get NEGATIVE_TERMS() { return _getValue('NEGATIVE_TERMS', DEFAULTS.NEGATIVE_TERMS); },
    set NEGATIVE_TERMS(v) { _setValue('NEGATIVE_TERMS', v); },

    get EXCLUDED_CATEGORIES() { return _getValue('EXCLUDED_CATEGORIES', DEFAULTS.EXCLUDED_CATEGORIES); },
    set EXCLUDED_CATEGORIES(v) { _setValue('EXCLUDED_CATEGORIES', v); },

    get MIN_OFFERS() { return parseInt(_getValue('MIN_OFFERS', DEFAULTS.MIN_OFFERS)); },
    set MIN_OFFERS(v) { _setValue('MIN_OFFERS', parseInt(v)); },

    get SORT_BY_OFFERS() { return _getValue('SORT_BY_OFFERS', DEFAULTS.SORT_BY_OFFERS); },
    set SORT_BY_OFFERS(v) { _setValue('SORT_BY_OFFERS', v); },

    get STOCK_FILTER() { return _getValue('STOCK_FILTER', DEFAULTS.STOCK_FILTER); },
    set STOCK_FILTER(v) { _setValue('STOCK_FILTER', v); },

    get ENABLE_FILTER_COUNTER() { return _getValue('ENABLE_FILTER_COUNTER', DEFAULTS.ENABLE_FILTER_COUNTER); },
    set ENABLE_FILTER_COUNTER(v) { _setValue('ENABLE_FILTER_COUNTER', v); },

    // Price Alarm Config
    get ALARM_ENABLED() { return _getValue('ALARM_ENABLED', DEFAULTS.ALARM_ENABLED); },
    set ALARM_ENABLED(v) { _setValue('ALARM_ENABLED', v); },

    get ALARM_TARGET_PERCENT() { return parseFloat(_getValue('ALARM_TARGET_PERCENT', DEFAULTS.ALARM_TARGET_PERCENT)); },
    set ALARM_TARGET_PERCENT(v) { _setValue('ALARM_TARGET_PERCENT', parseFloat(v)); },

    get ALARM_DURATION_DAYS() { return String(_getValue('ALARM_DURATION_DAYS', DEFAULTS.ALARM_DURATION_DAYS)); },
    set ALARM_DURATION_DAYS(v) { _setValue('ALARM_DURATION_DAYS', String(v)); },

    get ALARM_AUTO_SUBMIT() { return _getValue('ALARM_AUTO_SUBMIT', DEFAULTS.ALARM_AUTO_SUBMIT); },
    set ALARM_AUTO_SUBMIT(v) { _setValue('ALARM_AUTO_SUBMIT', v); },

    // System
    get OBSERVER_DEBOUNCE_MS() { return parseInt(_getValue('OBSERVER_DEBOUNCE_MS', DEFAULTS.OBSERVER_DEBOUNCE_MS)); },
    set OBSERVER_DEBOUNCE_MS(v) { _setValue('OBSERVER_DEBOUNCE_MS', parseInt(v)); },
    
    get DEBUG() { return _getValue('DEBUG', DEFAULTS.DEBUG); },
    set DEBUG(v) { _setValue('DEBUG', v); }
  };

  const log = (...args) => { if (CONFIG.DEBUG) console.log('[Toppreise-Suite]', ...args); };

  // Set of categories detected on page
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

  // Helper: Parse price string into float
  function parsePrice(priceStr) {
    if (!priceStr) return 0;
    const clean = priceStr.replace(/[^\d,.]/g, '').replace("'", "").replace(',', '.');
    const val = parseFloat(clean);
    return isNaN(val) ? 0 : val;
  }

  // Helper: Extract Card Category
  function extractCardCategory(card) {
    const catEl = card.querySelector('a[href*="/katalog/"], .categoryLink, .breadcrumb a, .category');
    if (catEl) return catEl.textContent.trim();
    return '';
  }

  // Helper: Extract Offer Count
  function extractOfferCount(card) {
    const text = card.textContent || '';
    const match = text.match(/(\d+)\s*(?:Angebote|Angebot)/i);
    if (match) return parseInt(match[1], 10);
    return card.querySelectorAll('.Plugin_DealerRelProdPriceInfo').length;
  }

  // Helper: Check Card Stock Status
  function checkCardStock(card) {
    const availabilityEls = card.querySelectorAll('.availability, .stock, .delivery, .stockStatus, [title*="lager"], [title*="lieferbar"], [title*="Lieferzeit"]');
    let hasImmediate = false;
    let hasKnown = false;

    if (availabilityEls.length === 0) {
      const dealerRows = card.querySelectorAll('.Plugin_DealerRelProdPriceInfo');
      dealerRows.forEach(row => {
        const rowText = row.textContent.toLowerCase();
        if (rowText.includes('sofort') || rowText.includes('ab lager') || rowText.includes('1-2') || rowText.includes('auf lager')) {
          hasImmediate = true;
          hasKnown = true;
        } else if (rowText.includes('tage') || rowText.includes('werktage') || rowText.includes('lieferant')) {
          hasKnown = true;
        }
      });
      if (!hasImmediate && !hasKnown && dealerRows.length > 0) {
        hasKnown = true;
        hasImmediate = true;
      }
      return { hasImmediate, hasKnown };
    }

    availabilityEls.forEach(el => {
      const text = (el.textContent + ' ' + (el.getAttribute('title') || '') + ' ' + (el.className || '')).toLowerCase();
      if (text.includes('sofort') || text.includes('ab lager') || text.includes('1-2') || text.includes('green') || text.includes('auf lager')) {
        hasImmediate = true;
        hasKnown = true;
      } else if (text.includes('tage') || text.includes('werktage') || text.includes('yellow') || text.includes('lieferant')) {
        hasKnown = true;
      }
    });

    return { hasImmediate, hasKnown };
  }

  // Helper: Check Negative Term Match
  function matchesNegativeTerms(card, termsList) {
    if (!termsList || termsList.length === 0) return false;
    const title = (card.querySelector('.titleLink, .title')?.textContent || '').toLowerCase();
    const specs = (card.querySelector('.specs, .description')?.textContent || '').toLowerCase();
    const fullText = title + ' ' + specs;
    return termsList.some(term => term.length > 0 && fullText.includes(term));
  }

  // Update Summary Bar
  function updateSummaryBar(counts) {
    if (!CONFIG.ENABLE_FILTER_COUNTER) {
      const bar = document.getElementById('tp-filter-summary-bar');
      if (bar) bar.style.display = 'none';
      return;
    }

    let bar = document.getElementById('tp-filter-summary-bar');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'tp-filter-summary-bar';
      document.body.appendChild(bar);
    }

    const totalHidden = counts.neg + counts.cat + counts.min + counts.stock;

    if (totalHidden === 0) {
      bar.style.display = 'none';
      return;
    }

    bar.style.display = 'flex';
    const isRevealed = document.body.classList.contains('tp-reveal-filtered');

    bar.innerHTML = `
      <span>🚫 <strong>${totalHidden}</strong> ausgeblendet</span>
      ${counts.neg > 0 ? `<span class="tp-summary-chip">${counts.neg} Text</span>` : ''}
      ${counts.cat > 0 ? `<span class="tp-summary-chip">${counts.cat} Kat.</span>` : ''}
      ${counts.min > 0 ? `<span class="tp-summary-chip">${counts.min} Angebote</span>` : ''}
      ${counts.stock > 0 ? `<span class="tp-summary-chip">${counts.stock} Lieferzeit</span>` : ''}
      <button class="tp-summary-toggle-btn" id="tp-btn-toggle-reveal">
        ${isRevealed ? 'Verbergen' : 'Einblenden'}
      </button>
    `;

    const toggleBtn = bar.querySelector('#tp-btn-toggle-reveal');
    if (toggleBtn) {
      toggleBtn.onclick = () => {
        document.body.classList.toggle('tp-reveal-filtered');
        updateSummaryBar(counts);
      };
    }
  }

  // ─── MODULE 1: PRODUCT LISTING PROCESSOR ─────────────────────────────────────
  function processListings() {
    log('Processing product listings...');

    const cards = document.querySelectorAll('.Plugin_Product.mixedBrowsingList, .Plugin_Product');
    if (cards.length === 0) return;

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
    const counts = { neg: 0, cat: 0, min: 0, stock: 0 };

    cards.forEach(card => {
      // 1. Category extraction
      const catName = extractCardCategory(card);
      if (catName) pageCategories.add(catName);

      // 2. Negative Text Filter
      const isNeg = matchesNegativeTerms(card, termsList);
      card.classList.toggle('tp-negative-filtered', isNeg);
      if (isNeg) counts.neg++;

      // 3. Category Filter
      const isCatExcluded = catName && excludedCats.includes(catName);
      card.classList.toggle('tp-category-filtered', isCatExcluded);
      if (isCatExcluded) counts.cat++;

      // 4. Offer Count Filter
      const offerCount = extractOfferCount(card);
      const isLowOffers = CONFIG.MIN_OFFERS > 0 && offerCount < CONFIG.MIN_OFFERS;
      card.classList.toggle('tp-min-offers-filtered', isLowOffers);
      if (isLowOffers) counts.min++;

      // 5. Stock Filter
      const { hasImmediate, hasKnown } = checkCardStock(card);
      let isStockFiltered = false;
      if (CONFIG.STOCK_FILTER === 'immediate-only' && !hasImmediate) isStockFiltered = true;
      else if (CONFIG.STOCK_FILTER === 'in-stock' && !hasKnown) isStockFiltered = true;
      card.classList.toggle('tp-stock-filtered', isStockFiltered);
      if (isStockFiltered) counts.stock++;

      // 6. Best Price Highlighting / Dimming
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

    // 7. Re-sorting by Offer Count
    if (CONFIG.SORT_BY_OFFERS !== 'none' && cards.length > 1) {
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

    // 8. Update Summary Bar
    updateSummaryBar(counts);
  }

  // ─── MODULE 2: PRICE ALARM AUTOMATION ────────────────────────────────────────
  function processPriceAlarmModal() {
    if (!CONFIG.ALARM_ENABLED) return;

    const modalContainer = document.querySelector('.Plugin_NewInfoMailForm');
    if (!modalContainer || modalContainer.dataset.tpAlarmProcessed === 'true') return;

    modalContainer.dataset.tpAlarmProcessed = 'true';
    log('Price Alarm modal detected! Automating configuration...');

    // 1. Locate Dialog & Close Button references before submission
    const dialogContainer = modalContainer.closest('.AbstractDialog');
    const closeButton = dialogContainer ? dialogContainer.querySelector('.AbstractDialog_CloseButton') : null;

    // 2. Extract present price
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

    // 3. Set Target Price Input
    const priceInput = modalContainer.querySelector('input#f_NewInfoMailForm_priceFrom') ||
                       modalContainer.querySelector('input[name="im_nimf_pvf"]');
    if (priceInput) {
      priceInput.value = targetPrice;
      priceInput.dispatchEvent(new Event('input', { bubbles: true }));
      priceInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // 4. Set Duration (2 years / 730 days)
    const durationHidden = modalContainer.querySelector('input[name="im_nimf_du"]');
    if (durationHidden) {
      durationHidden.value = CONFIG.ALARM_DURATION_DAYS;
      durationHidden.dispatchEvent(new Event('change', { bubbles: true }));
    }
    const durationOption = modalContainer.querySelector(`li[data-value="${CONFIG.ALARM_DURATION_DAYS}"]`);
    if (durationOption) durationOption.click();

    // 5. Check GDPR Terms checkbox
    const termsCheckbox = modalContainer.querySelector('input#im_nimf_prtrm');
    if (termsCheckbox) {
      termsCheckbox.checked = true;
      termsCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // 6. Submit & Auto-Close
    if (CONFIG.ALARM_AUTO_SUBMIT) {
      const submitBtn = modalContainer.querySelector('input.f_submitbtn');
      if (submitBtn) {
        log('Auto-submitting price alarm...');
        submitBtn.click();

        // Polling loop to close dialog once form is detached
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
        <button id="tp-settings-fab" title="Configure Toppreise Suite">
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
            <h3>Toppreise Suite Settings</h3>
            <div id="tp-settings-sections" style="display: flex; flex-direction: column; gap: 8px; max-height: 72vh; overflow-y: auto; padding-right: 4px;">
              <!-- Dynamic settings sections -->
            </div>
            <div class="tp-modal-actions">
              <button type="button" class="tp-btn tp-btn-secondary" id="tp-btn-close">Abbrechen</button>
              <button type="button" class="tp-btn tp-btn-primary" id="tp-btn-save">Speichern</button>
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
            <label>Transparenz Nicht-Günstigste</label>
            <div class="tp-range-container">
              <input type="range" id="tp-opacity-range" min="0.05" max="0.95" step="0.05" value="0.25">
              <input type="number" id="tp-opacity-val" min="5" max="95" step="5" value="25">
            </div>
          </div>

          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>inkl. Versandkosten vergleichen</label>
            </div>
            <label class="tp-switch">
              <input type="checkbox" id="tp-shipping-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>

          <!-- Section 2: Negativer Textfilter -->
          <div class="tp-section-header">2. Negativer Textfilter (Ausschluss)</div>
          <div class="tp-settings-group">
            <label>Auszuschließende Begriffe (Kommagetrennt)</label>
            <textarea id="tp-negative-terms-input" class="tp-textarea" placeholder="z. B. Hülle, Case, Refurbished, Gebraucht"></textarea>
          </div>

          <!-- Section 3: Kategorien Filter -->
          <div class="tp-section-header">3. Kategorien-Filter (Neue Toppreise)</div>
          <div class="tp-settings-group">
            <label>Erkannte Kategorien (Klicken zum Ausblenden):</label>
            <div id="tp-category-pills" class="tp-cat-pills-container">
              <!-- Rendered dynamically -->
            </div>
          </div>

          <!-- Section 4: Angebote & Sortierung -->
          <div class="tp-section-header">4. Angebote & Sortierung</div>
          <div class="tp-settings-group">
            <label>Mindestanzahl Angebote (0 = Aus)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-min-offers-range" min="0" max="15" step="1" value="0">
              <input type="number" id="tp-min-offers-val" min="0" max="50" step="1" value="0">
            </div>
          </div>

          <div class="tp-settings-group">
            <label>Sortierung nach Anzahl Angebote</label>
            <div class="tp-segmented-control">
              <input type="radio" id="tp-sort-none" name="tp-sort-offers" value="none">
              <label for="tp-sort-none">Standard</label>
              
              <input type="radio" id="tp-sort-desc" name="tp-sort-offers" value="desc">
              <label for="tp-sort-desc">Meiste ⬇</label>
              
              <input type="radio" id="tp-sort-asc" name="tp-sort-offers" value="asc">
              <label for="tp-sort-asc">Wenigste ⬆</label>
            </div>
          </div>

          <!-- Section 5: Lieferbarkeit & Statusleiste -->
          <div class="tp-section-header">5. Lieferbarkeit & Statusleiste</div>
          <div class="tp-settings-group">
            <label>Verfügbarkeits-Filter</label>
            <div class="tp-segmented-control">
              <input type="radio" id="tp-stock-all" name="tp-stock" value="all">
              <label for="tp-stock-all">Alle</label>
              
              <input type="radio" id="tp-stock-instock" name="tp-stock" value="in-stock">
              <label for="tp-stock-instock">Lieferbar</label>
              
              <input type="radio" id="tp-stock-immediate" name="tp-stock" value="immediate-only">
              <label for="tp-stock-immediate">Sofort ab Lager</label>
            </div>
          </div>

          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>Filter-Zähler Statusleiste anzeigen</label>
            </div>
            <label class="tp-switch">
              <input type="checkbox" id="tp-counter-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>

          <!-- Section 6: Preisalarm Auto-Filler -->
          <div class="tp-section-header" style="color: #3b82f6;">6. Preisalarm Auto-Filler</div>
          
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
              <label>Automatisch Absenden & Schließen</label>
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

    const stockAll = document.getElementById('tp-stock-all');
    const stockInStock = document.getElementById('tp-stock-instock');
    const stockImmediate = document.getElementById('tp-stock-immediate');

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

      const stock = CONFIG.STOCK_FILTER;
      if (stock === 'immediate-only') stockImmediate.checked = true;
      else if (stock === 'in-stock') stockInStock.checked = true;
      else stockAll.checked = true;

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

      CONFIG.MODE = checkedModeEl.value;
      CONFIG.MARGIN_PERCENT = Math.max(0, Math.min(100, parseFloat(marginVal.value) || 0));
      CONFIG.DIM_OPACITY = Math.max(0.05, Math.min(0.95, parseFloat(opacityRange.value) || 0.25));
      CONFIG.USE_SHIPPING_PRICE = shippingToggle.checked;

      CONFIG.NEGATIVE_TERMS = negTermsInput.value.trim();
      CONFIG.EXCLUDED_CATEGORIES = currentExcludedCats;
      CONFIG.MIN_OFFERS = Math.max(0, parseInt(minOffersVal.value) || 0);

      const checkedSort = document.querySelector('input[name="tp-sort-offers"]:checked');
      if (checkedSort) CONFIG.SORT_BY_OFFERS = checkedSort.value;

      const checkedStock = document.querySelector('input[name="tp-stock"]:checked');
      if (checkedStock) CONFIG.STOCK_FILTER = checkedStock.value;

      CONFIG.ENABLE_FILTER_COUNTER = counterToggle.checked;

      CONFIG.ALARM_ENABLED = alarmEnabledToggle.checked;
      CONFIG.ALARM_TARGET_PERCENT = Math.max(0.05, Math.min(0.99, (parseInt(alarmTargetVal.value) || 60) / 100));
      
      const checkedDur = document.querySelector('input[name="tp-alarm-duration"]:checked');
      if (checkedDur) CONFIG.ALARM_DURATION_DAYS = checkedDur.value;

      CONFIG.ALARM_AUTO_SUBMIT = alarmAutoSubmitToggle.checked;

      updateBodyClasses();
      processListings();
    });
  }

  // ─── OBSERVER & INITIALIZATION ───────────────────────────────────────────────
  let debounceTimer = null;
  const observer = new MutationObserver(() => {
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

  // Periodic safety check
  setInterval(() => {
    processListings();
    processPriceAlarmModal();
  }, 5000);

})();
