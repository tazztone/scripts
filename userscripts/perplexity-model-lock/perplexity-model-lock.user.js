// ==UserScript==
// @name         Perplexity Model Lock
// @namespace    https://github.com/tazztone/scripts
// @version      1.0.3
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

  // --- ORCHESTRATION ---

  let isInteracting = false;
  let lastSelectionTime = 0;

  function run() {
    try {
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
  observer.observe(document.documentElement, { childList: true, subtree: true });
  run();
  
  // Periodic safety check
  setInterval(run, 5000);
})();
