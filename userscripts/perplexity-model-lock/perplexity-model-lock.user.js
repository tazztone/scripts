// ==UserScript==
// @name         Perplexity Model Lock
// @namespace    https://github.com/tazztone/scripts
// @version      1.1.0
// @description  Automatically selects Claude Sonnet 4.6 and enables Thinking mode on Perplexity.ai when the site resets it.
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
  ENABLED: true,
  TARGET_MODEL: 'Claude Sonnet 4.6', // Case-insensitive model name to select
  ENABLE_THINKING: true,              // Whether to ensure "Thinking" mode is enabled
  OBSERVER_DEBOUNCE_MS: 150,          // Debounce for DOM mutation reactions
  COOLDOWN_MS: 3000,                  // Cooldown after an auto-lock selection to prevent loops
  DEBUG: true                         // Log debug info to console
};

// CSS for the visual indicator
const STYLE = `
  .px-model-lock-indicator {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
    margin-left: 8px;
    vertical-align: middle;
    transition: all 0.3s ease;
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
      const value = localStorage.getItem(`px_model_lock_${key}`);
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
      localStorage.setItem(`px_model_lock_${key}`, JSON.stringify(value));
    } catch (e) {}
  };

  const CONFIG = {
    get ENABLED() { return getValue('ENABLED', DEFAULTS.ENABLED); },
    set ENABLED(value) { setValue('ENABLED', value); },
    get TARGET_MODEL() { return getValue('TARGET_MODEL', DEFAULTS.TARGET_MODEL); },
    set TARGET_MODEL(value) { setValue('TARGET_MODEL', value); },
    get ENABLE_THINKING() { return getValue('ENABLE_THINKING', DEFAULTS.ENABLE_THINKING); },
    set ENABLE_THINKING(value) { setValue('ENABLE_THINKING', value); },
    get OBSERVER_DEBOUNCE_MS() { return parseInt(getValue('OBSERVER_DEBOUNCE_MS', DEFAULTS.OBSERVER_DEBOUNCE_MS)); },
    get COOLDOWN_MS() { return parseInt(getValue('COOLDOWN_MS', DEFAULTS.COOLDOWN_MS)); },
    get DEBUG() { return getValue('DEBUG', DEFAULTS.DEBUG); }
  };

  // Inject styles
  if (!document.getElementById('px-model-lock-style')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'px-model-lock-style';
    styleEl.textContent = STYLE;
    document.head.appendChild(styleEl);
  }
  if (!document.getElementById('px-settings-style')) {
    const settingsStyle = document.createElement('style');
    settingsStyle.id = 'px-settings-style';
    settingsStyle.textContent = MODAL_STYLES;
    document.head.appendChild(settingsStyle);
  }

  // --- UTILITIES ---

  const log = (...args) => {
    if (CONFIG.DEBUG) console.log('[Perplexity Model Lock]', ...args);
  };

  const err = (...args) => {
    console.error('[Perplexity Model Lock] Error:', ...args);
  };

  const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();

  function isVisible(el) {
    if (!document.contains(el)) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && 
           style.visibility !== 'hidden' && 
           style.opacity !== '0' && 
           el.getBoundingClientRect().width > 0;
  }

  // Dispatches robust events for Radix UI / React primitives
  function dispatchClickEvents(el) {
    if (!el) return;
    const events = [
      new PointerEvent('pointerdown', { bubbles: true, cancelable: true }),
      new PointerEvent('pointerup', { bubbles: true, cancelable: true }),
      new MouseEvent('mousedown', { bubbles: true, cancelable: true }),
      new MouseEvent('mouseup', { bubbles: true, cancelable: true }),
      new MouseEvent('click', { bubbles: true, cancelable: true })
    ];
    events.forEach(evt => el.dispatchEvent(evt));
  }

  // --- CORE SELECTION LOGIC ---

  function findModelButton() {
    try {
      // 1. Locate the main search query textarea as the stable anchor
      const textarea = document.querySelector('textarea[placeholder*="Ask"], textarea[placeholder*="anything"], textarea');
      if (!textarea) return findModelButtonKeywordFallback();
      
      // Find the closest shared container (the prompt input box)
      const promptBox = textarea.closest('form') || textarea.parentElement?.closest('div');
      if (!promptBox) return findModelButtonKeywordFallback();
      
      // 2. Scan all visible buttons within the prompt box context
      const buttons = Array.from(promptBox.querySelectorAll('button'));
      
      for (const btn of buttons) {
        if (!isVisible(btn)) continue;
        
        const text = normalize(btn.textContent);
        
        // 3. STRUCTURAL EXCLUSIONS: Ignore obviously non-model action buttons
        if (text.includes('github') || text.includes('attach') || text.includes('focus') || text.includes('search')) {
          continue;
        }
        
        // Filter out Voice/Microphone button
        const hasMicIcon = btn.querySelector('svg path[d*="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3"]') || 
                           btn.getAttribute('aria-label')?.toLowerCase().includes('voice') ||
                           btn.getAttribute('aria-label')?.toLowerCase().includes('dictate') ||
                           btn.querySelector('svg[class*="mic"]');
        if (hasMicIcon) continue;
        
        // Filter out circular Submit/Send button based on square aspect ratio & typical sizes
        const rect = btn.getBoundingClientRect();
        const isCircularSubmit = Math.abs(rect.width - rect.height) < 4 && rect.width < 50;
        const hasSendIcon = btn.querySelector('svg path[d*="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"]') ||
                            btn.querySelector('svg[class*="send"]') ||
                            btn.querySelector('svg[class*="arrow-up"]');
        if (isCircularSubmit || hasSendIcon) continue;
        
        // Filter out simple plus/attachment buttons
        if (text === '+' || text === '') {
          const hasPlusIcon = btn.querySelector('svg path[d*="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"]');
          if (hasPlusIcon) continue;
        }
        
        // 4. POSITIVE STRUCTURAL INDICATORS
        // A. Menu role triggers
        const hasMenuPopup = btn.getAttribute('aria-haspopup') === 'menu' || 
                             btn.getAttribute('aria-haspopup') === 'listbox' ||
                             btn.getAttribute('aria-haspopup') === 'dialog' ||
                             btn.getAttribute('aria-expanded') !== null;
                             
        // B. Contains a dropdown arrow/chevron or SVG icon
        const hasChevron = btn.querySelector('svg path[d*="M6 9l6 6 6-6"]') || 
                           btn.querySelector('svg[class*="chevron"]') ||
                           btn.querySelector('svg[class*="arrow-down"]') ||
                           text.includes('⌵') || 
                           text.includes('▼') ||
                           btn.querySelector('svg'); // any icon if placed next to text
                           
        // C. Model terms fallback reinforcement
        const keywords = ['model', 'best', 'sonar', 'gpt-', 'gemini', 'claude'];
        const hasKeyword = keywords.some(keyword => text.includes(keyword));
        
        if (hasMenuPopup || hasChevron || hasKeyword) {
          return btn;
        }
      }
    } catch (e) {
      err('Error inside structural finder:', e);
    }
    
    // Page-wide fallback
    return findModelButtonKeywordFallback();
  }

  // Page-wide fallback based strictly on model keyword matching
  function findModelButtonKeywordFallback() {
    const allButtons = Array.from(document.querySelectorAll('button'));
    const keywords = ['best', 'sonar', 'gpt-5.4', 'gpt-5.5', 'gemini 3.1', 'claude sonnet', 'claude opus', 'gpt-', 'gemini', 'claude'];
    
    return allButtons.find(btn => {
      if (!isVisible(btn)) return false;
      const text = normalize(btn.textContent);
      
      if (text.includes('github') || text.includes('files or tools') || text.includes('attach')) {
        return false;
      }
      
      const isGenericModelBtn = text === 'model' || text.startsWith('model ') || text.endsWith(' model');
      const matchesKeyword = keywords.some(keyword => text.includes(keyword));
      
      return isGenericModelBtn || matchesKeyword;
    });
  }

  function isTargetStateActive(btn) {
    if (!btn) return false;
    const text = normalize(btn.textContent);
    const targetModelNormalized = normalize(CONFIG.TARGET_MODEL);
    
    const hasModel = text.includes(targetModelNormalized);
    const hasThinking = text.includes('thinking');
    
    if (CONFIG.ENABLE_THINKING) {
      return hasModel && hasThinking;
    } else {
      return hasModel && !hasThinking;
    }
  }

  function findDropdownModelItem(targetModel) {
    const triggerBtn = findModelButton();
    const targetNormalized = normalize(targetModel);
    
    // 1. Look for interactive option roles
    const candidates = Array.from(document.querySelectorAll('[role="menuitem"], [role="option"], [role="menuitemcheckbox"], button, .dropdown-item'));
    for (const el of candidates) {
      if (!isVisible(el)) continue;
      if (triggerBtn && (triggerBtn === el || triggerBtn.contains(el))) continue;
      
      const text = normalize(el.textContent);
      if (text.includes(targetNormalized)) {
        return el;
      }
    }
    
    // 2. Fallback: Search visible divs and pick the deepest leaf node containing the text to avoid parent menu containers
    const divs = Array.from(document.querySelectorAll('div'));
    let bestMatch = null;
    let bestDepth = -1;
    
    for (const el of divs) {
      if (!isVisible(el)) continue;
      if (triggerBtn && (triggerBtn === el || triggerBtn.contains(el))) continue;
      
      const text = normalize(el.textContent);
      if (text.includes(targetNormalized)) {
        let depth = 0;
        let temp = el;
        while (temp.parentElement) {
          depth++;
          temp = temp.parentElement;
        }
        if (depth > bestDepth) {
          bestDepth = depth;
          bestMatch = el;
        }
      }
    }
    
    return bestMatch;
  }

  function findDropdownThinkingRow() {
    const triggerBtn = findModelButton();
    
    // 1. Look for interactive elements
    const candidates = Array.from(document.querySelectorAll('[role="menuitem"], [role="option"], [role="menuitemcheckbox"], button, .dropdown-item'));
    for (const el of candidates) {
      if (!isVisible(el)) continue;
      if (triggerBtn && (triggerBtn === el || triggerBtn.contains(el))) continue;
      
      const text = normalize(el.textContent);
      // Ensure we match "thinking" but skip other model rows containing "thinking" descriptions
      if (text.includes('thinking') && !text.includes('claude') && !text.includes('gpt') && !text.includes('sonar') && !text.includes('gemini')) {
        return el;
      }
    }
    
    // 2. Fallback: Deepest div matching
    const divs = Array.from(document.querySelectorAll('div'));
    let bestMatch = null;
    let bestDepth = -1;
    
    for (const el of divs) {
      if (!isVisible(el)) continue;
      if (triggerBtn && (triggerBtn === el || triggerBtn.contains(el))) continue;
      
      const text = normalize(el.textContent);
      if (text.includes('thinking') && !text.includes('claude') && !text.includes('gpt') && !text.includes('sonar') && !text.includes('gemini')) {
        let depth = 0;
        let temp = el;
        while (temp.parentElement) {
          depth++;
          temp = temp.parentElement;
        }
        if (depth > bestDepth) {
          bestDepth = depth;
          bestMatch = el;
        }
      }
    }
    
    return bestMatch;
  }

  // Helper to determine the state of the switch toggle
  function getSwitchState(rowEl) {
    const switchEl = rowEl.querySelector('button[role="switch"], input[type="checkbox"]');
    if (switchEl) {
      if (switchEl.getAttribute('role') === 'switch') {
        return switchEl.getAttribute('aria-checked') === 'true';
      }
      if (switchEl.type === 'checkbox') {
        return switchEl.checked;
      }
    }
    
    const ariaCheckedEl = rowEl.querySelector('[aria-checked]');
    if (ariaCheckedEl) {
      return ariaCheckedEl.getAttribute('aria-checked') === 'true';
    }
    
    return null; // Unknown state
  }

  function toggleSwitch(rowEl, targetState) {
    const switchEl = rowEl.querySelector('button[role="switch"], input[type="checkbox"]') || rowEl;
    const currentState = getSwitchState(rowEl);
    
    if (currentState !== targetState) {
      log('Toggling thinking switch from', currentState, 'to', targetState);
      dispatchClickEvents(switchEl);
      return true;
    }
    return false;
  }

  function updateStatusIndicator(isLocked, statusText) {
    const btn = findModelButton();
    if (!btn) return;
    
    let indicator = btn.querySelector('.px-model-lock-indicator');
    if (!indicator) {
      indicator = document.createElement('span');
      indicator.className = 'px-model-lock-indicator';
      btn.appendChild(indicator);
    }
    
    if (isLocked) {
      indicator.style.backgroundColor = '#00cc66';
      indicator.style.boxShadow = '0 0 6px #00cc66';
      indicator.title = `Model Lock Active: ${CONFIG.TARGET_MODEL} (Thinking: ${CONFIG.ENABLE_THINKING})`;
    } else {
      indicator.style.backgroundColor = '#ffa500';
      indicator.style.boxShadow = '0 0 6px #ffa500';
      indicator.title = `Model Lock Status: ${statusText}`;
    }
  }

  function removeStatusIndicators() {
    document.querySelectorAll('.px-model-lock-indicator').forEach(indicator => indicator.remove());
  }

  function ensureSettingsSkeleton() {
    if (document.getElementById('px-settings-fab')) return;

    const container = document.createElement('div');
    container.innerHTML = `
      <button id="px-settings-fab" type="button" title="Configure Perplexity enhancements" aria-label="Configure Perplexity enhancements">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543-.826-2.37 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
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
    if (document.getElementById('px-section-model-lock')) return;

    const sections = document.getElementById('px-settings-sections');
    const container = document.createElement('div');
    container.innerHTML = `
      <section class="px-settings-section" id="px-section-model-lock">
        <h4>Model Lock</h4>
        <div class="px-settings-group px-switch-container">
          <label for="px-model-lock-enabled">Enable model lock</label>
          <label class="px-switch">
            <input id="px-model-lock-enabled" type="checkbox">
            <span class="px-slider"></span>
          </label>
        </div>
        <div class="px-settings-group" id="px-model-lock-target-group">
          <label for="px-model-lock-target">Target model</label>
          <input id="px-model-lock-target" type="text" autocomplete="off">
        </div>
        <div class="px-settings-group px-switch-container" id="px-model-lock-thinking-group">
          <label for="px-model-lock-thinking">Enable Thinking mode</label>
          <label class="px-switch">
            <input id="px-model-lock-thinking" type="checkbox">
            <span class="px-slider"></span>
          </label>
        </div>
      </section>
    `;
    sections.appendChild(container.firstElementChild);

    const enabled = document.getElementById('px-model-lock-enabled');
    const target = document.getElementById('px-model-lock-target');
    const thinking = document.getElementById('px-model-lock-thinking');
    const targetGroup = document.getElementById('px-model-lock-target-group');
    const thinkingGroup = document.getElementById('px-model-lock-thinking-group');

    const updateControls = isEnabled => {
      [targetGroup, thinkingGroup].forEach(group => {
        group.style.opacity = isEnabled ? '1' : '0.4';
        group.querySelectorAll('input').forEach(input => { input.disabled = !isEnabled; });
      });
    };
    const syncFields = () => {
      enabled.checked = CONFIG.ENABLED;
      target.value = CONFIG.TARGET_MODEL;
      thinking.checked = CONFIG.ENABLE_THINKING;
      updateControls(CONFIG.ENABLED);
    };

    enabled.addEventListener('change', event => updateControls(event.target.checked));
    document.addEventListener('px-settings-open', syncFields);
    document.addEventListener('px-settings-save', () => {
      CONFIG.ENABLED = enabled.checked;
      CONFIG.TARGET_MODEL = target.value.trim() || DEFAULTS.TARGET_MODEL;
      CONFIG.ENABLE_THINKING = thinking.checked;
      if (!CONFIG.ENABLED) {
        isInteracting = false;
        removeStatusIndicators();
      } else {
        run();
      }
    });
    syncFields();
  }

  // --- ORCHESTRATION ---

  let isInteracting = false;
  let lastSelectionTime = 0;

  function run() {
    try {
      if (!CONFIG.ENABLED) {
        removeStatusIndicators();
        return;
      }
      const now = Date.now();
      // Skip logic if we are actively interacting or inside a selection cooldown
      if (isInteracting || (now - lastSelectionTime < CONFIG.COOLDOWN_MS)) {
        return;
      }
      
      const modelBtn = findModelButton();
      if (!modelBtn) {
        return;
      }
      
      if (isTargetStateActive(modelBtn)) {
        updateStatusIndicator(true, 'Locked');
        return;
      }
      
      log('Target model state not active. Current display:', modelBtn.textContent.trim());
      updateStatusIndicator(false, 'Syncing...');
      
      const dropdownModelItem = findDropdownModelItem(CONFIG.TARGET_MODEL);
      const thinkingRow = findDropdownThinkingRow();
      const isDropdownOpen = !!(dropdownModelItem || thinkingRow);
      
      if (!isDropdownOpen) {
        log('Opening model selection menu...');
        isInteracting = true;
        dispatchClickEvents(modelBtn);
        
        // Brief 300ms lock to let dropdown render, then unlock for the next mutation observer tick
        setTimeout(() => {
          isInteracting = false;
        }, 300);
        return;
      }
      
      // Dropdown menu is currently open
      log('Model dropdown is open. Adjusting state...');
      isInteracting = true;
      let actionTaken = false;
      
      // 1. Toggle Thinking if it is not in the desired state
      if (thinkingRow && CONFIG.ENABLE_THINKING) {
        const currentThinking = getSwitchState(thinkingRow);
        if (currentThinking === false) {
          log('Enabling thinking mode toggle...');
          toggleSwitch(thinkingRow, true);
          actionTaken = true;
        }
      }
      
      // 2. Select the target model
      if (dropdownModelItem) {
        log(`Selecting model: ${CONFIG.TARGET_MODEL}`);
        dispatchClickEvents(dropdownModelItem);
        actionTaken = true;
      }
      
      // Release logic lock and start selection cooldown (800ms buffer for click propagation)
      setTimeout(() => {
        isInteracting = false;
        lastSelectionTime = Date.now();
        log('Interaction completed, locking model state.');
      }, 800);
      
    } catch (errEl) {
      err('Error inside execution run:', errEl);
      isInteracting = false;
    }
  }

  // Debounced MutationObserver to watch SPA DOM updates efficiently
  let debounceTimer = null;
  const observer = new MutationObserver(() => {
    try {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(run, CONFIG.OBSERVER_DEBOUNCE_MS);
    } catch (e) {
      err('Observer callback error:', e);
    }
  });

  // SPA Page Swaps: Reset cooldown and execute immediately on path transitions
  function handleUrlChange() {
    log('SPA Page transition detected, resetting interaction states...');
    isInteracting = false;
    lastSelectionTime = 0;
    run();
  }

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

  // Initialize
  setupSettingsUI();
  observer.observe(document.documentElement, { childList: true, subtree: true });
  run();
  
  // Periodic safety check
  setInterval(run, 5000);
})();
