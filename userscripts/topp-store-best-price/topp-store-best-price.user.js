// ==UserScript==
// @name         Toppreise.ch Store Best Price Highlighter & Filter
// @namespace    https://github.com/tazztone/scripts
// @version      0.2.0
// @description  Highlights, dims, or hides products on Toppreise.ch based on whether a filtered store offers the best price.
// @author       tazztone
// @match        https://www.toppreise.ch/*
// @run-at       document-idle
// @grant        GM_getValue
// @grant        GM_setValue
// @noframes
// ==/UserScript==

// ─── CONFIG DEFAULT VALUES ───────────────────────────────────────────────────
const DEFAULTS = {
  // Mode of action: 'hide' | 'dim' | 'highlight-only'
  MODE: 'dim',
  
  // Margin percentage to count as "cheapest" (e.g., 0.0 = absolute cheapest, 2.5 = within 2.5%)
  MARGIN_PERCENT: 0.0,
  
  // Opacity for non-cheapest products (only applied in 'dim' mode)
  DIM_OPACITY: 0.25,
  
  // Use price including shipping. If false, compares base price excluding shipping.
  USE_SHIPPING_PRICE: true,
  
  // Debounce time for DOM updates to avoid layout thrashing
  OBSERVER_DEBOUNCE_MS: 200,
  
  // Enable debug logging in the browser console
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

  /* Floating Settings Button */
  #tp-settings-fab {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: rgba(30, 41, 59, 0.7);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
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
    width: 90%;
    max-width: 440px;
    background: rgba(30, 41, 59, 0.85);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.1);
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
    margin: 0 0 20px 0;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.5px;
    background: linear-gradient(to right, #34d399, #059669);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  /* Form Elements */
  .tp-settings-group {
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .tp-settings-group label {
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
  }
  
  /* Segmented Control for Mode selection */
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
    padding: 8px 12px;
    cursor: pointer;
    font-size: 12px;
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

  /* Range and Number sliders */
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
  .tp-range-container input[type="range"]::-webkit-slider-runnable-track {
    background: transparent;
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

  /* Toggles / Custom Switch Checkbox */
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
  .tp-switch input:checked + .tp-slider:before {
    transform: translateX(20px);
    background-color: #fff;
  }

  /* Action Buttons */
  .tp-modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
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
`;

// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  // Defensive fallback helper to get/set settings persistently
  const _getValue = (key, def) => {
    try {
      if (typeof GM_getValue !== 'undefined') return GM_getValue(key, def);
    } catch (e) {}
    try {
      const local = localStorage.getItem(`tp_best_price_${key}`);
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
      localStorage.setItem(`tp_best_price_${key}`, JSON.stringify(val));
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
    
    get OBSERVER_DEBOUNCE_MS() { return parseInt(_getValue('OBSERVER_DEBOUNCE_MS', DEFAULTS.OBSERVER_DEBOUNCE_MS)); },
    set OBSERVER_DEBOUNCE_MS(v) { _setValue('OBSERVER_DEBOUNCE_MS', parseInt(v)); },
    
    get DEBUG() { return _getValue('DEBUG', DEFAULTS.DEBUG); },
    set DEBUG(v) { _setValue('DEBUG', v); }
  };

  const log = (...args) => { if (CONFIG.DEBUG) console.log('[Topp-Best-Price]', ...args); };

  // Inject Custom Stylesheet
  const styleEl = document.createElement('style');
  styleEl.textContent = STYLES;
  document.head.appendChild(styleEl);

  function updateBodyClasses() {
    document.body.classList.remove('tp-mode-dim', 'tp-mode-hide', 'tp-mode-highlight-only');
    document.body.classList.add(`tp-mode-${CONFIG.MODE}`);
    document.documentElement.style.setProperty('--tp-dim-opacity', CONFIG.DIM_OPACITY);
  }

  // Initial update of body classes
  updateBodyClasses();

  // Helper: Normalize names for robust comparison (strip whitespace and special characters)
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

  // Core Processing Function
  function processListings() {
    log('Checking active store filters...');

    // Locate active dealer filters
    const filterElements = document.querySelectorAll('.filters .f_remove_filter[data-target-type="df"]');
    
    // If no store filter is active, reset styles and exit
    if (filterElements.length === 0) {
      log('No active store filter found. Resetting product highlights.');
      
      const cards = document.querySelectorAll('.Plugin_Product.mixedBrowsingList');
      cards.forEach(card => {
        card.classList.remove('tp-is-cheapest', 'tp-not-cheapest', 'tp-no-store-offer');
        const badge = card.querySelector('.tp-best-price-badge');
        if (badge) badge.remove();
      });
      return;
    }

    // Map active filter store names (clean up sub-elements like remove icons)
    const activeStores = Array.from(filterElements).map(el => {
      const clone = el.cloneNode(true);
      const closeIcons = clone.querySelectorAll('.icon-close, .f_remove_icon, .close, span');
      closeIcons.forEach(icon => icon.remove());
      return normalizeName(clone.textContent);
    }).filter(name => name.length > 0);

    log(`Active store filters:`, activeStores);

    const cards = document.querySelectorAll('.Plugin_Product.mixedBrowsingList');
    log(`Processing ${cards.length} product cards...`);

    cards.forEach(card => {
      // Find all dealer price rows in this card
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
        // Find store-specific price
        const storePriceEl = CONFIG.USE_SHIPPING_PRICE
          ? (matchedRow.querySelector('.shippingPrice .Plugin_Price') || matchedRow.querySelector('.productPrice .Plugin_Price'))
          : (matchedRow.querySelector('.productPrice .Plugin_Price') || matchedRow.querySelector('.shippingPrice .Plugin_Price'));
        const storePrice = storePriceEl ? parsePrice(storePriceEl.textContent) : 0;

        // Find overall lowest price
        const bestPriceEl = CONFIG.USE_SHIPPING_PRICE
          ? (card.querySelector('.price_information_product .shippingPrice .Plugin_Price') || card.querySelector('.price_information_product .productPrice .Plugin_Price'))
          : (card.querySelector('.price_information_product .productPrice .Plugin_Price') || card.querySelector('.price_information_product .shippingPrice .Plugin_Price'));
        const bestPrice = bestPriceEl ? parsePrice(bestPriceEl.textContent) : 0;

        if (storePrice > 0 && bestPrice > 0) {
          const threshold = bestPrice * (1 + CONFIG.MARGIN_PERCENT / 100);
          const isCheapest = storePrice <= threshold;

          log(`Product: "${card.querySelector('.titleLink')?.textContent?.trim()}" | Store Price: ${storePrice} | Best Price: ${bestPrice} | Cheapest: ${isCheapest}`);

          if (isCheapest) {
            card.classList.add('tp-is-cheapest');
            card.classList.remove('tp-not-cheapest', 'tp-no-store-offer');
            
            // Add premium badge if missing
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
          // Fallback if price parsing fails
          card.classList.add('tp-no-store-offer');
          card.classList.remove('tp-is-cheapest', 'tp-not-cheapest');
          const badge = card.querySelector('.tp-best-price-badge');
          if (badge) badge.remove();
        }
      } else {
        // Store does not sell this item
        card.classList.add('tp-no-store-offer');
        card.classList.remove('tp-is-cheapest', 'tp-not-cheapest');
        const badge = card.querySelector('.tp-best-price-badge');
        if (badge) badge.remove();
      }
    });
  }

  // Setup Floating Settings Icon & Glassmorphic Configuration Dialog
  function setupUI() {
    // 1. Inject Settings Floating Button (FAB)
    const fabContainer = document.createElement('div');
    fabContainer.innerHTML = `
      <button id="tp-settings-fab" title="Configure Toppreise Best Price Highlighter">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
    `;
    const fabButton = fabContainer.firstElementChild;
    document.body.appendChild(fabButton);

    // 2. Inject Modal Layout
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = `
      <div id="tp-settings-modal-backdrop">
        <div id="tp-settings-modal">
          <h3>Best Price Highlights</h3>
          
          <div class="tp-settings-group">
            <label>Filter Mode</label>
            <div class="tp-segmented-control">
              <input type="radio" id="tp-mode-highlight-only" name="tp-mode" value="highlight-only">
              <label for="tp-mode-highlight-only">Highlight</label>
              
              <input type="radio" id="tp-mode-dim" name="tp-mode" value="dim">
              <label for="tp-mode-dim">Dim</label>
              
              <input type="radio" id="tp-mode-hide" name="tp-mode" value="hide">
              <label for="tp-mode-hide">Hide</label>
            </div>
          </div>
          
          <div class="tp-settings-group">
            <label>Price Margin Tolerance (%)</label>
            <div class="tp-range-container">
              <input type="range" id="tp-margin-range" min="0" max="15" step="0.5" value="0">
              <input type="number" id="tp-margin-val" min="0" max="100" step="0.1" value="0">
            </div>
          </div>
          
          <div class="tp-settings-group" id="tp-dim-opacity-group">
            <label>Non-Cheapest Opacity</label>
            <div class="tp-range-container">
              <input type="range" id="tp-opacity-range" min="0.05" max="0.95" step="0.05" value="0.25">
              <input type="number" id="tp-opacity-val" min="5" max="95" step="5" value="25">
            </div>
          </div>
          
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>Compare Shipping</label>
              <span class="tp-switch-desc">Compare prices including delivery cost</span>
            </div>
            <label class="tp-switch">
              <input type="checkbox" id="tp-shipping-toggle">
              <span class="tp-slider"></span>
            </label>
          </div>
          
          <div class="tp-modal-actions">
            <button type="button" class="tp-btn tp-btn-secondary" id="tp-btn-close">Cancel</button>
            <button type="button" class="tp-btn tp-btn-primary" id="tp-btn-save">Save</button>
          </div>
        </div>
      </div>
    `;
    const backdrop = modalContainer.firstElementChild;
    document.body.appendChild(backdrop);

    // Form DOM Elements
    const modeHighlight = document.getElementById('tp-mode-highlight-only');
    const modeDim = document.getElementById('tp-mode-dim');
    const modeHide = document.getElementById('tp-mode-hide');
    const marginRange = document.getElementById('tp-margin-range');
    const marginVal = document.getElementById('tp-margin-val');
    const opacityRange = document.getElementById('tp-opacity-range');
    const opacityVal = document.getElementById('tp-opacity-val');
    const shippingToggle = document.getElementById('tp-shipping-toggle');
    const btnSave = document.getElementById('tp-btn-save');
    const btnClose = document.getElementById('tp-btn-close');

    // Populate current config values into form fields
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

    // Two-way binding for margin range/number fields
    marginRange.addEventListener('input', (e) => {
      marginVal.value = e.target.value;
    });
    marginVal.addEventListener('input', (e) => {
      let val = parseFloat(e.target.value);
      if (isNaN(val)) val = 0;
      marginRange.value = val;
    });

    // Two-way binding for dim opacity range/number fields
    opacityRange.addEventListener('input', (e) => {
      opacityVal.value = Math.round(parseFloat(e.target.value) * 100);
    });
    opacityVal.addEventListener('input', (e) => {
      let val = parseInt(e.target.value);
      if (isNaN(val)) val = 25;
      opacityRange.value = val / 100;
    });

    // Handle display mode switches to enable/disable opacity slider dynamically
    [modeHighlight, modeDim, modeHide].forEach(radio => {
      radio.addEventListener('change', () => {
        const mode = document.querySelector('input[name="tp-mode"]:checked').value;
        updateOpacityState(mode);
      });
    });

    // Open Config Modal
    fabButton.addEventListener('click', () => {
      syncFieldsFromConfig();
      backdrop.classList.add('open');
    });

    // Close Config Modal
    const closeModal = () => backdrop.classList.remove('open');
    btnClose.addEventListener('click', closeModal);
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeModal();
    });

    // Save and apply configurations
    btnSave.addEventListener('click', () => {
      const mode = document.querySelector('input[name="tp-mode"]:checked').value;
      const margin = parseFloat(marginVal.value) || 0;
      const opacity = parseFloat(opacityRange.value) || 0.25;
      const useShipping = shippingToggle.checked;

      // Persist values
      CONFIG.MODE = mode;
      CONFIG.MARGIN_PERCENT = margin;
      CONFIG.DIM_OPACITY = opacity;
      CONFIG.USE_SHIPPING_PRICE = useShipping;

      updateBodyClasses();
      closeModal();
      
      // Run processing immediately with new config
      processListings();
    });
  }

  // Debouncing to avoid infinite loops and UI lag during rapid DOM updates
  let debounceTimer = null;
  const observer = new MutationObserver(() => {
    try {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(processListings, CONFIG.OBSERVER_DEBOUNCE_MS);
    } catch (e) {
      log('Observer error:', e);
    }
  });

  // Start observing
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: false,
    characterData: false
  });

  // Initialize UI controls & default views
  setupUI();
  processListings();

  // Safety net fallback to catch occasional dynamic load delays
  setInterval(processListings, 5000);

})();
