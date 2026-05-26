// ==UserScript==
// @name         Perplexity Model Lock
// @namespace    https://github.com/tazztone/scripts
// @version      1.0.0
// @description  Automatically selects Claude Sonnet 4.6 and enables Thinking mode on Perplexity.ai when the site resets it.
// @author       tazztone
// @match        https://www.perplexity.ai/*
// @match        https://perplexity.ai/*
// @run-at       document-idle
// @grant        none
// @noframes
// ==/UserScript==

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const CONFIG = {
  TARGET_MODEL: 'Claude Sonnet 4.6', // Case-insensitive model name to select
  ENABLE_THINKING: true,              // Whether to ensure "Thinking" mode is enabled
  OBSERVER_DEBOUNCE_MS: 150,          // Debounce for DOM mutation reactions
  COOLDOWN_MS: 3000,                  // Cooldown after an auto-lock operation to prevent loops
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
// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  // Inject styles
  const styleEl = document.createElement('style');
  styleEl.textContent = STYLE;
  document.head.appendChild(styleEl);

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
    const allButtons = Array.from(document.querySelectorAll('button'));
    const keywords = ['best', 'sonar', 'gpt-5.4', 'gpt-5.5', 'gemini 3.1', 'claude sonnet', 'claude opus', 'gpt-', 'gemini', 'claude'];
    
    return allButtons.find(btn => {
      if (!isVisible(btn)) return false;
      const text = normalize(btn.textContent);
      
      // Exclude active tools/connectors (e.g. GitHub connector, attachment buttons)
      if (text.includes('github') || text.includes('files or tools') || text.includes('attach')) {
        return false;
      }
      
      return keywords.some(keyword => text.includes(keyword));
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
    const candidates = Array.from(document.querySelectorAll('[role="menuitem"], [role="option"], button, div'));
    
    for (const el of candidates) {
      if (!isVisible(el)) continue;
      if (triggerBtn && (triggerBtn === el || triggerBtn.contains(el))) continue;
      
      const text = normalize(el.textContent);
      
      // Ensure we target a discrete list option row rather than the whole dropdown panel
      const rect = el.getBoundingClientRect();
      if (rect.height > 80 || rect.width > 400) continue;
      
      if (text === targetNormalized || text.startsWith(targetNormalized)) {
        return el;
      }
    }
    return null;
  }

  function findDropdownThinkingRow() {
    const triggerBtn = findModelButton();
    const candidates = Array.from(document.querySelectorAll('[role="menuitem"], button, div'));
    
    for (const el of candidates) {
      if (!isVisible(el)) continue;
      if (triggerBtn && (triggerBtn === el || triggerBtn.contains(el))) continue;
      
      const text = normalize(el.textContent);
      
      // Ensure we target a discrete row rather than the whole dropdown panel
      const rect = el.getBoundingClientRect();
      if (rect.height > 80 || rect.width > 400) continue;
      
      if (text === 'thinking' || text.startsWith('thinking')) {
        return el;
      }
    }
    return null;
  }

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

  // --- ORCHESTRATION ---

  let isInteracting = false;
  let lastInteractionTime = 0;

  function run() {
    try {
      const now = Date.now();
      // Skip logic if we are actively interacting or inside a cooldown period
      if (isInteracting || (now - lastInteractionTime < CONFIG.COOLDOWN_MS)) {
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
        
        setTimeout(() => {
          isInteracting = false;
          lastInteractionTime = Date.now();
        }, 500); // 500ms lock for menu rendering
        return;
      }
      
      // Dropdown menu is currently open
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
      
      // Release logic lock and start the cooldown to avoid flickering
      setTimeout(() => {
        isInteracting = false;
        lastInteractionTime = Date.now();
        log('Interaction completed, locking model state.');
      }, 800); // 800ms cooldown for selections to commit and menu to close
      
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
    lastInteractionTime = 0;
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
  observer.observe(document.documentElement, { childList: true, subtree: true });
  run();
  
  // Periodic safety check
  setInterval(run, 5000);
})();
