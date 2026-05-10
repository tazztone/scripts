// ==UserScript==
// @name         Perplexity Auto Approve
// @namespace    https://github.com/tazztone/scripts
// @version      0.1.0
// @description  Automatically clicks the Approve button on Perplexity agent action cards. Uses MutationObserver to handle SPA navigation. Includes a short delay before clicking so you can intervene.
// @author       tazztone
// @match        https://www.perplexity.ai/*
// @match        https://perplexity.ai/*
// @run-at       document-idle
// @grant        none
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
// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();

  function cardAllowed(btn) {
    if (!APPROVE_ONLY_IF_CARD_CONTAINS.length) return true;
    // Walk up to find the card container, then check its text
    const card = btn.closest('[class*="card"], [class*="dialog"], [class*="modal"], [role="dialog"], [role="alertdialog"]') || btn.parentElement;
    const cardText = normalize(card ? card.textContent : '');
    return APPROVE_ONLY_IF_CARD_CONTAINS.some((phrase) =>
      cardText.includes(phrase.toLowerCase())
    );
  }

  function findApproveButton() {
    return [...document.querySelectorAll('button, [role="button"]')].find(
      (el) =>
        normalize(el.textContent) === 'approve' &&
        !el.disabled &&
        !el.dataset.pxAutoClicked
    );
  }

  function maybeClickApprove() {
    if (!AUTO_APPROVE_ENABLED) return;

    const btn = findApproveButton();
    if (!btn) return;
    if (!cardAllowed(btn)) return;

    // Mark immediately so subsequent observer calls don't double-schedule
    btn.dataset.pxAutoClicked = '1';

    console.log('[Perplexity Auto Approve] Approve button found — clicking in', CLICK_DELAY_MS, 'ms');

    setTimeout(() => {
      // Re-check: button may have disappeared or been disabled during the delay
      if (document.contains(btn) && !btn.disabled) {
        btn.click();
        console.log('[Perplexity Auto Approve] Clicked.');
      } else {
        console.log('[Perplexity Auto Approve] Button gone or disabled before click — skipped.');
      }
    }, CLICK_DELAY_MS);
  }

  // Watch for dynamically injected approval cards (React SPA)
  const observer = new MutationObserver(() => maybeClickApprove());
  observer.observe(document.documentElement, { childList: true, subtree: true });

  // Also try immediately in case the card is already in the DOM on load
  maybeClickApprove();
})();
