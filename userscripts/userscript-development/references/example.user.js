// ==UserScript==
// @name         Example Userscript Template
// @namespace    https://github.com/tazztone/scripts
// @version      1.0.0
// @description  Description
// @author       tazztone
// @match        https://*.example.com/*
// @run-at       document-idle
// @grant        none
// @noframes
// ==/UserScript==

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const CONFIG = {
  ENABLED: true,
  ACTION_DELAY_MS: 1000,
  OBSERVER_DEBOUNCE_MS: 150,
};

// CSS
const STYLE = `
  .my-custom-class {
    border: 2px solid red !important;
  }
`;
// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  const styleEl = document.createElement('style');
  styleEl.textContent = STYLE;
  document.head.appendChild(styleEl);

  const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();

  function isVisible(el) {
    if (!document.contains(el)) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && el.getBoundingClientRect().width > 0;
  }

  let logicLock = false;

  function performLogic() {
    if (!CONFIG.ENABLED) return;
    // EXAMPLE: Replace with selectors audited in RESEARCH_LOG.md
    const target = document.querySelector('.target-class');
    if (target && isVisible(target)) {
      target.click();
      console.log('[Script] Action performed.');
    }
  }

  async function run() {
    if (logicLock) return;
    logicLock = true;
    try {
      performLogic();
    } finally {
      // Cooldown delay to throttle execution on highly dynamic SPAs
      setTimeout(() => { logicLock = false; }, CONFIG.ACTION_DELAY_MS);
    }
  }

  function handleUrlChange() {
    console.log('[Script] URL changed:', location.href);
    logicLock = false; // Clear logical blocks on SPA route swaps
    run();
  }

  // Hook modern Navigation API or fallback observer for SPA routing
  if (self.navigation) {
    self.navigation.addEventListener('navigatesuccess', handleUrlChange);
  } else {
    let lastPath = location.href;
    new MutationObserver(() => {
      if (lastPath !== location.href) {
        lastPath = location.href;
        handleUrlChange();
      }
    }).observe(document, { subtree: true, childList: true });
  }

  let debounceTimer = null;
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(run, CONFIG.OBSERVER_DEBOUNCE_MS);
  });

  observer.observe(document.documentElement, { childList: true, subtree: true });
  
  // Bootstrap execution
  run();
})();
