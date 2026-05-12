// ==UserScript==
// @name         Perplexity Auto Approve
// @namespace    https://github.com/tazztone/scripts
// @version      0.4.5
// @description  Automatically clicks the Approve button on Perplexity agent action cards. Includes visual countdown, hover-to-pause, and auto-enables the GitHub connector.
// @author       tazztone
// @match        https://www.perplexity.ai/*
// @match        https://perplexity.ai/*
// @run-at       document-idle
// @grant        none
// @noframes
// ==/UserScript==

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const CONFIG = {
  AUTO_APPROVE: true,
  AUTO_ENABLE_GITHUB: true,
  CLICK_DELAY_MS: 3000,
  APPROVE_TEXTS: ['approve', 'confirm', 'allow'],
  OBSERVER_DEBOUNCE_MS: 150,
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
// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  // Inject styles
  const styleEl = document.createElement('style');
  styleEl.textContent = STYLE;
  document.head.appendChild(styleEl);

  const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();

  function isVisible(el) {
    if (!document.contains(el)) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && el.getBoundingClientRect().width > 0;
  }

  // --- CONNECTOR LOGIC ---

  let githubEnableAttempted = false;
  let lastUrl = location.href;

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

  async function ensureGithubEnabledViaMenu() {
    if (!CONFIG.AUTO_ENABLE_GITHUB || isGithubEnabled() || githubEnableAttempted) return;

    // Try to find the + button by multiple selectors
    const attachBtn = document.querySelector([
      'button[aria-label="Add files or tools"]',
      'button[aria-label="Add"]',
      'button[aria-label*="attach" i]',
      'button[aria-label*="add" i]',
      'button:has(svg[data-icon="plus"])',
      'button:has(svg path[d*="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"])',
    ].join(', '));
    if (!attachBtn) return;

    // Prevent multiple attempts once we found the button
    githubEnableAttempted = true;

    attachBtn.click();
    await new Promise(r => setTimeout(r, 400));

    const connectorsMenu = Array.from(document.querySelectorAll('div, button, li, [role="menuitem"]'))
      .filter(el => {
        const txt = el.textContent.trim().toLowerCase();
        return (txt.startsWith('connectors') || txt.includes('connectors and sources')) && isVisible(el);
      })
      .sort((a, b) => a.textContent.length - b.textContent.length)[0];
    if (!connectorsMenu) return;

    // Use correct event constructors — required for React/Radix components
    ['pointerenter', 'pointermove', 'mouseover', 'mouseenter'].forEach(type => {
      const EventClass = type.startsWith('pointer') ? PointerEvent : MouseEvent;
      connectorsMenu.dispatchEvent(new EventClass(type, { bubbles: true, cancelable: true }));
    });
    await new Promise(r => setTimeout(r, 400));

    // Find and click the GitHub checkbox
    const githubItem = Array.from(document.querySelectorAll('div, button, span, [role="menuitem"], [role="option"], [role="menuitemcheckbox"]'))
      .find(el => normalize(el.textContent) === 'github' && isVisible(el));
    
    if (githubItem) {
      // Check if it's already enabled via aria-checked to avoid toggling it OFF
      const checkbox = githubItem.querySelector('[role="checkbox"], [aria-checked]');
      const isAlreadyOn = githubItem.getAttribute('aria-checked') === 'true' || 
                         (checkbox && checkbox.getAttribute('aria-checked') === 'true');
      
      if (!isAlreadyOn) {
        githubItem.click();
        console.log('[Perplexity Auto Approve] GitHub enabled via menu.');
      } else {
        console.log('[Perplexity Auto Approve] GitHub is already enabled.');
      }
    }

    // Close menu by pressing Escape
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  }

  function tryClickSuggestionPill() {
    if (!CONFIG.AUTO_ENABLE_GITHUB || isGithubEnabled()) return false;
    
    // Look for the "Enable GitHub" suggestion pill
    const buttons = Array.from(document.querySelectorAll('button'));
    const pill = buttons.find(el => {
      const text = normalize(el.textContent);
      if (!text.includes('github')) return false;
      if (!isVisible(el)) return false;
      
      // DETECTION: Suggestion pills have specific features:
      // 1. Dashed border (characteristic of "Add" suggestions on PPLX)
      const isDashed = el.classList.contains('border-dashed') || 
                       window.getComputedStyle(el).borderStyle === 'dashed';
      
      // 2. Contains a plus icon (either as a path or a use-ref)
      const hasPlusIcon = el.querySelector('use[xlink\\:href*="plus"]') || 
                          el.querySelector('svg path[d*="M12 5l0 14 M5 12l14 0"]') ||
                          el.querySelector('svg path[d*="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"]') ||
                          el.textContent.includes('+');
      
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

  let connectorLogicLock = false;

  async function run() {
    if (lastUrl !== location.href) {
      lastUrl = location.href;
      githubEnableAttempted = false;
    }

    if (CONFIG.AUTO_APPROVE) {
      findApproveButtons().forEach(scheduleClick);
    }
    
    if (CONFIG.AUTO_ENABLE_GITHUB && !isGithubEnabled() && !connectorLogicLock) {
      connectorLogicLock = true;
      try {
        if (!tryClickSuggestionPill()) {
          await ensureGithubEnabledViaMenu();
        }
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

  observer.observe(document.documentElement, { childList: true, subtree: true });
  run();
})();
