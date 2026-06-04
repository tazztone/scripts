// ==UserScript==
// @name         Toppreise.ch Price Alarm Auto-Filler
// @namespace    https://github.com/tazztone/scripts
// @version      0.3.1
// @description  Automatically configures a price alarm (60% value, 2 years duration) on clicking the alarm bell.
// @author       tazztone
// @match        https://www.toppreise.ch/*
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

// CSS Style Definition for Toast Notification
const STYLES = `
  #tp-toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 999999;
    pointer-events: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  .tp-toast {
    background: rgba(18, 18, 18, 0.9);
    color: #ffffff;
    padding: 12px 20px;
    border-radius: 8px;
    margin-bottom: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    border-left: 4px solid #4caf50;
    transform: translateX(100%);
    opacity: 0;
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    font-size: 14px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 10px;
    backdrop-filter: blur(5px);
  }
  .tp-toast.visible {
    transform: translateX(0);
    opacity: 1;
  }
`;

// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  const log = (...args) => { if (CONFIG.DEBUG) console.log('[Topp-Alarm]', ...args); };

  // Rate limiting to prevent duplicate runs on rapid sequential DOM mutations
  let lastRunTimestamp = 0;
  const THROTTLE_MS = 2000; 

  // Inject CSS
  const styleEl = document.createElement('style');
  styleEl.textContent = STYLES;
  document.head.appendChild(styleEl);

  // Setup Container
  let toastContainer = document.getElementById('tp-toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'tp-toast-container';
    document.body.appendChild(toastContainer);
  }

  function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'tp-toast';
    toast.innerHTML = `<span>✅</span> <div>${message}</div>`;
    toastContainer.appendChild(toast);
    
    // Trigger animation
    requestAnimationFrame(() => {
      toast.classList.add('visible');
    });

    // Remove after 5 seconds
    setTimeout(() => {
      toast.classList.remove('visible');
      setTimeout(() => toast.remove(), 300);
    }, 5000);
  }

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
    // Double-guard check
    const now = Date.now();
    if (now - lastRunTimestamp < THROTTLE_MS) {
      log('Execution throttled (duplicate prevented).');
      return;
    }
    lastRunTimestamp = now;

    log('Processing price alarm modal...');

    // 1. Extract Base Price
    // Prefer shipping price wrapper first as defined in Research Log
    const isProductPage = window.location.pathname.startsWith('/preisvergleich/') 
                       || window.location.pathname.startsWith('/price-comparison/') 
                       || window.location.pathname.startsWith('/comparison-prix/');
    const priceEl = modalContainer.querySelector('.shippingPrice .Plugin_Price') 
                 || modalContainer.querySelector('.productPrice .Plugin_Price')
                 || (isProductPage ? document.querySelector('.pageContent .priceContainer .Plugin_Price') : null);

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

    // 5. Show Confirmation Toast
    const readableDuration = CONFIG.DURATION_DAYS === "730" ? "2 Years" : `${CONFIG.DURATION_DAYS} Days`;
    showToast(`Applied Alarm: <b>${targetPrice} CHF</b> | ${readableDuration}`);
    log('Displayed success notification banner.');

    // 6. Submit the form automatically
    if (CONFIG.AUTO_SUBMIT) {
      const submitBtn = modalContainer.querySelector('input.f_submitbtn[type="submit"]');
      if (submitBtn) {
        log('Submitting configuration...');
        // Brief delay before final submission to ensure standard scripts processes events
        setTimeout(() => {
          submitBtn.click();
          
          // Auto-close confirmation screen after successful submission
          let closeAttempts = 0;
          const autoCloseInterval = setInterval(() => {
            const dialog = modalContainer.closest('.AbstractDialog');
            const closeBtn = dialog?.querySelector('.AbstractDialog_CloseButton');
            const formEl = dialog?.querySelector('#f_NewInfoMailForm_priceFrom');
            
            closeAttempts++;
            if (!formEl) {
              clearInterval(autoCloseInterval);
              if (closeBtn) {
                closeBtn.click();
                log('Closed confirmation screen.');
              }
            } else if (closeAttempts > 15) {
              clearInterval(autoCloseInterval);
              log('Timeout waiting for form submission to complete.');
            }
          }, 200);
        }, 300);
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
