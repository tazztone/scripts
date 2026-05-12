// ==UserScript==
// @name         Toppreise.ch Price Alarm Auto-Filler
// @namespace    https://github.com/tazztone/scripts
// @version      0.1.0
// @description  Automatically configures a price alarm (60% value, 2 years duration) on clicking the alarm bell.
// @author       tazztone
// @match        https://www.toppreise.ch/preisvergleich/*
// @match        https://www.toppreise.ch/price-comparison/*
// @match        https://www.toppreise.ch/comparison-prix/*
// @run-at       document-idle
// @grant        none
// @noframes
// ==/UserScript==

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const CONFIG = {
  ENABLED: true,
  TARGET_PERCENT: 0.60, // 60% of present value
  DURATION_DAYS: "730", // 2 years
  ACTION_DELAY_MS: 300, // Initial delay after modal mount to ensure stability
  AUTO_SUBMIT: true,   // Set to false to only fill and not submit automatically
  DEBUG: true
};

// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  const log = (...args) => { if (CONFIG.DEBUG) console.log('[Topp-Alarm]', ...args); };

  function parsePrice(priceStr) {
    if (!priceStr) return 0;
    // Remove non-numeric garbage, handle thousands ' and comma decimals
    const clean = priceStr.replace(/[^\d,.]/g, '').replace("'", "").replace(',', '.');
    const val = parseFloat(clean);
    return isNaN(val) ? 0 : val;
  }

  function triggerInputEvents(el) {
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function performAutomation(modalContainer) {
    log('Processing price alarm modal...');

    // 1. Extract Base Price
    // Prefer shipping price wrapper first as defined in Research Log
    const priceEl = modalContainer.querySelector('.shippingPrice .Plugin_Price') 
                 || modalContainer.querySelector('.productPrice .Plugin_Price')
                 || document.querySelector('.pageContent .priceContainer .Plugin_Price'); // Fallback global

    if (!priceEl) {
      log('Error: Could not locate base price element.');
      return;
    }

    const basePrice = parsePrice(priceEl.textContent);
    if (basePrice === 0) {
      log('Error: Failed to parse base price.');
      return;
    }

    const targetPrice = (basePrice * CONFIG.TARGET_PERCENT).toFixed(2);
    log(`Base Price: ${basePrice}, Target Price (60%): ${targetPrice}`);

    // 2. Set Price Field
    const priceInput = modalContainer.querySelector('#f_NewInfoMailForm_priceFrom');
    if (priceInput) {
      priceInput.value = targetPrice;
      triggerInputEvents(priceInput);
      log('Set target price input.');
    } else {
      log('Error: Target price input not found.');
    }

    // 3. Configure Duration (2 Years)
    // First, set the hidden field
    const durInput = modalContainer.querySelector('input[name="im_nimf_du"]');
    if (durInput) {
      durInput.value = CONFIG.DURATION_DAYS;
      triggerInputEvents(durInput);
    }
    // Second, simulate dropdown item click if visible to sync custom UI state
    const dropdownItem = modalContainer.querySelector(`li[data-value="${CONFIG.DURATION_DAYS}"]`);
    if (dropdownItem) {
      dropdownItem.click();
      log('Selected duration from dropdown.');
    }

    // 4. Ensure Privacy / TOS is Accepted
    const tosCheckbox = modalContainer.querySelector('#im_nimf_prtrm');
    if (tosCheckbox) {
      if (!tosCheckbox.checked) {
        tosCheckbox.checked = true;
        triggerInputEvents(tosCheckbox);
        log('Accepted Privacy Terms (was unchecked).');
      } else {
        log('Privacy Terms already accepted.');
      }
    }

    // 5. Submit the form automatically
    if (CONFIG.AUTO_SUBMIT) {
      const submitBtn = modalContainer.querySelector('input.f_submitbtn[type="submit"]');
      if (submitBtn) {
        log('Submitting configuration...');
        // Brief delay before final submission to ensure standard scripts processes events
        setTimeout(() => { submitBtn.click(); }, 200);
      } else {
        log('Error: Could not find submit button.');
      }
    }
  }

  // Debounce safety for repetitive DOM mutations
  let runTimeout = null;

  function checkForModal() {
    if (!CONFIG.ENABLED) return;

    // Target injected modal form
    const modal = document.querySelector('.Plugin_NewInfoMailForm');
    
    // If modal exists and hasn't been processed yet
    if (modal && !modal.dataset.tpAlarmProcessed) {
      log('Modal detected! Scheduling automation run.');
      
      // Mark immediately to prevent duplicate entry
      modal.dataset.tpAlarmProcessed = 'true';

      clearTimeout(runTimeout);
      runTimeout = setTimeout(() => {
        // Verify modal is still present
        if (document.contains(modal)) {
          performAutomation(modal);
        }
      }, CONFIG.ACTION_DELAY_MS);
    }
  }

  // Observe body for dynamically added forms
  const observer = new MutationObserver((mutations) => {
    // Brief check if any childList mutation involves our key target
    const hasAdditions = mutations.some(m => m.addedNodes.length > 0);
    if (hasAdditions) {
      checkForModal();
    }
  });

  log('Initialized. Watching for price alarm triggers.');
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  // Immediate check in case modal is already open on run
  checkForModal();

})();
