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
  DEBUG: true,
};

// ─── STYLES ──────────────────────────────────────────────────────────────────
const STYLE = `
  .my-custom-class {
    border: 2px solid red !important;
  }
`;
// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  // Inject styles
  const styleEl = document.createElement('style');
  styleEl.textContent = STYLE;
  document.head.appendChild(styleEl);

  // ─── UTILITIES ──────────────────────────────────────────────────────────────
  const log = (...args) => { if (CONFIG.DEBUG) console.log('[Script]', ...args); };
  const err = (...args) => { console.error('[Script] Error:', ...args); };

  const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();

  function isVisible(el) {
    if (!document.contains(el)) return false;
    const style = window.getComputedStyle(el);
    return (
      style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      style.opacity !== '0' &&
      el.getBoundingClientRect().width > 0
    );
  }

  // ─── CORE LOGIC ─────────────────────────────────────────────────────────────
  let logicLock = false;
  let lastActionTime = 0;

  function performLogic() {
    if (!CONFIG.ENABLED) return;
    // EXAMPLE: Replace with selectors audited in RESEARCH_LOG.md
    const target = document.querySelector('.target-class');
    if (target && isVisible(target)) {
      target.click();
      log('Action performed.');
    }
  }

  function run() {
    if (logicLock) return;
    if (Date.now() - lastActionTime < CONFIG.ACTION_DELAY_MS) return;
    logicLock = true;
    try {
      performLogic();
      lastActionTime = Date.now();
    } catch (e) {
      err('run() error:', e);
    } finally {
      logicLock = false;
    }
  }

  // ─── ORCHESTRATION ──────────────────────────────────────────────────────────
  function handleUrlChange() {
    log('URL changed:', location.href);
    logicLock = false;
    lastActionTime = 0;
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
    // Guard: an uncaught error inside an observer silently kills it.
    try {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(run, CONFIG.OBSERVER_DEBOUNCE_MS);
    } catch (e) {
      err('Observer error:', e);
    }
  });

  // Primary: reactive observer
  observer.observe(document.documentElement, { childList: true, subtree: true });

  // Immediate: handle already-present DOM state
  run();

  // Safety net: periodic fallback if the observer dies
  setInterval(run, 5000);
})();
