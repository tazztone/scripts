// ==UserScript==
// @name         Example Userscript Template
// @namespace    https://github.com/tazztone/scripts
// @version      1.0.0
// @description  Standard boilerplate demonstrating Shadow DOM UI, non-destructive traversal, yielding, and reactive orchestration.
// @author       tazztone
// @match        https://*.example.com/*
// @run-at       document-idle
// @grant        GM_getValue
// @grant        GM_setValue
// @noframes
// ==/UserScript==

// ─── CONFIG & DEFAULTS ───────────────────────────────────────────────────────
const DEFAULTS = {
  ENABLED: true,
  ACTION_DELAY_MS: 1000,
  OBSERVER_DEBOUNCE_MS: 150,
  DEBUG: true,
};

const PREFIX = 'px_example_';

// ─── SHADOW DOM STYLES (100% Isolated from Page CSS) ────────────────────────
const SHADOW_STYLES = `
  :host { all: initial; font-family: system-ui, -apple-system, sans-serif; }
  #px-fab {
    position: fixed;
    right: 16px;
    bottom: 16px;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: #1e293b;
    color: #f8fafc;
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    z-index: 99999;
    transition: transform 0.2s ease, background 0.2s ease;
  }
  #px-fab:hover { transform: scale(1.08); background: #2563eb; }
  dialog[popover] {
    box-sizing: border-box;
    width: min(90%, 400px);
    max-height: 85vh;
    overflow-y: auto;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 12px;
    background: #0f172a;
    color: #f8fafc;
    padding: 20px;
    margin: auto;
    box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);
  }
  dialog::backdrop {
    background: rgba(15,23,42,0.6);
    backdrop-filter: blur(4px);
  }
  .px-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .px-btn { padding: 8px 14px; border-radius: 6px; border: 0; cursor: pointer; font-weight: 600; }
  .px-btn-primary { background: #2563eb; color: #fff; }
  .px-toast-container { position: fixed; top: 16px; right: 16px; display: flex; flex-direction: column; gap: 8px; z-index: 100000; }
  .px-toast { background: #1e293b; color: #fff; padding: 10px 16px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: opacity 0.3s; }
  .px-toast.fade-out { opacity: 0; }
`;

(() => {
  'use strict';

  // ─── STORAGE & CONFIG ───────────────────────────────────────────────────────
  function readConfig(key, fallback) {
    const fullKey = `${PREFIX}${key}`;
    try {
      if (typeof GM_getValue === 'function') {
        const val = GM_getValue(fullKey, undefined);
        if (val !== undefined) return val;
      }
      const local = localStorage.getItem(fullKey);
      if (local !== null) return JSON.parse(local);
    } catch (_) {}
    return fallback;
  }

  function writeConfig(key, value) {
    const fullKey = `${PREFIX}${key}`;
    try { if (typeof GM_setValue === 'function') GM_setValue(fullKey, value); } catch (_) {}
    try { localStorage.setItem(fullKey, JSON.stringify(value)); } catch (_) {}
  }

  // ─── LOGGING & UTILITIES ───────────────────────────────────────────────────
  const log = (...args) => { if (readConfig('DEBUG', DEFAULTS.DEBUG)) console.log('[Script]', ...args); };
  const err = (...args) => console.error('[Script] Error:', ...args);
  const normalize = s => String(s || '').replace(/\s+/g, ' ').trim().toLowerCase();

  function isVisible(el) {
    if (!el || !document.contains(el)) return false;
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none'
      && style.visibility !== 'hidden'
      && style.opacity !== '0'
      && rect.width > 0
      && rect.height > 0;
  }

  // Non-destructive text scanner: never overwrites innerHTML or destroys listeners
  function findTextNodes(root, pattern) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue?.trim()) return NodeFilter.FILTER_REJECT;
        const parent = node.parentElement;
        if (!parent || parent.closest('#px-root, script, style, textarea, input, [contenteditable="true"]')) {
          return NodeFilter.FILTER_REJECT;
        }
        return pattern.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
      }
    });
    const matches = [];
    while (walker.nextNode()) matches.push(walker.currentNode);
    return matches;
  }

  // Multi-element batched processor protecting Interaction to Next Paint (INP) with cancellation guard
  let activeProcessRunId = 0;

  async function batchProcessElements(elements, processFn, batchSize = 20) {
    const currentRunId = ++activeProcessRunId;
    for (let i = 0; i < elements.length; i += batchSize) {
      if (currentRunId !== activeProcessRunId) return; // Discard stale in-flight batch
      const chunk = elements.slice(i, i + batchSize);
      await new Promise(resolve => requestAnimationFrame(() => {
        chunk.forEach(processFn);
        resolve();
      }));
      if (currentRunId !== activeProcessRunId) return;
      if (globalThis.scheduler?.yield) await scheduler.yield();
    }
  }

  function dispatchClickEvents(element) {
    if (!element) return;
    [
      new PointerEvent('pointerdown', { bubbles: true, cancelable: true }),
      new PointerEvent('pointerup',   { bubbles: true, cancelable: true }),
      new MouseEvent('mousedown',     { bubbles: true, cancelable: true }),
      new MouseEvent('mouseup',       { bubbles: true, cancelable: true }),
      new MouseEvent('click',         { bubbles: true, cancelable: true }),
    ].forEach(e => element.dispatchEvent(e));
  }

  // ─── SHADOW DOM UI (FAB & Top-Layer Popover Modal) ──────────────────────────
  let shadowRoot = null;

  function initUI() {
    let host = document.getElementById('px-root');
    if (!host) {
      host = document.createElement('div');
      host.id = 'px-root';
      document.body.appendChild(host);
    }

    shadowRoot = host.shadowRoot || host.attachShadow({ mode: 'open' });
    shadowRoot.innerHTML = `
      <style>${SHADOW_STYLES}</style>
      <button id="px-fab" title="Open Settings" popovertarget="px-dialog">⚙️</button>
      <dialog id="px-dialog" popover="auto">
        <h3 style="margin-top:0">Userscript Settings</h3>
        <div class="px-row">
          <label for="px-enabled">Enabled</label>
          <input type="checkbox" id="px-enabled" ${readConfig('ENABLED', DEFAULTS.ENABLED) ? 'checked' : ''} />
        </div>
        <div style="display:flex;justify-content:flex-end;margin-top:16px;">
          <button id="px-save-btn" class="px-btn px-btn-primary">Save</button>
        </div>
      </dialog>
      <div id="px-toast-container" class="px-toast-container"></div>
    `;

    shadowRoot.getElementById('px-save-btn').addEventListener('click', () => {
      const isChecked = shadowRoot.getElementById('px-enabled').checked;
      writeConfig('ENABLED', isChecked);
      showToast('Settings saved');
      const dialog = shadowRoot.getElementById('px-dialog');
      if (dialog.hidePopover) dialog.hidePopover();
      run();
    });
  }

  function showToast(message, durationMs = 2500) {
    if (!shadowRoot) return;
    const container = shadowRoot.getElementById('px-toast-container');
    const toast = document.createElement('div');
    toast.className = 'px-toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('fade-out');
      toast.addEventListener('transitionend', () => toast.remove());
    }, durationMs);
  }

  // ─── CORE FEATURE LOGIC ─────────────────────────────────────────────────────
  let logicLock = false;
  let lastActionTime = 0;

  function performLogic() {
    if (!readConfig('ENABLED', DEFAULTS.ENABLED)) return;

    // Target elements discovered in RESEARCH_LOG.md
    const target = document.querySelector('.target-class');
    if (target && isVisible(target) && !target.dataset.pxProcessed) {
      target.dataset.pxProcessed = 'true';
      dispatchClickEvents(target);
      log('Action performed on target.');
    }
  }

  function run() {
    if (logicLock) return;
    const delay = readConfig('ACTION_DELAY_MS', DEFAULTS.ACTION_DELAY_MS);
    if (Date.now() - lastActionTime < delay) return;

    logicLock = true;
    try {
      performLogic();
      lastActionTime = Date.now();
    } catch (e) {
      err('run() failed:', e);
    } finally {
      logicLock = false;
    }
  }

  // ─── ORCHESTRATION ──────────────────────────────────────────────────────────
  function resetRouteState() {
    log('Resetting state for route:', location.href);
    logicLock = false;
    lastActionTime = 0;
    run();
  }

  if (self.navigation?.addEventListener) {
    self.navigation.addEventListener('navigatesuccess', resetRouteState);
  }

  let debounceTimer = null;
  let lastUrl = location.href;

  const observer = new MutationObserver(() => {
    try {
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        resetRouteState();
      }
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(run, DEFAULTS.OBSERVER_DEBOUNCE_MS);
    } catch (e) {
      err('Observer error:', e);
    }
  });

  // Observe only DOM structure changes — never script-owned attributes
  observer.observe(document.documentElement, { childList: true, subtree: true });

  // Initialize UI & perform initial pass
  initUI();
  run();

  // Safety net interval
  setInterval(run, 5000);
})();
