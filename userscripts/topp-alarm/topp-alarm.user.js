// ==UserScript==
// @name         Toppreise.ch Price Alarm Auto-Filler
// @namespace    https://github.com/tazztone/scripts
// @version      0.4.0
// @description  Automatically configures a price alarm (60% value, 2 years duration) on clicking the alarm bell.
// @author       tazztone
// @match        https://www.toppreise.ch/*
// @run-at       document-idle
// @grant        GM_getValue
// @grant        GM_setValue
// @noframes
// ==/UserScript==

// ─── CONFIG DEFAULT VALUES ───────────────────────────────────────────────────
const DEFAULTS = {
  ENABLED: true,
  TARGET_PERCENT: 0.60, // 60% of present value
  DURATION_DAYS: "730", // 2 years (options: 90, 180, 365, 730)
  ACTION_DELAY_MS: 300, // Initial delay after modal mount to ensure stability
  AUTO_SUBMIT: true,   // Set to false to only fill and not submit automatically
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
    bottom: 8px;
    right: 8px;
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
    max-width: 480px;
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
    margin: 0;
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

  /* Blue color variation for Alarm segmented controls */
  .tp-segmented-control-blue input[type="radio"]:checked + label {
    background: #3b82f6 !important;
    box-shadow: 0 2px 6px rgba(59, 130, 246, 0.3) !important;
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
  .tp-range-container.tp-blue input[type="range"] {
    accent-color: #3b82f6;
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

  /* Toast Notification */
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

  // Defensive fallback helper to get/set settings persistently
  const _getValue = (key, def) => {
    try {
      if (typeof GM_getValue !== 'undefined') return GM_getValue(key, def);
    } catch (e) {}
    try {
      const local = localStorage.getItem(`tp_alarm_${key}`);
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
      localStorage.setItem(`tp_alarm_${key}`, JSON.stringify(val));
    } catch (e) {}
  };

  // Dynamic config bindings using getters and setters
  const CONFIG = {
    get ENABLED() { return _getValue('ENABLED', DEFAULTS.ENABLED); },
    set ENABLED(v) { _setValue('ENABLED', v); },
    
    get TARGET_PERCENT() { return parseFloat(_getValue('TARGET_PERCENT', DEFAULTS.TARGET_PERCENT)); },
    set TARGET_PERCENT(v) { _setValue('TARGET_PERCENT', parseFloat(v)); },
    
    get DURATION_DAYS() { return _getValue('DURATION_DAYS', DEFAULTS.DURATION_DAYS).toString(); },
    set DURATION_DAYS(v) { _setValue('DURATION_DAYS', v.toString()); },
    
    get ACTION_DELAY_MS() { return parseInt(_getValue('ACTION_DELAY_MS', DEFAULTS.ACTION_DELAY_MS)); },
    set ACTION_DELAY_MS(v) { _setValue('ACTION_DELAY_MS', parseInt(v)); },
    
    get AUTO_SUBMIT() { return _getValue('AUTO_SUBMIT', DEFAULTS.AUTO_SUBMIT); },
    set AUTO_SUBMIT(v) { _setValue('AUTO_SUBMIT', v); },
    
    get DEBUG() { return _getValue('DEBUG', DEFAULTS.DEBUG); },
    set DEBUG(v) { _setValue('DEBUG', v); }
  };

  const log = (...args) => { if (CONFIG.DEBUG) console.log('[Topp-Alarm]', ...args); };

  // Rate limiting to prevent duplicate runs on rapid sequential DOM mutations
  let lastRunTimestamp = 0;
  const THROTTLE_MS = 2000; 

  // Inject Custom Stylesheet safely
  if (!document.getElementById('tp-unified-settings-styles')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'tp-unified-settings-styles';
    styleEl.textContent = STYLES;
    document.head.appendChild(styleEl);
  }

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
    log(`Base Price: ${basePrice}, Target Price (${Math.round(CONFIG.TARGET_PERCENT * 100)}%): ${targetPrice}`);

    // 2. Set Price Field
    const priceInput = modalContainer.querySelector('#f_NewInfoMailForm_priceFrom');
    if (priceInput) {
      priceInput.value = targetPrice;
      triggerInputEvents(priceInput);
      log('Set target price input.');
    } else {
      log('Error: Target price input not found.');
    }

    // 3. Configure Duration
    const durInput = modalContainer.querySelector('input[name="im_nimf_du"]');
    if (durInput) {
      durInput.value = CONFIG.DURATION_DAYS;
      triggerInputEvents(durInput);
    }
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
    const readableDuration = CONFIG.DURATION_DAYS === "730" ? "2 Years" : 
                             CONFIG.DURATION_DAYS === "365" ? "1 Year" : 
                             CONFIG.DURATION_DAYS === "180" ? "6 Months" : "3 Months";
    showToast(`Applied Alarm: <b>${targetPrice} CHF</b> | ${readableDuration}`);
    log('Displayed success notification banner.');

    // 6. Submit the form automatically
    if (CONFIG.AUTO_SUBMIT) {
      const submitBtn = modalContainer.querySelector('input.f_submitbtn[type="submit"]');
      if (submitBtn) {
        log('Submitting configuration...');
        
        // Resolve dialog container and close button references before submission
        const dialog = modalContainer.closest('.AbstractDialog');
        const closeBtn = dialog?.querySelector('.AbstractDialog_CloseButton');

        setTimeout(() => {
          submitBtn.click();
          
          let closeAttempts = 0;
          const autoCloseInterval = setInterval(() => {
            const formStillAttached = dialog && document.contains(modalContainer);
            
            closeAttempts++;
            if (!formStillAttached) {
              clearInterval(autoCloseInterval);
              const currentCloseBtn = dialog?.querySelector('.AbstractDialog_CloseButton') || closeBtn;
              if (currentCloseBtn) {
                currentCloseBtn.click();
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

  // Ensure Skeleton Modal is loaded (and shared between scripts)
  function ensureSkeleton() {
    // Ensure FAB exists
    let fabButton = document.getElementById('tp-settings-fab');
    if (!fabButton) {
      const fabContainer = document.createElement('div');
      fabContainer.innerHTML = `
        <button id="tp-settings-fab" title="Configure Toppreise Enhancements">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      `;
      fabButton = fabContainer.firstElementChild;
      document.body.appendChild(fabButton);
    }

    // Ensure Modal Backdrop and Container exists
    let backdrop = document.getElementById('tp-settings-modal-backdrop');
    if (!backdrop) {
      const modalContainer = document.createElement('div');
      modalContainer.innerHTML = `
        <div id="tp-settings-modal-backdrop">
          <div id="tp-settings-modal">
            <h3>Toppreise Enhancements</h3>
            <div id="tp-settings-sections" style="display: flex; flex-direction: column; gap: 24px; max-height: 70vh; overflow-y: auto; padding-right: 4px;">
              <!-- Individual settings groups are dynamically appended here -->
            </div>
            <div class="tp-modal-actions">
              <button type="button" class="tp-btn tp-btn-secondary" id="tp-btn-close">Cancel</button>
              <button type="button" class="tp-btn tp-btn-primary" id="tp-btn-save">Save Settings</button>
            </div>
          </div>
        </div>
      `;
      backdrop = modalContainer.firstElementChild;
      document.body.appendChild(backdrop);

      // Handle close dialog
      const btnClose = document.getElementById('tp-btn-close');
      const closeModal = () => backdrop.classList.remove('open');
      btnClose.addEventListener('click', closeModal);
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeModal();
      });

      // Show dialog + trigger fields sync across all scripts
      fabButton.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('tp-settings-open'));
        backdrop.classList.add('open');
      });

      // Save configurations across all scripts
      const btnSave = document.getElementById('tp-btn-save');
      btnSave.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('tp-settings-save'));
        closeModal();
      });
    }

    return { fabButton, backdrop };
  }

  // Setup Floating Settings Icon & Glassmorphic Configuration Dialog
  function setupUI() {
    ensureSkeleton();

    // Inject Alarm Section if not already there
    let section = document.getElementById('tp-section-alarm');
    if (!section) {
      const sectionsHolder = document.getElementById('tp-settings-sections');
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = `
        <div id="tp-section-alarm">
          <h4 style="margin: 0 0 16px 0; color: #3b82f6; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 6px;">Auto-Alarm Settings</h4>
          
          <div class="tp-settings-group tp-switch-container">
            <div class="tp-switch-label">
              <label>Enable Auto-Fill</label>
              <span class="tp-switch-desc">Automatically configure price alarm modals</span>
            </div>
            <label class="tp-switch tp-blue">
              <input type="checkbox" id="tp-alarm-enabled">
              <span class="tp-slider"></span>
            </label>
          </div>

          <div class="tp-settings-group" id="tp-alarm-percent-group">
            <label>Target Price Percent (%)</label>
            <div class="tp-range-container tp-blue">
              <input type="range" id="tp-alarm-percent-range" min="10" max="95" step="5" value="60">
              <input type="number" id="tp-alarm-percent-val" min="10" max="95" step="5" value="60">
            </div>
          </div>

          <div class="tp-settings-group" id="tp-alarm-duration-group">
            <label>Alarm Expiry Duration</label>
            <div class="tp-segmented-control tp-segmented-control-blue">
              <input type="radio" id="tp-dur-90" name="tp-alarm-duration" value="90">
              <label for="tp-dur-90">3m</label>
              
              <input type="radio" id="tp-dur-180" name="tp-alarm-duration" value="180">
              <label for="tp-dur-180">6m</label>
              
              <input type="radio" id="tp-dur-365" name="tp-alarm-duration" value="365">
              <label for="tp-dur-365">1y</label>
              
              <input type="radio" id="tp-dur-730" name="tp-alarm-duration" value="730">
              <label for="tp-dur-730">2y</label>
            </div>
          </div>

          <div class="tp-settings-group tp-switch-container" id="tp-alarm-autosubmit-group">
            <div class="tp-switch-label">
              <label>Auto-Submit</label>
              <span class="tp-switch-desc">Instantly submit the alarm after filling</span>
            </div>
            <label class="tp-switch tp-blue">
              <input type="checkbox" id="tp-alarm-autosubmit">
              <span class="tp-slider"></span>
            </label>
          </div>
        </div>
      `;
      section = tempDiv.firstElementChild;
      sectionsHolder.appendChild(section);
    }

    // Form DOM Elements
    const alarmEnabled = document.getElementById('tp-alarm-enabled');
    const alarmPercentRange = document.getElementById('tp-alarm-percent-range');
    const alarmPercentVal = document.getElementById('tp-alarm-percent-val');
    const dur90 = document.getElementById('tp-dur-90');
    const dur180 = document.getElementById('tp-dur-180');
    const dur365 = document.getElementById('tp-dur-365');
    const dur730 = document.getElementById('tp-dur-730');
    const alarmAutoSubmit = document.getElementById('tp-alarm-autosubmit');

    // Populate current config values into form fields
    function syncFieldsFromConfig() {
      alarmEnabled.checked = CONFIG.ENABLED;
      
      const percent = Math.round(CONFIG.TARGET_PERCENT * 100);
      alarmPercentRange.value = percent;
      alarmPercentVal.value = percent;
      
      const duration = CONFIG.DURATION_DAYS;
      if (duration === "90") dur90.checked = true;
      else if (duration === "180") dur180.checked = true;
      else if (duration === "365") dur365.checked = true;
      else dur730.checked = true;

      alarmAutoSubmit.checked = CONFIG.AUTO_SUBMIT;

      updateControlsState(CONFIG.ENABLED);
    }

    function updateControlsState(enabled) {
      const percentGroup = document.getElementById('tp-alarm-percent-group');
      const durationGroup = document.getElementById('tp-alarm-duration-group');
      const submitGroup = document.getElementById('tp-alarm-autosubmit-group');
      const elements = [percentGroup, durationGroup, submitGroup];

      elements.forEach(el => {
        if (el) {
          el.style.opacity = enabled ? '1' : '0.4';
          const inputs = el.querySelectorAll('input');
          inputs.forEach(input => {
            input.disabled = !enabled;
          });
        }
      });
    }

    // Initialize UI fields
    syncFieldsFromConfig();

    // Two-way bindings for percent range/number fields
    alarmPercentRange.addEventListener('input', (e) => {
      alarmPercentVal.value = e.target.value;
    });
    alarmPercentVal.addEventListener('input', (e) => {
      let val = parseInt(e.target.value);
      if (isNaN(val)) val = 60;
      alarmPercentRange.value = val;
    });

    // Disable/enable controls on enablement toggle
    alarmEnabled.addEventListener('change', (e) => {
      updateControlsState(e.target.checked);
    });

    // Register listeners for shared dialog open and save triggers
    document.addEventListener('tp-settings-open', () => {
      syncFieldsFromConfig();
    });

    document.addEventListener('tp-settings-save', () => {
      const enabled = alarmEnabled.checked;
      const percent = Math.max(10, Math.min(100, parseInt(alarmPercentVal.value) || 60)) / 100;
      
      const checkedDurEl = document.querySelector('input[name="tp-alarm-duration"]:checked');
      const duration = checkedDurEl ? checkedDurEl.value : "730";
      const autosubmit = alarmAutoSubmit.checked;

      // Persist config
      CONFIG.ENABLED = enabled;
      CONFIG.TARGET_PERCENT = percent;
      CONFIG.DURATION_DAYS = duration;
      CONFIG.AUTO_SUBMIT = autosubmit;
    });
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

  // Setup UI controls & bindings
  setupUI();

  // Immediate check in case modal is already open on run
  checkForModal();

})();
