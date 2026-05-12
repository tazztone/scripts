// ==UserScript==
// @name         Perplexity Auto Approve
// @namespace    https://github.com/tazztone/scripts
// @version      0.3.0
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
  CLICK_DELAY_MS: 3000, // Increased to 3s to make countdown visible
  APPROVE_TEXTS: ['approve', 'confirm', 'allow'],
  CHECK_INTERVAL_MS: 1000,
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
    const activeConnectors = document.querySelectorAll('[data-testid="message-input-active-connectors"], .flex.items-center.gap-x-2');
    return Array.from(activeConnectors).some(el => el.textContent.toLowerCase().includes('github') || el.querySelector('svg path[d*="M12 2C6.477 2 2 6.477 2 12c0 4.419 2.865 8.166 6.839 9.489"]'));
  }

  async function ensureGithubEnabled() {
    if (!CONFIG.AUTO_ENABLE_GITHUB || isGithubEnabled()) return;
    
    // Prevent infinite loops in SPA
    githubEnableAttempted = true;

    // Alternative Method: Try to click the suggestion pill if it appears above input
    const suggestionPills = Array.from(document.querySelectorAll('button')).filter(el => normalize(el.textContent).includes('github'));
    const suggestion = suggestionPills.find(el => isVisible(el));
    if (suggestion) {
      suggestion.click();
      console.log('[Perplexity Auto Approve] GitHub connector enabled via suggestion pill.');
      return;
    }

    // Method 1: Menu Sequence
    const attachBtn = document.querySelector('button[aria-label*="Attach"], button:has(svg[data-icon="plus"])');
    if (!attachBtn) return;
    
    attachBtn.click();
    await new Promise(r => setTimeout(r, 300));

    const connectorsMenu = Array.from(document.querySelectorAll('div, button, li')).find(el => el.textContent.includes('Connectors and sources'));
    if (!connectorsMenu) return;
    
    // Hover over connectors menu to open flyout
    connectorsMenu.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    connectorsMenu.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
    await new Promise(r => setTimeout(r, 300));

    // Find and click the GitHub checkbox
    const githubItem = Array.from(document.querySelectorAll('div, button, span')).find(el => normalize(el.textContent) === 'github');
    if (githubItem) {
      githubItem.click();
      console.log('[Perplexity Auto Approve] GitHub connector enabled via menu.');
    }

    // Close menu by clicking backdrop or escape
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
  }

  // --- APPROVE LOGIC ---

  const activeTimers = new Map();

  function findApproveButtons() {
    const allButtons = [...document.querySelectorAll('button, [role="button"]')];
    
    // Debug: Log all visible buttons if we can't find an approve button
    const approveButtons = allButtons.filter(
      (el) => {
        const text = normalize(el.textContent);
        const isMatch = CONFIG.APPROVE_TEXTS.some(t => text.startsWith(t));
        const visible = isVisible(el);
        const notClicked = !el.dataset.pxAutoClicked;
        
        return isMatch && !el.disabled && el.getAttribute('aria-disabled') !== 'true' && notClicked && visible;
      }
    );

    if (approveButtons.length > 0) {
      console.log('[Perplexity Auto Approve] Found buttons:', approveButtons.map(b => b.textContent));
    }
    
    return approveButtons;
  }

  function scheduleClick(btn) {
    if (activeTimers.has(btn)) return;

    btn.dataset.pxAutoClicked = '1';
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
      if (isPaused) return;
      timeLeft -= 100;
      updateUI();
      if (timeLeft <= 0) {
        clearInterval(timer);
        btn.click();
        console.log('[Perplexity Auto Approve] Clicked.');
      }
    };

    const timer = setInterval(tick, 100);
    activeTimers.set(btn, timer);

    btn.onmouseenter = () => {
      isPaused = true;
      btn.classList.add('px-paused');
    };
    btn.onmouseleave = () => {
      isPaused = false;
      btn.classList.remove('px-paused');
    };
  }

  function run() {
    if (lastUrl !== location.href) {
      lastUrl = location.href;
      githubEnableAttempted = false;
    }

    if (CONFIG.AUTO_APPROVE) {
      findApproveButtons().forEach(scheduleClick);
    }
    if (CONFIG.AUTO_ENABLE_GITHUB && !githubEnableAttempted) {
      ensureGithubEnabled();
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

