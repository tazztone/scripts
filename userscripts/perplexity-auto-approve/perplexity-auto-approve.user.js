// ==UserScript==
// @name         Perplexity Auto Approve
// @namespace    https://github.com/tazztone/scripts
// @version      0.2.0
// @description  Automatically clicks the Approve button on Perplexity agent action cards. Uses MutationObserver to handle SPA navigation. Includes a short delay before clicking so you can intervene.
// @author       tazztone
// @match        https://www.perplexity.ai/*
// @match        https://perplexity.ai/*
// @run-at       document-idle
// @grant        none
// @noframes
// ==/UserScript==

// ─── CONFIG ──────────────────────────────────────────────────────────────────
// Set to false to disable auto-click without uninstalling the script.
const AUTO_APPROVE_ENABLED = true;

// Milliseconds to wait after the button is detected before clicking.
// Gives you a window to intervene if needed.
const CLICK_DELAY_MS = 1500;

// Optional: only auto-approve if the card contains one of these strings.
// Leave empty [] to approve ALL action cards regardless of content.
// Example: ["Merge PR", "push files"] — case-insensitive.
const APPROVE_ONLY_IF_CARD_CONTAINS = [];

// Debounce delay for MutationObserver callback (ms).
// Prevents scanning the full DOM on every micro-mutation in a busy React app.
const OBSERVER_DEBOUNCE_MS = 150;
// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();

  // Treat both native disabled and aria-disabled="true" as disabled.
  function isDisabled(el) {
    return el.disabled || el.getAttribute('aria-disabled') === 'true';
  }

  // Check element is visible in the viewport (not hidden via CSS).
  function isVisible(el) {
    if (!document.contains(el)) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  // Walk up to 6 ancestors looking for a card/dialog container.
  // Falls back to gathering text from the button's siblings if no container found.
  function getCardText(btn) {
    let node = btn.parentElement;
    for (let i = 0; i < 6 && node && node !== document.body; i++) {
      const role = (node.getAttribute('role') || '').toLowerCase();
      if (
        role === 'dialog' ||
        role === 'alertdialog' ||
        node.tagName === 'DIALOG' ||
        // Look for non-hashed semantic indicators in the class list
        [...node.classList].some((c) => /^(card|modal|dialog|panel|action|approve)/i.test(c))
      ) {
        return normalize(node.textContent);
      }
      node = node.parentElement;
    }
    // Fallback: use the immediate parent's text
    return normalize(btn.parentElement ? btn.parentElement.textContent : '');
  }

  function cardAllowed(btn) {
    if (!APPROVE_ONLY_IF_CARD_CONTAINS.length) return true;
    const cardText = getCardText(btn);
    return APPROVE_ONLY_IF_CARD_CONTAINS.some((phrase) =>
      cardText.includes(phrase.toLowerCase())
    );
  }

  // Returns ALL unhandled, enabled, visible Approve buttons on the page.
  function findApproveButtons() {
    return [...document.querySelectorAll('button, [role="button"]')].filter(
      (el) =>
        normalize(el.textContent) === 'approve' &&
        !isDisabled(el) &&
        !el.dataset.pxAutoClicked &&
        isVisible(el)
    );
  }

  function scheduleClick(btn) {
    // Mark immediately so subsequent observer calls don't double-schedule.
    btn.dataset.pxAutoClicked = '1';
    console.log('[Perplexity Auto Approve] Approve button found — clicking in', CLICK_DELAY_MS, 'ms');

    setTimeout(() => {
      if (isVisible(btn) && !isDisabled(btn)) {
        btn.click();
        console.log('[Perplexity Auto Approve] Clicked.');
      } else {
        console.log('[Perplexity Auto Approve] Button gone/disabled/hidden before click — skipped.');
      }
    }, CLICK_DELAY_MS);
  }

  function maybeClickApprove() {
    if (!AUTO_APPROVE_ENABLED) return;
    findApproveButtons().forEach((btn) => {
      if (cardAllowed(btn)) scheduleClick(btn);
    });
  }

  // Debounced MutationObserver — avoids scanning the whole DOM on every
  // micro-mutation fired by React's render cycle.
  let debounceTimer = null;
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(maybeClickApprove, OBSERVER_DEBOUNCE_MS);
  });

  observer.observe(document.documentElement, { childList: true, subtree: true });

  // Run once immediately in case the card is already present on load.
  maybeClickApprove();
})();
