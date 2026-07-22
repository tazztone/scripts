// ==UserScript==
// @name         Perplexity Auto Approve
// @namespace    https://github.com/tazztone/scripts
// @version      0.5.0
// @description  Automatically clicks the Approve button on Perplexity agent action cards. Includes visual countdown, hover-to-pause, and auto-enables the GitHub connector.
// @author       tazztone
// @match        https://www.perplexity.ai/*
// @match        https://perplexity.ai/*
// @run-at       document-idle
// @grant        GM_getValue
// @grant        GM_setValue
// @noframes
// ==/UserScript==

// ─── CONFIG DEFAULT VALUES ───────────────────────────────────────────────────
const DEFAULTS = {
  AUTO_APPROVE: true,
  AUTO_ENABLE_GITHUB: true,
  CLICK_DELAY_MS: 3000,
  APPROVE_TEXTS: ['approve', 'confirm', 'allow'],
  OBSERVER_DEBOUNCE_MS: 150,
  DEBUG: true
};

// CSS for the visual countdown
const STYLE = `
  .px-auto-approve-btn {
    position: relative !important;
    overflow: hidden !important;
  }
  .px-progress-bar {
    position: absolute;
    top: 0;
    left: 0;
    height: 4px;
    background: #00cc66;
    width: 100%;
    transform-origin: left;
    transition: transform linear;
    z-index: 10;
    pointer-events: none;
  }
  .px-paused .px-progress-bar {
    background: #ffa500 !important;
    animation-play-state: paused !important;
  }
`;

const MODAL_STYLES = `
  #px-settings-fab {
    position: fixed;
    bottom: 8px;
    right: 8px;
    width: 50px;
    height: 50px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 50%;
    background: rgba(30, 41, 59, 0.8);
    color: #f1f5f9;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    cursor: pointer;
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
  }
  #px-settings-fab svg {
    display: block;
    width: 24px;
    height: 24px;
  }
  #px-settings-fab:hover {
    background: rgba(59, 130, 246, 0.9);
    box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
    transform: scale(1.1);
  }
  #px-settings-modal-backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 99998;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
  }
  #px-settings-modal-backdrop.open {
    opacity: 1;
    pointer-events: auto;
  }
  #px-settings-modal {
    width: 90%;
    max-width: 480px;
    max-height: 80vh;
    overflow-y: auto;
    padding: 24px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    background: rgba(30, 41, 59, 0.92);
    color: #f8fafc;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    transform: scale(0.95) translateY(10px);
    transition: transform 0.3s ease;
  }
  #px-settings-modal-backdrop.open #px-settings-modal {
    transform: scale(1) translateY(0);
  }
  #px-settings-modal h3 {
    margin: 0 0 20px;
    color: #60a5fa;
    font-size: 18px;
  }
  .px-settings-section {
    padding-bottom: 8px;
    margin-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
  .px-settings-section h4 {
    margin: 0 0 16px;
    color: #60a5fa;
    font-size: 13px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
  .px-settings-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 18px;
  }
  .px-settings-group label {
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 600;
  }
  .px-settings-group input[type="text"],
  .px-settings-group input[type="number"] {
    box-sizing: border-box;
    width: 100%;
    min-height: 34px;
    padding: 6px 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.6);
    color: #fff;
  }
  .px-settings-group input[type="range"] {
    width: 100%;
    accent-color: #3b82f6;
  }
  .px-switch-container {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
  .px-switch {
    width: 44px;
    height: 24px;
    position: relative;
  }
  .px-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }
  .px-slider {
    position: absolute;
    inset: 0;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 24px;
    background: rgba(15, 23, 42, 0.6);
    cursor: pointer;
  }
  .px-slider::before {
    content: "";
    position: absolute;
    left: 3px;
    bottom: 3px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #94a3b8;
    transition: transform 0.3s ease;
  }
  .px-switch input:checked + .px-slider {
    background: #3b82f6;
  }
  .px-switch input:checked + .px-slider::before {
    transform: translateX(20px);
    background: #fff;
  }
  .px-modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
  }
  .px-btn {
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }
  .px-btn-secondary {
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: transparent;
    color: #94a3b8;
  }
  .px-btn-primary {
    border: 0;
    background: linear-gradient(135deg, #60a5fa, #2563eb);
    color: #fff;
  }
`;
// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  const getValue = (key, fallback) => {
    try {
      if (typeof GM_getValue !== 'undefined') return GM_getValue(key, fallback);
    } catch (e) {}
    try {
      const value = localStorage.getItem(`px_auto_approve_${key}`);
      return value === null ? fallback : JSON.parse(value);
    } catch (e) {}
    return fallback;
  };

  const setValue = (key, value) => {
    try {
      if (typeof GM_setValue !== 'undefined') {
        GM_setValue(key, value);
        return;
      }
    } catch (e) {}
    try {
      localStorage.setItem(`px_auto_approve_${key}`, JSON.stringify(value));
    } catch (e) {}
  };

  const CONFIG = {
    get AUTO_APPROVE() { return getValue('AUTO_APPROVE', DEFAULTS.AUTO_APPROVE); },
    set AUTO_APPROVE(value) { setValue('AUTO_APPROVE', value); },
    get AUTO_ENABLE_GITHUB() { return getValue('AUTO_ENABLE_GITHUB', DEFAULTS.AUTO_ENABLE_GITHUB); },
    set AUTO_ENABLE_GITHUB(value) { setValue('AUTO_ENABLE_GITHUB', value); },
    get CLICK_DELAY_MS() { return parseInt(getValue('CLICK_DELAY_MS', DEFAULTS.CLICK_DELAY_MS)); },
    set CLICK_DELAY_MS(value) { setValue('CLICK_DELAY_MS', parseInt(value)); },
    get APPROVE_TEXTS() { return getValue('APPROVE_TEXTS', DEFAULTS.APPROVE_TEXTS); },
    get OBSERVER_DEBOUNCE_MS() { return parseInt(getValue('OBSERVER_DEBOUNCE_MS', DEFAULTS.OBSERVER_DEBOUNCE_MS)); },
    get DEBUG() { return getValue('DEBUG', DEFAULTS.DEBUG); }
  };

  // Inject styles
  if (!document.getElementById('px-auto-approve-style')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'px-auto-approve-style';
    styleEl.textContent = STYLE;
    document.head.appendChild(styleEl);
  }
  if (!document.getElementById('px-settings-style')) {
    const settingsStyle = document.createElement('style');
    settingsStyle.id = 'px-settings-style';
    settingsStyle.textContent = MODAL_STYLES;
    document.head.appendChild(settingsStyle);
  }

  const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();

  function isVisible(el) {
    if (!document.contains(el)) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && el.getBoundingClientRect().width > 0;
  }

  // --- CONNECTOR LOGIC ---

  function isGithubEnabled() {
    // 1. Check for the solid GitHub pill button (active connector) in the input area
    // Active connectors have aria-haspopup="menu" and a solid border/background.
    const activePill = Array.from(document.querySelectorAll('button[aria-haspopup="menu"], button[aria-expanded]'))
      .find(el => normalize(el.textContent).includes('github') && isVisible(el));
    if (activePill) return true;

    // 2. Check for the GitHub icon image in the active connectors area
    if (document.querySelector('[data-testid="message-input-active-connectors"] img[alt*="GitHub"]')) return true;

    // 3. Legacy check for specific SVG path (GitHub logo)
    return !!document.querySelector('svg path[d*="M12 2C6.477 2 2 6.477 2 12c0 4.419 2.865 8.166 6.839 9.489"]');
  }

  function tryClickSuggestionPill() {
    if (!CONFIG.AUTO_ENABLE_GITHUB || isGithubEnabled()) return false;
    
    // Look for the "Enable GitHub" suggestion pill
    const buttons = Array.from(document.querySelectorAll('button'));
    const pill = buttons.find(el => {
      const text = normalize(el.textContent);
      
      // Strict matching to avoid clicking search suggestions that contain the word "github"
      const exactMatches = ['github', '+ github', 'github +', 'add github', 'enable github'];
      if (!exactMatches.includes(text)) return false;

      if (!isVisible(el)) return false;
      
      // DETECTION: Suggestion pills have specific features:
      // 1. Dashed border (characteristic of "Add" suggestions on PPLX)
      const isDashed = el.classList.contains('border-dashed') || 
                       window.getComputedStyle(el).borderStyle === 'dashed';
      
      // 2. Contains a plus icon (either as a path or a use-ref)
      const hasPlusIcon = el.querySelector('use[xlink\\:href*="plus"]') || 
                          el.querySelector('svg path[d*="M12 5l0 14 M5 12l14 0"]') ||
                          el.querySelector('svg path[d*="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"]');
      
      // EXCLUSION: 
      // 1. Ignore active connectors (they have aria-haspopup="menu")
      const isActiveConnector = el.getAttribute('aria-haspopup') === 'menu';
      // 2. Ignore Follow-ups (full-width rows)
      const isFullWidthRow = el.offsetWidth > 500;
      
      return (isDashed || hasPlusIcon) && !isActiveConnector && !isFullWidthRow;
    });

    if (pill) {
      pill.click();
      console.log('[Perplexity Auto Approve] GitHub enabled via suggestion pill.');
      return true;
    }
    return false;
  }

  // --- APPROVE LOGIC ---

  const activeTimers = new Map();

  function findApproveButtons() {
    const allButtons = [...document.querySelectorAll('button, [role="button"]')];
    const approveButtons = allButtons.filter((el) => {
      const text = normalize(el.textContent);
      const isMatch = CONFIG.APPROVE_TEXTS.some(t => text.startsWith(t));
      const visible = isVisible(el);
      const notScheduled = !activeTimers.has(el) && !el.dataset.pxClicked;
      return isMatch && !el.disabled && el.getAttribute('aria-disabled') !== 'true' && notScheduled && visible;
    });

    if (approveButtons.length > 0) {
      console.log('[Perplexity Auto Approve] Found buttons:', approveButtons.map(b => b.textContent));
    }

    return approveButtons;
  }

  function scheduleClick(btn) {
    if (activeTimers.has(btn)) return;

    btn.classList.add('px-auto-approve-btn');

    const progressBar = document.createElement('div');
    progressBar.className = 'px-progress-bar';
    progressBar.style.transform = 'scaleX(1)';
    btn.appendChild(progressBar);

    let timeLeft = CONFIG.CLICK_DELAY_MS;
    let isPaused = false;

    const updateUI = () => {
      const scale = timeLeft / CONFIG.CLICK_DELAY_MS;
      progressBar.style.transform = `scaleX(${scale})`;
    };

    const tick = () => {
      // If button was removed from DOM, clean up and abort
      if (!isVisible(btn)) {
        clearInterval(timer);
        activeTimers.delete(btn);
        return;
      }
      if (isPaused) return;
      timeLeft -= 100;
      updateUI();
      if (timeLeft <= 0) {
        clearInterval(timer);
        activeTimers.delete(btn);
        btn.dataset.pxClicked = '1';
        btn.click();
        console.log('[Perplexity Auto Approve] Clicked.');
      }
    };

    const timer = setInterval(tick, 100);
    activeTimers.set(btn, timer);

    btn.addEventListener('mouseenter', () => {
      isPaused = true;
      btn.classList.add('px-paused');
    });
    btn.addEventListener('mouseleave', () => {
      isPaused = false;
      btn.classList.remove('px-paused');
    });
  }

  function cancelScheduledClicks() {
    activeTimers.forEach((timer, btn) => {
      clearInterval(timer);
      btn.classList.remove('px-auto-approve-btn', 'px-paused');
      btn.querySelector('.px-progress-bar')?.remove();
    });
    activeTimers.clear();
  }

  function ensureSettingsSkeleton() {
    if (document.getElementById('px-settings-fab')) return;

    const container = document.createElement('div');
    container.innerHTML = `
      <button id="px-settings-fab" type="button" title="Configure Perplexity enhancements" aria-label="Configure Perplexity enhancements">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924-1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543-.94-3.31.826-2.37 2.37a1.724 1.724 0 001.065-2.572c-1.756-.426-2.924-2.37 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543-.826-2.37 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
      <div id="px-settings-modal-backdrop">
        <div id="px-settings-modal" role="dialog" aria-modal="true" aria-labelledby="px-settings-title">
          <h3 id="px-settings-title">Perplexity Enhancements</h3>
          <div id="px-settings-sections"></div>
          <div class="px-modal-actions">
            <button type="button" class="px-btn px-btn-secondary" id="px-btn-close">Cancel</button>
            <button type="button" class="px-btn px-btn-primary" id="px-btn-save">Save Settings</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(container);

    const fab = document.getElementById('px-settings-fab');
    fab.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>';
    const backdrop = document.getElementById('px-settings-modal-backdrop');
    const close = () => backdrop.classList.remove('open');
    document.getElementById('px-btn-close').addEventListener('click', close);
    backdrop.addEventListener('click', event => {
      if (event.target === backdrop) close();
    });
    fab.addEventListener('click', () => {
      document.dispatchEvent(new CustomEvent('px-settings-open'));
      backdrop.classList.add('open');
    });
    document.getElementById('px-btn-save').addEventListener('click', () => {
      document.dispatchEvent(new CustomEvent('px-settings-save'));
      close();
    });
  }

  function setupSettingsUI() {
    ensureSettingsSkeleton();
    if (document.getElementById('px-section-auto-approve')) return;

    const sections = document.getElementById('px-settings-sections');
    const container = document.createElement('div');
    container.innerHTML = `
      <section class="px-settings-section" id="px-section-auto-approve">
        <h4>Auto Approve</h4>
        <div class="px-settings-group px-switch-container">
          <label for="px-auto-approve-enabled">Auto-approve actions</label>
          <label class="px-switch">
            <input id="px-auto-approve-enabled" type="checkbox">
            <span class="px-slider"></span>
          </label>
        </div>
        <div class="px-settings-group px-switch-container">
          <label for="px-auto-approve-github">Auto-enable GitHub</label>
          <label class="px-switch">
            <input id="px-auto-approve-github" type="checkbox">
            <span class="px-slider"></span>
          </label>
        </div>
        <div class="px-settings-group" id="px-auto-approve-delay-group">
          <label for="px-auto-approve-delay-range">Approval countdown (seconds)</label>
          <input id="px-auto-approve-delay-range" type="range" min="1" max="30" step="1">
          <input id="px-auto-approve-delay-value" type="number" min="1" max="30" step="1">
        </div>
      </section>
    `;
    sections.appendChild(container.firstElementChild);

    const autoApprove = document.getElementById('px-auto-approve-enabled');
    const autoGithub = document.getElementById('px-auto-approve-github');
    const delayRange = document.getElementById('px-auto-approve-delay-range');
    const delayValue = document.getElementById('px-auto-approve-delay-value');
    const delayGroup = document.getElementById('px-auto-approve-delay-group');

    const updateControls = isEnabled => {
      delayGroup.style.opacity = isEnabled ? '1' : '0.4';
      delayGroup.querySelectorAll('input').forEach(input => { input.disabled = !isEnabled; });
    };
    const syncFields = () => {
      autoApprove.checked = CONFIG.AUTO_APPROVE;
      autoGithub.checked = CONFIG.AUTO_ENABLE_GITHUB;
      const seconds = Math.round(CONFIG.CLICK_DELAY_MS / 1000);
      delayRange.value = seconds;
      delayValue.value = seconds;
      updateControls(CONFIG.AUTO_APPROVE);
    };

    delayRange.addEventListener('input', event => { delayValue.value = event.target.value; });
    delayValue.addEventListener('input', event => { delayRange.value = event.target.value; });
    autoApprove.addEventListener('change', event => updateControls(event.target.checked));
    document.addEventListener('px-settings-open', syncFields);
    document.addEventListener('px-settings-save', () => {
      const seconds = Math.max(1, Math.min(30, parseInt(delayValue.value) || 3));
      CONFIG.AUTO_APPROVE = autoApprove.checked;
      CONFIG.AUTO_ENABLE_GITHUB = autoGithub.checked;
      CONFIG.CLICK_DELAY_MS = seconds * 1000;
      cancelScheduledClicks();
      run();
    });
    syncFields();
  }

  let connectorLogicLock = false;

  function run() {
    if (CONFIG.AUTO_APPROVE) {
      findApproveButtons().forEach(scheduleClick);
    }
    
    if (CONFIG.AUTO_ENABLE_GITHUB && !isGithubEnabled() && !connectorLogicLock) {
      connectorLogicLock = true;
      try {
        tryClickSuggestionPill();
      } finally {
        // Cooldown to prevent loops during UI transitions
        setTimeout(() => { connectorLogicLock = false; }, 2000);
      }
    }
  }

  let debounceTimer = null;
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(run, CONFIG.OBSERVER_DEBOUNCE_MS);
  });

  setupSettingsUI();
  observer.observe(document.documentElement, { childList: true, subtree: true });
  run();
})();
