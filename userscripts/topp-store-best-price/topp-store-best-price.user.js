// ==UserScript==
// @name         Toppreise.ch Store Best Price Highlighter & Filter
// @namespace    https://github.com/tazztone/scripts
// @version      0.1.0
// @description  Highlights, dims, or hides products on Toppreise.ch based on whether a filtered store offers the best price.
// @author       tazztone
// @match        https://www.toppreise.ch/*
// @run-at       document-idle
// @grant        none
// @noframes
// ==/UserScript==

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const CONFIG = {
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
    opacity: ${CONFIG.DIM_OPACITY} !important;
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
`;

// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  const log = (...args) => { if (CONFIG.DEBUG) console.log('[Topp-Best-Price]', ...args); };

  // Inject Custom Stylesheet
  const styleEl = document.createElement('style');
  styleEl.textContent = STYLES;
  document.head.appendChild(styleEl);

  // Apply mode container class on the body
  document.body.classList.add(`tp-mode-${CONFIG.MODE}`);

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

  // Start observing. Note: attributes: false avoids callbacks triggering on class updates we perform!
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: false,
    characterData: false
  });

  // Initial Run
  processListings();

  // Safety net fallback to catch occasional dynamic load delays
  setInterval(processListings, 5000);

})();
